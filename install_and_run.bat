@echo off
chcp 65001 >nul 2>&1
title 네이버 지식인 모니터링 봇 - 자동 설치 및 실행

echo ============================================
echo   네이버 지식인 모니터링 봇 - 자동 설치
echo ============================================
echo.

:: ─── 1. Python 설치 확인 ───
echo [1/4] Python 확인 중...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    py --version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo ❌ Python이 설치되어 있지 않습니다.
        echo.
        echo    아래 링크에서 Python 3.10 이상을 설치해주세요:
        echo    https://www.python.org/downloads/
        echo.
        echo    ⚠️  설치 시 "Add Python to PATH" 체크 필수!
        echo.
        echo    설치 후 이 파일을 다시 실행하세요.
        echo.
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VER=%%i
echo    ✅ %PYTHON_VER% 감지됨

:: ─── 2. 가상환경 생성/활성화 ───
echo.
echo [2/4] 가상환경 설정 중...
if not exist "venv" (
    echo    가상환경 생성 중... (최초 1회)
    %PYTHON_CMD% -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ 가상환경 생성 실패
        pause
        exit /b 1
    )
    echo    ✅ 가상환경 생성 완료
) else (
    echo    ✅ 기존 가상환경 사용
)

call venv\Scripts\activate.bat

:: ─── 3. 패키지 설치 ───
echo.
echo [3/4] 필요한 패키지 설치 중...

pip show playwright >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo    패키지 설치 중... (최초 실행 시 몇 분 소요)
    pip install -r requirements.txt --quiet
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ 패키지 설치 실패
        pause
        exit /b 1
    )
    echo    ✅ Python 패키지 설치 완료

    echo    Playwright 브라우저 설치 중... (몇 분 소요)
    playwright install chromium
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Playwright 브라우저 설치 실패
        pause
        exit /b 1
    )
    echo    ✅ Playwright 브라우저 설치 완료
) else (
    echo    ✅ 패키지 이미 설치됨 (스킵)
)

:: ─── 4. credentials.json 확인 ───
if not exist "credentials.json" (
    echo.
    echo ⚠️  credentials.json 파일이 없습니다!
    echo    팀원에게 파일을 받아서 이 폴더에 넣어주세요.
    echo.
    pause
    exit /b 1
)

:: ─── 5. 실행 ───
echo.
echo ============================================
echo   ✅ 설치 완료! 봇을 실행합니다...
echo ============================================
echo.

python naver_kin_monitor.py

echo.
echo 봇 실행이 종료되었습니다.
pause
