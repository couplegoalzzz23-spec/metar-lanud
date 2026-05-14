import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import re

# --- 1. KONFIGURASI HALAMAN (WAJIB PALING ATAS) ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️", layout="wide")

# --- 2. FUNGSI LOGIKA (BACKEND) ---

def get_metar_raw(icao):
    """Ambil data METAR mentah dari server publik"""
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
    """Parsing sandi METAR ke format tabel QAM"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "temp": "NIL", "qnh": "1013", "time": datetime.utcnow().strftime("%H.%M")
    }
    if not raw: return data
    
    # Wind & Var
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w:
        data["wind"] = f"{w.group(1)}/{w.group(2)} KT"
        v = re.search(r'(\d{3})V(\d{3})', raw)
        if v: data["wind"] += f" VAR {v.group(1)}V{v.group(2)}"

    # Vis & Cloud
    if "CAVOK" in raw:
        data["vis"], data["cld"] = "10 KM OR MORE", "NIL"
    else:
        v_match = re.search(r'\s(\d{4})\s', raw)
        if v_match: data["vis"] = f"{v_match.group(1)} M"
        c_layers = re.findall(r'([A-Z]{3})(\d{3})', raw)
        if c_layers:
            data["cld"] = ", ".join([f"{l[0]} {int(l[1])*100} FT" for l in c_layers])

    # Wx, Temp, QNH
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

def create_pdf(data, icao, nama_lanud):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    qnh = float(data['qnh'])
    qfe = qnh - 4 # Estimasi koreksi
    
    def fmt_p(val):
        return f"{int(val)} mbs / {val*0.02953:.2f} ins / {val*0.75006:.1f} mm Hg"

    rows = [
        ("METEOROLOGICAL OBS AT", nama_lanud),
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
        y_start = pdf.get_y()
        pdf.multi_cell(85, 8, label, border=1)
        y_end = pdf.get_y()
        pdf.set_xy(85 + 10, y_start)
        pdf.multi_cell(105, y_end - y_start, str(val), border=1)
        pdf.set_y(y_end)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- 3. INTERFACE (FRONTEND) ---

st.title("✈️ Mil-Aero QAM Generator")
st.write("Dinas Pengembangan Operasi - TNI AU")

# Load Database Lanud dari CSV
try:
    df_lanud = pd.read_csv('lanud_tni_au_indonesia.csv')
    lanud_list = (df_lanud['Nama_Lanud'] + " (" + df_lanud['ICAO'] + ")").tolist()
except:
    df_lanud = None
    lanud_list = ["WIBB (Manual)"]

# Pilihan Mode
tab1, tab2 = st.tabs(["📡 Otomatis (Cloud)", "⌨️ Input Manual (Radio/HT)"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        if df_lanud is not None:
            pilih = st.selectbox("Pilih Pangkalan TNI AU:", lanud_list)
            target_icao = df_lanud.iloc[lanud_list.index(pilih)]['ICAO']
            target_name = df_lanud.iloc[lanud_list.index(pilih)]['Nama_Lanud']
        else:
            target_icao = st.text_input("Kode ICAO:", "WIBB")
            target_name = target_icao
            
    if st.button("Tarik Data & Buat PDF"):
        raw = get_metar_raw(target_icao)
        if raw:
            st.success(f"METAR: {raw}")
            parsed = parse_metar(raw)
            pdf = create_pdf(parsed, target_icao, target_name)
            st.download_button("📥 Download PDF QAM", pdf, f"QAM_{target_icao}.pdf", "application/pdf")
        else:
            st.error("Data tidak ditemukan di server publik. Gunakan 'Input Manual'.")

with tab2:
    st.info("Gunakan mode ini untuk pangkalan Militer Non-Publik.")
    icao_man = st.text_input("ICAO Pangkalan:", value="WIAJ")
    raw_man = st.text_area("Tempel Sandi METAR di sini:", placeholder="Contoh: WIAJ 140500Z 19004KT 9999 SCT010 32/23 Q1007")
    
    if st.button("Generate dari Manual"):
        if raw_man:
            parsed = parse_metar(raw_man)
            pdf = create_pdf(parsed, icao_man, icao_man)
            st.download_button("📥 Download PDF QAM (Manual)", pdf, f"QAM_{icao_man}_MAN.pdf", "application/pdf")
