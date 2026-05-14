import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# =====================================
# 🌑 MILITARY INTERFACE (DARK THEME)
# =====================================
st.set_page_config(page_title="Tactical QAM Generator", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", "Roboto Mono", monospace;}
    section[data-testid="stSidebar"] {background-color: #111; border-right: 1px solid #3f4f3f;}
    h1, h2, h3 {color: #a9df52; text-transform: uppercase;}
    
    .radar-box {text-align: center; padding: 10px; border: 1px solid #33ff55; border-radius: 8px; margin-bottom: 20px;}
    .radar-sweep {
        width: 80px; height: 80px; border-radius: 50%; border: 2px solid #33ff55;
        margin: auto; position: relative; overflow: hidden;
    }
    .radar-sweep:before {
        content: ""; position: absolute; top: 50%; left: 50%; width: 50%; height: 2px;
        background: linear-gradient(90deg, #33ff55, transparent);
        transform-origin: 0% 50%; animation: sweep 3s linear infinite;
    }
    @keyframes sweep { from {transform: rotate(0deg);} to {transform: rotate(360deg);} }

    /* REPLIKA FORM FISIK QAM (KERTAS PUTIH) */
    .qam-container {
        background-color: white; color: black; padding: 50px; 
        font-family: 'Courier New', Courier, monospace; 
        border: 1px solid #000; width: 800px; margin: auto;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.5);
    }
    .qam-table { width: 100%; border-collapse: collapse; }
    .qam-table td { 
        border: 1px solid black; padding: 6px 12px; 
        vertical-align: top; font-size: 14px; font-weight: bold;
    }
    .label-col { width: 55%; text-align: left; }
    .value-col { width: 45%; text-align: left; }
    .header-section { text-align: center; margin-bottom: 30px; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

# =====================================
# 📂 DATABASE LANUD (LENGKAP 24+ STASIUN)
# =====================================
LANUD_LIST = [
    {"Nama": "Lanud Halim Perdanakusuma", "ICAO": "WIHH"},
    {"Nama": "Lanud Atang Sendjaja", "ICAO": "WIAJ"},
    {"Nama": "Lanud Soewondo", "ICAO": "WIMK"},
    {"Nama": "Lanud Roesmin Nurjadin", "ICAO": "WIBB"},
    {"Nama": "Lanud Supadio", "ICAO": "WIOO"},
    {"Nama": "Lanud Iskandar", "ICAO": "WAOI"},
    {"Nama": "Lanud Adisutjipto", "ICAO": "WARJ"},
    {"Nama": "Lanud Abdulrachman Saleh", "ICAO": "WARA"},
    {"Nama": "Lanud Iswahyudi", "ICAO": "WARI"},
    {"Nama": "Lanud Juanda", "ICAO": "WARR"},
    {"Nama": "Lanud Husein Sastranegara", "ICAO": "WICC"},
    {"Nama": "Lanud Sultan Hasanuddin", "ICAO": "WAAA"},
    {"Nama": "Lanud Sam Ratulangi", "ICAO": "WAMM"},
    {"Nama": "Lanud El Tari", "ICAO": "WATT"},
    {"Nama": "Lanud Silas Papare", "ICAO": "WAJJ"},
    {"Nama": "Lanud Manuhua", "ICAO": "WABB"},
    {"Nama": "Lanud Pattimura", "ICAO": "WAPP"},
    {"Nama": "Lanud Leo Wattimena", "ICAO": "WAEE"},
    {"Nama": "Lanud Anang Busra", "ICAO": "WAXX"},
    {"Nama": "Lanud Raden Sadjad", "ICAO": "WION"},
    {"Nama": "Lanud Sultan Iskandar Muda", "ICAO": "WITT"},
    {"Nama": "Lanud Sri Mulyono Herlambang", "ICAO": "WIPR"},
    {"Nama": "Lanud Hang Nadim", "ICAO": "WIDD"},
    {"Nama": "Lanud Raja Haji Fisabilillah", "ICAO": "WIDN"}
]

# =====================================
# ⚙️ LOGIC (PARSING & FIXING)
# =====================================
def get_metar_tactical(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"
    try:
        r = requests.get(url, timeout=10)
        root = ET.fromstring(r.text)
        m = root.find(".//METAR")
        if m is None: return None
        
        clouds = [f"{s.get('sky_cover')} {s.get('cloud_base_ft_agl', '')}FT".strip() 
                  for s in m.findall("sky_condition")]
        
        return {
            "raw": m.findtext("raw_text", "NIL"),
            "temp": m.findtext("temp_c", "NIL"),
            "dew": m.findtext("dewpoint_c", "NIL"),
            "wdir": m.findtext("wind_dir_degrees", "000"),
            "wspd": m.findtext("wind_speed_kt", "00"),
            "vis_mi": m.findtext("visibility_statute_mi", "0"),
            "alt": m.findtext("altim_in_hg", "0"),
            "obs_time": m.findtext("observation_time", "NIL"),
            "clouds": ", ".join(clouds) if clouds else "NIL"
        }
    except: return None

# =====================================
# 🖥️ MAIN UI
# =====================================
with st.sidebar:
    st.markdown('<div class="radar-box"><div class="radar-sweep"></div><br><b>SYSTEM ACTIVE</b></div>', unsafe_allow_html=True)
    target = st.selectbox("SELECT AIRBASE", [x['Nama'] for x in LANUD_LIST])
    lanud = next(x for x in LANUD_LIST if x['Nama'] == target)
    st.divider()
    if st.button("REFRESH DATA"): st.rerun()

st.title("📡 TACTICAL METAR DASHBOARD")

data = get_metar_tactical(lanud['ICAO'])

if data:
    # 1. Fix Waktu (UTC)
    try:
        dt = datetime.fromisoformat(data['obs_time'].replace('Z', '+00:00'))
        date_val = dt.strftime("%d-%m-%Y")
        time_val = dt.strftime("%H.%M")
    except: date_val, time_val = "NIL", "NIL"

    # 2. Fix Visibilitas (Bulatkan ke 100 terdekat)
    try:
        vis_raw = float(data['vis_mi']) * 1609.34
        vis_f = f"{int(round(vis_raw / 100) * 100)} M"
    except: vis_f = "NIL"

    # 3. Fix Tekanan
    qnh_mbs = f"{float(data['alt']) * 33.8639:.1f}" if data['alt'] != "0" else "NIL"

    # --- HTML FORM REPLICA ---
    qam_html = f"""
    <div class="qam-container">
        <div class="header-section">
            MARKAS BESAR ANGKATAN UDARA<br>
            DINAS PENGEMBANGAN OPERASI<br><br>
            <b style="text-decoration: underline; font-size: 18px;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</b>
        </div>
        
        <table class="qam-table">
            <tr><td class="label-col">METEOROLOGICAL OBS AT</td><td class="value-col">{lanud['ICAO']} ({target.upper()})</td></tr>
            <tr><td class="label-col">DATE</td><td class="value-col">{date_val}</td></tr>
            <tr><td class="label-col">TIME (UTC)</td><td class="value-col">{time_val}</td></tr>
            <tr><td class="label-col">AERODROME IDENTIFICATION</td><td class="value-col">{lanud['ICAO']}</td></tr>
            <tr><td class="label-col">SURFACE WIND DIRECTION, SPEED<br>AND SIGNIFICANT VARIATION</td><td class="value-col">{data['wdir']} / {data['wspd']} KT</td></tr>
            <tr><td class="label-col">HORIZONTAL VISIBILITY</td><td class="value-col">{vis_f}</td></tr>
            <tr><td class="label-col">RUNWAY VISUAL RANGE</td><td class="value-col">NIL</td></tr>
            <tr><td class="label-col">PRESENT WEATHER</td><td class="value-col">NIL</td></tr>
            <tr><td class="label-col">AMOUNT AND HEIGHT OF BASE<br>OF LOW CLOUD</td><td class="value-col">{data['clouds']}</td></tr>
            <tr><td class="label-col">AIR TEMPERATURE AND<br>DEW POINT TEMPERATURE</td><td class="value-col">{data['temp']} / {data['dew']}</td></tr>
            <tr><td class="label-col">QNH</td><td class="value-col">{qnh_mbs} mbs / {data['alt']} ins</td></tr>
            <tr><td class="label-col">QFE*</td><td class="value-col">NIL mbs / NIL ins</td></tr>
            <tr><td class="label-col">SUPPLEMENTARY INFORMATION</td><td class="value-col" style="font-size: 12px;">{data['raw']}</td></tr>
            <tr><td class="label-col">TIME OF ISSUE (UTC)</td><td class="value-col">{time_val}</td></tr>
            <tr><td class="label-col">OBSERVER</td><td class="value-col">AUTO/SYSTEM</td></tr>
        </table>
        <p style="font-size: 11px; margin-top: 10px;">*ON REQUEST</p>
    </div>
    """
    
    st.markdown(qam_html, unsafe_allow_html=True)

    st.download_button(
        label="💾 DOWNLOAD QAM FORM (.HTML)",
        data=qam_html,
        file_name=f"QAM_{lanud['ICAO']}.html",
        mime="text/html",
        type="primary"
    )
else:
    st.error("⚠️ Gagal mengambil data. Pastikan koneksi internet stabil.")
