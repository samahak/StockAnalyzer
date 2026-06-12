import os
import sys
import streamlit.web.cli as stcli

if __name__ == "__main__":
    # PyInstaller 환경에서 실행될 때 실제 파일 경로를 찾기 위한 로직
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    # 실행할 Streamlit 대시보드 스크립트 경로 지정
    script_path = os.path.join(base_path, "stock_dashboard.py")
    
    # 런타임에 "streamlit run stock_dashboard.py"를 입력한 것과 동일한 효과
    sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false"]
    sys.exit(stcli.main())