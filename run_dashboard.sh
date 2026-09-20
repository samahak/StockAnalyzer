#!/usr/bin/env bash
# macOS / Linux 에서 대시보드를 실행합니다.
# 가상환경(.venv)이 없으면 만들고, requirements.txt가 바뀐 경우에만 의존성을 설치합니다.

set -euo pipefail
cd "$(dirname "$0")"

VENV_DIR=".venv"
REQ_STAMP="$VENV_DIR/.requirements.sha"
PORT=8503

echo "=========================================="
echo "   📈 주식 데이터 대시보드 실행 스크립트"
echo "=========================================="

# 1) 파이썬 확인
if ! command -v python3 > /dev/null 2>&1; then
    echo "[에러] python3 를 찾을 수 없습니다. Python 3.9 이상을 설치한 뒤 다시 실행해주세요."
    exit 1
fi

# 2) 가상환경 확인 및 생성
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "[1/3] 가상환경을 생성하는 중입니다... (최초 1회 조금 오래 걸릴 수 있습니다)"
    python3 -m venv "$VENV_DIR"
fi

# 3) 의존성 점검 (requirements.txt 내용이 바뀌었을 때만 설치)
CURRENT_SHA="$(shasum requirements.txt | awk '{print $1}')"
if [ ! -f "$REQ_STAMP" ] || [ "$(cat "$REQ_STAMP")" != "$CURRENT_SHA" ]; then
    echo "[2/3] 필수 라이브러리를 설치하는 중입니다..."
    "$VENV_DIR/bin/python" -m pip install --upgrade pip --quiet
    "$VENV_DIR/bin/pip" install -r requirements.txt --quiet
    echo "$CURRENT_SHA" > "$REQ_STAMP"
else
    echo "[2/3] 라이브러리가 최신 상태입니다."
fi

# 4) 실행 (포트는 8503 고정)
echo "[3/3] 대시보드를 실행합니다! (웹 브라우저가 자동으로 열립니다)"
echo "👉 주소: http://localhost:$PORT"
echo "💡 종료하시려면 이 터미널에서 Ctrl+C 를 누르세요."
echo
exec "$VENV_DIR/bin/streamlit" run stock_dashboard.py --server.port "$PORT"
