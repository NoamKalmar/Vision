from enum import Enum
import time
import traceback

import cv2
import numpy as np

from camera import Camera
from serial_com import SerialCommunicator
from map_display import MapDisplay
import arduino_upload
import letters
import targets
from win32api import GetSystemMetrics

class VictimStatus(Enum):
    STABLE = 0
    UNHARMED = 1
    HARMED = 2
    FAKE = 3

HEALTH_TO_STATUS = {2: VictimStatus.HARMED, 1: VictimStatus.UNHARMED, 0: VictimStatus.STABLE}
LETTER_TO_STATUS = {
    letters.Letter.PHI: VictimStatus.HARMED, 
    letters.Letter.PSI: VictimStatus.STABLE,
    letters.Letter.OMEGA: VictimStatus.UNHARMED
}

WHITE = (255, 255, 255)
RED = (0, 0, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)

TIME_BETWEEN_SERIAL_CONNECTION_CHECKS = 5

LOWER_WHITE = np.array([0, 0, 160])
UPPER_WHITE = np.array([180, 60, 255])

BLACK_FRAME = np.zeros((480, 480, 3))

SCREEN_WIDTH = GetSystemMetrics(0)
SCREEN_HEIGHT = GetSystemMetrics(1)

class Robot:
    def __init__(
            self,
            name: str,
            debug_mode: bool,
            serial_com: SerialCommunicator | None,
            left_camera: Camera | None,
            right_camera: Camera | None,
            continue_waiting_timeout: float,
            letters_config: letters.LettersConfig,
    ) -> None:
        self.name = name
        self.debug_mode = debug_mode
        self.serial_com = serial_com
        self.letters_config = letters_config
        self.continue_waiting_timeout = continue_waiting_timeout

        self.cameras: list[Camera] = [left_camera, right_camera]
        self.waiting_cameras: list[int] = []

        self.last_victim_time: float = 0
        
        # Relevant only for debug mode
        if self.debug_mode:
            self.debug_map_display: MapDisplay = MapDisplay()
            self.debug_chosen_camera_index: int = 0
            self.debug_chosen_contour: cv2.typing.MatLike | None = None
            self.debug_threshold_mode: bool = False
            self.debug_contours_mode: bool = False
            self.debug_camera_positions_set: bool = False

    def loop(self) -> None:
        if self.serial_com is not None:
            self.serial_com.try_connect()
        try:
            while True:
                try:
                    quit = self.loop_cycle()
                    if quit:
                        break
                except Exception as e:
                    # If debug mode is on, then crash the program with the error
                    # Otherwise, just print the error message and move on to the next loop cycle
                    if self.debug_mode:
                        raise e
                    traceback.print_exc()
        finally:
            self.close()

    def loop_cycle(self) -> bool:
        # Check serial connection and detect if needed
        if self.serial_com is not None:
            self.serial_loop()
        if time.time() - self.last_victim_time > self.continue_waiting_timeout:
            self.continue_cameras()
        # Check for victims and act accordingly
        for i in range(len(self.cameras)):
            if self.cameras[i] is not None:
                self.cameras[i].update_frame()
                self.check_and_handle_victim(i)

        if self.debug_mode:
            return self.debug_loop()

        return False

    def serial_loop(self) -> None:
        if not self.serial_com.check_connection():
            self.serial_com.try_connect()
        self.serial_com.read()
        if self.serial_com.got_start_message():
            self.continue_cameras()
            self.debug_map_display.reset_map()
        if self.serial_com.got_continue_message():
            self.continue_cameras()
        if self.debug_mode:
            map_data = self.serial_com.get_map_data()
            if map_data is not None:
                x, y, left, right, top, bottom = map_data
                self.debug_map_display.new_cell_info(x, y, left, right, top, bottom)

    def check_and_handle_victim(self, camera_index: int) -> None:
        camera = self.cameras[camera_index]
        if camera is None:
            return
        if camera.error:
            print(f"Error while reading from camera index {camera_index}")
            return
        if not camera.on:
            return
        if check_potential_victim(camera.frame, self.letters_config):
            # Starting a scan and acting upon the results
            print(f"Starting a scan on camera index {camera_index}")
            camera.scan()
            victim_status = self.get_victim_status(camera)
            if victim_status != VictimStatus.FAKE:
                camera.on = False
                self.waiting_cameras.append(camera_index)
                self.last_victim_time = time.time()
                serial_error = self.handle_victim(camera_index, victim_status)
                if serial_error:
                    print("Serial Error: Trying to reconnect")
                    self.serial_com.try_connect()

    def continue_cameras(self) -> None:
        for camera_index in self.waiting_cameras:
            self.cameras[camera_index].on = True
        self.waiting_cameras = []

    def debug_loop(self) -> bool:
        # Returns whether the user wants to quit
        self.display_debug()

        key = cv2.waitKey(1)
        if key == ord("q"):
            return True
        elif key == ord("r"):
            self.clear_debug()
        elif key == ord("t"):
            self.debug_threshold_mode = not self.debug_threshold_mode
        elif key == ord("c"):
            self.debug_contours_mode = not self.debug_contours_mode
        elif key == ord("o"):
            self.cameras[self.debug_chosen_camera_index].on = not self.cameras[self.debug_chosen_camera_index].on
        elif key == ord("u"):
            try:
                arduino_upload.start()
            except:
                pass
        # If the key is a digit, then the debug frame should be the frame coming from the camera in that index
        try:
            if chr(key).isdigit():
                index = int(chr(key))
                if index < len(self.cameras):
                    self.debug_chosen_camera_index = index
        except ValueError:
            pass

    def get_victim_status(self, camera: Camera) -> VictimStatus:
        frames_buffer = camera.frames_buffer
        if len(frames_buffer) == 0:
            print("Can't check victim status when the frames buffer is empty")
            return None
        # First check for a letter
        letter, contour = letters.frames_get_letter(frames_buffer, self.letters_config)
        if letter is not None:
            print(letter)
            self.debug_chosen_contour = contour
            status = LETTER_TO_STATUS.get(letter)
            return status
        # If no letter was found, check for a ring
        health = targets.get_cognitive_target_health(frames_buffer)
        if health is None:
            return VictimStatus.FAKE
        status = HEALTH_TO_STATUS.get(health)
        if status is None:
            return VictimStatus.FAKE
        return status

    def handle_victim(self, camera_index: int, status: VictimStatus) -> bool:
        # Returns wether the message was sent successfully
        print(f"Handling victim of status {status} coming from camera {camera_index}")
        if self.serial_com is None:
            return False
        error = self.serial_com.send_victim_message(camera_index, status.value)
        return error

    def display_debug(self) -> cv2.typing.MatLike:
        cv2.imshow("Map", self.debug_map_display.map_image)
        if self.cameras[0] is not None:
            cv2.imshow("Left Camera", self.get_debug_camera_image(0))
            if not self.debug_camera_positions_set:
                cv2.moveWindow(
                    "Left Camera", 
                    SCREEN_WIDTH // 10,
                    SCREEN_HEIGHT // 2 - cv2.getWindowImageRect("Left Camera")[3] // 2
                )
        if self.cameras[1] is not None:
            cv2.imshow("Right Camera", self.get_debug_camera_image(1))
            if not self.debug_camera_positions_set:
                print(SCREEN_WIDTH)
                cv2.moveWindow(
                    "Right Camera",
                    SCREEN_WIDTH - cv2.getWindowImageRect("Right Camera")[2] - SCREEN_WIDTH // 10,
                    SCREEN_HEIGHT // 2 - cv2.getWindowImageRect("Right Camera")[3] // 2
                )
        self.debug_camera_positions_set = True
    
    def get_debug_camera_image(self, camera_index: int) -> cv2.typing.MatLike:
        if len(self.cameras) == 0:
            return BLACK_FRAME
        camera = self.cameras[camera_index]
        if camera is None or camera.error:
            return BLACK_FRAME
        
        frame = camera.frame.copy()

        # Threshold mode cannot work with the other modes
        if self.debug_threshold_mode:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, frame = cv2.threshold(frame, self.letters_config.binary_threshold, 255, cv2.THRESH_BINARY_INV)
            return frame
        
        if self.debug_contours_mode:
            contours = letters.get_contours(frame, self.letters_config.binary_threshold)
            cv2.drawContours(frame, contours, -1, RED, 3)
        if self.debug_chosen_contour is not None and len(self.waiting_cameras) != 0:
            if camera_index == self.waiting_cameras[-1]:
                cv2.drawContours(frame, [self.debug_chosen_contour], 0, GREEN, 3)
        status = f"{camera_index}: On" if camera.on else f"{camera_index}: Off"
        cv2.putText(frame, status, (0, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, 2, cv2.LINE_AA)

        return frame

    def clear_debug(self) -> None:
        self.debug_contours = None
        self.debug_chosen_contour = None
        self.debug_contours_mode = None
        self.debug_threshold_mode = None

    def close(self) -> None:
        if self.serial_com is not None:
            self.serial_com.close()
        for camera in self.cameras:
            if camera is None:
                continue
            camera.close()
        cv2.destroyAllWindows()

def check_potential_victim(image: cv2.typing.MatLike, letters_config: letters.LettersConfig) -> bool:
    contours = letters.get_contours(image, letters_config.binary_threshold)
    if len(contours) > 30:
        return False
    contours = letters.filter_contours_by_area(contours, letters_config.area_range)
    contours = letters.filter_contours_by_ratio(contours, (0.5, 2.0))
    if len(contours) > 0 and len(contours) < 5:
        return True
    return False