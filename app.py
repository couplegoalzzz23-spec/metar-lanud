import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️")

# --- 2. DATABASE LANUD (HARDCODED) ---
# Daftar ini diambil langsung dari data yang Anda berikan
LANUD_DB = {
    "Lanud Halim Perdanakusuma (WIHH)": "WIHH",
    "Lanud Atang Sendjaja (WIAJ)": "WIAJ",
    "Lanud Soewondo (WIMK)": "WIMK",
    "Lanud Roesmin Nurjadin (WIBB)": "WIBB",
    "Lanud Supadio (WIOO)": "WIOO",
    "Lanud Iskandar (WAOI)": "WAOI",
    "Lanud Adisutjipto (WARJ)": "WARJ",
    "Lanud Abdulrachman Saleh (WARA)": "WARA",
    "Lanud Iswahyudi (WARI)": "WARI",
    "Lanud Juanda (WARR)": "WARR",
    "Lanud Husein Sastranegara (WICC)": "WICC",
    "Lanud Sulaiman (WICN)": "WICN",
    "Lanud Wiriadinata (WICD)": "WICD",
    "Lanud Sultan Hasanuddin (WAAA)": "WAAA",
    "Lanud Sam Ratulangi (WAMM)": "WAMM",
    "Lanud Anang Busra (WAQQ)": "WAQQ",
    "Lanud Dhomber (WALL)": "WALL",
    "Lanud Syamsudin Noor (WAOO)": "WAOO",
    "Lanud Silas Papare (WAJJ)": "WAJJ",
    "Lanud Manuhua (WABB)": "WABB",
    "Lanud Johanes Kapiyau (WABI)": "WABI",
    "Lanud Pattimura (WAPP)": "WAPP",
    "Lanud Leo Wattimena (WAMW)": "WAMW",
    "Lanud El Tari (WATT)": "WATT",
    "Lanud Harry Hadisoemantri (WIOO)": "WIOO",
    "Lanud Maimun Saleh (WITN)": "WITN",
    "Lanud SMH Palembang (WIPP)": "WIPP",
    "Lanud Radin Inten II (WILL)": "WILL",
    "Lanud Sugiri Sukani (WICW)": "WICW",
    "Lanud Wirasaba (WPDU)": "WPDU",
}

# --- 3. FUNGSI LOGIKA CUACA ---
def get_metar_raw(icao):
    """Mengambil data METAR dari Aviation Weather"""
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
    """Parsing sandi METAR ke komponen QAM"""
    data = {"wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", "temp": "NIL", "qnh": "1013"}
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

# --- 4. FORMAT PDF QAM MABES AU ---
class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(8)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(5)

def generate_pdf(data, icao, name):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    qnh = float(data['qnh'])
    qfe = qnh - 4 # Estimasi koreksi elevasi
    def fmt_p(v):
        return f"{int(v)} mbs / {v*0.02953:.2f} ins / {v*0.75006:.1f} mm Hg"
    
    time_now = datetime.utcnow().strftime("%H.%M")
    
    rows = [
        ("METEOROLOGICAL OBS AT", name),
        ("DATE", datetime.now().strftime("%d-%m-%Y")),
        ("TIME (UTC)", time_now),
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
        ("TIME OF ISSUE (UTC)", time_now),
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

# --- 5. TAMPILAN UTAMA ---
st.title("✈️ QAM Generator TNI AU")
st.write("Sesuai Standar Dinas Pengembangan Operasi")

# Dropdown Lanud
pilihan = st.selectbox("Pilih Pangkalan TNI AU:", list(LANUD_DB.keys()))
target_icao = LANUD_DB[pilihan]
target_name = pilihan.split(" (")[0]

if st.button("Generate QAM"):
    with st.spinner(f"Menarik data METAR {target_icao}..."):
        raw = get_metar_raw(target_icao)
        
        if raw:
            st.success("Data ditemukan!")
            st.code(raw)
            parsed_data = parse_metar(raw)
            pdf_bytes = generate_pdf(parsed_data, target_icao, target_name)
            
            st.download_button(
                label="📥 Download PDF QAM",
                data=pdf_bytes,
                file_name=f"QAM_{target_icao}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf"
            )
        else:
            st.error(f"Data METAR untuk {target_icao} tidak tersedia di server publik.")
            st.info("Pangkalan militer tertentu mungkin tidak mempublikasikan data cuacanya ke internet.")
