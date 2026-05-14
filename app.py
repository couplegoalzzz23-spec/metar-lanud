import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import io
import subprocess
import sys

# Auto-install fpdf2 jika belum ada (agar tidak perlu requirements.txt manual)
try:
    from fpdf import FPDF
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2"])
    from fpdf import FPDF

# =========================================================
# DATABASE LANUD (DATA EMBEDDED)
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
# FUNGSI METAR & PARSING
# =========================================================
def fetch_metar_tactical(icao):
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
            "vis_mi": metar.findtext("visibility_statute_mi", "NIL"),
            "alt": metar.findtext("altim_in_hg", "0"),
            "obs_time": metar.findtext("observation_time", "NIL"),
            "clouds": ", ".join(clouds) if clouds else "NIL"
        }
    except: return None

# =========================================================
# GENERATOR PDF (FORMAT QAM RESMI)
# =========================================================
class TacticalPDF(FPDF):
    def create_qam(self, lanud_name, icao, data):
        self.add_page()
        self.set_font("Courier", "B", 14)
        self.cell(0, 8, "MARKAS BESAR ANGKATAN UDARA", ln=True, align="C")
        self.cell(0, 8, "DINAS PENGEMBANGAN OPERASI", ln=True, align="C")
        self.ln(5)
        self.set_font("Courier", "BU", 12)
        self.cell(0, 8, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", ln=True, align="C")
        self.ln(10)
        
        # Perbaikan Waktu (Handling NIL)
        try:
            # Menggunakan fromisoformat untuk akurasi tinggi
            dt = datetime.fromisoformat(data['obs_time'].replace("Z", "+00:00"))
            d_str = dt.strftime("%d-%m-%Y")
            t_str = dt.strftime("%H.%M")
        except:
            d_str, t_str = "NIL", "NIL"

        # Perbaikan Visibilitas (Pembulatan ke ratusan terdekat)
        try:
            vis_val = float(data['vis_mi']) * 1609.34
            vis_m = f"{int(round(vis_val / 100.0) * 100)} M"
        except:
            vis_m = "NIL"

        # Perbaikan Tekanan
        qnh_hpa = f"{float(data['alt']) * 33.8639:.1f}" if data['alt'] != "0" else "NIL"

        # Isi Tabel
        self.set_font("Courier", "B", 10)
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
            ("QNH", f"{qnh_hpa} MBS / {data['alt']} INS"),
            ("SUPPLEMENTARY INFO", data['raw']),
            ("OBSERVER", "AUTO/SYSTEM")
        ]

        for label, val in rows:
            self.set_font("Courier", "B", 10)
            self.cell(70, 10, label, border=1)
            self.set_font("Courier", "", 10)
            self.multi_cell(0, 10, str(val), border=1)

# =========================================================
# TAMPILAN DASHBOARD
# =========================================================
st.set_page_config(page_title="Tactical METAR TNI AU", page_icon="✈️")

st.sidebar.title("✈️ PILIH PANGKALAN")
name_list = [x['Nama_Lanud'] for x in LANUD_DATA]
sel_lanud = st.sidebar.selectbox("Nama Lanud", name_list)
lanud_info = next(x for x in LANUD_DATA if x['Nama_Lanud'] == sel_lanud)

st.title(f"📊 Tactical Dashboard: {sel_lanud}")

if st.button("🔄 Refresh Data METAR"):
    st.rerun()

m_data = fetch_metar_tactical(lanud_info['ICAO'])

if m_data:
    # Widget Ringkasan
    c1, c2, c3 = st.columns(3)
    c1.metric("Wind", f"{m_data['wdir']}°/{m_data['wspd']} KT")
    c2.metric("Temp/Dew", f"{m_data['temp']}°/{m_data['dew']}°")
    c3.metric("Altimeter", m_data['alt'])

    # Tombol Unduh PDF
    pdf = TacticalPDF()
    pdf.create_qam(sel_lanud, lanud_info['ICAO'], m_data)
    
    # Output ke Bytes
    pdf_bytes = pdf.output()
    
    st.download_button(
        label="⬇️ UNDUH FORM QAM (PDF)",
        data=bytes(pdf_bytes),
        file_name=f"QAM_{lanud_info['ICAO']}.pdf",
        mime="application/pdf",
        type="primary"
    )
    
    st.text_area("Raw METAR Info", m_data['raw'], height=100)
else:
    st.error("⚠️ Data tidak tersedia. Periksa koneksi internet atau status stasiun.")
