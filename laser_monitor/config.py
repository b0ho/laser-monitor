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

    # 화질 프리셋 정의 (4K 카메라 지원)
    QUALITY_PRESETS = {
        'ultra': {
            'name': '최고 화질 (4K)',
            'width': 3840,
            'height': 2160,
            'fps': 60,
            'quality': 98,
            'brightness': 0,
            'contrast': 32,
            'saturation': 32,
            'autofocus': True,
            'description': '3840x2160 4K UHD, 60fps, 최고 화질'
        },
        'high': {
            'name': '고화질 (Full HD)',
            'width': 1920,
            'height': 1080,
            'fps': 60,
            'quality': 95,
            'brightness': 0,
            'contrast': 32,
            'saturation': 32,
            'autofocus': True,
            'description': '1920x1080 Full HD, 60fps, 고화질'
        },
        'medium': {
            'name': '중간 화질 (HD)',
            'width': 1280,
            'height': 720,
            'fps': 30,
            'quality': 85,
            'brightness': 0,
            'contrast': 32,
            'saturation': 32,
            'autofocus': True,
            'description': '1280x720 HD, 30fps, 표준 화질'
        },
        'low': {
            'name': '기본 화질 (SD)',
            'width': 640,
            'height': 480,
            'fps': 30,
            'quality': 75,
            'brightness': 0,
            'contrast': 32,
            'saturation': 32,
            'autofocus': True,
            'description': '640x480 SD, 30fps, 기본 화질'
        }
    }

    # 현재 화질 프리셋 (기본값: 4K 최고 화질)
    CURRENT_QUALITY_PRESET = os.getenv('QUALITY_PRESET', 'ultra')

    # 카메라 설정 (선택된 프리셋에서 가져옴)
    DEFAULT_VIDEO_SOURCE = int(os.getenv('DEFAULT_VIDEO_SOURCE', '0'))
    CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', str(QUALITY_PRESETS[CURRENT_QUALITY_PRESET]['width'])))
    CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', str(QUALITY_PRESETS[CURRENT_QUALITY_PRESET]['height'])))
    CAMERA_FPS = int(os.getenv('CAMERA_FPS', str(QUALITY_PRESETS[CURRENT_QUALITY_PRESET]['fps'])))
    VIDEO_QUALITY = int(os.getenv('VIDEO_QUALITY', str(QUALITY_PRESETS[CURRENT_QUALITY_PRESET]['quality'])))

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
    def get_quality_preset(cls, preset_name=None):
        """화질 프리셋 가져오기"""
        if preset_name is None:
            preset_name = cls.CURRENT_QUALITY_PRESET
        return cls.QUALITY_PRESETS.get(preset_name, cls.QUALITY_PRESETS['ultra'])

    @classmethod
    def set_quality_preset(cls, preset_name):
        """화질 프리셋 설정"""
        if preset_name in cls.QUALITY_PRESETS:
            cls.CURRENT_QUALITY_PRESET = preset_name
            preset = cls.QUALITY_PRESETS[preset_name]
            cls.CAMERA_WIDTH = preset['width']
            cls.CAMERA_HEIGHT = preset['height']
            cls.CAMERA_FPS = preset['fps']
            cls.VIDEO_QUALITY = preset['quality']
            return True
        return False

    @classmethod
    def get_available_presets(cls):
        """사용 가능한 화질 프리셋 목록"""
        return {name: preset for name, preset in cls.QUALITY_PRESETS.items()}

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