import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
from datetime import datetime, timedelta

# Streamlit 페이지 설정
st.set_page_config(page_title="비트코인 선물 그래프", layout="wide")

# 페이지 제목
st.title("비트코인 선물 이동 그래프")

# 데이터 가져오기
@st.cache_data
def get_data():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # 비트코인 선물 데이터 (CME)
    btc = yf.Ticker("BTC=F")
    df = btc.history(start=start_date, end=end_date)
    
    return df

# 데이터 로드
df = get_data()

# 그래프 생성
fig = go.Figure()

# 캔들스틱 차트 추가
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name='BTC 선물'
))

# 이동평균선 추가 (20일)
ma20 = df['Close'].rolling(window=20).mean()
fig.add_trace(go.Scatter(
    x=df.index,
    y=ma20,
    line=dict(color='orange', width=2),
    name='20일 이동평균'
))

# 레이아웃 설정
fig.update_layout(
    title='비트코인 선물 가격 (최근 30일)',
    yaxis_title='가격 (USD)',
    xaxis_rangeslider_visible=False
)

# Streamlit에 그래프 표시
st.plotly_chart(fig, use_container_width=True)

# 추가 정보 표시
st.subheader("최근 거래 정보")
st.write(f"최근 종가: ${df['Close'].iloc[-1]:.2f}")
st.write(f"30일 최고가: ${df['High'].max():.2f}")
st.write(f"30일 최저가: ${df['Low'].min():.2f}")
