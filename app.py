import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# =====================================
# ⚙️ KONFIGURASI DASAR
# =====================================
st.set_page_config(page_title="Tactical Weather Ops — BMKG Lanud Edition", layout="wide")

# =====================================
# 🌑 DATABASE LANUD INDONESIA (ICAO MAPPING)
# =====================================
LANUD_DB = {
    "WIII": {"name": "Lanud Halim Perdanakusuma (Jakarta)", "adm1": "31", "city": "Jakarta Timur"},
    "WICC": {"name": "Lanud Husein Sastranegara (Bandung)", "adm1": "32", "city": "Bandung"},
    "WIAW": {"name": "Lanud Atang Sendjaja (Bogor)", "adm1": "32", "city": "Bogor"},
    "WARI": {"name": "Lanud Iswahjudi (Madiun)", "adm1": "35", "city": "Magetan"},
    "WARA": {"name": "Lanud Abdulrachman Saleh (Malang)", "adm1": "35", "city": "Malang"},
    "WAHH": {"name": "Lanud Adisutjipto (Yogyakarta)", "adm1": "34", "city": "Sleman"},
    "WARQ": {"name": "Lanud Adisumarmo (Solo)", "adm1": "33", "city": "Boyolali"},
    "WIBB": {"name": "Lanud Roesmin Nurjadin (Pekanbaru)", "adm1": "14", "city": "Pekanbaru"},
    "WIMB": {"name": "Lanud Soewondo (Medan)", "adm1": "12", "city": "Medan"},
    "WAAA": {"name": "Lanud Sultan Hasanuddin (Makassar)", "adm1": "73", "city": "Maros"},
    "WITT": {"name": "Lanud Sultan Iskandar Muda (Aceh)", "adm1": "11", "city": "Aceh Besar"},
    "WIMG": {"name": "Lanud Sutan Sjahrir (Padang)", "adm1": "13", "city": "Padang"},
    "WIPR": {"name": "Lanud Sri Mulyono Herlambang (Palembang)", "adm1": "16", "city": "Palembang"},
    "WIOO": {"name": "Lanud Supadio (Pontianak)", "adm1": "61", "city": "Kubu Raya"},
    "WIPL": {"name": "Lanud Fatmawati Soekarno (Bengkulu)", "adm1": "17", "city": "Bengkulu"},
    "WIKK": {"name": "Lanud H.AS Hanandjoeddin (Belitung)", "adm1": "19", "city": "Belitung"},
    "WIDD": {"name": "Lanud Hang Nadim (Batam)", "adm1": "21", "city": "Batam"},
    "WAMM": {"name": "Lanud Sam Ratulangi (Manado)", "adm1": "71", "city": "Manado"},
    "WAPP": {"name": "Lanud Pattimura (Ambon)", "adm1": "81", "city": "Ambon"},
    "WAJJ": {"name": "Lanud Silas Papare (Jayapura)", "adm1": "94", "city": "Jayapura"},
}

# =====================================
# 🌑 CSS — MILITARY STYLE
# =====================================
CSS_STYLES = """
<style>
body { background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", monospace; }
.met-report-table { border: 1px solid #2b3c2b; width: 100%; margin-bottom: 20px; background-color: #0f1111; font-size: 0.95rem; border-collapse: collapse; }
.met-report-table th, .met-report-table td { border: 1px solid #2b3c2b; padding: 10px; text-align: left; }
.met-report-table th { background-color: #111; color: #a9df52; text-transform: uppercase; width: 40%; font-size: 0.8rem; }
.met-report-table td { color: #dfffe0; font-weight: bold; }
.met-report-header { text-align: center; background-color: #1a2a1f; color: #a9df52; font-weight: bold; padding: 10px; border: 1px solid #2b3c2b; }
.radar { position: relative; width: 150px; height: 150px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%); border: 2px solid #33ff55; margin: auto; box-shadow: 0 0 15px #33ff55; }
.radar:before { content: ""; position: absolute; top: 0; left: 0; width: 50%; height: 2px; background: #33ff55; transform-origin: 100% 50%; animation: sweep 3s linear infinite; }
@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.flight-card { padding: 20px; background-color: #0f1111; border: 1px solid #2b3c2b; border-radius: 8px; margin-bottom: 20px; }
.metric-label { font-size: 0.75rem; color: #9fa8a0; text-transform: uppercase; }
.metric-value { font-size: 1.8rem; color: #b6ff6d; font-weight: bold; }
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# =====================================
# 🧰 UTILITAS
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384 

@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    try:
        resp = requests.get(API_BASE, params={"adm1": adm1}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None

def safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if not np.isnan(v) else default
    except:
        return default

def estimate_dewpoint(temp, rh):
    if temp is None or rh is None: return None
    return temp - ((100 - rh) / 5)

# =====================================
# 🎚️ SIDEBAR
# =====================================
with st.sidebar:
    st.title("🛰️ Ops Controls")
    selected_icao = st.selectbox("🎯 Target Lanud (ICAO)", options=list(LANUD_DB.keys()))
    lanud = LANUD_DB[selected_icao]
    
    st.markdown(f"**{lanud['name']}**")
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    
    st.divider()
    show_map = st.checkbox("Show Map", value=True)
    show_qam = st.checkbox("Show QAM Report", value=True)
    
    # Auto Night/Day
    hour = datetime.now().hour
    mode_choice = st.radio("Display Mode", ["Auto", "Day", "Night"], horizontal=True)
    if mode_choice == "Auto":
        CURRENT_MODE = "night" if hour < 6 or hour > 18 else "day"
    else:
        CURRENT_MODE = mode_choice.lower()

# =====================================
# 📡 DATA PROCESSING
# =====================================
st.title("Tactical Weather Operations Dashboard")

raw_data = fetch_forecast(lanud['adm1'])

if not raw_data:
    st.error("📡 COMMUNICATION LOSS: Failed to fetch data from BMKG.")
    st.stop()

entries = raw_data.get("data", [])
target_city = lanud['city'].lower()
selected_entry = next((e for e in entries if target_city in e.get("lokasi", {}).get("kotkab", "").lower()), entries[0])

# Flatten weather data
rows = []
lokasi = selected_entry.get("lokasi", {})
for group in selected_entry.get("cuaca", []):
    for obs in group:
        obs.update(lokasi)
        obs["local_dt"] = pd.to_datetime(obs.get("local_datetime"), errors="coerce")
        rows.append(obs)

df = pd.DataFrame(rows)
df["ws_kt"] = pd.to_numeric(df["ws"], errors="coerce") * MS_TO_KT
now = df.iloc[0]

# Metrics
temp = safe_float(now.get('t'))
rh = safe_float(now.get('hu'))
dewpt = estimate_dewpoint(temp, rh)
dewpt_str = f"{dewpt:.1f}°C" if dewpt is not None else "—"
vis_m = now.get('vs', '—')
vis_sm = f"{(safe_float(vis_m) * 0.000621371):.1f} SM"

# =====================================
# ✈ DASHBOARD DISPLAY
# =====================================
st.markdown('<div class="flight-card">', unsafe_allow_html=True)
st.markdown(f"### ✈ AIRBASE STATUS: {selected_icao}")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='metric-label'>Temperature</div><div class='metric-value'>{temp}°C</div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-label'>Wind Speed</div><div class='metric-value'>{now.get('ws_kt', 0):.1f} KT</div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-label'>Visibility</div><div class='metric-value'>{vis_m}M</div><small>{vis_sm}</small>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-label'>Conditions</div><div class='metric-value'>{now.get('weather_desc','—')}</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# HUD
hud_color = "#33ff55" if CURRENT_MODE == "night" else "#1a4a1a"
wdir = safe_float(now.get('wd_deg'))
dx = np.sin(np.radians(wdir)) * 70
dy = -np.cos(np.radians(wdir)) * 70

st.markdown(f"""
<div style="background:#050505; border: 2px solid {hud_color}; border-radius:15px; padding:20px; text-align:center;">
    <h5 style="color:{hud_color};">TACTICAL HUD - {selected_icao}</h5>
    <svg viewBox="0 0 400 200" width="100%" height="200">
        <circle cx="200" cy="100" r="80" stroke="{hud_color}" fill="none" stroke-width="1" stroke-dasharray="4"/>
        <line x1="200" y1="100" x2="{200+dx}" y2="{100+dy}" stroke="{hud_color}" stroke-width="3"/>
        <text x="200" y="20" fill="{hud_color}" font-size="14" text-anchor="middle">HDG {int(wdir):03d}°</text>
        <text x="50" y="180" fill="{hud_color}" font-size="12">VIS {vis_m}M</text>
        <text x="350" y="180" fill="{hud_color}" font-size="12" text-anchor="end">TEMP {temp}°C</text>
    </svg>
</div>
""", unsafe_allow_html=True)

# QAM Report
if show_qam:
    st.divider()
    st.markdown('<div class="met-report-header">METEOROLOGICAL REPORT (QAM REPLICATION)</div>', unsafe_allow_html=True)
    qam_html = f"""
    <table class="met-report-table">
        <tr><th>AERODROME / ICAO</th><td>{selected_icao} - {lanud['name']}</td></tr>
        <tr><th>OBS TIME (LOCAL)</th><td>{now.get('local_datetime','—')}</td></tr>
        <tr><th>SURFACE WIND</th><td>{now.get('wd_deg','—')}° / {now.get('ws_kt', 0):.1f} KT</td></tr>
        <tr><th>HORIZONTAL VISIBILITY</th><td>{vis_m} M ({vis_sm})</td></tr>
        <tr><th>PRESENT WEATHER</th><td>{now.get('weather_desc','—')}</td></tr>
        <tr><th>TEMPERATURE / DEW POINT</th><td>T: {temp}°C / DP: {dewpt_str}</td></tr>
        <tr><th>HUMIDITY</th><td>{rh}%</td></tr>
    </table>
    """
    st.markdown(qam_html, unsafe_allow_html=True)

# Map
if show_map:
    st.divider()
    st.subheader("🗺️ Tactical Position")
    lat, lon = safe_float(now.get('lat')), safe_float(now.get('lon'))
    st.map(pd.DataFrame({'lat': [lat], 'lon': [lon]}), zoom=12)

st.caption(f"Military Weather Ops v2.5 | {datetime.now().strftime('%H:%M:%S')} Z | Standby.")
