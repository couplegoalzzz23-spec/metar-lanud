import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# =====================================
# ⚙️ KONFIGURASI DASAR
# =====================================
st.set_page_config(page_title="Tactical Weather Ops — BMKG", layout="wide")

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
    "WIDD": {"name": "Lanud Hang Nadim (Batam)", "adm1": "21", "city": "Batam"},
    "WAMM": {"name": "Lanud Sam Ratulangi (Manado)", "adm1": "71", "city": "Manado"},
    "WAPP": {"name": "Lanud Pattimura (Ambon)", "adm1": "81", "city": "Ambon"},
    "WAJJ": {"name": "Lanud Silas Papare (Jayapura)", "adm1": "94", "city": "Jayapura"},
}

# =====================================
# 🌑 CSS — MILITARY STYLE + RADAR + QAM
# =====================================
CSS_STYLES = """
<style>
body { background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", monospace; }
.met-report-table { border: 1px solid #2b3c2b; width: 100%; margin-bottom: 20px; background-color: #0f1111; font-size: 0.95rem; border-collapse: collapse; }
.met-report-table th, .met-report-table td { border: 1px solid #2b3c2b; padding: 8px; text-align: left; vertical-align: top; }
.met-report-table th { background-color: #111; color: #a9df52; text-transform: uppercase; width: 45%; font-size: 0.85rem; }
.met-report-table td { color: #dfffe0; width: 55%; font-weight: bold; }
.met-report-header { text-align: center; background-color: #0b0c0c; color: #a9df52; font-weight: bold; font-size: 1.1rem; padding: 10px 0; border: 1px solid #2b3c2b; border-bottom: none; }
.met-report-subheader { text-align: center; background-color: #0b0c0c; color: #cfd2c3; font-weight: normal; font-size: 0.8rem; padding-bottom: 5px; border: 1px solid #2b3c2b; border-top: none; border-bottom: none; }
.radar { position: relative; width: 160px; height: 160px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%); border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 20px #33ff55; }
.radar:before { content: ""; position: absolute; top: 0; left: 0; width: 50%; height: 2px; background: linear-gradient(90deg, #33ff55, transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite; }
@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.flight-card { padding: 20px 24px; background-color: #0f1111; border: 1px solid #2b3c2b; border-radius: 10px; margin-bottom: 22px; }
.flight-title { font-size: 1.25rem; font-weight: 700; color: #9adf4f; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 14px; }
.metric-label { font-size: 0.70rem; text-transform: uppercase; color: #9fa8a0; letter-spacing: 0.6px; margin-bottom: -6px; }
.metric-value { font-size: 1.9rem; color: #b6ff6d; margin-top: -6px; font-weight: 700; }
.small-note { font-size: 0.78rem; color: #9fa8a0; }
#f16hud-container { width: 100%; background: rgba(0, 10, 0, 0.70); border: 1px solid #1f3; border-radius: 12px; padding: 12px; margin-top: 18px; box-shadow: 0 0 15px #0f0 inset; }
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# =====================================
# 🧰 UTILITAS
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384 

def safe_float(val, default=0.0):
    try: return float(val) if val is not None and not np.isnan(float(val)) else default
    except: return default

def estimate_dewpoint(temp, rh):
    if pd.isna(temp) or pd.isna(rh): return None
    return temp - ((100 - rh) / 5)

def ceiling_proxy_from_tcc(tcc_pct):
    if pd.isna(tcc_pct): return 99999, "Unknown"
    tcc = float(tcc_pct)
    if tcc < 1: return 99999, "SKC (Clear)"
    elif tcc < 25: return 3500, "FEW"
    elif tcc < 50: return 2250, "SCT"
    elif tcc < 75: return 1250, "BKN"
    else: return 800, "OVC"

# =====================================
# 🎚️ SIDEBAR
# =====================================
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    selected_icao = st.selectbox("🎯 Target Lanud (ICAO)", options=list(LANUD_DB.keys()))
    lanud = LANUD_DB[selected_icao]
    
    st.markdown(f"**{lanud['name']}**")
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.button("🔄 Fetch Data")
    st.markdown("---")
    show_map = st.checkbox("Show Map", value=True)
    show_qam_report = st.checkbox("Show MET Report (QAM)", value=True)
    
    override_mode = st.selectbox("Display Mode", ["Auto", "Day", "Night"], index=0)
    CURRENT_MODE = "day" if (override_mode == "Day" or (override_mode == "Auto" and 6 <= datetime.now().hour < 18)) else "night"

# =====================================
# 📡 DATA LOAD
# =====================================
st.title("Tactical Weather Operations Dashboard")

try:
    with st.spinner("🛰️ Acquiring weather intelligence..."):
        raw = requests.get(API_BASE, params={"adm1": lanud['adm1']}, timeout=10).json()
    
    entries = raw.get("data", [])
    target_city = lanud['city'].lower()
    selected_entry = next((e for e in entries if target_city in e.get("lokasi", {}).get("kotkab", "").lower()), entries[0])

    rows = []
    lokasi = selected_entry.get("lokasi", {})
    for group in selected_entry.get("cuaca", []):
        for obs in group:
            obs.update(lokasi)
            obs["local_dt"] = pd.to_datetime(obs.get("local_datetime"), errors="coerce")
            rows.append(obs)
    
    df = pd.DataFrame(rows).sort_values("local_dt")
    now = df.iloc[0]

    # Kalkulasi
    temp = safe_float(now.get('t'))
    rh = safe_float(now.get('hu'))
    dp = estimate_dewpoint(temp, rh)
    dp_disp = f"{dp:.1f}°C" if dp is not None else "—"
    ceil_ft, ceil_lbl = ceiling_proxy_from_tcc(now.get('tcc'))
    vis_m = now.get('vs', '—')
    vis_sm = f"{(safe_float(vis_m)*0.000621371):.1f} SM"

# =====================================
# ✈ KEY METRICS (Tampilan Asli)
# =====================================
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="flight-title">✈ Key Meteorological Status: {selected_icao}</div>', unsafe_allow_html=True)
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.markdown(f"<div class='metric-label'>Temperature (°C)</div><div class='metric-value'>{temp}</div>", unsafe_allow_html=True)
    with colB:
        st.markdown(f"<div class='metric-label'>Wind Speed (KT)</div><div class='metric-value'>{(safe_float(now.get('ws'))*MS_TO_KT):.1f}</div>", unsafe_allow_html=True)
    with colC:
        st.markdown(f"<div class='metric-label'>Visibility (M)</div><div class='metric-value'>{vis_m}</div><div class='small-note'>({vis_sm})</div>", unsafe_allow_html=True)
    with colD:
        st.markdown(f"<div class='metric-label'>Weather</div><div class='metric-value'>{now.get('weather_desc','—')}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================
# 🟢 HUD F-16 (Tampilan Asli)
# =====================================
    st.markdown(f"<div id='f16hud-container'>", unsafe_allow_html=True)
    st.markdown("<div style='color:#0f0; text-align:center; margin-bottom:8px;'>F-16 TACTICAL HUD OVERLAY</div>", unsafe_allow_html=True)
    hud_svg = f"""
    <svg viewBox="0 0 800 220" width="100%">
      <line x1="50" y1="110" x2="750" y2="110" stroke="#0f0" stroke-width="1.5" stroke-dasharray="10,5"/>
      <text x="400" y="40" fill="#0f0" font-size="22" text-anchor="middle">HDG {int(safe_float(now.get('wd_deg'))):03d}°</text>
      <text x="120" y="200" fill="#0f0" font-size="16">VIS: {vis_m} m</text>
      <text x="680" y="200" fill="#0f0" font-size="16" text-anchor="end">CEIL: {ceil_ft} ft</text>
    </svg>
    """
    st.markdown(hud_svg, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================
# 📝 QAM REPORT (FORM REPLICATION - Perbaikan Utama)
# =====================================
    if show_qam_report:
        st.markdown("---")
        st.subheader("📝 Meteorological Report (QAM/Form Replication)")
        qam_html = f"""
        <div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div>
        <div class="met-report-subheader">DINAS PENGEMBANGAN OPERASI</div>
        <table class="met-report-table">
            <tr><th>METEOROLOGICAL OBS AT / DATE</th><td>{now.get('local_datetime','—')}</td></tr>
            <tr><th>AERODROME IDENTIFICATION</th><td>{selected_icao} / {lanud['name']}</td></tr>
            <tr><th>SURFACE WIND (DEG/KT)</th><td>{now.get('wd_deg','—')}° / {(safe_float(now.get('ws'))*MS_TO_KT):.1f} KT</td></tr>
            <tr><th>HORIZONTAL VISIBILITY</th><td>{vis_m} m ({vis_sm})</td></tr>
            <tr><th>PRESENT WEATHER</th><td>{now.get('weather_desc','—')}</td></tr>
            <tr><th>CLOUD COVER / CEILING</th><td>{now.get('tcc','—')}% / {ceil_lbl} ({ceil_ft} ft)</td></tr>
            <tr><th>TEMP / DEW POINT</th><td>T: {temp}°C / DP: {dp_disp}</td></tr>
            <tr><th>HUMIDITY</th><td>{rh}%</td></tr>
        </table>
        """
        st.markdown(qam_html, unsafe_allow_html=True)

# =====================================
# 🗺️ MAP
# =====================================
    if show_map:
        st.divider()
        st.map(pd.DataFrame({'lat': [safe_float(now.get('lat'))], 'lon': [safe_float(now.get('lon'))]}))

except Exception as e:
    st.error(f"System Error: {e}")
