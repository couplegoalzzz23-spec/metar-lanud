import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# =====================================
# 🌑 TEMA MILITER (SESUAI REQUEST)
# =====================================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", "Roboto Mono", monospace;}
    h1, h2, h3, h4 {color: #a9df52; text-transform: uppercase; letter-spacing: 1px;}
    section[data-testid="stSidebar"] {background-color: #111; border-right: 1px solid #3f4f3f;}
    .stButton>button {background-color: #1a2a1f; color: #a9df52; border: 1px solid #3f4f3f; border-radius: 4px; width: 100%;}
    div[data-testid="stMetricValue"] {color: #a9df52 !important; font-family: 'Courier New';}
    
    .radar-container {text-align: center; padding: 20px;}
    .radar {
        position: relative; width: 100px; height: 100px; border-radius: 50%; 
        border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 15px #33ff55;
    }
    .radar:before {
        content: ""; position: absolute; top: 50%; left: 50%; width: 50%; height: 2px; 
        background: linear-gradient(90deg, #33ff55, transparent); 
        transform-origin: 0% 50%; animation: sweep 2.5s linear infinite;
    }
    @keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

    /* QAM PHYSICAL FORM REPLICA */
    .qam-physical {
        background-color: white; color: black; padding: 40px; 
        font-family: 'Courier New', Courier, monospace; border: 1px solid #000;
        line-height: 1.2; max-width: 850px; margin: auto;
    }
    .qam-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .qam-table td { border: 1px solid black; padding: 5px 10px; vertical-align: top; font-size: 13px; }
    .header-text { text-align: center; font-weight: bold; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# =====================================
# 📂 DATA SELURUH LANUD (DATABASE LENGKAP)
# =====================================
LANUD_DATA = [
    {'Nama': 'Lanud Halim Perdanakusuma', 'ICAO': 'WIHH'}, {'Nama': 'Lanud Atang Sendjaja', 'ICAO': 'WIAJ'},
    {'Nama': 'Lanud Soewondo', 'ICAO': 'WIMK'}, {'Nama': 'Lanud Roesmin Nurjadin', 'ICAO': 'WIBB'},
    {'Nama': 'Lanud Supadio', 'ICAO': 'WIOO'}, {'Nama': 'Lanud Iskandar', 'ICAO': 'WAOI'},
    {'Nama': 'Lanud Adisutjipto', 'ICAO': 'WARJ'}, {'Nama': 'Lanud Abdulrachman Saleh', 'ICAO': 'WARA'},
    {'Nama': 'Lanud Iswahyudi', 'ICAO': 'WARI'}, {'Nama': 'Lanud Juanda', 'ICAO': 'WARR'},
    {'Nama': 'Lanud Husein Sastranegara', 'ICAO': 'WICC'}, {'Nama': 'Lanud Sultan Hasanuddin', 'ICAO': 'WAAA'},
    {'Nama': 'Lanud Sam Ratulangi', 'ICAO': 'WAMM'}, {'Nama': 'Lanud El Tari', 'ICAO': 'WATT'},
    {'Nama': 'Lanud Silas Papare', 'ICAO': 'WAJJ'}, {'Nama': 'Lanud Manuhua', 'ICAO': 'WABB'},
    {'Nama': 'Lanud Pattimura', 'ICAO': 'WAPP'}, {'Nama': 'Lanud Leo Wattimena', 'ICAO': 'WAEE'},
    {'Nama': 'Lanud Anang Busra', 'ICAO': 'WAXX'}, {'Nama': 'Lanud Raden Sadjad', 'ICAO': 'WION'},
    {'Nama': 'Lanud Sultan Iskandar Muda', 'ICAO': 'WITT'}, {'Nama': 'Lanud Sri Mulyono Herlambang', 'ICAO': 'WIPR'},
    {'Nama': 'Lanud Hang Nadim', 'ICAO': 'WIDD'}, {'Nama': 'Lanud Raja Haji Fisabilillah', 'ICAO': 'WIDN'}
]

def fetch_metar_data(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"
    try:
        res = requests.get(url, timeout=10)
        root = ET.fromstring(res.text)
        metar = root.find(".//METAR")
        if metar is None: return None
        
        clouds = [f"{s.get('sky_cover')} {s.get('cloud_base_ft_agl', '')}FT".strip() 
                  for s in metar.findall("sky_condition")]
            
        return {
            "raw": metar.findtext("raw_text", "NIL"),
            "temp": metar.findtext("temp_c", "NIL"),
            "dew": metar.findtext("dewpoint_c", "NIL"),
            "wdir": metar.findtext("wind_dir_degrees", "000"),
            "wspd": metar.findtext("wind_speed_kt", "00"),
            "vis_mi": metar.findtext("visibility_statute_mi", "0"),
            "alt": metar.findtext("altim_in_hg", "0"),
            "obs_time": metar.findtext("observation_time", "NIL"),
            "clouds": ", ".join(clouds) if clouds else "NIL"
        }
    except: return None

# =====================================
# 🖥️ INTERFACE
# =====================================
with st.sidebar:
    st.markdown('<div class="radar-container"><div class="radar"></div></div>', unsafe_allow_html=True)
    sel_name = st.selectbox("PILIH PANGKALAN (TARGET)", [x['Nama'] for x in LANUD_DATA])
    lanud = next(x for x in LANUD_DATA if x['Nama'] == sel_name)
    st.divider()

st.title("📡 TACTICAL METAR MONITORING")

data = fetch_metar_data(lanud['ICAO'])

if data:
    # Perbaikan Waktu
    try:
        dt = datetime.fromisoformat(data['obs_time'].replace('Z', '+00:00'))
        date_f, time_f = dt.strftime("%d-%m-%Y"), dt.strftime("%H.%M")
    except: date_f, time_f = "NIL", "NIL"

    # Perbaikan Visibilitas (Bulatkan ke 100 terdekat)
    try:
        vis_m = int(round((float(data['vis_mi']) * 1609.34) / 100) * 100)
        vis_str = f"{vis_m} M"
    except: vis_str = "NIL"

    # Perbaikan Tekanan
    qnh_mbs = f"{float(data['alt']) * 33.8639:.1f}" if data['alt'] != "0" else "NIL"

    # --- REPLIKA FORM FISIK QAM ---
    qam_html = f"""
    <div class="qam-physical">
        <div class="header-text">
            MARKAS BESAR ANGKATAN UDARA<br>
            DINAS PENGEMBANGAN OPERASI<br><br>
            <span style="text-decoration: underline;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</span>
        </div>
        
        <table class="qam-table">
            <tr><td style="width: 50%;">METEOROLOGICAL OBS AT</td><td>{lanud['ICAO']} ({sel_name.upper()})</td></tr>
            <tr><td>DATE</td><td>{date_f}</td></tr>
            <tr><td>TIME (UTC)</td><td>{time_f}</td></tr>
            <tr><td>AERODROME IDENTIFICATION</td><td>{lanud['ICAO']}</td></tr>
            <tr><td>SURFACE WIND DIRECTION, SPEED<br>AND SIGNIFICANT VARIATION</td><td>{data['wdir']} / {data['wspd']} KT</td></tr>
            <tr><td>HORIZONTAL VISIBILITY</td><td>{vis_str}</td></tr>
            <tr><td>RUNWAY VISUAL RANGE</td><td>NIL</td></tr>
            <tr><td>PRESENT WEATHER</td><td>NIL</td></tr>
            <tr><td>AMOUNT AND HEIGHT OF BASE<br>OF LOW CLOUD</td><td>{data['clouds']}</td></tr>
            <tr><td>AIR TEMPERATURE AND<br>DEW POINT TEMPERATURE</td><td>{data['temp']} / {data['dew']}</td></tr>
            <tr>
                <td>QNH</td>
                <td>{qnh_mbs} mbs / {data['alt']} ins</td>
            </tr>
            <tr>
                <td>QFE*</td>
                <td>NIL mbs / NIL ins</td>
            </tr>
            <tr><td>SUPPLEMENTARY INFORMATION</td><td style="font-size: 11px;">{data['raw']}</td></tr>
            <tr><td>TIME OF ISSUE (UTC)</td><td>{time_f}</td></tr>
            <tr><td>OBSERVER</td><td>AUTO/SYSTEM</td></tr>
        </table>
        <div style="margin-top: 15px; font-size: 10px; font-style: italic;">*ON REQUEST</div>
    </div>
    """
    
    st.markdown(qam_html, unsafe_allow_html=True)

    st.download_button(
        label="💾 EXPORT QAM FORM (HTML)",
        data=qam_html,
        file_name=f"QAM_{lanud['ICAO']}_{date_f}.html",
        mime="text/html"
    )
else:
    st.error("DATA GAGAL DIPROSES.")
