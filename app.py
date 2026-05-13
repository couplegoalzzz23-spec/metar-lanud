import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =====================================
# ⚙️ KONFIGURASI DASAR & DATABASE LANUD
# =====================================
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")

# Database Terintegrasi: ICAO (Aviation), WMO (Synoptic), ADM1 (Region Code)
LANUD_DATABASE = {
    "Lanud Halim Perdanakusuma (Jakarta)": {"icao": "WIHH", "wmo": "96749", "adm1": "31"},
    "Lanud Atang Sendjaja (Bogor)": {"icao": "WIAW", "wmo": "96753", "adm1": "32"},
    "Lanud Iswahjudi (Madiun)": {"icao": "WARW", "wmo": "96914", "adm1": "35"},
    "Lanud Abdulrachman Saleh (Malang)": {"icao": "WARA", "wmo": "96925", "adm1": "35"},
    "Lanud Sultan Hasanuddin (Makassar)": {"icao": "WAAA", "wmo": "97180", "adm1": "73"},
    "Lanud Roesmin Nurjadin (Pekanbaru)": {"icao": "WIBB", "wmo": "96109", "adm1": "14"},
    "Lanud Supadio (Pontianak)": {"icao": "WIOO", "wmo": "96581", "adm1": "61"},
    "Lanud Soewondo (Medan)": {"icao": "WIMK", "wmo": "96035", "adm1": "12"},
    "Lanud Sam Ratulangi (Manado)": {"icao": "WAMM", "wmo": "97014", "adm1": "71"},
    "Lanud El Tari (Kupang)": {"icao": "WATT", "wmo": "97268", "adm1": "53"},
    "Lanud Silas Papare (Jayapura)": {"icao": "WAJJ", "wmo": "97502", "adm1": "91"},
    "Lanud Suryadarma (Subang)": {"icao": "WICN", "wmo": "96741", "adm1": "32"},
    "Lanud Adisutjipto (Yogyakarta)": {"icao": "WAHH", "wmo": "96839", "adm1": "34"},
    "Lanud Adisumarmo (Solo)": {"icao": "WAHQ", "wmo": "96837", "adm1": "33"},
    "Lanud Husein Sastranegara (Bandung)": {"icao": "WIBT", "wmo": "96733", "adm1": "32"},
    "Lanud Raden Sadjad (Ranai)": {"icao": "WION", "wmo": "96163", "adm1": "21"},
    "Lanud Pattimura (Ambon)": {"icao": "WAPP", "wmo": "97560", "adm1": "81"},
}

# =====================================
# 🌑 CSS — MILITARY STYLE
# =====================================
CSS_STYLES = """
<style>
body { background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", monospace; }
.met-report-table { border: 1px solid #2b3c2b; width: 100%; background-color: #0f1111; font-size: 0.9rem; border-collapse: collapse; }
.met-report-table th, .met-report-table td { border: 1px solid #2b3c2b; padding: 8px; text-align: left; }
.met-report-table th { background-color: #111; color: #a9df52; text-transform: uppercase; width: 45%; }
.met-report-header { text-align: center; background-color: #0b0c0c; color: #a9df52; font-weight: bold; font-size: 1.1rem; padding: 10px 0; border: 1px solid #2b3c2b; border-bottom: none; }
.met-report-subheader { text-align: center; color: #cfd2c3; font-size: 0.8rem; padding-bottom: 5px; border-left: 1px solid #2b3c2b; border-right: 1px solid #2b3c2b; }
.radar { position: relative; width: 150px; height: 150px; border-radius: 50%; border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 15px #33ff55; }
.radar:before { content: ""; position: absolute; top: 0; left: 0; width: 50%; height: 2px; background: linear-gradient(90deg, #33ff55, transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite; }
@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.flight-card { padding: 20px; background-color: #0f1111; border: 1px solid #2b3c2b; border-radius: 10px; margin-bottom: 20px; }
.metric-value { font-size: 1.8rem; color: #b6ff6d; font-weight: bold; }
.hud-glow { stroke: #0f0; stroke-width: 2; fill: none; filter: drop-shadow(0 0 6px #0f0); }
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# =====================================
# 📡 UTILITAS & LOGIC
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384
METER_TO_SM = 0.000621371

@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    params = {"adm1": adm1}
    resp = requests.get(API_BASE, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def process_weather_data(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            obs.update({k: lokasi.get(k) for k in ["adm1", "adm2", "provinsi", "kotkab", "lon", "lat"]})
            obs["local_datetime_dt"] = pd.to_datetime(obs.get("local_datetime"), errors="coerce")
            rows.append(obs)
    df = pd.DataFrame(rows)
    for c in ["t","hu","ws","vs","tp","tcc","wd_deg"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ws_kt"] = df["ws"] * MS_TO_KT
    return df

def get_ceiling_info(tcc):
    if pd.isna(tcc) or tcc < 1: return 99999, "SKC"
    elif tcc < 25: return 3500, "FEW"
    elif tcc < 50: return 2250, "SCT"
    elif tcc < 75: return 1250, "BKN"
    else: return 800, "OVC"

# =====================================
# 🎚️ SIDEBAR
# =====================================
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    lanud_selection = st.selectbox("🎯 Select Airbase (Lanud)", options=list(LANUD_DATABASE.keys()))
    
    # Auto-fill dari database
    db = LANUD_DATABASE[lanud_selection]
    icao_code = db["icao"]
    wmo_code = db["wmo"]
    adm1_code = db["adm1"]
    
    st.success(f"**ICAO:** {icao_code} | **WMO:** {wmo_code}")
    st.info(f"**Region ID:** {adm1_code}")
    
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.button("🔄 Refresh Intel")
    st.markdown("---")
    show_qam = st.checkbox("Show QAM Form", value=True)
    show_hud = st.checkbox("Show HUD Overlay", value=True)

# =====================================
# 📡 DATA EXECUTION
# =====================================
st.title("Tactical Weather Operations Dashboard")

try:
    with st.spinner("📡 Intercepting BMKG Data..."):
        raw_data = fetch_forecast(adm1_code)
    
    mapping = { (e['lokasi'].get('kotkab') or e['lokasi'].get('adm2')): e for e in raw_data.get("data", []) }
    loc_choice = st.selectbox("📍 Area Sector", options=list(mapping.keys()))
    
    df = process_weather_data(mapping[loc_choice])
    now = df.iloc[0]

    # Pre-calculations
    temp = now['t']
    hum = now['hu']
    ws_kt = now['ws_kt']
    vis_m = now['vs']
    vis_sm = vis_m * METER_TO_SM
    dewpt = temp - ((100 - hum) / 5)
    ceil_ft, ceil_label = get_ceiling_info(now['tcc'])

    # =====================================
    # ✈ KEY METRICS PANEL
    # =====================================
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"TEMP<div class='metric-value'>{temp}°C</div>", unsafe_allow_html=True)
    c2.markdown(f"WIND<div class='metric-value'>{ws_kt:.1f} KT</div>", unsafe_allow_html=True)
    c3.markdown(f"VISIBILITY<div class='metric-value'>{vis_sm:.1f} SM</div>", unsafe_allow_html=True)
    c4.markdown(f"CEILING<div class='metric-value'>{ceil_ft if ceil_ft < 90000 else 'CLR'} FT</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # =====================================
    # 🟢 HUD OVERLAY
    # =====================================
    if show_hud:
        wdir = int(now['wd_deg'])
        dx = np.sin(np.radians(wdir)) * 80
        dy = -np.cos(np.radians(wdir)) * 80
        
        hud_svg = f"""
        <div style="background: rgba(0,20,0,0.8); border: 1px solid #0f0; border-radius: 10px; padding: 15px; margin-bottom: 20px;">
            <div style="color: #0f0; text-align: center; font-size: 0.8rem; margin-bottom: 10px;">F-16 TACTICAL HUD OVERLAY</div>
            <svg viewBox="0 0 800 200" style="width:100%; height:150px;">
                <line x1="100" y1="100" x2="700" y2="100" stroke="#0f0" stroke-width="1" stroke-dasharray="5,5"/>
                <circle cx="400" cy="100" r="5" fill="#0f0"/>
                <line x1="400" y1="100" x2="{400+dx}" y2="{100+dy}" stroke="#0f0" stroke-width="3"/>
                <text x="400" y="30" fill="#0f0" font-size="20" text-anchor="middle">HDG {wdir:03d}°</text>
                <text x="50" y="180" fill="#0f0" font-size="14">VIS: {vis_m}M</text>
                <text x="750" y="180" fill="#0f0" font-size="14" text-anchor="end">WIND: {ws_kt:.1f}KT</text>
            </svg>
        </div>
        """
        st.markdown(hud_svg, unsafe_allow_html=True)

    # =====================================
    # 📝 QAM REPORT
    # =====================================
    if show_qam:
        qam_html = f"""
        <div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div>
        <div class="met-report-subheader">DINAS PENGEMBANGAN OPERASI</div>
        <div class="met-report-header" style="border-top: 1px solid #2b3c2b;">METEOROLOGICAL REPORT (QAM)</div>
        <table class="met-report-table">
            <tr><th>OBS TIME</th><td>{now['local_datetime']} L / {now['utc_datetime']} Z</td></tr>
            <tr><th>AERODROME / WMO</th><td>{icao_code} / {wmo_code}</td></tr>
            <tr><th>SURFACE WIND</th><td>{wdir}° / {ws_kt:.1f} KT</td></tr>
            <tr><th>VISIBILITY</th><td>{vis_m} M ({vis_sm:.1f} SM)</td></tr>
            <tr><th>WEATHER</th><td>{now['weather_desc']}</td></tr>
            <tr><th>CLOUD / CEILING</th><td>{now['tcc']}% / {ceil_ft} FT ({ceil_label})</td></tr>
            <tr><th>TEMP / DP / RH</th><td>T: {temp}°C / DP: {dewpt:.1f}°C / RH: {hum}%</td></tr>
            <tr><th>REMARKS</th><td>Lanud {lanud_selection} - Sector {loc_choice}</td></tr>
        </table>
        """
        st.markdown(qam_html, unsafe_allow_html=True)
        st.download_button("⬇ Download QAM", data=qam_html, file_name=f"QAM_{icao_code}.html", mime="text/html")

    # =====================================
    # 📊 WINDROSE & TRENDS (FIXED)
    # =====================================
    st.markdown("---")
    st.subheader("🌪️ Windrose & Analysis")
    if not df.empty:
        fig_wind = px.bar_polar(df, r="ws_kt", theta="wd_deg", color="ws_kt",
                                template="plotly_dark", title="Wind Direction Distribution")
        st.plotly_chart(fig_wind, use_container_width=True)

except Exception as e:
    st.error(f"Operational Error: {e}")
