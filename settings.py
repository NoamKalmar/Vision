import cv2
import numpy as np
import platform
from letters import get_contours, filter_contours_by_area, filter_contours_by_ratio
from camera import Camera

ASSETS_PATH = "assets"
VIDEO_CAPTURE_API = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_V4L2

BINARY_THRESHOLD = 100
AREA_RANGE = (500, 10000)

GREEN = (0, 255, 0)

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
        cv2.imshow("Vision Template Calibration", frame_copy)
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

def conours_stats_calibration() -> None:
    cap_index = int(input("Enter video capture index: "))
    camera = Camera(cap_index)
    while camera.cap.isOpened():
        camera.update_frame()
        if camera.error:
            print("error reading from camera")
            return
        frame_copy = camera.frame.copy()
        contours = get_contours(camera.frame, BINARY_THRESHOLD)
        contours = filter_contours_by_ratio(contours, (0.75, 1.25))
        contours = filter_contours_by_area(contours, AREA_RANGE)
        cv2.drawContours(frame_copy, contours, -1, GREEN, 3)
        cv2.imshow("Vision Area Calibration", frame_copy)
        key = cv2.waitKey(1)
        if key == ord("q"):
            break
        if key == ord("c"):
            if len(contours) == 0:
                print("Invalid: Found 0 contours")
            elif len(contours) > 1:
                print("Invalid: More than one contour was found")
            else:
                contour = contours[0]
                area = cv2.contourArea(contour)
                solidity = area / cv2.contourArea(cv2.convexHull(contour))
                _, _, w, h = cv2.boundingRect(contour)
                arc_length = cv2.arcLength(contour, True)
                print(f"area: {area}, solidity: {solidity}, w-h-ratio: {w / h}, arc length: {arc_length}")

def main() -> None:
    print("Vision Settings")
    print("(1) letter templates")
    print("(2) contours stats calibration")
    option = input("Enter option index: ")
    if option == "1":
        templates_menu()
    elif option == "2":
        conours_stats_calibration()

if __name__ == "__main__":
    main()