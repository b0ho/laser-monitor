import os
from dotenv import load_dotenv

# .env 파일 로드 (선택사항)
try:
    load_dotenv()
except:
    pass

class Config:
    # Flask 설정
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

    # 카메라 설정
    DEFAULT_VIDEO_SOURCE = int(os.getenv('DEFAULT_VIDEO_SOURCE', '0'))
    CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '640'))
    CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '480'))
    CAMERA_FPS = int(os.getenv('CAMERA_FPS', '30'))
    VIDEO_QUALITY = int(os.getenv('VIDEO_QUALITY', '85'))

    # 모니터링 설정
    CAPTURE_INTERVAL = int(os.getenv('CAPTURE_INTERVAL', '60'))  # 초
    TARGET_DISTANCE = int(os.getenv('TARGET_DISTANCE', '10'))  # cm
    DETECTION_CONFIDENCE = float(os.getenv('DETECTION_CONFIDENCE', '0.6'))
    TOLERANCE = int(os.getenv('TOLERANCE', '50'))  # 픽셀

    # 파일 관리 설정
    MAX_CAPTURES = int(os.getenv('MAX_CAPTURES', '10'))
    MAX_FILES = int(os.getenv('MAX_FILES', '20'))
    CAPTURE_DIR = os.getenv('CAPTURE_DIR', 'laser_monitor/static/captures')

    # 이메일 설정
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
    SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')

    # 세션 관리 설정
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '60'))  # 초

    # 로깅 설정
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'laser_monitor.log')

    # 모델 파일 경로
    YOLO_MODEL_PATH = os.getenv('YOLO_MODEL_PATH', 'yolov8n.pt')

    @classmethod
    def validate_config(cls):
        """설정 검증"""
        errors = []

        # 필수 디렉토리 생성
        try:
            os.makedirs(cls.CAPTURE_DIR, exist_ok=True)
        except Exception as e:
            errors.append(f"캡처 디렉토리 생성 실패: {e}")

        # YOLO 모델 파일 확인
        if not os.path.exists(cls.YOLO_MODEL_PATH):
            errors.append(f"YOLO 모델 파일을 찾을 수 없습니다: {cls.YOLO_MODEL_PATH}")

        return errors