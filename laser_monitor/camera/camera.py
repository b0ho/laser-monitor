import cv2
from config import Config
from utils.logger import logger

class SharedCamera:
    """공유 카메라 클래스"""

    def __init__(self, video_source=None):
        """
        초기화

        Args:
            video_source (int): 비디오 소스 번호 (기본값: Config에서 가져옴)
        """
        try:
            self.video_source = video_source if video_source is not None else Config.DEFAULT_VIDEO_SOURCE
            self.cap = None
            self.active_sessions = set()

            # 비디오 설정을 Config에서 가져오기
            self.video_settings = {
                'width': Config.CAMERA_WIDTH,
                'height': Config.CAMERA_HEIGHT,
                'fps': Config.CAMERA_FPS,
                'quality': Config.VIDEO_QUALITY
            }

            logger.info(f"카메라 객체 초기화 완료 - 소스: {self.video_source}")

        except Exception as e:
            logger.log_exception("카메라 객체 초기화 중 오류", e)
            raise

    def start_capture(self):
        """카메라 캡처 시작"""
        try:
            if self.cap is None:
                logger.info(f"카메라 초기화 시도: source={self.video_source}")

                # 기본 카메라 소스로 시도
                self.cap = cv2.VideoCapture(self.video_source)

                if not self.cap.isOpened():
                    logger.warning(f"카메라 소스 {self.video_source} 연결 실패, 다른 소스 시도")

                    # 다른 카메라 소스들 시도 (0부터 3까지)
                    for i in range(4):
                        if i == self.video_source:
                            continue  # 이미 시도한 소스는 건너뛰기

                        logger.info(f"카메라 소스 {i} 시도")
                        if self.cap:
                            self.cap.release()

                        self.cap = cv2.VideoCapture(i)
                        if self.cap.isOpened():
                            self.video_source = i
                            logger.info(f"카메라 소스 {i} 연결 성공")
                            break
                    else:
                        logger.error("모든 카메라 소스 연결 실패")
                        return False

                # 카메라 설정 적용
                self._apply_camera_settings()

                # 연결 테스트
                if not self._test_camera_connection():
                    logger.error("카메라 연결 테스트 실패")
                    return False

                logger.info("카메라 초기화 성공")
                return True

            return self.cap.isOpened()

        except Exception as e:
            logger.log_exception("카메라 캡처 시작 중 오류", e)
            return False

    def _apply_camera_settings(self):
        """카메라 설정 적용"""
        try:
            if not self.cap:
                return False

            # 해상도 설정
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.video_settings['width'])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.video_settings['height'])
            self.cap.set(cv2.CAP_PROP_FPS, self.video_settings['fps'])

            # 버퍼 크기 설정 (최신 프레임 보장)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 실제 적용된 설정값 확인
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

            logger.info(f"카메라 설정 적용 - 해상도: {actual_width}x{actual_height}, FPS: {actual_fps}")

            # 설정값과 실제값이 다른 경우 경고
            if (actual_width != self.video_settings['width'] or
                actual_height != self.video_settings['height']):
                logger.warning(f"요청한 해상도({self.video_settings['width']}x{self.video_settings['height']})와 "
                             f"실제 해상도({actual_width}x{actual_height})가 다릅니다.")

            return True

        except Exception as e:
            logger.log_exception("카메라 설정 적용 중 오류", e)
            return False

    def _test_camera_connection(self):
        """카메라 연결 테스트"""
        try:
            if not self.cap or not self.cap.isOpened():
                return False

            # 테스트 프레임 읽기
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                logger.error("카메라에서 유효한 프레임을 읽을 수 없습니다.")
                return False

            logger.debug(f"테스트 프레임 크기: {frame.shape}")
            return True

        except Exception as e:
            logger.log_exception("카메라 연결 테스트 중 오류", e)
            return False

    def stop_capture(self):
        """카메라 캡처 중지"""
        try:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
                logger.info("카메라 연결 해제")
        except Exception as e:
            logger.log_exception("카메라 캡처 중지 중 오류", e)

    def add_session(self, session_id):
        """세션 추가"""
        try:
            self.active_sessions.add(session_id)
            logger.debug(f"세션 추가: {session_id}, 총 활성 세션: {len(self.active_sessions)}")

            # 첫 번째 세션인 경우 카메라 시작
            if len(self.active_sessions) == 1:
                if not self.start_capture():
                    logger.error("카메라 시작 실패")
                    return False
            return True

        except Exception as e:
            logger.log_exception(f"세션 추가 중 오류 (ID: {session_id})", e)
            return False

    def remove_session(self, session_id):
        """세션 제거"""
        try:
            if session_id in self.active_sessions:
                self.active_sessions.remove(session_id)
                logger.debug(f"세션 제거: {session_id}, 남은 활성 세션: {len(self.active_sessions)}")

                # 마지막 세션인 경우 카메라 중지
                if not self.active_sessions:
                    self.stop_capture()
                    logger.info("모든 세션이 종료되어 카메라를 중지합니다.")

        except Exception as e:
            logger.log_exception(f"세션 제거 중 오류 (ID: {session_id})", e)

    def is_active(self):
        """카메라 활성 상태 확인"""
        try:
            return (self.cap is not None and
                    self.cap.isOpened() and
                    len(self.active_sessions) > 0)
        except Exception as e:
            logger.log_exception("카메라 활성 상태 확인 중 오류", e)
            return False

    def get_frame(self):
        """프레임 읽기"""
        try:
            if not self.is_active():
                return False, None

            ret, frame = self.cap.read()
            if not ret or frame is None:
                logger.warning("프레임 읽기 실패")
                return False, None

            return True, frame

        except Exception as e:
            logger.log_exception("프레임 읽기 중 오류", e)
            return False, None

    def update_settings(self, new_settings):
        """비디오 설정 업데이트"""
        try:
            old_settings = self.video_settings.copy()
            self.video_settings.update(new_settings)

            # 카메라가 활성 상태인 경우 설정 적용
            if self.is_active():
                if not self._apply_camera_settings():
                    # 설정 적용 실패 시 이전 설정으로 복구
                    self.video_settings = old_settings
                    logger.warning("설정 업데이트 실패, 이전 설정으로 복구")
                    return False

            logger.info(f"비디오 설정 업데이트: {new_settings}")
            return True

        except Exception as e:
            logger.log_exception("비디오 설정 업데이트 중 오류", e)
            return False

    def get_camera_info(self):
        """카메라 정보 조회"""
        try:
            if not self.cap:
                return None

            return {
                'source': self.video_source,
                'width': self.cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                'height': self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                'fps': self.cap.get(cv2.CAP_PROP_FPS),
                'is_opened': self.cap.isOpened(),
                'active_sessions': len(self.active_sessions),
                'settings': self.video_settings.copy()
            }

        except Exception as e:
            logger.log_exception("카메라 정보 조회 중 오류", e)
            return None