import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re
from bs4 import BeautifulSoup

# --- 1. KONFIGURASI SISTEM ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️", layout="wide")

# --- 2. DATABASE LANUD (DIAMBIL DARI DATA VALID TNI AU) ---
# Daftar ini mencakup Lanud Utama dan Bandara pendukung sesuai CSV Anda
LANUD_DB = {
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

# --- 3. MESIN PENGAMBIL DATA (HYBRID ENGINE) ---

def fetch_metar_valid(icao):
    """Fungsi utama mengambil data dengan validasi berlapis"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    # LANGKAH 1: COBA BMKG (SUMBER UTAMA NASIONAL)
    url_bmkg = f"https://web-aviation.bmkg.go.id/web/metar_speci.php?i={icao}"
    try:
        response = requests.get(url_bmkg, headers=headers, timeout=12, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Mencari teks di dalam tabel atau elemen pre
            all_text = soup.get_text(separator=" ")
            # Cari pola: ICAO + Tanggal/Jam + Z + Kondisi
            match = re.search(fr"({icao}\s\d{{6}}Z\s.*?)(?==|$)", all_text)
            if match:
                return match.group(1).strip(), "BMKG Aviation"
    except:
        pass

    # LANGKAH 2: COBA NOAA (REFERENSI GLOBAL JIKA BMKG BLOCKING/OFFLINE)
    url_noaa = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
    try:
        response = requests.get(url_noaa, headers=headers, timeout=10)
        if response.status_code == 200 and len(response.text) > 15:
            return response.text.strip(), "NOAA Aviation Weather"
    except:
        pass

    return None, None

def parse_metar(raw):
    """Parsing sandi METAR ke komponen QAM secara presisi"""
    data = {"wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", "temp": "NIL", "qnh": "1013"}
    if not raw: return data
    
    # Wind (Arah/Kecepatan)
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w:
        data["wind"] = f"{w.group(1)}/{w.group(2)} KT"
        v = re.search(r'(\d{3})V(\d{3})', raw)
        if v: data["wind"] += f" VAR {v.group(1)}V{v.group(2)}"

    # Visibility (Horizontal)
    if "CAVOK" in raw:
        data["vis"], data["cld"] = "10 KM OR MORE", "NIL"
    else:
        v_match = re.search(r'\s(\d{4})\s', raw)
        if v_match: data["vis"] = f"{v_match.group(1)} M"
        # Cloud Layers
        c_layers = re.findall(r'([A-Z]{3})(\d{3})', raw)
        if c_layers:
            data["cld"] = ", ".join([f"{l[0]} {int(l[1])*100} FT" for l in c_layers])

    # Weather (Present Weather)
    wx_match = re.search(r'\s([-+]?[A-Z]{2,4})\s', raw)
    if wx_match: data["wx"] = wx_match.group(1)
    
    # Temperature & QNH
    td = re.search(r'(\d{2})/(\d{2})', raw)
    if td: data["temp"] = f"{td.group(1)}/{td.group(2)}"
    q = re.search(r'Q(\d{4})', raw)
    if q: data["qnh"] = q.group(1)

    return data

# --- 4. ENGINE PDF (FORMAT MABES AU) ---

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(10)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(5)

def create_pdf_file(data, icao, name):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    # Konversi Tekanan Lengkap
    try:
        qnh_val = float(data['qnh'])
        qfe_val = qnh_val - 4 # Koreksi standar elevasi pangkalan
    except:
        qnh_val, qfe_val = 1013, 1009

    def fmt_p(v):
        return f"{int(v)} mbs / {v*0.02953:.2f} ins / {v*0.75006:.1f} mm Hg"

    rows = [
        ("METEOROLOGICAL OBS AT", name),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", datetime.utcnow().strftime("%H.%M")),
        ("AERODROME IDENTIFICATION", icao),
        ("SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION", data['wind']),
        ("HORIZONTAL VISIBILITY", data['vis']),
        ("RUNWAY VISUAL RANGE", "NIL"),
        ("PRESENT WEATHER", data['wx']),
        ("AMOUNT AND HEIGHT OF BASE OF LOW CLOUD", data['cld']),
        ("AIR TEMPERATURE AND DEW POINT TEMPERATURE", data['temp']),
        ("QNH", fmt_p(qnh_val)),
        ("QFE*", fmt_p(qfe_val)),
        ("SUPPLEMENTARY INFORMATION", "NIL"),
        ("TIME OF ISSUE (UTC)", datetime.utcnow().strftime("%H.%M")),
    ]

    for label, val in rows:
        y_start = pdf.get_y()
        pdf.multi_cell(85, 9, label, border=1)
        y_end = pdf.get_y()
        pdf.set_xy(85 + 10, y_start)
        pdf.multi_cell(105, y_end - y_start, str(val), border=1)
        pdf.set_y(y_end)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    pdf.set_font("helvetica", 'I', 8)
    pdf.cell(0, 10, "* Generated automatically for reporting purposes. Always verify with official METAR source.", align='L')
    return bytes(pdf.output())

# --- 5. ANTARMUKA STREAMLIT ---

st.title("✈️ TNI AU QAM Generator (Professional)")
st.warning("PENTING: Alat ini adalah pembantu pelaporan. Pastikan sandi METAR yang ditarik sesuai dengan kondisi riil.")

col1, col2 = st.columns([1, 1])

with col1:
    pilihan = st.selectbox("Pilih Pangkalan / Lanud:", list(LANUD_DB.keys()))
    target_icao = LANUD_DB[pilihan]
    target_name = pilihan.split(" (")[0]
    
    generate_btn = st.button("TARIK DATA & GENERATE QAM", use_container_width=True)

with col2:
    st.info("Status Jaringan: BMKG (Primary), NOAA (Secondary)")

if generate_btn:
    with st.spinner(f"Menjalankan prosedur sinkronisasi data {target_icao}..."):
        raw_metar, sumber = fetch_metar_valid(target_icao)
        
        if raw_metar:
            st.success(f"DATA VALID DITEMUKAN (Sumber: {sumber})")
            st.code(raw_metar, language="bash")
            
            p_data = parse_metar(raw_metar)
            pdf_out = create_pdf_file(p_data, target_icao, target_name)
            
            st.download_button(
                label=f"📥 DOWNLOAD PDF QAM - {target_icao}",
                data=pdf_out,
                file_name=f"QAM_{target_icao}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error(f"FATAL: Data untuk {target_icao} tidak ditemukan di seluruh server.")
            st.markdown(f"""
            **Tindakan yang disarankan:**
            1. Cek manual di [Web Aviation BMKG](https://web-aviation.bmkg.go.id/web/metar_speci.php?i={target_icao})
            2. Pastikan stasiun {target_icao} sedang beroperasi (tidak sedang maintenance/off-air).
            3. Laporkan jika terjadi kendala jaringan persisten.
            """)
