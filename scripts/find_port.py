from serial.tools.list_ports import comports

def find_port():
    input("If connected, disconnect the cable (enter to continue)")
    ports_without_wanted = comports()
    input("Connect the cable (enter to continue)")
    ports_with_wanted = comports()
    added_ports = [port for port in ports_with_wanted if not port in ports_without_wanted]
    if len(added_ports) < 1:
        print("Could not find any new ports. Try again.")
    elif len(added_ports) > 1:
        print(f"Found too many new ports: {added_ports}\nTrying again.")
    else:
        print(f"Port found: {added_ports[0]}")

if __name__ == "__main__":
    find_port()