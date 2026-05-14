import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator - TNI AU", page_icon="✈️")

def get_metar(station_id):
    """Mengambil data METAR dengan Header Browser asli agar tidak diblokir"""
    # Gunakan endpoint API yang lebih stabil dengan format raw
    url = f"https://aviationweather.gov/api/data/metar?ids={station_id}&format=raw"
    
    # Header ini sangat penting agar server tidak menolak request kita
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            raw_text = response.text.strip()
            if not raw_text:
                return None, "Data kosong (Stasiun mungkin sedang offline atau ICAO salah)."
            return raw_text, None
        else:
            return None, f"Server Error: {response.status_code}"
    except requests.exceptions.Timeout:
        return None, "Koneksi Timeout (Server sedang sibuk)."
    except Exception as e:
        return None, f"Terjadi kesalahan: {str(e)}"

def parse_metar(raw_metar):
    """Ekstraksi data dari kode METAR mentah"""
    data = {
        "wind": "NIL", "vis": "NIL", "weather": "NIL", 
        "clouds": "NIL", "temp_dew": "NIL", "qnh_hpa": "1013",
        "time_utc": datetime.utcnow().strftime("%H.%M")
    }
    
    # Wind
    wind = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw_metar)
    if wind: data["wind"] = f"{wind.group(1)}/{wind.group(2)} KT"

    # Visibility
    if "CAVOK" in raw_metar:
        data["vis"] = "10 KM OR MORE"
        data["clouds"] = "NIL"
    else:
        vis = re.search(r'\s(\d{4})\s', raw_metar)
        if vis: data["vis"] = f"{vis.group(1)} M"

    # Weather & Clouds
    wx = re.search(r'\s([-+]?[A-Z]{2,4})\s', raw_metar)
    if wx: data["weather"] = wx.group(1)
    
    cld = re.search(r'([A-Z]{3})(\d{3})', raw_metar)
    if cld: data["clouds"] = f"{cld.group(1)} {int(cld.group(2))*100} FT"

    # Temp/Dew & QNH
    td = re.search(r'(\d{2})/(\d{2})', raw_metar)
    if td: data["temp_dew"] = f"{td.group(1)}/{td.group(2)}"
    
    qnh = re.search(r'Q(\d{4})', raw_metar)
    if qnh: data["qnh_hpa"] = qnh.group(1)

    return data

class QAM_PDF(FPDF):
    def header(self):
        # Header sesuai source [1] [2]
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(5)

def create_pdf_bytes(data, station_id):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=9)
    
    qnh = float(data['qnh_hpa'])
    qfe = qnh - 4 # Estimasi QFE
    
    def fmt(val):
        return f"{int(val)} mbs / {val*0.02953:.2f} ins / {val*0.75006:.1f} mm Hg"

    # Tabel QAM sesuai source [3-15]
    items = [
        ("METEOROLOGICAL OBS AT", station_id),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", data['time_utc']),
        ("AERODROME IDENTIFICATION", station_id),
        ("SURFACE WIND DIRECTION & SPEED", data['wind']),
        ("HORIZONTAL VISIBILITY", data['vis']),
        ("RUNWAY VISUAL RANGE", "NIL"),
        ("PRESENT WEATHER", data['weather']),
        ("AMOUNT & HEIGHT BASE OF LOW CLOUD", data['clouds']),
        ("AIR TEMP & DEW POINT TEMP", data['temp_dew']),
        ("QNH", fmt(qnh)),
        ("QFE*", fmt(qfe)),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", data['time_utc']),
    ]

    for label, val in items:
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(85, 10, label, border=1)
        pdf.set_xy(x + 85, y)
        pdf.cell(105, 10, str(val), border=1, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("✈️ Mil-Aero QAM Generator")
st.markdown("Format: **DINAS PENGEMBANGAN OPERASI - TNI AU** [cite: 1, 2]")

icao = st.text_input("Masukkan ICAO Code (Contoh: WIBB, WIII, WARR):", value="WIBB").upper()

if st.button("Ambil Data & Buat PDF"):
    if icao:
        with st.spinner(f"Mencari data untuk {icao}..."):
            raw_metar, error_msg = get_metar(icao)
            
            if raw_metar:
                st.success("Data Berhasil Ditarik!")
                st.code(raw_metar)
                
                parsed = parse_metar(raw_metar)
                pdf_data = create_pdf_bytes(parsed, icao)
                
                st.download_button(
                    label="📥 Unduh Laporan QAM (PDF)",
                    data=pdf_data,
                    file_name=f"QAM_{icao}_{datetime.now().strftime('%H%M')}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error(f"Gagal: {error_msg}")
                st.info("Saran: Pastikan kode ICAO benar dan stasiun tersebut aktif mengirimkan laporan METAR jam ini.")
    else:
        st.warning("Silakan masukkan kode ICAO.")
