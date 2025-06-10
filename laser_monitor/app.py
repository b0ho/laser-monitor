from flask import Flask, render_template, Response, jsonify, request, make_response
import cv2
import numpy as np
import time
import uuid
import os
import sys

# 현재 파일의 디렉토리를 path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from config import Config
    from utils.logger import logger
    from utils.email_sender import email_sender
    from models.state import MonitoringState
    from models.database import Database
    from camera.detector import detect_tshirt_center
except ImportError as e:
    print(f"Import error: {e}")
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
        SECRET_KEY = 'fallback-secret-key'
        DEBUG = True
        VIDEO_QUALITY = 85
        CAPTURE_DIR = 'laser_monitor/static/captures'

    # 최소한의 state와 detector
    class MockState:
        def __init__(self):
            self.status = "Import Error"
            self.distance = 0
            self.is_monitoring = False
            self.alert_enabled = False
            self.captures = []
            self.hsv_values = {'tolerance': 50}
            self.email = None

        def get_or_create_session(self, session_id):
            return self

        def add_capture(self, frame, is_manual=False):
            pass

    class MockDatabase:
        def get_setting(self, key):
            return None
        def save_setting(self, key, value):
            pass

    def detect_tshirt_center(frame, state):
        return frame

    state = MockState()
    db = MockDatabase()
    email_sender = None

# Flask 앱 초기화
app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# 설정 적용
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['DEBUG'] = Config.DEBUG

# 전역 객체 초기화 (import 성공한 경우에만)
if 'MonitoringState' in globals():
    state = MonitoringState()
    db = Database()
    # 설정 검증
    config_errors = Config.validate_config()
    if config_errors:
        for error in config_errors:
            logger.warning(f"설정 오류: {error}")

# 필요한 디렉토리 생성
os.makedirs(Config.CAPTURE_DIR, exist_ok=True)

def generate_frames(session_id):
    """비디오 프레임 생성기"""
    session = state.get_or_create_session(session_id)
    logger.info(f"프레임 생성 시작: 세션 {session_id}")

    while True:
        if not session.is_monitoring:
            time.sleep(0.1)
            continue

        try:
            # 카메라 연결 확인 및 재연결
            if hasattr(state, 'camera') and state.camera.cap is None or not state.camera.cap.isOpened():
                logger.warning("카메라 재연결 시도")
                if not state.camera.start_capture():
                    logger.error("카메라를 열 수 없습니다. 5초 후 재시도합니다.")
                    time.sleep(5)
                    continue

            # 임시로 더미 프레임 생성 (카메라 없는 경우)
            if not hasattr(state, 'camera') or state.camera.cap is None:
                # 640x480 더미 프레임 생성
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Camera not available", (50, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

                # 프레임 중심점 표시
                cv2.circle(frame, (320, 240), 5, (0, 255, 0), -1)
                cv2.line(frame, (310, 240), (330, 240), (0, 255, 0), 1)
                cv2.line(frame, (320, 230), (320, 250), (0, 255, 0), 1)

                processed_frame = frame
            else:
                ret, frame = state.camera.cap.read()
                if not ret:
                    logger.warning("프레임을 읽을 수 없습니다.")
                    state.camera.stop_capture()
                    continue

                # 프레임 좌우반전
                frame = cv2.flip(frame, 1)

                # 객체 감지 및 처리
                processed_frame = detect_tshirt_center(frame, state)

            # 프레임 유효성 검사
            if processed_frame is None or processed_frame.size == 0:
                logger.warning("유효하지 않은 프레임")
                continue

            # 프레임 인코딩
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), Config.VIDEO_QUALITY]
            ret, buffer = cv2.imencode('.jpg', processed_frame, encode_param)

            if not ret:
                logger.warning("프레임 인코딩 실패")
                continue

            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        except Exception as e:
            logger.log_exception("프레임 생성 중 오류 발생", e)
            time.sleep(1)

@app.route('/')
def index():
    """메인 페이지"""
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"새 세션 생성: {session_id}")

        # 저장된 이메일 주소 불러오기
        saved_email = db.get_setting('email')
        state.email = saved_email

        # 세션 생성 및 모니터링 시작
        session = state.get_or_create_session(session_id)
        session.is_monitoring = True

        logger.info(f"세션 {session_id} 모니터링 시작")

        response = make_response(render_template('index.html', saved_email=saved_email))
        response.set_cookie('session_id', session_id, secure=False, httponly=True)
        return response

    except Exception as e:
        logger.log_exception("메인 페이지 로드 중 오류", e)
        return "서버 오류가 발생했습니다.", 500

@app.route('/heartbeat')
def heartbeat():
    """세션 활성 상태 유지"""
    try:
        session_id = request.cookies.get('session_id')
        if session_id:
            session = state.get_or_create_session(session_id)
            session.last_active = time.time()
        return jsonify({'success': True})
    except Exception as e:
        logger.log_exception("하트비트 처리 중 오류", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/video_feed')
def video_feed():
    """비디오 스트림 제공"""
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            logger.warning("세션 ID 없이 비디오 피드 요청")
            return "No session", 400

        return Response(generate_frames(session_id),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        logger.log_exception("비디오 피드 제공 중 오류", e)
        return "Video feed error", 500

@app.route('/toggle_monitoring')
def toggle_monitoring():
    """모니터링 토글"""
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': '세션이 없습니다.'})

        session = state.get_or_create_session(session_id)
        session.is_monitoring = not session.is_monitoring

        logger.info(f"세션 {session_id} 모니터링 상태 변경: {session.is_monitoring}")

        return jsonify({
            'success': True,
            'is_monitoring': session.is_monitoring
        })
    except Exception as e:
        logger.log_exception("모니터링 토글 중 오류", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/toggle_alert')
def toggle_alert():
    """알림 토글"""
    try:
        state.alert_enabled = not state.alert_enabled
        logger.info(f"알림 상태 변경: {state.alert_enabled}")
        return jsonify({'alert_enabled': state.alert_enabled})
    except Exception as e:
        logger.log_exception("알림 토글 중 오류", e)
        return jsonify({'error': str(e)}), 500

@app.route('/get_status')
def get_status():
    """현재 상태 조회"""
    try:
        return jsonify({
            'status': state.status,
            'distance': state.distance,
            'is_monitoring': state.is_monitoring,
            'alert_enabled': state.alert_enabled
        })
    except Exception as e:
        logger.log_exception("상태 조회 중 오류", e)
        return jsonify({'error': str(e)}), 500

@app.route('/update_hsv', methods=['POST'])
def update_hsv():
    """HSV 값 업데이트"""
    try:
        hsv_values = request.get_json()
        if not hsv_values:
            return jsonify({'success': False, 'error': '데이터가 없습니다.'})

        state.hsv_values.update(hsv_values)
        logger.info(f"HSV 값 업데이트: {hsv_values}")
        return jsonify({'success': True})
    except Exception as e:
        logger.log_exception("HSV 업데이트 중 오류", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_captures')
def get_captures():
    """캡처 목록 조회"""
    try:
        return jsonify({'captures': state.captures})
    except Exception as e:
        logger.log_exception("캡처 목록 조회 중 오류", e)
        return jsonify({'error': str(e)}), 500

@app.route('/capture_current')
def capture_current():
    """현재 화면 캡처"""
    try:
        # 카메라가 활성 상태인지 확인
        if not hasattr(state, 'camera') or not state.camera or not state.camera.is_active():
            return jsonify({'success': False, 'error': '카메라가 활성화되지 않았습니다.'})

        # 현재 프레임 가져오기
        ret, frame = state.camera.get_frame()
        if not ret or frame is None:
            return jsonify({'success': False, 'error': '프레임을 가져올 수 없습니다.'})

        # 객체 감지 적용
        processed_frame = detect_tshirt_center(frame, state)
        if processed_frame is None:
            processed_frame = frame

        # 수동 캡처로 저장
        state.add_capture(processed_frame, is_manual=True)

        if state.captures:
            latest_capture = state.captures[0]  # 가장 최근 캡처
            logger.info(f"수동 캡처 완료: {latest_capture.get('time', 'Unknown')}")
            return jsonify({
                'success': True,
                'capture': latest_capture
            })
        else:
            return jsonify({'success': False, 'error': '캡처 저장에 실패했습니다.'})

    except Exception as e:
        logger.log_exception("현재 화면 캡처 중 오류", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/save_email', methods=['POST'])
def save_email():
    """이메일 주소 저장"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '데이터가 없습니다.'})

        email = data.get('email')
        if not email:
            return jsonify({'success': False, 'error': '이메일 주소가 필요합니다.'})

        # 간단한 이메일 형식 검증
        if '@' not in email or '.' not in email:
            return jsonify({'success': False, 'error': '올바른 이메일 형식이 아닙니다.'})

        state.email = email
        db.save_setting('email', email)
        logger.info(f"이메일 주소 저장: {email}")
        return jsonify({'success': True})
    except Exception as e:
        logger.log_exception("이메일 저장 중 오류", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/send_alert')
def send_alert():
    """알림 이메일 전송"""
    try:
        if not state.email:
            return jsonify({'success': False, 'error': '이메일 주소를 먼저 저장해주세요.'})

        if email_sender is None:
            return jsonify({'success': False, 'error': '이메일 기능이 비활성화되었습니다.'})

        message = f"비정상 상태가 감지되었습니다.\n상태: {state.status}\n거리: {state.distance}cm"

        success = email_sender.send_alert(state.email, message)

        if success:
            logger.info(f"알림 이메일 전송 성공: {state.email}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '이메일 전송 실패'})

    except Exception as e:
        logger.log_exception("알림 전송 중 오류", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_quality_presets')
def get_quality_presets():
    """화질 프리셋 목록 조회"""
    try:
        presets = Config.get_available_presets()
        return jsonify({
            'success': True,
            'presets': presets,
            'current': Config.CURRENT_QUALITY_PRESET
        })
    except Exception as e:
        logger.log_exception("화질 프리셋 조회 중 오류", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_current_quality')
def get_current_quality():
    """현재 화질 설정 조회"""
    try:
        current_preset = Config.get_quality_preset()

        # 카메라 정보 조회 (state.camera 사용)
        camera_info = None
        if hasattr(state, 'camera') and state.camera and hasattr(state.camera, 'get_camera_info'):
            camera_info = state.camera.get_camera_info()

        return jsonify({
            'success': True,
            'preset': current_preset,
            'preset_name': Config.CURRENT_QUALITY_PRESET,
            'camera_info': camera_info
        })
    except Exception as e:
        logger.log_exception("현재 화질 설정 조회 중 오류", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/set_quality_preset', methods=['POST'])
def set_quality_preset():
    """화질 프리셋 변경"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '데이터가 없습니다.'})

        preset_name = data.get('preset')
        if not preset_name:
            return jsonify({'success': False, 'error': '프리셋 이름이 필요합니다.'})

        # 프리셋 설정 적용
        if Config.set_quality_preset(preset_name):
            # 카메라에 새 설정 적용 (state.camera 사용)
            if hasattr(state, 'camera') and state.camera and state.camera.is_active():
                preset = Config.get_quality_preset(preset_name)
                new_settings = {
                    'width': preset['width'],
                    'height': preset['height'],
                    'fps': preset['fps'],
                    'quality': preset['quality']
                }

                # 카메라 설정 업데이트
                if state.camera.update_settings(new_settings):
                    logger.info(f"화질 프리셋 변경 성공: {preset_name} ({preset['description']})")
                    return jsonify({
                        'success': True,
                        'preset': preset,
                        'message': f"화질이 '{preset['name']}'으로 변경되었습니다."
                    })
                else:
                    logger.warning(f"화질 프리셋 설정 실패: {preset_name}")
                    return jsonify({'success': False, 'error': '카메라 설정 적용 실패'})
            else:
                logger.info(f"화질 프리셋 설정 (카메라 비활성 상태): {preset_name}")
                preset = Config.get_quality_preset(preset_name)
                return jsonify({
                    'success': True,
                    'preset': preset,
                    'message': f"화질이 '{preset['name']}'으로 설정되었습니다. (다음 카메라 시작 시 적용)"
                })
        else:
            return jsonify({'success': False, 'error': '유효하지 않은 프리셋입니다.'})

    except Exception as e:
        logger.log_exception("화질 프리셋 변경 중 오류", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """404 에러 핸들러"""
    logger.warning(f"404 오류: {request.url}")
    return "페이지를 찾을 수 없습니다.", 404

@app.errorhandler(500)
def internal_error(error):
    """500 에러 핸들러"""
    logger.error(f"500 오류: {error}")
    return "서버 내부 오류가 발생했습니다.", 500

if __name__ == '__main__':
    try:
        logger.info("레이저 모니터 애플리케이션 시작")
        logger.info(f"Debug 모드: {Config.DEBUG}")

        # 필요한 디렉토리 생성
        os.makedirs(Config.CAPTURE_DIR, exist_ok=True)

        app.run(host='127.0.0.1', port=5000, debug=Config.DEBUG, threaded=True)
    except Exception as e:
        logger.log_exception("애플리케이션 시작 중 오류", e)
        raise