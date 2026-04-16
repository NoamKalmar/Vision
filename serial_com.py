from time import sleep
import serial
from serial.tools.list_ports import comports

class SerialCommunicator:
    def __init__(self, default_port: str | None = None, baudrate: int = 9600) -> None:
        self.default_port = default_port
        self.baudrate = baudrate
        self.serial_com: serial.Serial | None = None


    def connect(self, port: str) -> bool:
        # Returns whether there was and error
        try:
            self.serial_com = serial.Serial(port, self.baudrate)
        except:
            print(f"Connetion to {port} failed")
            return True
        print(f"Connected to {port}")
        return False
    
    def wait_connect(self, time_between_checks: float = 2) -> None:
        # Waits for a new port to connect to
        while True:
            ports = comports()
            sleep(time_between_checks)
            print("Checking for a new device")
            new_ports = comports()
            added_ports = [port for port in new_ports if not port in ports]
            if len(added_ports) != 1:
                continue
            print(f"Trying to connect to {added_ports[0].device}")
            error = self.connect(added_ports[0].device)
            if not error:
                break
    
    def try_connect(self) -> None:
        # Tries to connect to the default port, if there was a failure then wait for a new port
        error = self.connect(self.default_port)
        if error:
            print("Could not connect to the default port. Waiting for a new port.")
            self.wait_connect()

    def send_victim_message(self, camera_index: int, victim_value: int) -> bool:
        """Message format: <camera_index>:<victim_value>
        Returns whether there was an error
        """
        message = f"{camera_index}:{victim_value}"
        try:
            self.serial_com.write(bytes(message, "utf-8"))
        except serial.SerialException:
            return True
        return False

    def close(self) -> None:
        self.serial_com.close()