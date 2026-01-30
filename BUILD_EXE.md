# 📦 실행 파일(EXE) 만들기 가이드

이 프로그램을 파이썬이 설치되지 않은 컴퓨터(예: 친구들의 컴퓨터)에서도 실행할 수 있게 `.exe` 파일로 만드는 방법입니다.

## 1. PyInstaller 설치
터미널(명령 프롬프트)에 아래 명령어를 입력하여 라이브러리를 설치합니다.

```bash
pip install pyinstaller
```

## 2. EXE 파일 생성
프로젝트 폴더(`d:\Python\Sword`)에서 아래 명령어를 실행합니다.

```bash
pyinstaller --onefile --noconsole --name "KakaoSwordBot" --icon=NONE kakao_enhance_bot.py
```

### 명령어 설명:
- `--onefile`: 파일 하나로 깔끔하게 만듭니다.
- `--noconsole`: 실행했을 때 검은색 도스창(콘솔)이 뜨지 않게 합니다. (GUI 프로그램이므로)
- `--name "KakaoSwordBot"`: 파일 이름을 `KakaoSwordBot.exe`로 설정합니다.

## 3. 파일 확인
명령어가 완료되면 `dist` 폴더가 생깁니다. 그 안에 있는 `KakaoSwordBot.exe` 파일만 있으면 어디서든 실행할 수 있습니다!

> **주의**: 백신 프로그램이, 서명되지 않은 프로그램이라고 경고할 수 있습니다. 이는 개인 개발자가 만든 프로그램이라 발생하는 자연스러운 현상입니다.
