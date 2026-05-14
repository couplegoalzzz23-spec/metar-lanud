import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from fpdf import FPDF
import pandas as pd

# =========================================================
# DATABASE LANUD (EMBEDDED - TANPA CSV)
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
# FUNGSI PENGAMBILAN DATA
# =========================================================
def get_metar_data(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"
    try:
        res = requests.get(url, timeout=10)
        root = ET.fromstring(res.text)
        metar = root.find(".//METAR")
        if metar is None: return None
        
        # Ekstraksi Awan
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
            "vis_mi": metar.findtext("visibility_statute_mi", "NIL"),
            "alt": metar.findtext("altim_in_hg", "0"),
            "obs_time": metar.findtext("observation_time", "NIL"),
            "clouds": ", ".join(clouds) if clouds else "NIL"
        }
    except: return None

# =========================================================
# GENERATOR PDF
# =========================================================
class QAM_PDF(FPDF):
    def generate_report(self, lanud_name, icao, data):
        self.add_page()
        self.set_font("Courier", "B", 14)
        self.cell(0, 7, "MARKAS BESAR ANGKATAN UDARA", ln=True, align="C")
        self.cell(0, 7, "DINAS PENGEMBANGAN OPERASI", ln=True, align="C")
        self.ln(5)
        self.set_font("Courier", "BU", 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", ln=True, align="C")
        self.ln(10)
        
        # Parsing Waktu
        try:
            dt = datetime.fromisoformat(data['obs_time'].replace("Z", "+00:00"))
            d_str, t_str = dt.strftime("%d-%m-%Y"), dt.strftime("%H.%M")
        except:
            d_str, t_str = "NIL", "NIL"

        # Kalkulasi Satuan
        vis_val = float(data['vis_mi']) if data['vis_mi'] != "NIL" else 0
        vis_m = f"{round(vis_val * 1609.34 / 100) * 100} M" if vis_val > 0 else "NIL"
        qnh_hpa = f"{float(data['alt']) * 33.8639:.1f}" if data['alt'] != "0" else "NIL"

        # Konten Tabel
        self.set_font("Courier", "", 10)
        table_data = [
            ("METEOROLOGICAL OBS AT", f"{icao} ({lanud_name.upper()})"),
            ("DATE", d_str),
            ("TIME (UTC)", t_str),
            ("AERODROME IDENTIFICATION", icao),
            ("SURFACE WIND (DIR/SPD)", f"{data['wdir']}/{data['wspd']} KT"),
            ("HORIZONTAL VISIBILITY", vis_m),
            ("PRESENT WEATHER", "NIL"),
            ("CLOUDS (AMOUNT/HEIGHT)", data['clouds']),
            ("TEMPERATURE / DEW POINT", f"{data['temp']} / {data['dew']}"),
            ("QNH", f"{qnh_hpa} MBS / {data['alt']} INS"),
            ("SUPPLEMENTARY INFO", data['raw']),
            ("OBSERVER", "AUTO/SYSTEM")
        ]

        for label, value in table_data:
            self.set_font("Courier", "B", 10)
            self.cell(70, 10, label, border=1)
            self.set_font("Courier", "", 10)
            self.multi_cell(0, 10, str(value), border=1)

# =========================================================
# STREAMLIT UI
# =========================================================
st.set_page_config(page_title="Tactical METAR TNI AU", page_icon="✈️")

st.sidebar.title("✈️ NAVIGASI")
sel_name = st.sidebar.selectbox("Pilih Lanud", [x['Nama_Lanud'] for x in LANUD_DATA])
lanud = next(x for x in LANUD_DATA if x['Nama_Lanud'] == sel_name)

st.title(f"📊 QAM Dashboard: {sel_name}")

with st.spinner("Mengambil data cuaca real-time..."):
    m_data = get_metar_data(lanud['ICAO'])

if m_data:
    st.success("Data Terverifikasi.")
    
    # Preview Singkat
    col1, col2, col3 = st.columns(3)
    col1.metric("Wind", f"{m_data['wdir']}°/{m_data['wspd']} KT")
    col2.metric("Temp", f"{m_data['temp']}°C")
    col3.metric("QNH", m_data['alt'])

    # Tombol Download PDF
    pdf = QAM_PDF()
    pdf.generate_report(sel_name, lanud['ICAO'], m_data)
    pdf_output = pdf.output()
    
    st.download_button(
        label="⬇️ UNDUH LAPORAN QAM (PDF)",
        data=bytes(pdf_output),
        file_name=f"QAM_{lanud['ICAO']}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf",
        type="primary"
    )
    
    with st.expander("Lihat Raw Data"):
        st.write(m_data)
else:
    st.error("Gagal mendapatkan data METAR. Pastikan Lanud memiliki pemancar aktif.")
