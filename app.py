import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from fpdf import FPDF
from datetime import datetime
import re
from bs4 import BeautifulSoup

# --- 1. KONFIGURASI SISTEM ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️", layout="wide")

# --- 2. DATABASE LANUD (ELEVASI AKTUAL UNTUK PRESISI QFE) ---
LANUD_MAP = {
    "Lanud Halim Perdanakusuma (WIHH)": {"icaos": ["WIHH", "WIII"], "elev_ft": 85},
    "Lanud Atang Sendjaja (WIAJ)": {"icaos": ["WIAJ", "WIHH", "WIII"], "elev_ft": 535},
    "Lanud Suryadarma (WIAK)": {"icaos": ["WIAK", "WICC", "WIIH"], "elev_ft": 380},
    "Lanud Husein Sastranegara (WICC)": {"icaos": ["WICC", "WIII"], "elev_ft": 2436},
    "Lanud Iswahjudi (WARI)": {"icaos": ["WARI", "WARQ", "WARR"], "elev_ft": 360},
    "Lanud Abdulrachman Saleh (WARA)": {"icaos": ["WARA", "WARR"], "elev_ft": 1726},
    "Lanud Adisutjipto (WARJ)": {"icaos": ["WARJ", "WAHH", "WARQ"], "elev_ft": 350},
    "Lanud Juanda (WARR)": {"icaos": ["WARR"], "elev_ft": 9},
    "Lanud Sultan Hasanuddin (WAAA)": {"icaos": ["WAAA"], "elev_ft": 48},
    # (Tambahkan Lanud lainnya dengan format yang sama jika diperlukan)
}

# --- 3. ENGINE PENGAMBIL & PARSING DATA ---
def get_robust_session():
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
    return session

def fetch_metar_raw(icao):
    try:
        url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        res = get_robust_session().get(url, timeout=6)
        if res.status_code == 200 and icao in res.text: return res.text.strip(), "NOAA API"
    except: pass
    return None, None

def fetch_taf_raw(icao):
    try:
        url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw"
        res = get_robust_session().get(url, timeout=6)
        if res.status_code == 200 and icao in res.text: return res.text.strip()
    except: pass
    return "TAFOR DATA NIL="

def parse_metar(raw, original_icao, elev_ft):
    data = {"obs_date": "NIL", "obs_time": "NIL", "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", "tt_td": "NIL", "qnh": "NIL", "qfe": "NIL", "trend": "NOSIG", "rmk": "NIL"}
    if not raw: return data
    
    # Ekstraksi Waktu (DDHHMM)
    time_match = re.search(r'\b\d{2}(\d{2})(\d{2})Z\b', raw)
    if time_match: data["obs_time"] = f"{time_match.group(1)}.{time_match.group(2)}"
    
    # QNH & QFE (Kalkulasi presisi menggunakan elevasi)
    q_match = re.search(r'Q(\d{4})', raw)
    if q_match:
        qnh_val = int(q_match.group(1))
        data["qnh"] = f"{qnh_val}/{qnh_val*0.02953:.2f}"
        qfe_val = int(round(qnh_val - (elev_ft / 30.0)))
        data["qfe"] = f"{qfe_val}/{qfe_val*0.02953:.2f}"
    return data

# --- 4. ENGINE PDF ---
class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 6, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", ln=True, align='C')
        self.ln(5)

def generate_pdf(data, raw_taf, icao):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", '', 10)
    pdf.cell(0, 6, f"METEOROLOGICAL OBS: {icao} | TIME: {data['obs_time']} UTC", ln=True)
    pdf.ln(5)
    
    # Tabel Data
    table_data = [["AERODROME", icao], ["WIND", data['wind']], ["QNH", data['qnh']], ["QFE", data['qfe']]]
    for item in table_data:
        pdf.cell(90, 7, item[0], border=1)
        pdf.cell(90, 7, item[1], border=1, ln=True)
    
    pdf.ln(5)
    pdf.cell(0, 6, "TAFOR:", ln=True)
    pdf.multi_cell(0, 5, raw_taf)
    return bytes(pdf.output())

# --- 5. INTERFACE ---
st.title("✈️ TNI AU QAM Generator")
pilihan = st.selectbox("Pilih Lanud:", list(LANUD_MAP.keys()))

if st.button("TARIK DATA & GENERATE QAM"):
    cfg = LANUD_MAP[pilihan]
    raw, taf, src, icao = None, None, None, None
    
    for i in cfg["icaos"]:
        r, s = fetch_metar_raw(i)
        if r:
            raw, taf, src, icao = r, fetch_taf_raw(i), s, i
            break
            
    if raw:
        st.success(f"Data berhasil diambil dari {src}")
        p_data = parse_metar(raw, icao, cfg["elev_ft"])
        pdf_bytes = generate_pdf(p_data, taf, icao)
        st.download_button("📥 DOWNLOAD PDF", pdf_bytes, f"QAM_{icao}.pdf", "application/pdf")
    else:
        st.error("Data tidak tersedia.")
