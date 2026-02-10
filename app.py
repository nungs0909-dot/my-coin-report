import streamlit as st
import ccxt
import pandas as pd
from datetime import datetime
import time

# ---------------------------------------------------------
# 1. 기본 설정
# ---------------------------------------------------------
st.set_page_config(page_title="Binance 스마트 트래커", page_icon="🔶", layout="wide")

st.title("🔶 Binance 스마트 트래커")
st.markdown("""
세계 1위 거래소 **Binance**의 데이터를 직접 분석합니다.
**전날(Daily) 캔들**을 기준으로 '가격은 횡보하는데 거래량만 터진' 매집 코인을 찾습니다.
""")
st.caption(f"기준 시간: {datetime.now().strftime('%Y-%m-%d %H:%M')} KST")

# ---------------------------------------------------------
# 2. 데이터 가져오기 (Binance API)
# ---------------------------------------------------------
@st.cache_data(ttl=600)
def get_binance_data():
    exchange = ccxt.binance({
        'enableRateLimit': True,  # 거래소 요청 속도 조절 (차단 방지)
    })
    
    # 분석할 메이저 코인 리스트 (선물/현물 공통 메이저)
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'BNB/USDT',
        'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'TRX/USDT', 'SHIB/USDT',
        'DOT/USDT', 'LINK/USDT', 'MATIC/USDT', 'LTC/USDT', 'UNI/USDT'
    ]
    
    report_list = []
    
    # 진행바 설정
    progress_text = "바이낸스 데이터 수집 중... (서버 상태에 따라 느릴 수 있습니다)"
    my_bar = st.progress(0, text=progress_text)
    
    for i, symbol in enumerate(symbols):
        try:
            # 일봉(1d) 데이터 5개만 가져오기
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=5)
            
            # [중요] 데이터가 비어있으면 건너뛰기 (에러 방지 핵심)
            if not ohlcv or len(ohlcv) < 3:
                continue

            df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            # 데이터 정리 (어제 확정봉 = 뒤에서 2번째)
            yesterday = df.iloc[-2]
            day_before = df.iloc[-3]
            
            # 1. 가격 등락률
            price_change_pct = ((yesterday['close'] - yesterday['open']) / yesterday['open']) * 100
            
            # 2. 거래량 변화율 (0으로 나누기 방지)
            if day_before['volume'] > 0:
                vol_change_pct = ((yesterday['volume'] - day_before['volume']) / day_before['volume']) * 100
            else:
                vol_change_pct = 0
            
            # 3. 변동성 (고가 - 저가)
            volatility = ((yesterday['high'] - yesterday['low']) / yesterday['low']) * 100
            
            report_list.append({
                'coin': symbol.replace('/USDT', ''),
                'price': yesterday['close'],
                'price_change': price_change_pct,
                'vol_change': vol_change_pct,
                'volatility': volatility
            })
            
            # 너무 빨리 요청하면 차단당하므로 0.1초 쉬기
            time.sleep(0.1)

        except Exception as e:
            # 에러가 나도 무시하고 다음 코인으로 넘어감
            continue
        
        # 진행바 업데이트
        my_bar.progress((i + 1) / len(symbols), text=progress_text)
    
    my_bar.empty()
    return pd.DataFrame(report_list)

# 데이터 실행
df = get_binance_data()

# ---------------------------------------------------------
# 3. 결과 보여주기
# ---------------------------------------------------------

if df.empty:
    st.error("⚠️ 데이터 수집 실패!")
    st.warning("""
    **원인:** 바이낸스가 현재 이 웹사이트 서버(Streamlit Cloud)의 접속을 일시적으로 차단했습니다.
    
    **해결책:** 이 코드를 웹사이트가 아니라 **사용자님의 PC**에서 실행하면 100% 작동합니다.
    (내 컴퓨터 IP는 차단하지 않기 때문입니다.)
    """)
else:
    st.success(f"✅ 총 {len(df)}개 코인 분석 완료")
    st.divider()

    tab1, tab2, tab3 = st.tabs(["🔥 거래량 급증", "👀 폭풍전야 (횡보+매집)", "🌊 변동성 확대"])

    # [조건 1] 거래량 급증 (50% 이상)
    with tab1:
        st.header("전날 대비 거래량 폭발 🔥")
        condition1 = df[df['vol_change'] > 50].sort_values(by='vol_change', ascending=False)
        if not condition1.empty:
            st.dataframe(
                condition1[['coin', 'vol_change', 'price_change']]
                .style.format({'vol_change': "+{:.1f}%", 'price_change': "{:.1f}%"}),
                use_container_width=True
            )
        else:
            st.info("거래량이 50% 이상 폭발한 코인이 없습니다.")

    # [조건 2] 폭풍전야 (가격 횡보 + 거래량 증가) - 사용자 핵심 요청
    with tab2:
        st.header("폭풍전야 (횡보 + 거래량 증가) 👀")
        st.caption("가격 변동은 ±3%로 조용한데, 거래량은 20% 이상 늘어난 '수상한' 코인")
        
        condition2 = df[
            (df['price_change'].abs() < 3) & 
            (df['vol_change'] > 20)
        ].sort_values(by='vol_change', ascending=False)
        
        if not condition2.empty:
            st.dataframe(
                condition2[['coin', 'price', 'vol_change', 'price_change']]
                .style.format({'price': "${:,.2f}", 'vol_change': "+{:.1f}%", 'price_change': "{:.1f}%"}),
                use_container_width=True
            )
        else:
            st.info("현재 횡보하면서 거래량이 증가하는 패턴이 없습니다.")

    # [조건 3] 변동성 확대
    with tab3:
        st.header("위아래로 흔드는 코인 🌊")
        condition3 = df[df['volatility'] > 5].sort_values(by='volatility', ascending=False)
        if not condition3.empty:
            st.dataframe(
                condition3[['coin', 'volatility', 'price_change']]
                .style.format({'volatility': "{:.1f}%", 'price_change': "{:.1f}%"}),
                use_container_width=True
            )
        else:
            st.info("변동성이 5% 이상인 코인이 없습니다.")

    if st.button("🔄 다시 조회"):
        st.cache_data.clear()
