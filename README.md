# amnezia_stats

Simple panel that shows amnezia wireguard clients statistics based on hourly cron-based `wg show dump` command executed on amnezia-awg container.

## Prerequisites

Running `amnezia-awg` docker container deployed by official Amnezia client on dedicated Ubuntu machine (vps).

## Installation

Clone app:

``` shell
mkdir /apps
cd /apps
git clone https://github.com/pavelplus/amnezia_stats.git
```

Setup `.env` variables:

``` shell
cd /apps/amnezia_stats/amnezia_stats
cp .env.example .env
nano .env
```

`.env` example:

``` ini
DEBUG=False
SECRET_KEY=<generate django secret key>
ALLOWED_HOSTS=awg.domain.com,ip.add.re.ss
STATIC_ROOT=/apps/amnezia_stats/static
STATS_DIR=/var/log/wireguard-stats
# Comma-separated list of amnezia docker container names to collect stats from.
# Each entry may be "name" or "name:interface" (interface defaults to wg0).
# Dump files are stored in per-container subfolders: STATS_DIR/<container>/
AMNEZIA_CONTAINERS=amnezia-awg:wg0
TIME_ZONE=Europe/Moscow
SERVER_TIME_ZONE_OFFSET=0
AMNEZIA_MAIN_CLIENT_TIME_ZONE_OFFSET=3
```

Multiple containers are supported: list their docker names comma-separated, e.g. `AMNEZIA_CONTAINERS=amnezia-awg:wg0,amnezia-awg-2:awg0`. The optional `:interface` suffix sets the wireguard interface name used by the `wg show` dump command inside that container (defaults to `wg0`). Statistics for each container are shown separately and switchable by the container dropdown on the stats page.

Boot up venv, install modules and start django-app:

``` shell
cd /apps/amnezia_stats
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py createsuperuser
```

## Setup nginx+gunicorn to serve webapp
### gunicorn

Install in venv:
```
pip install gunicorn
```

Test:
```
gunicorn --bind 0.0.0.0:8000 config.wsgi:application
```

Create a Systemd Service File:
```
nano /etc/systemd/system/gunicorn.service
```

``` ini
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/apps/amnezia_stats/amnezia_stats
ExecStart=/apps/amnezia_stats/.venv/bin/gunicorn \
        --access-logfile - \
        --workers 1 \
        --bind unix:/run/gunicorn.sock \
        --timeout 60 \
        config.wsgi:application

[Install]
WantedBy=multi-user.target
```

Start and enable
``` shell
systemctl daemon-reload
systemctl start gunicorn
systemctl status gunicorn
systemctl enable gunicorn
```

### nginx

```
apt install nginx
```

```
nano /etc/nginx/sites-available/amnezia_stats
```

``` nginx
server {
    listen 80;
    server_name <<INSERT SERVER URL OR IP>>;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root /apps/amnezia_stats;  # /static/....
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```

``` shell
ln -s /etc/nginx/sites-available/amnezia_stats /etc/nginx/sites-enabled
nginx -t  # Test the configuration for syntax errors
systemctl restart nginx
nginx -s reload  # как варинат вместо systemctl
```

## Cron job for stats processing

Create log dirs:
``` bash
mkdir /var/log/wireguard-stats
```

Script for stats dump and processing. It reads the container list from `.env` (`AMNEZIA_CONTAINERS`) and dumps stats for every container into its own subfolder:

``` bash
#!/bin/bash

# Load AMNEZIA_CONTAINERS from the app .env
ENV_FILE="/apps/amnezia_stats/amnezia_stats/.env"
AMNEZIA_CONTAINERS=$(grep -E '^AMNEZIA_CONTAINERS=' "$ENV_FILE" | cut -d'=' -f2- | tr -d ' ')
AMNEZIA_CONTAINERS=${AMNEZIA_CONTAINERS:-amnezia-awg}

STATS_DIR=$(grep -E '^STATS_DIR=' "$ENV_FILE" | cut -d'=' -f2- | tr -d ' ')
STATS_DIR=${STATS_DIR:-/var/log/wireguard-stats}

# Create base directory for logs if it doesn't exist
mkdir -p "$STATS_DIR"

# Dump stats from every configured container into its own subfolder.
# Each entry may be "name" or "name:interface" (interface defaults to wg0).
for ENTRY in ${AMNEZIA_CONTAINERS//,/ }; do
    CONTAINER="${ENTRY%%:*}"
    INTERFACE="${ENTRY##*:}"
    if [ "$INTERFACE" = "$CONTAINER" ]; then
        INTERFACE="wg0"
    fi

    mkdir -p "$STATS_DIR/$CONTAINER/processed"

    # Generate filename with date and time
    FILENAME="$STATS_DIR/$CONTAINER/wg-stats-$(date +'%Y-%m-%d_%H-%M-%S').txt"

    # Execute the command in the docker container and save output to file
    docker exec "$CONTAINER" wg show "$INTERFACE" dump > "$FILENAME"

    # Dump clients table
    docker exec "$CONTAINER" cat /opt/amnezia/awg/clientsTable > "$STATS_DIR/$CONTAINER/clientsTable.txt"
done

# Execute processing python script (processes all configured containers)
/apps/amnezia_stats/.venv/bin/python3 /apps/amnezia_stats/amnezia_stats/manage.py process_stats_files
```

Save this script to `/usr/local/bin/wg-stats-hourly.sh` and make it executable:

``` bash
sudo nano /usr/local/bin/wg-stats-hourly.sh
# Paste the script content
sudo chmod +x /usr/local/bin/wg-stats-hourly.sh
```

Edit the crontab:

``` bash
sudo crontab -e
```

Add this line to run the script every hour:

``` bash
# Run WireGuard stats every hour at minute 0
0 * * * * /usr/local/bin/wg-stats-hourly.sh

# Alternatively, if you want to run at a specific minute (e.g., minute 5):
# 5 * * * * /usr/local/bin/wg-stats-hourly.sh
```

## Access panel

Go to http://your-ip-or-domain/stats
Django admin: http://your-ip-or-domain/admin

## Upgrading from single-container setup

If you are upgrading an existing installation:

1. Add containers list to `.env` (the first container is used for all existing data):

``` ini
AMNEZIA_CONTAINERS=amnezia-awg
```

2. Apply the migration (it tags all existing clients with the first container):

``` shell
python3 manage.py migrate
```

3. Move existing dump files into the first container's subfolder:

``` bash
cd /var/log/wireguard-stats
mv wg-stats-*.txt clientsTable.txt amnezia-awg/
```

> Note: files left directly in `STATS_DIR` root (old layout) are still processed and tagged with the first configured container, so this step is optional.