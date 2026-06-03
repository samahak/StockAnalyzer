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

# 페이지 설정
st.set_page_config(
    page_title="주식 데이터 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

PASSWORD_HASH = "P@ssw0rd"  # 실제 배포 시에는 안전한 방식으로 관리하세요

# 비밀번호 인증
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

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
                if password == PASSWORD_HASH:
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

# 제목
st.title("📈 미국 주식 데이터 대시보드")
company_name_placeholder = st.empty()
st.markdown("---")

# 월 선택 섹션
col1, col2, col3, col4 = st.columns([2, 2, 7, 1])

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

with col1:
    selected_year = st.number_input(
        "연도",
        min_value=2020,
        max_value=latest_year,
        value=latest_year,
        step=1
    )

max_month = latest_month if selected_year == latest_year else 12

with col2:
    selected_month = st.number_input(
        "월",
        min_value=1,
        max_value=max_month,
        value=max_month if selected_year == latest_year else 12,
        step=1
    )

with col4:
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
    
    # 입력 방식 선택
    input_method = st.radio(
        "입력 방식 선택",
        ["심볼 선택", "직접 입력"],
        horizontal=True
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
        symbol = st.selectbox(
            "주식 심볼 선택",
            popular_symbols,
            help="미국 주식 심볼을 선택하세요"
        )
    else:
        custom_symbol = st.text_input(
            "주식 심볼 직접 입력",
            placeholder="예: NFLX, ZM",
            help="심볼을 입력하고 Enter를 누르세요"
        )
        
        if custom_symbol.strip():
            symbol = custom_symbol.strip().upper()
        else:
            st.info("💡 조회할 미국 주식 심볼을 입력해주세요.")
            st.stop()

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
    y_min = price_min - (price_range * 0.05)
    y_max = price_max + (price_range * 0.05)
    
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
    
    # 과매수선 (70)
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", 
                      annotation_text="과매수 (70)", annotation_position="right")
    
    # 과매도선 (30)
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="blue",
                      annotation_text="과매도 (30)", annotation_position="right")
    
    # 중간선 (50)
    fig_rsi.add_hline(y=50, line_dash="dot", line_color="gray",
                      annotation_text="중간값 (50)", annotation_position="right")
    
    fig_rsi.add_annotation(
        x=1.02,
        xref='paper',
        y=current_rsi,
        yref='y',
        text=f"현재 RSI {current_rsi:.2f}",
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
        if current_rsi > 70:
            st.warning("⚠️ 과매수 상태")
        elif current_rsi < 30:
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
