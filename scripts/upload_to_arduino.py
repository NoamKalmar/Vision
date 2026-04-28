import requests
from pathlib import Path
from datetime import datetime

url = "https://localhost:5000/upload"
last_modified_time = None

def send_file(path: str):
    pass

def main():
    for f in Path(".").iterdir():
        if ".hex" in f and "bootloader" not in f:
            file = Path(f)
            modified_time = datetime.fromtimestamp(file.stat().st_mtime)
            if last_modified_time is None:
                last_modified_time = modified_time
                continue
            if last_modified_time == modified_time:
                send_file(f)

    with open(""):
        pass