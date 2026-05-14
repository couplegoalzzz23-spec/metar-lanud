import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
from datetime import datetime

# Menggunakan WeasyPrint untuk konversi HTML ke PDF di Streamlit
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="LANUD TNI AU METAR",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# STYLE
# =====================================
st.markdown("""
<style>
.stApp {
    background-color: #08111f;
    color: white;
}
.metric-box {
    background-color: #132238;
    padding: 15px;
    border-radius: 12px;
}
/* Style untuk Preview Laporan QAM */
.qam-preview {
    background-color: white;
    color: black;
    padding: 30px;
    border-radius: 8px;
    font-family: "Courier New", Courier, monospace;
    margin-top: 20px;
}
.qam-header { text-align: center; font-weight: bold; font-size: 14pt; margin-bottom: 5px; }
.qam-subheader { text-align: center; font-weight: bold; font-size: 12pt; margin-bottom: 25px; }
.qam-title { text-align: center; font-weight: bold; font-size: 12pt; text-decoration: underline; margin-bottom: 20px; }
.qam-table { width: 100%; border-collapse: collapse; }
.qam-table td { border: 1px solid #000; padding: 8px 12px; vertical-align: middle; }
.qam-label { width: 50%; font-weight: bold; }
.qam-value { width: 50%; }
.qam-sub-table { width: 100%; border: none; }
.qam-sub-table td { border: none; padding: 2px 0; }
</style>
""", unsafe_allow_html=True)

# =====================================
# DATABASE LANUD
# =====================================
LANUD_DATA = [
    {"Nama":"Lanud Halim Perdanakusuma","ICAO":"WIHH","WMO":"96749"},
    {"Nama":"Lanud Roesmin Nurjadin","ICAO":"WIBB","WMO":"96109"},
    {"Nama":"Lanud Supadio","ICAO":"WIOO","WMO":"96413"},
    {"Nama":"Lanud Adisutjipto","ICAO":"WARJ","WMO":"96839"},
    {"Nama":"Lanud Abdulrachman Saleh","ICAO":"WARA","WMO":"96881"},
    {"Nama":"Lanud Iswahyudi","ICAO":"WARI","WMO":"96877"},
    {"Nama":"Lanud Juanda","ICAO":"WARR","WMO":"96935"},
    {"Nama":"Lanud Husein Sastranegara","ICAO":"WICC","WMO":"96781"},
    {"Nama":"Lanud Sultan Hasanuddin","ICAO":"WAAA","WMO":"97180"},
    {"Nama":"Lanud Sam Ratulangi","ICAO":"WAMM","WMO":"97014"},
    {"Nama":"Lanud Pattimura","ICAO":"WAPP","WMO":"97724"},
    {"Nama":"Lanud El Tari","ICAO":"WATT","WMO":"97372"},
    {"Nama":"Lanud Ngurah Rai","ICAO":"WADD","WMO":"97230"},
    {"Nama":"Lanud Silas Papare","ICAO":"WAJJ","WMO":"97690"},
    {"Nama":"Lanud Frans Kaisiepo","ICAO":"WABB","WMO":"97560"},
    {"Nama":"Lanud Dhomber","ICAO":"WALL","WMO":"96633"},
    {"Nama":"Lanud Tarakan","ICAO":"WAQQ","WMO":"96509"}
]

df = pd.DataFrame(LANUD_DATA)

# =====================================
# FETCH METAR
# =====================================
@st.cache_data(ttl=300)
def fetch_metar(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        metar = root.find(".//METAR")

        if metar is None: return None

        # Mengambil data awan
        clouds = []
        for sky in metar.findall("sky_condition"):
            cover = sky.get("sky_cover", "")
            base = sky.get("cloud_base_ft_agl", "")
            if cover and base:
                clouds.append(f"{cover} {base} FT")
            elif cover in ["CLR", "SKC"]:
                clouds.append(cover)

        return {
            "raw_text": metar.findtext("raw_text", "NIL"),
            "temp_c": metar.findtext("temp_c", "NIL"),
            "dewpoint_c": metar.findtext("dewpoint_c", "NIL"),
            "wind_dir": metar.findtext("wind_dir_degrees", "000"),
            "wind_speed": metar.findtext("wind_speed_kt", "00"),
            "visibility_mi": metar.findtext("visibility_statute_mi", "NIL"),
            "altimeter": metar.findtext("altim_in_hg", "0"),
            "flight_category": metar.findtext("flight_category", "NIL"),
            "obs_time": metar.findtext("observation_time", "NIL"),
            "clouds": ", ".join(clouds) if clouds else "NIL"
        }
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return None

# =====================================
# SIDEBAR
# =====================================
st.sidebar.title("✈️ LANUD TACTICAL")
selected_lanud = st.sidebar.selectbox("Pilih Pangkalan Udara", df["Nama"])
selected_row = df[df["Nama"] == selected_lanud].iloc[0]
icao = selected_row["ICAO"]
wmo = selected_row["WMO"]

st.sidebar.info(f"**ICAO:** {icao}\n\n**WMO:** {wmo}")

# =====================================
# MAIN DASHBOARD
# =====================================
st.title("✈️ METAR & QAM REPORT DASHBOARD")
metar = fetch_metar(icao)

if metar:
    # --- Perhitungan Data QAM ---
    # Konversi visibilitas ke Meter
    try:
        vis_m = int(float(metar['visibility_mi']) * 1609.34)
        vis_str = f"{vis_m} M"
    except:
        vis_str = "NIL"
    
    # Konversi Altimeter ke Milibar (QNH)
    try:
        qnh_mbs = float(metar['altimeter']) * 33.8639
        qnh_mbs_str = f"{qnh_mbs:.1f}"
    except:
        qnh_mbs_str = "NIL"

    # Format Waktu
    obs_time = metar["obs_time"]
    if obs_time != "NIL":
        try:
            dt_obj = datetime.strptime(obs_time, "%Y-%m-%dT%H:%M:%SZ")
            date_str = dt_obj.strftime("%d-%m-%Y")
            time_str = dt_obj.strftime("%H.%M")
        except:
            date_str, time_str = "NIL", "NIL"
    else:
        date_str, time_str = "NIL", "NIL"

    # Format Wind
    try:
        wind_str = f"{int(metar['wind_dir']):03d}/{int(metar['wind_speed']):02d} KT"
    except:
        wind_str = f"{metar['wind_dir']}/{metar['wind_speed']} KT"

    # --- HTML Generator ---
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        @page {{ size: A4; margin: 20mm; background-color: #ffffff; }}
        body {{ font-family: "Courier New", Courier, monospace; font-size: 11pt; color: #000; margin: 0; padding: 0; }}
        .header {{ text-align: center; font-weight: bold; font-size: 14pt; margin-bottom: 5px; }}
        .subheader {{ text-align: center; font-weight: bold; font-size: 12pt; margin-bottom: 25px; }}
        .title {{ text-align: center; font-weight: bold; font-size: 12pt; text-decoration: underline; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td {{ border: 1px solid #000; padding: 8px 12px; vertical-align: middle; }}
        .col-label {{ width: 50%; font-weight: bold; }}
        .col-value {{ width: 50%; }}
        .sub-table {{ width: 100%; border: none; }}
        .sub-table td {{ border: none; padding: 2px 0; }}
    </style>
    </head>
    <body>
        <div class="header">MARKAS BESAR ANGKATAN UDARA</div>
        <div class="subheader">DINAS PENGEMBANGAN OPERASI</div>
        <div class="title">METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING</div>
        <table>
            <tr><td class="col-label">METEOROLOGICAL OBS AT</td><td class="col-value">{icao} ({selected_lanud.upper()})</td></tr>
            <tr><td class="col-label">DATE</td><td class="col-value">{date_str}</td></tr>
            <tr><td class="col-label">TIME</td><td class="col-value">{time_str} (UTC)</td></tr>
            <tr><td class="col-label">AERODROME IDENTIFICATION</td><td class="col-value">{icao}</td></tr>
            <tr><td class="col-label">SURFACE WIND DIRECTION, SPEED<br>AND SIGNIFICANT VARIATION</td><td class="col-value">{wind_str}</td></tr>
            <tr><td class="col-label">HORIZONTAL VISIBILITY</td><td class="col-value">{vis_str}</td></tr>
            <tr><td class="col-label">RUNWAY VISUAL RANGE</td><td class="col-value">NIL</td></tr>
            <tr><td class="col-label">PRESENT WEATHER</td><td class="col-value">NIL</td></tr>
            <tr><td class="col-label">AMOUNT AND HEIGHT OF BASE<br>OF LOW CLOUD</td><td class="col-value">{metar['clouds']}</td></tr>
            <tr><td class="col-label">AIR TEMPERATURE AND<br>DEW POINT TEMPERATURE</td><td class="col-value">{metar['temp_c']}/{metar['dewpoint_c']}</td></tr>
            <tr>
                <td class="col-label">QNH</td>
                <td class="col-value">
                    <table class="sub-table">
                        <tr><td>{qnh_mbs_str}</td><td>mbs</td></tr>
                        <tr><td>{metar['altimeter']}</td><td>ins*</td></tr>
                        <tr><td>......</td><td>mm Hg*</td></tr>
                    </table>
                </td>
            </tr>
            <tr>
                <td class="col-label">QFE*</td>
                <td class="col-value">
                    <table class="sub-table">
                        <tr><td>......</td><td>mbs</td></tr>
                        <tr><td>......</td><td>ins*</td></tr>
                        <tr><td>......</td><td>mm Hg*</td></tr>
                    </table>
                </td>
            </tr>
            <tr><td class="col-label">SUPPLEMENTARY<br>INFORMATION</td><td class="col-value">{metar['raw_text']}</td></tr>
            <tr><td class="col-label">TIME OF ISSUE (UTC)<br>OBSERVER</td><td class="col-value">{time_str}<br>AUTO/SYSTEM</td></tr>
        </table>
        <div style="margin-top:20px; font-size:9pt;">*ON REQUEST</div>
    </body>
    </html>
    """

    st.success(f"Intelijen Cuaca {selected_lanud} Terverifikasi")
    
    # --- Live Preview QAM Form ---
    st.markdown("### 📄 Preview Laporan QAM")
    st.markdown(f'<div class="qam-preview">{html_content}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # --- Tombol Export PDF ---
    if WEASYPRINT_AVAILABLE:
        pdf_bytes = HTML(string=html_content).write_pdf()
        st.download_button(
            label="⬇️ Unduh Dokumen QAM (PDF)",
            data=pdf_bytes,
            file_name=f"QAM_{icao}_{date_str}_{time_str.replace('.', '')}.pdf",
            mime="application/pdf",
            type="primary"
        )
    else:
        st.download_button(
            label="⬇️ Unduh Dokumen QAM (HTML)",
            data=html_content,
            file_name=f"QAM_{icao}_{date_str}.html",
            mime="text/html",
            type="primary"
        )
        st.info("💡 Instal `weasyprint` (pip install weasyprint) di server Anda agar format PDF dapat langsung diproses melalui tombol di atas. Untuk saat ini, simpan file HTML lalu gunakan fitur 'Print to PDF' di browser.")

else:
    st.warning("Data METAR tidak tersedia atau koneksi terputus.")
