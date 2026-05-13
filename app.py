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

# Database Mapping Lanud Indonesia (Contoh beberapa Lanud Utama)
# Anda bisa melengkapi list ini sesuai kebutuhan
LANUD_DATABASE = {
    "Lanud Halim Perdanakusuma (Jakarta)": {"icao": "WIHH", "adm1": "31"},
    "Lanud Atang Sendjaja (Bogor)": {"icao": "WIAW", "adm1": "32"},
    "Lanud Iswahjudi (Madiun)": {"icao": "WSRR", "adm1": "35"},
    "Lanud Abdulrachman Saleh (Malang)": {"icao": "WARA", "adm1": "35"},
    "Lanud Sultan Hasanuddin (Makassar)": {"icao": "WAAA", "adm1": "73"},
    "Lanud Roesmin Nurjadin (Pekanbaru)": {"icao": "WIBB", "adm1": "14"},
    "Lanud Supadio (Pontianak)": {"icao": "WIOO", "adm1": "61"},
    "Lanud Soewondo (Medan)": {"icao": "WIMK", "adm1": "12"},
    "Lanud Sam Ratulangi (Manado)": {"icao": "WAMM", "adm1": "71"},
    "Lanud El Tari (Kupang)": {"icao": "WATT", "adm1": "53"},
    "Lanud Silas Papare (Jayapura)": {"icao": "WAJJ", "adm1": "91"},
    "Lanud Suryadarma (Subang)": {"icao": "WICN", "adm1": "32"},
}

# =====================================
# 🌑 CSS — MILITARY STYLE + RADAR ANIMATION + FLIGHT PANEL + MET REPORT TABLE
# =====================================
CSS_STYLES = """
<style>
body { background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", monospace; }
.met-report-table { border: 1px solid #2b3c2b; width: 100%; margin-bottom: 20px; background-color: #0f1111; font-size: 0.95rem; border-collapse: collapse; }
.met-report-table th, .met-report-table td { border: 1px solid #2b3c2b; padding: 8px; text-align: left; vertical-align: top; }
.met-report-table th { background-color: #111; color: #a9df52; text-transform: uppercase; width: 45%; font-size: 0.85rem; }
.met-report-table td { color: #dfffe0; width: 55%; font-weight: bold; }
.met-report-header { text-align: center; background-color: #0b0c0c; color: #a9df52; font-weight: bold; font-size: 1.1rem; padding: 10px 0; border: 1px solid #2b3c2b; }
.met-report-subheader { text-align: center; background-color: #0b0c0c; color: #cfd2c3; font-size: 0.8rem; padding-bottom: 5px; border-left: 1px solid #2b3c2b; border-right: 1px solid #2b3c2b; }
.radar { position: relative; width: 150px; height: 150px; border-radius: 50%; border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 15px #33ff55; background: radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 50%); }
.radar:before { content: ""; position: absolute; top: 0; left: 0; width: 50%; height: 2px; background: linear-gradient(90deg, #33ff55, transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite; }
@keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.flight-card { padding: 20px; background-color: #0f1111; border: 1px solid #2b3c2b; border-radius: 10px; margin-bottom: 20px; }
.metric-value { font-size: 1.8rem; color: #b6ff6d; font-weight: bold; }
.badge-green { color:#002b00; background:#b6ff6d; padding:2px 6px; border-radius:4px; }
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# =====================================
# 📡 KONFIGURASI API & UTILITAS
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
            r.update({k: lokasi.get(k) for k in ["adm1", "adm2", "provinsi", "kotkab", "lon", "lat"]})
            r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"), errors="coerce")
            rows.append(r)
    df = pd.DataFrame(rows)
    cols_to_fix = ["t","tcc","tp","wd_deg","ws","hu","vs"]
    for c in cols_to_fix:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def estimate_dewpoint(temp, rh):
    return temp - ((100 - rh) / 5) if pd.notna(temp) and pd.notna(rh) else None

def convert_vis_to_sm(visibility_m):
    if pd.isna(visibility_m): return "—"
    vis_sm = float(visibility_m) * METER_TO_SM
    return f"{vis_sm:.1f} SM"

def ceiling_proxy_from_tcc(tcc_pct):
    if pd.isna(tcc_pct): return None, "Unknown"
    tcc = float(tcc_pct)
    if tcc < 1: return 99999, "SKC (Clear)"
    elif tcc < 25: return 3500, "FEW"
    elif tcc < 50: return 2250, "SCT"
    elif tcc < 75: return 1250, "BKN"
    else: return 800, "OVC"

# =====================================
# 🎚️ SIDEBAR (INTEGRASI LANUD)
# =====================================
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    
    selected_lanud_name = st.selectbox("🎯 Select Airbase (Lanud)", options=list(LANUD_DATABASE.keys()))
    
    # Auto-mapping berdasarkan seleksi
    current_icao = LANUD_DATABASE[selected_lanud_name]["icao"]
    current_adm1 = LANUD_DATABASE[selected_lanud_name]["adm1"]
    
    st.info(f"**ICAO:** {current_icao} | **Region:** {current_adm1}")
    
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.button("🔄 Refresh Data")
    
    st.markdown("---")
    show_qam_report = st.checkbox("Show MET Report (QAM)", value=True)
    st.caption("Data Source: BMKG API · Military Ops v2.5")

# =====================================
# 📡 DATA PROCESSING
# =====================================
st.title("Tactical Weather Operations Dashboard")

try:
    with st.spinner("🛰️ Acquiring weather intelligence..."):
        raw = fetch_forecast(current_adm1)
    
    entries = raw.get("data", [])
    if not entries:
        st.warning("No forecast data available for this region.")
        st.stop()

    mapping = { (e['lokasi'].get('kotkab') or e['lokasi'].get('adm2')): e for e in entries }
    loc_choice = st.selectbox("📍 Select Specific Area in Region", options=list(mapping.keys()))
    
    selected_entry = mapping[loc_choice]
    df = flatten_cuaca_entry(selected_entry)
    df["ws_kt"] = df["ws"] * MS_TO_KT
    
    # Time Selection (Default first index)
    now = df.iloc[0]
    
    # Calculations
    dewpt = estimate_dewpoint(now.get("t"), now.get("hu"))
    vis_sm_disp = convert_vis_to_sm(now.get('vs'))
    ceiling_ft, ceiling_label = ceiling_proxy_from_tcc(now.get("tcc"))

    # =====================================
    # ✈ FLIGHT WEATHER STATUS
    # =====================================
    st.markdown('<div class="flight-card">', unsafe_allow_html=True)
    st.markdown(f'<div style="color:#9adf4f; font-weight:bold; margin-bottom:10px;">✈ CURRENT STATUS: {selected_lanud_name}</div>', unsafe_allow_html=True)
    colA, colB, colC, colD = st.columns(4)
    with colA:
        st.write("TEMP"); st.markdown(f"<div class='metric-value'>{now.get('t','—')}°C</div>", unsafe_allow_html=True)
    with colB:
        st.write("WIND"); st.markdown(f"<div class='metric-value'>{now.get('ws_kt',0):.1f} KT</div>", unsafe_allow_html=True)
    with colC:
        st.write("VIS"); st.markdown(f"<div class='metric-value'>{vis_sm_disp}</div>", unsafe_allow_html=True)
    with colD:
        st.write("SKY"); st.markdown(f"<div class='metric-value'>{now.get('weather_desc','—')}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # =====================================
    # 📝 QAM REPORT (FORM REPLICATION)
    # =====================================
    if show_qam_report:
        st.subheader("📝 Meteorological Report (QAM/Form Replication)")
        
        qam_html = f"""
        <div style="border: 2px solid #2b3c2b; padding: 5px;">
            <div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div>
            <div class="met-report-subheader">DINAS PENGEMBANGAN OPERASI</div>
            <div class="met-report-header" style="border-top: 1px solid #2b3c2b;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</div>
            <table class="met-report-table">
                <tr>
                    <th>METEOROLOGICAL OBS AT / DATE / TIME</th>
                    <td>{now.get('local_datetime','—')} L / {now.get('utc_datetime','—')} Z</td>
                </tr>
                <tr>
                    <th>AERODROME IDENTIFICATION</th>
                    <td>{current_icao} / {selected_lanud_name}</td>
                </tr>
                <tr>
                    <th>SURFACE WIND (DIR/SPD)</th>
                    <td>{now.get('wd_deg','—')}° / {now.get('ws_kt',0):.1f} KT</td>
                </tr>
                <tr>
                    <th>HORIZONTAL VISIBILITY</th>
                    <td>{now.get('vs','—')} M ({vis_sm_disp})</td>
                </tr>
                <tr>
                    <th>PRESENT WEATHER</th>
                    <td>{now.get('weather_desc','—')} (Rain: {now.get('tp',0):.1f} mm)</td>
                </tr>
                <tr>
                    <th>CLOUD COVER & CEILING</th>
                    <td>{now.get('tcc','—')}% / {ceiling_ft if ceiling_ft < 90000 else 'None'} FT ({ceiling_label})</td>
                </tr>
                <tr>
                    <th>AIR TEMP / DEW POINT</th>
                    <td>T: {now.get('t','—')}°C / DP: {dewpt:.1f if dewpt else '—'}°C / RH: {now.get('hu','—')}%</td>
                </tr>
                <tr>
                    <th>SUPPLEMENTARY INFO</th>
                    <td>Location: {loc_choice} | Lat: {now.get('lat')} Lon: {now.get('lon')}</td>
                </tr>
            </table>
        </div>
        """
        st.markdown(qam_html, unsafe_allow_html=True)
        
        st.download_button(
            label="⬇ Download QAM Report",
            data=f"<html><head>{CSS_STYLES}</head><body>{qam_html}</body></html>",
            file_name=f"QAM_{current_icao}_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html"
        )

    # ... (Bagian Grafik Trends dan Windrose bisa dilanjutkan di bawah sini) ...

except Exception as e:
    st.error(f"Error connecting to BMKG Tactical Server: {e}")
