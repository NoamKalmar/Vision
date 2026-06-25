import argparse

import cv2

from serial_com import SerialCommunicator
from camera import Camera
from letters import Letter, LettersConfig, get_template_contours
from targets import Color
from robot import Robot

TEMPLATE_PATHS = {Letter.PHI: "assets/phi.npy", 
               Letter.PSI: "assets/psi.npy", 
               Letter.OMEGA: "assets/omega.npy"}

MIN_MATCHES = {Letter.PHI: 0.2, Letter.PSI: 1.5, Letter.OMEGA: 3.0}
NORMAL_SOLIDITY_RANGES = {Letter.PHI: (0.90, 0.94), Letter.PSI: (0.42, 0.48), Letter.OMEGA: (0.38, 0.42)}

BINARY_THRESHOLD = 100

NUM_SCAN_FRAMES = 10

CONTINUE_WAITING_TIMEOUT = 25

AREA_RANGE = (1000, 15000)

RIGHT_CAP_INDEX = 0
LEFT_CAP_INDEX = 2
RIGHT_FLIP = False
LEFT_FLIP = False

DEFAULT_PORTS = ["/dev/ttyUSB0", "/dev/ttyUSB1"]
BAUDRATE = 115200

#!!!
# TO DO: add circularity validation for letters: (4 * pie * area) / (perimeter^2)
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
    templates = get_template_contours(TEMPLATE_PATHS)
    letters_config = LettersConfig(
        templates=templates,
        binary_threshold=BINARY_THRESHOLD,
        area_range=AREA_RANGE,
        min_matches=MIN_MATCHES,
        normal_width_to_height_range=(0.5, 1.5),
        normal_solidity_range_for_letter=NORMAL_SOLIDITY_RANGES
    )
    serial_com = None
    if not args.noserial:
        serial_com = SerialCommunicator(DEFAULT_PORTS, BAUDRATE)
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
        continue_waiting_timeout=CONTINUE_WAITING_TIMEOUT,
        letters_config=letters_config
    )
    
    robot.loop()

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()