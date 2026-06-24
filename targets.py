import cv2
import numpy as np
from enum import Enum
from dataclasses import dataclass
from collections import Counter
from itertools import chain
from typing import Sequence
from math import floor

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

BLACK_MAX_VALUE = 53

def get_circle(frame: cv2.typing.MatLike) -> tuple[cv2.typing.Point2f, float] | None:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # filter by area and circularity
    contours = list(filter(lambda c: cv2.contourArea(c) > 200, contours))
    contours = list(filter(lambda c: (4 * np.pi * cv2.contourArea(c)) / (cv2.arcLength(c, True) ** 2) > 0.80, contours))
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
        times = floor(pixels / (total_pixels / 6))
        for _ in range(times):
            colors.append(color)
    # Invalid result
    if len(colors) != 5 or None in colors:
        return None
    return colors

def get_color_counts(hsv_frame: cv2.typing.MatLike) -> dict[Color, int]:
    h = hsv_frame[:, :, 0]
    s = hsv_frame[:, :, 1]
    v = hsv_frame[:, :, 2]
    black_mask = v < 50
    color_mask = (v >= 50) & (s > 50)
    counts = {
        Color.BLACK: np.sum(black_mask),
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

def get_health_from_colors(colors: list[Color]) -> int:
    health = 0
    for color in colors:
        health += COLOR_TO_HEALTH_VALUE[color]
    return health

def get_cognitive_target_health(frames: Sequence[cv2.typing.MatLike]) -> int:
    counter = Counter()
    for frame in frames:
        colors = get_colors(frame)
        if colors is None:
            counter[None] += 1
            continue
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