import cv2

class SharedCamera:
    def __init__(self):
        self.cap = None
        self.active_sessions = set()
        self.video_settings = {
            'width': 1280,
            'height': 720,
            'fps': 30,
            'quality': 85
        }

    def start_capture(self):
        try:
            if self.cap is None:
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    return False
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.video_settings['width'])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.video_settings['height'])
                self.cap.set(cv2.CAP_PROP_FPS, self.video_settings['fps'])
            return self.cap.isOpened()
        except Exception as e:
            print(f"Error starting capture: {e}")
            return False

    def stop_capture(self):
        if self.cap is not None and not self.active_sessions:
            self.cap.release()
            self.cap = None

    def add_session(self, session_id):
        self.active_sessions.add(session_id)
        if len(self.active_sessions) == 1:
            self.start_capture()

    def remove_session(self, session_id):
        if session_id in self.active_sessions:
            self.active_sessions.remove(session_id)
            if not self.active_sessions:
                self.stop_capture()