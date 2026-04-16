import cv2
import serial

from serial_com import SerialCommunicator
from letters import Letter, LettersConfig, get_template_contours
from rings import Color
from robot import Robot

PHI_PATH = "assets/phi.png"
PSI_PATH = "assets/psi.png"
OMEGA_PATH = "assets/omega.png"
IMAGE_PATHS = {Letter.PHI: "assets/phi.png", 
               Letter.PSI: "assets/psi.png", 
               Letter.OMEGA: "assets/omega.png"}

MIN_MATCHES = {Letter.PHI: 0.2, Letter.PSI: 1.5, Letter.OMEGA: 1.5}
NORMAL_SOLIDITY_RANGES = {Letter.PHI: (0.9, 0.93), Letter.PSI: (0.375, 0.45), Letter.OMEGA: (0.35, 0.41)}

BINARY_THRESHOLD = 75

NUM_SCAN_FRAMES = 30

COLOR_RANGES = {
    Color.RED: ((0, 120, 70), (10, 255, 255)),
    Color.YELLOW: ((20, 100, 100), (30, 255, 255)),
    Color.GREEN: ((35, 80, 80), (85, 255, 255)),
    Color.BLUE: ((90, 80, 80), (130, 255, 255))
}

MORE_COLOR_RANGES = {Color.RED: ((170, 120, 70), (179, 255, 255))}

ROBOT_STOP_TIME = 1
TIME_BETWEEN_SCANS = 3

LEFT_CAP_INDEX = 0
RIGHT_CAP_INDEX = 2

PORT = "/dev/ttyUSB0"
BAUDRATE = 115200
NO_SERIAL = False

#!!!
# TO DO: add circularity validation for letters: (4 * pie * area) / (perimeter^2)
# TO DO: CHECK WHY COLORS RETURN A LOT OF NONES
#!!!

def main():
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
    if not NO_SERIAL:
        serial_com = SerialCommunicator(PORT, BAUDRATE)
    robot = Robot(
        name="Vision",
        serial_com=serial_com,
        cap_indexes=[LEFT_CAP_INDEX, RIGHT_CAP_INDEX],
        num_scan_frames=NUM_SCAN_FRAMES,
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