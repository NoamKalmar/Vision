from enum import Enum
import time

import cv2
import numpy as np

from camera import Camera
from serial_com import SerialCommunicator
import letters
import rings


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

class Robot:
    def __init__(
            self,
            name: str,
            serial_com: SerialCommunicator | None,
            cap_indexes: list[int],
            num_scan_frames: int,
            time_to_stop: float,
            time_between_scans: float,
            letters_config: letters.LettersConfig,
            color_ranges: dict[rings.Color, tuple[tuple, tuple]],
            more_color_ranges: dict[rings.Color, tuple[tuple, tuple]]
    ) -> None:
        self.name = name
        self.serial_com = serial_com
        self.letters_config = letters_config
        self.color_ranges = color_ranges
        self.more_color_ranges = more_color_ranges
        self.time_to_stop = time_to_stop
        self.time_between_scans = time_between_scans

        # Initalize a camera for each video capture
        self.cameras: list[Camera] = []
        for cap_index in cap_indexes:
            camera = Camera(
                cap_index=cap_index,
                num_scan_frames=num_scan_frames
            )
            self.cameras.append(camera)

        self.no_scan: bool = False  

        self.debug_chosen_camera_index: int = 0
        self.debug_ring: cv2.typing.MatLike | None = None
        self.debug_points: list[tuple[int, int]] | None = None
        self.debug_chosen_contour: cv2.typing.MatLike | None = None
        self.debug_threshold_mode: bool = False
        self.debug_contours_mode: bool = False

    def loop(self) -> None:
        self.serial_com.try_connect()
        while True:
            # try:
            quit = self.loop_cycle()
            if quit:
                break
            # except:
                # print("An error occured")
        self.close()

    def loop_cycle(self) -> bool:
        for i, camera in enumerate(self.cameras):
            if not camera.on:
                continue
            camera.update_frame()
            if camera.error:
                print(f"Error while reading from camera index {i}")
                continue
            if check_potential_victim(camera.frame, self.letters_config):
                # Check if the minimal time between scans from the same camera has passed
                if time.time() - camera.last_scan_time < self.time_between_scans:
                    continue
                # Sending a signal for the robot to stop
                self.handle_victim(i, VictimStatus.POTENTIAL)
                print(f"Starting a scan on camera index {i} in {self.time_to_stop} seconds")
                time.sleep(self.time_to_stop)
                # Starting a scan and acting upon the results
                camera.scan()
                victim_status = self.get_victim_status(camera)
                serial_error = self.handle_victim(i, victim_status)
                if serial_error:
                    print("Serial Error: Trying to reconnect")
                    self.serial_com.try_connect()

        self.show_debug(self.debug_chosen_camera_index)

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
        # If the key is a digit, then the debug frame should be the frame coming from the camera in that index
        try:
            if chr(key).isdigit():
                index = int(chr(key))
                if index < len(self.cameras):   
                    self.debug_chosen_camera_index = index
        except ValueError:
            pass

        return False

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
        colors, ring = rings.frames_get_colors(frames_buffer, self.color_ranges, self.more_color_ranges)
        if colors is not None:
            print(colors)
            self.debug_ring = ring
            self.debug_points = rings.point_per_layer(ring)
            health = rings.colors_to_health(colors)
            status = HEALTH_TO_STATUS.get(health)
            if status is not None:
                return status
        # If neither a letter nor a ring were found, then return a fake status
        return VictimStatus.FAKE


    def handle_victim(self, camera_index: int, status: VictimStatus) -> bool:
        # Returns wether the message was sent successfully
        print(f"Handling victim of status {status} coming from camera {camera_index}")
        if self.serial_com is None:
            return False
        error = self.serial_com.send_victim_message(camera_index, status.value)
        return error

    def show_debug(self, camera_index: int) -> None:
        camera = self.cameras[camera_index]
        if camera.error:
            cv2.imshow("Error", np.zeros((480, 480, 3)))
            return
        frame = camera.frame.copy()
        status = f"{camera_index}: On" if camera.on else f"{camera_index}: Off"
        cv2.putText(frame, status, (0, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, 2, cv2.LINE_AA)
        # Threshold mode cannot work with the other modes
        if self.debug_threshold_mode:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, frame = cv2.threshold(frame, self.letters_config.binary_threshold, 255, cv2.THRESH_BINARY_INV)
            cv2.imshow(self.name, frame)
            return
        
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
        cv2.imshow(self.name, frame)

    def clear_debug(self) -> None:
        self.debug_ring = None
        self.debug_contours = None
        self.debug_chosen_contour = None
        self.debug_points = None
        self.debug_contours_mode = None
        self.debug_threshold_mode = None

    def close(self) -> None:
        for camera in self.cameras:
            camera.close()
        cv2.destroyAllWindows()

def check_potential_victim(image: cv2.typing.MatLike, letters_config: letters.LettersConfig) -> bool:
    return rings.check_potential_ring(image) or letters.check_potential_letter(image, letters_config)