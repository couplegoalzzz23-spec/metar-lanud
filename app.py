import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator - WIBB", page_icon="✈️")

def get_metar(station_id):
    """Mengambil data METAR mentah dari AviationWeather API"""
    url = f"https://aviationweather.gov/api/data/metar?ids={station_id}&format=raw"
    try:
        response = requests.get(url)
        if response.status_status == 200 and response.text:
            return response.text.strip()
        return None
    except:
        return None

def parse_metar(raw_metar):
    """Parsing sederhana untuk mengekstrak data METAR ke format QAM"""
    data = {
        "wind": "NIL",
        "vis": "NIL",
        "weather": "NIL",
        "clouds": "NIL",
        "temp_dew": "NIL",
        "qnh": "NIL",
        "qfe": "NIL",
        "time_utc": datetime.utcnow().strftime("%H.%M")
    }
    
    # Wind: 04005KT -> 040/05 KT
    wind_match = re.search(r'(\d{3})(\d{2})G?(\d{2})?KT', raw_metar)
    if wind_match:
        data["wind"] = f"{wind_match.group(1)}/{wind_match.group(2)} KT"

    # Visibility
    vis_match = re.search(r'\s(\d{4})\s', raw_metar)
    if vis_match:
        data["vis"] = vis_match.group(1) + " M"

    # Clouds: FEW010 -> FEW 1000 FT
    cloud_match = re.search(r'([A-Z]{3})(\d{3})', raw_metar)
    if cloud_match:
        height = int(cloud_match.group(2)) * 100
        data["clouds"] = f"{cloud_match.group(1)} {height} FT"

    # Temp/Dew: 26/20
    td_match = re.search(r'(\d{2})/(\d{2})', raw_metar)
    if td_match:
        data["temp_dew"] = f"{td_match.group(1)}/{td_match.group(2)}"

    # QNH: Q1012 -> 1012 mbs
    qnh_match = re.search(r'Q(\d{4})', raw_metar)
    if qnh_match:
        qnh_val = int(qnh_match.group(1))
        data["qnh"] = f"{qnh_val}"
        # Estimasi QFE (WIBB Elevasi ~100ft, QFE = QNH - 3.7 hPa)
        data["qfe"] = f"{qnh_val - 4}"

    return data

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("Arial", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(5)
        self.set_font("Arial", 'B', 11)
        self.cell(0, 10, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(2)

def create_pdf(data, station_id):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    
    # Table Structure
    table_data = [
        ("METEOROLOGICAL OBS AT", station_id),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", data['time_utc']),
        ("AERODROME IDENTIFICATION", station_id),
        ("SURFACE WIND DIRECTION, SPEED\nAND SIGNIFICANT VARIATION", data['wind']),
        ("HORIZONTAL VISIBILITY", data['vis']),
        ("RUNWAY VISUAL RANGE", "NIL"),
        ("PRESENT WEATHER", data['weather']),
        ("AMOUNT AND HEIGHT OF BASE\nOF LOW CLOUD", data['clouds']),
        ("AIR TEMPERATURE AND\nDEW POINT TEMPERATURE", data['temp_dew']),
        ("QNH", f"{data['qnh']} mbs / {(float(data['qnh'])*0.02953):.2f} ins"),
        ("QFE*", f"{data['qfe']} mbs / {(float(data['qfe'])*0.02953):.2f} ins"),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", data['time_utc']),
    ]

    for label, value in table_data:
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.multi_cell(80, 10, label, border=1)
        pdf.set_xy(x + 80, y)
        pdf.multi_cell(110, 10 if "\n" not in label else 5, value, border=1, align='L')
    
    pdf.ln(5)
    pdf.cell(0, 10, "OBSERVER: .........................", ln=True, align='R')
    
    return pdf.output(dest='S')

# --- UI STREAMLIT ---
st.title("✈️ QAM Form Generator")
st.write("Format Laporan Meteorologi Take-off/Landing (WIBB)")

icao = st.text_input("Masukkan ICAO Code:", value="WIBB").upper()

if st.button("Ambil Data & Preview"):
    with st.spinner("Mengambil data METAR..."):
        raw = get_metar(icao)
        if raw:
            st.info(f"**METAR Mentah:** {raw}")
            parsed = parse_metar(raw)
            
            # Tampilkan Ringkasan
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Wind", parsed['wind'])
                st.metric("QNH", parsed['qnh'])
            with col2:
                st.metric("Clouds", parsed['clouds'])
                st.metric("Temp/Dew", parsed['temp_dew'])
            
            # Generate PDF
            pdf_bytes = create_pdf(parsed, icao)
            
            st.download_button(
                label="📥 Unduh PDF QAM",
                data=pdf_bytes,
                file_name=f"QAM_{icao}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
        else:
            st.error("Gagal mengambil data. Pastikan kode ICAO benar.")

st.divider()
st.caption("Aplikasi ini dibuat untuk format otomatisasi dokumen meteorologi penerbangan.")
