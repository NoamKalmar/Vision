import numpy as np
import cv2

RED = (0, 0, 255)
GREEN = (0, 255, 0)
GRAY = (20, 20, 20)
WHITE = (255, 255, 255)

class MapDisplay:
    def __init__(self, map_length: int = 40, map_window_size: int = 600) -> None:
        self.map_length = map_length
        self.map_size = map_window_size
        self.cell_size = map_window_size // map_length
        self.map_image = np.zeros((map_window_size, map_window_size, 3), dtype=np.uint8)

        self.robot_x: int = 20
        self.robot_y: int = 20
        self.move_robot(self.robot_x, self.robot_y)

        self.horizontal_lines = ([False for _ in range(self.map_size)] for _ in range(self.map_size + 1))
        self.vertical_lines = ([False for _ in range(self.map_size + 1)] for _ in range(self.map_size))
        for y in range(self.map_size):
            for x in range(self.map_size):
                self.draw_cell_lines(x, y, False, False, False, False)

    def new_cell_info(self, x: int, y: int, left: bool, right: bool, top: bool, bottom: bool) -> None:
        self.move_robot(x, y)
        self.draw_cell_lines(x, y, left, right, top, bottom)

    def move_robot(self, x: int, y: int) -> None:
        # Remove the robot from the last cell
        self.mark_cell(self.robot_x, self.robot_y)
        # Draw the robot in the new cell
        self.mark_cell(x, y)
        center_point = (self.cell_size * x + self.cell_size // 2, self.cell_size * y + self.cell_size // 2)
        cv2.circle(self.map_image, center_point, self.cell_size // 2, RED, -1)
        self.robot_x = x
        self.robot_y = y

    def mark_cell(self, x: int, y: int) -> None:
        pt1 = (self.cell_size * x + 1, self.cell_size * y + 1)
        pt2 = (self.cell_size * (x + 1) - 1, self.cell_size * (y + 1) - 1)
        cv2.rectangle(self.map_image, pt1, pt2, GREEN, -1)

    def draw_cell_lines(self, x: int, y: int, left: bool, right: bool, top: bool, bottom: bool) -> None:
        top_left = (self.cell_size * x, self.cell_size * y)
        top_right = (self.cell_size * (x + 1), self.cell_size * y)
        bottom_left = (self.cell_size * x, self.cell_size * (y + 1))
        bottom_right = (self.cell_size * (x + 1), self.cell_size * (y + 1))
        
        left_color = WHITE if left else GRAY
        right_color = WHITE if right else GRAY
        top_color = WHITE if top else GRAY
        bottom_color = WHITE if bottom else GRAY
        
        cv2.line(self.map_image, top_left, bottom_left, left_color, 1)
        cv2.line(self.map_image, top_right, bottom_right, right_color, 1)
        cv2.line(self.map_image, top_left, top_right, top_color, 1)
        cv2.line(self.map_image, bottom_left, bottom_right, bottom_color, 1)