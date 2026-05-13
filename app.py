import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime

# =====================================
# ⚙️ DATABASE LANUD LENGKAP (ICAO, WMO, ADM1)
# =====================================
# ADM1: Kode Provinsi BMKG | WMO: Station ID (Jika tersedia di BMKG/WMO)
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
    "Lanud Maimun Saleh (Sabang)": {"icao": "WITN", "wmo": "96001", "adm1": "11"},
    "Lanud Pattimura (Ambon)": {"icao": "WAPP", "wmo": "97560", "adm1": "81"},
    "Lanud Syamsudin Noor (Banjarmasin)": {"icao": "WAOO", "wmo": "96685", "adm1": "63"},
    "Lanud Ngurah Rai (Bali)": {"icao": "WADD", "wmo": "97230", "adm1": "51"}
}

# =====================================
# 🌑 CSS — MILITARY STYLE
# =====================================
CSS_STYLES = """
<style>
body { background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", monospace; }
.met-report-table { border: 1px solid #2b3c2b; width: 100%; background-color: #0f1111; font-size: 0.9rem; border-collapse: collapse; }
.met-report-table th, .met-report-table td { border: 1px solid #2b3c2b; padding: 6px 10px; text-align: left; }
.met-report-table th { background-color: #1a1c1c; color: #a9df52; text-transform: uppercase; width: 40%; }
.met-report-header { text-align: center; background-color: #111; color: #a9df52; font-weight: bold; padding: 10px; border: 1px solid #2b3c2b; border-bottom: none; }
.met-report-subheader { text-align: center; color: #cfd2c3; font-size: 0.75rem; padding-bottom: 8px; border-left: 1px solid #2b3c2b; border-right: 1px solid #2b3c2b; }
.metric-value { font-size: 1.8rem; color: #b6ff6d; font-weight: bold; }
</style>
"""
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# =====================================
# 📡 UTILITAS API BMKG
# =====================================
@st.cache_data(ttl=300)
def fetch_forecast(adm1):
    url = f"https://cuaca.bmkg.go.id/api/df/v1/forecast/adm?adm1={adm1}"
    resp = requests.get(url, timeout=10)
    return resp.json()

def process_data(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            obs.update({k: lokasi.get(k) for k in ["adm1", "adm2", "provinsi", "kotkab", "lon", "lat"]})
            rows.append(obs)
    df = pd.DataFrame(rows)
    for c in ["t","hu","ws","vs","tp","tcc","wd_deg"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# =====================================
# 🎚️ SIDEBAR
# =====================================
with st.sidebar:
    st.title("🛰️ Tactical Dashboard")
    selected_name = st.selectbox("🎯 Select Lanud", options=list(LANUD_DATABASE.keys()))
    
    # Extract DB Info
    db_info = LANUD_DATABASE[selected_name]
    icao = db_info["icao"]
    wmo = db_info["wmo"]
    adm1 = db_info["adm1"]
    
    st.success(f"**IDENT:** {icao} | **WMO:** {wmo}")
    st.info(f"**BMKG Region:** {adm1}")
    st.markdown("---")
    show_qam = st.checkbox("Show QAM Form", value=True)

# =====================================
# 📡 MAIN OPS
# =====================================
st.title("Tactical Weather Operations Dashboard")

try:
    data_raw = fetch_forecast(adm1)
    entries = { (e['lokasi'].get('kotkab') or e['lokasi'].get('adm2')): e for e in data_raw.get("data", []) }
    
    # Pilih sektor area di dalam provinsi tersebut
    loc_choice = st.selectbox("📍 Sector Selection", options=list(entries.keys()))
    df = process_data(entries[loc_choice])
    now = df.iloc[0]

    # Pre-calculations
    ws_kt = now['ws'] * 1.94384
    vis_sm = now['vs'] * 0.000621371
    temp = now['t']
    hum = now['hu']
    dewpt = temp - ((100 - hum) / 5) if pd.notna(temp) else 0

    # =====================================
    # 📝 QAM FORM REPLICATION
    # =====================================
    if show_qam:
        st.subheader("📝 Meteorological Report (QAM/Form Replication)")
        
        qam_html = f"""
        <div style="background-color: #0b0c0c; padding: 10px;">
            <div class="met-report-header">MARKAS BESAR ANGKATAN UDARA</div>
            <div class="met-report-subheader">DINAS PENGEMBANGAN OPERASI</div>
            <div class="met-report-header" style="border-top: 1px solid #2b3c2b; font-size: 0.9rem;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</div>
            <table class="met-report-table">
                <tr>
                    <th>OBS TIME / DATE</th>
                    <td>{now.get('local_datetime','—')} (L) / {now.get('utc_datetime','—')} (Z)</td>
                </tr>
                <tr>
                    <th>AERODROME / WMO ID</th>
                    <td><b>{icao}</b> / WMO: {wmo}</td>
                </tr>
                <tr>
                    <th>SURFACE WIND (DIR/SPD)</th>
                    <td>{now.get('wd_deg','—')}° / {ws_kt:.1f} KT</td>
                </tr>
                <tr>
                    <th>HORIZONTAL VISIBILITY</th>
                    <td>{now.get('vs','—')} M ({vis_sm:.1f} SM)</td>
                </tr>
                <tr>
                    <th>PRESENT WEATHER</th>
                    <td>{now.get('weather_desc','—')}</td>
                </tr>
                <tr>
                    <th>CLOUD COVER / CEILING</th>
                    <td>{now.get('tcc','—')}% / Est: {800 if now['tcc'] > 75 else 2500} FT</td>
                </tr>
                <tr>
                    <th>TEMP / DEW POINT / RH</th>
                    <td>T: {temp}°C | DP: {dewpt:.1f}°C | RH: {hum}%</td>
                </tr>
                <tr>
                    <th>SUPPLEMENTARY INFO</th>
                    <td>LANUD: {selected_name} | SECTOR: {loc_choice}</td>
                </tr>
            </table>
        </div>
        """
        st.markdown(qam_html, unsafe_allow_html=True)
        
        # Download Button
        st.download_button(
            label="⬇ Export QAM HTML",
            data=f"<html><head>{CSS_STYLES}</head><body>{qam_html}</body></html>",
            file_name=f"QAM_{icao}_{datetime.now().strftime('%H%M')}.html",
            mime="text/html"
        )

    # Key Metrics Display
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Wind Speed", f"{ws_kt:.1f} KT")
    c2.metric("Visibility", f"{vis_sm:.1f} SM")
    c3.metric("Air Temp", f"{temp}°C")
    c4.metric("Humidity", f"{hum}%")

except Exception as e:
    st.error(f"Operational Data Link Severed: {e}")
