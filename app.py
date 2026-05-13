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
# 🌑 CSS — MILITARY STYLE + RADAR ANIMATION + FLIGHT PANEL + MET REPORT TABLE
# =====================================

CSS_STYLES = """
<style>
/* Base theme */
body {
    background-color: #0b0c0c;
    color: #cfd2c3;
    font-family: "Consolas", "Roboto Mono", monospace;
}
/* Custom CSS for the MET REPORT TABLE (REVISED QAM FORMAT) */
.met-report-table {
    border: 1px solid #2b3c2b;
    width: 100%;
    margin-bottom: 20px;
    background-color: #0f1111;
    font-size: 0.95rem;
    border-collapse: collapse;
}
.met-report-table th, .met-report-table td {
    border: 1px solid #2b3c2b;
    padding: 8px;
    text-align: left;
    vertical-align: top;
}
.met-report-table th {
    background-color: #111;
    color: #a9df52;
    text-transform: uppercase;
    width: 45%;
    font-size: 0.85rem;
}
.met-report-table td {
    color: #dfffe0;
    width: 55%;
    font-weight: bold;
}
.met-report-header {
    text-align: center;
    background-color: #0b0c0c;
    color: #a9df52;
    font-weight: bold;
    font-size: 1.1rem;
    padding: 10px 0;
    border: 1px solid #2b3c2b;
    border-bottom: none;
}
.met-report-subheader {
    text-align: center;
    background-color: #0b0c0c;
    color: #cfd2c3;
    font-weight: normal;
    font-size: 0.8rem;
    padding-bottom: 5px;
}
@media print {
    body { -webkit-print-color-adjust: exact; color-adjust: exact; }
}

h1, h2, h3, h4 { color: #a9df52; text-transform: uppercase; letter-spacing: 1px; }
section[data-testid="stSidebar"] { background-color: #111; color: #d0d3ca; }

.radar {
  position: relative;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%),
              radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%);
  background-size: 20px 20px;
  border: 2px solid #33ff55;
  overflow: hidden;
  margin: auto;
  box-shadow: 0 0 20px #33ff55;
}
.radar:before {
  content: "";
  position: absolute;
  top: 0; left: 0;
  width: 50%; height: 2px;
  background: linear-gradient(90deg, #33ff55, transparent);
  transform-origin: 100% 50%;
  animation: sweep 2.5s linear infinite;
}
@keyframes sweep {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.flight-card {
    padding: 20px 24px;
    background-color: #0f1111;
    border: 1px solid #2b3c2b;
    border-radius: 10px;
    margin-bottom: 22px;
}
.flight-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #9adf4f;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 14px;
}
.metric-label { font-size: 0.70rem; text-transform: uppercase; color: #9fa8a0; letter-spacing: 0.6px; margin-bottom: -6px; }
.metric-value { font-size: 1.9rem; color: #b6ff6d; margin-top: -6px; font-weight: 700; }
.small-note { font-size: 0.78rem; color: #9fa8a0; }
.badge-green { color:#002b00; background:#b6ff6d; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-yellow { color:#4a3b00; background:#ffd86b; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-red { color:#2b0000; background:#ff6b6b; padding:4px 8px; border-radius:6px; font-weight:700; }
.detail-value { font-size: 1.2rem; color: #dfffe0; font-weight: bold; }

#f16hud-container {
    width: 100%;
    background: rgba(0, 10, 0, 0.70);
    border: 1px solid #1f3;
    border-radius: 12px;
    padding: 12px;
    margin-top: 18px;
    box-shadow: 0 0 15px #0f0 inset;
}
.hud-glow { stroke: #0f0; stroke-width: 2; fill: none; filter: drop-shadow(0 0 6px #0f0); }
#hud-wind-arrow { stroke-width: 3; stroke-linecap: round; animation: windPulse 1.8s infinite ease-in-out; }
@keyframes windPulse { 0% { stroke-opacity: 0.4; } 50% { stroke-opacity: 1.0; } 100% { stroke-opacity: 0.4; } }
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# =====================================
# 🧰 UTILITAS
# =====================================
API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384 
METER_TO_SM = 0.000621371

def safe_float(val, default=0.0):
    try: return float(val) if val is not None and not np.isnan(float(val)) else default
    except: return default

def safe_int(val, default=0):
    try: return int(round(float(val))) if val is not None else default
    except: return default

@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    resp = requests.get(API_BASE, params={"adm1": adm1}, timeout=10)
    resp.raise_for_status()
    return resp.json()

def flatten_cuaca_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            r = obs.copy()
            r.update(lokasi)
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def estimate_dewpoint(temp, rh):
    if pd.isna(temp) or pd.isna(rh): return None
    return temp - ((100 - rh) / 5)

def ceiling_proxy_from_tcc(tcc_pct):
    if pd.isna(tcc_pct): return None, "Unknown"
    tcc = float(tcc_pct)
    if tcc < 1: return 99999, "SKC (Clear)"
    elif tcc < 25: return 3500, "FEW"
    elif tcc < 50: return 2250, "SCT"
    elif tcc < 75: return 1250, "BKN"
    else: return 800, "OVC"

def convert_vis_to_sm(visibility_m):
    if pd.isna(visibility_m): return "—"
    vis_sm = float(visibility_m) * METER_TO_SM
    return f"{vis_sm:.1f} SM"

def classify_ifr_vfr(visibility_m, ceiling_ft):
    vis_sm = safe_float(visibility_m) / 1609.34
    if vis_sm >= 5 and (ceiling_ft is None or ceiling_ft > 3000): return "VFR"
    if vis_sm >= 3 or (ceiling_ft is not None and ceiling_ft > 1000): return "MVFR"
    return "IFR"

def badge_html(status):
    if status in ["VFR", "Recommended", "SKC (Clear)"]: return "<span class='badge-green'>OK</span>"
    if status in ["MVFR", "Caution"]: return "<span class='badge-yellow'>CAUTION</span>"
    return "<span class='badge-red'>NO-GO</span>"

# =====================================
# 🎚️ SIDEBAR
# =====================================
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    
    # Input ICAO Lanud
    selected_icao = st.selectbox("🎯 Target Lanud (ICAO)", options=list(LANUD_DB.keys()))
    lanud = LANUD_DB[selected_icao]
    
    st.markdown(f"**{lanud['name']}**")
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#5f5;'>Scanning Weather...</p>", unsafe_allow_html=True)
    
    st.button("🔄 Fetch Data")
    st.markdown("---")
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Table (Raw Data)", value=False)
    show_qam_report = st.checkbox("Show MET Report (QAM)", value=True)
    
    override_mode = st.selectbox("Override Mode", ["Auto", "Day", "Night"], index=0)
    CURRENT_MODE = "day" if (override_mode == "Day" or (override_mode == "Auto" and 6 <= datetime.now().hour < 18)) else "night"

# =====================================
# 📡 LOAD DATA
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.markdown(f"*Target: {selected_icao} - {lanud['name']}*")

try:
    with st.spinner("🛰️ Acquiring weather intelligence..."):
        raw = fetch_forecast(lanud['adm1'])
        
    entries = raw.get("data", [])
    target_city = lanud['city'].lower()
    # Cari lokasi yang cocok dengan kota lanud
    selected_entry = next((e for e in entries if target_city in e.get("lokasi", {}).get("kotkab", "").lower()), entries[0])

    df = flatten_cuaca_entry(selected_entry)
    df["ws_kt"] = df["ws"] * MS_TO_KT
    df = df.sort_values("local_datetime_dt")
    
    now = df.iloc[0]

    # Pre-calculations
    dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
    dewpt_disp = f"{dewpt:.1f}°C" if dewpt is not None else "—"
    ceiling_est_ft, ceiling_label = ceiling_proxy_from_tcc(now.get("tcc"))
    ceiling_display = f"{ceiling_est_ft} ft" if ceiling_est_ft is not None and ceiling_est_ft <= 99999 else "—"
    vis_sm_disp = convert_vis_to_sm(now.get('vs'))

# =====================================
# ✈ FLIGHT WEATHER STATUS
# =====================================
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="flight-title">✈ Key Meteorological Status: {selected_icao}</div>', unsafe_allow_html=True)
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.markdown(f"<div class='metric-label'>Temperature (°C)</div><div class='metric-value'>{now.get('t','—')}</div>", unsafe_allow_html=True)
    with colB:
        st.markdown(f"<div class='metric-label'>Wind Speed (KT)</div><div class='metric-value'>{now.get('ws_kt',0):.1f}</div><div class='small-note'>{now.get('wd_deg','—')}°</div>", unsafe_allow_html=True)
    with colC:
        st.markdown(f"<div class='metric-label'>Visibility (M/SM)</div><div class='metric-value'>{now.get('vs','—')}</div><div class='small-note'>({vis_sm_disp})</div>", unsafe_allow_html=True)
    with colD:
        st.markdown(f"<div class='metric-label'>Weather</div><div class='metric-value'>{now.get('weather_desc','—')}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================
# 🟢 HUD PANEL (Mode B)
# =====================================
    hud_mode_attr = f"data-mode='{CURRENT_MODE}'"
    st.markdown(f"<div id='f16hud-container' {hud_mode_attr}>", unsafe_allow_html=True)
    st.markdown("<div style='color:#0f0; text-align:center; margin-bottom:10px;'>F-16 TACTICAL HUD OVERLAY</div>", unsafe_allow_html=True)
    
    _wdir = safe_int(now.get("wd_deg"))
    _wspd = safe_float(now.get("ws_kt"))
    dx = np.sin(np.radians(_wdir)) * min(120, _wspd * 5)
    dy = -np.cos(np.radians(_wdir)) * min(120, _wspd * 5)

    hud_svg = f"""
    <svg viewBox="0 0 800 250" preserveAspectRatio="xMidYMid meet">
      <line x1="50" y1="125" x2="750" y2="125" class="hud-glow" stroke="#0f0" stroke-width="1.5"/>
      <text x="400" y="30" fill="#0f0" font-size="22" text-anchor="middle">HDG {_wdir:03d}°</text>
      <line id="hud-wind-arrow" x1="400" y1="125" x2="{400 + dx}" y2="{125 + dy}" stroke="#0f0" />
      <text x="400" y="160" fill="#0f0" font-size="18" text-anchor="middle">WIND {_wspd:.1f} KT</text>
      <text x="120" y="220" fill="#0f0" font-size="16">VIS: {now.get('vs')} m</text>
      <text x="680" y="220" fill="#0f0" font-size="16" text-anchor="end">CEIL: {ceiling_est_ft} ft</text>
    </svg>
    """
    st.markdown(hud_svg, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================
# 📝 QAM REPORT
# =====================================
    if show_qam_report:
        st.markdown("---")
        st.subheader("📝 Meteorological Report (QAM)")
        qam_content = f"""
        <div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div>
        <div class="met-report-subheader">DINAS PENGEMBANGAN OPERASI</div>
        <table class="met-report-table">
            <tr><th>ICAO / AERODROME</th><td>{selected_icao} / {lanud['name']}</td></tr>
            <tr><th>DATE / TIME (LOCAL)</th><td>{now.get('local_datetime','—')}</td></tr>
            <tr><th>SURFACE WIND</th><td>{now.get('wd_deg','—')}° / {now.get('ws_kt',0):.1f} KT</td></tr>
            <tr><th>VISIBILITY</th><td>{now.get('vs','—')} m ({vis_sm_disp})</td></tr>
            <tr><th>WEATHER</th><td>{now.get('weather_desc','—')}</td></tr>
            <tr><th>CLOUD / CEILING</th><td>{now.get('tcc','—')}% / {ceiling_display}</td></tr>
            <tr><th>TEMP / DEW POINT</th><td>T: {now.get('t','—')}°C / DP: {dewpt_disp}</td></tr>
        </table>
        """
        st.markdown(qam_content, unsafe_allow_html=True)

# =====================================
# 📈 TRENDS & MAP
# =====================================
    if show_map:
        st.subheader("🗺️ Tactical Map")
        st.map(pd.DataFrame({'lat': [safe_float(now.get('lat'))], 'lon': [safe_float(now.get('lon'))]}), zoom=10)

    st.subheader("📊 Wind Trend")
    st.plotly_chart(px.line(df, x="local_datetime_dt", y="ws_kt", title="Wind Speed (KT)"), use_container_width=True)

    if show_table:
        st.dataframe(df)

except Exception as e:
    st.error(f"System Error: {e}")
