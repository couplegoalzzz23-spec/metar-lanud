import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator - TNI AU", page_icon="✈️")

def get_metar(station_id):
    """Mengambil data METAR mentah"""
    url = f"https://aviationweather.gov/api/data/metar?ids={station_id}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and response.text:
            return response.text.strip()
        return None
    except:
        return None

def parse_metar(raw_metar):
    """Parsing METAR dengan fallback nilai aman"""
    data = {
        "wind": "NIL",
        "vis": "NIL",
        "weather": "NIL",
        "clouds": "NIL",
        "temp_dew": "NIL",
        "qnh_hpa": "1013", # Default standard pressure
        "time_utc": datetime.utcnow().strftime("%H.%M")
    }
    
    # Wind
    wind_match = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw_metar)
    if wind_match:
        data["wind"] = f"{wind_match.group(1)}/{wind_match.group(2)} KT"

    # Visibility
    if "CAVOK" in raw_metar:
        data["vis"] = "10 KM OR MORE"
    else:
        vis_match = re.search(r'\s(\d{4})\s', raw_metar)
        if vis_match:
            data["vis"] = f"{vis_match.group(1)} M"

    # Present Weather
    wx_match = re.search(r'\s([-+]?[A-Z]{2,4})\s', raw_metar)
    if wx_match:
        data["weather"] = wx_match.group(1)

    # Clouds
    cloud_match = re.search(r'([A-Z]{3})(\d{3})', raw_metar)
    if cloud_match:
        height = int(cloud_match.group(2)) * 100
        data["clouds"] = f"{cloud_match.group(1)} {height} FT"

    # Temp/Dew
    td_match = re.search(r'(\d{2})/(\d{2})', raw_metar)
    if td_match:
        data["temp_dew"] = f"{td_match.group(1)}/{td_match.group(2)}"

    # QNH
    qnh_match = re.search(r'Q(\d{4})', raw_metar)
    if qnh_match:
        data["qnh_hpa"] = qnh_match.group(1)

    return data

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

def create_pdf_bytes(data, station_id):
    """Membuat PDF dan mengembalikan object BYTES yang valid"""
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=9)
    
    # Perhitungan Tekanan
    try:
        qnh_val = float(data['qnh_hpa'])
    except:
        qnh_val = 1013.0
    
    qfe_val = qnh_val - 4 # Estimasi selisih elevasi
    
    def format_pressure(val):
        ins = val * 0.02953
        mmhg = val * 0.75006
        return f"{int(val)} mbs / {ins:.2f} ins / {mmhg:.1f} mm Hg"

    table_items = [
        ("METEOROLOGICAL OBS AT", station_id),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", data['time_utc']),
        ("AERODROME IDENTIFICATION", station_id),
        ("SURFACE WIND DIRECTION, SPEED AND VARIATION", data['wind']),
        ("HORIZONTAL VISIBILITY", data['vis']),
        ("RUNWAY VISUAL RANGE", "NIL"),
        ("PRESENT WEATHER", data['weather']),
        ("AMOUNT AND HEIGHT OF BASE OF LOW CLOUD", data['clouds']),
        ("AIR TEMPERATURE AND DEW POINT", data['temp_dew']),
        ("QNH", format_pressure(qnh_val)),
        ("QFE*", format_pressure(qfe_val)),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", data['time_utc']),
    ]

    for label, val in table_items:
        # Menggunakan format baru fpdf2 untuk tabel
        curr_x = pdf.get_x()
        curr_y = pdf.get_y()
        pdf.multi_cell(85, 10, str(label), border=1)
        pdf.set_xy(curr_x + 85, curr_y)
        pdf.cell(105, 10, str(val), border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', new_x="LMARGIN", new_y="NEXT")
    
    # PENTING: Mengembalikan hasil dalam bentuk bytes murni
    return bytes(pdf.output())

# --- UI STREAMLIT ---
st.title("✈️ Mil-Aero QAM Generator")
st.write("Format Laporan Meteorologi Take-off/Landing (WIBB/TNI AU) [cite: 1, 2]")

icao = st.text_input("Masukkan ICAO Code:", value="WIBB").upper()

if st.button("Proses Data"):
    if icao:
        with st.spinner("Mengambil data..."):
            raw_metar = get_metar(icao)
            if raw_metar:
                st.success(f"Data METAR Terdeteksi!")
                st.code(raw_metar)
                
                parsed = parse_metar(raw_metar)
                
                # Membuat PDF dalam memori
                try:
                    pdf_data = create_pdf_bytes(parsed, icao)
                    
                    # Tombol unduh dengan data bytes yang sudah dipastikan valid
                    st.download_button(
                        label="📥 Unduh PDF QAM",
                        data=pdf_data,
                        file_name=f"QAM_{icao}_{datetime.now().strftime('%d%m%y_%H%M')}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Gagal menyusun PDF: {e}")
            else:
                st.error("Gagal menarik data METAR. Coba kode ICAO lain.")
    else:
        st.warning("Silakan isi kode ICAO.")
