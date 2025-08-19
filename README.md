![스크린샷](images/screenshot.jpg)

# WoW 3.3.5 런처

AzerothCore를 지원하는 World of Warcraft 3.3.5a용 최신 런처입니다.

## 기능

- 🎮 현대적인 사용자 인터페이스
- 🔄 실시간 서버 상태 표시
- 👥 SRP6를 지원하는 인증 시스템
- ⚙️ 유연한 게임 설정
- 📰 뉴스 시스템
- 🚀 빠른 게임 실행

## 요구 사항

- Python 3.8+
- PySide6
- MySQL 서버 (AzerothCore 연동)

## 설치

1. 저장소 복제:
```bash
git clone https://github.com/kazamok/Game-Launcher.git
cd Game-Launcher
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

3. `config.json` 파일에서 설정 구성.

4. 런처 실행:
```bash
python main.py
```

## 개발

이 프로젝트는 활발히 개발 중입니다. 현재 단계:
- ✅ 기본 구조
- ✅ 인터페이스
- ✅ 스타일링
- ✅ 설정
- 🔄 실행 기능
- 📝 네트워크 상호 작용
- 📝 업데이트 시스템
- 📝 애드온 관리자

## 의존성
```
PySide6>=6.5.0
aiohttp>=3.8.0
aiomysql>=0.2.0
cryptography>=41.0.0
```
## 기술

- Python 3.8+
- PySide6 (최신 UI를 위한 Qt)
- MySQL (AzerothCore와 통합)
- asyncio (비동기 작업)
- aiomysql (MySQL 비동기 작업)

## 구현 특징

- 부드러운 UI 작동을 위한 비동기 아키텍처
- SRP6를 통한 안전한 인증
- 빠른 작동을 위한 데이터 캐싱
- Battle.net 스타일의 현대적인 디자인
- QSS를 통한 테마 지원

## 라이선스

MIT 라이선스

## 감사

- 훌륭한 에뮬레이터를 만들어준 [AzerothCore](https://www.azerothcore.org/)
- 지원과 테스트를 해준 WoW 커뮤니티

## 라이선스

이 프로젝트는 MIT에 따라 라이선스가 부여됩니다. 자세한 내용은 `LICENSE` 파일을 참조하십시오.
