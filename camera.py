from collections import deque
import platform

import cv2
import numpy as np

CAP_API = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_V4L2

WIDTH = 320
HEIGHT = 240

class Camera:
    def __init__(self, cap_index: int, num_scan_frames: int = 20, flip: bool = False, saved_last_detections: int = 5) -> None:
        self.cap_index = cap_index
        self.num_scan_frames = num_scan_frames
        self.flip = flip
        self.cap = cv2.VideoCapture(cap_index, CAP_API)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
        self.on: bool = True
        self.error: bool = False
        self.frame: cv2.typing.MatLike | None = None
        self.frames_buffer: list[cv2.typing.MatLike] = []
        self.scan_mode: bool = False
        self.last_detections: deque[object] = deque([None for _ in range(saved_last_detections)], maxlen=saved_last_detections)

    def update_frame(self) -> None:
        ret, self.frame = self.cap.read()
        self.error = not ret
        if not self.error:
            if self.flip:
                self.frame = cv2.flip(self.frame, -1)
    
    def scan(self) -> None:
        self.frames_buffer = []
        while len(self.frames_buffer) <= self.num_scan_frames:
            self.update_frame()
            self.frames_buffer.append(self.frame)

    def add_detection(self, detection: object) -> None:
        self.last_detections.append(detection)
    
    def is_detection_significant(self) -> bool:
        count = self.last_detections.count(self.last_detections[-1])
        if count > len(self.last_detections) / 2:
            return True
        return False
    
    def clear_detections(self) -> None:
        for i in range(len(self.last_detections)):
            self.last_detections[i] = None

    def close(self) -> None:
        self.cap.release()