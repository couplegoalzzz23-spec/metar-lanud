import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️")

def get_metar_data(icao):
    """Mengambil data METAR dari API resmi Aviation Weather"""
    # Menggunakan endpoint API data mentah agar tidak diblokir
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200 and response.text.strip():
            return response.text.strip(), None
        return None, "Stasiun offline atau data tidak dipublikasikan (Militer)."
    except Exception as e:
        return None, f"Masalah koneksi: {str(e)}"

def parse_metar(raw):
    """Memecah kode METAR menjadi komponen QAM"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "temp": "NIL", "qnh": "1013", "time": datetime.utcnow().strftime("%H.%M")
    }
    # Wind
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w: data["wind"] = f"{w.group(1)}/{w.group(2)} KT"
    # Visibility
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

def create_pdf(data, icao, nama_lanud):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    qnh = float(data['qnh'])
    qfe = qnh - 4 # Estimasi selisih tekanan
    
    def fmt_press(val):
        return f"{int(val)} mbs / {val*0.02953:.2f} ins"

    # Struktur Tabel sesuai file PDF CamScanner Anda
    rows = [
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
        ("QNH", fmt_press(qnh)),
        ("QFE*", fmt_press(qfe)),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", data['time']),
    ]

    for label, val in rows:
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(80, 10, label, border=1)
        pdf.set_xy(x + 80, y)
        pdf.cell(110, 10, str(val), border=1, ln=True)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- MAIN INTERFACE ---
st.title("✈️ QAM Generator - TNI AU")

# Membaca File CSV yang Anda unggah
try:
    df = pd.read_csv('lanud_tni_au_indonesia.csv')
    options = df['Nama_Lanud'] + " (" + df['ICAO'] + ")"
    selection = st.selectbox("Pilih Lanud:", options)
    idx = options.to_list().index(selection)
    target_icao = df.iloc[idx]['ICAO']
    target_name = df.iloc[idx]['Nama_Lanud']
    status_metar = df.iloc[idx]['Status_METAR_QAM']
except Exception as e:
    st.error(f"File CSV tidak ditemukan atau rusak: {e}")
    target_icao = st.text_input("Input ICAO Manual:", "WIBB").upper()
    target_name = target_icao
    status_metar = "AKTIF"

if st.button("Ambil Data & Buat PDF"):
    with st.spinner(f"Menghubungi server untuk {target_icao}..."):
        raw_metar, err = get_metar_data(target_icao)
        
        if raw_metar:
            st.success("Data Berhasil Ditarik!")
            st.code(raw_metar)
            
            parsed_data = parse_metar(raw_metar)
            pdf_bytes = create_pdf(parsed_data, target_icao, target_name)
            
            st.download_button(
                label="📥 Unduh PDF QAM",
                data=pdf_bytes,
                file_name=f"QAM_{target_icao}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf"
            )
        else:
            st.error(f"Gagal: {err}")
            if status_metar == "MILITER / NON PUBLIK":
                st.warning(f"Lanud {target_name} berstatus Militer murni. Datanya tidak tersedia di server publik (AviationWeather).")
