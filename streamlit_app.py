import streamlit as st
from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime, timedelta
import time
import plotly.graph_objs as go

# Streamlit 페이지 설정
st.set_page_config(page_title="비트코인 분석(Bryan Cho)", layout="wide")

# 페이지 제목
st.title("비트코인 분석 대시보드")

# 사이드바 생성
st.sidebar.title("메뉴")
main_menu = st.sidebar.radio("메인 메뉴:", ["데이터 로드", "그래프", "분석"])

# AI 가격 예측 사이드바
st.sidebar.title("AI 가격 예측")
target_price = st.sidebar.number_input("목표 가격 (USD)", min_value=0.0, value=50000.0, step=100.0)
position = st.sidebar.selectbox("포지션", ["롱", "숏"])
leverage = st.sidebar.number_input("레버리지", min_value=1, max_value=100, value=1, step=1)

if st.sidebar.button("분석"):
    st.sidebar.empty()  # 기존 사이드바 내용 지우기
    st.sidebar.subheader("AI 비트코인 가격 예측 결과")
    st.sidebar.write(f"목표 가격: ${target_price:,.2f}")
    st.sidebar.write(f"선택한 포지션: {position}")
    st.sidebar.write(f"레버리지: {leverage}x")
    
    # AI 예측 결과 (예시)
    st.sidebar.info("AI 모델이 비트코인 가격 데이터를 분석 중입니다...")
    
    # 예시 차트 (실제 AI 예측 결과로 대체 가능)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2, 3, 4, 5], y=[10, 11, 12, 13, 14], mode='lines+markers', name='예측 가격'))
    fig.update_layout(title='AI 예측 비트코인 가격 추세 (예시)', xaxis_title='시간', yaxis_title='가격 (USD)')
    st.sidebar.plotly_chart(fig, use_container_width=True)
    
    st.sidebar.markdown("### AI 예측 결과 해석")
    st.sidebar.write("1. 단기 전망: 상승 추세")
    st.sidebar.write("2. 중기 전망: 변동성 증가")
    st.sidebar.write("3. 장기 전망: 불확실")
    
    st.sidebar.warning("주의: 이 예측은 예시이며, 실제 시장 상황과 다를 수 있습니다.")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**현재 분석 알고리즘 수정중**")
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
            df['date'] = df.index.date
            ohlc = df.groupby('date').agg({
                'price': ['first', 'max', 'min', 'last']
            }).reset_index()
            ohlc.columns = ['timestamp', 'open', 'high', 'low', 'close']
            ohlc['timestamp'] = pd.to_datetime(ohlc['timestamp'])
            ohlc.set_index('timestamp', inplace=True)
            
            # EMA 계산
            ohlc['EMA10'] = calculate_ema(ohlc, 10)
            ohlc['EMA20'] = calculate_ema(ohlc, 20)
            ohlc['EMA50'] = calculate_ema(ohlc, 50)
            ohlc['EMA100'] = calculate_ema(ohlc, 100)
            
            return ohlc
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

    # 최근 3개월 데이터만 선택
    three_months_ago = datetime.now() - timedelta(days=90)
    df_recent = df[df.index >= three_months_ago]

    fig = go.Figure()

    # 캔들스틱 차트 추가
    fig.add_trace(go.Candlestick(
        x=df_recent.index,
        open=df_recent['open'],
        high=df_recent['high'],
        low=df_recent['low'],
        close=df_recent['close'],
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
if main_menu == "데이터 로드":
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

elif main_menu == "그래프":
    if 'data' not in st.session_state:
        st.warning("먼저 데이터를 로드해주세요.")
    else:
        fig = create_graph(st.session_state['data'])
        st.plotly_chart(fig, use_container_width=True)

elif main_menu == "분석":
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