from flask import Flask, render_template, Response, jsonify, request, make_response
import cv2
import time
import uuid
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from .models.state import MonitoringState
from .models.database import Database
from .camera.detector import detect_tshirt_center

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
            static_folder=os.path.join(os.path.dirname(__file__), 'static'))
state = MonitoringState()
db = Database()

def generate_frames(session_id):
    session = state.get_or_create_session(session_id)

    while True:
        if not session.is_monitoring:
            time.sleep(0.1)
            continue

        try:
            if state.camera.cap is None or not state.camera.cap.isOpened():
                if not state.camera.start_capture():
                    time.sleep(1)
                    continue

            ret, frame = state.camera.cap.read()
            if not ret:
                continue

            # 프레임 좌우반전
            frame = cv2.flip(frame, 1)

            # detect_tshirt_center 사용
            processed_frame = detect_tshirt_center(frame, state)

            # 자동 캡처 로직
            current_time = time.time()
            if current_time - state.last_capture_time >= state.capture_interval:
                state.add_capture(processed_frame)

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),
                          state.camera.video_settings['quality']]
            ret, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        except Exception as e:
            print(f"Frame generation error for session {session_id}: {e}")
            time.sleep(1)

@app.route('/')
def index():
    session_id = request.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())

    # 저장된 이메일 주소 불러오기
    saved_email = db.get_setting('email')
    state.email = saved_email

    response = make_response(render_template('index.html', saved_email=saved_email))
    response.set_cookie('session_id', session_id)
    return response

@app.route('/heartbeat')
def heartbeat():
    session_id = request.cookies.get('session_id')
    if session_id:
        session = state.get_or_create_session(session_id)
        session.last_active = time.time()
    return jsonify({'success': True})

@app.route('/video_feed')
def video_feed():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return "No session", 400
    return Response(generate_frames(session_id),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_monitoring')
def toggle_monitoring():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'success': False})

    session = state.get_or_create_session(session_id)
    session.is_monitoring = not session.is_monitoring

    return jsonify({
        'success': True,
        'is_monitoring': session.is_monitoring
    })

@app.route('/toggle_alert')
def toggle_alert():
    state.alert_enabled = not state.alert_enabled
    return jsonify({'alert_enabled': state.alert_enabled})

@app.route('/get_status')
def get_status():
    return jsonify({
        'status': state.status,
        'distance': state.distance,
        'is_monitoring': state.is_monitoring,
        'alert_enabled': state.alert_enabled
    })

@app.route('/update_hsv', methods=['POST'])
def update_hsv():
    state.hsv_values = request.json
    return jsonify({'success': True})

@app.route('/change_source/<int:source>')
def change_source(source):
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'success': False})

    session = state.get_or_create_session(session_id)
    success = session.is_monitoring = True
    return jsonify({'success': success})

@app.route('/get_captures')
def get_captures():
    return jsonify({'captures': state.captures})

@app.route('/capture_current')
def capture_current():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'success': False})

    session = state.get_or_create_session(session_id)
    if not session.is_monitoring or state.camera.cap is None or not state.camera.cap.isOpened():
        return jsonify({'success': False, 'error': '모니터링이 활성화되지 않았습니다.'})

    ret, frame = state.camera.cap.read()
    if not ret:
        return jsonify({'success': False, 'error': '프레임을 읽을 수 없습니다.'})

    frame = detect_tshirt_center(frame, state)
    state.add_capture(frame, is_manual=True)

    return jsonify({'success': True, 'capture': state.captures[0]})

@app.route('/update_video_settings', methods=['POST'])
def update_video_settings():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'success': False})

    session = state.get_or_create_session(session_id)
    settings = request.json
    state.camera.video_settings.update(settings)
    return jsonify({'success': True})

@app.route('/save_email', methods=['POST'])
def save_email():
    email = request.json.get('email')
    if not email:
        return jsonify({'success': False, 'error': '이메일 주소가 필요합니다.'})
    state.email = email
    db.save_setting('email', email)
    return jsonify({'success': True})

def send_email_alert(to_email, message):
    try:
        # Gmail SMTP 서버 설정
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "ybg4828@gmail.com"
        sender_password = "qpxn yszx gukb hnvj"  # Gmail 앱 비밀번호 (16자리)

        # 이메일 메시지 생성
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = "[레이저 모니터링] 알림"

        msg.attach(MIMEText(message, 'plain'))

        # SMTP 서버 연결 및 이메일 전송
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

@app.route('/send_alert')
def send_alert():
    if not state.email:
        return jsonify({'success': False, 'error': '이메일 주소를 먼저 저장해주세요.'})

    try:
        message = f"비정상 상태가 감지되었습니다.\n상태: {state.status}\n거리: {state.distance}"
        if send_email_alert(state.email, message):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': '이메일 전송 실패'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)