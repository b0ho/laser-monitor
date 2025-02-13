import cv2
import numpy as np
from ultralytics import YOLO

class TshirtDetector:
    def __init__(self):
        # YOLOv8n 모델 로드
        self.model = YOLO('yolov8n.pt')
        # 티셔츠 관련 클래스 ID (COCO dataset: 'person': 0, 'tie': 27, ...)
        self.target_classes = [0, 27]  # person과 tie 클래스를 사용하여 상체 영역 추정

    def detect_keypoints(self, frame):
        # YOLOv8로 객체 감지 및 키포인트 추출
        results = self.model(frame, conf=0.5)
        return results[0] if results else None

def detect_tshirt_center(frame, state):
    try:
        frame_height, frame_width = frame.shape[:2]
        frame_center_x = frame_width // 2
        frame_center_y = frame_height // 2

        # YOLO 모델로 객체 감지
        model = YOLO('yolov8n.pt')
        results = model(frame)

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

            if class_id == 0 and confidence > 0.6:
                x1, y1, x2, y2 = map(int, result[:4])
                box_height = y2 - y1

                # 머리 위치(y1)에서 10cm 아래 지점을 목표점으로 설정
                target_y = y1 + int(10 * PIXELS_PER_CM)  # 10cm를 픽셀로 변환

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
            # 목표점 계산 (머리 위치에서 10cm 아래, 좌우 중앙)
            target_center_x = (best_match['x1'] + best_match['x2']) // 2
            target_center_y = best_match['target_y']

            # X축과 Y축 거리 별도 계산
            distance_x = abs(frame_center_x - target_center_x)
            distance_y = abs(frame_center_y - target_center_y)
            distance = np.sqrt(distance_x**2 + distance_y**2)

            # 실제 거리(cm) 계산
            real_distance_cm = distance / PIXELS_PER_CM

            # 상태 업데이트 (X, Y 축 각각 확인)
            tolerance = state.hsv_values['tolerance']
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

            state.distance = int(real_distance_cm)  # 거리를 cm 단위로 저장

            # 시각화
            # 프레임 중심점
            cv2.circle(frame, (frame_center_x, frame_center_y), 5, (0, 255, 0), -1)
            # 목표 중심점
            cv2.circle(frame, (target_center_x, target_center_y), 5, (0, 0, 255), -1)
            # 전체 영역 표시
            cv2.rectangle(frame,
                        (best_match['x1'], best_match['y1']),
                        (best_match['x2'], best_match['y2']),
                        (255, 0, 0), 2)
            # 중심점 연결선
            cv2.line(frame, (frame_center_x, frame_center_y),
                    (target_center_x, target_center_y), (255, 0, 0), 2)
            # 거리 정보
            cv2.putText(frame, f"Distance: {int(real_distance_cm)}cm", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Confidence: {best_match['confidence']:.2f}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            detected = True

        if not detected:
            state.status = "사람이 감지되지 않음"
            state.distance = 0

        return frame

    except Exception as e:
        return frame