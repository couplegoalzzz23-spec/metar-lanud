import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import io

# Konfigurasi Halaman
st.set_page_config(page_title="Tactical METAR & QAM TNI AU", page_icon="✈️", layout="wide")

# CSS untuk Tampilan Dashboard dan Preview Laporan
st.markdown("""
<style>
    .stApp { background-color: #0b1623; color: white; }
    .qam-preview { 
        background-color: white; color: black; padding: 40px; 
        border-radius: 5px; font-family: "Courier New", Courier, monospace; 
        line-height: 1.2; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .qam-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    .qam-table td { border: 1px solid #000; padding: 6px 10px; font-size: 10pt; }
    .qam-label { font-weight: bold; width: 45%; }
    .header-text { text-align: center; font-weight: bold; margin-bottom: 0; }
    .sub-table { width: 100%; border: none !important; }
    .sub-table td { border: none !important; padding: 0 !important; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# DATA DATABASE LANUD (EMBEDDED)
# =========================================================
LANUD_DATA = [
    {'Nama_Lanud': 'Lanud Halim Perdanakusuma', 'ICAO': 'WIHH', 'WMO': '96749', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Atang Sendjaja', 'ICAO': 'WIAJ', 'WMO': 'NIL', 'Status': 'MILITER / NON PUBLIK'},
    {'Nama_Lanud': 'Lanud Soewondo', 'ICAO': 'WIMK', 'WMO': '96035', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Roesmin Nurjadin', 'ICAO': 'WIBB', 'WMO': '96109', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Supadio', 'ICAO': 'WIOO', 'WMO': '96413', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Iskandar', 'ICAO': 'WAOI', 'WMO': '96655', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Adisutjipto', 'ICAO': 'WARJ', 'WMO': '96839', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Abdulrachman Saleh', 'ICAO': 'WARA', 'WMO': '96881', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Iswahyudi', 'ICAO': 'WARI', 'WMO': '96877', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Juanda', 'ICAO': 'WARR', 'WMO': '96935', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Husein Sastranegara', 'ICAO': 'WICC', 'WMO': '96781', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Sultan Hasanuddin', 'ICAO': 'WAAA', 'WMO': '97180', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Sam Ratulangi', 'ICAO': 'WAMM', 'WMO': '97014', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud El Tari', 'ICAO': 'WATT', 'WMO': '97268', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Silas Papare', 'ICAO': 'WAJJ', 'WMO': '98233', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Manuhua', 'ICAO': 'WABB', 'WMO': '97502', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Pattimura', 'ICAO': 'WAPP', 'WMO': '97724', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Leo Wattimena', 'ICAO': 'WAEE', 'WMO': '97600', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Anang Busra', 'ICAO': 'WAXX', 'WMO': '96509', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Syamsudin Noor', 'ICAO': 'WAAA', 'WMO': '97180', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Raden Sadjad', 'ICAO': 'WION', 'WMO': '96011', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Maimun Saleh', 'ICAO': 'WITN', 'WMO': '96001', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Sultan Iskandar Muda', 'ICAO': 'WITT', 'WMO': '96011', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Sri Mulyono Herlambang', 'ICAO': 'WIPR', 'WMO': '96223', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Hang Nadim', 'ICAO': 'WIDD', 'WMO': '96109', 'Status': 'AKTIF'},
    {'Nama_Lanud': 'Lanud Raja Haji Fisabilillah', 'ICAO': 'WIDN', 'WMO': '96109', 'Status': 'AKTIF'}
]

# =========================================================
# FUNGSI FETCH METAR
# =========================================================
@st.cache_data(ttl=300)
def fetch_metar(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"
    try:
        res = requests.get(url, timeout=10)
        root = ET.fromstring(res.text)
        metar = root.find(".//METAR")
        if metar is None: return None
        
        clouds = []
        for sky in metar.findall("sky_condition"):
            cover = sky.get("sky_cover", "")
            base = sky.get("cloud_base_ft_agl", "")
            clouds.append(f"{cover} {base}FT".strip())
            
        return {
            "raw": metar.findtext("raw_text", "NIL"),
            "temp": metar.findtext("temp_c", "NIL"),
            "dew": metar.findtext("dewpoint_c", "NIL"),
            "wdir": metar.findtext("wind_dir_degrees", "000"),
            "wspd": metar.findtext("wind_speed_kt", "00"),
            "vis": metar.findtext("visibility_statute_mi", "NIL"),
            "alt": metar.findtext("altim_in_hg", "0"),
            "time": metar.findtext("observation_time", "NIL"),
            "clouds": ", ".join(clouds) if clouds else "NIL"
        }
    except: return None

# =========================================================
# INTERFACE UTAMA
# =========================================================
st.sidebar.title("✈️ NAVIGASI LANUD")
lanud_names = [item['Nama_Lanud'] for item in LANUD_DATA]
selected_name = st.sidebar.selectbox("Pilih Pangkalan Udara", lanud_names)
lanud = next(item for item in LANUD_DATA if item['Nama_Lanud'] == selected_name)

st.sidebar.markdown(f"**ICAO:** `{lanud['ICAO']}`")
st.sidebar.markdown(f"**WMO:** `{lanud['WMO']}`")
st.sidebar.markdown(f"**Status:** {lanud['Status']}")

st.title(f"📊 METAR/QAM Dashboard: {selected_name}")

data = fetch_metar(lanud['ICAO'])

if data:
    # Konversi data untuk form
    try:
        vis_m = f"{int(float(data['vis']) * 1609.34)} M"
    except: vis_m = "NIL"
    
    try:
        qnh_hpa = f"{float(data['alt']) * 33.8639:.1f}"
    except: qnh_hpa = "NIL"

    try:
        dt = datetime.strptime(data['time'], "%Y-%m-%dT%H:%M:%SZ")
        date_f, time_f = dt.strftime("%d-%m-%Y"), dt.strftime("%H.%M")
    except: date_f, time_f = "NIL", "NIL"

    # Preview Laporan QAM
    st.markdown("### 📄 Preview Laporan QAM (Form Take Off/Landing)")
    
    qam_html = f"""
    <div class="qam-preview">
        <div class="header-text">MARKAS BESAR ANGKATAN UDARA</div>
        <div class="header-text" style="margin-bottom: 20px;">DINAS PENGEMBANGAN OPERASI</div>
        <div class="header-text" style="text-decoration: underline; margin-bottom: 25px;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</div>
        
        <table class="qam-table">
            <tr><td class="qam-label">METEOROLOGICAL OBS AT</td><td>{lanud['ICAO']} ({selected_name.upper()})</td></tr>
            <tr><td class="qam-label">DATE</td><td>{date_f}</td></tr>
            <tr><td class="qam-label">TIME (UTC)</td><td>{time_f}</td></tr>
            <tr><td class="qam-label">AERODROME IDENTIFICATION</td><td>{lanud['ICAO']}</td></tr>
            <tr><td class="qam-label">SURFACE WIND (DIR/SPD)</td><td>{data['wdir']}/{data['wspd']} KT</td></tr>
            <tr><td class="qam-label">HORIZONTAL VISIBILITY</td><td>{vis_m}</td></tr>
            <tr><td class="qam-label">PRESENT WEATHER</td><td>NIL</td></tr>
            <tr><td class="qam-label">CLOUDS (AMOUNT/HEIGHT)</td><td>{data['clouds']}</td></tr>
            <tr><td class="qam-label">TEMPERATURE / DEW POINT</td><td>{data['temp']} / {data['dew']}</td></tr>
            <tr>
                <td class="qam-label">QNH</td>
                <td>
                    <table class="sub-table">
                        <tr><td>{qnh_hpa} mbs</td></tr>
                        <tr><td>{data['alt']} ins</td></tr>
                    </table>
                </td>
            </tr>
            <tr><td class="qam-label">SUPPLEMENTARY INFO</td><td>{data['raw']}</td></tr>
            <tr><td class="qam-label">OBSERVER</td><td>AUTO/SYSTEM</td></tr>
        </table>
    </div>
    """
    
    st.markdown(qam_html, unsafe_allow_html=True)
    
    # Download Button (HTML based, format PDF bisa via Print)
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="⬇️ Download Dokumen QAM (.html)",
        data=qam_html,
        file_name=f"QAM_{lanud['ICAO']}_{date_f}.html",
        mime="text/html",
        type="primary"
    )
    st.info("💡 Klik tombol di atas untuk menyimpan laporan. Anda bisa membukanya di browser dan memilih 'Print -> Save as PDF' untuk mendapatkan file PDF resmi.")

else:
    st.error(f"⚠️ Data METAR untuk {lanud['ICAO']} saat ini tidak tersedia atau bersifat privat (Non-Publik).")
