import cv2

class SharedCamera:
    def __init__(self, video_source=0):
        self.video_source = video_source
        self.cap = None
        self.active_sessions = set()
        self.video_settings = {
            'width': 640,  # 해상도를 낮춰서 시도
            'height': 480,
            'fps': 30,
            'quality': 85
        }

    def start_capture(self):
        try:
            if self.cap is None:
                print(f"카메라 초기화 시도: source={self.video_source}")

                # macOS에서 카메라 초기화 시 추가 옵션 설정
                self.cap = cv2.VideoCapture(self.video_source)
                if not self.cap.isOpened():
                    # 다른 카메라 소스 시도
                    for i in range(4):  # 0부터 3까지 시도
                        print(f"카메라 소스 {i} 시도")
                        self.cap = cv2.VideoCapture(i)
                        if self.cap.isOpened():
                            self.video_source = i
                            print(f"카메라 소스 {i} 연결 성공")
                            break

                if not self.cap.isOpened():
                    print(f"카메라를 열 수 없습니다. video_source: {self.video_source}")
                    return False

                # 카메라 설정 적용 및 확인
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.video_settings['width'])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.video_settings['height'])
                self.cap.set(cv2.CAP_PROP_FPS, self.video_settings['fps'])

                # 설정이 제대로 적용되었는지 확인
                actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                actual_fps = self.cap.get(cv2.CAP_PROP_FPS)

                print(f"카메라 설정 - 너비: {actual_width}, 높이: {actual_height}, FPS: {actual_fps}")

                # 테스트 프레임 읽기
                ret, frame = self.cap.read()
                if not ret:
                    print("카메라에서 프레임을 읽을 수 없습니다.")
                    return False

                print("카메라 초기화 성공")
                return True

            return self.cap.isOpened()
        except Exception as e:
            print(f"카메라 초기화 중 오류 발생: {e}")
            return False

    def stop_capture(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("카메라 연결 해제")

    def add_session(self, session_id):
        self.active_sessions.add(session_id)
        if len(self.active_sessions) == 1:
            self.start_capture()

    def remove_session(self, session_id):
        if session_id in self.active_sessions:
            self.active_sessions.remove(session_id)
            if not self.active_sessions:
                self.stop_capture()