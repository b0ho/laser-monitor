import os
from camera.camera import SharedCamera
from .session import UserSession
import time
import cv2
from datetime import datetime
from config import Config
from utils.logger import logger

class MonitoringState:
    """모니터링 상태 관리 클래스"""

    def __init__(self):
        """초기화"""
        try:
            self.sessions = {}
            self.camera = SharedCamera(video_source=Config.DEFAULT_VIDEO_SOURCE)
            self.is_monitoring = True
            self.alert_enabled = False
            self.email = None
            self.status = "대기중"
            self.distance = 0

            # HSV 값들을 설정에서 가져오기
            self.hsv_values = {
                'h_lower': 0, 'h_upper': 10,
                's_lower': 100, 's_upper': 255,
                'v_lower': 100, 'v_upper': 255,
                'tolerance': Config.TOLERANCE
            }

            self.video_source = Config.DEFAULT_VIDEO_SOURCE
            self.capture_interval = Config.CAPTURE_INTERVAL
            self.last_capture_time = 0
            self.captures = []
            self.capture_dir = Config.CAPTURE_DIR

            # 캡처 디렉토리 생성
            os.makedirs(self.capture_dir, exist_ok=True)

            self.error_message = None
            self.target_distance = Config.TARGET_DISTANCE

            logger.info("모니터링 상태 초기화 완료")

        except Exception as e:
            logger.log_exception("모니터링 상태 초기화 중 오류", e)
            raise

    def get_or_create_session(self, session_id):
        """세션 생성 또는 조회"""
        try:
            if session_id not in self.sessions:
                self.sessions[session_id] = UserSession(session_id)
                self.camera.add_session(session_id)
                logger.info(f"새 세션 생성: {session_id}")
            return self.sessions[session_id]
        except Exception as e:
            logger.log_exception(f"세션 생성/조회 중 오류 (ID: {session_id})", e)
            raise

    def cleanup_inactive_sessions(self, timeout=None):
        """비활성 세션 정리"""
        if timeout is None:
            timeout = Config.SESSION_TIMEOUT

        try:
            current_time = time.time()
            inactive_sessions = []

            for session_id, session in self.sessions.items():
                if current_time - session.last_active > timeout:
                    inactive_sessions.append(session_id)

            for session_id in inactive_sessions:
                self.camera.remove_session(session_id)
                del self.sessions[session_id]
                logger.info(f"비활성 세션 제거: {session_id}")

            if inactive_sessions:
                logger.info(f"{len(inactive_sessions)}개의 비활성 세션을 정리했습니다.")

        except Exception as e:
            logger.log_exception("세션 정리 중 오류", e)

    def add_capture(self, frame, is_manual=False):
        """캡처 추가"""
        try:
            current_time = time.time()
            if is_manual or current_time - self.last_capture_time >= self.capture_interval:

                if frame is None or frame.size == 0:
                    logger.warning("유효하지 않은 프레임, 캡처 건너뜀")
                    return

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                prefix = 'manual' if is_manual else 'auto'
                filename = f'{prefix}_capture_{timestamp}.jpg'
                filepath = os.path.join(self.capture_dir, filename)

                logger.debug(f"캡처 저장 시도: {filepath}")

                # 이미지 저장
                success = cv2.imwrite(filepath, frame)
                if not success:
                    logger.error(f"이미지 저장 실패: {filepath}")
                    return

                capture_info = {
                    'image_url': f'/static/captures/{filename}',
                    'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': self.status,
                    'distance': self.distance,
                    'is_manual': is_manual
                }

                logger.info(f"캡처 성공: {filename} ({'수동' if is_manual else '자동'})")

                # 최근 캡처만 유지
                self.captures = [capture_info] + self.captures[:Config.MAX_CAPTURES-1]

                if not is_manual:
                    self.last_capture_time = current_time

                # 오래된 파일 정리
                self._cleanup_old_captures()

        except Exception as e:
            logger.log_exception("캡처 추가 중 오류", e)

    def _cleanup_old_captures(self):
        """오래된 캡처 파일 정리"""
        try:
            if not os.path.exists(self.capture_dir):
                return

            files = []
            for f in os.listdir(self.capture_dir):
                filepath = os.path.join(self.capture_dir, f)
                if os.path.isfile(filepath) and f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    files.append((filepath, os.path.getmtime(filepath)))

            # 수정 시간 기준 정렬 (최신순)
            files.sort(key=lambda x: x[1], reverse=True)

            # 최대 파일 수 초과 시 오래된 파일 삭제
            deleted_count = 0
            for filepath, _ in files[Config.MAX_FILES:]:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                except OSError as e:
                    logger.warning(f"파일 삭제 실패: {filepath} - {e}")

            if deleted_count > 0:
                logger.info(f"{deleted_count}개의 오래된 캡처 파일을 삭제했습니다.")

        except Exception as e:
            logger.log_exception("오래된 캡처 파일 정리 중 오류", e)

    def start_capture(self):
        """캡처 시작"""
        try:
            if not self.camera.cap or not self.camera.cap.isOpened():
                logger.warning("카메라를 열 수 없습니다.")
                return False
            return True
        except Exception as e:
            logger.log_exception("캡처 시작 중 오류", e)
            return False

    def get_status_summary(self):
        """상태 요약 정보 반환"""
        try:
            return {
                'status': self.status,
                'distance': self.distance,
                'is_monitoring': self.is_monitoring,
                'alert_enabled': self.alert_enabled,
                'active_sessions': len(self.sessions),
                'total_captures': len(self.captures),
                'camera_connected': self.camera.cap is not None and self.camera.cap.isOpened() if self.camera.cap else False
            }
        except Exception as e:
            logger.log_exception("상태 요약 정보 조회 중 오류", e)
            return {
                'status': '오류',
                'distance': 0,
                'is_monitoring': False,
                'alert_enabled': False,
                'active_sessions': 0,
                'total_captures': 0,
                'camera_connected': False
            }