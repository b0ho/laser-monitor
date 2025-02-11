import time

class UserSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.is_monitoring = False
        self.last_active = time.time()