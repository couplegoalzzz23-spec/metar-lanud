import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# =====================================
# 🌑 CSS — MILITARY STYLE + RADAR ANIMATION
# =====================================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", "Roboto Mono", monospace;}
    h1, h2, h3, h4 {color: #a9df52; text-transform: uppercase; letter-spacing: 1px;}
    section[data-testid="stSidebar"] {background-color: #111; border-right: 1px solid #3f4f3f;}
    .stButton>button {background-color: #1a2a1f; color: #a9df52; border: 1px solid #3f4f3f; border-radius: 4px; width: 100%;}
    div[data-testid="stMetricValue"] {color: #a9df52 !important; font-family: 'Courier New';}
    
    /* RADAR ANIMATION */
    .radar-container {text-align: center; padding: 20px;}
    .radar {
        position: relative; width: 120px; height: 120px; border-radius: 50%; 
        background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%); 
        background-size: 15px 15px; border: 2px solid #33ff55; overflow: hidden; 
        margin: auto; box-shadow: 0 0 15px #33ff55;
    }
    .radar:before {
        content: ""; position: absolute; top: 50%; left: 50%; width: 50%; height: 2px; 
        background: linear-gradient(90deg, #33ff55, transparent); 
        transform-origin: 0% 50%; animation: sweep 2.5s linear infinite;
    }
    @keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    
    /* QAM TABLE STYLE */
    .qam-box {
        background-color: #f8f9fa; color: #1a1a1a; padding: 25px; 
        border: 2px solid #000; font-family: 'Courier New', Courier, monospace;
    }
</style>
""", unsafe_allow_html=True)

# =====================================
# 🛠️ DATABASE & LOGIC
# =====================================
LANUD_DATA = [
    {'Nama': 'Lanud Halim Perdanakusuma', 'ICAO': 'WIHH'},
    {'Nama': 'Lanud Roesmin Nurjadin', 'ICAO': 'WIBB'},
    {'Nama': 'Lanud Iswahyudi', 'ICAO': 'WARI'},
    {'Nama': 'Lanud Adisutjipto', 'ICAO': 'WARJ'},
    {'Nama': 'Lanud Sultan Hasanuddin', 'ICAO': 'WAAA'},
    {'Nama': 'Lanud Abdulrachman Saleh', 'ICAO': 'WARA'}
]

def fetch_metar(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"
    try:
        res = requests.get(url, timeout=10)
        root = ET.fromstring(res.text)
        metar = root.find(".//METAR")
        if metar is None: return None
        
        # Ekstraksi Awan
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
# 🖥️ UI LAYOUT
# =====================================
with st.sidebar:
    st.markdown('<div class="radar-container"><div class="radar"></div><p style="color:#a9df52; margin-top:10px;">SCANNING AIRSPACE...</p></div>', unsafe_allow_html=True)
    sel_name = st.selectbox("TARGET BASE", [x['Nama'] for x in LANUD_DATA])
    lanud = next(x for x in LANUD_DATA if x['Nama'] == sel_name)
    st.divider()
    st.info(f"Unit: {lanud['ICAO']}\nStatus: Monitoring")

st.title("📡 TACTICAL WEATHER DASHBOARD")
st.subheader(f"OPERATIONAL SECTOR: {sel_name}")

data = fetch_metar(lanud['ICAO'])

if data:
    # --- DATA NORMALIZATION ---
    # Fix Time (UTC)
    try:
        dt = datetime.fromisoformat(data['obs_time'].replace('Z', '+00:00'))
        date_f, time_f = dt.strftime("%d-%m-%Y"), dt.strftime("%H.%M")
    except:
        date_f, time_f = "NIL", "NIL"

    # Fix Visibility (6002 -> 6000)
    try:
        vis_m = int(round((float(data['vis_mi']) * 1609.34) / 100) * 100)
        vis_display = f"{vis_m} M"
    except:
        vis_display = "NIL"

    # Fix Pressure
    qnh_hpa = f"{float(data['alt']) * 33.8639:.1f}" if data['alt'] != "0" else "NIL"

    # --- METRIC DISPLAY ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("WIND", f"{data['wdir']}°/{data['wspd']}KT")
    c2.metric("VIS", vis_display)
    c3.metric("TEMP", f"{data['temp']}°C")
    c4.metric("QNH", f"{qnh_hpa}")

    # --- QAM REPORT SECTION ---
    st.markdown("### 📝 GENERATED QAM FORM")
    
    qam_html = f"""
    <div class="qam-box">
        <center>
            <b>MARKAS BESAR ANGKATAN UDARA</b><br>
            <b>DINAS PENGEMBANGAN OPERASI</b><br><br>
            <u>METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</u>
        </center>
        <br>
        <table style="width:100%; border-collapse:collapse;">
            <tr><td style="width:45%; border:1px solid #000; padding:5px;"><b>METEOROLOGICAL OBS AT</b></td><td style="border:1px solid #000; padding:5px;">{lanud['ICAO']} ({sel_name.upper()})</td></tr>
            <tr><td style="border:1px solid #000; padding:5px;"><b>DATE</b></td><td style="border:1px solid #000; padding:5px;">{date_f}</td></tr>
            <tr><td style="border:1px solid #000; padding:5px;"><b>TIME (UTC)</b></td><td style="border:1px solid #000; padding:5px;">{time_f}</td></tr>
            <tr><td style="border:1px solid #000; padding:5px;"><b>SURFACE WIND</b></td><td style="border:1px solid #000; padding:5px;">{data['wdir']}/{data['wspd']} KT</td></tr>
            <tr><td style="border:1px solid #000; padding:5px;"><b>HORIZONTAL VISIBILITY</b></td><td style="border:1px solid #000; padding:5px;">{vis_display}</td></tr>
            <tr><td style="border:1px solid #000; padding:5px;"><b>CLOUDS (AMT/HGT)</b></td><td style="border:1px solid #000; padding:5px;">{data['clouds']}</td></tr>
            <tr><td style="border:1px solid #000; padding:5px;"><b>QNH</b></td><td style="border:1px solid #000; padding:5px;">{qnh_hpa} MBS / {data['alt']} INS</td></tr>
            <tr><td style="border:1px solid #000; padding:5px;"><b>SUPPLEMENTARY INFO</b></td><td style="border:1px solid #000; padding:5px; font-size:11px;">{data['raw']}</td></tr>
        </table>
    </div>
    """
    st.markdown(qam_html, unsafe_allow_html=True)

    # Download Button
    st.download_button(
        label="💾 EXPORT REPORT (HTML)",
        data=qam_html,
        file_name=f"QAM_{lanud['ICAO']}.html",
        mime="text/html"
    )
else:
    st.error("❌ SIGNAL LOST: Gagal mengambil data METAR.")
