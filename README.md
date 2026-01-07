# amnezia_stats

Simple panel that shows amnezia wireguard clients statistics based on hourly cron-based `wg show dump` command executed on amnezia-awg container.

## Prerequisites

Running `amnezia-awg` docker container deployed by official Amnezia client on dedicated Ubuntu machine (vps).

## Installation

Clone app:

``` shell
mkdir /apps/amnezia_stats
cd /apps
git clone https://github.com/pavelplus/amnezia_stats.git
```

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
    server_name csnl.bitpak.ru;

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

Script for stats dump and processing

``` bash
#!/bin/bash

# Create directory for logs if it doesn't exist
mkdir -p /var/log/wireguard-stats

# Generate filename with date and time
FILENAME="/var/log/wireguard-stats/wg-stats-$(date +'%Y-%m-%d_%H-%M-%S').txt"

# Execute the command in the docker container and save output to file
docker exec amnezia-awg wg show wg0 dump > "$FILENAME"

# Dump clients table
docker exec amnezia-awg cat /opt/amnezia/awg/clientsTable > /var/log/wireguard-stats/clientsTable.txt

# Execute processing python script
/apps/amnezia_stats/.venv/bin/python3 /apps/amnezia_stats/amnezia_stats/manage.py process_stats_files

# Optional: Add timestamp to the beginning of the file
# echo "# Generated at: $(date)" | cat - "$FILENAME" > /tmp/wg-tmp && mv /tmp/wg-tmp "$FILENAME"
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