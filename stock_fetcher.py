"""
Yahoo Finance API를 사용해서 미국 주식 일단위 가격을 가져오는 모듈
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List


def calculate_rsi(prices, period=14):
    """
    RSI (Relative Strength Index)를 계산합니다.
    
    Parameters:
    -----------
    prices : pd.Series
        종가 데이터
    period : int
        RSI 계산 기간 (기본값: 14)
    
    Returns:
    --------
    pd.Series
        RSI 값
    """
    # 가격 변화 계산
    delta = prices.diff()
    
    # 상승과 하락 분리
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # 평균 계산 (EMA 사용 - 더 자연스러운 RSI)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    
    # RS 계산 (0으로 나누기 방지)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    
    # RSI 계산
    rsi = 100 - (100 / (1 + rs))
    
    # 초기값(첫 날) 처리 - 첫 날은 50으로 설정
    rsi.iloc[0] = 50
    
    # 남은 NaN 값 처리
    rsi = rsi.fillna(rsi.mean())
    
    return rsi


def fetch_stock_daily(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "1y"
) -> pd.DataFrame:
    """
    Yahoo Finance에서 주식의 일단위 가격 데이터를 가져옵니다.
    
    Parameters:
    -----------
    symbol : str
        주식 심볼 (예: 'AAPL', 'GOOGL', 'MSFT')
    start_date : str, optional
        시작 날짜 (형식: 'YYYY-MM-DD'). 지정하지 않으면 period 사용
    end_date : str, optional
        종료 날짜 (형식: 'YYYY-MM-DD'). 기본값은 오늘
    period : str
        데이터 기간 ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max')
        start_date가 지정되면 무시됨
    
    Returns:
    --------
    pd.DataFrame
        일단위 주식 데이터:
        - Date: 거래일
        - Open: 시가
        - High: 고가
        - Low: 저가
        - Close: 종가
        - Adj Close: 조정 종가
        - Volume: 거래량
    """
    try:
        ticker = yf.Ticker(symbol)
        
        if start_date and end_date:
            df = ticker.history(start=start_date, end=end_date)
        else:
            df = ticker.history(period=period)
        
        if df.empty:
            print(f"경고: '{symbol}'에 대한 데이터를 찾을 수 없습니다.")
            return pd.DataFrame()
        
        # 인덱스를 컬럼으로 변환
        df.reset_index(inplace=True)
        
        # 거래가 없는 날(휴일·누락) 또는 데이터 오류 행 제거
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df.dropna(subset=required_cols)
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
        df = df[df['Volume'] > 0].copy()
        
        # 날짜 정규화 및 중복 제거
        df['Date'] = pd.to_datetime(df['Date']).dt.normalize()
        df = df.drop_duplicates(subset=['Date'], keep='last').sort_values('Date').reset_index(drop=True)
        
        if df.empty:
            print(f"경고: '{symbol}'에 대한 유효한 거래일 데이터를 찾을 수 없습니다.")
            return pd.DataFrame()
        
        # RSI 계산 (기본값: 14)
        df['RSI'] = calculate_rsi(df['Close'], period=14)
        
        return df
    
    except Exception as e:
        print(f"오류 발생: {e}")
        return pd.DataFrame()


def fetch_multiple_stocks(
    symbols: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "1y"
) -> dict:
    """
    여러 개의 주식 데이터를 한번에 가져옵니다.
    
    Parameters:
    -----------
    symbols : List[str]
        주식 심볼 리스트 (예: ['AAPL', 'GOOGL', 'MSFT'])
    start_date : str, optional
        시작 날짜
    end_date : str, optional
        종료 날짜
    period : str
        데이터 기간
    
    Returns:
    --------
    dict
        {심볼: DataFrame} 형태의 딕셔너리
    """
    result = {}
    for symbol in symbols:
        print(f"'{symbol}' 데이터 가져오는 중...")
        df = fetch_stock_daily(symbol, start_date, end_date, period)
        if not df.empty:
            result[symbol] = df
    
    return result


def get_stock_info(symbol: str) -> dict:
    """
    주식의 기본 정보를 가져옵니다.
    
    Parameters:
    -----------
    symbol : str
        주식 심볼
    
    Returns:
    --------
    dict
        주식 정보 (회사명, 섹터, 산업, 현재가 등)
    """
    try:
        ticker = yf.Ticker(symbol)
        info = {
            'symbol': symbol,
            'company_name': ticker.info.get('longName', 'N/A'),
            'sector': ticker.info.get('sector', 'N/A'),
            'industry': ticker.info.get('industry', 'N/A'),
            'current_price': ticker.info.get('currentPrice', 'N/A'),
            'market_cap': ticker.info.get('marketCap', 'N/A'),
            'pe_ratio': ticker.info.get('trailingPE', 'N/A'),
        }
        return info
    except Exception as e:
        print(f"오류 발생: {e}")
        return {}


if __name__ == "__main__":
    # 사용 예제
    print("="*60)
    print("Yahoo Finance API - 주식 데이터 가져오기")
    print("="*60)
    
    # 1. 단일 주식 데이터 가져오기 (최근 1년)
    print("\n1. Apple (AAPL) - 최근 1년 데이터")
    print("-"*60)
    aapl_data = fetch_stock_daily("AAPL", period="1y")
    print(f"총 {len(aapl_data)} 거래일의 데이터")
    print("\n최근 5일 데이터:")
    print(aapl_data.tail())
    
    # 2. 특정 기간의 데이터 가져오기
    print("\n\n2. Microsoft (MSFT) - 특정 기간 (2024-01-01 ~ 2024-12-31)")
    print("-"*60)
    msft_data = fetch_stock_daily("MSFT", start_date="2024-01-01", end_date="2024-12-31")
    print(f"총 {len(msft_data)} 거래일의 데이터")
    print("\n첫 5일 데이터:")
    print(msft_data.head())
    
    # 3. 여러 주식 한번에 가져오기
    print("\n\n3. 여러 주식 데이터 가져오기")
    print("-"*60)
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
    multi_data = fetch_multiple_stocks(symbols, period="3mo")
    for symbol, df in multi_data.items():
        print(f"\n{symbol}: {len(df)} 거래일")
        print(f"  종가 범위: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
    
    # 4. 주식 정보 가져오기
    print("\n\n4. 주식 기본 정보")
    print("-"*60)
    info = get_stock_info("AAPL")
    for key, value in info.items():
        print(f"{key}: {value}")
    
    # 5. CSV 파일로 저장하기
    print("\n\n5. 데이터를 CSV로 저장")
    print("-"*60)
    aapl_data.to_csv("aapl_data.csv", index=False, encoding='utf-8-sig')
    print("✓ aapl_data.csv 파일이 저장되었습니다.")
