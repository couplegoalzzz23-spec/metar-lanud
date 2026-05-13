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
# 🗺️ MAPPING ICAO LANUD KE ADM1 BMKG
# =====================================
LANUD_MAP = {
    "WIHH": {"name": "Lanud Halim Perdanakusuma (Jakarta)", "adm1": "31"},
    "WATS": {"name": "Lanud Atang Sendjaja (Bogor)", "adm1": "32"},
    "WRSV": {"name": "Lanud Iswahjudi (Madiun)", "adm1": "35"},
    "WARA": {"name": "Lanud Abdulrachman Saleh (Malang)", "adm1": "35"},
    "WIBB": {"name": "Lanud Roesmin Nurjadin (Pekanbaru)", "adm1": "14"},
    "WIOO": {"name": "Lanud Supadio (Pontianak)", "adm1": "61"},
    "WAAA": {"name": "Lanud Sultan Hasanuddin (Makassar)", "adm1": "73"},
    "WIMK": {"name": "Lanud Soewondo (Medan)", "adm1": "12"},
    "WIDD": {"name": "Lanud Hang Nadim (Batam)", "adm1": "21"},
    "WIPL": {"name": "Lanud Sri Mulyono Herlambang (Palembang)", "adm1": "16"},
    "WIGG": {"name": "Lanud Sutan Sjahrir (Padang)", "adm1": "13"},
    "WAJJ": {"name": "Lanud Silas Papare (Jayapura)", "adm1": "94"},
    "WARI": {"name": "Lanud Manuhua (Biak)", "adm1": "94"},
    "WRLO": {"name": "Lanud Sam Ratulangi (Manado)", "adm1": "71"},
    "WAPP": {"name": "Lanud Pattimura (Ambon)", "adm1": "81"},
    "WADA": {"name": "Lanud I Gusti Ngurah Rai (Bali)", "adm1": "51"},
    "WICC": {"name": "Lanud Husein Sastranegara (Bandung)", "adm1": "32"},
}

# =====================================
# 🌑 CSS — MILITARY STYLE
# =====================================
CSS_STYLES = """
<style>
body { background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", monospace; }
.met-report-table { border: 1px solid #2b3c2b; width: 100%; margin-bottom: 20px; background-color: #0f1111; font-size: 0.95rem; border-collapse: collapse; }
.met-report-table th, .met-report-table td { border: 1px solid #2b3c2b; padding: 8px; text-align: left; vertical-align: top; }
.met-report-table th { background-color: #111; color: #a9df52; text-transform: uppercase; width: 45%; font-size: 0.85rem; }
.met-report-table td { color: #dfffe0; width: 55%; font-weight: bold; }
.met-report-header { text-align: center; background-color: #0b0c0c; color: #a9df52; font-weight: bold; font-size: 1.1rem; padding: 10px 0; border: 1px solid #2b3c2b; border-bottom: none; }
h1, h2, h3, h4 { color: #a9df52; text-transform: uppercase; letter-spacing: 1px; }
section[data-testid="stSidebar"] { background-color: #111; color: #d0d3ca; }
.radar { position: relative; width: 160px; height: 160px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%), radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%); background-size: 20px 20px; border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 20px #33ff55; }
.radar:before { content: ""; position: absolute; top: 0; left: 0; width: 50%; height: 2px; background: linear-gradient(90deg, #33ff55, transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite; }
@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.flight-card { padding: 20px 24px; background-color: #0f1111; border: 1px solid #2b3c2b; border-radius: 10px; margin-bottom: 22px; }
.flight-title { font-size: 1.25rem; font-weight: 700; color: #9adf4f; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 14px; }
.metric-label { font-size: 0.70rem; text-transform: uppercase; color: #9fa8a0; letter-spacing: 0.6px; margin-bottom: -6px; }
.metric-value { font-size: 1.9rem; color: #b6ff6d; margin-top: -6px; font-weight: 700; }
.small-note { font-size: 0.78rem; color: #9fa8a0; }
.badge-green { color:#002b00; background:#b6ff6d; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-yellow { color:#4a3b00; background:#ffd86b; padding:4px 8px; border-radius:6px; font-weight:700; }
.badge-red { color:#2b0000; background:#ff6b6b; padding:4px 8px; border-radius:6px; font-weight:700; }
#f16hud-container { width: 100%; background: rgba(0, 10, 0, 0.70); border: 1px solid #1f3; border-radius: 12px; padding: 12px; margin-top: 18px; box-shadow: 0 0 15px #0f0 inset; }
#f16hud-title { color: #0f0; font-size: 1.05rem; text-align: center; margin-bottom: 8px; text-shadow: 0 0 6px #0f0; }
.hud-glow { stroke: #0f0; stroke-width: 2; fill: none; filter: drop-shadow(0 0 6px #0f0); }
#hud-wind-arrow { stroke-width: 3; stroke-linecap: round; animation: windPulse 1.8s infinite ease-in-out; }
@keyframes windPulse { 0% { stroke-opacity: 0.4; } 50% { stroke-opacity: 1.0; } 100% { stroke-opacity: 0.4; } }
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# =====================================
# 🧰 UTILITAS
# =====================================
def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None and not pd.isna(val) else default
    except:
        return default

def safe_int(val, default=0):
    try:
        return int(round(float(val))) if val is not None and not pd.isna(val) else default
    except:
        return default

@st.cache_data(ttl=300)
def fetch_forecast(adm_code: str):
    url = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
    params = {"adm1": adm_code}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

def flatten_cuaca_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            r = obs.copy()
            r.update({k: lokasi.get(k) for k in ["adm1", "adm2", "provinsi", "kotkab", "lon", "lat"]})
            r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"), errors="coerce")
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t","tcc","tp","wd_deg","ws","hu","vs"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def estimate_dewpoint(temp, rh):
    if pd.notna(temp) and pd.notna(rh):
        return temp - ((100 - rh) / 5)
    return None

def ceiling_proxy_from_tcc(tcc_pct):
    if pd.isna(tcc_pct): return None, "Unknown"
    tcc = float(tcc_pct)
    if tcc < 1: return 99999, "SKC (Clear)"
    elif tcc < 25: return 3500, "FEW (>3000 ft)"
    elif tcc < 50: return 2250, "SCT (1500-3000 ft)"
    elif tcc < 75: return 1250, "BKN (1000-1500 ft)"
    else: return 800, "OVC (<1000 ft)"

def convert_vis_to_sm(visibility_m):
    if pd.isna(visibility_m): return "—"
    vis_sm = float(visibility_m) * 0.000621371
    return f"{vis_sm:.1f} SM" if vis_sm < 5 else f"{int(round(vis_sm))} SM"

def classify_ifr_vfr(visibility_m, ceiling_ft):
    if pd.isna(visibility_m): return "Unknown"
    vis_sm = float(visibility_m) / 1609.34
    if vis_sm >= 5 and (ceiling_ft is None or ceiling_ft > 3000): return "VFR"
    if (3 <= vis_sm < 5) or (1000 < ceiling_ft <= 3000): return "MVFR"
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
    icao_input = st.selectbox("Select LANUD (ICAO)", options=list(LANUD_MAP.keys()), index=0)
    selected_lanud_info = LANUD_MAP[icao_input]
    st.info(f"📍 {selected_lanud_info['name']}")
    
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    if st.button("🔄 Refresh System"):
        st.cache_data.clear()
    st.markdown("---")
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Table (Raw)", value=False)
    show_qam_report = st.checkbox("Show MET Report (QAM)", value=True)

# =====================================
# 📡 CORE ENGINE
# =====================================
st.title("Tactical Weather Operations Dashboard")

try:
    with st.spinner("🛰️ Acquiring intelligence..."):
        raw = fetch_forecast(selected_lanud_info['adm1'])
    
    entries = raw.get("data", [])
    if not entries:
        st.warning("No forecast data available for this sector.")
        st.stop()

    mapping = { (e.get("lokasi", {}).get("kotkab") or f"Sector {i}"): {"entry": e} for i, e in enumerate(entries) }
    loc_choice = st.selectbox("🎯 Select Tactical Area", options=list(mapping.keys()))
    
    df = flatten_cuaca_entry(mapping[loc_choice]["entry"])
    df["ws_kt"] = df["ws"] * 1.94384

    # Time Selection
    min_dt, max_dt = df["local_datetime_dt"].min().to_pydatetime(), df["local_datetime_dt"].max().to_pydatetime()
    with st.sidebar:
        start_dt = st.slider("Time Range", min_value=min_dt, max_value=max_dt, value=(min_dt, min_dt + pd.Timedelta(hours=6)), step=pd.Timedelta(hours=3))
    
    df_sel = df[(df["local_datetime_dt"] >= pd.to_datetime(start_dt[0])) & (df["local_datetime_dt"] <= pd.to_datetime(start_dt[1]))].copy()
    if df_sel.empty: 
        st.info("No data in selected range.")
        st.stop()
    
    now = df_sel.iloc[0]
    
    # Pre-calculating variables
    dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
    ceil_ft, ceil_lbl = ceiling_proxy_from_tcc(now.get("tcc"))
    vis_sm = convert_vis_to_sm(now.get('vs'))
    
    # Formatting display variables to avoid f-string logic errors
    dewpt_str = f"{dewpt:.1f}" if dewpt is not None else "—"
    wind_kt = now.get('ws_kt', 0)
    wind_deg = now.get('wd_deg', 0)

    # ✈ KEY METRICS
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown('<div class="flight-title">✈ Key Meteorological Status</div>', unsafe_allow_html=True)
    cA, cB, cC, cD = st.columns(4)
    cA.markdown(f"<div class='metric-label'>Temp</div><div class='metric-value'>{now.get('t')}°C</div>", unsafe_allow_html=True)
    cB.markdown(f"<div class='metric-label'>Wind</div><div class='metric-value'>{wind_kt:.1f}</div><div class='small-note'>{wind_deg}°</div>", unsafe_allow_html=True)
    cC.markdown(f"<div class='metric-label'>Vis</div><div class='metric-value'>{now.get('vs')}m</div><div class='small-note'>{vis_sm}</div>", unsafe_allow_html=True)
    cD.markdown(f"<div class='metric-label'>Weather</div><div class='metric-value'>{now.get('weather_desc')}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 🏹 F-16 HUD Overlay
    hud_w_dir = safe_int(wind_deg)
    hud_w_spd = safe_float(wind_kt)
    dx = np.sin(np.radians(hud_w_dir)) * min(120, hud_w_spd * 5)
    dy = -np.cos(np.radians(hud_w_dir)) * min(120, hud_w_spd * 5)
    
    st.markdown(f"""<div id='f16hud-container'><div id='f16hud-title'>F-16 TACTICAL HUD — {icao_input}</div>
    <svg viewBox="0 0 800 300" style="width:100%; height:220px;">
    <line x1="50" y1="150" x2="750" y2="150" class="hud-glow" stroke="#0f0"/>
    <text x="400" y="40" fill="#0f0" font-size="20" text-anchor="middle">HDG {hud_w_dir:03d}°</text>
    <line x1="400" y1="150" x2="{400+dx}" y2="{150+dy}" stroke="#0f0" stroke-width="3" id="hud-wind-arrow"/>
    <text x="400" y="190" fill="#0f0" font-size="16" text-anchor="middle">WIND {hud_w_spd:.1f} KT</text>
    <text x="100" y="260" fill="#0f0" font-size="14">VIS: {now.get('vs')}m</text>
    <text x="700" y="260" fill="#0f0" font-size="14" text-anchor="end">CEIL: {ceil_ft}ft</text>
    </svg></div>""", unsafe_allow_html=True)

    # 📝 QAM REPORT
    if show_qam_report:
        st.markdown("### 📝 Meteorological Report (QAM)")
        qam_html = f"""<div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div><table class="met-report-table">
        <tr><th>OBS TIME</th><td>{now.get('local_datetime')}</td></tr>
        <tr><th>AERODROME (ICAO)</th><td>{icao_input} / {now.get('kotkab')}</td></tr>
        <tr><th>WIND</th><td>{wind_deg}° / {wind_kt:.1f} KT</td></tr>
        <tr><th>VISIBILITY</th><td>{now.get('vs')}m ({vis_sm})</td></tr>
        <tr><th>WEATHER</th><td>{now.get('weather_desc')}</td></tr>
        <tr><th>CLOUD/CEILING</th><td>{now.get('tcc')}% / {ceil_ft} ft</td></tr>
        <tr><th>TEMP / DEWPOINT</th><td>{now.get('t')}°C / {dewpt_str}°C</td></tr>
        </table>"""
        st.markdown(qam_html, unsafe_allow_html=True)

    # 🔴 DECISION MATRIX
    ifr_vfr = classify_ifr_vfr(now.get("vs"), ceil_ft)
    st.markdown("---")
    st.subheader("🔴 Operational Decision Matrix")
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Regulatory Category**<br>{badge_html(ifr_vfr)} {ifr_vfr}", unsafe_allow_html=True)
    c2.markdown(f"**Takeoff Recommendation**<br>{badge_html('VFR')} Recommended", unsafe_allow_html=True)
    c3.markdown(f"**Landing Recommendation**<br>{badge_html('VFR')} Recommended", unsafe_allow_html=True)

    # 📈 VISUALS
    st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature Trend", template="plotly_dark", color_discrete_sequence=['#a9df52']), use_container_width=True)
    
    if show_map: 
        st.subheader("🗺️ Tactical AO Map")
        st.map(df_sel[['lat', 'lon']].dropna().drop_duplicates())
    if show_table: 
        st.subheader("📋 Raw Meteorological Data")
        st.dataframe(df_sel, use_container_width=True)

except Exception as e:
    st.error(f"SYSTEM ERROR: {e}")
