import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from fpdf import FPDF
import io

# =========================================================
# DATABASE LANUD (EMBEDDED)
# =========================================================
LANUD_DATA = [
    {'Nama_Lanud': 'Lanud Halim Perdanakusuma', 'ICAO': 'WIHH', 'WMO': '96749'},
    {'Nama_Lanud': 'Lanud Atang Sendjaja', 'ICAO': 'WIAJ', 'WMO': 'NIL'},
    {'Nama_Lanud': 'Lanud Soewondo', 'ICAO': 'WIMK', 'WMO': '96035'},
    {'Nama_Lanud': 'Lanud Roesmin Nurjadin', 'ICAO': 'WIBB', 'WMO': '96109'},
    {'Nama_Lanud': 'Lanud Supadio', 'ICAO': 'WIOO', 'WMO': '96413'},
    {'Nama_Lanud': 'Lanud Iskandar', 'ICAO': 'WAOI', 'WMO': '96655'},
    {'Nama_Lanud': 'Lanud Adisutjipto', 'ICAO': 'WARJ', 'WMO': '96839'},
    {'Nama_Lanud': 'Lanud Abdulrachman Saleh', 'ICAO': 'WARA', 'WMO': '96881'},
    {'Nama_Lanud': 'Lanud Iswahyudi', 'ICAO': 'WARI', 'WMO': '96877'},
    {'Nama_Lanud': 'Lanud Juanda', 'ICAO': 'WARR', 'WMO': '96935'},
    {'Nama_Lanud': 'Lanud Husein Sastranegara', 'ICAO': 'WICC', 'WMO': '96781'},
    {'Nama_Lanud': 'Lanud Sultan Hasanuddin', 'ICAO': 'WAAA', 'WMO': '97180'},
    {'Nama_Lanud': 'Lanud Sam Ratulangi', 'ICAO': 'WAMM', 'WMO': '97014'},
    {'Nama_Lanud': 'Lanud El Tari', 'ICAO': 'WATT', 'WMO': '97268'},
    {'Nama_Lanud': 'Lanud Silas Papare', 'ICAO': 'WAJJ', 'WMO': '98233'},
    {'Nama_Lanud': 'Lanud Manuhua', 'ICAO': 'WABB', 'WMO': '97502'},
    {'Nama_Lanud': 'Lanud Pattimura', 'ICAO': 'WAPP', 'WMO': '97724'},
    {'Nama_Lanud': 'Lanud Leo Wattimena', 'ICAO': 'WAEE', 'WMO': '97600'},
    {'Nama_Lanud': 'Lanud Anang Busra', 'ICAO': 'WAXX', 'WMO': '96509'},
    {'Nama_Lanud': 'Lanud Raden Sadjad', 'ICAO': 'WION', 'WMO': '96011'},
    {'Nama_Lanud': 'Lanud Sultan Iskandar Muda', 'ICAO': 'WITT', 'WMO': '96011'},
    {'Nama_Lanud': 'Lanud Sri Mulyono Herlambang', 'ICAO': 'WIPR', 'WMO': '96223'},
    {'Nama_Lanud': 'Lanud Hang Nadim', 'ICAO': 'WIDD', 'WMO': '96109'},
    {'Nama_Lanud': 'Lanud Raja Haji Fisabilillah', 'ICAO': 'WIDN', 'WMO': '96109'}
]

# =========================================================
# FUNGSI FETCH & PDF
# =========================================================
def fetch_metar(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"
    try:
        res = requests.get(url, timeout=10)
        root = ET.fromstring(res.text)
        metar = root.find(".//METAR")
        if metar is None: return None
        
        # Parsing data awan
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
            "vis_mi": metar.findtext("visibility_statute_mi", "NIL"),
            "alt": metar.findtext("altim_in_hg", "0"),
            "time_raw": metar.findtext("observation_time", "NIL"),
            "clouds": ", ".join(clouds) if clouds else "NIL"
        }
    except: return None

def create_pdf(lanud_name, icao, data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", "B", 14)
    
    # Header
    pdf.cell(0, 7, "MARKAS BESAR ANGKATAN UDARA", ln=True, align="C")
    pdf.cell(0, 7, "DINAS PENGEMBANGAN OPERASI", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Courier", "BU", 12)
    pdf.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", ln=True, align="C")
    pdf.ln(10)
    
    # Data Processing
    try:
        dt = datetime.strptime(data['time_raw'], "%Y-%m-%dT%H:%M:%SZ")
        d_str, t_str = dt.strftime("%d-%m-%Y"), dt.strftime("%H.%M")
    except:
        d_str, t_str = "NIL", "NIL"
        
    vis_m = f"{round(float(data['vis_mi']) * 1609.34 / 100) * 100} M" if data['vis_mi'] != "NIL" else "NIL"
    qnh_hpa = f"{float(data['alt']) * 33.8639:.1f}" if data['alt'] != "0" else "NIL"

    # Table
    pdf.set_font("Courier", "B", 10)
    rows = [
        ("METEOROLOGICAL OBS AT", f"{icao} ({lanud_name.upper()})"),
        ("DATE", d_str),
        ("TIME (UTC)", t_str),
        ("AERODROME IDENTIFICATION", icao),
        ("SURFACE WIND (DIR/SPD)", f"{data['wdir']}/{data['wspd']} KT"),
        ("HORIZONTAL VISIBILITY", vis_m),
        ("PRESENT WEATHER", "NIL"),
        ("CLOUDS (AMOUNT/HEIGHT)", data['clouds']),
        ("TEMPERATURE / DEW POINT", f"{data['temp']} / {data['dew']}"),
        ("QNH (HPA / INS)", f"{qnh_hpa} MBS / {data['alt']} INS"),
        ("SUPPLEMENTARY INFO", data['raw']),
        ("OBSERVER", "AUTO/SYSTEM")
    ]
    
    for label, val in rows:
        pdf.cell(70, 10, label, border=1)
        pdf.multi_cell(0, 10, val, border=1)
        
    return pdf.output()

# =========================================================
# STREAMLIT UI
# =========================================================
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️")

st.sidebar.title("✈️ NAVIGASI")
sel_name = st.sidebar.selectbox("Pilih Lanud", [x['Nama_Lanud'] for x in LANUD_DATA])
lanud = next(x for x in LANUD_DATA if x['Nama_Lanud'] == sel_name)

st.title(f"📄 QAM Report: {sel_name}")

metar_data = fetch_metar(lanud['ICAO'])

if metar_data:
    # Preview di Web
    st.info(f"**Raw METAR:** {metar_data['raw']}")
    
    # Tombol Generate PDF
    pdf_bytes = create_pdf(sel_name, lanud['ICAO'], metar_data)
    
    st.download_button(
        label="⬇️ UNDUH LAPORAN QAM (PDF)",
        data=pdf_bytes,
        file_name=f"QAM_{lanud['ICAO']}_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        type="primary"
    )
    
    st.success("Laporan siap diunduh dalam format PDF resmi.")
else:
    st.error("Gagal mengambil data METAR. Pastikan koneksi internet aktif.")
