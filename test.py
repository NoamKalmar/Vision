import cv2
import numpy as np
from collections import Counter

NUM_LAYERS = 5
MIN_VALID_FRAMES = 5  # adjust this based on FPS/window size


def classify_color(bgr):
    hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = hsv

    if v < 50 or s < 50:
        return "Black"

    if h < 10 or h > 170:
        return "Red"

    if 15 <= h < 35:
        return "Yellow"

    if 35 <= h < 85:
        return "Green"

    if 85 <= h < 140:
        return "Blue"

    return "Green"


def detect_ellipse(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)

    if len(c) < 5:
        return None

    return cv2.fitEllipse(c)


def sample_layer_colors(frame, ellipse):
    (cx, cy), (major, minor), angle = ellipse

    a = major / 2.0
    theta = np.deg2rad(angle)

    direction = np.array([np.cos(theta), np.sin(theta)])

    scales = np.linspace(0.0, 0.95, NUM_LAYERS)

    colors = []

    for s in scales:
        x = int(cx + direction[0] * a * s)
        y = int(cy + direction[1] * a * s)

        x = np.clip(x, 0, frame.shape[1] - 1)
        y = np.clip(y, 0, frame.shape[0] - 1)

        patch = frame[max(0, y-2):y+3, max(0, x-2):x+3]
        color = np.median(patch.reshape(-1, 3), axis=0)

        colors.append(classify_color(color))

    return colors


def frames_get_colors(last_frames: list):
    layer_votes = [Counter() for _ in range(NUM_LAYERS)]
    valid_frames = 0

    for frame in last_frames:
        ellipse = detect_ellipse(frame)

        if ellipse is None:
            continue

        valid_frames += 1

        colors = sample_layer_colors(frame, ellipse)

        for i, c in enumerate(colors):
            layer_votes[i][c] += 1

    if valid_frames < MIN_VALID_FRAMES:
        return None

    result = []

    for i in range(NUM_LAYERS):
        if layer_votes[i]:
            result.append(layer_votes[i].most_common(1)[0][0])
        else:
            result.append("Unknown")

    return result