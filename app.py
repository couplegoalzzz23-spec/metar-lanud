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

# --- 2. DATABASE LANUD DENGAN SISTEM FALLBACK YANG SUDAH DIOPTIMALKAN ---
LANUD_MAP = {
    "Lanud Halim Perdanakusuma (WIHH)": ["WIHH", "WIII"],
    "Lanud Atang Sendjaja (WIAJ)": ["WIAJ", "WIHH", "WIII"],
    "Lanud Suryadarma (WIAK)": ["WIAK", "WICC", "WIIH"],
    "Lanud Husein Sastranegara (WICC)": ["WICC", "WIII"],
    "Lanud Sugiri Sukani (WIER)": ["WIER", "WICN", "WICC"],
    "Lanud Sutan Sjahrir - Padang (WIMG)": ["WIMG", "WIEE"], 
    "Lanud Soewondo - Medan (WIMK)": ["WIMK", "WIMM"],     
    "Lanud Roesmin Nurjadin (WIBB)": ["WIBB"],
    "Lanud Supadio (WIOO)": ["WIOO"],
    "Lanud Sultan Iskandar Muda (WITT)": ["WITT"],
    "Lanud Sri Mulyono Herlambang (WIPP)": ["WIPP"],
    "Lanud Radin Inten II (WILL)": ["WILL"],
    "Lanud Raja Haji Fisabilillah (WIDN)": ["WIDN"],
    "Lanud Hang Nadim (WIDD)": ["WIDD"],
    "Lanud Raden Sadjad (WION)": ["WION"],
    "Lanud Iswahjudi (WARI)": ["WARI", "WARQ", "WARR"], 
    "Lanud Abdulrachman Saleh (WARA)": ["WARA", "WARR"], 
    "Lanud Adisutjipto (WARJ)": ["WARJ", "WAHH", "WARQ"], 
    "Lanud Juanda (WARR)": ["WARR"],
    "Lanud Sultan Hasanuddin (WAAA)": ["WAAA"],
    "Lanud I Gusti Ngurah Rai (WADD)": ["WADD"],
    "Lanud El Tari (WATT)": ["WATT"],
    "Lanud Sam Ratulangi (WAMM)": ["WAMM"],
    "Lanud Syamsudin Noor (WAOO)": ["WAOO"],
    "Lanud Dhomber (WALL)": ["WALL"],
    "Lanud Iskandar (WAOI)": ["WAOI"],
    "Lanud Silas Papare (WAJJ)": ["WAJJ"],
    "Lanud Manuhua (WABB)": ["WABB"],
    "Lanud Johanes Kapiyau (WABI)": ["WABI"],
    "Lanud Pattimura (WAPP)": ["WAPP"],
    "Lanud Leo Wattimena (WAMW)": ["WAMW"],
    "Lanud J.A. Dimara (WAKK)": ["WAKK"],
}

# --- 3. MESIN PENGAMBIL DATA (METAR & TAFOR) ---

def get_robust_session():
    """Membuat session HTTP yang tahan banting dengan auto-retry jika jaringan lambat"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def fetch_metar_raw(icao):
    """Mencari data METAR dari multi-source secara agresif"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationalWeatherClient'}
    icao = icao.upper().strip()
    session = get_robust_session()
    
    try:
        url = "https://web-aviation.bmkg.go.id/web/metar_speci.php"
        res = session.get(url, headers=headers, timeout=7, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            clean_html_text = " ".join(soup.get_text().split())
            match = re.search(fr"\b({icao}\s+\d{{6}}Z\s+.*?)(?=[A-Z]{{4}}\s+\d{{6}}Z|=|$)", clean_html_text)
            if match:
                raw_metar = match.group(1).strip()
                if not raw_metar.endswith('='): raw_metar += '='
                return raw_metar, "BMKG Pusat"
    except: pass

    try:
        url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        res = session.get(url, headers=headers, timeout=6)
        if res.status_code == 200 and len(res.text.strip()) > 10 and icao in res.text:
            return res.text.strip(), "NOAA API"
    except: pass

    try:
        url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao}.TXT"
        res = session.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            lines = res.text.strip().split('\n')
            if len(lines) > 1 and icao in lines[1]:
                return lines[1].strip(), "NOAA Server"
    except: pass
    
    return None, None

def fetch_taf_raw(icao):
    """Mencari data TAFOR (Terminal Aerodrome Forecast) dari multi-source"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationalWeatherClient'}
    icao = icao.upper().strip()
    session = get_robust_session()
    
    # 1. Coba BMKG TAF Center
    try:
        url = "https://web-aviation.bmkg.go.id/web/taf.php"
        res = session.get(url, headers=headers, timeout=7, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            clean_html_text = " ".join(soup.get_text().split())
            match = re.search(fr"\b(TAF\s+(?:AMD\s+|COR\s+)?{icao}\s+\d{{6}}Z\s+.*?)(?=TAF\s+(?:AMD\s+|COR\s+)?[A-Z]{{4}}|=|$)", clean_html_text)
            if match:
                raw_taf = match.group(1).strip()
                if not raw_taf.endswith('='): raw_taf += '='
                return raw_taf
    except: pass

    # 2. Coba NOAA TAF API
    try:
        url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw"
        res = session.get(url, headers=headers, timeout=6)
        if res.status_code == 200 and len(res.text.strip()) > 10 and icao in res.text:
            return res.text.strip()
    except: pass

    # 3. Coba NOAA TAF FTP Text Server
    try:
        url = f"https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/{icao}.TXT"
        res = session.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            lines = res.text.strip().split('\n')
            if len(lines) > 1 and icao in lines[1]:
                return lines[1].strip()
    except: pass

    return "TAFOR DATA NIL="

def get_data_with_fallback(icao_list):
    """Mengecek list ICAO stasiun utama sampai stasiun cadangan hingga data didapatkan"""
    for icao in icao_list:
        raw_metar, src = fetch_metar_raw(icao)
        if raw_metar: 
            raw_taf = fetch_taf_raw(icao)
            return raw_metar, raw_taf, src, icao
    return None, None, None, None

def parse_metar(raw, original_icao):
    """Parsing METAR presisi tinggi dengan pembersihan karakter ilegal"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "tt_td": "NIL", "qnh": "1013/29.92", "qfe": "NIL", # QFE default diubah menjadi NIL
        "trend": "NOSIG", "rmk": "NIL"
    }
    if not raw: return data
    
    main_part = raw
    if "RMK" in raw:
        main_part, rmk_part = raw.split("RMK", 1)
        data["rmk"] = rmk_part.replace("=", "").strip()
        
    trend_search = re.search(r'\b(TEMPO|BECMG|NOSIG)\b(.*)', main_part)
    if trend_search:
        trend_type = trend_search.group(1)
        trend_rest = trend_search.group(2).replace("=", "").strip()
        data["trend"] = "NOSIG" if trend_type == "NOSIG" else f"{trend_type} {trend_rest}".strip()
        main_part = main_part[:trend_search.start()].strip()
    
    main_part = main_part.replace("=", "").strip()

    # 1. WIND
    w = re.search(r'\b(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT\b', main_part)
    if w:
        gust = w.group(3) if w.group(3) else ""
        data["wind"] = f"{w.group(1)}/{w.group(2)}{gust} KT"

    # 2. VISIBILITY
    v_match = re.search(r'\b(\d{4})\b', main_part)
    if v_match:
        dist = int(v_match.group(1))
        data["vis"] = "10 KM" if dist == 9999 else f"{dist} M"
    elif "CAVOK" in main_part: data["vis"] = "10 KM"

    # 3. WEATHER
    wx_codes = r'(?:VC|MI|BC|PR|DR|BL|SH|TS|FZ|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)'
    all_wx = re.findall(fr'\b([-+]?(?:{wx_codes})+)\b', main_part)
    all_wx = [x for x in all_wx if x not in [original_icao, "TEMPO", "BECMG", "NOSIG"]]
    data["wx"] = " ".join(all_wx) if all_wx else "NIL"

    # 4. CLOUD
    c_layers = re.findall(r'\b(FEW|SCT|BKN|OVC|NSC|SKC)(\d{3})(CB|TCU)?\b', main_part)
    if c_layers:
        data["cld"] = " ".join([f"{t} {int(h)*100} FT{'' if not c else ' '+c}" for t, h, c in c_layers])
    elif "CAVOK" in main_part: data["cld"] = "NIL"

    # 5. TT/TD
    tt_td = re.search(r'\b(M?\d{2})/(M?\d{2})\b', main_part)
    if tt_td: data["tt_td"] = f"{tt_td.group(1).replace('M','-')}/{tt_td.group(2).replace('M','-')}"

    # 6. QNH/QFE
    q = re.search(r'\bQ(\d{4})\b', main_part)
    if q:
        val = int(q.group(1))
        data["qnh"] = f"{val}/{val*0.02953:.2f}"
        data["qfe"] = "NIL"  # DIKOSONGKAN: Kalkulasi statis dihapus untuk menghindari kesalahan operasional
    
    return data

# --- 4. ENGINE PDF (UPDATED FORMAT) ---

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 11)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True, align='L')
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True, align='L')
        self.ln(6)
        self.set_font("helvetica", 'BU', 12)
        # Typo "TAE OFF" pada dokumen fisik diperbaiki menjadi "TAKE OFF" agar sesuai kaidah penerbangan
        self.cell(0, 6, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", ln=True, align='C')
        self.ln(6)

def generate_pdf(data, raw_taf, icao, name):
    pdf = QAM_PDF()
    pdf.add_page()
    
    pdf.set_font("helvetica", 'B', 10)
    date_str = datetime.utcnow().strftime('%d-%m-%Y')
    time_str = datetime.utcnow().strftime('%H.%M')
    
    # Header Date & Time
    pdf.cell(0, 6, f"METEOROLOGICAL OBS AT      DATE {date_str}      TIME {time_str} (UTC)", ln=True)
    pdf.ln(3)
    
    # Fungsi Helper untuk menghitung prediksi baris (wrap text) di kolom kanan
    def get_multicell_lines(text, max_width):
        lines = 0
        for paragraph in text.split('\n'):
            words = paragraph.split(' ')
            current_line = ""
            for word in words:
                if pdf.get_string_width(current_line + word + " ") > max_width:
                    lines += 1
                    current_line = word + " "
                else:
                    current_line += word + " "
            lines += 1
        return lines

    # Fungsi Helper pembuatan baris 2-kolom dengan bentuk tabel (bounding-box)
    def add_fixed_row(label_lines, value_lines, h):
        x = pdf.get_x()
        y = pdf.get_y()
        
        # Handler Jika Kertas Habis (Pindah Halaman Baru)
        if y + h > 270:
            pdf.add_page()
            x = pdf.get_x()
            y = pdf.get_y()
            
        # Draw Border
        pdf.rect(x, y, 95, h)
        pdf.rect(x + 95, y, 95, h)
        
        # Kolom Label Kiri
        pdf.set_font("helvetica", 'B', 10)
        pdf.set_xy(x + 2, y + 2)
        for line in label_lines:
            pdf.cell(91, 5, line, ln=2)
            
        # Kolom Value Kanan
        pdf.set_font("helvetica", '', 10)
        pdf.set_xy(x + 97, y + 2)
        for line in value_lines:
            pdf.cell(91, 5, line, ln=2)
            
        pdf.set_xy(x, y + h)

    # Konstruksi Tabel sesuai Format Dokumen yang Diunggah
    add_fixed_row(["AERODROME IDENTIFICATION"], [icao], 10)
    add_fixed_row(["SURFACE WIND DIRECTION, SPEED", "AND SIGNIFICANT VARIATION"], [data['wind']], 12)
    add_fixed_row(["HORIZONTAL VISIBILITY"], [data['vis']], 10)
    add_fixed_row(["RUNWAY VISUAL RANGE"], ["NIL"], 10)
    add_fixed_row(["PRESENT WEATHER"], [data['wx']], 10)
    add_fixed_row(["AMOUNT AND HEIGHT OF BASE", "OF LOW CLOUD"], [data['cld']], 12)
    add_fixed_row(["AIR TEMPERATURE AND", "DEW POINT TEMPERATURE"], [data['tt_td']], 12)
    add_fixed_row(["QNH"], [data['qnh']], 10)
    add_fixed_row(["QFE*"], [data['qfe']], 10)
    
    # Row Khusus: Supplementary Info (Tinggi menyesuaikan panjang TAFOR/Remarks)
    pdf.set_font("helvetica", '', 10)
    supp_label = "SUPPLEMENTARY\nINFORMATION"
    
    # Gabungkan Remarks, Trend, dan TAFOR menjadi satu kotak di bagian bawah tabel
    supp_val = f"RMK: {data['rmk']}\nTREND: {data['trend']}\n\nTAFOR:\n{raw_taf}"
    
    # Kalkulasi tinggi baris sesuai isi TAFOR yang ditarik secara dinamis
    h_supp = max(15, get_multicell_lines(supp_val, 91) * 5 + 4)
    
    x = pdf.get_x()
    y = pdf.get_y()
    
    if y + h_supp > 270:
        pdf.add_page()
        x = pdf.get_x()
        y = pdf.get_y()
        
    pdf.rect(x, y, 95, h_supp)
    pdf.rect(x + 95, y, 95, h_supp)
    
    pdf.set_font("helvetica", 'B', 10)
    pdf.set_xy(x + 2, y + 2)
    pdf.multi_cell(91, 5, supp_label)
    
    pdf.set_font("helvetica", '', 10)
    pdf.set_xy(x + 97, y + 2)
    pdf.multi_cell(91, 5, supp_val)
    
    pdf.set_xy(x, y + h_supp)
    
    # Footer Section (Tanda Tangan & Keterangan)
    pdf.ln(8)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(95, 5, "TIME OF ISSUE ............................ (UTC)", ln=0)
    pdf.cell(95, 5, "OBSERVER ........................................", ln=1, align='R')
    pdf.cell(95, 5, "*ON REQUEST", ln=1)
    
    return bytes(pdf.output())

# --- 5. INTERFACE DASHBOARD ---

st.title("✈️ TNI AU QAM Generator")
st.info("Penarikan data METAR real-time dengan sistem Fallback Terdekat.")

col1, col2 = st.columns([1, 1])

with col1:
    pilihan = st.selectbox("Pilih Pangkalan / Lanud:", list(sorted(LANUD_MAP.keys())))
    icao_list = LANUD_MAP[pilihan]
    display_name = pilihan.split(" (")[0].replace("Lanud ", "")
    generate_btn = st.button("TARIK DATA & GENERATE QAM", use_container_width=True)

with col2:
    st.info("Status Jaringan: Multi-Source (BMKG/NOAA/Nearby)")

if generate_btn:
    with st.spinner(f"Menghubungi server untuk {icao_list[0]}..."):
        raw_text, raw_taf, source, found_icao = get_data_with_fallback(icao_list)
        
        if raw_text:
            if found_icao != icao_list[0]:
                st.warning(f"Data {icao_list[0]} Offline. Menggunakan data stasiun terdekat: {found_icao}")
            
            st.success(f"BERHASIL (Sumber: {source})")
            
            # TAFOR dan METAR digabungkan dalam satu kotak kode bawaan agar struktur layout dashboard tetap presisi
            combined_raw_display = f"// RAW METAR DATA\n{raw_text}\n\n// RAW TAFOR FORECAST DATA\n{raw_taf}"
            st.code(combined_raw_display)
            
            p_data = parse_metar(raw_text, icao_list[0])
            pdf_bytes = generate_pdf(p_data, raw_taf, icao_list[0], display_name)
            
            st.download_button(
                label=f"📥 DOWNLOAD PDF QAM - {icao_list[0]}",
                data=pdf_bytes,
                file_name=f"QAM_{icao_list[0]}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Semua server (Utama & Terdekat) tidak merespon. Coba beberapa saat lagi.")
