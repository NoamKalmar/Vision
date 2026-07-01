from enum import Enum
from collections import Counter
from typing import Sequence
from math import floor

import numpy as np
import cv2

import contour_utils

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

MORPH_KERNEL = np.ones((11, 11), np.uint8)

COLOR_RANGES = {
    Color.RED: [
        (np.array([0, 120, 70]), np.array([10, 255, 255])),
        (np.array([165, 120, 70]), np.array([180, 255, 255]))
    ],
    Color.YELLOW: [
        (np.array([15, 50, 50]), np.array([35, 255, 255]))
    ],
    Color.GREEN: [
        (np.array([35, 50, 50]), np.array([90, 255, 255]))
    ],
    Color.BLUE: [
        (np.array([90, 50, 50]), np.array([130, 255, 255]))
    ],
    Color.BLACK: [
        (np.array([0, 0, 0]), np.array([180, 255, 50]))
    ]
}

MIN_CIRCULAIRTY = 0.75

def get_colored_contours(frame: cv2.typing.MatLike) -> Sequence[cv2.typing.MatLike]:
    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = np.zeros((h, w), dtype=np.uint8)

    for color, ranges in COLOR_RANGES.items():
        color_mask = np.zeros((h, w), dtype=np.uint8)
        for lower, upper in ranges:
            color_mask |= cv2.inRange(hsv, lower, upper)
        mask |= color_mask
    # mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, MORPH_KERNEL)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours, mask

def get_circle(frame: cv2.typing.MatLike) -> tuple[cv2.typing.Point2f, float] | None:
    contours, _ = get_colored_contours(frame)
    contours = contour_utils.filter_contours(contours, (1000, 100000), (0.75, 1.25))
    contours = list(filter(lambda c: contour_utils.get_circularity(c) > MIN_CIRCULAIRTY, contours))
    if len(contours) == 0:
        return None
    circle_contour = max(contours, key=lambda c: cv2.contourArea(c)) # Choose the biggest contour
    circle = cv2.minEnclosingCircle(circle_contour)
    return circle

def get_colors(frame: cv2.typing.MatLike) -> list[Color] | None:
    circle = get_circle(frame)
    if circle is None:
        return None
    (cx, cy), R = circle
    polar = cv2.warpPolar(frame, (360, int(R)), (cx, cy), R, cv2.WARP_POLAR_LINEAR)
    hsv = cv2.cvtColor(polar, cv2.COLOR_BGR2HSV)
    color_counts = get_color_counts(hsv)
    total_pixels = 360 * R
    colors = []
    for color, pixels in color_counts.items():
        times = floor(pixels / (total_pixels / 7))
        for _ in range(times):
            colors.append(color)
    return colors

def get_color_counts(hsv_frame: cv2.typing.MatLike) -> dict[Color, int]:
    h = hsv_frame[:, :, 0]
    s = hsv_frame[:, :, 1]
    v = hsv_frame[:, :, 2]
    black_mask = v < 50
    color_mask = (v >= 50) & (s > 50)
    counts = {
        Color.BLACK: int(np.sum(black_mask)),
        Color.RED: 0,
        Color.YELLOW: 0,
        Color.GREEN: 0,
        Color.BLUE: 0,
        None: 0
    }
    h_color = h[color_mask]
    for hue_val in h_color:
        color = classify_hue(hue_val)
        if color in counts:
            counts[color] += 1
    return counts

def get_health_from_colors(colors: list[Color] | None) -> int | None:
    if colors is None or len(colors) != 5 or None in colors:
        return None
    health = 0
    for color in colors:
        health += COLOR_TO_HEALTH_VALUE[color]
    return health

def get_cognitive_target_health(frames: Sequence[cv2.typing.MatLike]) -> int | None:
    counter = Counter()
    for frame in frames:
        circle = get_circle(frame)
        if circle is None:
            return None
        colors = get_layer_colors(frame, circle)
        health = get_health_from_colors(colors)
        counter[health] += 1
    return max(counter, key=counter.get)

def classify_hue(hue) -> Color | None:
    if hue < 10 or hue > 170:
        return Color.RED
    elif 15 <= hue < 35:
        return Color.YELLOW
    elif 35 <= hue < 85:
        return Color.GREEN
    elif 85 <= hue < 130:
        return Color.BLUE
    return None


def classify_layer(frame: cv2.typing.MatLike, circle: tuple, layer_index: int) -> Color | None:
    (cx, cy), R = circle
    h, w = frame.shape[:2]
    Y, X = np.indices((h, w))
    dist_squared = (X - cx) ** 2 + (Y - cy) ** 2
    min_dist = layer_index * (R / 5)
    max_dist = (layer_index + 1) * (R / 5)
    mask = (dist_squared >= min_dist ** 2) & (dist_squared <= max_dist ** 2)
    hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hsv_pixels = hsv_frame[mask]
    colors = classify_hsv(hsv_pixels)
    color_votes = Counter(colors)
    return max(color_votes, key=color_votes.get)

def get_layer_colors(frame: cv2.typing.MatLike, circle: tuple) -> list[Color | None]:
    colors = []
    for i in range(5):
        color = classify_layer(frame, circle, i)
        colors.append(color)
    return colors

def classify_hsv(hsv: np.ndarray) -> Color | None:
    h = hsv[:, 0]
    v = hsv[:, 2]
    colors = np.full(len(h), None, dtype=object)
    colors[(h < 10) | (h > 170)] = Color.RED
    colors[(h >= 15) & (h < 35)] = Color.YELLOW
    colors[(h >= 35) & (h < 85)] = Color.GREEN
    colors[(h >= 85) & (h < 130)] = Color.BLUE
    colors[v <= 55] = Color.BLACK
    return colors