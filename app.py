import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# =========================================================
# DATABASE LANUD (EMBEDDED)
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
# FUNGSI PARSING DATA
# =========================================================
def get_clean_metar(icao):
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
            if base: clouds.append(f"{cover} {base}FT")
            else: clouds.append(cover)
            
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
# TAMPILAN DASHBOARD
# =========================================================
st.set_page_config(page_title="Tactical METAR TNI AU", layout="wide")

st.sidebar.header("✈️ KONFIGURASI")
selected_lanud_name = st.sidebar.selectbox("Pilih Pangkalan", [x['Nama_Lanud'] for x in LANUD_DATA])
lanud_info = next(item for item in LANUD_DATA if item["Nama_Lanud"] == selected_lanud_name)

st.title(f"📊 Laporan Meteorologi: {selected_lanud_name}")

data = get_clean_metar(lanud_info['ICAO'])

if data:
    # --- LOGIKA PERBAIKAN DATA ---
    # 1. Perbaikan Waktu (Fix NIL)
    try:
        dt_obj = datetime.fromisoformat(data['obs_time'].replace('Z', '+00:00'))
        date_str = dt_obj.strftime("%d-%m-%Y")
        time_str = dt_obj.strftime("%H.%M")
    except:
        date_str, time_str = "NIL", "NIL"

    # 2. Perbaikan Visibilitas (Fix 6002 M -> 6000 M)
    try:
        vis_meters = float(data['vis_mi']) * 1609.34
        vis_rounded = int(round(vis_meters / 100) * 100)
        vis_display = f"{vis_rounded} M"
    except:
        vis_display = "NIL"

    # 3. Perbaikan Tekanan
    qnh_hpa = f"{float(data['alt']) * 33.8639:.1f}" if data['alt'] != "0" else "NIL"

    # --- GENERASI HTML REPORT ---
    report_html = f"""
    <div id="qam-report" style="background-color: white; color: black; padding: 30px; font-family: 'Courier New', Courier, monospace; border: 2px solid black; max-width: 800px; margin: auto;">
        <div style="text-align: center; font-weight: bold; font-size: 18px;">MARKAS BESAR ANGKATAN UDARA</div>
        <div style="text-align: center; font-weight: bold; font-size: 16px;">DINAS PENGEMBANGAN OPERASI</div>
        <div style="text-align: center; font-weight: bold; text-decoration: underline; margin: 20px 0;">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</div>
        
        <table style="width: 100%; border-collapse: collapse; border: 1px solid black;">
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold; width: 40%;">METEOROLOGICAL OBS AT</td><td style="border: 1px solid black; padding: 8px;">{lanud_info['ICAO']} ({selected_lanud_name.upper()})</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">DATE</td><td style="border: 1px solid black; padding: 8px;">{date_str}</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">TIME (UTC)</td><td style="border: 1px solid black; padding: 8px;">{time_str}</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">AERODROME IDENTIFICATION</td><td style="border: 1px solid black; padding: 8px;">{lanud_info['ICAO']}</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">SURFACE WIND (DIR/SPD)</td><td style="border: 1px solid black; padding: 8px;">{data['wdir']}/{data['wspd']} KT</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">HORIZONTAL VISIBILITY</td><td style="border: 1px solid black; padding: 8px;">{vis_display}</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">PRESENT WEATHER</td><td style="border: 1px solid black; padding: 8px;">NIL</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">CLOUDS (AMOUNT/HEIGHT)</td><td style="border: 1px solid black; padding: 8px;">{data['clouds']}</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">TEMPERATURE / DEW POINT</td><td style="border: 1px solid black; padding: 8px;">{data['temp']} / {data['dew']}</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">QNH</td><td style="border: 1px solid black; padding: 8px;">{qnh_hpa} mbs / {data['alt']} ins</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">SUPPLEMENTARY INFO</td><td style="border: 1px solid black; padding: 8px; font-size: 12px;">{data['raw']}</td></tr>
            <tr><td style="border: 1px solid black; padding: 8px; font-weight: bold;">OBSERVER</td><td style="border: 1px solid black; padding: 8px;">AUTO/SYSTEM</td></tr>
        </table>
    </div>
    """

    # Tampilkan di Streamlit
    st.markdown(report_html, unsafe_allow_html=True)

    st.divider()
    
    # Tombol Download
    st.download_button(
        label="⬇️ DOWNLOAD LAPORAN (HTML)",
        data=report_html,
        file_name=f"QAM_{lanud_info['ICAO']}_{date_str}.html",
        mime="text/html",
        type="primary"
    )
    
    st.info("💡 **Tips PDF:** Setelah klik download, buka file HTML tersebut di browser Anda, lalu tekan **Ctrl + P** (Cetak) dan pilih **'Simpan sebagai PDF'**.")

else:
    st.error("Gagal mengambil data dari stasiun. Pastikan ICAO benar dan pemancar aktif.")
