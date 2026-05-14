import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import re

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️")

# --- 2. FUNGSI LOGIKA (BACKEND) ---

def get_metar_raw(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.text.strip() if response.status_code == 200 else None
    except:
        return None

def parse_metar(raw):
    """Parsing sandi METAR untuk mode otomatis"""
    data = {"wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", "temp": "NIL", "qnh": "1013"}
    if not raw: return data
    
    # Wind
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w: data["wind"] = f"{w.group(1)}/{w.group(2)} KT"
    
    # Visibility
    if "CAVOK" in raw: data["vis"] = "10 KM OR MORE"
    else:
        v = re.search(r'\s(\d{4})\s', raw)
        if v: data["vis"] = f"{v.group(1)} M"

    # Cloud
    c = re.findall(r'([A-Z]{3})(\d{3})', raw)
    if c: data["cld"] = ", ".join([f"{l[0]} {int(l[1])*100} FT" for l in c])

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
        self.ln(8)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(5)

def create_pdf(data, icao, name, time):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    # Perhitungan Tekanan
    qnh_val = float(data['qnh'])
    qfe_val = qnh_val - 4
    
    def fmt_p(v):
        return f"{int(v)} mbs / {v*0.02953:.2f} ins / {v*0.75006:.1f} mm Hg"

    rows = [
        ("METEOROLOGICAL OBS AT", name),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", time),
        ("AERODROME IDENTIFICATION", icao),
        ("SURFACE WIND DIRECTION & SPEED", data['wind']),
        ("HORIZONTAL VISIBILITY", data['vis']),
        ("RUNWAY VISUAL RANGE", "NIL"),
        ("PRESENT WEATHER", data['wx']),
        ("AMOUNT & HEIGHT OF CLOUD", data['cld']),
        ("AIR TEMP / DEW POINT", data['temp']),
        ("QNH", fmt_p(qnh_val)),
        ("QFE*", fmt_p(qfe_val)),
        ("SUPPLEMENTARY INFO", "NIL"),
        ("TIME OF ISSUE (UTC)", time),
    ]

    for label, val in rows:
        y = pdf.get_y()
        pdf.multi_cell(85, 9, label, border=1)
        h = pdf.get_y() - y
        pdf.set_xy(85 + 10, y)
        pdf.cell(105, h, str(val), border=1, ln=True)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- 3. INTERFACE (FRONTEND) ---

st.title("✈️ QAM Generator")

# Load Database Lanud
try:
    df = pd.read_csv('lanud_tni_au_indonesia.csv')
    lanud_map = {f"{r['Nama_Lanud']} ({r['ICAO']})": r for _, r in df.iterrows()}
    pilihan = st.selectbox("Pilih Pangkalan:", list(lanud_map.keys()))
    sel_icao = lanud_map[pilihan]['ICAO']
    sel_name = lanud_map[pilihan]['Nama_Lanud']
except:
    sel_icao = st.text_input("Kode ICAO:", "WIBB").upper()
    sel_name = sel_icao

tab1, tab2 = st.tabs(["📡 Tarik Otomatis", "⌨️ Isian Manual"])

with tab1:
    if st.button("Generate dari Cloud"):
        raw = get_metar_raw(sel_icao)
        if raw:
            st.info(f"METAR Terdeteksi: {raw}")
            p = parse_metar(raw)
            pdf = create_pdf(p, sel_icao, sel_name, datetime.utcnow().strftime("%H.%M"))
            st.download_button("📥 Unduh PDF QAM", pdf, f"QAM_{sel_icao}.pdf")
        else:
            st.error("Data tidak ditemukan di internet. Gunakan tab 'Isian Manual'.")

with tab2:
    st.write("Isi data sesuai laporan radio/HT:")
    c1, c2 = st.columns(2)
    with c1:
        m_wind = st.text_input("Wind (Arah/Kecepatan):", "040/05 KT")
        m_vis = st.text_input("Visibility:", "9999 M")
        m_temp = st.text_input("Temp/Dew Point:", "30/25")
    with c2:
        m_cld = st.text_input("Cloud (Jumlah/Tinggi):", "FEW 1000 FT")
        m_qnh = st.text_input("QNH (Hanya Angka):", "1013")
        m_time = st.text_input("Waktu (UTC):", datetime.utcnow().strftime("%H.%M"))
    
    if st.button("Generate dari Manual"):
        m_data = {"wind": m_wind, "vis": m_vis, "wx": "NIL", "cld": m_cld, "temp": m_temp, "qnh": m_qnh}
        pdf = create_pdf(m_data, sel_icao, sel_name, m_time)
        st.download_button("📥 Unduh PDF QAM (Manual)", pdf, f"QAM_{sel_icao}_Manual.pdf")
