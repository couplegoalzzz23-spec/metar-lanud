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
st.set_page_config(page_title="Tactical Weather Ops — BMKG Lanud Edition", layout="wide")

# =====================================
# 🌑 DATABASE LANUD INDONESIA (ICAO MAPPING)
# =====================================
# Mapping ICAO ke Kode ADM1 (Provinsi) dan Nama Kota/Kabupaten (ADM2) untuk API BMKG
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
.met-report-table th, .met-report-table td { border: 1px solid #2b3c2b; padding: 8px; text-align: left; }
.met-report-table th { background-color: #111; color: #a9df52; text-transform: uppercase; width: 45%; font-size: 0.85rem; }
.met-report-table td { color: #dfffe0; font-weight: bold; }
.met-report-header { text-align: center; background-color: #0b0c0c; color: #a9df52; font-weight: bold; font-size: 1.1rem; padding: 10px 0; border: 1px solid #2b3c2b; }
.radar { position: relative; width: 160px; height: 160px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%); border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 20px #33ff55; }
.radar:before { content: ""; position: absolute; top: 0; left: 0; width: 50%; height: 2px; background: linear-gradient(90deg, #33ff55, transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite; }
@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.flight-card { padding: 20px; background-color: #0f1111; border: 1px solid #2b3c2b; border-radius: 10px; margin-bottom: 20px; }
.flight-title { font-size: 1.25rem; font-weight: 700; color: #9adf4f; text-transform: uppercase; margin-bottom: 14px; }
.metric-value { font-size: 1.9rem; color: #b6ff6d; font-weight: 700; }
.badge-green { color:#002b00; background:#b6ff6d; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-yellow { color:#4a3b00; background:#ffd86b; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-red { color:#2b0000; background:#ff6b6b; padding:4px 8px; border-radius:6px; font-weight:700; }
#f16hud-container { width: 100%; background: rgba(0, 10, 0, 0.70); border: 1px solid #1f3; border-radius: 12px; padding: 12px; margin-top: 18px; box-shadow: 0 0 15px #0f0 inset; }
.hud-glow { stroke: #0f0; stroke-width: 2; fill: none; filter: drop-shadow(0 0 6px #0f0); }
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# =====================================
# 🧰 UTILITAS & LOGIC
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

def flatten_cuaca_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            r = obs.copy()
            r.update({
                "adm1": lokasi.get("adm1"), "adm2": lokasi.get("adm2"),
                "provinsi": lokasi.get("provinsi"), "kotkab": lokasi.get("kotkab"),
                "lon": lokasi.get("lon"), "lat": lokasi.get("lat"),
            })
            r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"), errors="coerce")
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs","ws_kt"]:
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
    if pd.isna(visibility_m) or visibility_m is None: return "—"
    vis_sm = float(visibility_m) * METER_TO_SM
    return f"{vis_sm:.1f} SM"

def safe_float(val, default=0.0):
    try: return float(val) if val is not None and not np.isnan(val) else default
    except: return default

def badge_html(status):
    if status in ["VFR", "Recommended", "SKC (Clear)"]: return "<span class='badge-green'>OK</span>"
    if status in ["MVFR", "Caution"]: return "<span class='badge-yellow'>CAUTION</span>"
    return "<span class='badge-red'>NO-GO</span>"

# =====================================
# 🎚️ SIDEBAR (MODIFIED FOR LANUD)
# =====================================
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    
    # PERUBAHAN UTAMA: Memilih Lanud berdasarkan ICAO
    selected_icao = st.selectbox("🎯 Select LANUD (ICAO)", options=list(LANUD_DB.keys()), index=0)
    lanud_info = LANUD_DB[selected_icao]
    
    st.info(f"📍 {lanud_info['name']}")
    
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        
    st.markdown("---")
    show_map = st.checkbox("Show Map", value=True)
    show_qam_report = st.checkbox("Show MET Report (QAM)", value=True)
    
    # Display Mode
    override_mode = st.selectbox("HUD Mode", ["Auto", "Day", "Night"], index=0)
    CURRENT_MODE = "day" if (override_mode == "Day" or (override_mode == "Auto" and 6 <= datetime.now().hour < 18)) else "night"

# =====================================
# 📡 DATA FETCHING
# =====================================
st.title("Tactical Weather Operations Dashboard")
st.markdown(f"**CURRENT AIRBASE: {selected_icao} - {lanud_info['name']}**")

try:
    with st.spinner("🛰️ Scanning Airbase Intelligence..."):
        raw_data = fetch_forecast(lanud_info['adm1'])
    
    entries = raw_data.get("data", [])
    if not entries:
        st.error("Connection to BMKG Data Source failed.")
        st.stop()

    # Cari lokasi yang paling mendekati target city lanud
    target_city = lanud_info['city'].lower()
    selected_entry = None
    
    for e in entries:
        kotkab = e.get("lokasi", {}).get("kotkab", "").lower()
        if target_city in kotkab:
            selected_entry = e
            break
    
    # Jika tidak ketemu spesifik, ambil yang pertama dalam provinsi tersebut
    if not selected_entry:
        selected_entry = entries[0]

    df = flatten_cuaca_entry(selected_entry)
    if "ws_kt" not in df.columns: df["ws_kt"] = df["ws"] * MS_TO_KT
    
    # Time Selection
    df = df.sort_values("local_datetime_dt")
    now = df.iloc[0] # Data terbaru (Current Forecast)

    # Variables for Display
    dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
    vis_sm_disp = convert_vis_to_sm(now.get('vs'))
    ceiling_est_ft, ceiling_label = ceiling_proxy_from_tcc(now.get("tcc"))

# =====================================
# ✈ FLIGHT WEATHER STATUS
# =====================================
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="flight-title">✈ METAR DATA: {selected_icao}</div>', unsafe_allow_html=True)
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.markdown(f"<div class='metric-label'>TEMP</div><div class='metric-value'>{now.get('t','—')}°C</div>", unsafe_allow_html=True)
    with colB:
        st.markdown(f"<div class='metric-label'>WIND (KT)</div><div class='metric-value'>{now.get('ws_kt',0):.1f}</div><small>{now.get('wd_deg','—')}°</small>", unsafe_allow_html=True)
    with colC:
        st.markdown(f"<div class='metric-label'>VISIBILITY</div><div class='metric-value'>{now.get('vs','—')}m</div><small>{vis_sm_disp}</small>", unsafe_allow_html=True)
    with colD:
        st.markdown(f"<div class='metric-label'>WX</div><div class='metric-value'>{now.get('weather_desc','—')}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================
# ⚡ HUD PANEL
# =====================================
    hud_color = "#0f0" if CURRENT_MODE == "night" else "#005500"
    dx = np.sin(np.radians(safe_float(now.get("wd_deg")))) * 80
    dy = -np.cos(np.radians(safe_float(now.get("wd_deg")))) * 80

    hud_svg = f"""
    <div id="f16hud-container" style="border-color:{hud_color};">
      <div style="text-align:center; color:{hud_color}; font-weight:bold; margin-bottom:10px;">F-16 HUD OVERLAY - {selected_icao}</div>
      <svg viewBox="0 0 800 250" width="100%">
        <line x1="50" y1="125" x2="750" y2="125" stroke="{hud_color}" stroke-width="1" stroke-dasharray="5,5"/>
        <text x="400" y="30" fill="{hud_color}" font-size="20" text-anchor="middle">MAG HDG {int(safe_float(now.get('wd_deg'))):03d}</text>
        <line x1="400" y1="125" x2="{400+dx}" y2="{125+dy}" stroke="{hud_color}" stroke-width="3" />
        <circle cx="400" cy="125" r="5" fill="{hud_color}" />
        <text x="100" y="220" fill="{hud_color}" font-size="16">VIS: {now.get('vs')}M</text>
        <text x="700" y="220" fill="{hud_color}" font-size="16" text-anchor="end">ALT: {ceiling_est_ft}FT</text>
      </svg>
    </div>
    """
    st.markdown(hud_svg, unsafe_allow_html=True)

# =====================================
# 📝 QAM REPORT
# =====================================
    if show_qam_report:
        st.markdown("---")
        st.subheader("📝 Meteorological Report (QAM)")
        qam_html = f"""
        <div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div>
        <table class="met-report-table">
            <tr><th>ICAO IDENTIFICATION</th><td>{selected_icao} / {lanud_info['name']}</td></tr>
            <tr><th>DATE / TIME (LOCAL)</th><td>{now.get('local_datetime','—')}</td></tr>
            <tr><th>SURFACE WIND</th><td>{now.get('wd_deg','—')}° / {now.get('ws_kt',0):.1f} KT</td></tr>
            <tr><th>VISIBILITY</th><td>{now.get('vs','—')} m ({vis_sm_disp})</td></tr>
            <tr><th>PRESENT WEATHER</th><td>{now.get('weather_desc','—')}</td></tr>
            <tr><th>CLOUD COVER</th><td>{now.get('tcc','—')}% / Base: {ceiling_est_ft} ft</td></tr>
            <tr><th>TEMP / DEW POINT</th><td>T: {now.get('t','—')}°C / DP: {dewpt:.1f if dewpt else '—'}°C</td></tr>
        </table>
        """
        st.markdown(qam_html, unsafe_allow_html=True)

# =====================================
# 🗺️ MAP & TRENDS
# =====================================
    col_m1, col_m2 = st.columns([1, 1])
    with col_m1:
        if show_map:
            st.subheader("📍 Deployment Map")
            m_lat, m_lon = safe_float(now.get('lat')), safe_float(now.get('lon'))
            st.map(pd.DataFrame({'lat': [m_lat], 'lon': [m_lon]}), zoom=11)
    
    with col_m2:
        st.subheader("📊 Wind Trend (24H)")
        fig = px.line(df, x="local_datetime_dt", y="ws_kt", markers=True)
        fig.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"System Error: {e}")
    st.info("Check API connection or Lanud mapping data.")

st.caption(f"Military Weather Intelligence | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Standby for Ops.")
