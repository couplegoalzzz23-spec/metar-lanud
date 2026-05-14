import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re
from bs4 import BeautifulSoup

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️", layout="centered")

# --- 2. DATABASE LANUD (25+ Pangkalan Utama) ---
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
        if match:
            return match.group(1).strip(), "BMKG"
    except:
        pass

    # Sumber 2: NOAA
    try:
        url_noaa = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        res = requests.get(url_noaa, headers=headers, timeout=10)
        if res.status_code == 200 and len(res.text) > 10:
            return res.text.strip(), "NOAA"
    except:
        pass

    return None, None

def parse_metar(raw):
    """Parsing METAR sesuai kebutuhan format MET REPORT (QAM)"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", 
        "cld": "NIL", "tt_td": "NIL", "qnh": "1013", 
        "trend": "NOSIG", "rmk": "NIL"
    }
    if not raw: return data
    
    # WIND
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w: data["wind"] = f"{w.group(1)}/{w.group(2)}KT"
    
    # VISIBILITY
    if "CAVOK" in raw:
        data["vis"] = "10 KM"
        data["cld"] = "NIL"
    else:
        v_match = re.search(r'\s(\d{4})\s', raw)
        if v_match:
            dist = int(v_match.group(1))
            data["vis"] = f"{dist//1000} KM" if dist >= 1000 else f"{dist} M"
        
        # CLOUD
        c_match = re.search(r'([A-Z]{3}\d{3})', raw)
        if c_match: data["cld"] = c_match.group(1)

    # WEATHER
    wx_match = re.search(r'\s([-+]?[A-Z]{2,4})\s', raw)
    if wx_match: data["wx"] = wx_match.group(1)
    
    # TT/TD
    tt_td_match = re.search(r'(\d{2})/(\d{2})', raw)
    if tt_td_match:
        data["tt_td"] = f"{tt_td_match.group(1)}°C/{tt_td_match.group(2)}°C"
    
    # QNH
    q_match = re.search(r'Q(\d{4})', raw)
    if q_match: data["qnh"] = q_match.group(1)

    return data

# --- 4. FORMAT PDF QAM MABES AU ---

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(10)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT (QAM)", align='C', ln=True)
        self.ln(5)

def create_qam_pdf(data, icao, name):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=11)
    
    # Perhitungan Tekanan
    qnh = int(data['qnh'])
    qfe = qnh - 1 # Selisih standar mb
    
    # Mapping Data ke Format Contoh
    rows = [
        ("MET REPORT (QAM)", ""),
        (f"LANUD {name.upper()} ({icao})", ""),
        ("DATE", datetime.now().strftime("%d/%m/%Y")),
        ("TIME", f"{datetime.utcnow().strftime('%H.%M')} UTC"),
        ("-" * 40, "-" * 40), # Pembatas
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

    for label, val in rows:
        if val == "":
            pdf.set_font("helvetica", 'B', 11)
            pdf.cell(0, 8, label, ln=True)
        elif label.startswith("-"):
            pdf.cell(0, 5, label, ln=True)
        else:
            pdf.set_font("helvetica", '', 11)
            pdf.cell(50, 8, label, border=0)
            pdf.cell(10, 8, ":", border=0)
            pdf.cell(0, 8, str(val), border=0, ln=True)
    
    pdf.ln(15)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- 5. TAMPILAN APLIKASI ---

st.title("✈️ QAM Generator - TNI AU")
st.write("Format Data berdasarkan Standar MET REPORT (QAM)")

pilih_lanud = st.selectbox("Pilih Pangkalan:", list(LANUD_DB.keys()))
icao_code = LANUD_DB[pilih_lanud]
lanud_name = pilih_lanud.split(" (")[0].replace("Lanud ", "")

if st.button("GENERATE REPORT"):
    with st.spinner("Mensinkronisasi data cuaca..."):
        raw_text, source = fetch_metar(icao_code)
        
        if raw_text:
            st.success(f"Data Berhasil Ditarik (Sumber: {source})")
            st.text_area("Original METAR:", raw_text, height=70)
            
            parsed_data = parse_metar(raw_text)
            pdf_bytes = create_qam_pdf(parsed_data, icao_code, lanud_name)
            
            st.download_button(
                label="📥 Download PDF QAM",
                data=pdf_bytes,
                file_name=f"QAM_{icao_code}_{datetime.now().strftime('%d%m%y_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Gagal mendapatkan data. Pastikan koneksi internet stabil atau cek kode ICAO.")
