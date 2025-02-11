import os
from ..camera.camera import SharedCamera
from .session import UserSession
import time
import cv2
from datetime import datetime

class MonitoringState:
    def __init__(self):
        self.sessions = {}
        self.camera = SharedCamera()
        self.is_monitoring = False
        self.alert_enabled = False
        self.email = None  # 알림 수신 이메일
        self.status = "대기중"
        self.distance = 0
        self.hsv_values = {
            'h_lower': 0, 'h_upper': 10,
            's_lower': 100, 's_upper': 255,
            'v_lower': 100, 'v_upper': 255,
            'tolerance': 50
        }
        self.video_source = 0
        self.capture_interval = 60
        self.last_capture_time = 0
        self.captures = []
        self.capture_dir = 'laser_monitor/static/captures'
        os.makedirs(self.capture_dir, exist_ok=True)
        self.error_message = None

    def get_or_create_session(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = UserSession(session_id)
            self.camera.add_session(session_id)
        return self.sessions[session_id]

    def cleanup_inactive_sessions(self, timeout=60):
        current_time = time.time()
        for session_id, session in list(self.sessions.items()):
            if current_time - session.last_active > timeout:
                self.camera.remove_session(session_id)
                del self.sessions[session_id]

    def add_capture(self, frame, is_manual=False):
        current_time = time.time()
        if is_manual or current_time - self.last_capture_time >= self.capture_interval:
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                prefix = 'manual' if is_manual else 'auto'
                filename = f'{prefix}_capture_{timestamp}.jpg'
                filepath = os.path.join(self.capture_dir, filename)

                print(f"Saving capture to: {filepath}")

                success = cv2.imwrite(filepath, frame)
                if not success:
                    print(f"Failed to save image to {filepath}")
                    return

                capture_info = {
                    'image_url': f'/static/captures/{filename}',
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': self.status,
                    'is_manual': is_manual
                }

                print(f"Capture info: {capture_info}")

                # 최근 10개만 유지
                self.captures = [capture_info] + self.captures[:9]
                if not is_manual:
                    self.last_capture_time = current_time

                self._cleanup_old_captures()

            except Exception as e:
                print(f"Error during capture: {e}")

    def _cleanup_old_captures(self):
        # 최근 20개 파일만 유지
        files = sorted(os.listdir(self.capture_dir), reverse=True)
        for old_file in files[20:]:
            os.remove(os.path.join(self.capture_dir, old_file))