import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from config import Config
from .logger import logger

class EmailSender:
    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.sender_email = Config.SENDER_EMAIL
        self.sender_password = Config.SENDER_PASSWORD

        # 설정 검증
        if not all([self.sender_email, self.sender_password]):
            logger.warning("이메일 설정이 완전하지 않습니다. 이메일 기능이 비활성화됩니다.")
            self.enabled = False
        else:
            self.enabled = True

    def send_alert(self, to_email, message, subject="[레이저 모니터링] 알림", image_path=None):
        """
        알림 이메일 전송

        Args:
            to_email (str): 수신자 이메일
            message (str): 메시지 내용
            subject (str): 이메일 제목
            image_path (str): 첨부할 이미지 경로 (선택사항)

        Returns:
            bool: 전송 성공 여부
        """
        if not self.enabled:
            logger.error("이메일 기능이 비활성화되어 있습니다.")
            return False

        try:
            # 이메일 메시지 생성
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # 텍스트 내용 추가
            msg.attach(MIMEText(message, 'plain', 'utf-8'))

            # 이미지 첨부 (선택사항)
            if image_path and os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as f:
                        img_data = f.read()
                    image = MIMEImage(img_data)
                    image.add_header('Content-Disposition',
                                   f'attachment; filename={os.path.basename(image_path)}')
                    msg.attach(image)
                    logger.debug(f"이미지 첨부됨: {image_path}")
                except Exception as e:
                    logger.warning(f"이미지 첨부 실패: {e}")

            # SMTP 서버 연결 및 이메일 전송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(f"이메일 전송 성공: {to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP 인증 실패. 이메일과 비밀번호를 확인하세요.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP 오류: {e}")
            return False
        except Exception as e:
            logger.log_exception("이메일 전송 중 예상치 못한 오류", e)
            return False

    def test_connection(self):
        """
        이메일 서버 연결 테스트

        Returns:
            bool: 연결 성공 여부
        """
        if not self.enabled:
            return False

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
            logger.info("이메일 서버 연결 테스트 성공")
            return True
        except Exception as e:
            logger.log_exception("이메일 서버 연결 테스트 실패", e)
            return False

# 싱글톤 인스턴스
email_sender = EmailSender()