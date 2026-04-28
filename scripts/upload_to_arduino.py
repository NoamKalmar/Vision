import requests
from pathlib import Path
from datetime import datetime
from time import sleep

IP_PATH = "ip.txt"

def read_ip() -> str:
    return ""

def send_file(url, file: Path) -> None:
    with file.open("rb") as f:
        response = requests.post(
            url,
            files={"file": f}
        )
        print(response.status_code)
        print(response.text)

def main():
    last_modified_time = None
    ip = Path(IP_PATH).read_text()
    url = f"https://{ip}/upload"
    while True:
        for file in Path(".").iterdir():
            if ".hex" in file.name and "bootloader" not in file.name:
                modified_time = datetime.fromtimestamp(file.stat().st_mtime)
                if last_modified_time is None:
                    last_modified_time = modified_time
                    continue
                if last_modified_time != modified_time:
                    last_modified_time = modified_time
                    send_file(url, file)
        sleep(1)

if __name__ == "__main__":
    main()