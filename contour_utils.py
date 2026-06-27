import cv2
import numpy as np

def get_solidity(contour: cv2.typing.MatLike) -> float:
    convex_hull_area = cv2.contourArea(cv2.convexHull(contour))
    if convex_hull_area == 0:
        return 0
    return cv2.contourArea(contour) / convex_hull_area

def get_circularity(contour: cv2.typing.MatLike) -> float:
    arc_length = cv2.arcLength(contour)
    if arc_length == 0:
        return 0
    return (4 * np.pi * cv2.contourArea(contour)) / (arc_length ** 2)