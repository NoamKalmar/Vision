import cv2
import numpy as np
from letters import get_template_contours, Letter, get_letter, LettersConfig
import contour_utils
from camera import Camera
from targets import get_circle, classify_hue, get_colors, get_layer_colors, get_colored_contours
from main import AREA_RANGE, EXTENT_RANGES, SOLIDITY_RANGES, CIRCULARITY_RANGES, MIN_MATCHES

ASSETS_PATH = "assets"

mouse_click_x, mouse_click_y = None, None
clicked = False

TEMPLATE_PATHS = {Letter.PHI: "assets/phi.npy", 
               Letter.PSI: "assets/psi.npy", 
               Letter.OMEGA: "assets/omega.npy"}

AREA_RANGE = (500, 15000)

GREEN = (0, 255, 0)
RED = (0, 0, 255)
BLUE = (255, 0, 0)

def mouse_click(event: int, x: int, y: int, flags: int, param: None) -> None:
    global mouse_click_x, mouse_click_y, clicked
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_click_x, mouse_click_y = x, y
        clicked = True
    elif event == cv2.EVENT_LBUTTONDBLCLK:
        mouse_click_x, mouse_click_y = None, None

def was_mouse_clicked() -> bool:
    global clicked
    if clicked:
        clicked = False
        return True
    return False

def ask_letter_get_path() -> str:
    print("(1) phi")
    print("(2) psi")
    print("(3) omega")
    letter = input("Enter letter index: ")
    path = f"{ASSETS_PATH}/"
    if letter == "1":
        path += "phi.npy"
    elif letter == "2":
        path += "psi.npy"
    elif letter == "3":
        path += "omega.npy"
    return path

def get_contour_center(contour: cv2.typing.MatLike) -> tuple[int, int] | None:
    moments = cv2.moments(contour)
    m00 = moments["m00"]
    m10 = moments["m10"]
    m01 = moments["m01"]
    if m00 == 0:
        return None
    x = int(m10 / m00)
    y = int(m01 / m00)
    return x, y

def contours_calibration(camera: Camera) -> None:
    templates = get_template_contours(TEMPLATE_PATHS)
    letters_config = LettersConfig(
        templates=templates,
        area_range=AREA_RANGE,
        min_matches=MIN_MATCHES,
        width_to_height_range=(0.65, 1.35),
        solidity_ranges=SOLIDITY_RANGES,
        circularity_ranges=CIRCULARITY_RANGES,
        extent_ranges=EXTENT_RANGES
    )
    letters_mode = False
    while camera.cap.isOpened():
        camera.update_frame()
        if camera.error:
            print("error reading from camera")
            return
        frame = camera.frame
        contours = list(contour_utils.get_contours(frame))
        # contours, mask = get_colored_contours(frame)
        contours = list(contours)
        chosen_contour = None
        if mouse_click_x is not None:
            cv2.circle(frame, (mouse_click_x, mouse_click_y), 5, BLUE, -1)
            min_distance_squared = None
            chosen_contour_index = None
            # Choosing the contour closest to the point selected
            for i, contour in enumerate(contours):
                center = get_contour_center(contour)
                if center is not None:
                    x, y = center
                    distance = (mouse_click_x - x) ** 2 + (mouse_click_y - y) ** 2
                    if min_distance_squared is None or distance < min_distance_squared:
                        min_distance_squared = distance
                        chosen_contour_index = i
            if min_distance_squared is not None:
                chosen_contour = contours.pop(chosen_contour_index)
                cv2.drawContours(frame, [chosen_contour], -1, GREEN, 3)

        cv2.drawContours(frame, contours, -1, RED, 3)

        cv2.imshow("Settings", frame)
        # cv2.imshow("mask", mask)
        key = cv2.waitKey(1)
        if chosen_contour is not None:
            area = cv2.contourArea(chosen_contour)
            solidity = contour_utils.get_solidity(chosen_contour)
            width_height_ratio = contour_utils.get_width_height_ratio(chosen_contour)
            extent = contour_utils.get_extent(chosen_contour) 
            circularity = contour_utils.get_circularity(chosen_contour)
            phi = cv2.matchShapes(chosen_contour, templates[Letter.PHI], 1, 0.0)
            psi = cv2.matchShapes(chosen_contour, templates[Letter.PSI], 1, 0.0)
            omega = cv2.matchShapes(chosen_contour, templates[Letter.OMEGA], 1, 0.0)
            print(f"area: {area:.2f}, w-h-ratio: {width_height_ratio:.2f}, solidity: {solidity:.2f}, circularity: {circularity:.2f}, extent: {extent:.2f}")
            print(f"phi: {phi:.2f}, psi: {psi:.2f}, omega: {omega:.2f}")
        if letters_mode:
            letter, contour = get_letter(frame, letters_config)
            print(letter)            
        if key == ord("q"):
            break
        if key == ord("c"):
            if chosen_contour is None:
                print("Please select a contour first")
            path = ask_letter_get_path()
            np.save(path, chosen_contour)
        if key == ord("l"):
            letters_mode = not letters_mode

def circles_calibration(camera: Camera) -> None:
    while camera.cap.isOpened():
        camera.update_frame()
        if camera.error:
            print("error reading from camera")
            return
        frame = camera.frame
        circle = get_circle(frame)
        if circle is not None:
            (x, y), r = circle
            cv2.circle(frame, (int(x), int(y)), int(r), GREEN, 2)
        if was_mouse_clicked():
            hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            h, s, v = hsv_frame[mouse_click_y, mouse_click_x]
            print(h, s, v, classify_hue(h))
        cv2.imshow("Settings", frame)
        key = cv2.waitKey(1)
        if key == ord("q"):
            break
        if key == ord("c"):
            colors = get_layer_colors(frame, circle)
            print(colors)
    cv2.destroyAllWindows()

def threshold_calibration(camera: Camera) -> None:
    threshold = 100
    while camera.cap.isOpened():
        camera.update_frame()
        if camera.error:
            print("Error: Can't read from camera")
            return
        gray = cv2.cvtColor(camera.frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
        cv2.imshow("Settings", thresh)
        key = cv2.waitKey(1)
        if key == ord("q"):
            return
        elif key == ord("-"):
            threshold -= 1
        elif key == ord("="):
            threshold += 1
        print(threshold)
    cv2.destroyAllWindows()

def main() -> None:
    print("Vision Settings")
    print("(1) contours")
    print("(2) circles")
    print("(3) threshold")
    option = input("Enter option index: ")
    cap_index = int(input("Enter video capture index: "))
    camera = Camera(cap_index)

    cv2.namedWindow("Settings")
    cv2.setMouseCallback("Settings", mouse_click)

    if option == "1":
        contours_calibration(camera)
    elif option == "2":
        circles_calibration(camera)
    elif option == "3":
        threshold_calibration(camera)
    camera.close()

if __name__ == "__main__":
    main()