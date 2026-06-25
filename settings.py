import cv2
import numpy as np
import platform
from letters import get_contours, filter_contours_by_area, filter_contours_by_ratio
from camera import Camera
from targets import get_circle, classify_hue
import math

ASSETS_PATH = "assets"
VIDEO_CAPTURE_API = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_V4L2

mouse_click_x, mouse_click_y = None, None
clicked = False

BINARY_THRESHOLD = 100
AREA_RANGE = (500, 15000)

GREEN = (0, 255, 0)
RED = (0, 0, 255)
BLUE = (255, 0, 0)

def mouse_click(event: int, x: int, y: int, flags: int, param: None) -> None:
    global mouse_click_x, mouse_click_y, clicked
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_click_x, mouse_click_y = x, y
        clicked = True

def was_mouse_clicked() -> bool:
    global clicked
    if clicked:
        clicked = False
        return True
    return False


def capture_template(cap_index: int, output_path: str) -> None:
    camera = Camera(cap_index)
    captured_frame: cv2.typing.MatLike | None = None
    print("Press 'c' to capture")
    while camera.cap.isOpened():
        camera.update_frame()
        if camera.error:
            print("error reading from camera")
            return
        frame_copy = camera.frame.copy()
        contours = get_contours(camera.frame, BINARY_THRESHOLD)
        contours = filter_contours_by_area(contours, AREA_RANGE)
        cv2.drawContours(frame_copy, contours, -1, GREEN, 3)
        cv2.imshow("Settings", frame_copy)
        key = cv2.waitKey(1)
        if key == ord("q"):
            break
        elif key == ord("c"):
            if len(contours) == 0:
                print("Invalid: Found 0 contours")
            elif len(contours) > 1:
                print("Invalid: More than one contour was found")
            else:
                np.save(output_path, contours[0])
                # cv2.imwrite(img_output_path, frame)
                break
    camera.close()
    cv2.destroyAllWindows()

def templates_menu() -> None:
    print("(1) phi")
    print("(2) psi")
    print("(3) omega")
    letter = input("Enter letter index: ")
    cap_index = int(input("Enter video capture index: "))
    path = f"{ASSETS_PATH}/"
    if letter == "1":
        path += "phi.npy"
    elif letter == "2":
        path += "psi.npy"
    elif letter == "3":
        path += "omega.npy"
    capture_template(cap_index, path)

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

def contours_calibration() -> None:
    cap_index = int(input("Enter video capture index: "))
    camera = Camera(cap_index)
    while camera.cap.isOpened():
        camera.update_frame()
        if camera.error:
            print("error reading from camera")
            return
        frame = camera.frame

        contours = list(get_contours(frame, BINARY_THRESHOLD))
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
        key = cv2.waitKey(1)
        if chosen_contour is not None:
            area = cv2.contourArea(chosen_contour)
            solidity = area / cv2.contourArea(cv2.convexHull(chosen_contour))
            _, _, w, h = cv2.boundingRect(chosen_contour)
            arc_length = cv2.arcLength(chosen_contour, True)
            circularity = 4 * np.pi * area / (arc_length ** 2)
            print(f"area: {area}, solidity: {solidity}, w-h-ratio: {w / h}, arc length: {arc_length}, circularity: {circularity}")
        if key == ord("q"):
            break

def circles_calibration() -> None:
    cap_index = int(input("Enter video capture index: "))
    camera = Camera(cap_index)
    while camera.cap.isOpened():
        camera.update_frame()
        if camera.error:
            print("error reading from camera")
            return
        frame = camera.frame
        circle = get_circle(frame)
        if circle is not None:
            (x, y), r = circle
            cv2.circle(frame, (int(x), int(y)), int(r), GREEN, 3)
        if was_mouse_clicked():
            hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            h, s, v = hsv_frame[mouse_click_y, mouse_click_x]
            print(h, s, v, classify_hue(h))
        cv2.imshow("Settings", frame)
        key = cv2.waitKey(1)
        if key == ord("q"):
            break
    camera.close()
    cv2.destroyAllWindows()

def main() -> None:
    cv2.namedWindow("Settings")
    cv2.setMouseCallback("Settings", mouse_click)
    print("Vision Settings")
    print("(1) letter templates")
    print("(2) contours")
    print("(3) circles")
    option = input("Enter option index: ")
    if option == "1":
        templates_menu()
    elif option == "2":
        contours_calibration()
    elif option == "3":
        circles_calibration()

if __name__ == "__main__":
    main()