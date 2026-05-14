import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator - TNI AU", page_icon="✈️", layout="centered")

def get_metar(station_id):
    """Mengambil data METAR mentah dari AviationWeather API"""
    # Menggunakan API terbaru dari aviationweather.gov
    url = f"https://aviationweather.gov/api/data/metar?ids={station_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and response.text:
            return response.text.strip()
        return None
    except Exception as e:
        return None

def parse_metar(raw_metar):
    """Parsing METAR secara teliti untuk format QAM"""
    data = {
        "wind": "NIL",
        "vis": "NIL",
        "weather": "NIL",
        "clouds": "NIL",
        "temp_dew": "NIL",
        "qnh_hpa": "1013",
        "time_utc": datetime.utcnow().strftime("%H.%M")
    }
    
    # Wind: Contoh 04005KT
    wind_match = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw_metar)
    if wind_match:
        data["wind"] = f"{wind_match.group(1)}/{wind_match.group(2)} KT"

    # Visibility: Contoh 5000 atau 9999
    vis_match = re.search(r'\s(\d{4})\s', raw_metar)
    if vis_match:
        data["vis"] = f"{vis_match.group(1)} M"
    elif "CAVOK" in raw_metar:
        data["vis"] = "10 KM OR MORE"

    # Weather: Contoh TSRA, RA, HZ
    wx_match = re.search(r'\s([-+]?[A-Z]{2,4})\s', raw_metar)
    if wx_match:
        data["weather"] = wx_match.group(1)

    # Clouds: Contoh FEW010
    cloud_match = re.search(r'([A-Z]{3})(\d{3})', raw_metar)
    if cloud_match:
        height = int(cloud_match.group(2)) * 100
        data["clouds"] = f"{cloud_match.group(1)} {height} FT"
    elif "CAVOK" in raw_metar:
        data["clouds"] = "NIL"

    # Temp/Dew: Contoh 26/20
    td_match = re.search(r'(\d{2})/(\d{2})', raw_metar)
    if td_match:
        data["temp_dew"] = f"{td_match.group(1)}/{td_match.group(2)}"

    # QNH: Contoh Q1012
    qnh_match = re.search(r'Q(\d{4})', raw_metar)
    if qnh_match:
        data["qnh_hpa"] = qnh_match.group(1)

    return data

class QAM_PDF(FPDF):
    def header(self):
        # Header sesuai source [1] dan [2]
        self.set_font("Arial", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(5)
        self.set_font("Arial", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(5)

def create_pdf(data, station_id):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=9)
    
    qnh = float(data['qnh_hpa'])
    qfe = qnh - 4 # Estimasi perbedaan elevasi standar (bisa disesuaikan)

    # Konversi Satuan sesuai source [24-29]
    def get_values(val):
        ins = val * 0.02953
        mmhg = val * 0.75006
        return f"{int(val)} mbs / {ins:.2f} ins / {mmhg:.1f} mm Hg"

    # Tabel Data sesuai urutan source [3] sampai [16]
    table_content = [
        ("METEOROLOGICAL OBS AT", station_id),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", data['time_utc']),
        ("AERODROME IDENTIFICATION", station_id),
        ("SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION", data['wind']),
        ("HORIZONTAL VISIBILITY", data['vis']),
        ("RUNWAY VISUAL RANGE", "NIL"),
        ("PRESENT WEATHER", data['weather']),
        ("AMOUNT AND HEIGHT OF BASE OF LOW CLOUD", data['clouds']),
        ("AIR TEMPERATURE AND DEW POINT TEMPERATURE", data['temp_dew']),
        ("QNH", get_values(qnh)),
        ("QFE*", get_values(qfe)),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", data['time_utc']),
    ]

    for label, value in table_content:
        # Menentukan tinggi cell berdasarkan panjang teks (wrap text)
        h = 10 if len(label) < 40 else 14
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(85, h/2 if h>10 else 10, label, border=1)
        pdf.set_xy(x + 85, y)
        pdf.cell(105, h, str(value), border=1, ln=True)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", ln=True, align='R')
    return pdf.output(dest='S')

# --- ANTARMUKA STREAMLIT ---
st.title("✈️ Mil-Aero QAM Generator")
st.markdown("Automated Meteorological Report based on **MARKAS BESAR ANGKATAN UDARA** Format.")

icao = st.text_input("Masukkan ICAO Code (Contoh: WIBB, WIII):", value="WIBB").upper()

if st.button("Generate & Download Report"):
    if not icao:
        st.warning("Masukkan kode ICAO terlebih dahulu.")
    else:
        with st.spinner(f"Menghubungi server untuk {icao}..."):
            raw_metar = get_metar(icao)
            
            if raw_metar:
                st.success("Data METAR berhasil diambil!")
                st.code(raw_metar, language="txt")
                
                parsed_data = parse_metar(raw_metar)
                pdf_output = create_pdf(parsed_data, icao)
                
                st.download_button(
                    label="📥 Unduh PDF QAM",
                    data=pdf_output,
                    file_name=f"QAM_{icao}_{datetime.now().strftime('%H%M')}Z.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Gagal mengambil data. Periksa koneksi internet atau validitas Kode ICAO.")

st.divider()
st.caption("Catatan: Data QFE dihitung berdasarkan estimasi QNH standar.")
