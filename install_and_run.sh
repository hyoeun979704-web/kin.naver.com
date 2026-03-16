#!/bin/bash
set -e

echo "============================================"
echo "  네이버 지식인 모니터링 봇 - 자동 설치"
echo "============================================"
echo

# 스크립트 파일 기준 디렉토리로 이동
cd "$(dirname "$0")"

# ─── 1. Python 설치 확인 ───
echo "[1/4] Python 확인 중..."
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo
    echo "❌ Python이 설치되어 있지 않습니다."
    echo
    echo "   macOS:  brew install python3"
    echo "   Ubuntu: sudo apt install python3 python3-venv python3-pip"
    echo
    echo "   설치 후 이 스크립트를 다시 실행하세요."
    exit 1
fi

PYTHON_VER=$($PYTHON_CMD --version 2>&1)
echo "   ✅ $PYTHON_VER 감지됨"

# ─── 2. 가상환경 생성/활성화 ───
echo
echo "[2/4] 가상환경 설정 중..."
if [ ! -d "venv" ]; then
    echo "   가상환경 생성 중... (최초 1회)"
    $PYTHON_CMD -m venv venv
    echo "   ✅ 가상환경 생성 완료"
else
    echo "   ✅ 기존 가상환경 사용"
fi

source venv/bin/activate

# ─── 3. 패키지 설치 ───
echo
echo "[3/4] 필요한 패키지 설치 중..."

if ! python -c "import playwright" 2>/dev/null; then
    echo "   패키지 설치 중... (최초 실행 시 몇 분 소요)"
    pip install -r requirements.txt --quiet
    echo "   ✅ Python 패키지 설치 완료"

    echo "   Playwright 브라우저 설치 중... (몇 분 소요)"
    playwright install chromium
    echo "   ✅ Playwright 브라우저 설치 완료"
else
    echo "   ✅ 패키지 이미 설치됨 (스킵)"
fi

# ─── 4. credentials.json 확인 ───
if [ ! -f "credentials.json" ]; then
    echo
    echo "⚠️  credentials.json 파일이 없습니다!"
    echo "   팀원에게 파일을 받아서 이 폴더에 넣어주세요."
    exit 1
fi

# ─── 5. 실행 ───
echo
echo "============================================"
echo "  ✅ 설치 완료! 봇을 실행합니다..."
echo "============================================"
echo

python naver_kin_monitor.py
