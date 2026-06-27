import cv2
import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import Sequence
from collections import Counter

MORPH_KERNEL2 = np.ones((2, 2), np.uint8)
MORPH_KERNEL1 = np.ones((5, 5), np.uint8)


@dataclass
class LettersConfig:
    templates: dict[int, cv2.typing.MatLike] # letter to template (contour). can get by using get_contour_template
    binary_threshold: int = 75 # max value for a pixel to be considered as black (0 is black, 255 is white)
    area_range: tuple[int, int] | None = None # for all letters
    min_matches: dict[int, float] | None = None # letter to min match for that letter
    normal_width_to_height_range: tuple[float, float] | None = None # for all letters 
    normal_solidity_range_for_letter: dict[int, tuple[float, float]] | None = None # for each letter

class Letter(Enum):
    PHI = 0
    PSI = 1
    OMEGA = 2

def get_contours(image: cv2.typing.MatLike, binary_threshold: int) -> Sequence[cv2.typing.MatLike]:
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(grayscale, binary_threshold, 255, cv2.THRESH_BINARY_INV)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, MORPH_KERNEL1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, MORPH_KERNEL2)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours

def get_template_contours(template_paths: dict[int, set]) -> dict[int, Sequence[cv2.typing.MatLike]]:
    contours = {}
    for template_key, path in template_paths.items():
        contours[template_key] = np.load(path)
    return contours

def filter_contours_by_ratio(contours: Sequence[cv2.typing.MatLike], valid_range: tuple[float, float]) -> Sequence[cv2.typing.MatLike]:
    filtered_contours = []
    for contour in contours:
        _, _, w, h = cv2.boundingRect(contour)
        ratio = w / h
        if ratio > valid_range[0] and ratio < valid_range[1]:
            filtered_contours.append(contour)
    return filtered_contours

def filter_contours_by_area(contours: Sequence[cv2.typing.MatLike], area_range: tuple[int, int]) -> Sequence[cv2.typing.MatLike]:
    filtered_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area >= area_range[0] and area <= area_range[1]:
            filtered_contours.append(contour)
    return filtered_contours

def check_for_templates(
        contours: Sequence[cv2.typing.MatLike], 
        templates: dict[Letter, cv2.typing.MatLike]
) -> tuple[dict[Letter, float], dict[Letter, cv2.typing.MatLike]]:
    # Returns the best match for each template, and the correlating contour for that match
    min_match_for_template = {template_key: 100 for template_key in templates.keys()}
    best_contour_for_template = {template_key: None for template_key in templates.keys()}
    for contour in contours:
        for template_key, template in templates.items():
            template_match = cv2.matchShapes(contour, template, 1, 0.0)
            min_match_for_template[template_key] = min(min_match_for_template[template_key], template_match)
            if template_match == min_match_for_template[template_key]:
                best_contour_for_template[template_key] = contour
    return min_match_for_template, best_contour_for_template

def is_match_valid(
        match: float, 
        min_valid: float, 
        contour: cv2.typing.MatLike | None, 
        solidity_range: tuple[float, float] | None
) -> bool:
    if match > min_valid:
        return False
    solidity = cv2.contourArea(contour) / cv2.contourArea(cv2.convexHull(contour))
    if solidity_range is not None:
        if solidity < solidity_range[0] or solidity > solidity_range[1]:
            return False
    return True

def get_letter(
        frame: cv2.typing.MatLike, 
        config: LettersConfig
) -> tuple[Letter, cv2.typing.MatLike] | tuple[None, None]:
    """Returns the correct letter and the contour that was identified to be that letter"""
    contours = get_contours(frame, config.binary_threshold)
    if config.normal_width_to_height_range is not None:
        contours = filter_contours_by_ratio(contours, config.normal_width_to_height_range)
    if config.area_range is not None:
        contours = filter_contours_by_area(contours, config.area_range)
    matches, best_contours = check_for_templates(contours, config.templates)
    # print(matches)
    sorted_matches = sorted(matches.items(), key=lambda match: match[1])
    for letter, match in sorted_matches:
        if is_match_valid(
            match, 
            config.min_matches[letter], 
            best_contours[letter], 
            config.normal_solidity_range_for_letter[letter]
        ):
            return letter, best_contours[letter]
    return None, None

def frames_get_letter(frames: list[cv2.typing.MatLike], config: LettersConfig) -> int | None:
    letters_counter = Counter()
    letter_contours: dict[Letter, cv2.typing.MatLike] = {}
    for frame in frames:
        letter, chosen_contour = get_letter(frame, config)
        letters_counter[letter] += 1
        letter_contours[letter] = chosen_contour
    chosen_letter = letters_counter.most_common(1)[0][0]
    return chosen_letter, letter_contours[chosen_letter]