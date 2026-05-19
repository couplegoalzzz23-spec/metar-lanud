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

# --- 2. DATABASE LANUD DENGAN SISTEM FALLBACK ---
LANUD_MAP = {
    "Lanud Maimun Saleh - Sabang (WITN)": ["WITN", "WITT"],
    "Lanud Sultan Iskandar Muda - Aceh (WITT)": ["WITT"],
    "Lanud Soewondo - Medan (WIMK)": ["WIMK", "WIMM"],
    "Lanud Sutan Sjahrir - Padang (WIMG)": ["WIMG", "WIEE"],
    "Lanud Roesmin Nurjadin - Pekanbaru (WIBB)": ["WIBB"],
    "Lanud Raja Haji Fisabilillah - Tanjungpinang (WIDN)": ["WIDN", "WIDD"],
    "Lanud Hang Nadim - Batam (WIDD)": ["WIDD", "WIDN"],
    "Lanud Raden Sadjad - Natuna (WION)": ["WION"],
    "Lanud Sri Mulyono Herlambang - Palembang (WIPP)": ["WIPP"],
    "Lanud Radin Inten II - Lampung (WILL)": ["WILL", "WIAT"],
    "Lanud Pangeran M. Bun Yamin - Astra Ksetra (WIAT)": ["WIAT", "WILL"],
    "Lanud Halim Perdanakusuma - Jakarta (WIHH)": ["WIHH", "WIII"],
    "Lanud Atang Sendjaja - Bogor (WIAJ)": ["WIAJ", "WIHH", "WIII"],
    "Lanud Suryadarma - Kalijati (WIAK)": ["WIAK", "WICC", "WIIH"],
    "Lanud Husein Sastranegara - Bandung (WICC)": ["WICC", "WIII"],
    "Lanud Sugiri Sukani - Majalengka (WIER)": ["WIER", "WICN", "WICC"],
    "Lanud Wiriadinata - Tasikmalaya (WICM)": ["WICM", "WICC"],
    "Lanud Jenderal Besar Soedirman - Purbalingga (WICP)": ["WICP", "WARQ"],
    "Lanud Adisutjipto - Yogyakarta (WARJ)": ["WARJ", "WAHH", "WARQ"],
    "Lanud Iswahjudi - Madiun (WARI)": ["WARI", "WARQ", "WARR"],
    "Lanud Abdulrachman Saleh - Malang (WARA)": ["WARA", "WARR"],
    "Lanud Juanda - Surabaya (WARR)": ["WARR"],
    "Lanud I Gusti Ngurah Rai - Bali (WADD)": ["WADD"],
    "Lanud TGKH. M. Zainuddin Abdul Madjid - Lombok (WADL)": ["WADL", "WADD"],
    "Lanud El Tari - Kupang (WATT)": ["WATT"],
    "Lanud Supadio - Pontianak (WIOO)": ["WIOO"],
    "Lanud Harry Hadisoemantri - Singkawang (WIOK)": ["WIOK", "WIOO"],
    "Lanud Iskandar - Pangkalan Bun (WAOI)": ["WAOI", "WAGG"],
    "Lanud Tjilik Riwut - Palangkaraya (WAGG)": ["WAGG", "WAOO"],
    "Lanud Syamsudin Noor - Banjarmasin (WAOO)": ["WAOO"],
    "Lanud Dhomber - Balikpapan (WALL)": ["WALL"],
    "Lanud Anang Busra - Tarakan (WAQQ)": ["WAQQ", "WALL"],
    "Lanud Sultan Hasanuddin - Makassar (WAAA)": ["WAAA"],
    "Lanud Haluoleo - Kendari (WAWW)": ["WAWW", "WAAA"],
    "Lanud Sam Ratulangi - Manado (WAMM)": ["WAMM"],
    "Lanud Pattimura - Ambon (WAPP)": ["WAPP"],
    "Lanud Dominicus Dumatubun - Tual (WAPL)": ["WAPL", "WAPP"],
    "Lanud Ignatius Dewanto - Saumlaki (WAPI)": ["WAPI", "WAPP"],
    "Lanud Leo Wattimena - Morotai (WAMW)": ["WAMW", "WAMT"],
    "Lanud Silas Papare - Jayapura (WAJJ)": ["WAJJ"],
    "Lanud Manuhua - Biak (WABB)": ["WABB"],
    "Lanud Yohanis Kapiyau - Timika (WAYY)": ["WAYY", "WABP"],
    "Lanud J.A. Dimara - Merauke (WAKK)": ["WAKK"],
}

# --- 3. SISTEM KEAMANAN & MESIN PENGAMBIL DATA ---

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

def is_data_fresh(raw_text):
    """FAIL-SAFE KRITIS: Menolak data usang (Cache mati). Mengizinkan toleransi beda hari (cross-midnight)"""
    if not raw_text: return False
    time_match = re.search(r'\b(\d{2})\d{4}Z\b', raw_text)
    if not time_match: return False
    
    data_day = int(time_match.group(1))
    current_utc_day = datetime.utcnow().day
    
    # Toleransi: Hari ini, kemarin (karena beda zona waktu UTC), atau pergantian bulan
    if data_day == current_utc_day or abs(current_utc_day - data_day) <= 1 or abs(current_utc_day - data_day) >= 27:
        return True
        
    return False # REJECT DATA JIKA LEBIH DARI 1-2 HARI!

def fetch_metar_raw(icao):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationalWeatherClient'}
    icao = icao.upper().strip()
    session = get_robust_session()
    
    # 1. SUMBER UTAMA 1: BMKG WEB AVIATION (Paling presisi untuk Indonesia)
    try:
        url = "https://web-aviation.bmkg.go.id/web/metar_speci.php"
        res = session.get(url, headers=headers, timeout=6, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text(separator=" ")
            text = re.sub(r'\s+', ' ', text)
            match = re.search(fr"\b((?:METAR\s+|SPECI\s+)?{icao}\s+\d{{6}}Z\s+.*?)(?=(?:METAR|SPECI|[A-Z]{{4}}\s+\d{{6}}Z|=|$))", text)
            if match:
                raw_metar = match.group(1).strip()
                if not raw_metar.endswith('='): raw_metar += '='
                if is_data_fresh(raw_metar): return raw_metar, "BMKG Pusat"
    except: pass

    # 2. SUMBER UTAMA 2: NOAA TEXT API
    try:
        url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        res = session.get(url, headers=headers, timeout=5)
        if res.status_code == 200 and icao in res.text:
            raw_metar = res.text.strip()
            if is_data_fresh(raw_metar): return raw_metar, "NOAA API"
    except: pass

    # 3. SUMBER CADANGAN 1: NOAA WEB HTML
    try:
        url = f"https://aviationweather.gov/data/metar/?ids={icao}&taf=1"
        res = session.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for block in soup.find_all('code'):
                text = block.get_text().strip()
                if icao in text and ('METAR' in text or 'Z' in text):
                    match = re.search(fr"\b((?:METAR\s+)?{icao}\s+\d{{6}}Z\s+.*?)(?=(?:TAF|=|$))", text)
                    if match:
                        raw_metar = match.group(1).strip()
                        if not raw_metar.endswith('='): raw_metar += '='
                        if is_data_fresh(raw_metar): return raw_metar, "NOAA Web"
    except: pass

    # 4. SUMBER TERAKHIR (LAPIS KE-4): NOAA FTP SERVER (Diamankan dengan is_data_fresh)
    try:
        url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao}.TXT"
        res = session.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            lines = res.text.strip().split('\n')
            if len(lines) > 1 and icao in lines[1]:
                raw_metar = lines[1].strip()
                if not raw_metar.endswith('='): raw_metar += '='
                if is_data_fresh(raw_metar): return raw_metar, "NOAA FTP Server (Verified)"
    except: pass

    return None, None

def fetch_taf_raw(icao):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperationalWeatherClient'}
    icao = icao.upper().strip()
    session = get_robust_session()
    
    # 1. BMKG TAF WEB
    try:
        url = "https://web-aviation.bmkg.go.id/web/taf.php"
        res = session.get(url, headers=headers, timeout=6, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text(separator=" ")
            text = re.sub(r'\s+', ' ', text)
            match = re.search(fr"\b(TAF\s+(?:AMD\s+|COR\s+)?{icao}\s+\d{{6}}Z\s+.*?)(?=TAF\s+(?:AMD\s+|COR\s+)?[A-Z]{{4}}|=|$)", text)
            if match:
                raw_taf = match.group(1).strip()
                if not raw_taf.endswith('='): raw_taf += '='
                if is_data_fresh(raw_taf): return raw_taf
    except: pass

    # 2. NOAA TAF API
    try:
        url = f"https://aviationweather.gov/api/data/taf?ids={icao}&format=raw"
        res = session.get(url, headers=headers, timeout=5)
        if res.status_code == 200 and icao in res.text:
            raw_taf = res.text.strip()
            if is_data_fresh(raw_taf): return raw_taf
    except: pass
    
    # 3. NOAA TAF WEB
    try:
        url = f"https://aviationweather.gov/data/metar/?ids={icao}&taf=1"
        res = session.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for block in soup.find_all('code'):
                text = block.get_text().strip()
                if icao in text and 'TAF' in text:
                    match = re.search(fr"\b(TAF\s+(?:AMD\s+|COR\s+)?{icao}\s+\d{{6}}Z\s+.*?)(?=(?:=|$))", text)
                    if match:
                        raw_taf = match.group(1).strip()
                        if not raw_taf.endswith('='): raw_taf += '='
                        if is_data_fresh(raw_taf): return raw_taf
    except: pass

    # 4. NOAA FTP SERVER
    try:
        url = f"https://tgftp.nws.noaa.gov/data/forecasts/taf/stations/{icao}.TXT"
        res = session.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            lines = res.text.strip().split('\n')
            if len(lines) > 1 and icao in lines[1]:
                raw_taf = lines[1].strip()
                if is_data_fresh(raw_taf): return raw_taf
    except: pass

    return "TAFOR DATA NIL="

def get_data_with_fallback(icao_list):
    for icao in icao_list:
        raw_metar, src = fetch_metar_raw(icao)
        if raw_metar: 
            raw_taf = fetch_taf_raw(icao)
            return raw_metar, raw_taf, src, icao
    return None, None, None, None

def parse_metar(raw, original_icao):
    """Parsing METAR - SINKRONISASI TOTAL 100% SAMA DENGAN SUMBER ASLI"""
    data = {
        "obs_date": datetime.utcnow().strftime('%d'),
        "obs_time": datetime.utcnow().strftime('%H.%M'),
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "tt_td": "NIL", "qnh": "NIL", "qfe": "NIL",
        "trend": "NOSIG", "rmk": "NIL"
    }
    if not raw: return data
    
    # Ambil Tanggal dan Waktu Observasi Asli METAR Raw
    time_match = re.search(r'\b[A-Z]{4}\s+(\d{2})(\d{2})(\d{2})Z\b', raw)
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

    # 1. SURFACE WIND DIRECTION & SPEED
    w = re.search(r'\b(\d{3}|VRB)(\d{2,3})(G\d{2,3})?(KT|MPS)\b', main_part)
    if w:
        gust = w.group(3) if w.group(3) else ""
        unit = w.group(4)
        data["wind"] = f"{w.group(1)}/{w.group(2)}{gust} {unit}"

    # 2. HORIZONTAL VISIBILITY & CAVOK HANDLING
    if "CAVOK" in main_part:
        data["vis"] = "9999 M"
        data["cld"] = "NIL"
        data["wx"] = "NIL"
    else:
        v_match = re.search(r'\b(\d{4})\b', main_part)
        sm_match = re.search(r'\b(\d{1,2})(?:/(\d{1,2}))?SM\b', main_part)
        
        if v_match:
            data["vis"] = f"{v_match.group(1)} M"
        elif sm_match:
            data["vis"] = f"{sm_match.group(0)}"

        # PRESENT WEATHER
        wx_codes = r'(?:VC|MI|BC|PR|DR|BL|SH|TS|FZ|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)'
        all_wx = re.findall(fr'\b([-+]?(?:{wx_codes})+)\b', main_part)
        all_wx = [x for x in all_wx if x not in [original_icao, "TEMPO", "BECMG", "NOSIG"]]
        data["wx"] = " ".join(all_wx) if all_wx else "NIL"

        # CLOUD STRUCTURE FORMATTING
        c_layers = re.findall(r'\b(FEW|SCT|BKN|OVC|NSC|SKC|VV)(\d{3})(CB|TCU)?\b', main_part)
        if c_layers:
            layers_formatted = []
            for t, h, c in c_layers:
                if t in ["NSC", "SKC"]:
                    layers_formatted.append(t)
                else:
                    layers_formatted.append(f"{t} {int(h)*100} FT{'' if not c else ' '+c}")
            data["cld"] = " ".join(layers_formatted)

    # 3. TEMPERATURE
    tt_td = re.search(r'\b(M?\d{2})/(M?\d{2})\b', main_part)
    if tt_td: 
        t_val = tt_td.group(1).replace('M', '-')
        td_val = tt_td.group(2).replace('M', '-')
        data["tt_td"] = f"{t_val}/{td_val}"

    # 4. QNH MURNI TANPA EDIT TEXT
    q = re.search(r'\b(Q|A)(\d{4})\b', main_part)
    if q:
        tipe = q.group(1)
        val = int(q.group(2))
        if tipe == 'Q':
            data["qnh"] = f"{val}"
        elif tipe == 'A':
            inHg = val / 100.0
            data["qnh"] = f"{int(inHg * 33.8639)}"

    # 5. QFE DARI REMARKS
    qfe_match = re.search(r'QFE(\d{3,4})', data["rmk"])
    if qfe_match:
        data["qfe"] = f"{qfe_match.group(1)}"
    else:
        data["qfe"] = "NIL"
    
    return data

# --- 4. ENGINE PDF ---

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
    
    current_month_year = datetime.utcnow().strftime('%m-%Y')
    date_str = f"{data['obs_date']}-{current_month_year}"
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

    # ICAO YANG DICETAK ADALAH ICAO AKTUAL (ANTI-SPOOFING)
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
st.info("Penarikan data METAR real-time dengan Validasi Fail-Safe (Anti Data Kadaluarsa).")

col1, col2 = st.columns([1, 1])

with col1:
    pilihan = st.selectbox("Pilih Pangkalan / Lanud:", list(sorted(LANUD_MAP.keys())))
    icao_list = LANUD_MAP[pilihan]
    display_name = pilihan.split(" (")[0].replace("Lanud ", "")
    generate_btn = st.button("TARIK DATA & GENERATE QAM", use_container_width=True)

with col2:
    st.info("Status Jaringan: Multi-Source Berjenjang (BMKG -> NOAA API -> NOAA Web -> NOAA FTP)")

if generate_btn:
    with st.spinner(f"Menghubungi server untuk {icao_list[0]}..."):
        raw_text, raw_taf, source, found_icao = get_data_with_fallback(icao_list)
        
        if raw_text:
            if found_icao != icao_list[0]:
                st.error(f"⚠️ KESELAMATAN: Data {icao_list[0]} OFFLINE/KADALUARSA pada seluruh sumber. Menampilkan & mencetak cuaca stasiun terdekat/alternatif: {found_icao}.")
            else:
                st.success(f"BERHASIL (Sumber Aktual: {source} - Terverifikasi Real-Time)")
            
            combined_raw_display = f"// RAW METAR DATA ({found_icao})\n{raw_text}\n\n// RAW TAFOR FORECAST DATA ({found_icao})\n{raw_taf}"
            st.code(combined_raw_display)
            
            p_data = parse_metar(raw_text, found_icao)
            pdf_bytes = generate_pdf(p_data, raw_taf, found_icao, display_name)
            
            st.download_button(
                label=f"📥 DOWNLOAD PDF QAM - {found_icao}",
                data=pdf_bytes,
                file_name=f"QAM_{found_icao}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Gagal menarik data! Semua sumber jaringan memutus akses atau hanya menyediakan data usang (kadaluarsa). Coba beberapa saat lagi.")
