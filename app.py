import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# =========================================================
# DATABASE LANUD (EMBEDDED - TIDAK BUTUH CSV)
# =========================================================
LANUD_DATA = [
    {'Nama_Lanud': 'Lanud Halim Perdanakusuma', 'ICAO': 'WIHH'},
    {'Nama_Lanud': 'Lanud Atang Sendjaja', 'ICAO': 'WIAJ'},
    {'Nama_Lanud': 'Lanud Soewondo', 'ICAO': 'WIMK'},
    {'Nama_Lanud': 'Lanud Roesmin Nurjadin', 'ICAO': 'WIBB'},
    {'Nama_Lanud': 'Lanud Supadio', 'ICAO': 'WIOO'},
    {'Nama_Lanud': 'Lanud Iskandar', 'ICAO': 'WAOI'},
    {'Nama_Lanud': 'Lanud Adisutjipto', 'ICAO': 'WARJ'},
    {'Nama_Lanud': 'Lanud Abdulrachman Saleh', 'ICAO': 'WARA'},
    {'Nama_Lanud': 'Lanud Iswahyudi', 'ICAO': 'WARI'},
    {'Nama_Lanud': 'Lanud Juanda', 'ICAO': 'WARR'},
    {'Nama_Lanud': 'Lanud Husein Sastranegara', 'ICAO': 'WICC'},
    {'Nama_Lanud': 'Lanud Sultan Hasanuddin', 'ICAO': 'WAAA'},
    {'Nama_Lanud': 'Lanud Sam Ratulangi', 'ICAO': 'WAMM'},
    {'Nama_Lanud': 'Lanud El Tari', 'ICAO': 'WATT'},
    {'Nama_Lanud': 'Lanud Silas Papare', 'ICAO': 'WAJJ'},
    {'Nama_Lanud': 'Lanud Manuhua', 'ICAO': 'WABB'},
    {'Nama_Lanud': 'Lanud Pattimura', 'ICAO': 'WAPP'},
    {'Nama_Lanud': 'Lanud Leo Wattimena', 'ICAO': 'WAEE'},
    {'Nama_Lanud': 'Lanud Anang Busra', 'ICAO': 'WAXX'},
    {'Nama_Lanud': 'Lanud Raden Sadjad', 'ICAO': 'WION'},
    {'Nama_Lanud': 'Lanud Sultan Iskandar Muda', 'ICAO': 'WITT'},
    {'Nama_Lanud': 'Lanud Sri Mulyono Herlambang', 'ICAO': 'WIPR'},
    {'Nama_Lanud': 'Lanud Hang Nadim', 'ICAO': 'WIDD'},
    {'Nama_Lanud': 'Lanud Raja Haji Fisabilillah', 'ICAO': 'WIDN'}
]

# =========================================================
# FUNGSI FETCH DATA METAR
# =========================================================
def fetch_metar_final(icao):
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
            "vis_mi": metar.findtext("visibility_statute_mi", "0"),
            "alt": metar.findtext("altim_in_hg", "0"),
            "obs_time": metar.findtext("observation_time", "NIL"),
            "clouds": ", ".join(clouds) if clouds else "NIL"
        }
    except: return None

# =========================================================
# UI STREAMLIT
# =========================================================
st.set_page_config(page_title="Tactical QAM TNI AU", page_icon="✈️")

st.sidebar.title("✈️ NAVIGASI")
sel_name = st.sidebar.selectbox("Pilih Lanud", [x['Nama_Lanud'] for x in LANUD_DATA])
lanud = next(x for x in LANUD_DATA if x['Nama_Lanud'] == sel_name)

st.title(f"📊 Dashboard QAM: {sel_name}")

data = fetch_metar_final(lanud['ICAO'])

if data:
    # 1. Perbaikan Waktu (Fix NIL)
    try:
        # Menangani format ISO 2024-05-14T04:30:00Z
        clean_time = data['obs_time'].replace('Z', '+00:00')
        dt = datetime.fromisoformat(clean_time)
        date_f = dt.strftime("%d-%m-%Y")
        time_f = dt.strftime("%H.%M")
    except:
        date_f, time_f = "NIL", "NIL"

    # 2. Perbaikan Visibilitas (Fix 6002 M -> 6000 M)
    try:
        vis_val = float(data['vis_mi']) * 1609.34
        vis_m = f"{int(round(vis_val / 100) * 100)} M"
    except:
        vis_m = "NIL"

    # 3. Perbaikan Tekanan
    try:
        qnh_hpa = f"{float(data['alt']) * 33.8639:.1f}"
    except:
        qnh_hpa = "NIL"

    # Template HTML (Format Laporan Resmi)
    html_report = f"""
    <div style="background-color: white; color: black; padding: 40px; font-family: 'Courier New', Courier, monospace; border: 1px solid #000;">
        <div style="text-align: center; font-weight: bold; font-size: 16px;">MARKAS BESAR ANGKATAN UDARA<br>DINAS PENGEMBANGAN OPERASI</div>
        <div style="text-align: center; font-weight: bold; text-decoration: underline; margin-top: 20px; margin-bottom: 25px;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</div>
        
        <table style="width: 100%; border-collapse: collapse; border: 1px solid black;">
            <tr style="border: 1px solid black;"><td style="width: 50%; padding: 10px; font-weight: bold; border: 1px solid black;">METEOROLOGICAL OBS AT</td><td style="padding: 10px; border: 1px solid black;">{lanud['ICAO']} ({sel_name.upper()})</td></tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">DATE</td><td style="padding: 10px; border: 1px solid black;">{date_f}</td></tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">TIME (UTC)</td><td style="padding: 10px; border: 1px solid black;">{time_f}</td></tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">AERODROME IDENTIFICATION</td><td style="padding: 10px; border: 1px solid black;">{lanud['ICAO']}</td></tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">SURFACE WIND (DIR/SPD)</td><td style="padding: 10px; border: 1px solid black;">{data['wdir']}/{data['wspd']} KT</td></tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">HORIZONTAL VISIBILITY</td><td style="padding: 10px; border: 1px solid black;">{vis_m}</td></tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">PRESENT WEATHER</td><td style="padding: 10px; border: 1px solid black;">NIL</td></tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">CLOUDS (AMOUNT/HEIGHT)</td><td style="padding: 10px; border: 1px solid black;">{data['clouds']}</td></tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">TEMPERATURE / DEW POINT</td><td style="padding: 10px; border: 1px solid black;">{data['temp']} / {data['dew']}</td></tr>
            <tr style="border: 1px solid black;">
                <td style="padding: 10px; font-weight: bold; border: 1px solid black;">QNH</td>
                <td style="padding: 10px; border: 1px solid black;">{qnh_hpa} mbs / {data['alt']} ins</td>
            </tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">SUPPLEMENTARY INFO</td><td style="padding: 10px; border: 1px solid black;">{data['raw']}</td></tr>
            <tr style="border: 1px solid black;"><td style="padding: 10px; font-weight: bold; border: 1px solid black;">OBSERVER</td><td style="padding: 10px; border: 1px solid black;">AUTO/SYSTEM</td></tr>
        </table>
    </div>
    """

    st.markdown("### 📄 Preview Laporan")
    st.markdown(html_report, unsafe_allow_html=True)

    # Download Button
    st.download_button(
        label="⬇️ UNDUH LAPORAN QAM (.HTML)",
        data=html_report,
        file_name=f"QAM_{lanud['ICAO']}_{date_f}.html",
        mime="text/html",
        type="primary"
    )
    
    st.info("💡 **Cara mendapatkan PDF:** Klik tombol unduh di atas, buka file HTML-nya di browser, lalu tekan **Ctrl+P** dan pilih **'Save as PDF'**. Hasilnya akan persis seperti dokumen resmi.")

else:
    st.error("Data METAR tidak ditemukan. Pastikan koneksi internet aktif.")
