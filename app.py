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

# --- 2. DATABASE LANUD (DILENGKAPI ELEVASI AKTUAL DALAM FEET UNTUK PRESISI QFE) ---
LANUD_MAP = {
    "Lanud Halim Perdanakusuma (WIHH)": {"icaos": ["WIHH", "WIII"], "elev_ft": 85},
    "Lanud Atang Sendjaja (WIAJ)": {"icaos": ["WIAJ", "WIHH", "WIII"], "elev_ft": 535},
    "Lanud Suryadarma (WIAK)": {"icaos": ["WIAK", "WICC", "WIIH"], "elev_ft": 380},
    "Lanud Husein Sastranegara (WICC)": {"icaos": ["WICC", "WIII"], "elev_ft": 2436},
    "Lanud Sugiri Sukani (WIER)": {"icaos": ["WIER", "WICN", "WICC"], "elev_ft": 150},
    "Lanud Sutan Sjahrir - Padang (WIMG)": {"icaos": ["WIMG", "WIEE"], "elev_ft": 9}, 
    "Lanud Soewondo - Medan (WIMK)": {"icaos": ["WIMK", "WIMM"], "elev_ft": 90},     
    "Lanud Roesmin Nurjadin (WIBB)": {"icaos": ["WIBB"], "elev_ft": 104},
    "Lanud Supadio (WIOO)": {"icaos": ["WIOO"], "elev_ft": 10},
    "Lanud Sultan Iskandar Muda (WITT)": {"icaos": ["WITT"], "elev_ft": 65},
    "Lanud Sri Mulyono Herlambang (WIPP)": {"icaos": ["WIPP"], "elev_ft": 40},
    "Lanud Radin Inten II (WILL)": {"icaos": ["WILL"], "elev_ft": 284},
    "Lanud Raja Haji Fisabilillah (WIDN)": {"icaos": ["WIDN"], "elev_ft": 58},
    "Lanud Hang Nadim (WIDD)": {"icaos": ["WIDD"], "elev_ft": 125},
    "Lanud Raden Sadjad (WION)": {"icaos": ["WION"], "elev_ft": 6},
    "Lanud Iswahjudi (WARI)": {"icaos": ["WARI", "WARQ", "WARR"], "elev_ft": 360}, 
    "Lanud Abdulrachman Saleh (WARA)": {"icaos": ["WARA", "WARR"], "elev_ft": 1726}, 
    "Lanud Adisutjipto (WARJ)": {"icaos": ["WARJ", "WAHH", "WARQ"], "elev_ft": 350}, 
    "Lanud Juanda (WARR)": {"icaos": ["WARR"], "elev_ft": 9},
    "Lanud Sultan Hasanuddin (WAAA)": {"icaos": ["WAAA"], "elev_ft": 48},
    "Lanud I Gusti Ngurah Rai (WADD)": {"icaos": ["WADD"], "elev_ft": 14},
    "Lanud El Tari (WATT)": {"icaos": ["WATT"], "elev_ft": 335},
    "Lanud Sam Ratulangi (WAMM)": {"icaos": ["WAMM"], "elev_ft": 264},
    "Lanud Syamsudin Noor (WAOO)": {"icaos": ["WAOO"], "elev_ft": 65},
    "Lanud Dhomber (WALL)": {"icaos": ["WALL"], "elev_ft": 12},
    "Lanud Iskandar (WAOI)": {"icaos": ["WAOI"], "elev_ft": 75},
    "Lanud Silas Papare (WAJJ)": {"icaos": ["WAJJ"], "elev_ft": 289},
    "Lanud Manuhua (WABB)": {"icaos": ["WABB"], "elev_ft": 46},
    "Lanud Johanes Kapiyau (WABI)": {"icaos": ["WABI"], "elev_ft": 32},
    "Lanud Pattimura (WAPP)": {"icaos": ["WAPP"], "elev_ft": 13},
    "Lanud Leo Wattimena (WAMW)": {"icaos": ["WAMW"], "elev_ft": 50},
    "Lanud J.A. Dimara (WAKK)": {"icaos": ["WAKK"], "elev_ft": 10},
}

# --- 3. MESIN PENGAMBIL DATA (METAR & TAFOR) ---

def get_robust_session():
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationalWeatherClient'}
    icao = icao.upper().strip()
    session = get_robust_session()
    
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

    try:
        url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw"
        res = session.get(url, headers=headers, timeout=6)
        if res.status_code == 200 and len(res.text.strip()) > 10 and icao in res.text:
            return res.text.strip()
    except: pass

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
    for icao in icao_list:
        raw_metar, src = fetch_metar_raw(icao)
        if raw_metar: 
            raw_taf = fetch_taf_raw(icao)
            return raw_metar, raw_taf, src, icao
    return None, None, None, None

def parse_metar(raw, original_icao, elev_ft):
    """Parsing METAR Presisi Tinggi (Tanpa Dummy Data)"""
    # 1. Menghapus Nilai Default Dummy (Semua diset "NIL" untuk keamanan)
    data = {
        "obs_date": "NIL", "obs_time": "NIL",
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "tt_td": "NIL", "qnh": "NIL", "qfe": "NIL",
        "trend": "NOSIG", "rmk": "NIL"
    }
    if not raw: return data
    
    # 2. Ekstraksi Waktu Riil dari String METAR (Bukan Jam Komputer)
    # Format sandi waktu: "210900Z" (Tanggal 21, Jam 09, Menit 00 UTC)
    time_match = re.search(r'\b(?:[A-Z]{4}\s+)?(\d{2})(\d{2})(\d{2})Z\b', raw)
    if time_match:
        data["obs_date"] = time_match.group(1)
        data["obs_time"] = f"{time_match.group(2)}.{time_match.group(3)}"

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

    # WIND
    w = re.search(r'\b(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT\b', main_part)
    if w:
        gust = w.group(3) if w.group(3) else ""
        data["wind"] = f"{w.group(1)}/{w.group(2)}{gust} KT"

    # VISIBILITY
    v_match = re.search(r'\b(\d{4})\b', main_part)
    if v_match:
        dist = int(v_match.group(1))
        data["vis"] = "10 KM" if dist == 9999 else f"{dist} M"
    elif "CAVOK" in main_part: data["vis"] = "10 KM"

    # WEATHER
    wx_codes = r'(?:VC|MI|BC|PR|DR|BL|SH|TS|FZ|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)'
    all_wx = re.findall(fr'\b([-+]?(?:{wx_codes})+)\b', main_part)
    all_wx = [x for x in all_wx if x not in [original_icao, "TEMPO", "BECMG", "NOSIG"]]
    data["wx"] = " ".join(all_wx) if all_wx else "NIL"

    # CLOUD
    c_layers = re.findall(r'\b(FEW|SCT|BKN|OVC|NSC|SKC)(\d{3})(CB|TCU)?\b', main_part)
    if c_layers:
        data["cld"] = " ".join([f"{t} {int(h)*100} FT{'' if not c else ' '+c}" for t, h, c in c_layers])
    elif "CAVOK" in main_part: data["cld"] = "NIL"

    # TT/TD
    tt_td = re.search(r'\b(M?\d{2})/(M?\d{2})\b', main_part)
    if tt_td: data["tt_td"] = f"{tt_td.group(1).replace('M','-')}/{tt_td.group(2).replace('M','-')}"

    # 3. KALKULASI QNH & QFE (Murni dari sumber aktual / elevasi riil)
    qnh_val = None
    q = re.search(r'\bQ(\d{4})\b', main_part)
    if q:
        qnh_val = int(q.group(1))
        data["qnh"] = f"{qnh_val}/{qnh_val*0.02953:.2f}"

    qfe_match = re.search(r'QFE(\d{3,4})', data["rmk"])
    if qfe_match:
        # Prioritas 1: Ekstrak QFE Aktual dari stasiun observasi
        qfe_val = int(qfe_match.group(1))
        data["qfe"] = f"{qfe_val}/{qfe_val*0.02953:.2f}"
    elif qnh_val is not None:
        # Prioritas 2: Rumus presisi ICAO menggunakan elevasi stasiun riil
        qfe_val = int(round(qnh_val - (elev_ft / 30.0)))
        data["qfe"] = f"{qfe_val}/{qfe_val*0.02953:.2f}"
    
    return data

# --- 4. ENGINE PDF (UPDATED FORMAT) ---

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 11)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True, align='L')
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True, align='L')
        self.ln(6)
        self.set_font("helvetica", 'BU', 12)
        self.cell(0, 6, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", ln=True, align='C')
        self.ln(6)

def generate_pdf(data, raw_taf, icao, name):
    pdf = QAM_PDF()
    pdf.add_page()
    
    pdf.set_font("helvetica", 'B', 10)
    
    # 4. Pencetakan Waktu Ekstraksi Aman 
    # (Bulan/Tahun diambil dari waktu komputer, tapi TANGGAL dan JAM wajib dari METAR)
    current_month_year = datetime.utcnow().strftime('%m-%Y')
    date_str = f"{data['obs_date']}-{current_month_year}" if data['obs_date'] != "NIL" else "NIL"
    time_str = data['obs_time']
    
    pdf.cell(0, 6, f"METEOROLOGICAL OBS AT      DATE {date_str}      TIME {time_str} (UTC)", ln=True)
    pdf.ln(3)
    
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

    def add_fixed_row(label_lines, value_lines, h):
        x = pdf.get_x()
        y = pdf.get_y()
        
        if y + h > 270:
            pdf.add_page()
            x = pdf.get_x()
            y = pdf.get_y()
            
        pdf.rect(x, y, 95, h)
        pdf.rect(x + 95, y, 95, h)
        
        pdf.set_font("helvetica", 'B', 10)
        pdf.set_xy(x + 2, y + 2)
        for line in label_lines:
            pdf.cell(91, 5, line, ln=2)
            
        pdf.set_font("helvetica", '', 10)
        pdf.set_xy(x + 97, y + 2)
        for line in value_lines:
            pdf.cell(91, 5, line, ln=2)
            
        pdf.set_xy(x, y + h)

    add_fixed_row(["AERODROME IDENTIFICATION"], [icao], 10)
    add_fixed_row(["SURFACE WIND DIRECTION, SPEED", "AND SIGNIFICANT VARIATION"], [data['wind']], 12)
    add_fixed_row(["HORIZONTAL VISIBILITY"], [data['vis']], 10)
    add_fixed_row(["RUNWAY VISUAL RANGE"], ["NIL"], 10)
    add_fixed_row(["PRESENT WEATHER"], [data['wx']], 10)
    add_fixed_row(["AMOUNT AND HEIGHT OF BASE", "OF LOW CLOUD"], [data['cld']], 12)
    add_fixed_row(["AIR TEMPERATURE AND", "DEW POINT TEMPERATURE"], [data['tt_td']], 12)
    add_fixed_row(["QNH"], [data['qnh']], 10)
    add_fixed_row(["QFE*"], [data['qfe']], 10)
    
    pdf.set_font("helvetica", '', 10)
    supp_label = "SUPPLEMENTARY\nINFORMATION"
    
    supp_val = f"RMK: {data['rmk']}\nTREND: {data['trend']}\n\nTAFOR:\n{raw_taf}"
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
    
    pdf.ln(8)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(95, 5, "TIME OF ISSUE ............................ (UTC)", ln=0)
    pdf.cell(95, 5, "OBSERVER ........................................", ln=1, align='R')
    pdf.cell(95, 5, "*ON REQUEST", ln=1)
    
    return bytes(pdf.output())

# --- 5. INTERFACE DASHBOARD ---

st.title("✈️ TNI AU QAM Generator")
st.info("Sistem Penarikan Data METAR/TAF Real-Time Berstandar ICAO.")

col1, col2 = st.columns([1.2, 1])

with col1:
    # Menggunakan UI pencarian agar lebih aman dan anti typo
    pilihan = st.selectbox(
        "📍 Pencarian Pangkalan / Lanud:", 
        options=list(sorted(LANUD_MAP.keys())),
        index=0,
        help="💡 Ketik nama Lanud/Pangkalan untuk mencari secara cepat."
    )
    
    icao_list = LANUD_MAP[pilihan]["icaos"]
    elev_ft = LANUD_MAP[pilihan]["elev_ft"]
    display_name = pilihan.split(" (")[0].replace("Lanud ", "")
    
    st.write("") 
    generate_btn = st.button("🚀 TARIK DATA & GENERATE QAM", use_container_width=True, type="primary")

with col2:
    st.info("Status Jaringan: Multi-Source (BMKG/NOAA/Nearby)")
    st.success(f"**Target Operasi:** {display_name}\n\n**ICAO:** `{icao_list[0]}` | **Elevasi:** `{elev_ft} ft`")

if generate_btn:
    with st.spinner(f"Menghubungi server untuk {icao_list[0]}..."):
        raw_text, raw_taf, source, found_icao = get_data_with_fallback(icao_list)
        
        if raw_text:
            if found_icao != icao_list[0]:
                st.warning(f"Data {icao_list[0]} Offline. Menggunakan data stasiun terdekat: {found_icao}")
            
            st.success(f"BERHASIL (Sumber Aktual: {source})")
            
            combined_raw_display = f"// RAW METAR DATA ({found_icao})\n{raw_text}\n\n// RAW TAFOR FORECAST DATA ({found_icao})\n{raw_taf}"
            st.code(combined_raw_display)
            
            # Memasukkan argumen elevasi (elev_ft) agar perhitungan engine akurat
            p_data = parse_metar(raw_text, icao_list[0], elev_ft)
            pdf_bytes = generate_pdf(p_data, raw_taf, icao_list[0], display_name)
            
            # Nama file diamankan menggunakan timestamp file dibuat, bukan observasi cuaca (ini aman untuk penamaan file)
            st.download_button(
                label=f"📥 DOWNLOAD PDF QAM - {icao_list[0]}",
                data=pdf_bytes,
                file_name=f"QAM_{icao_list[0]}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Semua server (Utama & Terdekat) tidak merespon. Coba beberapa saat lagi.")
