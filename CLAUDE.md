# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 실행 (venv 생성 + 의존성 설치 + 기동까지 처리)
./run_dashboard.sh                      # macOS / Linux
run_dashboard.bat                       # Windows

# 가상환경을 직접 쓸 때
.venv/bin/streamlit run stock_dashboard.py
.venv/bin/python run_app.py             # PyInstaller 프리징도 고려한 엔트리포인트

# 데이터 계층 스모크 테스트 (실제 네트워크 호출, cwd에 aapl_data.csv를 생성함)
.venv/bin/python stock_fetcher.py

# DB 상태 점검 (경로, 로그인 요구 여부, 종목 수, 개인 설정)
.venv/bin/python app_db.py
```

가상환경 디렉터리는 `.venv` (Python 3.10.6)로 통일되어 있다. 두 실행 스크립트와 README 모두 `.venv`를 가리킨다.

### 검증 방법

테스트 프레임워크, 린터, 포매터, CI 설정은 이 저장소에 없다. 대시보드를 직접 띄우는 대신 Streamlit의 AppTest로 스크립트를 실제 실행해 검증할 수 있다. `curl`로 HTTP 200만 확인하면 정적 셸만 받는 것이고 스크립트는 실행되지 않으므로 검증이 되지 않는다.

```bash
.venv/bin/python -c "
from streamlit.testing.v1 import AppTest
at = AppTest.from_file('stock_dashboard.py', default_timeout=180); at.run()
print(at.exception, [t.value for t in at.title], len(at.get('plotly_chart')))"
```

위젯은 `at.number_input(key='ui_rsi_buy').set_value(25)`처럼 key로 조작하고, 사이드바 요소는 `at.sidebar.button[0].click().run()`으로 누른다. 네트워크(yfinance)를 실제로 타므로 타임아웃을 넉넉히 준다.

## 아키텍처

네 개의 모듈로 구성된다. 계층 분리가 유일한 구조적 규칙이다.

- **`app_db.py`** — SQLite 저장소. 계정(`users`), 앱 설정(`app_settings`), 종목 목록(`tickers`), 개인 설정(`user_prefs`) 네 테이블을 관리한다. Streamlit을 import하지 않는다.
- **`app_secret.py`** — Fernet 암호화 헬퍼. `app_db`의 개인 설정 저장에만 쓰인다. 순환 import를 피하려고 `app_db`를 함수 안에서 import한다(양쪽 모두).
- **`stock_fetcher.py`** — 데이터 계층. Streamlit을 import하지 않는다. yfinance 조회, 거래일 정제(Volume 0/NaN 행 제거, 날짜 정규화·중복 제거), RSI 계산까지 수행하고 `DataFrame`을 반환한다. 실패 시 예외를 던지지 않고 빈 `DataFrame` 또는 빈 dict를 반환하므로, 호출부는 항상 `df.empty`를 확인해야 한다.
- **`stock_dashboard.py`** — UI 계층 전체. 함수로 나뉘어 있지 않고 위에서 아래로 실행되는 하나의 스크립트다. 새 기능은 올바른 실행 지점에 끼워 넣어야 한다.

### 대시보드 스크립트의 실행 순서와 중단 지점

스크립트는 `st.stop()` 세 곳으로 화면이 갈린다. 코드 위치가 곧 렌더링 조건이다.

1. **인증 게이트** — 스크립트 맨 위에서 `init_db()`를 호출하고, DB의 `require_login` 설정으로 로그인 화면 표시 여부를 정한다. 기본값은 0(끔)이라 메인 화면이 바로 뜬다. 켜려면 `app_db.set_login_required(True)`. 비밀번호는 코드에 없고 `verify_password()`가 DB 해시와 대조한다.
2. **사용법(도움말) 게이트** — `show_help`가 True면 설명 문서를 렌더링하고 `st.stop()`으로 메인 화면 렌더링을 막는다.
3. **데이터 게이트** — 심볼이 비었거나 해당 월 데이터가 비면 `st.stop()`.

이 지점들보다 아래에 있는 코드는 위 조건에서 실행되지 않는다.

### 저장 계층: 무엇을 어떻게 저장하는가

| 대상 | 테이블 | 방식 |
|------|--------|------|
| 비밀번호 | `users` | PBKDF2-HMAC-SHA256(200k) + 임의 솔트. **해시이지 암호화가 아니다** — 로그인 검증에 원문이 필요 없으므로 복호화 불가가 맞다. |
| 개인 설정 | `user_prefs` | JSON을 Fernet으로 암호화해 한 칸(`encrypted_value`)에 저장 |
| 종목 목록 | `tickers` | 평문 (공개 정보). 삭제는 행 제거가 아니라 `is_active = 0` |
| 앱 설정 | `app_settings` | 평문 |

암호화 키는 `STOCK_APP_SECRET_KEY` 환경변수 또는 DB 옆의 `.secret.key`(권한 0600, 없으면 자동 생성)에서 온다. **키가 사라지면 `decrypt_text()`가 None을 반환하고 `get_user_prefs()`는 조용히 `DEFAULT_PREFS`로 되돌아간다** — 예외를 던지지 않는 것은 의도된 동작이다.

`get_user_prefs()`는 `DEFAULT_PREFS`에 있는 키만 받아들인다. 새 설정 항목을 추가하려면 `DEFAULT_PREFS`에 먼저 넣어야 하며, 그러지 않으면 저장해도 읽을 때 버려진다.

종목 목록의 최초 시드는 `app_db.SEED_TICKERS`다. DB가 만들어진 뒤에는 이 리스트를 고쳐도 반영되지 않는다(원본은 DB). 사용자가 목록에 없는 티커를 직접 입력하면 `add_ticker()`로 DB에 등록되어 다음 실행부터 목록에 남는다.

### session_state 규칙: `ui_` 접두사

모든 위젯 key는 `ui_`로 시작한다(`ui_selected_year`, `ui_rsi_diff_value`, `ui_symbol`, `ui_rsi_buy` 등). 이건 취향이 아니라 동작상 필수다. 사용법 화면으로 전환하면 메인 화면 위젯이 렌더링되지 않고, Streamlit은 렌더링되지 않은 위젯의 session_state 값을 버린다. "사용법" 버튼 핸들러가 `ui_`로 시작하는 키만 골라 `saved_state`에 백업하고, "닫기" 버튼이 이를 복원한다. **새 위젯을 추가할 때 `ui_` 접두사 key를 주지 않으면 도움말을 열었다 닫는 순간 그 입력값이 초기화된다.**

반대로 비밀번호 입력 위젯(`pw_current`, `pw_new`, `pw_confirm`)은 **일부러** `ui_` 접두사를 쓰지 않는다. 평문 비밀번호가 `saved_state`로 백업되어 세션에 남는 것을 막기 위해서다. 민감한 입력값에는 이 접두사를 붙이지 말 것.

위젯 초기값은 `prefs = get_user_prefs()`(복호화된 개인 설정)에서 온다. 위젯 생성 **전에** `st.session_state`에 심는 방식이므로, 새 설정 항목도 같은 패턴을 따라야 한다.

### 데이터 파이프라인: 룩백 → 파생 컬럼 → 월 필터

순서가 중요하다.

1. 선택한 월의 **45일 전**(`lookback_days`)부터 조회한다. RSI(14)와 N일 전 대비 변동폭이 월 첫 거래일부터 제대로 나오려면 워밍업 구간이 필요하기 때문이다.
2. `Prev_RSI`, `Prev_Period_RSI`(= `RSI.shift(rsi_diff_period)`), `RSI_Change`를 계산한다.
3. **그 다음에** 선택한 월로 필터링하고 `DateLabel`(`'%m월 %d일'`)을 만든다.

shift/rolling 기반 파생 컬럼을 추가한다면 반드시 월 필터링 **이전**에 계산해야 한다. 이후에 넣으면 월초 며칠이 NaN이 된다.

### 차트 3단 정렬

캔들·거래량·RSI 차트는 세로로 쌓여 하나의 일자 축을 공유하는 것처럼 보여야 한다. 실제로는 독립된 Plotly figure 3개이며, 다음 값을 **모두 동일하게** 맞춰서 정렬을 유지한다.

- `xaxis.type='category'` + `categoryarray=date_labels` + `range=x_axis_range` (`[-0.5, len-0.5]`)
- 좌우 여백: `margin(l=60, r=common_chart_margin_r)`

날짜 눈금 라벨은 맨 아래 RSI 차트에만 표시한다(위 두 차트는 `showticklabels=False`). 어느 한 차트의 margin이나 x축 설정을 바꾸면 세 차트의 정렬이 어긋난다. 카테고리 축을 쓰는 이유는 휴장일을 빈칸 없이 이어 붙이기 위해서다.

### 매매 신호와 가상 매매

신호는 과매수/과매도 기준선이 아니라 **RSI 변동폭**으로 판정한다. 기준선(`ui_rsi_buy`/`ui_rsi_sell`)은 RSI 차트의 점선 표시와 현재 상태 문구에만 쓰이고 신호 생성에는 관여하지 않는다 — 혼동하기 쉬운 지점이다.

- 매수: `RSI_Change <= -rsi_diff_value` / 매도: `RSI_Change >= rsi_diff_value`
- 강한 신호: 변동폭이 `rsi_diff_value * 2` 이상. 강조 마커(큰 반투명 삼각형)와 본 마커 두 trace를 겹쳐 그린다.
- 가상 매매는 tab1 안의 인라인 루프다. 시작 100만원, 신호일 종가 전액 매수/전액 매도, 수수료·환율 제외, 마지막 보유분은 기간 마지막 종가로 평가.

### RSI 구현 특이점

`calculate_rsi()`는 Wilder의 SMMA가 아니라 `ewm(span=period)`를 쓴다. 첫 행은 강제로 50, 남은 NaN은 평균으로 채운다. 다른 도구의 RSI 값과 숫자가 정확히 일치하지 않는 것은 이 때문이며, 의도된 동작이다.

## 컨벤션

- UI 문자열, 주석, 커밋 메시지 모두 한국어다.
- Streamlit 1.58+ API를 쓴다: `st.plotly_chart(..., width='stretch')`, `st.selectbox(..., accept_new_options=True)`. 구버전 `use_container_width` 방식과 섞지 말 것.
- 종목 목록과 개인 설정 기본값은 DB에서 읽는다. 대시보드 코드에 하드코딩하지 말 것.
- `stock_analyzer.db`와 `.secret.key`는 `.gitignore` 대상이다. 계정 정보와 개인 정보가 들어 있으므로 커밋하면 안 된다.
- 캔들 색상은 한국식이다(상승 빨강, 하락 파랑).
