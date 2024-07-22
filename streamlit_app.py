import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import hmac
import hashlib
import base64
import warnings
import plotly.graph_objs as go
import json
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 정보 가져오기
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
API_PASS = os.getenv('API_PASS')
BASE_URL = os.getenv('BASE_URL')

# Streamlit 페이지 설정
st.set_page_config(page_title="비트코인 분석(Bryan Cho)", layout="wide")

def sign(message, secret):
    mac = hmac.new(bytes(secret, 'utf-8'), bytes(message, 'utf-8'), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode('utf-8')

def get_headers(method, request_path):
    timestamp = str(int(time.time() * 1000))
    message = timestamp + method + request_path
    signature = sign(message, API_SECRET)
    headers = {
        'Content-Type': 'application/json',
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': signature,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': API_PASS
    }
    return headers

# EMA 계산 함수
def calculate_ema(data, period, column='close'):
    return data[column].ewm(span=period, adjust=False).mean()

@st.cache_data(show_spinner=False)
def get_data(granularity="3600"):
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)
    
    start_timestamp = int(start_date.timestamp() * 1000)  # 밀리초 단위로 변경
    end_timestamp = int(end_date.timestamp() * 1000)  # 밀리초 단위로 변경
    
    request_path = f'/api/mix/v1/market/candles?symbol=BTCUSDT_UMCBL&granularity={granularity}&startTime={start_timestamp}&endTime={end_timestamp}'
    url = BASE_URL + request_path
    headers = get_headers('GET', request_path)
    
    #st.write(f"Request URL: {url}")  # URL 출력
    #st.write(f"Headers: {headers}")  # 헤더 출력
    
    response = requests.get(url, headers=headers)
    #st.write(f"API Response: {response.text}")  # API 응답 내용 출력
    #st.write(f"Response Status Code: {response.status_code}")  # 상태 코드 출력
    
    if response.status_code != 200:
        st.error(f"API 요청 실패: {response.status_code}")
        return None
    
    price_data = response.json()

    if not isinstance(price_data, list) or len(price_data) == 0:
        st.error("API에서 유효한 데이터를 가져오지 못했습니다.")
        return None

    df = pd.DataFrame(price_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'usdVolume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)

    # EMA 계산
    for period in [10, 20, 50, 100]:
        df[f'EMA{period}'] = df['close'].ewm(span=period, adjust=False).mean()

    return df


def create_candlestick_chart(df):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Candlestick'
    ))

    ema_settings = {
        10: {'color': '#DAA520', 'width': 2},
        20: {'color': 'red', 'width': 2},
        50: {'color': 'blue', 'width': 2},
        100: {'color': 'black', 'width': 2}
    }

    # EMA 선
    for period, settings in ema_settings.items():
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[f'EMA{period}'],
            mode='lines',
            name=f'EMA {period}',
            line=dict(color=settings['color'], width=settings['width'])
        ))

    fig.update_layout(
        title='비트코인 가격 차트',
        yaxis_title='가격 (USD)',
        xaxis_title='날짜',
        xaxis_rangeslider_visible=False
    )

    return fig

def create_analysis(df):
    if df.empty:
        return "데이터가 없습니다. 데이터를 먼저 로드해주세요."

    last_price = df['close'].iloc[-1]
    max_price = df['high'].max()
    min_price = df['low'].min()
    price_change = (df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0] * 100

    analysis_text = "## 비트코인 시장 분석\n\n최근 30일간의 비트코인 시장 동향:\n\n"
    analysis_text += f"- 현재 가격: ${last_price:.2f}\n"
    analysis_text += f"- 30일 최고가: ${max_price:.2f}\n"
    analysis_text += f"- 30일 최저가: ${min_price:.2f}\n"
    analysis_text += f"- 가격 변동률: {price_change:.2f}%\n"

    analysis_text += "\n### 시장 동향\n"
    analysis_text += f"{'상승' if price_change > 0 else '하락'} 추세를 보이고 있으며, \n"
    analysis_text += f"최근 30일 동안 ${min_price:.2f}에서 ${max_price:.2f} 사이에서 거래되었습니다.\n"

    analysis_text += "\n### 투자 유의사항\n암호화폐 시장은 변동성이 높습니다. 투자 결정 시 신중을 기하시기 바랍니다."

    return analysis_text

def get_trade_history():
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=30)  # 최근 30일 데이터
    
    start_timestamp = int(start_date.timestamp() * 1000)
    end_timestamp = int(end_date.timestamp() * 1000)
    
    request_path = f'/api/mix/v1/order/history?symbol=BTCUSDT_UMCBL&startTime={start_timestamp}&endTime={end_timestamp}'
    url = BASE_URL + request_path
    headers = get_headers('GET', request_path)
    
    st.write(f"요청 URL: {url}")
    st.write(f"요청 헤더: {headers}")
    
    try:
        response = requests.get(url, headers=headers)
        st.write(f"응답 상태 코드: {response.status_code}")
        
        response.raise_for_status()
        
        trade_data = response.json()
        
        if 'data' in trade_data and 'orderList' in trade_data['data']:
            order_list = trade_data['data']['orderList']
            if not order_list:
                st.warning("거래 내역이 없습니다.")
                return None
            
            df = pd.DataFrame(order_list)
            
            # 시간 컬럼 처리
            for time_col in ['cTime', 'uTime']:
                if time_col in df.columns:
                    df[time_col] = pd.to_datetime(df[time_col].astype(float), unit='ms')
            
            # 숫자 컬럼 처리
            numeric_columns = ['size', 'filledQty', 'fee', 'price', 'filledAmount', 'totalProfits']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 인덱스 설정
            if 'cTime' in df.columns:
                df.set_index('cTime', inplace=True)
            elif 'uTime' in df.columns:
                df.set_index('uTime', inplace=True)
            
            return df
        else:
            st.error("예상치 못한 API 응답 구조입니다.")
            return None
    
    except requests.exceptions.RequestException as e:
        st.error(f"API 요청 중 오류 발생: {str(e)}")
    except ValueError as e:
        st.error(f"JSON 파싱 중 오류 발생: {str(e)}")
    except Exception as e:
        st.error(f"예상치 못한 오류 발생: {str(e)}")
    
    return None

# 페이지 제목
st.title("비트코인 분석 대시보드")

# 메인 사이드바 생성
main_menu = st.sidebar.radio("메인 메뉴:", ["데이터 로드", "그래프", "분석", "내 거래 현황"])

# 메인 로직에서 데이터 로드 부분
if st.sidebar.button("데이터 로드", key="load_data_button"):
    try:
        with st.spinner("데이터를 불러오는 중..."):
            df = get_data()  # 기본 granularity 사용
        if df is not None and not df.empty:
            st.session_state['data'] = df
            st.sidebar.success("데이터 로드 완료!")
            st.write(df)
        else:
            st.sidebar.error("데이터를 불러오는데 실패했습니다.")
    except Exception as e:
        st.sidebar.error(f"데이터 로드 중 오류 발생: {str(e)}")

# AI 가격 예측 사이드바
st.sidebar.title("AI 가격 예측")
target_price = st.sidebar.number_input("목표 가격 (USD)", min_value=0.0, value=50000.0, step=100.0)
position = st.sidebar.selectbox("포지션", ["롱", "숏"])
leverage = st.sidebar.number_input("레버리지", min_value=1, max_value=100, value=1, step=1)

if st.sidebar.button("분석", key="analyze_button"):
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

# 메인 로직
if main_menu == "데이터 로드":
    if 'data' in st.session_state:
        st.write(st.session_state['data'])
    else:
        st.warning("데이터를 로드해주세요.")

elif main_menu == "그래프":
    timeframe = st.selectbox("시간 프레임 선택", ["일봉", "4시간봉", "1시간봉", "15분봉"])
    granularity_map = {
        "일봉": "86400",
        "4시간봉": "14400",
        "1시간봉": "3600",
        "15분봉": "900"
    }
    granularity = granularity_map[timeframe]

    try:
        df = get_data(granularity)
        if df is not None and not df.empty:
            st.session_state['data'] = df
            chart = create_candlestick_chart(df)
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.error("해당 시간 프레임의 데이터를 불러오지 못했습니다.")
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {str(e)}")

elif main_menu == "분석":
    if 'data' not in st.session_state:
        st.warning("먼저 데이터를 로드해주세요.")
    else:
        analysis = create_analysis(st.session_state['data'])
        st.markdown(analysis)
elif main_menu == "내 거래 현황":
    st.title("내 거래 현황")
    trade_history = get_trade_history()
    if trade_history is not None and not trade_history.empty:
        st.write("최근 거래 내역:")
        st.dataframe(trade_history)
        
        # 거래 통계
        total_trades = len(trade_history)
        st.write(f"총 거래 횟수: {total_trades}")
        
        # 'totalProfits' 컬럼이 있는 경우에만 수익/손실 거래 계산
        if 'totalProfits' in trade_history.columns:
            profitable_trades = len(trade_history[trade_history['totalProfits'] > 0])
            loss_trades = len(trade_history[trade_history['totalProfits'] < 0])
            st.write(f"수익 거래: {profitable_trades}")
            st.write(f"손실 거래: {loss_trades}")
            
            # 수익률 차트
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trade_history.index, y=trade_history['totalProfits'].cumsum(),
                                     mode='lines', name='누적 수익'))
            fig.update_layout(title='누적 수익 차트', xaxis_title='날짜', yaxis_title='누적 수익')
            st.plotly_chart(fig)
        else:
            st.warning("수익 정보를 찾을 수 없습니다.")
    elif trade_history is not None:
        st.warning("거래 내역이 없습니다.")
    else:
        st.error("거래 내역을 불러오는데 실패했습니다.")

# 추가 정보 표시
if 'data' in st.session_state:
    with st.sidebar.expander("최근 거래 정보"):
        df = st.session_state['data']
        if not df.empty:
            if 'close' in df.columns and not df['close'].empty:
                st.write(f"최근 종가: ${df['close'].iloc[-1]:.2f}")
            if 'high' in df.columns and not df['high'].empty:
                st.write(f"30일 최고가: ${df['high'].max():.2f}")
            if 'low' in df.columns and not df['low'].empty:
                st.write(f"30일 최저가: ${df['low'].min():.2f}")
        else:
            st.write("데이터가 없습니다. 데이터를 먼저 로드해주세요.")