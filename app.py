import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
from data_loader import DataLoader
from models import ExcelBitcoinModel
from utils import get_translation

st.set_page_config(page_title="Bitcoin Cycle Predictor", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for dark institutional theme and glassmorphism
st.markdown("""
<style>
    body { background-color: #0d1117; color: #c9d1d9; }
    .main .block-container { padding-top: 2rem; }
    .metric-card {
        background: rgba(22, 27, 34, 0.6);
        border: 1px solid rgba(48, 54, 61, 0.8);
        border-radius: 10px;
        padding: 20px;
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    }
    .hero-price {
        font-size: 4rem;
        font-weight: bold;
        color: #e6edf3;
        line-height: 1.1;
    }
    .green-text { color: #3fb950; font-weight: bold; }
    .red-text { color: #f85149; font-weight: bold; }
    .yellow-text { color: #d29922; font-weight: bold; }
    h3, h4 { color: #8b949e; font-weight: 500; margin-bottom: 0px; }
    .header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
    .header-ticker { text-align: right; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'lang' not in st.session_state:
    st.session_state.lang = 'es'
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

def t(key):
    return get_translation(st.session_state.lang, key)

with st.sidebar:
    lang = st.radio(t('lang_toggle'), ['ES', 'EN'], index=0 if st.session_state.lang == 'es' else 1)
    if lang == 'EN':
        st.session_state.lang = 'en'
    else:
        st.session_state.lang = 'es'

@st.cache_data(ttl=3600)
def load_all_data():
    dl = DataLoader()
    rt_data = dl.get_current_price_data()
    hist_df = dl.get_historical_prices()
    aths = dl.detect_aths(hist_df)
    return dl, rt_data, hist_df, aths

try:
    with st.spinner("Loading Market Data..."):
        dl, rt_data, hist_df, aths = load_all_data()
    st.session_state.data_loaded = True
except Exception as e:
    st.error(f"Error loading data: {e}")

if st.session_state.data_loaded:
    # Header Area
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.title(t('app_title'))
    with col3:
        st.markdown(f"""
        <div class='header-ticker'>
            <h3>BTC: ${rt_data['price']:,.0f}</h3>
            <span class='{"green-text" if rt_data["change_24h"] > 0 else "red-text"}'>{'+' if rt_data["change_24h"] > 0 else ''}{rt_data['change_24h']:.2f}% (24h)</span>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    # Input Area
    col_in1, col_in2, col_in3 = st.columns([1, 1, 2])
    with col_in1:
        st.subheader(t('target_date'))
        target_date = st.date_input("", datetime.date.today() + datetime.timedelta(days=365))
    with col_in2:
        st.subheader(t('reference_cycle'))
        selected_cycle = st.selectbox("", [t('auto'), "2017", "2021"])
        ref_cycle_map = {t('auto'): 'Auto', "2017": "2017", "2021": "2021"}
        actual_cycle_ref = ref_cycle_map[selected_cycle]

    bm = ExcelBitcoinModel(hist_df, rt_data['price'], aths)
    
    if st.button(t('predict_button'), use_container_width=True):
        if target_date <= datetime.date.today():
            st.warning("Please select a future date.")
        else:
            with st.spinner("Processing Model..."):
                pred = bm.predict(target_date, reference_cycle=actual_cycle_ref)
                
            # Layout for Results
            col_hero, col_metrics = st.columns([2, 1])
            
            with col_hero:
                upside = ((pred['estimated_price'] / rt_data['price']) - 1) * 100
                upside_class = "green-text" if upside > 0 else "red-text"
                upside_sign = "+" if upside > 0 else ""

                st.markdown(f"""
                <div class='metric-card'>
                    <h3>{t('estimated_price')}</h3>
                    <div class='hero-price'>${pred['estimated_price']:,.0f}</div>
                    <div style='margin-top: 10px; font-size: 1.1rem;'>
                        Crecimiento desde nivel actual: <span class='{upside_class}'>{upside_sign}{upside:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Probabilistic Range
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='display: flex; justify-content: space-between; font-size: 1.1rem;'>
                        <div style='text-align: left; color: #f85149; flex: 1;'>{t('bear_prob')}<br><b>${pred['bear']:,.0f}</b></div>
                        <div style='text-align: center; color: #d29922; flex: 1;'>{t('base_prob')}<br><b>${pred['base']:,.0f}</b></div>
                        <div style='text-align: right; color: #3fb950; flex: 1;'>{t('bull_prob')}<br><b>${pred['bull']:,.0f}</b></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with col_metrics:
                st.markdown(f"""
                <div class='metric-card'>
                    <h3>{t('market_phase')}</h3>
                    <h2 class='yellow-text'>{t(pred['market_phase'])}</h2>
                    <br>
                    <p style='color: #8b949e; font-size: 0.9rem;'>
                        <b>{t('days_since_ath')}:</b> {(datetime.date.today() - aths['current']['date']).days}<br>
                        <b>{t('drawdown')}:</b> {pred['drawdown']:.1f}%<br>
                        <b>{t('ratio_applied')}:</b> {pred['ratio']:.2f}x ({pred['reference_cycle']} Cycle)<br>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
            # Chart
            st.markdown(f"<h3>Comparativa de Caídas (Alineado a 1 Año Post-ATH)</h3>", unsafe_allow_html=True)
            try:
                df = hist_df.copy()
                curr_auth_date = aths['current']['date']
                
                fig = go.Figure()
                
                # Eje X basado en Meses de vida (0 a 12)
                def plot_aligned_cycle(cycle_year, color, name_key):
                    c_date = aths[cycle_year]['date']
                    c_price = aths[cycle_year]['price']
                    
                    df_c = df[df.index >= c_date].copy()
                    
                    if not df_c.empty:
                        df_c['days_since'] = [(d - c_date).days for d in df_c.index]
                        df_c = df_c[df_c['days_since'] <= 365]
                        
                        # Convertir días a meses transcurridos
                        df_c['months_since'] = [d / 30.44 for d in df_c['days_since']]
                        
                        df_c['pct_growth'] = (df_c['price'] / c_price) * 100
                        
                        fig.add_trace(go.Scatter(
                            x=df_c['months_since'], 
                            y=df_c['pct_growth'], 
                            mode='lines', 
                            name=f"{t(name_key)} (Inicio Alineado)", 
                            line=dict(color=color, width=2)
                        ))

                plot_aligned_cycle('2017', 'rgba(139, 148, 158, 0.4)', 'cycle_17')
                plot_aligned_cycle('2021', 'rgba(139, 148, 158, 0.7)', 'cycle_21')
                
                # Current Cycle
                c_date = aths['current']['date']
                c_price = aths['current']['price']
                df_curr = df[df.index >= c_date].copy()
                
                if not df_curr.empty:
                    df_curr['days_since'] = [(d - c_date).days for d in df_curr.index]
                    df_curr = df_curr[df_curr['days_since'] <= 365]
                    df_curr['months_since'] = [d / 30.44 for d in df_curr['days_since']]
                    df_curr['pct_growth'] = (df_curr['price'] / c_price) * 100
                    
                    fig.add_trace(go.Scatter(
                        x=df_curr['months_since'], 
                        y=df_curr['pct_growth'], 
                        mode='lines', 
                        name=f"{t('current_trajectory')} (Inicio Alineado)", 
                        line=dict(color='#56ff6a', width=3)
                    ))
                
                # Prediction Point (only if it falls within the 1-year timeline)
                if pred['days_target'] <= 365:
                    target_month = pred['days_target'] / 30.44
                    pred_pct = (pred['estimated_price'] / c_price) * 100
                    fig.add_trace(go.Scatter(
                        x=[target_month], y=[pred_pct], mode='markers', 
                        name='Target Date', marker=dict(color='white', size=12, symbol='star', line=dict(color='black', width=1))
                    ))
                
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#c9d1d9'),
                    xaxis_title="Meses Transcurridos desde el ATH", 
                    yaxis_title="% del Valor Máximo (ATH)",
                    yaxis=dict(ticksuffix="%"),
                    xaxis=dict(tick0=0, dtick=1), # Forzar que las marcas X sean números enteros de meses (1, 2, 3... 12)
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error drawing chart: {e}")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    st.caption(f"<div style='text-align: center; color: #8b949e; font-size: 0.85rem;'>{t('disclaimer')}</div>", unsafe_allow_html=True)
