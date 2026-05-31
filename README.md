# Yahoo Finance API를 이용한 미국 주식 데이터 수집

미국 주식 일단위 가격 데이터를 Yahoo Finance API를 통해 가져오는 Python 프로젝트입니다.

## 설치

1. **라이브러리 설치**
```bash
pip install -r requirements.txt
```

또는 개별 설치:
```bash
pip install yfinance pandas requests
```

## 사용 방법

### 1. 단일 주식 데이터 가져오기

```python
from stock_fetcher import fetch_stock_daily

# 최근 1년 데이터
df = fetch_stock_daily("AAPL", period="1y")
print(df.head())
```

### 2. 특정 기간 데이터 가져오기

```python
# 2024년 1월 1일 ~ 2024년 12월 31일
df = fetch_stock_daily("MSFT", start_date="2024-01-01", end_date="2024-12-31")
```

### 3. 여러 주식 한번에 가져오기

```python
from stock_fetcher import fetch_multiple_stocks

symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
data = fetch_multiple_stocks(symbols, period="3mo")

for symbol, df in data.items():
    print(f"{symbol}: {len(df)} rows")
```

### 4. 주식 기본 정보 가져오기

```python
from stock_fetcher import get_stock_info

info = get_stock_info("AAPL")
print(info)
# 출력:
# {
#   'symbol': 'AAPL',
#   'company_name': 'Apple Inc.',
#   'sector': 'Technology',
#   'industry': 'Consumer Electronics',
#   'current_price': 150.5,
#   ...
# }
```

### 5. CSV 파일로 저장

```python
from stock_fetcher import fetch_stock_daily

df = fetch_stock_daily("AAPL")
df.to_csv("aapl_data.csv", index=False)
```

## 사용가능한 기간(period) 옵션

- `1d`: 1일
- `5d`: 5일
- `1mo`: 1개월
- `3mo`: 3개월
- `6mo`: 6개월
- `1y`: 1년 (기본값)
- `2y`: 2년
- `5y`: 5년
- `10y`: 10년
- `max`: 전체 데이터

## 반환되는 데이터의 컬럼

| 컬럼 | 설명 |
|------|------|
| Date | 거래일 |
| Open | 시가 |
| High | 고가 |
| Low | 저가 |
| Close | 종가 |
| Adj Close | 조정 종가 |
| Volume | 거래량 |

## 주요 함수

### `fetch_stock_daily(symbol, start_date=None, end_date=None, period="1y")`

- **symbol**: 주식 심볼 (예: 'AAPL', 'GOOGL')
- **start_date**: 시작 날짜 (형식: 'YYYY-MM-DD')
- **end_date**: 종료 날짜 (형식: 'YYYY-MM-DD')
- **period**: 데이터 기간 (start_date가 없을 때만 사용)
- **반환**: pandas DataFrame

### `fetch_multiple_stocks(symbols, start_date=None, end_date=None, period="1y")`

- **symbols**: 주식 심볼 리스트
- **반환**: {심볼 : DataFrame} 형태의 딕셔너리

### `get_stock_info(symbol)`

- **symbol**: 주식 심볼
- **반환**: 기본 정보가 담긴 딕셔너리

## 실행 방법

### 스크립트로 실행

```bash
python stock_fetcher.py
```

프로젝트에 포함된 예제 코드들이 실행됩니다.

## 참고사항

- Yahoo Finance는 비공식 API이므로 데이터 수집에 약간의 지연이 있을 수 있습니다.
- 대량의 데이터를 수집할 때는 요청 간에 약간의 시간 간격을 두는 것이 좋습니다.
- 일부 주식 데이터는 실시간이 아닌 지연된 데이터입니다.

## 예제 코드

자세한 예제는 `stock_fetcher.py` 파일의 `if __name__ == "__main__"` 섹션을 참고하세요.

## 라이선스

MIT License
