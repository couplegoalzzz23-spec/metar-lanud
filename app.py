import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️")

def get_metar_raw(icao):
    """Ambil data METAR mentah dengan Header Browser agar tidak diblokir"""
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200 and response.text.strip():
            return response.text.strip()
        return None
    except:
        return None

def parse_metar(raw):
    """Parsing METAR untuk keamanan operasional penerbangan"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "temp": "NIL", "qnh": "1013", "time": datetime.utcnow().strftime("%H.%M")
    }
    
    # Wind & Variation
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w:
        data["wind"] = f"{w.group(1)}/{w.group(2)} KT"
        v = re.search(r'(\d{3})V(\d{3})', raw)
        if v: data["wind"] += f" VAR {v.group(1)}V{v.group(2)}"

    # Visibility & Clouds
    if "CAVOK" in raw:
        data["vis"], data["cld"] = "10 KM OR MORE", "NIL"
    else:
        v_match = re.search(r'\s(\d{4})\s', raw)
        if v_match: data["vis"] = f"{v_match.group(1)} M"
        c_layers = re.findall(r'([A-Z]{3})(\d{3})', raw)
        if c_layers:
            data["cld"] = ", ".join([f"{l[0]} {int(l[1])*100} FT" for l in c_layers])

    # Weather, Temp, QNH
    wx_match = re.search(r'\s([-+]?[A-Z]{2,4})\s', raw)
    if wx_match: data["wx"] = wx_match.group(1)
    td = re.search(r'(\d{2})/(\d{2})', raw)
    if td: data["temp"] = f"{td.group(1)}/{td.group(2)}"
    q = re.search(r'Q(\d{4})', raw)
    if q: data["qnh"] = q.group(1)

    return data

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(8)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(5)

def create_pdf(data, icao):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    qnh = float(data['qnh'])
    qfe = qnh - 4 # Koreksi QFE standar
    
    def fmt_p(val):
        return f"{int(val)} mbs / {val*0.02953:.2f} ins / {val*0.75006:.1f} mm Hg"

    # Baris Tabel (Label Harus Persis PDF TNI AU)
    rows = [
        ("METEOROLOGICAL OBS AT", icao),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", data['time']),
        ("AERODROME IDENTIFICATION", icao),
        ("SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION", data['wind']),
        ("HORIZONTAL VISIBILITY", data['vis']),
        ("RUNWAY VISUAL RANGE", "NIL"),
        ("PRESENT WEATHER", data['wx']),
        ("AMOUNT AND HEIGHT OF BASE OF LOW CLOUD", data['cld']),
        ("AIR TEMPERATURE AND DEW POINT TEMPERATURE", data['temp']),
        ("QNH", fmt_p(qnh)),
        ("QFE*", fmt_p(qfe)),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", data['time']),
    ]

    for label, val in rows:
        # Logika perbaikan teks tumpang tindih
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        # Gambar label (Kolom Kiri)
        pdf.multi_cell(85, 8, label, border=1)
        y_end_label = pdf.get_y()
        
        # Gambar isi (Kolom Kanan)
        pdf.set_xy(x_start + 85, y_start)
        h_box = y_end_label - y_start
        pdf.multi_cell(105, h_box, str(val), border=1, align='L')
        
        # Reset posisi ke baris baru
        pdf.set_y(y_end_label)
    
    pdf.ln(10)
    pdf.cell(0, 10, f"TIME OF ISSUE: {data['time']} UTC", ln=True)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- INTERFACE ---
st.title("✈️ QAM Generator Real-Time")
st.write("Sesuai Standar Markas Besar Angkatan Udara")

icao = st.text_input("Masukkan Kode ICAO (WIBB, WIII, WARR):", value="WIBB").upper()

if st.button("Tarik Data & Generate PDF"):
    with st.spinner("Mengambil data cuaca terbaru..."):
        raw_metar = get_metar_raw(icao)
        if raw_metar:
            st.success("Data Berhasil Ditarik!")
            st.code(raw_metar)
            
            parsed = parse_metar(raw_metar)
            pdf_bytes = create_pdf(parsed, icao)
            
            st.download_button(
                label="📥 Download PDF QAM",
                data=pdf_bytes,
                file_name=f"QAM_{icao}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf"
            )
        else:
            st.error("Data tidak tersedia atau ICAO salah. Gunakan kode ICAO bandara aktif.")
