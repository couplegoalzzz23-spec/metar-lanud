import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️")

def get_metar_raw(icao):
    """Mengambil data METAR mentah dari API resmi"""
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and response.text.strip():
            return response.text.strip()
        return None
    except:
        return None

def parse_metar(raw):
    """Parsing data METAR untuk kolom QAM"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "temp": "NIL", "qnh": "1013", "time": datetime.utcnow().strftime("%H.%M")
    }
    # Wind
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w: data["wind"] = f"{w.group(1)}/{w.group(2)} KT"
    # Visibility & Clouds
    if "CAVOK" in raw:
        data["vis"], data["cld"] = "10 KM OR MORE", "NIL"
    else:
        v = re.search(r'\s(\d{4})\s', raw)
        if v: data["vis"] = f"{v.group(1)} M"
        c = re.search(r'([A-Z]{3})(\d{3})', raw)
        if c: data["cld"] = f"{c.group(1)} {int(c.group(2))*100} FT"
    # Temp & QNH
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
        self.ln(10)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(5)

def create_pdf(data, icao):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    qnh = float(data['qnh'])
    qfe = qnh - 4 # Estimasi
    
    # Fungsi format tekanan sesuai kolom di PDF (mbs, ins, mm Hg)
    def fmt_val(val):
        ins = val * 0.02953
        mmhg = val * 0.75006
        return f"{int(val)} mbs / {ins:.2f} ins / {mmhg:.1f} mm Hg"

    # Tabel sesuai urutan di lampiran CamScanner Anda
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
        ("QNH", fmt_val(qnh)),
        ("QFE*", fmt_val(qfe)),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", data['time']),
    ]

    for label, val in rows:
        x, y = pdf.get_x(), pdf.get_y()
        # Menggunakan multi_cell agar teks panjang otomatis turun ke bawah (wrap)
        pdf.multi_cell(85, 10, label, border=1)
        pdf.set_xy(x + 85, y)
        pdf.cell(105, 10, str(val), border=1, ln=True)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- UI STREAMLIT ---
st.title("✈️ QAM Generator")
st.write("Format: Dinas Pengembangan Operasi TNI AU")

icao_input = st.text_input("Masukkan Kode ICAO (Contoh: WIBB, WIII):", value="WIBB").upper()

if st.button("Tampilkan Data & Buat PDF"):
    with st.spinner("Mengambil data..."):
        raw = get_metar_raw(icao_input)
        
        if raw:
            st.success(f"Data METAR {icao_input} Berhasil Ditemukan")
            st.code(raw)
            
            parsed = parse_metar(raw)
            pdf_bytes = create_pdf(parsed, icao_input)
            
            st.download_button(
                label="📥 Unduh PDF QAM",
                data=pdf_bytes,
                file_name=f"QAM_{icao_input}.pdf",
                mime="application/pdf"
            )
        else:
            st.error("Gagal menarik data. Pastikan kode ICAO benar dan stasiun sedang online.")
