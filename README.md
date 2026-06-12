# StockAnalyzer

Yahoo Finance 데이터를 이용해 미국 주식의 일별 가격, 거래량, RSI 지표를 조회하고 시각화하는 Python 프로젝트입니다.  
Streamlit 기반 웹 대시보드와 데이터 수집용 백엔드 모듈을 함께 제공합니다.

## 주요 기능

- 미국 주식 일별 OHLCV 데이터 조회
- RSI(14) 계산 및 과매수/과매도 기준선 표시
- 선택한 연도/월 기준의 월별 캔들차트, 거래량 차트, RSI 차트 제공
- 캔들차트, 거래량 차트, RSI 차트의 일자 축 정렬
- RSI 변동폭 기반 매수/매도 신호와 강한 신호 마커 표시
- 신호 기준 가상 매매 수익률 계산
- 미국 주요 시가총액 상위 종목 선택 및 목록에 없는 티커 직접 입력
- 회사명, 섹터, 산업, 시가총액 등 기본 정보 조회
- 상세 데이터 테이블 확인 및 CSV 다운로드

## 프로젝트 구조

| 파일 | 설명 |
|------|------|
| `stock_dashboard.py` | Streamlit 웹 대시보드 메인 파일 |
| `stock_fetcher.py` | Yahoo Finance 데이터 수집, RSI 계산, 종목 정보 조회 모듈 |
| `run_app.py` | Streamlit 앱 실행용 Python 엔트리포인트 |
| `run_dashboard.bat` | Windows용 대시보드 실행 스크립트 |
| `requirements.txt` | Python 의존성 목록 |

## 설치

### 1. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate
```

Windows에서는 다음 명령을 사용합니다.

```bat
venv\Scripts\activate
```

### 2. 라이브러리 설치

```bash
pip install -r requirements.txt
```

## 대시보드 실행

### macOS / Linux

```bash
streamlit run stock_dashboard.py
```

또는 실행 엔트리포인트를 사용할 수 있습니다.

```bash
python run_app.py
```

### Windows

```bat
run_dashboard.bat
```

`run_dashboard.bat`는 Python 설치 여부를 확인하고, 가상환경이 없으면 생성한 뒤 필요한 라이브러리를 설치하고 대시보드를 실행합니다.

## 대시보드 사용 방법

1. 상단에서 분석할 연도와 월을 선택합니다.
2. `RSI 차이값`과 `RSI 비교기간(일)`을 설정해 매수/매도 신호 기준을 조정합니다.
3. 왼쪽 사이드바의 `주식 심볼 입력`에서 상위 100개 종목을 선택하거나 목록에 없는 티커를 직접 입력합니다.
4. RSI 과매수/과매도 기준값을 설정합니다. 기본값은 과매도 30, 과매수 70입니다.
5. `주식 분석` 탭에서 캔들차트, 거래량, RSI, 신호 기준 가상 매매 결과, 주요 지표를 확인합니다.
6. `데이터 테이블` 탭에서 상세 데이터를 확인하고 CSV로 다운로드합니다.

### RSI 신호 기준

대시보드의 매수/매도 마커는 사용자가 입력한 비교기간 대비 RSI 변화량으로 계산됩니다.

- RSI가 `RSI 차이값` 이상 하락하면 매수 신호가 표시됩니다.
- RSI가 `RSI 차이값` 이상 상승하면 매도 신호가 표시됩니다.
- RSI 변동폭이 `RSI 차이값`의 2배 이상이면 더 크고 진한 강한 매수/매도 신호로 표시됩니다.

예를 들어 `RSI 비교기간(일)`이 1이고 `RSI 차이값`이 5이면, 전 거래일 대비 RSI가 5 이상 하락한 날에는 매수 신호, 5 이상 상승한 날에는 매도 신호가 표시됩니다.
RSI가 10 이상 변동한 날은 강한 신호로 강조됩니다.

### 가상 매매 수익률

`주식 분석` 탭의 RSI 차트 아래에는 신호 기준 가상 매매 결과가 표시됩니다.

- 시작 금액은 1,000,000원으로 가정합니다.
- 매수 신호가 나오면 해당 거래일 종가에 전액 매수합니다.
- 매도 신호가 나오면 해당 거래일 종가에 전액 매도합니다.
- 마지막에 주식을 보유 중이면 선택 기간의 마지막 종가로 평가합니다.
- 수수료와 환율 변동은 계산에서 제외합니다.

## 데이터 수집 모듈 사용

`stock_fetcher.py`는 대시보드와 별도로 Python 코드에서 직접 사용할 수 있습니다.

### 단일 주식 데이터 가져오기

```python
from stock_fetcher import fetch_stock_daily

df = fetch_stock_daily("AAPL", period="1y")
print(df.head())
```

### 특정 기간 데이터 가져오기

```python
from stock_fetcher import fetch_stock_daily

df = fetch_stock_daily(
    "MSFT",
    start_date="2024-01-01",
    end_date="2024-12-31"
)
```

### 여러 종목 데이터 가져오기

```python
from stock_fetcher import fetch_multiple_stocks

symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
data = fetch_multiple_stocks(symbols, period="3mo")

for symbol, df in data.items():
    print(f"{symbol}: {len(df)} 거래일")
```

### 주식 기본 정보 가져오기

```python
from stock_fetcher import get_stock_info

info = get_stock_info("AAPL")
print(info)
```

## 주요 함수

### `calculate_rsi(prices, period=14)`

- 종가 데이터를 기반으로 RSI 값을 계산합니다.
- 대시보드에서는 기본적으로 RSI(14)를 사용합니다.

### `fetch_stock_daily(symbol, start_date=None, end_date=None, period="1y")`

- Yahoo Finance에서 일별 주식 데이터를 가져옵니다.
- 거래량이 없거나 유효하지 않은 행을 제거합니다.
- `Date`, `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume`, `RSI` 컬럼을 포함한 `pandas.DataFrame`을 반환합니다.

### `fetch_multiple_stocks(symbols, start_date=None, end_date=None, period="1y")`

- 여러 종목의 데이터를 순차적으로 조회합니다.
- `{심볼: DataFrame}` 형태의 딕셔너리를 반환합니다.

### `get_stock_info(symbol)`

- 회사명, 섹터, 산업, 현재가, 시가총액, PER 등 기본 정보를 조회합니다.
- Yahoo Finance에서 정보를 가져오지 못하면 빈 딕셔너리를 반환합니다.

## 사용 가능한 period 옵션

| 값 | 기간 |
|----|------|
| `1d` | 1일 |
| `5d` | 5일 |
| `1mo` | 1개월 |
| `3mo` | 3개월 |
| `6mo` | 6개월 |
| `1y` | 1년 |
| `2y` | 2년 |
| `5y` | 5년 |
| `10y` | 10년 |
| `max` | 전체 데이터 |

## 반환 데이터 컬럼

| 컬럼 | 설명 |
|------|------|
| `Date` | 거래일 |
| `Open` | 시가 |
| `High` | 고가 |
| `Low` | 저가 |
| `Close` | 종가 |
| `Adj Close` | 조정 종가 |
| `Volume` | 거래량 |
| `RSI` | RSI(14) 값 |

## 참고사항

- 데이터는 Yahoo Finance를 통해 조회되며, 일부 종목은 실시간이 아닌 지연 데이터일 수 있습니다.
- Yahoo Finance는 비공식 API이므로 네트워크 상태나 서비스 응답에 따라 조회가 실패할 수 있습니다.
- 대시보드의 로그인 화면 코드는 포함되어 있지만 현재 기본 설정은 인증을 통과한 상태로 시작하도록 되어 있습니다.
- 투자 판단은 본인의 책임이며, 이 프로젝트의 지표와 신호는 참고용입니다.

## 라이선스

MIT License
