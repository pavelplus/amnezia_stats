

def bytes_to_hrs(bytes: int) -> str:
    """bytes to Human Readable String"""
    
    if bytes < 1000:
        return f'{bytes} B'
    elif bytes < 1000*1000:
        return f'{bytes/1000:.1f} kB'
    elif bytes < 1000*1000*1000:
        return f'{bytes/1000/1000:.1f} MB'
    else:
        return f'{bytes/1000/1000/1000:.1f} GB'