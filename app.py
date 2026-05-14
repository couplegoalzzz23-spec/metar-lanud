import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator - TNI AU", page_icon="✈️")

def get_metar_raw(icao):
    """Fungsi pengambil data METAR yang paling stabil"""
    # Menggunakan endpoint API khusus data raw
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            res_text = response.text.strip()
            if res_text == "":
                return None, "Data Kosong (Stasiun Militer/Offline)"
            return res_text, None
        return None, f"Server Error ({response.status_code})"
    except Exception as e:
        return None, f"Koneksi Gagal: {str(e)}"

def parse_metar(raw):
    """Ekstraksi data METAR untuk tabel QAM"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "temp": "NIL", "qnh": "1013", "time_utc": datetime.utcnow().strftime("%H.%M")
    }
    
    # Wind (Arah/Kecepatan)
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

    # Temp/Dew & QNH
    td = re.search(r'(\d{2})/(\d{2})', raw)
    if td: data["temp"] = f"{td.group(1)}/{td.group(2)}"
    q = re.search(r'Q(\d{4})', raw)
    if q: data["qnh"] = q.group(1)

    return data

class QAM_PDF(FPDF):
    def header(self):
        # Header sesuai dokumen TNI AU
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(5)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 10, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(5)

def create_pdf(data, icao, nama_lanud):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    qnh_val = float(data['qnh'])
    qfe_val = qnh_val - 4 # Estimasi QFE (Disesuaikan elevasi)
    
    def format_p(val):
        return f"{int(val)} mbs / {val*0.02953:.2f} ins"

    # Struktur Tabel QAM
    table_data = [
        ("METEOROLOGICAL OBS AT", nama_lanud),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", data['time_utc']),
        ("AERODROME IDENTIFICATION", icao),
        ("SURFACE WIND DIRECTION & SPEED", data['wind']),
        ("HORIZONTAL VISIBILITY", data['vis']),
        ("RUNWAY VISUAL RANGE", "NIL"),
        ("PRESENT WEATHER", data['wx']),
        ("AMOUNT & HEIGHT BASE OF LOW CLOUD", data['cld']),
        ("AIR TEMP & DEW POINT TEMP", data['temp']),
        ("QNH", format_p(qnh_val)),
        ("QFE*", format_p(qfe_val)),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", data['time_utc']),
    ]

    for label, value in table_data:
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(85, 10, label, border=1)
        pdf.set_xy(x + 85, y)
        pdf.cell(105, 10, str(value), border=1, ln=True)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- INTERFACE UTAMA ---
st.title("✈️ Aplikasi QAM Otomatis")
st.write("Sesuai Format Dinas Pengembangan Operasi TNI AU")

# Membaca CSV Lanud
try:
    df = pd.read_csv('lanud_tni_au_indonesia.csv')
    options = df['Nama_Lanud'] + " (" + df['ICAO'] + ")"
    choice = st.selectbox("Pilih Lanud / Pangkalan:", options)
    
    # Ambil data dari baris yang dipilih
    selected_row = df[options == choice].iloc[0]
    target_icao = selected_row['ICAO']
    target_name = selected_row['Nama_Lanud']
    status_stasiun = selected_row['Status_METAR_QAM']
except Exception as e:
    st.error("File CSV 'lanud_tni_au_indonesia.csv' tidak ditemukan!")
    target_icao = "WIBB"
    target_name = "Lanud Roesmin Nurjadin"
    status_stasiun = "AKTIF"

if st.button("Generate Laporan"):
    with st.spinner(f"Menghubungi server untuk {target_icao}..."):
        raw_metar, error_msg = get_metar_raw(target_icao)
        
        if raw_metar:
            st.success("Data METAR Berhasil Ditarik!")
            st.code(raw_metar)
            
            p_data = parse_metar(raw_metar)
            pdf_out = create_pdf(p_data, target_icao, target_name)
            
            st.download_button(
                label="📥 Unduh PDF QAM",
                data=pdf_out,
                file_name=f"QAM_{target_icao}.pdf",
                mime="application/pdf"
            )
        else:
            st.error(f"Gagal: {error_msg}")
            if "MILITER" in str(status_stasiun):
                st.warning("Info: Lanud ini berstatus Militer/Non-Publik. Data tidak tersedia di server sipil.")
