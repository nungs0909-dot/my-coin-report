import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# 웹사이트 제목 설정
st.set_page_config(page_title="코인 급변동 리포트", page_icon="🚀")
st.title("📊 나만의 코인 시장 리포트")
st.write(f"업데이트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 데이터 가져오기 (서버 과부하 방지를 위해 5분간 데이터 저장)
@st.cache_data(ttl=300)
def load_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false"
    }
    response = requests.get(url, params=params)
    return pd.DataFrame(response.json())

with st.spinner('실시간 데이터를 불러오는 중입니다...'):
    df = load_data()

# 분석 지표 계산 (거래 회전율)
df['turnover'] = df['total_volume'] / df['market_cap']

st.markdown("---")

# 1. 가격 급변동 코인 (5% 이상)
st.header("🚀 가격 급변동 (Top 5)")
volatility = df[(df['price_change_percentage_24h'] > 5) | (df['price_change_percentage_24h'] < -5)]

if not volatility.empty:
    top_vol = volatility.sort_values(by='price_change_percentage_24h', ascending=False).head(5)
    display_vol = top_vol[['symbol', 'current_price', 'price_change_percentage_24h']].copy()
    display_vol.columns = ['코인명', '현재가($)', '24H 변동률(%)']
    display_vol['코인명'] = display_vol['코인명'].str.upper()
    
    # 웹사이트에 표 그리기
    st.dataframe(display_vol, use_container_width=True)
else:
    st.info("현재 5% 이상 급변동하는 코인이 없습니다.")

st.markdown("---")

# 2. 거래량 폭발 코인 (회전율 30% 이상)
st.header("🔥 거래량 폭발 (숨은 세력 찾기)")
st.caption("시가총액 대비 거래량이 30% 이상 터진 코인입니다.")

volume_spike = df[df['turnover'] > 0.3]

if not volume_spike.empty:
    top_vol_spike = volume_spike.sort_values(by='turnover', ascending=False).head(5)
    display_spike = top_vol_spike[['symbol', 'current_price', 'turnover']].copy()
    display_spike['turnover'] = (display_spike['turnover'] * 100).round(1).astype(str) + '%'
    display_spike.columns = ['코인명', '현재가($)', '회전율(%)']
    display_spike['코인명'] = display_spike['코인명'].str.upper()

    st.dataframe(display_spike, use_container_width=True)
else:
    st.info("현재 거래량이 폭발한 특이 코인이 없습니다.")

# 새로고침 (캐시 지우기)
if st.button("🔄 최신 데이터 다시 불러오기"):
    st.cache_data.clear()
