import cv2

TITLE = "MQTT Face Tracking"


class Preview:
    """The preview window. Keys: f = fullscreen on/off, m = small/normal size, q = quit.

    The image keeps its aspect ratio at any window size (no stretching; bars fill the rest).
    Minimizing is done with the window manager's own button; the tracking loop does not depend on the window.
    """

    def __init__(self, fullscreen: bool = False):
        cv2.namedWindow(TITLE, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        self.fullscreen = False
        self.size = None  # frame size, known after the first frame
        self.small = False
        if fullscreen:
            self._toggle_fullscreen()

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        cv2.setWindowProperty(TITLE, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN if self.fullscreen else cv2.WINDOW_NORMAL)

    def _resize(self):
        width, height = self.size
        cv2.resizeWindow(TITLE, *((width // 3, height // 3) if self.small else (width, height)))

    def show(self, frame) -> bool:
        """Draw the frame and handle keys. Returns False when the user asks to quit."""
        if self.size is None:
            self.size = (frame.shape[1], frame.shape[0])
            if not self.fullscreen:
                self._resize()
        cv2.imshow(TITLE, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("f"):
            self._toggle_fullscreen()
        elif key == ord("m"):
            self.small = not self.small
            if self.fullscreen:
                self._toggle_fullscreen()
            self._resize()
        return key != ord("q")

    def close(self):
        cv2.destroyAllWindows()
