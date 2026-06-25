import time
import platform

import cv2
import numpy as np

CAP_API = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_V4L2

WIDTH = 320
HEIGHT = 240

class Camera:
    def __init__(self, cap_index: int, num_scan_frames: int = 20, flip: bool = False) -> None:
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
        self.last_scan_time: float = 0

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
        self.last_scan_time = time.time()
    
    def close(self) -> None:
        self.cap.release()