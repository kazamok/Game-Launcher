from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, 
    QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QObject
from api.auth_api import AuthAPI, AuthResult
import asyncio
from asyncio import TimeoutError

class LoginSignals(QObject):
    success = Signal(AuthResult)
    error = Signal(str)

class LoginDialog(QDialog):
    def __init__(self, loop, parent=None):
        super().__init__(parent)
        self.loop = loop  # MainWindow로부터 이벤트 루프를 전달받음
        self.auth_api = AuthAPI()
        self.auth_result = None
        self.signals = LoginSignals()
        self.login_timeout = 5  # 타임아웃 (초)
        # UI 상태 캐싱
        self._is_logging_in = False
        self.setObjectName("login-dialog")
        self.setup_ui()
        
        # 시그널 연결
        self.signals.success.connect(self.on_login_success)
        self.signals.error.connect(self.on_login_error)
        
    def setup_ui(self):
        """UI 설정"""
        self.setWindowTitle("로그인")
        self.setFixedSize(350, 320)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 제목
        title = QLabel("계정 로그인")
        title.setAlignment(Qt.AlignCenter)
        title.setProperty("class", "login-title")
        layout.addSpacing(5)
        layout.addWidget(title)
        layout.addSpacing(20)
        
        # 입력 필드
        self.username = QLineEdit()
        self.username.setPlaceholderText("계정 이름")
        self.username.setProperty("class", "login-input")
        self.username.setFixedHeight(40)
        layout.addWidget(self.username)
        layout.addSpacing(15)
        
        self.password = QLineEdit()
        self.password.setPlaceholderText("비밀번호")
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setProperty("class", "login-input")
        self.password.setFixedHeight(40)
        layout.addWidget(self.password)
        layout.addSpacing(20)
        
        # 로그인 버튼
        self.login_button = QPushButton("로그인")
        self.login_button.setProperty("class", "login-button")
        self.login_button.setFixedHeight(40)
        self.login_button.clicked.connect(self.handle_login)
        layout.addWidget(self.login_button)
        layout.addStretch() # 버튼 아래 공간을 채우기 위해 Stretch 추가
        
    def handle_login(self):
        """로그인 버튼 클릭 핸들러"""
        if self._is_logging_in:
            return
            
        username = self.username.text().strip()
        password = self.password.text().strip()
        
        if not username or not password:
            QMessageBox.warning(
                self,
                "오류",
                "계정 이름과 비밀번호를 입력하세요"
            )
            return
            
        self._is_logging_in = True
        self.login_button.setEnabled(False)
        self.login_button.setText("로그인 중...")
        
        # MainWindow의 이벤트 루프를 사용하여 비동기 로그인 실행
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.try_login(username, password), self.loop)
        else:
            self.on_login_error("이벤트 루프를 찾을 수 없습니다.")
        
    async def try_login(self, username: str, password: str):
        """비동기 로그인 시도"""
        try:
            # 로그인 작업에 타임아웃 추가
            result = await asyncio.wait_for(
                self.auth_api.login(username, password),
                timeout=self.login_timeout
            )
            if result.success:
                self.signals.success.emit(result)
            else:
                self.signals.error.emit(result.message)
        except TimeoutError:
            self.signals.error.emit("요청 시간이 초과되었습니다. 서버 연결을 확인하세요.")
        except ConnectionRefusedError:
            self.signals.error.emit("데이터베이스 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        except Exception as e:
            # 모든 다른 예외에 대해 구체적인 오류 메시지를 표시합니다.
            error_message = f"예상치 못한 오류가 발생했습니다:\n{str(e)}"
            self.signals.error.emit(error_message)
            print(f"로그인 오류: {str(e)}")  # 디버깅용
            
    def on_login_success(self, result: AuthResult):
        """성공적인 로그인 핸들러"""
        self.auth_result = result
        self.accept()
        
    def on_login_error(self, message: str):
        """로그인 오류 핸들러"""
        QMessageBox.warning(
            self,
            "로그인 오류",
            message
        ) 