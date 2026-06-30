import cv2
import numpy as np

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

kernel = np.ones((5, 5), np.uint8)

# -----------------------------
# HSV COLOR RANGES
# -----------------------------
color_ranges = {
    "Red": [
        (np.array([0, 120, 70]), np.array([10, 255, 255])),
        (np.array([170, 120, 70]), np.array([180, 255, 255]))
    ],
    "Green": [
        (np.array([35, 40, 40]), np.array([95, 255, 255]))
    ],
    "Blue": [
        (np.array([100, 120, 50]), np.array([140, 255, 255]))
    ],
    "Yellow": [
        (np.array([15, 120, 100]), np.array([35, 255, 255]))
    ],
    "Black": [
        (np.array([0, 0, 0]), np.array([180, 255, 60]))
    ]
}


def detect_color(hsv_pixel):
    for name, ranges in color_ranges.items():
        for lower, upper in ranges:
            if np.all(hsv_pixel >= lower) and np.all(hsv_pixel <= upper):
                return name
    return "Unknown"


while True:

    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # -----------------------------
    # BUILD COLOR MASK
    # -----------------------------
    mask = np.zeros((h, w), dtype=np.uint8)

    for ranges in color_ranges.values():
        m = np.zeros((h, w), dtype=np.uint8)
        for lower, upper in ranges:
            m |= cv2.inRange(hsv, lower, upper)
        mask |= m

    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # -----------------------------
    # FIND OUTER CIRCLE
    # -----------------------------
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_score = 0

    for c in contours:
        area = cv2.contourArea(c)
        if area < 3000:
            continue

        peri = cv2.arcLength(c, True)
        if peri == 0:
            continue

        circularity = 4 * np.pi * area / (peri * peri)

        if circularity > best_score:
            best_score = circularity
            best = c

    output = frame.copy()

    if best is not None and best_score > 0.7:

        cv2.drawContours(output, [best], -1, (0, 255, 255), 3)

        (x, y), R = cv2.minEnclosingCircle(best)
        cx, cy = int(x), int(y)
        R = int(R)

        cv2.circle(output, (cx, cy), 4, (0, 0, 255), -1)

        ring_results = []

        # precompute coordinate grid
        yy, xx = np.indices((h, w))
        dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)

        for i in range(5):

            r_outer = R * (1 - i / 5.0)
            r_inner = R * (1 - (i + 1) / 5.0)

            # FULL ring mask (ALL pixels)
            ring_mask = (dist <= r_outer) & (dist > r_inner)

            if np.any(ring_mask):

                hsv_pixels = hsv[ring_mask]

                mean_hsv = np.mean(hsv_pixels, axis=0).astype(int)
                print(i, mean_hsv)
                label = detect_color(mean_hsv)

                ring_results.append(label)

            else:
                ring_results.append("Unknown")

        # print("\nOutside → Inside:", ring_results)

        cv2.putText(output,
                    " | ".join(ring_results),
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2)

    cv2.imshow("Rings", output)
    cv2.imshow("Mask", mask)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()