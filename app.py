import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# =====================================
# 🌑 MILITARY INTERFACE & PHYSICAL REPLICA CSS
# =====================================
st.set_page_config(page_title="Tactical QAM System", layout="wide")

st.markdown("""
<style>
    /* UI Dashboard */
    [data-testid="stAppViewContainer"] {background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", monospace;}
    section[data-testid="stSidebar"] {background-color: #111; border-right: 1px solid #3f4f3f;}
    
    /* RADAR ANIMATION */
    .radar-container {text-align: center; padding: 20px;}
    .radar {
        position: relative; width: 100px; height: 100px; border-radius: 50%; 
        border: 2px solid #33ff55; margin: auto; box-shadow: 0 0 15px #33ff55;
    }
    .radar:before {
        content: ""; position: absolute; top: 50%; left: 50%; width: 50%; height: 2px; 
        background: linear-gradient(90deg, #33ff55, transparent); 
        transform-origin: 0% 50%; animation: sweep 2.5s linear infinite;
    }
    @keyframes sweep { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

    /* REPLIKA FORM FISIK QAM (HASIL SCAN) */
    .qam-paper {
        background-color: #ffffff; color: #000000; padding: 60px;
        font-family: 'Courier New', Courier, monospace;
        width: 850px; margin: auto; border: 1px solid #000;
        box-shadow: 10px 10px 25px rgba(0,0,0,0.7);
        line-height: 1.1;
    }
    .qam-header { text-align: center; font-weight: bold; margin-bottom: 30px; font-size: 16px; }
    .qam-table { width: 100%; border-collapse: collapse; border: 1.5px solid black; }
    .qam-table td { 
        border: 1px solid black; padding: 8px 15px; 
        font-size: 14px; font-weight: bold; vertical-align: middle;
    }
    .col-label { width: 55%; text-align: left; }
    .col-value { width: 45%; text-align: left; }
    .dotted-line { border-bottom: 1px dotted #000; display: inline-block; min-width: 50px; }
</style>
""", unsafe_allow_html=True)

# =====================================
# 📂 DATABASE LENGKAP (24 LANUD)
# =====================================
LANUD_DB = [
    {"Nama": "Lanud Halim Perdanakusuma", "ICAO": "WIHH"}, {"Nama": "Lanud Atang Sendjaja", "ICAO": "WIAJ"},
    {"Nama": "Lanud Soewondo", "ICAO": "WIMK"}, {"Nama": "Lanud Roesmin Nurjadin", "ICAO": "WIBB"},
    {"Nama": "Lanud Supadio", "ICAO": "WIOO"}, {"Nama": "Lanud Iskandar", "ICAO": "WAOI"},
    {"Nama": "Lanud Adisutjipto", "ICAO": "WARJ"}, {"Nama": "Lanud Abdulrachman Saleh", "ICAO": "WARA"},
    {"Nama": "Lanud Iswahyudi", "ICAO": "WARI"}, {"Nama": "Lanud Juanda", "ICAO": "WARR"},
    {"Nama": "Lanud Husein Sastranegara", "ICAO": "WICC"}, {"Nama": "Lanud Sultan Hasanuddin", "ICAO": "WAAA"},
    {"Nama": "Lanud Sam Ratulangi", "ICAO": "WAMM"}, {"Nama": "Lanud El Tari", "ICAO": "WATT"},
    {"Nama": "Lanud Silas Papare", "ICAO": "WAJJ"}, {"Nama": "Lanud Manuhua", "ICAO": "WABB"},
    {"Nama": "Lanud Pattimura", "ICAO": "WAPP"}, {"Nama": "Lanud Leo Wattimena", "ICAO": "WAEE"},
    {"Nama": "Lanud Anang Busra", "ICAO": "WAXX"}, {"Nama": "Lanud Raden Sadjad", "ICAO": "WION"},
    {"Nama": "Lanud Sultan Iskandar Muda", "ICAO": "WITT"}, {"Nama": "Lanud Sri Mulyono Herlambang", "ICAO": "WIPR"},
    {"Nama": "Lanud Hang Nadim", "ICAO": "WIDD"}, {"Nama": "Lanud Raja Haji Fisabilillah", "ICAO": "WIDN"}
]

# =====================================
# ⚙️ LOGIC & DATA FETCHING
# =====================================
def get_metar_xml(icao):
    try:
        url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"
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
# 🖥️ UI APPLICATION
# =====================================
with st.sidebar:
    st.markdown('<div class="radar-container"><div class="radar"></div></div>', unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; color:#a9df52;'>OPERATIONAL UNIT</h3>", unsafe_allow_html=True)
    sel_lanud = st.selectbox("PILIH PANGKALAN", [x['Nama'] for x in LANUD_DB])
    lanud = next(x for x in LANUD_DB if x['Nama'] == sel_lanud)
    st.divider()
    st.write(f"**ICAO:** {lanud['ICAO']}")
    st.write(f"**STATUS:** MONITORING")

st.title("📡 TACTICAL QAM GENERATOR")

data = get_metar_xml(lanud['ICAO'])

if data:
    # --- DATA PROCESSING ---
    # 1. Fix Tanggal & Jam (UTC)
    try:
        dt = datetime.fromisoformat(data['obs_time'].replace('Z', '+00:00'))
        date_str = dt.strftime("%d-%m-%Y")
        time_str = dt.strftime("%H.%M")
    except:
        date_str, time_str = "NIL", "NIL"

    # 2. Fix Visibilitas (Bulatkan ke 100 terdekat)
    try:
        vis_val = int(round((float(data['vis_mi']) * 1609.34) / 100) * 100)
        vis_display = f"{vis_val} M"
    except:
        vis_display = "NIL"

    # 3. Fix Tekanan (QNH)
    try:
        qnh_mbs = f"{float(data['alt']) * 33.8639:.1f}"
        qnh_ins = f"{float(data['alt']):.2f}"
    except:
        qnh_mbs, qnh_ins = "NIL", "NIL"

    # --- REPLIKA FORM FISIK TNI AU ---
    qam_physical_form = f"""
    <div class="qam-paper">
        <div class="qam-header">
            MARKAS BESAR ANGKATAN UDARA<br>
            DINAS PENGEMBANGAN OPERASI<br><br>
            <span style="text-decoration: underline;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</span>
        </div>
        
        <table class="qam-table">
            <tr><td class="col-label">METEOROLOGICAL OBS AT</td><td class="col-value">{lanud['ICAO']} ({sel_lanud.upper()})</td></tr>
            <tr><td class="col-label">DATE</td><td class="col-value">{date_str}</td></tr>
            <tr><td class="col-label">TIME (UTC)</td><td class="col-value">{time_str}</td></tr>
            <tr><td class="col-label">AERODROME IDENTIFICATION</td><td class="col-value">{lanud['ICAO']}</td></tr>
            <tr><td class="col-label">SURFACE WIND DIRECTION, SPEED<br>AND SIGNIFICANT VARIATION</td><td class="col-value">{data['wdir']} / {data['wspd']} KT</td></tr>
            <tr><td class="col-label">HORIZONTAL VISIBILITY</td><td class="col-value">{vis_display}</td></tr>
            <tr><td class="col-label">RUNWAY VISUAL RANGE</td><td class="col-value">NIL</td></tr>
            <tr><td class="col-label">PRESENT WEATHER</td><td class="col-value">NIL</td></tr>
            <tr><td class="col-label">AMOUNT AND HEIGHT OF BASE<br>OF LOW CLOUD</td><td class="col-value">{data['clouds']}</td></tr>
            <tr><td class="col-label">AIR TEMPERATURE AND<br>DEW POINT TEMPERATURE</td><td class="col-value">{data['temp']} / {data['dew']}</td></tr>
            <tr>
                <td class="col-label">QNH</td>
                <td class="col-value">{qnh_mbs} mbs / {qnh_ins} ins</td>
            </tr>
            <tr>
                <td class="col-label">QFE*</td>
                <td class="col-value">NIL mbs / NIL ins</td>
            </tr>
            <tr><td class="col-label">SUPPLEMENTARY INFORMATION</td><td class="col-value" style="font-size: 11px; font-weight: normal;">{data['raw']}</td></tr>
            <tr><td class="col-label">TIME OF ISSUE (UTC)</td><td class="col-value">{time_str}</td></tr>
            <tr><td class="col-label">OBSERVER</td><td class="col-value">AUTO/SYSTEM</td></tr>
        </table>
        <div style="margin-top: 15px; font-size: 11px; font-style: italic;">*ON REQUEST</div>
    </div>
    """

    st.markdown(qam_physical_form, unsafe_allow_html=True)
    
    st.divider()
    
    # Tombol Download
    st.download_button(
        label="⬇️ DOWNLOAD FORM QAM (HTML)",
        data=qam_physical_form,
        file_name=f"QAM_{lanud['ICAO']}_{date_str}.html",
        mime="text/html",
        type="primary"
    )

else:
    st.error("Gagal sinkronisasi dengan server AviationWeather. Pastikan ICAO aktif.")
