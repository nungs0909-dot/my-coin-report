import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime

# ---------------------------------------------------------
# 1. 기본 설정 및 디자인
# ---------------------------------------------------------
st.set_page_config(page_title="스마트 머니 트래커", page_icon="💎", layout="wide")

st.title("💎 스마트 머니 트래커")
st.markdown("""
이 리포트는 시가총액 상위 20개 코인의 **일봉(Daily Candle)**을 분석합니다.
단순 등락이 아니라 **'거래량의 이상 징후'**를 포착하는 데 집중합니다.
""")
st.info(f"기준 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')} (데이터 출처: Binance)")

# ---------------------------------------------------------
# 2. 데이터 가져오기 (Binance Exchange)
# ---------------------------------------------------------
@st.cache_data(ttl=600)  # 10분마다 갱신
def get_market_analysis():
    exchange = ccxt.binance()
    # 상위 20개 코인 수동 리스트 (안정적인 분석을 위해 메이저 위주 선정)
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT',
        'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'TRX/USDT', 'DOT/USDT',
        'LINK/USDT', 'MATIC/USDT', 'LTC/USDT', 'BCH/USDT', 'UNI/USDT',
        'XLM/USDT', 'ATOM/USDT', 'ETC/USDT', 'FIL/USDT', 'NEAR/USDT'
    ]
    
    report_list = []
    
    # 진행률 표시바
    progress_bar = st.progress(0)
    
    for i, symbol in enumerate(symbols):
        try:
            # 최근 5일치 일봉 데이터 가져오기 (Open, High, Low, Close, Volume)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=5)
            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            # 어제 데이터 (확정된 캔들) = 뒤에서 두 번째 [-2]
            # 그제 데이터 (비교군) = 뒤에서 세 번째 [-3]
            yesterday = df.iloc[-2]
            day_before = df.iloc[-3]
            
            # 변동률 계산
            price_change_pct = ((yesterday['close'] - yesterday['open']) / yesterday['open']) * 100
            vol_change_pct = ((yesterday['volume'] - day_before['volume']) / day_before['volume']) * 100
            
            # 변동성(High - Low) 계산
            volatility = ((yesterday['high'] - yesterday['low']) / yesterday['low']) * 100
            
            report_list.append({
                'coin': symbol.replace('/USDT', ''),
                'price': yesterday['close'],
                'price_change': price_change_pct,
                'vol_change': vol_change_pct,
                'volatility': volatility,
                'volume': yesterday['volume']
            })
            
        except Exception as e:
            continue
            
        # 진행률 업데이트
        progress_bar.progress((i + 1) / len(symbols))
            
    progress_bar.empty() # 완료되면 바 숨기기
    return pd.DataFrame(report_list)

# 데이터 로드
df = get_market_analysis()

st.divider()

# ---------------------------------------------------------
# 3. 핵심 조건별 필터링 (사용자 요청 사항)
# ---------------------------------------------------------

# Tab을 사용하여 깔끔하게 정리
tab1, tab2, tab3 = st.tabs(["🔥 거래량 급증", "👀 매집 의심 (횡보+거래량)", "🌊 변동성 확대"])

# [조건 1] 거래량이 전날 대비 크게 증가 (50% 이상 증가)
with tab1:
    st.header("전날 대비 거래량 폭발 🔥")
    st.caption("가격 방향과 상관없이, 시장의 관심이 갑자기 쏠린 코인입니다.")
    
    condition1 = df[df['vol_change'] > 50].sort_values(by='vol_change', ascending=False)
    
    if not condition1.empty:
        # 보기 좋게 포맷팅
        display_df = condition1[['coin', 'vol_change', 'price_change']].copy()
        display_df.columns = ['코인명', '거래량 증가율', '가격 등락률']
        display_df['거래량 증가율'] = display_df['거래량 증가율'].apply(lambda x: f"+{x:.1f}% 🔺")
        display_df['가격 등락률'] = display_df['가격 등락률'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("어제 거래량이 50% 이상 급증한 코인이 없습니다.")

# [조건 2] 가격은 횡보인데 거래량만 증가 (매집/손바뀜 의심)
# 기준: 가격 변동폭이 -3% ~ +3% 사이인데, 거래량은 20% 이상 증가
with tab2:
    st.header("폭풍전야 (횡보 + 거래량 증가) 👀")
    st.caption("가격은 잠잠한데 거래량만 늘었습니다. 세력이 몰래 담고 있거나(매집), 물량을 넘기는 중(분산)일 수 있습니다.")
    
    condition2 = df[
        (df['price_change'].abs() < 3) &  # 가격 변동이 3% 미만 (횡보)
        (df['vol_change'] > 20)           # 거래량은 20% 이상 증가
    ].sort_values(by='vol_change', ascending=False)
    
    if not condition2.empty:
        display_df = condition2[['coin', 'price', 'vol_change', 'price_change']].copy()
        display_df.columns = ['코인명', '현재가', '거래량 증가율', '가격 등락률']
        display_df['거래량 증가율'] = display_df['거래량 증가율'].apply(lambda x: f"+{x:.1f}% 🔺")
        display_df['가격 등락률'] = display_df['가격 등락률'].apply(lambda x: f"{x:.1f}% (횡보)")
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("조건(횡보+거래량증가)에 맞는 특이 코인이 없습니다.")

# [조건 3] 변동성이 갑자기 커진 코인
# 기준: 하루 고가와 저가의 차이(변동성)가 5% 이상인 것
with tab3:
    st.header("위아래로 흔드는 코인 (변동성) 🌊")
    st.caption("고가와 저가의 차이가 큽니다. 단타 기회가 있거나 위험할 수 있습니다.")
    
    condition3 = df[df['volatility'] > 5].sort_values(by='volatility', ascending=False)
    
    if not condition3.empty:
        display_df = condition3[['coin', 'volatility', 'price_change']].copy()
        display_df.columns = ['코인명', '일일 변동성(고저차)', '마감 등락률']
        display_df['일일 변동성(고저차)'] = display_df['일일 변동성(고저차)'].apply(lambda x: f"{x:.1f}% 〰️")
        display_df['마감 등락률'] = display_df['마감 등락률'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("변동성이 5% 이상인 코인이 없습니다.")

# 새로고침 버튼
if st.button("🔄 데이터 다시 분석하기"):
    st.cache_data.clear()
