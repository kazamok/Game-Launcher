import os
from subprocess import Popen, PIPE
from pathlib import Path
import logging
import platform
import shutil
import json
import hashlib
from PySide6.QtCore import QObject, Signal
from utils.resource_path import resource_path
# from utils.torrent_manager import TorrentManager

class GameLauncherSignals(QObject):
    client_missing = Signal()
    download_progress = Signal(float, str, float)
    download_error = Signal(str)
    login_required = Signal()
    verification_progress = Signal(float, str)  # percentage, filename

class GameLauncher:
    def __init__(self, settings: dict, parent=None):
        self.settings = settings
        self.parent = parent
        self.signals = GameLauncherSignals()
        self.logger = logging.getLogger('GameLauncher')
        self.platform = platform.system().lower()
        self.account_username = None
        self.account_id = None
        self.torrent_manager = None
        self.client_version = "3.3.5a"
        self.required_size = 17_179_869_184  # 16GB in bytes
        # 파일 경로 캐싱
        self.game_path = Path(settings.get('game', {}).get('path', ''))
        self.config_path = self.game_path / 'WTF' / 'Config.wtf'
        self.realmlist_paths = [
            self.game_path / 'Data' / 'koKR' / 'realmlist.wtf'
        ]
        self.client_info = None
        self.torrent_path = Path("assets/client/wow-3.3.5.torrent")
        self.trackers = [
            "udp://tracker1.example.com:6969/announce",
            "udp://tracker2.example.com:6969/announce"
        ]

    def validate_game_path(self, path: str) -> bool:
        """게임 경로의 유효성을 확인합니다"""
        if not path:
            self.signals.client_missing.emit()
            return False
            
        game_path = Path(path)
        
        required_files = [
            game_path / 'Wow.exe',
            game_path / 'Data/common.MPQ',
            game_path / 'Data/common-2.MPQ'
        ]
        
        try:
            # 각 파일 확인
            for required_file in required_files:
                if not required_file.exists():
                    self.logger.error(f"필수 파일 없음: {required_file}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"게임 경로 유효성 검사 오류: {e}")
            return False

    def verify_data_files(self) -> (bool, str):
        """Verifies the integrity of game files against a manifest using size and mtime first."""
        manifest_path = resource_path("config/manifest.json")
        if not manifest_path.exists():
            return False, "Manifest file (manifest.json) not found. Cannot verify files."

        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except Exception as e:
            return False, f"Error reading manifest file: {e}"

        data_path = self.game_path / "Data"
        total_files = len(manifest)
        checked_files = 0

        for relative_path, file_info in manifest.items():
            file_path = data_path / relative_path.replace('/', os.sep)
            
            checked_files += 1
            progress = (checked_files / total_files) * 100
            self.signals.verification_progress.emit(progress, relative_path)

            if not file_path.exists():
                error_msg = f"File is missing: Data\\{relative_path}"
                self.logger.error(error_msg)
                return False, error_msg

            try:
                file_stat = file_path.stat()
                # 1. Check size and modification time first for a quick check
                if file_stat.st_size == file_info["size"] and file_stat.st_mtime == file_info["mtime"]:
                    continue  # Skip hash check if size and mtime match

                # 2. If they don't match, perform the expensive hash check
                sha256_hash = hashlib.sha256()
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                current_hash = sha256_hash.hexdigest()

                if current_hash != file_info["hash"]:
                    error_msg = f"File is corrupt or has been modified: Data\\{relative_path}"
                    self.logger.error(error_msg)
                    return False, error_msg
            
            except IOError as e:
                error_msg = f"Could not read file for verification: {relative_path} ({e})"
                self.logger.error(error_msg)
                return False, error_msg
        
        return True, "All files verified successfully."

    def update_realmlist(self, path: str, realmlist: str) -> bool:
        """realmlist.wtf 파일을 업데이트합니다"""
        try:
            # 두 가지 가능한 경로 확인
            data_paths = [
                Path(path) / 'Data' / 'koKR' / 'realmlist.wtf'  # 한국어 로케일 경로
            ]
            
            # 기존 파일 업데이트 또는 새 파일 생성
            updated = False
            for data_path in data_paths:
                try:
                    data_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(data_path, 'w', encoding='utf-8') as f:
                        f.write(f'set realmlist {realmlist}\n')
                    updated = True
                except Exception as e:
                    self.logger.warning(f"{data_path}를 업데이트할 수 없습니다: {e}")
            
            return updated
        except Exception as e:
            self.logger.error(f"realmlist 업데이트 오류: {e}")
            return False

    def update_config_wtf(self, path: str) -> bool:
        """자동 로그인을 위해 Config.wtf 파일을 업데이트합니다"""
        try:
            # 설정에서 realmlist 가져오기
            realmlist = self.settings.get('game', {}).get('realmlist', '127.0.0.1')
            
            config_path = Path(path) / 'WTF' / 'Config.wtf'
            
            # WTF 디렉토리가 없으면 생성
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 기존 설정 읽기
            config = {}
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('SET '):
                            key, value = line[4:].strip().split(' ', 1)
                            config[key] = value.strip('"')
            
            # 설정 업데이트
            if self.account_username:
                # 자동 로그인 및 계정 이름 미리 채우기 설정
                config['lastAccountName'] = self.account_username.upper()
                config['accountName'] = self.account_username.upper()

            # 드롭다운 목록을 유발하는 설정들을 제거합니다.
            config.pop('accountList', None)
            config.pop('savedAccountList', None)
            
            # 그래픽 설정 업데이트
            graphics_settings = self.settings.get('graphics', {})
            quality_map = {"낮음": "0", "중간": "1", "높음": "2", "울트라": "3"}
            if 'quality' in graphics_settings:
                config['gxFixLag'] = "0"
                config['gxquality'] = quality_map.get(graphics_settings['quality'], "2")
            if 'windowed' in graphics_settings:
                config['gxWindow'] = "1" if graphics_settings['windowed'] else "0"
            if 'resolution' in graphics_settings:
                config['gxResolution'] = graphics_settings['resolution']

            # 다른 중요한 설정이 없으면 추가
            defaults = {
                'locale': 'koKR', # 로케일 한국어로 변경
                'readTOS': '1',
                'readEULA': '1',
                'readTerminationWithoutNotice': '1',
                'accounttype': 'LK',
                'lastSelectedRealm': '1',  # 마지막으로 선택한 리얼름 인덱스
                'realmList': realmlist,  # 서버 주소
                'patchlist': f"'{realmlist}'",  # 패치 서버 주소
                'accountListType': "1",  # 계정 목록 유형
                'autoSelect': "1",  # 계정 자동 선택
                'autoConnect': "1"  # 자동 연결
            }
            
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value
            
            # 업데이트된 설정 쓰기
            with open(config_path, 'w', encoding='utf-8') as f:
                for key, value in config.items():
                    # 값이 숫자인 경우 따옴표 없이 씀
                    if value.replace('.', '').isdigit():
                        f.write(f'SET {key} {value}\n')
                    else:
                        f.write(f'SET {key} "{value}"\n')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Config.wtf 업데이트 오류: {e}")
            return False

    def set_account_info(self, username: str, account_id: int):
        """자동 로그인을 위한 계정 데이터 설정"""
        self.account_username = username
        self.account_id = account_id

    def launch_game(self) -> bool:
        """지정된 매개변수로 게임 시작"""
        try:
            game_path = self.settings.get('game', {}).get('path', '')
            if not game_path or not self.validate_game_path(game_path):
                self.logger.error("잘못된 게임 경로")
                return False

            # realmlist 업데이트
            realmlist = self.settings.get('game', {}).get('realmlist', '127.0.0.1')
            if not self.update_realmlist(game_path, realmlist):
                return False

            # 자동 로그인을 위해 Config.wtf 업데이트
            if self.account_username and not self.update_config_wtf(game_path):
                return False

            # 실행 파일 경로 생성
            exe_path = str(Path(game_path) / 'Wow.exe')

            # 시작 매개변수 생성
            launch_options = self.settings.get('game', {}).get('launch_options', '').split()
            
            # 그래픽 매개변수 추가
            graphics = self.settings.get('graphics', {})
            if graphics.get('windowed', False):
                launch_options.append('-windowed')
            
            resolution = graphics.get('resolution', '1920x1080')
            if resolution:
                width, height = resolution.split('x')
                launch_options.extend(['-width', width, '-height', height])

            # 프로세스 시작
            if self.platform == 'linux':
                try:
                    runner = self.settings.get('game', {}).get('runner', 'wine')
                    
                    if runner == 'portproton':
                        cmd = ['portproton', exe_path] + launch_options
                    elif runner == 'wine':
                        cmd = ['wine', exe_path] + launch_options
                    elif runner == 'lutris':
                        cmd = ['lutris', 'rungame', exe_path] + launch_options
                    elif runner == 'proton':
                        cmd = ['proton', 'run', exe_path] + launch_options
                    elif runner == 'crossover':
                        cmd = ['crossover', exe_path] + launch_options
                    else:
                        raise RuntimeError(f"알 수 없는 에뮬레이터: {runner}")
                      
                    # Wine 환경 변수 추가
                    env = os.environ.copy()
                    if self.settings.get('game', {}).get('wineprefix'):
                        env['WINEPREFIX'] = self.settings['game']['wineprefix']
                    env['WINEARCH'] = 'win32'
                      
                    # 프로세스 시작
                    Popen(cmd, env=env)
                    
                except Exception as e:
                    self.logger.error(f"Wine으로 시작 중 오류: {e}")
                    return False
                    
            elif self.platform == 'darwin':
                Popen(['open', exe_path, '--args'] + launch_options)
            else:
                Popen([exe_path] + launch_options)
                
            return True

        except Exception as e:
            self.logger.error(f"게임 시작 오류: {e}")
            return False 

    def _check_free_space(self, path: str) -> bool:
        """사용 가능한 공간이 충분한지 확인"""
        try:
            free_space = shutil.disk_usage(path).free
            return free_space >= self.required_size
        except Exception as e:
            self.logger.error(f"사용 가능한 공간 확인 오류: {e}")
            return False

    def _verify_client_files(self, path: str) -> tuple[bool, list[str]]:
        """클라이언트 파일 무결성 확인"""
        missing_files = []
        game_path = Path(path)
        
        # 중요한 파일 및 해당 MD5 목록
        required_files = {
            'Wow.exe': 'expected_md5_1',
            'Data/common.MPQ': 'expected_md5_2',
            'Data/common-2.MPQ': 'expected_md5_3',
            'Data/expansion.MPQ': 'expected_md5_4',
            'Data/lichking.MPQ': 'expected_md5_5',
            'Data/patch.MPQ': 'expected_md5_6',
        }
        
        for file_path, expected_md5 in required_files.items():
            full_path = game_path / file_path
            if not full_path.exists():
                missing_files.append(file_path)
                continue
                
            # TODO: MD5 확인 추가
        
        return len(missing_files) == 0, missing_files

    async def _get_client_info(self):
        """서버에서 클라이언트 정보 가져오기"""
        if not self.client_info:
            self.client_info = await self.server_api.get_client_info()
        return self.client_info
        
    def _verify_client_version(self, path: str) -> bool:
        """클라이언트 버전 확인"""
        try:
            exe_path = Path(path) / "Wow.exe"
            if not exe_path.exists():
                return False
                
            # TODO: exe에서 버전 확인 추가
            return True
        except Exception as e:
            self.logger.error(f"클라이언트 버전 확인 오류: {e}")
            return False

    def is_game_running(self) -> bool:
        """게임이 실행 중인지 확인"""
        if self.platform == 'linux':
            # Linux의 경우 wine 프로세스 확인
            try:
                result = subprocess.run(['pgrep', '-f', 'Wow.exe'], 
                                      stdout=subprocess.PIPE)
                return result.returncode == 0
            except:
                return False
        else:
            # Windows의 경우 Wow.exe 프로세스 확인
            try:
                result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe'],
                                      stdout=subprocess.PIPE)
                return b"Wow.exe" in result.stdout
            except:
                return False

    def _download_client(self):
        """클라이언트 다운로드 시작"""
        try:
            if not self.torrent_path.exists():
                raise RuntimeError("토렌트 파일을 찾을 수 없습니다")

            # 사용 가능한 공간 확인
            if not self._check_free_space(self.settings['game']['path']):
                raise RuntimeError("사용 가능한 공간이 부족합니다")

            # 디렉토리가 없으면 생성
            Path(self.settings['game']['path']).mkdir(parents=True, exist_ok=True)

            # TorrentManager 초기화
            if not self.torrent_manager:
                # self.torrent_manager = TorrentManager()
                pass

            # 푸터에 진행률 표시
            self.signals.download_progress.emit(0, '', 0)

            # 다운로드 시작
            # self.torrent_manager.start_download(
            #     torrent_path=str(self.torrent_path),
            #     save_path=self.settings['game']['path'],
            #     trackers=self.trackers,
            #     status_callback=lambda s: self.signals.download_progress.emit(
            #         s.progress, s.state, s.speed
            #     )
            # )
            pass

        except Exception as e:
            self.logger.error(f"클라이언트 다운로드 오류: {e}")
            self.signals.download_error.emit(str(e))
            raise