from time import sleep, time
import serial
from serial.tools.list_ports import comports

START_MESSAGE = "START"
READY_MESSAGE = "READY"
CONTINUE_MESSAGE = "CONTINUE"
ENABLE_RIGHT_MESSAGE = "ENABLE_RIGHT"
ENABLE_LEFT_MESSAGE = "ENABLE_LEFT"
DISABLE_RIGHT_MESSAGE = "DISABLE_RIGHT"
DISABLE_LEFT_MESSAGE = "DISABLE_LEFT"


class SerialCommunicator:
    def __init__(self, default_port: str | None = None, baudrate: int = 9600) -> None:
        self.default_port = default_port
        self.baudrate = baudrate
        self.serial_com: serial.Serial | None = None

        self.start_time: float | None = None
        self.is_ready = False
        self.is_continue = True
        self.is_left_enabled = True
        self.is_right_enabled = True

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
    
    def send_victim_message(self, camera_index: int, victim_value: int, time_of_detection: float) -> bool:
        """Message format:
        <camera_index>:<victim_value>:<(time_of_detection - start_time) (round to 1 decimal point) * 1000>:
        Returns whether there was an error
        """
        # if self.start_time == None:
        #     print("Error while trying to send message: START message have not been sent yet")
        #     return
        # message = f"{camera_index}:{victim_value}:{int(round((time_of_detection - self.start_time) * 1000, -2))}:"
        message = f"{camera_index}:{victim_value}:0:"
        
        print(message)
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
        # if self.start_time is not None:
        #     print((time() - self.start_time) * 1000 - int(data))
        if START_MESSAGE in data:
            print(f"Got {START_MESSAGE} message")
            self.start_time = time()
            self.is_continue = True
        elif READY_MESSAGE in data:
            print(f"Got {READY_MESSAGE} message")
            self.is_ready = True
            self.is_continue = False
        elif CONTINUE_MESSAGE in data:
            print(f"Got {CONTINUE_MESSAGE} message")
            self.is_continue = True
        elif ENABLE_LEFT_MESSAGE in data:
            print(f"Got {ENABLE_LEFT_MESSAGE} message")
            self.is_enable_left = True
        elif ENABLE_RIGHT_MESSAGE in data:
            print(f"Got {ENABLE_RIGHT_MESSAGE} message")
            self.is_enable_right = True
        elif DISABLE_LEFT_MESSAGE in data:
            print(f"Got {DISABLE_LEFT_MESSAGE} message")
            self.is_left_enabled = False
        elif DISABLE_RIGHT_MESSAGE in data:
            print(f"Got {DISABLE_RIGHT_MESSAGE} message")
            self.is_right_enabled = False

    def got_ready(self) -> bool:
        if self.is_ready:
            self.is_ready = False
            return True
        return False

    def close(self) -> None:
        self.serial_com.close()