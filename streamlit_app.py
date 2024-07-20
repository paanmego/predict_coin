import streamlit as st
from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objs as go

cg = CoinGeckoAPI()

@st.cache_data
def get_data():
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Bitcoin 데이터 가져오기
        data = cg.get_coin_market_chart_range_by_id(
            id='bitcoin',
            vs_currency='usd',
            from_timestamp=int(start_date.timestamp()),
            to_timestamp=int(end_date.timestamp())
        )
        
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # OHLC 데이터 생성
        df = df.resample('D').agg({
            'price': ['first', 'max', 'min', 'last']
        })
        df.columns = ['Open', 'High', 'Low', 'Close']
        
        return df
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")
        return None

# 그래프 생성 함수
def create_graph(df):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='BTC-USD'
    ))

    ma20 = df['Close'].rolling(window=20).mean()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=ma20,
        line=dict(color='orange', width=2),
        name='20일 이동평균'
    ))

    fig.update_layout(
        title='비트코인 가격 (최근 30일)',
        yaxis_title='가격 (USD)',
        xaxis_rangeslider_visible=False
    )

    return fig

# 분석 텍스트 생성 함수
def create_analysis(df):
    last_price = df['Close'].iloc[-1]
    max_price = df['High'].max()
    min_price = df['Low'].min()
    price_change = (df['Close'].iloc[-1] - df['Open'].iloc[0]) / df['Open'].iloc[0] * 100

    analysis_text = f"""
    ## 비트코인 시장 분석
    
    최근 30일간의 비트코인 시장 동향:
    
    - 현재 가격: ${last_price:.2f}
    - 30일 최고가: ${max_price:.2f}
    - 30일 최저가: ${min_price:.2f}
    - 가격 변동률: {price_change:.2f}%
    
    ### 시장 동향
    {'상승' if price_change > 0 else '하락'} 추세를 보이고 있으며, 
    최근 30일 동안 ${min_price:.2f}에서 ${max_price:.2f} 사이에서 거래되었습니다.
    
    ### 투자 유의사항
    암호화폐 시장은 변동성이 높습니다. 투자 결정 시 신중을 기하시기 바랍니다.
    """
    return analysis_text

# 메인 로직
st.title("비트코인 가격 분석")

if st.sidebar.button("데이터 로드"):
    with st.spinner("데이터를 불러오는 중..."):
        df = get_data()
    if df is not None:
        st.session_state['data'] = df
        st.success("데이터 로드 완료!")
        st.write(df)
    else:
        st.error("데이터를 불러오는데 실패했습니다.")

if 'data' in st.session_state:
    df = st.session_state['data']
    
    st.subheader("비트코인 가격 그래프")
    fig = create_graph(df)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("시장 분석")
    analysis = create_analysis(df)
    st.markdown(analysis)