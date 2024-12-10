from .utils import verify_password
from .schemas import UserInDB

class User(UserInDB):
    def check_password(self, password: str) -> bool:
        try:
            print(f"Checking password. Hash: {self.hashed_password}")  # 调试日志
            return verify_password(password, self.hashed_password)
        except Exception as e:
            print(f"Password check error: {e}")  # 调试日志
            return False