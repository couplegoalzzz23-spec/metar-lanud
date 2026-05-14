import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re
from bs4 import BeautifulSoup

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️", layout="centered")

# --- 2. DATABASE LANUD ---
LANUD_DB = {
    "Lanud I Gusti Ngurah Rai (WADD)": "WADD",
    "Lanud Halim Perdanakusuma (WIHH)": "WIHH",
    "Lanud Roesmin Nurjadin (WIBB)": "WIBB",
    "Lanud Supadio (WIOO)": "WIOO",
    "Lanud Sultan Hasanuddin (WAAA)": "WAAA",
    "Lanud Sam Ratulangi (WAMM)": "WAMM",
    "Lanud Iswahyudi (WARI)": "WARI",
    "Lanud Abdulrachman Saleh (WARA)": "WARA",
    "Lanud Adisutjipto (WARJ)": "WARJ",
    "Lanud Juanda (WARR)": "WARR",
    "Lanud Husein Sastranegara (WICC)": "WICC",
    "Lanud Pattimura (WAPP)": "WAPP",
    "Lanud El Tari (WATT)": "WATT",
    "Lanud Silas Papare (WAJJ)": "WAJJ",
    "Lanud Soewondo (WIMK)": "WIMK",
    "Lanud Atang Sendjaja (WIAJ)": "WIAJ",
    "Lanud Iskandar (WAOI)": "WAOI",
    "Lanud Syamsudin Noor (WAOO)": "WAOO",
    "Lanud Dhomber (WALL)": "WALL",
    "Lanud Manuhua (WABB)": "WABB",
    "Lanud Johanes Kapiyau (WABI)": "WABI",
    "Lanud Leo Wattimena (WAMW)": "WAMW",
    "Lanud Radin Inten II (WILL)": "WILL",
    "Lanud SMH Palembang (WIPP)": "WIPP",
    "Lanud Hang Nadim (WIDD)": "WIDD",
    "Lanud Raja Haji Fisabilillah (WIDN)": "WIDN",
}

# --- 3. ENGINE PENGAMBIL DATA ---

def fetch_metar(icao):
    """Mengambil data dari BMKG dengan fallback ke NOAA"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    # Sumber 1: BMKG
    try:
        url_bmkg = f"https://web-aviation.bmkg.go.id/web/metar_speci.php?i={icao}"
        res = requests.get(url_bmkg, headers=headers, timeout=10, verify=False)
        all_text = BeautifulSoup(res.text, 'html.parser').get_text(separator=" ")
        match = re.search(fr"({icao}\s\d{{6}}Z\s.*?)(?==|$)", all_text)
        if match: return match.group(1).strip(), "BMKG"
    except: pass
    # Sumber 2: NOAA
    try:
        url_noaa = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        res = requests.get(url_noaa, headers=headers, timeout=10)
        if res.status_code == 200 and len(res.text) > 10: return res.text.strip(), "NOAA"
    except: pass
    return None, None

def parse_metar(raw, icao):
    """Parsing METAR secara detail untuk format QAM"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", 
        "cld": "NIL", "tt_td": "NIL", "qnh": "1013", 
        "trend": "NOSIG", "rmk": "NIL"
    }
    if not raw: return data
    
    # WIND
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w: data["wind"] = f"{w.group(1)}/{w.group(2)}KT"
    
    # VISIBILITY & CLOUD
    if "CAVOK" in raw:
        data["vis"] = "10 KM"
        data["cld"] = "NIL"
    else:
        v_match = re.search(r'\s(\d{4})\s', raw)
        if v_match:
            dist = int(v_match.group(1))
            data["vis"] = f"{dist//1000} KM" if dist >= 1000 else f"{dist} M"
        
        # Mencari awan (Contoh: FEW017, SCT010, BKN020)
        c_match = re.search(r'([A-Z]{3}\d{3})', raw)
        if c_match: data["cld"] = c_match.group(1) + "FT"

    # WEATHER (PERBAIKAN: Menghindari ICAO masuk ke Weather)
    # Mencari sandi cuaca standar METAR seperti TS, RA, DZ, HZ, BR, FG, dll.
    wx_codes = r'(VC|MI|BC|PR|DR|BL|SH|TS|FZ|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)'
    wx_search = re.search(fr'\s([-+]?{wx_codes}+)\s', raw)
    if wx_search:
        data["wx"] = wx_search.group(1)
    else:
        data["wx"] = "NIL"
    
    # TT/TD
    tt_td_match = re.search(r'(\d{2})/(\d{2})', raw)
    if tt_td_match:
        data["tt_td"] = f"{tt_td_match.group(1)}°C/{tt_td_match.group(2)}°C"
    
    # QNH
    q_match = re.search(r'Q(\d{4})', raw)
    if q_match: data["qnh"] = q_match.group(1)

    return data

# --- 4. ENGINE PDF (FORMAT SESUAI CONTOH) ---

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(10)

def create_qam_pdf(data, icao, name):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=11)
    
    qnh = int(data['qnh'])
    qfe = qnh - 1 # Estimasi standar MB
    
    # Header Report
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 7, "MET REPORT (QAM)", ln=True)
    pdf.cell(0, 7, f"LANUD {name.upper()} ({icao})", ln=True)
    
    pdf.set_font("helvetica", '', 11)
    pdf.cell(20, 7, "DATE", border=0)
    pdf.cell(5, 7, ":", border=0)
    pdf.cell(0, 7, datetime.now().strftime("%d/%m/%Y"), ln=True)
    
    pdf.cell(20, 7, "TIME", border=0)
    pdf.cell(5, 7, ":", border=0)
    pdf.cell(0, 7, f"{datetime.utcnow().strftime('%H.%M')} UTC", ln=True)
    
    pdf.cell(0, 5, "=" * 35, ln=True)
    pdf.ln(2)

    # Body Report sesuai format contoh
    body = [
        ("WIND", data['wind']),
        ("VISIBILITY", data['vis']),
        ("WEATHER", data['wx']),
        ("CLOUD", data['cld']),
        ("TT/TD", data['tt_td']),
        ("QNH", f"{qnh} MB"),
        ("QFE", f"{qfe} MB"),
        ("REMARKS", data['rmk']),
        ("TREND", data['trend']),
    ]

    for label, val in body:
        pdf.cell(35, 8, label, border=0)
        pdf.cell(5, 8, ":", border=0)
        pdf.cell(0, 8, str(val), border=0, ln=True)
    
    pdf.ln(15)
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    
    return bytes(pdf.output())

# --- 5. INTERFACE ---

st.title("✈️ QAM Generator TNI AU")

pilih_lanud = st.selectbox("Pilih Pangkalan:", list(LANUD_DB.keys()))
icao_code = LANUD_DB[pilih_lanud]
lanud_name = pilih_lanud.split(" (")[0].replace("Lanud ", "")

if st.button("GENERATE REPORT", use_container_width=True):
    with st.spinner("Mengambil data cuaca terbaru..."):
        raw_text, source = fetch_metar(icao_code)
        
        if raw_text:
            st.success(f"Data sinkron (Source: {source})")
            parsed = parse_metar(raw_text, icao_code)
            
            # Tampilkan Preview di App
            st.markdown(f"""
            **Preview MET REPORT (QAM)** LANUD {lanud_name.upper()} ({icao_code})  
            ---
            **WIND**: {parsed['wind']}  
            **VISIBILITY**: {parsed['vis']}  
            **WEATHER**: {parsed['wx']}  
            **CLOUD**: {parsed['cld']}  
            **TT/TD**: {parsed['tt_td']}  
            **QNH**: {parsed['qnh']} MB
            """)
            
            pdf_bytes = create_qam_pdf(parsed, icao_code, lanud_name)
            
            st.download_button(
                label="📥 DOWNLOAD PDF QAM",
                data=pdf_bytes,
                file_name=f"QAM_{icao_code}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Gagal menarik data. Cek koneksi atau coba ICAO lain.")
