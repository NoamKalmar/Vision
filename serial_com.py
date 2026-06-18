from time import sleep, time
import serial
from serial.tools.list_ports import comports

START_MESSAGE = "START"
MAP_MESSAGE = "map"


class SerialCommunicator:
    def __init__(self, default_port: str | None = None, baudrate: int = 9600) -> None:
        self.default_port = default_port
        self.baudrate = baudrate
        self.serial_com: serial.Serial | None = None

        self.got_start = False
        self.map_data: tuple[int, int, bool, bool, bool, bool] | None = None

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

    def check_connection(self) -> bool:
        # if self.serial_com is None:
        #     return False
        # try:
        #     self.serial_com.write(b".")
        # except serial.SerialException:
        #     return False
        # return True
        for port in comports():
            if port.device == self.serial_com.port:
                return True
        return False
    
    def send_victim_message(self, camera_index: int, victim_value: int) -> bool:
        """Message format:
        <camera_index>:<victim_value>:<(time_of_detection - start_time) (round to 1 decimal point) * 1000>:
        Returns whether there was an error
        """
        # if self.start_time == None:
        #     print("Error while trying to send message: START message have not been sent yet")
        #     return
        # message = f"{camera_index}:{victim_values}:"
        message = f"{camera_index}:{victim_value}:"
        
        print(f"Sending: {message}")
        try:
            self.serial_com.write(bytes(message, "utf-8"))
        except serial.SerialException:
            return True
        return False
    
    def read(self) -> None:
        if self.serial_com.in_waiting <= 0:
            return
        data = self.serial_com.readline().decode("utf-8").strip()
        print(f"Serial data: {data}")
        if START_MESSAGE in data:
            print(f"Got {START_MESSAGE} message")
            self.got_start = True
        if MAP_MESSAGE in data:
            # e.g. map:20:20:0:0:0:0:
            map_data = tuple(data.split(":")[1:-1])
            if len(map_data) != 6:
                return
            map_data = [int(x) for x in map_data]
            for i in range(2, 6):
                map_data[i] = bool(map_data[i])
            self.map_data = map_data

    def get_map_data(
            self
    ) -> tuple[int, int, bool, bool, bool, bool] | None:
        if self.map_data is not None:
            map_data = self.map_data
            self.map_data = None
            return map_data
        return None
    
    def got_start_message(self) -> bool:
        if self.got_start:
            self.got_start = False
            return True
        return False

    def close(self) -> None:
        self.serial_com.close()