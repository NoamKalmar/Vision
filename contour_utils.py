from typing import Sequence

import cv2
import numpy as np

MORPH_KERNEL2 = np.ones((2, 2), np.uint8)
MORPH_KERNEL1 = np.ones((5, 5), np.uint8)

BINARY_THRESHOLD = 75

def get_contours(image: cv2.typing.MatLike) -> Sequence[cv2.typing.MatLike]:
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(grayscale, BINARY_THRESHOLD, 255, cv2.THRESH_BINARY_INV)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, MORPH_KERNEL1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, MORPH_KERNEL2)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours

def get_width_height_ratio(contour: cv2.typing.MatLike) -> float:
    _, _, w, h = cv2.boundingRect(contour)
    if h == 0: return 0
    return w / h

def get_extent(contour: cv2.typing.MatLike) -> float:
    _, _, w, h = cv2.boundingRect(contour)
    bounding_rect_area = w * h
    if bounding_rect_area == 0: return 0
    area = cv2.contourArea(contour)
    return area / bounding_rect_area

def get_solidity(contour: cv2.typing.MatLike) -> float:
    convex_hull_area = cv2.contourArea(cv2.convexHull(contour))
    if convex_hull_area == 0: return 0
    return cv2.contourArea(contour) / convex_hull_area

def get_circularity(contour: cv2.typing.MatLike) -> float:
    arc_length = cv2.arcLength(contour, True)
    if arc_length == 0: return 0
    return (4 * np.pi * cv2.contourArea(contour)) / (arc_length ** 2)\

def filter_contours(
    contours: Sequence[cv2.typing.MatLike],
    area_range: tuple[int, int] | None,
    width_height_ratio_range: tuple[float, float] | None
) -> list[cv2.typing.MatLike]:
    def filter_function(contour: cv2.typing.MatLike) -> bool:
        if area_range is not None:
            area = cv2.contourArea(contour)
            if area < area_range[0] or area > area_range[1]:
                return False
        if width_height_ratio_range is not None:
            ratio = get_width_height_ratio(contour)
            if ratio < width_height_ratio_range[0] or ratio > width_height_ratio_range[1]:
                return False
        return True
    contours = list(filter(filter_function, contours))
    return list(filter(filter_function, contours))