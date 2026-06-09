import cv2
import platform
from letters import get_contours

ASSETS_PATH = "assets"
VIDEO_CAPTURE_API = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_V4L2

BINARY_THRESHOLD = 100

GREEN = (0, 255, 0)

def capture_template(cap_index: int, img_output_path: str) -> None:
    cap = cv2.VideoCapture(cap_index, VIDEO_CAPTURE_API)
    captured_frame: cv2.typing.MatLike | None = None
    print("Press 'c' to capture")
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            print("error reading from camera")
            return
        contours = get_contours(frame, BINARY_THRESHOLD)
        cv2.drawContours(frame, contours, -1, GREEN, 3)
        cv2.imshow("Vision Template Calibration", frame)
        key = cv2.waitKey(1)
        if key == ord("q"):
            break
        elif key == ord("c"):
            if len(contours) == 0:
                print("Invalid: Found 0 contours")
            elif len(contours) > 1:
                print("Invalid: More than one contour was found")
            else:
                cv2.imwrite(img_output_path, frame)
                break
    cap.release()
    cv2.destroyAllWindows()

def templates_menu() -> None:
    print("(1) phi")
    print("(2) psi")
    print("(3) omega")
    letter = input("Enter letter index: ")
    cap_index = int(input("Enter video capture index: "))
    path = f"{ASSETS_PATH}/"
    if letter == "1":
        path += "phi.png"
    elif letter == "2":
        path += "psi.png"
    elif letter == "3":
        path += "omega.png"
    capture_template(cap_index, path)

def main() -> None:
    print("Vision Settings")
    print("(1) letter templates")
    option = input("Enter option index: ")
    if option == "1":
        templates_menu() 

if __name__ == "__main__":
    main()