import streamlit as st
from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime, timedelta
import time
import plotly.graph_objs as go

# Streamlit 페이지 설정
st.set_page_config(page_title="비트코인 분석", layout="wide")

# 페이지 제목
st.title("비트코인 분석 대시보드")

# 사이드바 생성
st.sidebar.title("메뉴")
menu = st.sidebar.radio("선택하세요:", ["데이터 로드", "그래프", "분석"])

cg = CoinGeckoAPI()
# EMA 계산 함수 추가
def calculate_ema(data, period, column='close'):
    return data[column].ewm(span=period, adjust=False).mean()


@st.cache_data
def get_data():
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)  # 1년치 데이터
            
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
            df.columns = ['open', 'high', 'low', 'close']
            
            # EMA 계산
            df['EMA10'] = calculate_ema(df, 10)
            df['EMA20'] = calculate_ema(df, 20)
            df['EMA50'] = calculate_ema(df, 50)
            df['EMA100'] = calculate_ema(df, 100)
            
            return df
        except Exception as e:
            if attempt < max_retries - 1:
                st.warning(f"오류 발생. {retry_delay}초 후 재시도합니다. (시도 {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {str(e)}")
                raise e

    return None

# 그래프 생성 함수 수정
def create_graph(df):
    fig = go.Figure()

    # 캔들스틱 차트 추가
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='BTC/USD'
    ))

    # EMA 선 추가
    ema_colors = ['blue', 'green', 'orange', 'red']
    ema_periods = [10, 20, 50, 100]
    
    for period, color in zip(ema_periods, ema_colors):
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[f'EMA{period}'],
            line=dict(color=color, width=1),
            name=f'EMA {period}'
        ))

    # 레이아웃 설정
    fig.update_layout(
        title='비트코인 가격 및 EMA (최근 1년)',
        yaxis_title='가격 (USD)',
        xaxis_rangeslider_visible=False
    )

    return fig

# 분석 텍스트 생성 함수
def create_analysis(df):
    last_price = df['close'].iloc[-1]
    max_price = df['high'].max()
    min_price = df['low'].min()
    price_change = (df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0] * 100

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
if menu == "데이터 로드":
    if st.sidebar.button("데이터 로드"):
        try:
            with st.spinner("데이터를 불러오는 중..."):
                df = get_data()
            if df is not None:
                st.session_state['data'] = df
                st.success("데이터 로드 완료!")
                st.write(df)
            else:
                st.error("데이터를 불러오는데 실패했습니다.")
        except Exception as e:
            st.error(f"데이터 로드 중 오류 발생: {str(e)}")

elif menu == "그래프":
    if 'data' not in st.session_state:
        st.warning("먼저 데이터를 로드해주세요.")
    else:
        fig = create_graph(st.session_state['data'])
        st.plotly_chart(fig, use_container_width=True)

elif menu == "분석":
    if 'data' not in st.session_state:
        st.warning("먼저 데이터를 로드해주세요.")
    else:
        analysis = create_analysis(st.session_state['data'])
        st.markdown(analysis)

# 추가 정보 표시
if 'data' in st.session_state:
    with st.sidebar.expander("최근 거래 정보"):
        df = st.session_state['data']
        st.write(f"최근 종가: ${df['close'].iloc[-1]:.2f}")
        st.write(f"30일 최고가: ${df['high'].max():.2f}")
        st.write(f"30일 최저가: ${df['low'].min():.2f}")