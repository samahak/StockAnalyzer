"""
Yahoo Finance 주식 데이터 대시보드 (Streamlit)
웹 기반 UI로 미국 주식 일단위 가격을 조회하고 시각화합니다.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from stock_fetcher import fetch_stock_daily, get_stock_info
from datetime import datetime, timedelta
import calendar
import streamlit.components.v1 as components
import numpy as np

# 페이지 설정
st.set_page_config(
    page_title="주식 데이터 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

DEFAULT_AUTH = True
DEFAULT_PASSWORD = "P@ssw0rd"  # 실제 배포 시에는 안전한 방식으로 관리하세요

# 비밀번호 인증
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = DEFAULT_AUTH

if not st.session_state['authenticated']:
    # 'Press enter to apply' 영문 안내 문구 숨김 CSS 적용
    st.markdown("""
        <style>
        div[data-testid="InputInstructions"] {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # 화면 중앙 정렬을 위한 3분할 컬럼 사용
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("🔒 로그인")
        with st.form("login_form"):
            password = st.text_input("비밀번호를 입력하세요", type="password", max_chars=20)
            submit_button = st.form_submit_button("로그인", use_container_width=True)
            
            if submit_button:
                if password == DEFAULT_PASSWORD:
                    st.session_state['authenticated'] = True
                    st.rerun()
                else:
                    st.error("❌ 비밀번호가 일치하지 않습니다.")
                    
                    # 입력창 수정(타이핑) 시 즉시 에러를 숨기기 위한 자바스크립트 주입
                    # (Streamlit DOM 재사용으로 인한 렌더링 오류를 막기 위해 f-string과 고유값 추가, display 상태 초기화)
                    components.html(
                        f"""
                        <script>
                        // {datetime.now().timestamp()}
                        const doc = window.parent.document;
                        
                        // 이전 이벤트로 인해 display:none 된 DOM이 재사용되었을 수 있으므로 강제 초기화
                        const alerts = doc.querySelectorAll('[data-testid="stAlert"]');
                        alerts.forEach(alert => {{
                            if (alert.innerText.includes('비밀번호가 일치하지 않습니다')) {{
                                alert.style.display = ''; 
                            }}
                        }});
                        
                        const pwdInput = doc.querySelector('input[type="password"]');
                        if (pwdInput && !pwdInput.dataset.listenerAttached) {{
                            pwdInput.addEventListener('input', function() {{
                                const currentAlerts = doc.querySelectorAll('[data-testid="stAlert"]');
                                currentAlerts.forEach(a => {{
                                    if (a.innerText.includes('비밀번호가 일치하지 않습니다')) {{
                                        a.style.display = 'none';
                                    }}
                                }});
                            }});
                            pwdInput.dataset.listenerAttached = 'true';
                        }}
                        </script>
                        """, height=0, width=0
                    )
    st.stop()

# 입력 상태 유지를 위한 딕셔너리 초기화
if 'saved_state' not in st.session_state:
    st.session_state['saved_state'] = {}

# 사용법(도움말) 페이지 표시 여부 상태 관리
if 'show_help' not in st.session_state:
    st.session_state['show_help'] = False

# 사용 설명서 화면 렌더링
if st.session_state['show_help']:
    col_title, col_btn = st.columns([9, 1])
    with col_title:
        st.title("📖 대시보드 사용 설명서")
    with col_btn:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("❌ 닫기", use_container_width=True, help="메인 화면으로 돌아가기"):
            st.session_state['show_help'] = False
            # 메인 화면으로 돌아가기 전, 저장해둔 UI 상태 값들을 강제로 복구
            for k, v in st.session_state['saved_state'].items():
                st.session_state[k] = v
            st.rerun()
            
    st.markdown("""
    ### 📌 주요 기능 안내

    **1. 🔒 로그인**
    * 초기 기본 비밀번호는 `P@ssw0rd`로 설정되어 있습니다. (보안을 위해 필요 시 소스코드 내 비밀번호 수정 가능)

    **2. 📅 기간 설정 및 RSI 변동 매매 신호 (화면 상단)**
    * **연도/월 선택**: 특정 연도와 월을 선택하여 해당 기간의 데이터를 집중적으로 분석할 수 있습니다.
    * **RSI 차이값 & 비교 기간**: 차트 상에 표시될 **매수/매도 마커(세모 기호)**의 기준이 됩니다.
        * *예) 비교 기간 `1`일, RSI 차이값 `10` 설정 시:* 이전 날짜(1일 전) 대비 RSI가 10 이상 하락하면 매수 신호(초록색 상향 세모), 10 이상 상승하면 매도 신호(검은색 하향 세모)가 표시됩니다.

    **3. ⚙️ 종목 및 지표 설정 (좌측 사이드바)**
    * **종목 선택**: 미국 주식 시가총액 상위 100대 기업을 리스트에서 바로 선택하거나, 조회하고 싶은 티커(예: TSLA, NFLX)를 직접 입력할 수 있습니다.
    * **RSI 매매 신호 설정**: 하단 RSI 차트에 표시될 과매수/과매도 기준선(점선)을 설정하여 현재 주식의 상태를 판단합니다. (기본값: 과매수 70, 과매도 30)

    **4. 📊 차트 및 상세 데이터 (메인 화면)**
    * **📊 주식 차트 탭**: 
        * 상단부터 **캔들차트, 거래량 바 차트, RSI 선 차트** 순으로 배치되어 있습니다.
        * 캔들이나 차트 마커에 마우스를 올리면 각 일자별 상세 수치와 RSI 변동폭 등을 툴팁으로 확인할 수 있습니다.
    * **📋 데이터 테이블 탭**: 
        * 일자별 가격/거래량/RSI 상세 데이터를 표 형태로 확인하고, `CSV 다운로드` 버튼을 통해 엑셀 등 외부 프로그램에서 활용할 수 있습니다.
    """)
    st.stop() # 사용 설명서 페이지 활성화 시 기존 메인 화면 렌더링 중지

# 메인 화면 제목
col_title, col_btn = st.columns([9, 1])
with col_title:
    st.title("📈 미국 주식 데이터 알람")
with col_btn:
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    if st.button("사용법", use_container_width=True, help="대시보드 사용 설명서 보기"):
        # 화면이 전환되면서 Streamlit이 숨겨진 위젯의 값을 초기화하는 것을 방지하기 위해 현재 상태 백업
        st.session_state['saved_state'] = {k: v for k, v in st.session_state.items() if k.startswith('ui_')}
        st.session_state['show_help'] = True
        st.rerun()

company_name_placeholder = st.empty()
st.markdown("---")

# 월 선택 섹션
col1, col2, col3, col4, col5, _ = st.columns([2, 2, 1.5, 1.5, 0.8, 3.2])

@st.cache_data(ttl=3600)
def get_latest_trading_month():
    """미국장(SPY 기준)의 가장 최근 거래 연도와 월을 반환합니다."""
    df_market = fetch_stock_daily("SPY", period="5d")
    if not df_market.empty:
        last_date = df_market['Date'].max()
        return last_date.year, last_date.month
        
    # API 오류 등으로 데이터가 없으면 로컬 시간 기준 (월초 1~3일은 보수적으로 전월 반환)
    today = datetime.now()
    if today.day <= 3:
        prev = today.replace(day=1) - timedelta(days=1)
        return prev.year, prev.month
    return today.year, today.month

latest_year, latest_month = get_latest_trading_month()

if 'ui_selected_year' not in st.session_state:
    st.session_state['ui_selected_year'] = latest_year

if 'ui_selected_month' not in st.session_state:
    st.session_state['ui_selected_month'] = latest_month

if 'ui_rsi_diff_value' not in st.session_state:
    st.session_state['ui_rsi_diff_value'] = 5

if 'ui_rsi_diff_period' not in st.session_state:
    st.session_state['ui_rsi_diff_period'] = 1

with col1:
    selected_year = st.number_input(
        "연도",
        min_value=2020,
        max_value=latest_year,
        step=1,
        key='ui_selected_year'
    )

max_month = latest_month if selected_year == latest_year else 12

# 만약 현재 세션의 월이 최대 월(max_month)보다 크다면 최대 월로 보정 (연도를 변경할 때 발생 가능)
if st.session_state['ui_selected_month'] > max_month:
    st.session_state['ui_selected_month'] = max_month

with col2:
    selected_month = st.number_input(
        "월",
        min_value=1,
        max_value=max_month,
        step=1,
        key='ui_selected_month'
    )

with col3:
    rsi_diff_value = st.number_input(
        "RSI 차이값",
        min_value=1,
        max_value=30,
        step=1,
        help="검증할 RSI 차이값을 입력하세요",
        key='ui_rsi_diff_value'
    )

with col4:
    rsi_diff_period = st.number_input(
        "비교 기간 (일)",
        min_value=1,
        max_value=14,
        step=1,
        help="1~14일 사이의 차이를 비교할 기간을 입력하세요",
        key='ui_rsi_diff_period'
    )

with col5:
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    if st.button("🔄", help="데이터 로드", use_container_width=True):
        st.rerun()

# 선택된 월의 시작일과 종료일 계산
first_day = datetime(selected_year, selected_month, 1)
last_day = datetime(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1])

# 월 이름 한글 표시
month_names = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월']
st.info(f"📅 선택 기간: **{selected_year}년 {month_names[selected_month-1]}** ({first_day.strftime('%Y-%m-%d')} ~ {last_day.strftime('%Y-%m-%d')})")

st.markdown("---")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    default_input_method = st.session_state['saved_state'].get('ui_input_method', "심볼 선택")
    method_idx = 0 if default_input_method == "심볼 선택" else 1
    
    # 입력 방식 선택
    input_method = st.radio(
        "입력 방식 선택",
        ["심볼 선택", "직접 입력"],
        index=method_idx,
        horizontal=True,
        key='ui_input_method'
    )
    
    if input_method == "심볼 선택":
        top_100_symbols = [
            "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "BRK-B", "LLY", "TSLA", "AVGO",
            "JPM", "UNH", "V", "XOM", "JNJ", "MA", "PG", "HD", "COST", "MRK",
            "ABBV", "CRM", "CVX", "AMD", "NFLX", "PEP", "KO", "BAC", "WMT", "TMO",
            "LIN", "MCD", "ADBE", "DIS", "CSCO", "ACN", "ABT", "INTU", "QCOM", "WFC",
            "DHR", "GE", "IBM", "CAT", "NOW", "TXN", "VZ", "AMGN", "COP", "PM",
            "PFE", "ISRG", "SPGI", "BA", "UNP", "HON", "NKE", "SYK", "RTX", "GS",
            "LOW", "PLD", "BKNG", "ELV", "MS", "T", "BLK", "DE", "INTC", "MDT",
            "VRTX", "REGN", "AMT", "LMT", "ADP", "MMC", "CB", "PANW", "CI", "TMUS",
            "BSX", "PGR", "SCHW", "ETN", "CMCSA", "C", "FI", "MU", "ZTS", "KLAC",
            "NEE", "LRCX", "SNPS", "CDNS", "TJX", "WM", "SHW", "GD", "MO", "SO"
        ]
        popular_symbols = sorted(top_100_symbols)
        default_symbol = st.session_state['saved_state'].get('ui_symbol', popular_symbols[0])
        symbol_idx = popular_symbols.index(default_symbol) if default_symbol in popular_symbols else 0
        symbol = st.selectbox(
            "주식 심볼 선택",
            popular_symbols,
            index=symbol_idx,
            help="미국 주식 심볼을 선택하세요",
            key='ui_symbol'
        )
    else:
        default_custom = st.session_state['saved_state'].get('ui_custom_symbol', "")
        custom_symbol = st.text_input(
            "주식 심볼 직접 입력",
            value=default_custom,
            placeholder="예: NFLX, ZM",
            help="심볼을 입력하고 Enter를 누르세요",
            key='ui_custom_symbol'
        )
        
        if custom_symbol.strip():
            symbol = custom_symbol.strip().upper()
        else:
            st.info("💡 조회할 미국 주식 심볼을 입력해주세요.")
            st.stop()
            
    st.markdown("---")
    st.header("📊 RSI 매매 신호 설정")
    
    default_buy = st.session_state['saved_state'].get('ui_rsi_buy', 30)
    rsi_buy_threshold = st.number_input("매수 RSI 기준 (이하 하락 시)", min_value=1, max_value=100, value=default_buy, step=1, key='ui_rsi_buy')
    
    default_sell = st.session_state['saved_state'].get('ui_rsi_sell', 70)
    rsi_sell_threshold = st.number_input("매도 RSI 기준 (이상 상승 시)", min_value=1, max_value=100, value=default_sell, step=1, key='ui_rsi_sell')

# 데이터 로딩
lookback_days = 45
rsi_start = first_day - timedelta(days=lookback_days)
with st.spinner(f"'{symbol}' 데이터를 불러오는 중..."):
    df = fetch_stock_daily(
        symbol,
        start_date=rsi_start.strftime('%Y-%m-%d'),
        end_date=last_day.strftime('%Y-%m-%d')
    )
    info = get_stock_info(symbol)

# 상단 타이틀 아래에 회사명 표시
if info:
    # 정보가 없는 경우('N/A') 심볼 이름으로 대체하여 깔끔하게 표시
    comp_name = info.get('company_name', symbol)
    comp_name = symbol if comp_name == 'N/A' else comp_name
    company_name_placeholder.subheader(f"🏢 {comp_name} ({symbol})")
else:
    company_name_placeholder.subheader(f"🏢 {symbol}")

# 거래 없는 날(Volume 0) 제거
if not df.empty:
    df['Date'] = pd.to_datetime(df['Date']).dt.normalize().dt.tz_localize(None)
    df = df[df['Volume'] > 0].copy()
    df = df.drop_duplicates(subset=['Date'], keep='last').sort_values('Date').reset_index(drop=True)
    df['Prev_RSI'] = df['RSI'].shift(1)
    df['Prev_Period_RSI'] = df['RSI'].shift(int(rsi_diff_period))
    df['RSI_Change'] = df['RSI'] - df['Prev_Period_RSI']

# 선택한 월 데이터만 표시
if not df.empty:
    df = df[(df['Date'] >= first_day) & (df['Date'] <= last_day)].copy()
    df['DateLabel'] = df['Date'].dt.strftime('%m월 %d일')

# 데이터 확인
if df.empty:
    st.error(f"❌ '{symbol}'의 데이터를 불러올 수 없습니다. 심볼을 확인하세요.")
    st.stop()

# 차트 탭
tab1, tab2 = st.tabs(["📊 주식 분석", "📋 데이터 테이블"])

with tab1:
    st.subheader("📈 주식 차트")
    
    # 한 달 내 상하한가 계산
    price_min = df['Low'].min()
    price_max = df['High'].max()
    price_range = price_max - price_min
    
    # y축 범위 설정 (상하한가 기준)
    y_min = price_min - (price_range * 0.1)
    y_max = price_max + (price_range * 0.1)
    
    # 캔들스틱 차트
    fig = go.Figure(data=[
        go.Candlestick(
            x=df['DateLabel'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            increasing=dict(line=dict(color='red'), fillcolor='rgba(255,0,0,0.5)'),
            decreasing=dict(line=dict(color='blue'), fillcolor='rgba(0,0,255,0.5)'),
            name='캔들',
            hovertemplate='<b>%{x}</b><br>Open: %{open:.2f}<br>High: %{high:.2f}<br>Low: %{low:.2f}<br>Close: %{close:.2f}<extra></extra>'
        )
    ])
    
    # 매매 신호 계산 (입력한 비교 기간 대비 RSI 변동폭 기준)
    buy_signals = df[df['RSI_Change'] <= -rsi_diff_value]
    sell_signals = df[df['RSI_Change'] >= rsi_diff_value]
    
    # 매수 신호 표시 (캔들 하단)
    if not buy_signals.empty:
        fig.add_trace(go.Scatter(
            x=buy_signals['DateLabel'],
            y=buy_signals['Low'] - (price_range * 0.03),
            mode='markers',
            marker=dict(symbol='triangle-up', size=14, color='green', line=dict(width=1, color='darkgreen')),
            name='매수 신호',
            hovertemplate='<b>매수 신호</b><br>RSI: %{customdata[0]:.2f}<br>RSI 변동: %{customdata[1]:+.2f}<extra></extra>',
            customdata=np.stack((buy_signals['RSI'], buy_signals['RSI_Change']), axis=-1)
        ))
        
    # 매도 신호 표시 (캔들 상단)
    if not sell_signals.empty:
        fig.add_trace(go.Scatter(
            x=sell_signals['DateLabel'],
            y=sell_signals['High'] + (price_range * 0.03),
            mode='markers',
            marker=dict(symbol='triangle-down', size=14, color='black', line=dict(width=1, color='black')),
            name='매도 신호',
            hovertemplate='<b>매도 신호</b><br>RSI: %{customdata[0]:.2f}<br>RSI 변동: %{customdata[1]:+.2f}<extra></extra>',
            customdata=np.stack((sell_signals['RSI'], sell_signals['RSI_Change']), axis=-1)
        ))
    
    fig.update_layout(
        title=f"{symbol} 일별 캔들차트",
        yaxis_title="가격 ($)",
        yaxis=dict(range=[y_min, y_max]),
        hovermode='x unified',
        height=420,
        template='plotly_white',
        margin=dict(l=60, r=20, t=40, b=0),
        xaxis=dict(
            type='category',
            showticklabels=False,
            showgrid=False,
            rangeslider=dict(visible=False)
        )
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # 거래량 차트 (0 이하인 일자는 제외)
    df_vol = df.copy()
    df_vol['Volume'] = pd.to_numeric(df_vol['Volume'], errors='coerce')
    df_vol = df_vol[df_vol['Volume'] > 0]

    if not df_vol.empty:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Bar(
            x=df_vol['DateLabel'],
            y=df_vol['Volume'],
            marker_color='royalblue',
            name='거래량',
            hovertemplate='거래량: %{y:,.0f}<extra></extra>'
        ))
        fig_vol.update_layout(
            title='',
            yaxis_title="거래량",
            hovermode='x unified',
            height=100,
            template='plotly_white',
            margin=dict(l=60, r=20, t=10, b=0),
            xaxis=dict(
                type='category',
                showticklabels=False,
                showgrid=False
            )
        )
        st.plotly_chart(fig_vol, width='stretch')
    else:
        st.info("거래량 데이터가 없습니다.")
    
    # RSI 차트
    current_rsi = df['RSI'].iloc[-1]
    fig_rsi = go.Figure()
    
    # RSI 라인
    fig_rsi.add_trace(go.Scatter(
        x=df['DateLabel'],
        y=df['RSI'],
        mode='lines',
        name='RSI (14)',
        line=dict(color='#FF6B6B', width=2),
        hovertemplate='RSI: %{y:.2f}<extra></extra>'
    ))
    
    # 매도 기준선
    fig_rsi.add_hline(y=rsi_sell_threshold, line_dash="dash", line_color="red", 
                      annotation_text=f"과매수 ({rsi_sell_threshold})", annotation_position="right")
    
    # 매수 기준선
    fig_rsi.add_hline(y=rsi_buy_threshold, line_dash="dash", line_color="blue",
                      annotation_text=f"과매도 ({rsi_buy_threshold})", annotation_position="right")
    
    # 중간선 (50)
    fig_rsi.add_hline(y=50, line_dash="dot", line_color="gray",
                      annotation_text="중간값 (50)", annotation_position="right")
    
    fig_rsi.add_annotation(
        x=1.02,
        xref='paper',
        y=current_rsi,
        yref='y',
        text=f"RSI값 {current_rsi:.2f}",
        showarrow=False,
        xanchor='left',
        font=dict(size=14, color='black')
    )
    
    fig_rsi.update_layout(
        title='',
        xaxis_title="날짜",
        yaxis_title="RSI",
        yaxis=dict(range=[0, 100], tickfont=dict(size=12), title=dict(font=dict(size=14))),
        hovermode='x unified',
        height=300,
        template='plotly_white',
        margin=dict(l=60, r=140, t=10, b=20),
        xaxis=dict(
            type='category',
            tickangle=-45,
            tickfont=dict(size=12),
        )
    )
    
    st.plotly_chart(fig_rsi, width='stretch')
    
    # 메인 컨텐츠
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        final_price = df['Close'].iloc[-1]
        prev_close_index = max(0, len(df) - 5)
        prev_close = df['Close'].iloc[prev_close_index]
        st.metric(
            "최종 가격",
            f"${final_price:.2f}",
            delta=f"${final_price - prev_close:.2f}"
        )

    with col2:
        high_price = df['High'].max()
        st.metric("최고가 (기간)", f"${high_price:.2f}")

    with col3:
        low_price = df['Low'].min()
        st.metric("최저가 (기간)", f"${low_price:.2f}")

    with col4:
        avg_volume = df['Volume'].mean()
        st.metric("평균 거래량", f"{avg_volume:,.0f}")

    st.markdown("---")

    # 주식 정보 표시
    if info:
        info_cols = st.columns(3)
        
        with info_cols[0]:
            st.write(f"**섹터:** {info.get('sector', 'N/A')}")
        
        with info_cols[1]:
            st.write(f"**산업:** {info.get('industry', 'N/A')}")
        
        with info_cols[2]:
            market_cap = info.get('market_cap', 'N/A')
            market_cap_display = f"{market_cap:,}" if isinstance(market_cap, (int, float)) else market_cap
            st.write(f"**시가총액:** {market_cap_display}")
        
        st.markdown("---")

    # 통계
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("변동률", f"{((df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100):.2f}%")
    
    with col2:
        st.metric("표준편차", f"${df['Close'].std():.2f}")
    
    with col3:
        st.metric("데이터 기간", f"{len(df)} 거래일")
    
    st.markdown("---")
    
    # RSI 해석
    current_rsi = df['RSI'].iloc[-1]
    prev_rsi_index = max(0, len(df) - 5)
    prev_rsi = df['RSI'].iloc[prev_rsi_index]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("현재 RSI", f"{current_rsi:.2f}", delta=f"{current_rsi - prev_rsi:.2f}")
    
    with col2:
        if current_rsi >= rsi_sell_threshold:
            st.warning("⚠️ 과매수 상태")
        elif current_rsi <= rsi_buy_threshold:
            st.info("ℹ️ 과매도 상태")
        else:
            st.success("✅ 중립 상태")
    
    with col3:
        rsi_trend = "📈 상승" if current_rsi > prev_rsi else "📉 하락"
        st.write(f"**RSI 추세**: {rsi_trend}")
    
    st.markdown("---")

with tab2:
    st.subheader("상세 데이터")
    
    # 데이터 포맷팅
    df_display = df.copy()
    if 'Date' in df_display.columns:
        # 날짜를 한글로 포맷 (예: 2026년 5월 29일 목요일)
        df_display['Date'] = df_display['Date'].apply(
            lambda x: pd.to_datetime(x).strftime('%Y년 %m월 %d일 %A').replace(
                'Monday', '월요일'
            ).replace(
                'Tuesday', '화요일'
            ).replace(
                'Wednesday', '수요일'
            ).replace(
                'Thursday', '목요일'
            ).replace(
                'Friday', '금요일'
            ).replace(
                'Saturday', '토요일'
            ).replace(
                'Sunday', '일요일'
            )
        )
    
    # 가격 컬럼 포맷팅
    price_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close']
    for col in price_cols:
        if col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: f"${x:.2f}")
    
    # RSI 포맷팅
    if 'RSI' in df_display.columns:
        df_display['RSI'] = df_display['RSI'].apply(lambda x: f"{x:.2f}")
    
    # 거래량 포맷팅
    if 'Volume' in df_display.columns:
        df_display['Volume'] = df_display['Volume'].apply(lambda x: f"{x:,.0f}")
    
    # 역순 정렬 (최신순) - Date 컬럼이 있으면 사용
    if 'Date' in df_display.columns:
        df_display = df_display.iloc[::-1].reset_index(drop=True)
    
    st.dataframe(
        df_display,
        width='stretch',
        hide_index=True
    )
    
    # 다운로드 버튼
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name=f"{symbol}_{selected_year}_{selected_month:02d}.csv",
        mime="text/csv"
    )

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 12px;'>
    <p>데이터 출처: Yahoo Finance | 마지막 업데이트: {} | 개발: Stock Analyzer</p>
</div>
""".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)
