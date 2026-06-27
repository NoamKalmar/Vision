from typing import Sequence

import cv2
import numpy as np

def get_width_height_ratio(contour: cv2.typing.MatLike) -> float:
    _, _, w, h = cv2.boundingRect(contour)
    if h == 0: return 0
    return w / h

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
                False
        if width_height_ratio_range is not None:
            ratio = get_width_height_ratio(contour)
            if ratio < width_height_ratio_range[0] or ratio > width_height_ratio_range[1]:
                return False
        return True
    return list(filter(filter_function, contours))