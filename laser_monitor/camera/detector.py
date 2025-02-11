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
    # 프레임 좌우반전
    frame = cv2.flip(frame, 1)

    # 원본 프레임 복사
    output = frame.copy()
    height, width = frame.shape[:2]
    center_x = width // 2
    center_y = height // 2

    # 화면 중앙 표시
    cv2.circle(output, (center_x, center_y), 5, (255, 0, 0), -1)  # 중앙점
    cv2.line(output, (center_x, 0), (center_x, height), (255, 0, 0), 1)  # 수직선
    cv2.line(output, (0, center_y), (width, center_y), (255, 0, 0), 1)  # 수평선

    try:
        # 이미지 전처리
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        # Canny 엣지 검출
        edges = cv2.Canny(blurred, 50, 150)

        # 윤곽선 찾기
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # 면적이 큰 순서대로 정렬
            contours = sorted(contours, key=cv2.contourArea, reverse=True)

            # 가장 큰 윤곽선 선택
            largest_contour = contours[0]

            # 윤곽선 면적이 너무 작으면 무시
            if cv2.contourArea(largest_contour) < 10000:  # 최소 면적 조정
                state.status = "티셔츠가 너무 작음"
                state.distance = -1
                return output

            # 외접 사각형 구하기
            rect = cv2.minAreaRect(largest_contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)

            # 티셔츠의 중심점 계산
            tshirt_center_x = int(rect[0][0])
            tshirt_center_y = int(rect[0][1])

            # 회전된 사각형 그리기
            cv2.drawContours(output, [box], 0, (0, 255, 0), 2)

            # 중심점 표시
            cv2.circle(output, (tshirt_center_x, tshirt_center_y), 5, (0, 255, 0), -1)

            # 가이드라인 표시 (로고 영역 표시)
            width_rect = int(rect[1][0])
            height_rect = int(rect[1][1])
            logo_size = min(width_rect, height_rect) // 4  # 로고 크기는 티셔츠 크기의 1/4

            cv2.circle(output, (tshirt_center_x, tshirt_center_y), logo_size, (0, 255, 255), 2)

            # 중앙점과의 거리 계산
            distance_x = abs(center_x - tshirt_center_x)
            distance_y = abs(center_y - tshirt_center_y)

            # 허용 오차 (화면 크기의 1%로 설정 - 더 정확한 정렬을 위해)
            tolerance_x = width * 0.01
            tolerance_y = height * 0.01

            # 상태 업데이트
            if distance_x <= tolerance_x and distance_y <= tolerance_y:
                state.status = "정상 - 로고 위치 OK"
                state.distance = 0
                # 정확히 중앙에 있을 때 녹색 원으로 표시
                cv2.circle(output, (center_x, center_y), logo_size, (0, 255, 0), 2)
            else:
                state.status = "비정상 - 중앙 맞춤 필요"
                state.distance = int(max(distance_x, distance_y))

                # 방향 안내
                if distance_x > tolerance_x:
                    direction_x = "오른쪽으로" if tshirt_center_x < center_x else "왼쪽으로"
                    cv2.putText(output, direction_x, (10, 30),
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                if distance_y > tolerance_y:
                    direction_y = "위로" if tshirt_center_y < center_y else "아래로"
                    cv2.putText(output, direction_y, (10, 60),
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # 거리 및 정확도 표시
            accuracy = max(0, 100 - (state.distance / max(tolerance_x, tolerance_y)) * 100)
            cv2.putText(output, f"정확도: {accuracy:.1f}%", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(output, f"오차: {distance_x:.1f}, {distance_y:.1f}px", (10, 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        else:
            state.status = "티셔츠 감지 안됨"
            state.distance = -1

    except Exception as e:
        print(f"Error in detect_tshirt_center: {e}")
        state.status = "에러"
        state.distance = -1

    return output