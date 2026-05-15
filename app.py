import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly.express as px

# =====================================
# ⚙️ PAGE CONFIG & METOC NAVY CSS STYLE
# =====================================
st.set_page_config(page_title="METOC Lanud RSN - WIBB", layout="wide", page_icon="✈️")

st.markdown("""
<style>
    /* US Navy METOC Inspired Theme */
    body {background-color: #f4f6f9;}
    .stApp {background-color: #f4f6f9;}
    
    /* Header Banner */
    .metoc-header {
        background-color: #1a365d; /* Navy Blue */
        color: white;
        padding: 15px 25px;
        border-bottom: 4px solid #a9df52; /* Tactical Green Accent */
        margin-bottom: 20px;
        border-radius: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .metoc-title {font-family: 'Arial Black', sans-serif; font-size: 24px; margin: 0;}
    .metoc-subtitle {font-family: 'Consolas', monospace; font-size: 14px; color: #a9df52;}
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #2c3e50;
        color: white;
    }
    .css-1d391kg, .css-1dp5vir {color: white !important;} /* Sidebar text */
    
    /* Metrics and text */
    div[data-testid="stMetricValue"] {color: #1a365d !important; font-weight: bold;}
    h1, h2, h3 {color: #1a365d; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;}
    
    /* Button */
    .stButton>button {
        background-color: #1a365d; color: white; border: 1px solid #1a365d; 
        border-radius: 4px; font-weight: bold; width: 100%;
    }
    .stButton>button:hover {background-color: #a9df52; color: #1a365d; border-color: #a9df52;}
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {
        background-color: #e2e8f0; border-radius: 4px 4px 0px 0px; 
        padding: 10px 20px; color: #1a365d; font-weight: bold;
    }
    .stTabs [aria-selected="true"] {background-color: #1a365d; color: white;}
</style>
""", unsafe_allow_html=True)

# =====================================
# 🪖 HEADER BANNER
# =====================================
st.markdown("""
<div class="metoc-header">
    <div>
        <p class="metoc-title">METEOROLOGY & CLIMATOLOGY CENTER</p>
        <p class="metoc-subtitle">ROESMIN NURJADIN AIR FORCE BASE (WIBB) | TACTICAL WEATHER COMMAND</p>
    </div>
    <div>
        <h2 style="color:white; margin:0; border:none;">✈️ 📡 🛰️</h2>
    </div>
</div>
""", unsafe_allow_html=True)

# =====================================
# 🔹 TAB NAVIGATION
# =====================================
tab1, tab2, tab3 = st.tabs([
    "📡 LIVE QAM METAR (WIBB)", 
    "🛰️ TACTICAL FORECAST (BMKG)", 
    "📊 AERODROME CLIMATOLOGICAL SUMMARY"
])

# =====================================
# TAB 1: QAM METAR (WIBB)
# =====================================
with tab1:
    st.subheader("Live Meteorological Report (QAM) - WIBB")
    
    METAR_API = "https://aviationweather.gov/api/data/metar"
    
    def fetch_metar():
        try:
            r = requests.get(METAR_API, params={"ids": "WIBB", "format": "raw"}, timeout=10)
            r.raise_for_status()
            return r.text.strip()
        except:
            return "WIBB METAR DATA UNAVAILABLE"

    # Parsers
    def parse_metar_element(metar_str, regex, default="-"):
        match = re.search(regex, metar_str)
        return match if match else default

    metar = fetch_metar()
    now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
    
    # Simple parsing logic
    wind_match = re.search(r'(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT', metar)
    wind_str = f"{wind_match.group(1)}° / {wind_match.group(2)} kt" if wind_match else "-"
    vis_match = re.search(r' (\d{4}) ', metar)
    vis_str = f"{vis_match.group(1)} m" if vis_match else "-"
    temp_match = re.search(r' (M?\d{2})/(M?\d{2})', metar)
    temp_str = f"{temp_match.group(1)} / {temp_match.group(2)} °C".replace('M', '-') if temp_match else "-"
    qnh_match = re.search(r' Q(\d{4})', metar)
    qnh_str = f"{qnh_match.group(1)} hPa" if qnh_match else "-"

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"**Date/Time:** {now}")
        st.markdown(f"**Aerodrome:** WIBB (Pekanbaru)")
        st.info(f"**RAW METAR:**\n\n{metar}")
    
    with col2:
        c1, c2 = st.columns(2)
        c1.metric("Surface Wind", wind_str)
        c2.metric("Visibility", vis_str)
        c1.metric("Temp / Dewpoint", temp_str)
        c2.metric("QNH", qnh_str)

# =====================================
# TAB 2: BMKG TACTICAL FORECAST
# =====================================
with tab2:
    st.subheader("Integrated BMKG Tactical Forecast - Riau Province")
    API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
    
    @st.cache_data(ttl=600)
    def fetch_forecast():
        # ADM1 14 = Riau (Kode BMKG untuk Riau)
        resp = requests.get(API_BASE, params={"adm1": "14"}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None

    with st.spinner("Acquiring BMKG Data..."):
        bmkg_data = fetch_forecast()

    if bmkg_data and "data" in bmkg_data:
        # Cari data untuk Kota Pekanbaru
        pekanbaru_data = next((item for item in bmkg_data['data'] if item.get('lokasi', {}).get('kotkab') == 'Kota Pekanbaru'), None)
        
        if pekanbaru_data:
            st.success("Target Locked: KOTA PEKANBARU (WIBB)")
            # Flatten data cuaca
            rows = []
            for group in pekanbaru_data.get("cuaca", []):
                for obs in group:
                    obs['datetime'] = pd.to_datetime(obs.get("local_datetime"))
                    rows.append(obs)
            
            df_forecast = pd.DataFrame(rows)
            df_forecast['ws_kt'] = pd.to_numeric(df_forecast['ws'], errors='coerce') * 1.94384
            df_forecast['t'] = pd.to_numeric(df_forecast['t'], errors='coerce')
            
            fig = px.line(df_forecast, x="datetime", y=["t", "ws_kt"], 
                          title="Temperature (°C) & Wind Speed (KT) Forecast",
                          markers=True)
            fig.update_layout(template="plotly_white", hovermode="x unified", 
                              legend_title="Parameters", plot_bgcolor="#f4f6f9")
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Show Tabular Forecast Data"):
                st.dataframe(df_forecast[['datetime', 'weather_desc', 't', 'hu', 'ws_kt', 'wd_to']].head(10))
        else:
            st.warning("Data Pekanbaru tidak ditemukan di response API.")
    else:
        st.error("Gagal mengambil data dari API BMKG.")

# =====================================
# TAB 3: AERODROME CLIMATOLOGICAL SUMMARY (ACS)
# =====================================
with tab3:
    st.subheader("Aerodrome Climatological Summary (ACS) - WIBB")
    st.markdown("""
    *Meteogram ini adalah representasi visual dari ringkasan iklim (Climatological Summary) Lanud Roesmin Nurjadin. 
    Data di bawah ini merupakan **data simulasi/dummy** yang nantinya akan dihubungkan dengan database/excel hasil olahan skripsi Anda.*
    """)
    
    # 1. BUAT DATA DUMMY UNTUK SKRIPSI
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    acs_data = {
        'Month': months,
        'Mean_Temp': [26.8, 27.1, 27.5, 27.8, 28.1, 27.9, 27.6, 27.5, 27.4, 27.2, 26.9, 26.7],
        'Max_Temp': [31.5, 32.1, 33.0, 33.5, 33.8, 33.2, 32.8, 32.9, 32.5, 32.1, 31.8, 31.2],
        'Min_Temp': [22.1, 22.1, 22.0, 22.1, 22.4, 22.6, 22.4, 22.1, 22.3, 22.3, 22.0, 22.2],
        'Rainfall_mm': [240, 190, 250, 280, 210, 150, 130, 160, 200, 290, 320, 280],
        'Haze_Days': [2, 3, 5, 2, 4, 8, 12, 15, 10, 5, 2, 1], # Asap/Haze sering terjadi di Pekanbaru
        'Mean_Wind_Kt': [4.5, 5.0, 4.8, 4.2, 4.0, 4.5, 5.2, 5.5, 4.9, 4.5, 4.2, 4.3]
    }
    df_acs = pd.DataFrame(acs_data)
    
    # 2. PLOTING METEOGRAM ACS
    fig_acs = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("Temperature Climatology (°C)", "Mean Monthly Rainfall (mm)", "Frequency of Haze/Smoke Days", "Mean Wind Speed (Kt)"),
        row_heights=[0.3, 0.25, 0.25, 0.2]
    )

    # Row 1: Temperature (Max, Mean, Min)
    fig_acs.add_trace(go.Scatter(x=df_acs['Month'], y=df_acs['Max_Temp'], name='Max Temp', line=dict(color='red', width=2)), row=1, col=1)
    fig_acs.add_trace(go.Scatter(x=df_acs['Month'], y=df_acs['Mean_Temp'], name='Mean Temp', line=dict(color='green', width=3)), row=1, col=1)
    fig_acs.add_trace(go.Scatter(x=df_acs['Month'], y=df_acs['Min_Temp'], name='Min Temp', line=dict(color='blue', width=2)), row=1, col=1)

    # Row 2: Rainfall
    fig_acs.add_trace(go.Bar(x=df_acs['Month'], y=df_acs['Rainfall_mm'], name='Rainfall (mm)', marker_color='#1f77b4'), row=2, col=1)

    # Row 3: Haze Days (Relevan untuk Pekanbaru)
    fig_acs.add_trace(go.Bar(x=df_acs['Month'], y=df_acs['Haze_Days'], name='Days with Haze', marker_color='#ff7f0e'), row=3, col=1)

    # Row 4: Wind
    fig_acs.add_trace(go.Scatter(x=df_acs['Month'], y=df_acs['Mean_Wind_Kt'], name='Wind Speed', mode='lines+markers', line=dict(color='purple')), row=4, col=1)

    fig_acs.update_layout(
        height=900,
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
        plot_bgcolor="#f8fafc"
    )
    
    st.plotly_chart(fig_acs, use_container_width=True)
    
    # 3. FITUR EXPORT (Sesuai kebutuhan sistem informasi skripsi)
    st.markdown("### 📥 Download ACS Data")
    csv_acs = df_acs.to_csv(index=False)
    st.download_button(
        label="Download ACS Table (CSV)",
        data=csv_acs,
        file_name='WIBB_ACS_Data.csv',
        mime='text/csv'
    )

# =====================================
# FOOTER / SIDEBAR
# =====================================
with st.sidebar:
    st.markdown("<h2 style='color:white; border-bottom:1px solid #a9df52;'>SYSTEM STATUS</h2>", unsafe_allow_html=True)
    st.markdown("🟢 **API BMKG:** ONLINE")
    st.markdown("🟢 **METAR (NOAA):** ONLINE")
    st.markdown("🟢 **ACS DATABASE:** CONNECTED")
    st.markdown("---")
    st.markdown("**Navigasi Cepat:**")
    st.markdown("- [BMKG Official](https://bmkg.go.id)")
    st.markdown("- [Aviation Weather](https://aviationweather.gov)")
    st.markdown("---")
    st.caption("Dikembangkan untuk Skripsi:\nPENGEMBANGAN AERODROME CLIMATOLOGICAL SUMMARY... \n\n© 2026")
