import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator - TNI AU", page_icon="✈️")

def get_metar_raw(icao):
    """Mengambil data METAR menggunakan API Data mentah (Bukan link web biasa)"""
    # URL API Resmi untuk data mentah
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200 and response.text.strip():
            return response.text.strip(), None
        return None, "Data tidak ditemukan atau stasiun sedang offline."
    except Exception as e:
        return None, str(e)

def parse_metar(raw):
    """Parsing data METAR ke format QAM"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "temp": "NIL", "qnh": "1013", "time": datetime.utcnow().strftime("%H.%M")
    }
    
    # Wind
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w: data["wind"] = f"{w.group(1)}/{w.group(2)} KT"

    # Vis & Cloud (CAVOK)
    if "CAVOK" in raw:
        data["vis"], data["cld"] = "10 KM OR MORE", "NIL"
    else:
        v = re.search(r'\s(\d{4})\s', raw)
        if v: data["vis"] = f"{v.group(1)} M"
        c = re.search(r'([A-Z]{3})(\d{3})', raw)
        if c: data["cld"] = f"{c.group(1)} {int(c.group(2))*100} FT"

    # Temp/Dew & QNH
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
        self.ln(5)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(5)

def create_pdf(data, icao, nama_lanud):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=9)
    
    qnh = float(data['qnh'])
    qfe = qnh - 4 # Estimasi selisih elevasi aerodrome
    
    def fmt_p(val):
        return f"{int(val)} mbs / {val*0.02953:.2f} ins / {val*0.75006:.1f} mm Hg"

    items = [
        ("METEOROLOGICAL OBS AT", nama_lanud),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", data['time']),
        ("AERODROME IDENTIFICATION", icao),
        ("SURFACE WIND DIRECTION & SPEED", data['wind']),
        ("HORIZONTAL VISIBILITY", data['vis']),
        ("RUNWAY VISUAL RANGE", "NIL"),
        ("PRESENT WEATHER", data['wx']),
        ("AMOUNT & HEIGHT BASE OF LOW CLOUD", data['cld']),
        ("AIR TEMP & DEW POINT TEMP", data['temp']),
        ("QNH", fmt_p(qnh)),
        ("QFE*", fmt_p(qfe)),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", data['time']),
    ]

    for label, val in items:
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(85, 10, label, border=1)
        pdf.set_xy(x + 85, y)
        pdf.cell(105, 10, str(val), border=1, ln=True)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- MAIN APP ---
st.title("✈️ QAM Generator - TNI AU")

# Load daftar lanud dari CSV
try:
    df = pd.read_csv('lanud_tni_au_indonesia.csv')
    # Filter hanya yang berstatus AKTIF jika diinginkan, atau tampilkan semua
    lanud_options = df['Nama_Lanud'] + " (" + df['ICAO'] + ")"
    selection = st.selectbox("Pilih Pangkalan Udara:", lanud_options)
    target_icao = df.iloc[lanud_options.to_list().index(selection)]['ICAO']
    target_name = df.iloc[lanud_options.to_list().index(selection)]['Nama_Lanud']
except:
    target_icao = st.text_input("Input ICAO Manual (CSV tidak ditemukan):", value="WIBB").upper()
    target_name = target_icao

if st.button("Tarik Data METAR"):
    raw, err = get_metar_raw(target_icao)
    if raw:
        st.success(f"Berhasil menarik data {target_icao}")
        st.code(raw)
        
        parsed = parse_metar(raw)
        pdf_bytes = create_pdf(parsed, target_icao, target_name)
        
        st.download_button(
            label="📥 Download QAM PDF",
            data=pdf_bytes,
            file_name=f"QAM_{target_icao}.pdf",
            mime="application/pdf"
        )
    else:
        st.error(f"Error: {err}")
        st.warning("Catatan: Beberapa Lanud Militer tidak mempublikasikan data METAR ke server publik.")
