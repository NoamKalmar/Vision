import numpy as np

class MapDisplay:
    def __init__(self, map_length: int = 40, map_window_size: int = 600) -> None:
        self.map_length = map_length
        self.map_size = map_window_size
        self.map_image = np.zeros((map_window_size, map_window_size, 3)) 