import sys
from pathlib import Path
import threading
import asyncio
import logging
from PySide6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow

# --- 단일 인스턴스 확인을 위한 코드 추가 ---
from win32event import CreateMutex, ReleaseMutex
from win32api import GetLastError
from winerror import ERROR_ALREADY_EXISTS

class SingleInstance:
    def __init__(self, mutex_name):
        self.mutex_name = mutex_name
        self.mutex = CreateMutex(None, 1, self.mutex_name)
        self.already_exists = (GetLastError() == ERROR_ALREADY_EXISTS)

    def __del__(self):
        if self.mutex:
            ReleaseMutex(self.mutex)
            self.mutex.Close()

def run_async_loop(loop_ready_event, window):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    window.loop = loop
    loop_ready_event.set()  # 이벤트 루프가 준비되었음을 알림
    loop.run_forever()

def main():
    try:
        app = QApplication(sys.argv)

        # Wow.exe 경로 확인
        wow_exe_path = Path(sys.executable).parent / "Wow.exe"
        if not wow_exe_path.is_file():
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setWindowTitle("오류")
            error_box.setText("Wow.exe 파일을 찾을 수 없습니다.")
            error_box.setInformativeText("런처를 Wow.exe가 있는 폴더로 이동시킨 후 다시 실행해주세요.")
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.exec()
            sys.exit(1)

        # --- 단일 인스턴스 확인을 위한 코드 추가 ---
        mutex_name = "WoWLauncher_Mutex_F2C2E5A8_704D_4A8F_A4E3_B5A9F6E8C9B1"
        instance = SingleInstance(mutex_name)

        if instance.already_exists:
            logging.warning("런처가 이미 실행 중입니다. 새 인스턴스를 종료합니다.")
            sys.exit(0)

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        app.instance = instance  # instance를 app 객체에 할당하여 프로그램 실행 내내 유지되도록 합니다.
        app.setStyle('Fusion')
        
        window = MainWindow()
        
        # 비동기 루프 스레드 준비
        loop_ready_event = threading.Event()
        thread = threading.Thread(target=run_async_loop, args=(loop_ready_event, window), daemon=True)
        thread.start()
        
        loop_ready_event.wait()

        window.update_server_status()
        window.show()
        
        sys.exit(app.exec())

    except Exception as e:
        import traceback
        with open('crash.log', 'w', encoding='utf-8') as f:
            f.write(f"An error occurred: {e}\n")
            traceback.print_exc(file=f)
        sys.exit(1)

if __name__ == "__main__":
    main()