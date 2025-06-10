import cv2
import numpy as np
import sys
import os

# 상위 디렉토리를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    print("WARNING: ultralytics 모듈을 찾을 수 없습니다. pip install ultralytics로 설치하세요.")
    YOLO_AVAILABLE = False

try:
    from config import Config
    from utils.logger import logger
except ImportError:
    # fallback logger
    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")
        def log_exception(self, msg, e): print(f"ERROR: {msg}: {e}")

    logger = MockLogger()

    # fallback config
    class Config:
        YOLO_MODEL_PATH = 'yolov8n.pt'
        DETECTION_CONFIDENCE = 0.6
        TARGET_DISTANCE = 10
        TOLERANCE = 50

class TshirtDetector:
    """T셔츠 감지를 위한 YOLO 기반 감지기"""
    _instance = None
    _model = None

    def __new__(cls):
        """싱글톤 패턴으로 모델 인스턴스 관리"""
        if cls._instance is None:
            cls._instance = super(TshirtDetector, cls).__new__(cls)
            cls._load_model()
        return cls._instance

    @classmethod
    def _load_model(cls):
        """YOLO 모델 로드"""
        if not YOLO_AVAILABLE:
            logger.error("YOLO 모듈이 설치되지 않았습니다. 객체 감지를 사용할 수 없습니다.")
            cls._model = None
            return

        try:
            cls._model = YOLO(Config.YOLO_MODEL_PATH)
            logger.info(f"YOLO 모델 로드 성공: {Config.YOLO_MODEL_PATH}")
        except Exception as e:
            logger.log_exception("YOLO 모델 로드 실패", e)
            cls._model = None

    def detect_keypoints(self, frame):
        """YOLOv8로 객체 감지 및 키포인트 추출"""
        if self._model is None:
            logger.error("YOLO 모델이 로드되지 않았습니다.")
            return None

        try:
            results = self._model(frame, conf=Config.DETECTION_CONFIDENCE)
            return results[0] if results else None
        except Exception as e:
            logger.log_exception("객체 감지 중 오류", e)
            return None

# 전역 감지기 인스턴스
detector = TshirtDetector()

def detect_tshirt_center(frame, state):
    """
    프레임에서 사람을 감지하고 T셔츠 중심점을 계산

    Args:
        frame: 입력 프레임
        state: 모니터링 상태 객체

    Returns:
        처리된 프레임
    """
    try:
        if frame is None or frame.size == 0:
            logger.warning("유효하지 않은 프레임")
            return frame

        frame_height, frame_width = frame.shape[:2]
        frame_center_x = frame_width // 2
        frame_center_y = frame_height // 2

        # YOLO 모델이 사용 불가능한 경우 기본 시각화만 제공
        if not YOLO_AVAILABLE or detector._model is None:
            state.status = "YOLO 모델 없음"
            state.distance = 0

            # 기본 시각화 (프레임 중심점만 표시)
            cv2.circle(frame, (frame_center_x, frame_center_y), 5, (0, 255, 0), -1)
            cv2.line(frame, (frame_center_x - 10, frame_center_y),
                    (frame_center_x + 10, frame_center_y), (0, 255, 0), 1)
            cv2.line(frame, (frame_center_x, frame_center_y - 10),
                    (frame_center_x, frame_center_y + 10), (0, 255, 0), 1)

            cv2.putText(frame, "YOLO model not available", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            return frame

        # YOLO 모델로 객체 감지
        results = detector._model(frame, conf=Config.DETECTION_CONFIDENCE)

        if not results or not results[0].boxes:
            state.status = "사람이 감지되지 않음"
            state.distance = 0
            return frame

        # 사람의 상체 부분만 감지
        detected = False
        best_match = None
        min_upper_body_y = float('inf')

        # 픽셀당 실제 거리(cm) 계산을 위한 기준값
        # 예: 1.5m 거리에서 촬영 시 사람의 평균 키(170cm)가 프레임 높이의 80%를 차지한다고 가정
        PIXELS_PER_CM = (frame_height * 0.8) / 170  # 1cm당 픽셀 수

        for result in results[0].boxes.data:
            class_id = int(result[5])
            confidence = float(result[4])

            # 사람 클래스(class_id=0)만 처리
            if class_id == 0 and confidence > Config.DETECTION_CONFIDENCE:
                x1, y1, x2, y2 = map(int, result[:4])

                # 머리 위치(y1)에서 목표 거리만큼 아래 지점을 목표점으로 설정
                target_y = y1 + int(Config.TARGET_DISTANCE * PIXELS_PER_CM)

                if y1 < min_upper_body_y:
                    min_upper_body_y = y1
                    best_match = {
                        'x1': x1,
                        'y1': y1,
                        'x2': x2,
                        'y2': y2,
                        'target_y': target_y,
                        'confidence': confidence
                    }

        if best_match:
            # 목표점 계산 (머리 위치에서 설정된 거리만큼 아래, 좌우 중앙)
            target_center_x = (best_match['x1'] + best_match['x2']) // 2
            target_center_y = best_match['target_y']

            # X축과 Y축 거리 별도 계산
            distance_x = abs(frame_center_x - target_center_x)
            distance_y = abs(frame_center_y - target_center_y)
            distance = np.sqrt(distance_x**2 + distance_y**2)

            # 실제 거리(cm) 계산
            real_distance_cm = distance / PIXELS_PER_CM

            # 상태 업데이트 (X, Y 축 각각 확인)
            tolerance = Config.TOLERANCE
            if distance_x <= tolerance and distance_y <= tolerance:
                state.status = "정상"
            elif distance_x > tolerance and distance_y <= tolerance:
                state.status = "좌우 벗어남"
            elif distance_x <= tolerance and distance_y > tolerance:
                if target_center_y < frame_center_y:
                    state.status = "너무 높음"
                else:
                    state.status = "너무 낮음"
            else:
                state.status = "중심에서 벗어남"

            state.distance = int(real_distance_cm)

            # 시각화
            _draw_visualization(frame, frame_center_x, frame_center_y,
                              target_center_x, target_center_y,
                              best_match, real_distance_cm)

            detected = True
            logger.debug(f"감지 성공: 상태={state.status}, 거리={state.distance}cm")

        if not detected:
            state.status = "사람이 감지되지 않음"
            state.distance = 0

        return frame

    except Exception as e:
        logger.log_exception("T셔츠 중심점 감지 중 오류", e)
        state.status = "처리 오류"
        state.distance = 0
        return frame

def _draw_visualization(frame, frame_center_x, frame_center_y,
                       target_center_x, target_center_y,
                       best_match, real_distance_cm):
    """
    프레임에 시각화 요소들을 그립니다.

    Args:
        frame: 대상 프레임
        frame_center_x, frame_center_y: 프레임 중심점
        target_center_x, target_center_y: 목표 중심점
        best_match: 감지된 객체 정보
        real_distance_cm: 실제 거리(cm)
    """
    try:
        # 프레임 중심점 (녹색)
        cv2.circle(frame, (frame_center_x, frame_center_y), 5, (0, 255, 0), -1)

        # 목표 중심점 (빨간색)
        cv2.circle(frame, (target_center_x, target_center_y), 5, (0, 0, 255), -1)

        # 감지된 영역 표시 (파란색)
        cv2.rectangle(frame,
                     (best_match['x1'], best_match['y1']),
                     (best_match['x2'], best_match['y2']),
                     (255, 0, 0), 2)

        # 중심점 연결선 (파란색)
        cv2.line(frame, (frame_center_x, frame_center_y),
                (target_center_x, target_center_y), (255, 0, 0), 2)

        # 정보 텍스트
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2

        # 거리 정보
        cv2.putText(frame, f"Distance: {int(real_distance_cm)}cm",
                   (10, 30), font, font_scale, (0, 255, 0), thickness)

        # 신뢰도 정보
        cv2.putText(frame, f"Confidence: {best_match['confidence']:.2f}",
                   (10, 60), font, font_scale, (0, 255, 0), thickness)

        # 프레임 중심 십자가
        cv2.line(frame, (frame_center_x - 10, frame_center_y),
                (frame_center_x + 10, frame_center_y), (0, 255, 0), 1)
        cv2.line(frame, (frame_center_x, frame_center_y - 10),
                (frame_center_x, frame_center_y + 10), (0, 255, 0), 1)

    except Exception as e:
        logger.log_exception("시각화 그리기 중 오류", e)