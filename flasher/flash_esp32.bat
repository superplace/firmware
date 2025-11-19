@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Python 경로 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo Python이 설치되어 있지 않습니다.
    echo Python을 설치해주세요: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 필요한 패키지 설치 확인
python -c "import esptool" >nul 2>&1
if errorlevel 1 (
    echo esptool이 설치되어 있지 않습니다.
    echo 설치 중...
    pip install esptool pyserial
)

REM 스크립트 실행
python "%~dp0flash_esp32.py" %*

pause

