import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re
from bs4 import BeautifulSoup

# --- 1. KONFIGURASI SISTEM ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️", layout="wide")

# --- 2. DATABASE LANUD DENGAN SISTEM FALLBACK ---
# Format: "Nama": [ICAO_Utama, ICAO_Alternatif_1, ICAO_Alternatif_2]
LANUD_MAP = {
    "Lanud Halim Perdanakusuma (WIHH)": ["WIHH", "WIII"],
    "Lanud Atang Sendjaja (WIAJ)": ["WIAJ", "WIHH", "WIII"],
    "Lanud Suryadarma (WIAK)": ["WIAK", "WICC", "WIIH"],
    "Lanud Husein Sastranegara (WICC)": ["WICC"],
    "Lanud Sugiri Sukani (WIER)": ["WIER", "WICN"],
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

# --- 3. MESIN PENGAMBIL DATA ---

def fetch_metar_raw(icao):
    """Fungsi dasar penarikan data dengan pembersihan HTML dan Multi-Endpoint"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 1. Coba NOAA (AWC API)
    try:
        url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200 and len(res.text.strip()) > 10 and icao in res.text:
            return res.text.strip(), "NOAA (API)"
    except: pass

    # 2. Coba NOAA (TGFTP Text Server - Backup kuat untuk stasiun militer)
    try:
        url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao.upper()}.TXT"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            lines = res.text.strip().split('\n')
            if len(lines) > 1 and icao in lines[1]:
                return lines[1].strip(), "NOAA (FTP)"
    except: pass

    # 3. Coba BMKG dengan BeautifulSoup parsing HTML
    try:
        url = f"https://web-aviation.bmkg.go.id/web/metar_speci.php?i={icao}"
        res = requests.get(url, headers=headers, timeout=5, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            clean_text = soup.get_text(separator=" ")
            match = re.search(fr"({icao}\s\d{{6}}Z\s.*?(?:=|$))", clean_text)
            if match: 
                return match.group(1).replace("\n", " ").strip(), "BMKG"
    except: pass
    
    return None, None

def get_data_with_fallback(icao_list):
    """Mencoba setiap ICAO dalam daftar sampai ditemukan data"""
    for icao in icao_list:
        raw, src = fetch_metar_raw(icao)
        if raw: return raw, src, icao
    return None, None, None

def parse_metar(raw, original_icao):
    """Parsing METAR secara presisi dengan pemisahan Main Body, Trend, dan Remarks"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "tt_td": "NIL", "qnh": "1013/29.92", "qfe": "1012/29.88",
        "trend": "NOSIG", "rmk": "NIL"
    }
    if not raw: return data
    
    # Isolasi bagian REMARKS (RMK)
    main_part = raw
    if "RMK" in raw:
        main_part, rmk_part = raw.split("RMK", 1)
        data["rmk"] = rmk_part.strip()
        
    # Isolasi bagian TREND (TEMPO / BECMG / NOSIG)
    trend_search = re.search(r'\b(TEMPO|BECMG|NOSIG)\b(.*)', main_part)
    if trend_search:
        trend_type = trend_search.group(1)
        trend_rest = trend_search.group(2).strip()
        data["trend"] = "NOSIG" if trend_type == "NOSIG" else f"{trend_type} {trend_rest}".strip()
        main_part = main_part[:trend_search.start()].strip()
    
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
    wx_match = re.findall(r'\b([-+]?(?:VC|MI|BC|PR|DR|BL|SH|TS|FZ)?[A-Z]{2})\b', main_part)
    valid_wx_codes = ['RA', 'DZ', 'SN', 'SG', 'IC', 'PL', 'GR', 'GS', 'UP', 'BR', 'FG', 'FU', 'VA', 'DU', 'SA', 'HZ', 'PY', 'PO', 'SQ', 'FC', 'SS', 'DS', 'TS', 'SH']
    actual_wx = [w for w in wx_match if any(code in w for code in valid_wx_codes) and w not in ["NOSIG", "TEMPO", "BECMG", "CAVOK", original_icao]]
    data["wx"] = " ".join(actual_wx) if actual_wx else "NIL"

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
        data["qfe"] = f"{val-5}/{(val-5)*0.02953:.2f}"
    
    return data

# --- 4. ENGINE PDF ---

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(8)

def generate_pdf(data, icao, name):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 7, "MET REPORT (QAM)", ln=True)
    pdf.cell(0, 7, f"LANUD {name.upper()} ({icao})", ln=True)
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 7, f"DATE    : {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 7, f"TIME    : {datetime.utcnow().strftime('%H.%M')} UTC", ln=True)
    pdf.cell(0, 5, "=" * 40, ln=True)
    pdf.ln(2)

    fields = [("WIND", data['wind']), ("VISIBILITY", data['vis']), ("WEATHER", data['wx']),
              ("CLOUD", data['cld']), ("TT/TD", data['tt_td']), ("QNH", data['qnh']),
              ("QFE", data['qfe']), ("REMARKS", data['rmk']), ("TREND", data['trend'])]

    for label, val in fields:
        pdf.set_font("helvetica", 'B', 11); pdf.cell(35, 8, label + " :", border=0)
        pdf.set_font("helvetica", '', 11); pdf.cell(0, 8, str(val), ln=True)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
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
        raw_text, source, found_icao = get_data_with_fallback(icao_list)
        
        if raw_text:
            if found_icao != icao_list[0]:
                st.warning(f"Data {icao_list[0]} Offline. Menggunakan data stasiun terdekat: {found_icao}")
            
            st.success(f"BERHASIL (Sumber: {source})")
            st.code(raw_text)
            
            p_data = parse_metar(raw_text, icao_list[0])
            pdf_bytes = generate_pdf(p_data, icao_list[0], display_name)
            
            st.download_button(
                label=f"📥 DOWNLOAD PDF QAM - {icao_list[0]}",
                data=pdf_bytes,
                file_name=f"QAM_{icao_list[0]}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Semua server (Utama & Terdekat) tidak merespon. Coba beberapa saat lagi.")
