@echo off
chcp 65001 > nul
title 주식 데이터 대시보드

echo ==========================================
echo    📈 주식 데이터 대시보드 실행 스크립트
echo ==========================================
echo.

:: 파이썬 설치 여부 확인
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [에러] Python이 설치되어 있지 않거나 PATH 환경변수에 등록되지 않았습니다.
    echo 파이썬 공식 홈페이지에서 설치 후 다시 실행해주세요.
    pause
    exit /b
)

:: 가상환경 확인 및 생성
if not exist "venv\Scripts\activate.bat" (
    echo [1/3] 가상환경을 생성하는 중입니다... (최초 1회 조금 오래 걸릴 수 있습니다)
    python -m venv venv
)

:: 라이브러리 설치 및 앱 실행
echo [2/3] 가상환경 활성화 및 필수 라이브러리 점검 중...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

echo [3/3] 대시보드를 실행합니다! (웹 브라우저가 자동으로 열립니다)
echo 💡 종료하시려면 이 검은색 터미널 창을 닫아주세요.
echo.
streamlit run stock_dashboard.py
