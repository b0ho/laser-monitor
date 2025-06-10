import logging
import os
import sys
from datetime import datetime

# 상위 디렉토리를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import Config
except ImportError:
    # Config 클래스가 없는 경우 기본값 사용
    class Config:
        LOG_LEVEL = 'INFO'
        LOG_FILE = 'laser_monitor.log'

class LaserMonitorLogger:
    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LaserMonitorLogger, cls).__new__(cls)
            cls._setup_logger()
        return cls._instance

    @classmethod
    def _setup_logger(cls):
        """로거 설정"""
        cls._logger = logging.getLogger('laser_monitor')
        cls._logger.setLevel(getattr(logging, Config.LOG_LEVEL))

        # 로그 포맷 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 파일 핸들러
        log_dir = os.path.dirname(Config.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = logging.FileHandler(Config.LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # 핸들러 추가
        cls._logger.addHandler(file_handler)
        cls._logger.addHandler(console_handler)

    def debug(self, message):
        self._logger.debug(message)

    def info(self, message):
        self._logger.info(message)

    def warning(self, message):
        self._logger.warning(message)

    def error(self, message):
        self._logger.error(message)

    def critical(self, message):
        self._logger.critical(message)

    def log_exception(self, message, exception):
        """예외와 함께 로그 기록"""
        self._logger.error(f"{message}: {str(exception)}", exc_info=True)

# 싱글톤 인스턴스 생성
logger = LaserMonitorLogger()