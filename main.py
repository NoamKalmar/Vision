import argparse

import cv2
import serial

from serial_com import SerialCommunicator
from camera import Camera
from letters import Letter, LettersConfig, get_template_contours
from rings import Color
from robot import Robot

PHI_PATH = "assets/phi.png"
PSI_PATH = "assets/psi.png"
OMEGA_PATH = "assets/omega.png"
IMAGE_PATHS = {Letter.PHI: "assets/phi.png", 
               Letter.PSI: "assets/psi.png", 
               Letter.OMEGA: "assets/omega.png"}

MIN_MATCHES = {Letter.PHI: 0.2, Letter.PSI: 1.5, Letter.OMEGA: 2.3}
NORMAL_SOLIDITY_RANGES = {Letter.PHI: (0.89, 0.94), Letter.PSI: (0.36, 0.45), Letter.OMEGA: (0.32, 0.41)}

BINARY_THRESHOLD = 100

NUM_SCAN_FRAMES = 1

COLOR_RANGES = {
    Color.RED: ((0, 120, 70), (10, 255, 255)),
    Color.YELLOW: ((20, 100, 100), (35, 255, 255)),
    Color.GREEN: ((35, 80, 80), (85, 255, 255)),
    Color.BLUE: ((90, 80, 80), (130, 255, 255))
}

MORE_COLOR_RANGES = {Color.RED: ((170, 120, 70), (179, 255, 255))}

ROBOT_STOP_TIME = 5
TIME_BETWEEN_SCANS = 0

RIGHT_CAP_INDEX = 0
LEFT_CAP_INDEX = 2
RIGHT_FLIP = True
LEFT_FLIP = False

PORT = "/dev/ttyUSB0"
BAUDRATE = 115200

#!!!
# TO DO: add circularity validation for letters: (4 * pie * area) / (perimeter^2)
# TO DO: CHECK WHY COLORS RETURN A LOT OF NONES
#!!!

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--noserial",
        action="store_true",
        help="run without connecting a serial device to communicate with"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="""activates debug mode which has effects:
        1. display the debug window, containg different information, mostly cameras input
        2. crash if the program encounters an error in a loop cycle
        """
    )
    parser.add_argument(
        "--left",
        default=f"{LEFT_CAP_INDEX}",
        help="The video capture index for the left camera (-1 to not use it)"
    )
    parser.add_argument(
        "--right",
        default=f"{RIGHT_CAP_INDEX}",
        help="The video capture index for the right camera (-1 to not ues it)"
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    templates = get_template_contours(IMAGE_PATHS, BINARY_THRESHOLD)
    letters_config = LettersConfig(
        templates=templates,
        binary_threshold=BINARY_THRESHOLD,
        min_area=50,
        min_matches=MIN_MATCHES,
        normal_width_to_height_range=(0.5, 1.5),
        normal_solidity_range_for_letter=NORMAL_SOLIDITY_RANGES
    )
    serial_com = None
    if not args.noserial:
        serial_com = SerialCommunicator(PORT, BAUDRATE)
    left_camera = None
    if int(args.left) >= 0:
        left_camera = Camera(
            int(args.left),
            NUM_SCAN_FRAMES,
            LEFT_FLIP
        )
    right_camera = None
    if int(args.right) >= 0:
        right_camera = Camera(
            int(args.right),
            NUM_SCAN_FRAMES,
            RIGHT_FLIP
        )
    
    robot = Robot(
        name="Vision",
        debug_mode=args.debug,
        serial_com=serial_com,
        left_camera=left_camera,
        right_camera=right_camera,
        time_to_stop=ROBOT_STOP_TIME,
        time_between_scans=TIME_BETWEEN_SCANS,
        letters_config=letters_config,
        color_ranges=COLOR_RANGES,
        more_color_ranges=MORE_COLOR_RANGES
    )
    
    robot.loop()

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()