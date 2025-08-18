import json
from pathlib import Path
import os
import aiohttp
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QFrame, 
    QGridLayout, QLineEdit, QDialog, QTabWidget,
    QCheckBox, QFileDialog, QComboBox, QMenu, QMessageBox, QGroupBox,
    QSystemTrayIcon, QApplication
)
from PySide6.QtCore import Qt, QSize, QTimer, QPoint, Signal
from PySide6.QtGui import (
    QPixmap, QPalette, QBrush, QFont, QIcon, 
    QPainter, QLinearGradient, QColor, QAction
)
from api.server_api import ServerAPI
from api.auth_api import AuthResult
import asyncio
import sys
from ui.login_dialog import LoginDialog
from utils.game_launcher import GameLauncher
from utils.resource_path import resource_path
import platform
import humanize
import webbrowser

# 상수
CARD_SPACING = 15
CARD_MARGINS = (15, 10, 15, 10)
DEFAULT_ICON_SIZE = QSize(20, 20)
PLAY_BUTTON_SIZE = QSize(200, 50)
SETTINGS_BUTTON_SIZE = QSize(40, 40)
PROGRESS_BAR_HEIGHT = 4

# 색상
COLOR_PRIMARY = "#FFB100"
COLOR_SUCCESS = "#2ecc71"
COLOR_BACKGROUND = "rgba(0, 0, 0, 0.7)"

# 크기
MAIN_NEWS_IMAGE_HEIGHT = 200
SMALL_NEWS_IMAGE_HEIGHT = 100
SETTINGS_DIALOG_WIDTH = 600

class Card(QFrame):
    """카드 위젯의 기본 클래스"""
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        if title:
            title_label = QLabel(title)
            title_label.setProperty("class", "title")
            self.layout.addWidget(title_label)

class MainWindow(QMainWindow):
    server_status_updated = Signal(dict)
    game_launch_success = Signal()
    game_launch_error = Signal(str, str)

    def __init__(self):
        super().__init__()
        
        # 자주 사용하는 위젯 캐싱
        self._cached_widgets = {}
        
        # 스타일 로드
        self._load_styles()
        
        # 비동기 작업을 위한 이벤트 루프 준비
        self.loop = None
        
        # API 클라이언트 초기화
        self.server_api = ServerAPI()
        
        # 상태 업데이트 타이머
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_server_status)
        self.status_timer.start(30000)  # 30초마다 업데이트
        
        # --- 설정 경로 수정 ---
        app_data_path = Path(os.getenv('LOCALAPPDATA')) / 'WoWLauncher'
        self.settings_file = app_data_path / "settings.json"
        
        self.default_settings = {
            "game": {
                "path": "",
                "realmlist": "127.0.0.1", # 수정이 필요합니다
                "launch_options": ""
            },
            "graphics": {
                "resolution": "1920x1080",
                "quality": "높음",
                "windowed": False
            },
            "auth": {
                "username": None,
                "account_id": None,
                "auto_login": False
            }
        }
        
        self.settings = self.load_settings()
        self.game_launcher = GameLauncher(self.settings, self)
        self.current_user = None
        
        # GameLauncher 시그널 연결
        self.game_launcher.signals.client_missing.connect(self.show_download_buttons)
        self.game_launcher.signals.download_progress.connect(self.update_download_progress)
        self.game_launcher.signals.download_error.connect(self.on_download_error)
        self.game_launcher.signals.login_required.connect(self.handle_login_required)
        self.game_launcher.signals.verification_progress.connect(self.update_verification_progress)
        
        # 저장된 인증 정보 확인
        auth = self.settings.get('auth', {})
        if auth.get('username') and auth.get('account_id'):
            self.current_user = AuthResult(
                success=True,
                message="세션이 복원되었습니다",
                username=auth['username'],
                account_id=auth['account_id']
            )
            # GameLauncher에 데이터 업데이트
            self.game_launcher.set_account_info(
                auth['username'],
                auth['account_id']
            )

        # UI 생성
        self.setWindowTitle("WoW 3.3.5 런처")
        self.setWindowIcon(QIcon(str(resource_path("assets/images/wow-logo.png"))))
        self.setFixedSize(1200, 800)
        
        # 배경 이미지
        self.background = QPixmap(str(resource_path("assets/images/background.jpg")))
        self.updateBackground()
        
        # 메인 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 30, 40, 30)
        
        # 컴포넌트
        main_layout.addWidget(self.create_header())
        main_layout.addWidget(self.create_status_cards())
        main_layout.addWidget(self.create_content())
        
        # 푸터 생성
        footer = QWidget()
        footer.setObjectName("footer")
        self.footer_layout = QHBoxLayout(footer)
        self.footer_layout.setContentsMargins(20, 10, 20, 10)
        self.footer_layout.setSpacing(10)
        self.footer_layout.setAlignment(Qt.AlignLeft)  # 왼쪽 정렬
        
        # 게임 버튼 설정
        self.setup_game_button()

        # 클라이언트 받기 버튼 추가
        get_client_button = QPushButton("클라이언트 받기")
        get_client_button.setObjectName("get-client-button")
        get_client_button.clicked.connect(self.open_download_page)
        self.footer_layout.addWidget(get_client_button)
        
        # 버튼 뒤에 늘어나는 스페이서 추가
        self.footer_layout.addStretch()
        
        main_layout.addWidget(footer)
        
        self.server_status_updated.connect(self._on_server_status_updated)
        self.game_launch_success.connect(self.handle_game_launch_success)
        self.game_launch_error.connect(self.handle_game_launch_error)
        
        # 저장된 세션이 있으면 UI 업데이트
        # 저장된 세션이 있으면 UI 업데이트
        # 저장된 세션이 있으면 UI 업데이트
        if self.current_user:
            self.update_ui_after_login()

        # 트레이 아이콘 초기화
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(str(resource_path("assets/images/wow-logo.png"))))
        self.tray_icon.setToolTip("WoW 3.3.5 런처")  # 마우스 오버 시 툴팁
        
        # 트레이 아이콘 메뉴 생성
        self.tray_menu = QMenu()
        
        # 메뉴 항목 추가
        play_action = QAction("게임 시작", self)
        play_action.triggered.connect(lambda: asyncio.run_coroutine_threadsafe(self.launch_game_from_tray(), self.loop))
        self.tray_menu.addAction(play_action)
        
        restore_action = QAction("복원", self)
        restore_action.triggered.connect(self.show_normal)
        self.tray_menu.addAction(restore_action)
        
        exit_action = QAction("종료", self)
        exit_action.triggered.connect(self.close)
        self.tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()  # 아이콘 바로 표시

    def _load_styles(self):
        """스타일 로드"""
        try:
            with open(str(resource_path("assets/styles/main.qss")), "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"스타일 로드 오류: {e}")

    def _get_widget(self, name: str):
        """캐시된 위젯 가져오기"""
        if name not in self._cached_widgets:
            self._cached_widgets[name] = self.findChild(QWidget, name)
        return self._cached_widgets[name]

    def create_content(self):
        content = Card("뉴스")
        content.setMinimumHeight(400)
        
        # 뉴스를 위한 그리드 레이아웃 생성
        grid = QGridLayout()
        grid.setSpacing(15)
        content.layout.addLayout(grid)
        
        # 메인 뉴스를 생성하여 그리드 전체를 차지하도록 설정
        main_news = self.create_news_card(
            "새 시즌 오픈",
            "",
            "main_news.jpg",
            is_main=True
        )
        grid.addWidget(main_news, 0, 0, 1, 1)  # 1x1 셀 차지, 그리드 레이아웃이 알아서 확장함
        
        return content

    def create_header(self):
        """로고와 내비게이션이 있는 헤더 생성"""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 로고
        logo = QLabel()
        logo_pixmap = QPixmap(str(resource_path("assets/images/wow-logo.png")))
        logo.setPixmap(logo_pixmap.scaled(150, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(logo)
        
        # 내비게이션
        nav = QHBoxLayout()
        nav.setSpacing(20)
        
        # 왼쪽에 늘어나는 요소 추가
        nav.addStretch()
        
        # 내비게이션 버튼
        # 나중에 변경필요
        homepage_btn = self.create_nav_button("홈페이지 (CMS)", str(resource_path("assets/images/news-icon.svg")))
        homepage_btn.clicked.connect(self.open_homepage)
        nav.addWidget(homepage_btn)
        
        # 로그인/계정 버튼
        self.account_btn = QPushButton("로그인")
        self.account_btn.setProperty("class", "login-button")
        self.account_btn.clicked.connect(self.show_login_dialog)
        nav.addWidget(self.account_btn)
        
        # 설정 버튼
        settings_btn = QPushButton()
        settings_btn.setIcon(QIcon(str(resource_path("assets/images/settings.svg"))))
        settings_btn.setIconSize(DEFAULT_ICON_SIZE)
        settings_btn.setProperty("class", "icon-button")
        settings_btn.clicked.connect(self.show_settings)
        nav.addWidget(settings_btn)
        
        layout.addLayout(nav)
        return header
    
    def create_status_cards(self):
        """서버 상태, 온라인, 버전 카드 생성"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(CARD_SPACING)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 서버 상태
        status_card = Card()
        status_card.setObjectName("status_card")
        status_card.setProperty("class", "base-card status-card status-card-green")
        
        status_layout = QVBoxLayout()
        status_layout.setSpacing(5)
        status_layout.setContentsMargins(*CARD_MARGINS)
        
        title = self.create_label("서버 상태", "title")
        self.status_label = self.create_label("온라인", "status-value-online")
        self.realm_name = self.create_label("WISE 시즌 2", "subtitle")
        
        status_layout.addWidget(title)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.realm_name)
        status_card.layout.addLayout(status_layout)
        
        # 온라인
        online_card = Card()
        online_card.setProperty("class", "status-card status-card-blue")
        
        online_layout = QVBoxLayout()
        online_layout.setSpacing(5)
        online_layout.setContentsMargins(*CARD_MARGINS)
        
        online_title = self.create_label("온라인 플레이어", "title")
        
        self.online_count = self.create_label("1500", "value")
        
        self.online_trend = self.create_label("↑ 시간당 +125", "trend-up")
        
        online_layout.addWidget(online_title)
        online_layout.addWidget(self.online_count)
        online_layout.addWidget(self.online_trend)
        online_card.layout.addLayout(online_layout)
        
        # 버전
        version_card = Card()
        version_card.setProperty("class", "status-card status-card-purple")
        
        version_layout = QVBoxLayout()
        version_layout.setSpacing(5)
        version_layout.setContentsMargins(*CARD_MARGINS)
        
        version_title = self.create_label("버전", "title")
        
        version_number = self.create_label("3.3.5a", "value")
        
        build_number = self.create_label("12340", "subtitle")
        
        version_layout.addWidget(version_title)
        version_layout.addWidget(version_number)
        version_layout.addWidget(build_number)
        version_card.layout.addLayout(version_layout)
        
        # 레이아웃에 카드 추가
        layout.addWidget(status_card)
        layout.addWidget(online_card)
        layout.addWidget(version_card)
        layout.addStretch()
        
        return widget
    
    def create_news_section(self):
        """뉴스 섹션 생성"""
        news_widget = QWidget()
        layout = QVBoxLayout(news_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 섹션 제목
        title = QLabel("뉴스")
        title.setProperty("class", "section-title")
        layout.addWidget(title)
        
        # 뉴스 그리드
        news_grid = QGridLayout()
        news_grid.setSpacing(20)
        
        # 메인 뉴스
        main_news = self.create_news_card(
            "업데이트 3.3.5a",
            "패치 3.3.5a가 설치되었습니다...",
            str(resource_path("assets/images/news/main_news.jpg")),
            True
        )
        news_grid.addWidget(main_news, 0, 0, 1, 2)
        
        # 추가 뉴스
        news1 = self.create_news_card(
            "아레나 오픈",
            "새로운 아레나 시즌...",
            str(resource_path("assets/images/news/arena_news.jpg")),
        )
        news_grid.addWidget(news1, 1, 0)
        
        news2 = self.create_news_card(
            "새로운 아이템",
            "새로운 아이템이 추가되었습니다...",
            str(resource_path("assets/images/news/items_news.jpg")),
        )
        news_grid.addWidget(news2, 1, 1)
        
        layout.addLayout(news_grid)
        return news_widget
    
    def create_news_card(self, title, text, image_path, tag=None, is_main=False):
        card = QFrame()
        card.setProperty("class", "news-card")
        
        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        
        # 태그 (있는 경우)
        if tag:
            tag_label = QLabel(tag)
            tag_label.setProperty("class", "news-tag")
            tag_label.adjustSize()
            tag_label.setContentsMargins(8, 2, 8, 2)
            layout.addWidget(tag_label)
        
        # 제목
        title_label = QLabel(title)
        title_label.setProperty("class", "news-title")
        if is_main:
            title_label.setProperty("main", "true")
        layout.addWidget(title_label)
        
        # 텍스트
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setProperty("class", "news-text")
        layout.addWidget(text_label)
        
        layout.addStretch()
        return card
    
    def create_footer(self):
        # 이 메서드는 더 이상 필요하지 않음, __init__에서 푸터 생성
        pass
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateBackground()
    
    def updateBackground(self):
        # 창 크기 가져오기
        window_size = self.size()
        
        # 이미지가 창 전체를 덮도록 스케일링
        scaled_bg = self.background.scaled(
            window_size.width() + 50,  # 너비에 약간의 여유 추가
            window_size.height() + 50,  # 높이에도 여유 추가하여 빈 가장자리 방지
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # 이미지가 창보다 크면 중앙을 기준으로 자르기
        if scaled_bg.width() > window_size.width() or scaled_bg.height() > window_size.height():
            x = (scaled_bg.width() - window_size.width()) // 2
            y = (scaled_bg.height() - window_size.height()) // 2
            scaled_bg = scaled_bg.copy(
                x, y, 
                window_size.width(), 
                window_size.height()
            )
        
        # 배경 설정
        palette = self.palette()
        palette.setBrush(QPalette.Window, QBrush(scaled_bg))
        self.setPalette(palette)
    
    def pulse_play_button(self):
        self.play_button.setProperty("class", "play-button-pulse")
    
    def load_settings(self):
        """파일에서 설정 로드"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"설정 로드 오류: {e}")
                return self.default_settings.copy()
        return self.default_settings.copy()
    
    def save_settings(self):
        """파일에 설정 저장"""
        try:
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"설정을 저장할 수 없습니다.\n[Errno {e.errno}] {e.strerror}: '{e.filename}'")

    def get_setting(self, category, key):
        """카테고리와 키로 설정 값 가져오기"""
        return self.settings.get(category, {}).get(key, self.default_settings[category][key])
    
    def set_setting(self, category, key, value):
        """설정 값 설정"""
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
        self.save_settings()
    
    def show_settings(self):
        """설정 창 표시"""
        dialog = SettingsDialog(self)
        dialog.exec()

    def create_label(self, text, class_name, additional_props=None):
        """지정된 클래스로 스타일링된 QLabel 생성
        
        Args:
            text (str): 라벨 텍스트
            class_name (str): 스타일을 위한 클래스 이름
            additional_props (dict, optional): 추가 속성
            
        Returns:
            QLabel: 생성된 라벨
        """
        label = QLabel(text)
        label.setProperty("class", class_name)
        if additional_props:
            for key, value in additional_props.items():
                label.setProperty(key, value)
        return label

    def _on_server_status_updated(self, status_data):
        """서버 상태 시그널을 받아 UI를 업데이트하는 슬롯"""
        if status_data:
            online = status_data['online']
            status_text = status_data['status_text']
            
            # 상태 텍스트 및 스타일 업데이트
            self.status_label.setText(status_text)
            self.status_label.setProperty(
                "class", 
                "status-value-online" if online else "status-value-offline"
            )
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            
            # 상태 카드 스타일 업데이트
            status_card = self.findChild(Card, "status_card")
            if status_card:
                new_class = f"base-card status-card {'status-card-green' if online else 'status-card-red'}"
                status_card.setProperty("class", new_class)
                status_card.style().unpolish(status_card)
                status_card.style().polish(status_card)
                status_card.update()
            
            self.realm_name.setText(status_data['realm_name'])
            self.online_count.setText(str(status_data['players_online']))
            self.online_trend.setText(f"↑ {status_data['players_online']} / {status_data['max_players']}")
        else:
            self.status_label.setText("사용 불가")
            self.status_label.setProperty("class", "status-value-offline")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            
            # 카드 스타일을 빨간색으로 업데이트
            status_card = self.findChild(Card, "status_card")
            if status_card:
                status_card.setProperty("class", "base-card status-card status-card-red")
                status_card.style().unpolish(status_card)
                status_card.style().polish(status_card)

    def update_server_status(self):
        """서버 상태 정보 업데이트"""
        async def get_status():
            status = await self.server_api.get_server_status()
            status_data = {}
            if status:
                online = status.auth_online and status.world_online
                
                if online:
                    status_text = "온라인"
                elif not status.auth_online and not status.world_online:
                    status_text = "오프라인"
                elif not status.auth_online:
                    status_text = "인증 서버 오프라인"
                else:
                    status_text = "월드 서버 오프라인"

                status_data = {
                    'online': online,
                    'status_text': status_text,
                    'realm_name': status.realm_name,
                    'players_online': status.players_online,
                    'max_players': status.max_players,
                }
            # 메인 스레드로 데이터 전송
            self.server_status_updated.emit(status_data)

        # 이벤트 루프에서 비동기 작업 실행
        future = asyncio.run_coroutine_threadsafe(get_status(), self.loop)
        future.add_done_callback(lambda f: self.handle_status_update_error(f))

    def handle_status_update_error(self, future):
        """상태 업데이트 오류 처리"""
        try:
            future.result()
        except Exception as e:
            print(f"서버 상태 업데이트 오류: {e}")

    def show_login(self):
        """인증 대화 상자 표시"""
        dialog = LoginDialog(self.loop, self)
        if dialog.exec_():
            # 성공적인 인증
            self.current_user = dialog.auth_result
            self.update_ui_after_login()
    
    def update_ui_after_login(self):
        """성공적인 인증 후 UI 업데이트"""
        self.game_button.setEnabled(True)
        self.update_account_info()
        
    def update_account_info(self):
        """UI의 계정 정보 업데이트"""
        if self.current_user:
            # 계정 버튼 업데이트
            self.account_btn.setText(self.current_user.username)
            self.account_btn.setProperty("class", "account-button")
            
            # 스타일 업데이트
            self.account_btn.style().unpolish(self.account_btn)
            self.account_btn.style().polish(self.account_btn)
            
            # 계정 메뉴 업데이트
            self.create_account_menu()
    
    def create_account_menu(self):
        """계정 메뉴 생성"""
        menu = QMenu(self)
        menu.setProperty("class", "account-menu")
        
        if self.current_user:
            # 계정 정보 추가
            account_info = QAction(f"계정: {self.current_user.username}", self)
            account_info.setEnabled(False)
            menu.addAction(account_info)
            
            menu.addSeparator()
            
            # 로그아웃 버튼
            logout = QAction("로그아웃", self)
            logout.triggered.connect(self.logout)
            menu.addAction(logout)
        else:
            # 로그인 버튼
            login = QAction("로그인", self)
            login.triggered.connect(self.show_login)
            menu.addAction(login)
        
        return menu

    def logout(self):
        """계정에서 로그아웃"""
        # 인증 데이터 지우기
        self.settings['auth']['username'] = None
        self.settings['auth']['account_id'] = None
        self.settings['auth']['auto_login'] = False
        self.settings['auth']['saved_password'] = ""
        
        # 설정 저장
        self.save_settings()
        
        # current_user 초기화
        self.current_user = None
        
        # UI 업데이트
        self.account_btn.setText("로그인")
        self.account_btn.setProperty("class", "login-button")
        self.account_btn.setMenu(None)
        
        # 시그널 재연결
        try:
            self.account_btn.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass # 연결이 없는 경우 오류 무시
        self.account_btn.clicked.connect(self.show_login_dialog)

        # 스타일 새로고침
        self.account_btn.style().unpolish(self.account_btn)
        self.account_btn.style().polish(self.account_btn)

        # 게임 시작 버튼 비활성화
        self.play_button.setEnabled(False)
        
        # GameLauncher에서 데이터 지우기
        self.game_launcher.set_account_info(None, None)

    def show_login_dialog(self):
        """인증 대화 상자 표시"""
        if not self.current_user:  # 사용자가 인증되지 않은 경우
            dialog = LoginDialog(self.loop, self)
            if dialog.exec_():
                # 성공적인 인증
                self.current_user = dialog.auth_result
                self.update_ui_after_login()
        else:  # 사용자가 이미 인증된 경우
            self.show_account_menu()

    def show_account_menu(self):
        """계정 메뉴 표시"""
        menu = QMenu(self)
        menu.setProperty("class", "account-menu")
        
        # 계정 정보 추가
        account_info = QAction(f"계정: {self.current_user.username}", menu)
        account_info.setEnabled(False)
        menu.addAction(account_info)
        
        menu.addSeparator()
        
        # 작업 추가
        logout = QAction("로그아웃", menu)
        logout.triggered.connect(self.logout)
        menu.addAction(logout)
        
        # 버튼 아래에 메뉴 표시
        menu.exec_(self.account_btn.mapToGlobal(
            QPoint(0, self.account_btn.height())
        ))

    def create_nav_button(self, text: str, icon_path: str) -> QPushButton:
        """내비게이션 버튼 생성"""
        btn = QPushButton(text)
        btn.setIcon(QIcon(icon_path))
        btn.setIconSize(DEFAULT_ICON_SIZE)
        btn.setProperty("class", "nav-button")
        return btn

    async def request_game_access(self):
        """백엔드에 게임 접속을 요청하고 (성공 여부, 메시지) 튜플을 반환합니다."""
        if not self.current_user:
            return False, "로그인이 필요합니다."

        url = "http://127.0.0.1:5000/api/request-game-access"
        payload = {"username": self.current_user.username}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=5) as response:
                    if response.status == 200:
                        print(f"성공적으로 게임 접속을 요청했습니다: {self.current_user.username}")
                        return True, "Success"
                    else:
                        error_text = await response.text()
                        return False, f"게임 접속 요청에 실패했습니다. (상태: {response.status})\n{error_text}"
        except aiohttp.ClientError as e:
            return False, f"백엔드 서버에 연결할 수 없습니다.\n{e}"

    async def launch_game(self):
        """실행 버튼 클릭 핸들러"""
        if not self.current_user:
            self.game_launcher.signals.login_required.emit()
            return

        # --- 1. UI를 "검사 중" 상태로 설정 ---
        self._setup_ui_for_verification()

        try:
            # --- 2. 실제 검증 및 실행 로직 ---
            if not self.game_launcher.validate_game_path(self.settings.get('game', {}).get('path', '')):
                self.game_launch_error.emit("오류", "잘못된 게임 경로입니다. 설정을 확인하세요.")
                return

            access_granted, message = await self.request_game_access()
            if not access_granted:
                self.game_launch_error.emit("접속 오류", message)
                return

            if self.current_user:
                self.game_launcher.set_account_info(
                    self.current_user.username,
                    self.current_user.account_id
                )

            verified, message = await self.loop.run_in_executor(None, self.game_launcher.verify_data_files)
            if not verified:
                self.game_launch_error.emit("파일 오류", message)
                return
            
            if self.game_launcher.launch_game():
                self.game_launch_success.emit()
            else:
                self.game_launch_error.emit("오류", "게임을 시작할 수 없습니다. 설정과 게임 파일을 확인하세요.")

        finally:
            # --- 3. UI를 원래 상태로 복원 ---
            self._reset_ui_after_verification()

    def handle_game_launch_success(self):
        """게임 실행 성공 시그널을 처리하는 슬롯"""
        self.showMinimized()

    def handle_game_launch_error(self, title, message):
        """게임 실행 오류 시그널을 처리하는 슬롯"""
        QMessageBox.critical(self, title, message)

    def handle_login_required(self):
        """로그인 필요 시그널을 처리하는 슬롯"""
        QMessageBox.warning(self, "로그인 필요", "게임을 시작하려면 먼저 로그인해야 합니다.")
        self.show_login_dialog()

    def show_download_buttons(self):
        """클라이언트 다운로드 버튼 표시"""
        self.play_button.hide()
        
        # 푸터에 버튼 생성
        self.download_button = QPushButton("클라이언트 다운로드")
        self.download_button.setObjectName("download-button")
        self.download_button.clicked.connect(self.start_download)
        
        self.select_folder_button = QPushButton("폴더 선택")
        self.select_folder_button.setObjectName("select-folder-button")
        self.select_folder_button.clicked.connect(self.select_game_folder)
        
        # 푸터에 추가
        self.footer_layout.insertWidget(1, self.download_button)
        self.footer_layout.insertWidget(2, self.select_folder_button)
        
    def show_download_progress(self):
        """다운로드 진행률 표시"""
        self.game_button.setEnabled(False)
        self.game_button.setText("다운로드 중...")
        self.game_button.setProperty("state", "downloading")
        
        # 진행률 표시줄 생성 및 추가
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("download-progress")
        self.progress_bar.setFixedHeight(40)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.footer_layout.insertWidget(1, self.progress_bar)
        
        # 스타일 업데이트
        self.game_button.style().unpolish(self.game_button)
        self.game_button.style().polish(self.game_button)

    def update_download_progress(self, progress: float, status: str, speed: float):
        """다운로드 진행률 업데이트"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(int(progress))
            speed_str = humanize.naturalsize(speed, binary=True) + "/s"
            self.progress_bar.setFormat(f"{status} - {speed_str}")

    def on_download_error(self, error_msg: str):
        """다운로드 오류 핸들러"""
        self.hide_download_progress()
        QMessageBox.critical(self, "다운로드 오류", error_msg)

    def handle_game_launch_error(self, title, message):
        """게임 실행 오류 시그널을 처리하는 슬롯"""
        QMessageBox.critical(self, title, message)

    def _setup_ui_for_verification(self):
        """파일 검사를 위해 UI를 설정합니다."""
        self.game_button.setEnabled(False)
        self.game_button.setText("파일 검사 준비 중...")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("verification-progress")
        self.progress_bar.setFixedHeight(40)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False) # 텍스트는 버튼에 표시

        self.verification_status_label = QLabel("대기 중...")
        self.verification_status_label.setObjectName("verification-label")
        
        # 푸터에 위젯 추가 (버튼은 이미 있음)
        self.footer_layout.insertWidget(1, self.verification_status_label)
        self.footer_layout.insertWidget(2, self.progress_bar)

    def _reset_ui_after_verification(self):
        """파일 검사 후 UI를 원래 상태로 복원합니다."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.hide()
            self.progress_bar.deleteLater()
            del self.progress_bar
        if hasattr(self, 'verification_status_label'):
            self.verification_status_label.hide()
            self.verification_status_label.deleteLater()
            del self.verification_status_label
            
        self.game_button.setEnabled(True)
        self.game_button.setText("게임 시작")

    def update_verification_progress(self, progress: float, filename: str):
        """파일 검증 진행률을 업데이트합니다."""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(int(progress))
            self.game_button.setText(f"파일 검사 중... ({int(progress)}%)")
            self.verification_status_label.setText(f"검사 파일: {filename}")

    def setup_game_button(self):
        """메인 게임/다운로드 버튼 설정"""
        self.game_button = QPushButton()
        self.game_button.setObjectName("game-button")
        
        # 버튼 상태 업데이트
        self.update_game_button_state()
        
        # 푸터에 추가
        self.footer_layout.addWidget(self.game_button)

    def on_tray_icon_activated(self, reason):
        """트레이 아이콘 클릭 핸들러"""
        if reason == QSystemTrayIcon.Trigger:  # 일반 클릭
            self.show_normal()

    async def launch_game_from_tray(self):
        """트레이에서 게임 시작"""
        if not self.current_user:
            self.show_normal()
            self.game_launcher.signals.login_required.emit()
            return

        if not self.game_launcher.validate_game_path(self.settings.get('game', {}).get('path', '')):
            self.show_normal()
            QMessageBox.warning(
                self,
                "오류", 
                "잘못된 게임 경로입니다. 설정을 확인하세요."
            )
            return

        # 백엔드에 게임 접속 요청
        access_granted = await self.request_game_access()
        if not access_granted:
            self.show_normal() # 오류 발생 시 창 표시
            return
            
        if self.current_user:
            self.game_launcher.set_account_info(
                self.current_user.username,
                self.current_user.account_id
            )
            
        if self.game_launcher.launch_game():
            self.hide()
            self.tray_icon.show()

    def update_game_button_state(self):
        """클라이언트 유무에 따라 버튼 상태 업데이트"""
        # 이전 연결 안전하게 해제
        try:
            if self.game_button.receivers(self.game_button.clicked) > 0:
                self.game_button.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass  # 연결 해제 오류 무시
            
        if not self.settings['game']['path']:
            # 선택된 폴더 없음
            self.game_button.setText("폴더 선택")
            self.game_button.setProperty("state", "select")
            self.game_button.clicked.connect(self.select_game_folder)
            
        elif not self.game_launcher.validate_game_path(self.settings['game']['path']):
            # 폴더는 선택되었지만 클라이언트 없음
            self.game_button.setText("클라이언트 다운로드")
            self.game_button.setProperty("state", "download")
            self.game_button.clicked.connect(self.start_download)
            
        else:
            # 클라이언트 발견됨
            self.game_button.setText("게임 시작")
            self.game_button.setProperty("state", "play")
            self.game_button.clicked.connect(lambda: asyncio.run_coroutine_threadsafe(self.launch_game(), self.loop))

        # 스타일 업데이트
        self.game_button.style().unpolish(self.game_button)
        self.game_button.style().polish(self.game_button)

    def open_download_page(self):
        """클라이언트 다운로드 웹페이지 열기"""
        webbrowser.open("http://naver.me/5uIKMWKH")

    def open_homepage(self):
        """홈페이지 열기"""
        # 나중에 변경필요
        webbrowser.open("http://127.0.0.1")

    def start_download(self):
        """클라이언트 다운로드 시작"""
        try:
            self.game_launcher._download_client()
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))
            
    def select_game_folder(self):
        """게임 폴더 선택 대화 상자 열기"""
        path = QFileDialog.getExistingDirectory(
            self,
            "게임 폴더를 선택하세요",
            dir="C:\\WISE\\WOW335"
        )
        if path:
            self.settings['game']['path'] = path
            self.save_settings()
            # 새 경로 확인 및 버튼 상태 업데이트
            self.game_launcher.validate_game_path(path)
            self.update_game_button_state()

    def show_login_required_message(self):
        """로그인 필요 메시지 표시"""
        QMessageBox.warning(self, "로그인 필요", "게임을 시작하려면 먼저 로그인해야 합니다.")
        self.show_login_dialog()

    def on_login_success(self, result: AuthResult):
        """성공적인 인증 핸들러"""
        self.current_user = result
        self.settings['auth']['username'] = result.username
        self.settings['auth']['account_id'] = result.account_id
        self.save_settings()

    def start_game_monitoring(self):
        """게임 프로세스 모니터링 시작"""
        self.game_monitor_timer = QTimer()
        self.game_monitor_timer.timeout.connect(self.check_game_running)
        self.game_monitor_timer.start(5000)  # 5초마다 확인

    def check_game_running(self):
        """게임이 실행 중인지 확인"""
        if not self.game_launcher.is_game_running():
            self.game_monitor_timer.stop()
            self.tray_icon.hide()  # 아이콘 숨기기
            self.showNormal()  # 창 복원

    def show_normal(self):
        """트레이에서 창 복원"""
        self.showNormal()
        self.activateWindow()

    def closeEvent(self, event):
        """애플리케이션 종료 이벤트 핸들러"""
        # 이벤트 루프 정리
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        # 트레이 아이콘 숨기기
        self.tray_icon.hide()
        
        # 기본 종료 이벤트 수락
        event.accept()

class SettingsDialog(QDialog):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.settings = main_window.settings.copy()
        self.game_launcher = main_window.game_launcher
        self.setup_ui()
    
    def browse_directory(self, line_edit, title):
        """폴더 선택 대화 상자 열기"""
        path = QFileDialog.getExistingDirectory(self, title)
        if path:
            line_edit.setText(path)
            # 게임 경로인 경우 클라이언트 유무 확인
            if line_edit.objectName() == "game_path":
                if not self.game_launcher.validate_game_path(path):
                    QMessageBox.warning(
                        self,
                        "클라이언트 없음",
                        "지정된 폴더에 WoW 클라이언트가 없습니다. "
                        "설정을 저장하면 다운로드하라는 메시지가 표시됩니다."
                    )
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 탭 생성
        tabs = QTabWidget()
        tabs.addTab(self.create_game_tab(), "게임")
        tabs.addTab(self.create_graphics_tab(), "그래픽")
        tabs.addTab(self.create_addons_tab(), "애드온")
        
        layout.addWidget(tabs)
        
        # 버튼
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.setSpacing(10)
        
        save_btn = QPushButton("저장")
        save_btn.setObjectName("save_button")
        save_btn.setProperty("class", "save-button")
        save_btn.setFixedHeight(40)
        
        cancel_btn = QPushButton("취소")
        cancel_btn.setObjectName("cancel_button")
        cancel_btn.setProperty("class", "cancel-button")
        cancel_btn.setFixedHeight(40)
        
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        
        layout.addLayout(buttons)
        
        # 시그널 연결
        save_btn.clicked.connect(self.save_settings)
        cancel_btn.clicked.connect(self.reject)
    
    def create_game_tab(self):
        tab = QWidget()
        tab.setObjectName("game_tab")  # 검색을 위한 ID 추가
        layout = QVBoxLayout(tab)
        
        # Linux용 설정 그룹
        if platform.system().lower() == 'linux':
            linux_group = QGroupBox("Linux 설정")
            linux_layout = QVBoxLayout(linux_group)
            
            # 에뮬레이터 선택
            runner_label = QLabel("에뮬레이터:")
            runner_combo = QComboBox()
            runner_combo.setObjectName("runner_combo")  # 검색을 위한 ID 추가
            runner_combo.setProperty("class", "settings-combobox")
            runner_combo.addItems(["wine", "lutris", "proton", "portproton"])
            runner_combo.setCurrentText(self.settings.get('game', {}).get('runner', 'wine'))
            
            # WINEPREFIX
            prefix_label = QLabel("WINEPREFIX:")
            prefix_input = QLineEdit()
            prefix_input.setObjectName("prefix_input")  # 검색을 위한 ID 추가
            prefix_input.setProperty("class", "settings-input")
            prefix_input.setText(self.settings.get('game', {}).get('wineprefix', ''))
            
            # WINEPREFIX 선택 버튼
            prefix_browse = QPushButton("찾아보기")
            prefix_browse.setProperty("class", "browse-button")
            prefix_browse.clicked.connect(lambda: self.browse_directory(prefix_input, "WINEPREFIX를 선택하세요"))
            
            prefix_layout = QHBoxLayout()
            prefix_layout.addWidget(prefix_input)
            prefix_layout.addWidget(prefix_browse)
            
            linux_layout.addWidget(runner_label)
            linux_layout.addWidget(runner_combo)
            linux_layout.addWidget(prefix_label)
            linux_layout.addLayout(prefix_layout)
            
            layout.addWidget(linux_group)
        
        # 게임 경로
        path_label = QLabel("게임 경로:")
        path_input = QLineEdit()
        path_input.setObjectName("game_path")  # 검색을 위한 ID 추가
        path_input.setProperty("class", "settings-input")
        path_input.setText(self.settings.get('game', {}).get('path', ''))
        
        # 경로 선택 버튼
        path_browse = QPushButton("찾아보기")
        path_browse.setProperty("class", "browse-button")
        path_browse.clicked.connect(lambda: self.browse_directory(path_input, "게임 폴더를 선택하세요"))
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(path_input)
        path_layout.addWidget(path_browse)
        
        # 리얼름 목록
        realmlist_label = QLabel("리얼름 목록:")
        realmlist_input = QLineEdit()
        realmlist_input.setObjectName("realmlist_input")  # 검색을 위한 ID 추가
        realmlist_input.setProperty("class", "settings-input")
        realmlist_input.setText(self.settings.get('game', {}).get('realmlist', '127.0.0.1'))
        
        # 실행 옵션
        launch_label = QLabel("실행 옵션:")
        launch_input = QLineEdit()
        launch_input.setObjectName("launch_options")  # 검색을 위한 ID 추가
        launch_input.setProperty("class", "settings-input")
        launch_input.setText(self.settings.get('game', {}).get('launch_options', ''))
        
        layout.addWidget(path_label)
        layout.addLayout(path_layout)
        layout.addWidget(realmlist_label)
        layout.addWidget(realmlist_input)
        layout.addWidget(launch_label)
        layout.addWidget(launch_input)
        
        return tab
    
    def create_graphics_tab(self):
        tab = QWidget()
        tab.setObjectName("graphics_tab")
        layout = QVBoxLayout(tab)
        
        # 화면 해상도
        self.resolution = QComboBox()
        self.resolution.setObjectName("resolution_combo")
        self.resolution.addItems(["1920x1080", "1600x900", "1366x768"])
        self.resolution.setProperty("class", "settings-combobox")
        self.resolution.setCurrentText(self.settings.get('graphics', {}).get('resolution', '1920x1080'))
        layout.addWidget(QLabel("해상도:"))
        layout.addWidget(self.resolution)
        
        # 그래픽 품질
        self.graphics = QComboBox()
        self.graphics.setObjectName("quality_combo")
        self.graphics.addItems(["낮음", "중간", "높음", "울트라"])
        self.graphics.setProperty("class", "settings-combobox")
        self.graphics.setCurrentText(self.settings.get('graphics', {}).get('quality', '높음'))
        layout.addWidget(QLabel("그래픽 품질:"))
        layout.addWidget(self.graphics)
        
        # 창 모드
        self.windowed = QCheckBox("창 모드")
        self.windowed.setObjectName("windowed_check")
        self.windowed.setProperty("class", "settings-checkbox")
        self.windowed.setChecked(self.settings.get('graphics', {}).get('windowed', False))
        layout.addWidget(self.windowed)
        
        layout.addStretch()
        return tab
    
    def create_addons_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("애드온 목록은 다음 업데이트에 제공될 예정입니다"))
        layout.addStretch()
        return tab
    
    def create_path_selector(self, label_text, button_text, line_edit):
        layout = QHBoxLayout()
        
        layout.addWidget(label_text)
        layout.addWidget(line_edit)
        
        browse_btn = QPushButton(button_text)
        browse_btn.setProperty("class", "browse-button")
        browse_btn.clicked.connect(lambda: self.browse_path(line_edit))
        layout.addWidget(browse_btn)
        
        return layout
    
    def browse_path(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, "폴더를 선택하세요")
        if path:
            line_edit.setText(path) 

    def save_settings(self):
        """설정 저장"""
        try:
            # 게임 탭에서 값 가져오기
            game_tab = self.findChild(QWidget, "game_tab")
            
            # 게임 경로
            game_path = game_tab.findChild(QLineEdit, "game_path").text()
            old_path = self.settings['game'].get('path', '')
            self.settings['game']['path'] = game_path
            
            # 경로가 변경된 경우 클라이언트 유무 확인
            if game_path != old_path:
                if not self.game_launcher.validate_game_path(game_path):
                    if QMessageBox.question(
                        self,
                        "클라이언트 없음",
                        "지정된 폴더에 WoW 클라이언트가 없습니다. 다운로드하시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No
                    ) == QMessageBox.Yes:
                        self.accept()  # 설정 닫기
                        self.main_window.show_download_buttons()
                        return
            
            # 리얼름 목록
            realmlist = game_tab.findChild(QLineEdit, "realmlist_input").text()
            old_realmlist = self.settings['game'].get('realmlist', '')
            self.settings['game']['realmlist'] = realmlist
            
            # 리얼름 목록 또는 게임 경로가 변경된 경우 파일 업데이트
            if (realmlist != old_realmlist or game_path != old_path) and game_path:
                if not self.game_launcher.update_realmlist(game_path, realmlist):
                    raise Exception("realmlist.wtf를 업데이트할 수 없습니다")
            
            # 실행 옵션
            launch_options = game_tab.findChild(QLineEdit, "launch_options").text()
            self.settings['game']['launch_options'] = launch_options
            
            # Linux 설정
            if platform.system().lower() == 'linux':
                runner = game_tab.findChild(QComboBox, "runner_combo").currentText()
                wineprefix = game_tab.findChild(QLineEdit, "prefix_input").text()
                
                self.settings['game']['runner'] = runner
                self.settings['game']['wineprefix'] = wineprefix
            
            # 그래픽 탭에서 값 가져오기
            graphics_tab = self.findChild(QWidget, "graphics_tab")
            if graphics_tab:
                resolution = graphics_tab.findChild(QComboBox, "resolution_combo").currentText()
                quality = graphics_tab.findChild(QComboBox, "quality_combo").currentText()
                windowed = graphics_tab.findChild(QCheckBox, "windowed_check").isChecked()

                self.settings['graphics']['resolution'] = resolution
                self.settings['graphics']['quality'] = quality
                self.settings['graphics']['windowed'] = windowed

            # 그래픽 탭에서 값 가져오기
            resolution = self.resolution.currentText()
            quality = self.graphics.currentText()
            windowed = self.windowed.isChecked()

            self.settings['graphics']['resolution'] = resolution
            self.settings['graphics']['quality'] = quality
            self.settings['graphics']['windowed'] = windowed

            # 설정 저장
            self.main_window.settings = self.settings
            self.main_window.save_settings()
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정을 저장할 수 없습니다: {str(e)}")