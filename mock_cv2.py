# Mock implementations for cv2 functions

class VideoCapture:
    """Mock implementation of cv2.VideoCapture"""

    def __init__(self, device_index):
        print(f"MOCK: Initializing VideoCapture with device {device_index}")
        self.is_opened = True

    def read(self):
        """Mock implementation of cv2.VideoCapture.read"""
        print("MOCK: Reading frame")
        # Return a dummy frame (black image) and success status
        import numpy as np
        return True, np.zeros((480, 640, 3), dtype=np.uint8)

    def release(self):
        """Mock implementation of cv2.VideoCapture.release"""
        print("MOCK: Releasing VideoCapture")


def imshow(window_name, image):
    """Mock implementation of cv2.imshow"""
    print(f"MOCK: Showing image in window {window_name}")


def waitKey(delay):
    """Mock implementation of cv2.waitKey"""
    print(f"MOCK: Waiting for key with delay {delay}")
    # Return -1 (no key pressed) or a key code (for 'q' we return 113)
    return -1


def destroyAllWindows():
    """Mock implementation of cv2.destroyAllWindows"""
    print("MOCK: Destroying all windows")


def cvtColor(image, color_code):
    """Mock implementation of cv2.cvtColor"""
    print("MOCK: Converting image color")
    return image


# Mock constants
COLOR_BGR2RGB = 0