from enum import Enum
from typing import Sequence
from dataclasses import dataclass
from collections import Counter

import cv2
import numpy as np

import contour_utils

MORPH_KERNEL2 = np.ones((2, 2), np.uint8)
MORPH_KERNEL1 = np.ones((5, 5), np.uint8)

class Letter(Enum):
    PHI = 0
    PSI = 1
    OMEGA = 2

@dataclass
class LettersConfig:
    templates: dict[int, cv2.typing.MatLike] # letter to template (contour). can get by using get_contour_template
    area_range: tuple[int, int] | None = None # for all letters
    width_to_height_range: tuple[float, float] | None = None # for all letters 
    min_matches: dict[Letter, float] | None = None # for each letter
    solidity_ranges: dict[Letter, tuple[float, float]] | None = None # for each letter
    circularity_ranges: dict[Letter, tuple[float, float]] | None = None # for each letter
    extent_ranges: dict[Letter, tuple[float, float]] | None = None # for each letter

def get_template_contours(template_paths: dict[Letter, str]) -> dict[Letter, cv2.typing.MatLike]:
    contours = {}
    for template_key, path in template_paths.items():
        contours[template_key] = np.load(path)
    return contours

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
        solidity_range: tuple[float, float] | None,
        circularity_range: tuple[float, float] | None,
        extent_range: tuple[float, float] | None
) -> bool:
    if match > min_valid:
        return False
    if solidity_range is not None:
        solidity = contour_utils.get_solidity(contour)
        if solidity < solidity_range[0] or solidity > solidity_range[1]:
            return False
    if circularity_range is not None:
        circularity = contour_utils.get_circularity(contour)
        if circularity < circularity_range[0] or circularity > circularity_range[1]:
            return False
    if extent_range is not None:
        extent = contour_utils.get_extent(contour)
        if extent < extent_range[0] or extent > extent_range[1]:
            return False
    return True

def get_letter(
        frame: cv2.typing.MatLike, 
        config: LettersConfig
) -> tuple[Letter, cv2.typing.MatLike] | tuple[None, None]:
    """Returns the correct letter and the contour that was identified to be that letter"""
    contours = contour_utils.get_contours(frame)
    contours = contour_utils.filter_contours(contours, config.area_range, config.width_to_height_range)
    matches, best_contours = check_for_templates(contours, config.templates)
    sorted_matches = sorted(matches.items(), key=lambda match: match[1])
    for letter, match in sorted_matches:
        if is_match_valid(
            match, 
            config.min_matches[letter], 
            best_contours[letter], 
            config.solidity_ranges[letter],
            config.circularity_ranges[letter],
            config.extent_ranges[letter]
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