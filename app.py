import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️")

def get_metar_raw(icao):
    """Mengambil data METAR mentah dari API resmi Aviation Weather"""
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
    """Parsing data METAR dengan logika yang konsisten"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "temp": "NIL", "qnh": "1013", "time": datetime.utcnow().strftime("%H.%M")
    }
    
    # Wind (Arah/Kecepatan & Variasi)
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w:
        data["wind"] = f"{w.group(1)}/{w.group(2)} KT"
        # Cek jika ada variasi arah (misal 180V240)
        v = re.search(r'(\d{3})V(\d{3})', raw)
        if v: data["wind"] += f" VAR {v.group(1)}V{v.group(2)}"

    # Visibility & Clouds
    if "CAVOK" in raw:
        data["vis"], data["cld"] = "10 KM OR MORE", "NIL"
    else:
        v_match = re.search(r'\s(\d{4})\s', raw)
        if v_match: data["vis"] = f"{v_match.group(1)} M"
        
        # Cloud Layers
        c_layers = re.findall(r'([A-Z]{3})(\d{3})', raw)
        if c_layers:
            data["cld"] = ", ".join([f"{l[0]} {int(l[1])*100} FT" for l in c_layers])

    # Present Weather
    wx_match = re.search(r'\s([-+]?[A-Z]{2,4})\s', raw)
    if wx_match: data["wx"] = wx_match.group(1)

    # Temp/Dew Point
    td = re.search(r'(\d{2})/(\d{2})', raw)
    if td: data["temp"] = f"{td.group(1)}/{td.group(2)}"

    # QNH
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
    qfe = qnh - 4 # Estimasi koreksi elevasi
    
    def fmt_p(val):
        return f"{int(val)} mbs / {val*0.02953:.2f} ins / {val*0.75006:.1f} mm Hg"

    # Tabel dengan perbaikan label agar tidak rusak
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
        # Gunakan multi_cell dengan tinggi baris konsisten
        x_pos = pdf.get_x()
        y_pos = pdf.get_y()
        
        # Kolom Kiri (Label)
        pdf.multi_cell(85, 8, label, border=1)
        next_y = pdf.get_y()
        
        # Kolom Kanan (Isi) - Kembali ke posisi Y awal baris ini
        pdf.set_xy(x_pos + 85, y_pos)
        
        # Hitung tinggi kotak kanan agar sama dengan kotak kiri
        h_box = next_y - y_pos
        pdf.multi_cell(105, h_box, str(val), border=1, align='L')
        
        # Pindah ke baris baru
        pdf.set_y(next_y)
    
    pdf.ln(10)
    pdf.cell(0, 10, f"TIME OF ISSUE: {data['time']} UTC", ln=True)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- UI STREAMLIT ---
st.title("✈️ QAM Form Generator (Fixed)")
st.info("Input kode ICAO untuk menarik data METAR real-time.")

icao_input = st.text_input("Masukkan Kode ICAO:", value="WIBB").upper()

if st.button("Generate QAM"):
    raw = get_metar_raw(icao_input)
    if raw:
        st.success(f"METAR: {raw}")
        parsed = parse_metar(raw)
        pdf_bytes = create_pdf(parsed, icao_input)
        
        st.download_button(
            label="📥 Download PDF QAM",
            data=pdf_bytes,
            file_name=f"QAM_{icao_input}_{datetime.now().strftime('%H%M')}Z.pdf",
            mime="application/pdf"
        )
    else:
        st.error("Gagal menarik data. Periksa kode ICAO atau koneksi internet.")
