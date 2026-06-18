from enum import Enum
import time
import traceback
from typing import Literal

import cv2
import numpy as np

from camera import Camera
from serial_com import SerialCommunicator
from map_display import MapDisplay
import arduino_upload
import letters
import rings
import test


class VictimStatus(Enum):
    POTENTIAL = 0
    HARMED = 1
    UNHARMED = 2
    STABLE = 3
    FAKE = 4

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

BLACK_FRAME = np.zeros((240, 320, 3))

class Robot:
    def __init__(
            self,
            name: str,
            debug_mode: bool,
            serial_com: SerialCommunicator | None,
            left_camera: Camera | None,
            right_camera: Camera | None,
            time_to_stop: float,
            time_between_scans: float,
            letters_config: letters.LettersConfig,
            color_ranges: dict[rings.Color, tuple[tuple, tuple]],
            more_color_ranges: dict[rings.Color, tuple[tuple, tuple]]
    ) -> None:
        self.name = name
        self.debug_mode = debug_mode
        self.serial_com = serial_com
        self.letters_config = letters_config
        self.color_ranges = color_ranges
        self.more_color_ranges = more_color_ranges
        self.time_to_stop = time_to_stop
        self.time_between_scans = time_between_scans

        # Initalize a camera for each video capture
        self.cameras: list[Camera] = [left_camera, right_camera]

        self.no_scan: bool = False
        self.last_victim_time: float = 0
        self.last_serial_check_time: int = 0
        
        # Relevant only for debug mode
        if self.debug_mode:
            self.debug_display_mode: Literal["camera", "map"] = "camera"
            self.debug_window_title: str = ""
            self.debug_map_display: MapDisplay = MapDisplay()
            self.debug_chosen_camera_index: int = 0
            self.debug_ring: cv2.typing.MatLike | None = None
            self.debug_points: list[tuple[int, int]] | None = None
            self.debug_chosen_contour: cv2.typing.MatLike | None = None
            self.debug_threshold_mode: bool = False
            self.debug_contours_mode: bool = False

    def loop(self) -> None:
        if self.serial_com is not None:
            self.serial_com.try_connect()
        # self.debug_map_display.new_cell_info(18, 18, True, True, False, True)
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
        # Check for victims and act accor.dingly
        for i, camera in enumerate(self.cameras):
            if camera is None:
                continue
            camera.update_frame()
            if camera.error:
                print(f"Error while reading from camera index {i}")
                continue
            if not camera.on:
                continue
            if check_potential_victim(camera.frame, self.letters_config):
                # Check if the minimal time between scans from the same camera has passed
                if time.time() - self.last_victim_time < self.time_between_scans:
                    continue
                # Starting a scan and acting upon the results
                print(f"Starting a scan on camera index {i}")
                camera.scan()
                victim_status = self.get_victim_status(camera)
                if victim_status != VictimStatus.FAKE:
                    self.last_victim_time = time.time()
                    serial_error = self.handle_victim(i, victim_status)
                    if serial_error:
                        print("Serial Error: Trying to reconnect")
                        self.serial_com.try_connect()

        if self.debug_mode:
            return self.debug_loop()

        return False

    def serial_loop(self) -> None:
        if not self.serial_com.check_connection():
            self.serial_com.try_connect()
        self.serial_com.read()
        if self.serial_com.got_start_message():
            self.debug_map_display.reset_map()
        map_data = self.serial_com.get_map_data()
        if map_data is not None:
            x, y, left, right, top, bottom = map_data
            self.debug_map_display.new_cell_info(x, y, left, right, top, bottom)

    def debug_loop(self) -> bool:
        # Returns whether the user wants to quit
        cv2.namedWindow(self.name, cv2.WINDOW_AUTOSIZE)
        cv2.imshow(self.name, self.get_debug_image())

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
        elif key == ord("m"):
            self.debug_display_mode = "map"
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
                self.debug_display_mode = "camera"
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
        # colors, ring = rings.frames_get_colors(frames_buffer, self.color_ranges, self.more_color_ranges)
        # if ring is not None:
        #     self.debug_ring = ring
        #     self.debug_points = rings.point_per_layer(ring)
        # if colors is not None:
        #     print(colors)
        #     health = rings.colors_to_health(colors)
        #     status = HEALTH_TO_STATUS.get(health)
        #     if status is not None:
        #         return status
        # If neither a letter nor a ring were found, then return a fake status
        return VictimStatus.FAKE


    def handle_victim(self, camera_index: int, status: VictimStatus) -> bool:
        # Returns wether the message was sent successfully
        print(f"Handling victim of status {status} coming from camera {camera_index}")
        if self.serial_com is None:
            return False
        error = self.serial_com.send_victim_message(camera_index, status.value)
        return error

    def get_debug_image(self) -> cv2.typing.MatLike:
        if self.debug_display_mode == "map":
            return self.debug_map_display.map_image
        elif self.debug_display_mode == "camera":
            # frames = np.hstack((self.get_debug_camera_image(0), self.get_debug_camera_image(1)))
            # return frames
            return self.get_debug_camera_image(self.debug_chosen_camera_index)
        return
    
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
        if self.debug_ring is not None:
            cv2.circle(frame, (self.debug_ring[0], self.debug_ring[1]), self.debug_ring[2], GREEN, 3)
        if self.debug_points is not None:
            for point in self.debug_points:
                cv2.circle(frame, point, 1, WHITE, 3)
        if self.debug_chosen_contour is not None:
            cv2.drawContours(frame, [self.debug_chosen_contour], 0, GREEN, 3)
        status = f"{self.debug_chosen_camera_index}: On" if camera.on else f"{self.debug_chosen_camera_index}: Off"
        cv2.putText(frame, status, (0, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, 2, cv2.LINE_AA)
        return frame

    def debug_wait_for_ready(self, timeout: float = 3) -> bool:
        start_time = time.time()
        while time.time() - start_time <= timeout:
            if self.serial_com is not None:
                self.serial_com.read()
                if self.serial_com.got_ready():
                    return True
            for camera in self.cameras:
                if camera is not None:
                    camera.update_frame()
            if self.debug_mode:            
                self.debug_loop()
        return False

    def clear_debug(self) -> None:
        self.debug_ring = None
        self.debug_contours = None
        self.debug_chosen_contour = None
        self.debug_points = None
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
    contours = letters.filter_contours_by_area(contours, letters_config.min_area)
    contours = letters.filter_contours_by_ratio(contours, (0.5, 2.0))
    if len(contours) > 0 and len(contours) < 5:
        # print("len", len(contours))
        return True
    # if letters.check_potential_letter(image, letters_config):
    #     return True
    # if rings.check_potential_ring(image):
    #     return True
    return False

def get_white_percent(image: cv2.typing.MatLike) -> float:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_WHITE, UPPER_WHITE)
    white = cv2.countNonZero(mask)
    total_pixels = mask.size
    return white / total_pixels