import cv2
import numpy as np
from enum import Enum
from dataclasses import dataclass
from collections import Counter
from itertools import chain

class Color(Enum):
    BLACK = 0
    RED = 1
    YELLOW = 2
    GREEN = 3
    BLUE = 4

COLOR_TO_HEALTH_VALUE = {
    Color.BLACK: -2,
    Color.RED: -1,
    Color.YELLOW: 0,
    Color.GREEN: 1,
    Color.BLUE: 2
}

def check_potential_ring(image: cv2.typing.MatLike) -> bool:
    return get_circles(image) is not None

def get_circles(image: cv2.typing.MatLike) -> cv2.typing.MatLike | None:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, image.shape[0] / 8,
                                param1=150, param2=65,
                                minRadius=20, maxRadius=500)
    if circles is None:
        return []
    circles = np.uint16(np.around(circles))
    return circles[0]


def point_per_layer(circle: cv2.typing.MatLike) -> list[tuple[int, int]]:
    x, y, r = circle
    points = []
    for i in range(5):
        points.append([x, y - i * r // 5])
        if i != 0:
            points[i][1] -= r // 12  
    
    return points

def classify_color(
        hsv_color: cv2.typing.MatLike, 
        color_ranges: dict[Color, tuple[tuple, tuple]],
        more_color_ranges: dict[Color, tuple[tuple, tuple]]
) -> Color:
    "Will return the color corresponding to the correct range, -1 if black, else None"
    if hsv_color[2] < 50: # checking for black
        return Color.BLACK
    for color, (range_low, range_high) in chain(color_ranges.items(), more_color_ranges.items()):
        if np.all((hsv_color >= range_low) & (hsv_color <= range_high)):
            return color
    return None

# def frames_get_colors(
#         last_frames: list[cv2.typing.MatLike], 
#         color_ranges: dict[Color, tuple[tuple, tuple]],
#         more_color_ranges: dict[Color, tuple[tuple, tuple]]
# ) -> tuple[list[Color], tuple] | None:
#     """Returns the colors of the ring and the ring"""
#     # The biggest ring is the circle
#     ring = None
#     for frame in last_frames:
#         circles = get_circles(frame)
#         if len(circles) == None:
#             continue
#         biggest_circle = max(circles, key=lambda circle: circle[2])
#         if ring is None:
#             ring = biggest_circle
#         else:
#             ring = max(ring, biggest_circle, key=lambda circle: circle[2])
#     if ring is None:
#         return None, None
#     # For each layer, its color should be the color that was found in most frames
#     points = point_per_layer(ring)
#     layer_colors_counters = [Counter() for _ in range(5)]
#     for frame in last_frames:
#         for i, point in enumerate(points):
#             hsv_pixel = cv2.cvtColor(frame[point[1], point[0]].reshape(1, 1, 3), cv2.COLOR_BGR2HSV)[0][0]
#             color = classify_color(hsv_pixel, color_ranges, more_color_ranges)
#             if color is not None:
#                 layer_colors_counters[i][color] += 1
#     layer_colors = []
#     for i in range(5):
#         if len(layer_colors_counters[i]) == 0:
#             return None, None
#         layer_colors.append(layer_colors_counters[i].most_common(1)[0][0])
#     return layer_colors, ring

def frames_get_colors(
        last_frames: list[cv2.typing.MatLike], 
        color_ranges: dict[Color, tuple[tuple, tuple]],
        more_color_ranges: dict[Color, tuple[tuple, tuple]]
) -> tuple[list[Color], tuple] | None:
    """Returns the list of the colors, and the circle that was detected in the last frame"""
    layer_colors_counters = [Counter() for _ in range(5)]
    # For each frame, check what are the colors in each layer, and update the counters accordingly
    for frame in last_frames:
        circles = get_circles(frame)
        if len(circles) == 0:
            continue
        ring = max(circles, key=lambda circle: circle[2])
        points = point_per_layer(ring)
        for i, point in enumerate(points):
            hsv_pixel = cv2.cvtColor(frame[point[1], point[0]].reshape(1, 1, 3), cv2.COLOR_BGR2HSV)[0][0]
            color = classify_color(hsv_pixel, color_ranges, more_color_ranges)
            if color is not None:
                layer_colors_counters[i][color] += 1
    # Pick the colors that have the highest values in the counters
    layer_colors = []
    for counter in layer_colors_counters:
        if len(counter) == 0:
            return None, None
        layer_colors.append(counter.most_common(1)[0][0])
    return layer_colors, ring

def colors_to_health(colors: list[Color]) -> int | None:
    health = 0
    for color in colors:
        if color is None:
            return None
        health += COLOR_TO_HEALTH_VALUE[color]
    return health