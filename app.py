import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re
from bs4 import BeautifulSoup

# --- 1. KONFIGURASI SISTEM ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️", layout="wide")

# --- 2. DATABASE LANUD DENGAN SISTEM FALLBACK MILITER & SIPIL ---
# Format: "Nama": [ICAO_Utama, ICAO_Alternatif/Terdekat]
LANUD_MAP = {
    "Lanud Halim Perdanakusuma (WIHH)": ["WIHH", "WIII"],
    "Lanud Atang Sendjaja (WIAJ)": ["WIAJ", "WIHH", "WIII"],
    "Lanud Suryadarma (WIAK)": ["WIAK", "WICA", "WICC", "WIHH"],
    "Lanud Husein Sastranegara (WICC)": ["WICC", "WICA", "WIHH"],
    "Lanud Sugiri Sukani (WIER)": ["WIER", "WICA", "WICC"],
    "Lanud Sutan Sjahrir - Padang (WIMG)": ["WIMG", "WIEE"], 
    "Lanud Soewondo - Medan (WIMK)": ["WIMK", "WIMM"],     
    "Lanud Roesmin Nurjadin (WIBB)": ["WIBB", "WIIK"],
    "Lanud Supadio (WIOO)": ["WIOO"],
    "Lanud Sultan Iskandar Muda (WITT)": ["WITT"],
    "Lanud Sri Mulyono Herlambang (WIPP)": ["WIPP", "WIPL"],
    "Lanud Radin Inten II (WILL)": ["WILL", "WIII"],
    "Lanud Raja Haji Fisabilillah (WIDN)": ["WIDN", "WIDD"],
    "Lanud Hang Nadim (WIDD)": ["WIDD"],
    "Lanud Raden Sadjad (WION)": ["WION", "WIDD"],
    "Lanud Iswahjudi (WARI)": ["WARI", "WARQ", "WARR"],   # Fallback ke Solo / Juanda
    "Lanud Abdulrachman Saleh (WARA)": ["WARA", "WARR"], # Fallback ke Juanda Surabaya
    "Lanud Adisutjipto (WARJ)": ["WARJ", "WAHI", "WARQ"], # Fallback ke YIA / Solo
    "Lanud Juanda (WARR)": ["WARR"],
    "Lanud Sultan Hasanuddin (WAAA)": ["WAAA"],
    "Lanud I Gusti Ngurah Rai (WADD)": ["WADD"],
    "Lanud El Tari (WATT)": ["WATT"],
    "Lanud Sam Ratulangi (WAMM)": ["WAMM"],
    "Lanud Syamsudin Noor (WAOO)": ["WAOO"],
    "Lanud Dhomber (WALL)": ["WALL"],
    "Lanud Iskandar (WAOI)": ["WAOI", "WAOO"],
    "Lanud Silas Papare (WAJJ)": ["WAJJ"],
    "Lanud Manuhua (WABB)": ["WABB", "WAJJ"],
    "Lanud Johanes Kapiyau (WABI)": ["WABI", "WABB"],
    "Lanud Pattimura (WAPP)": ["WAPP"],
    "Lanud Leo Wattimena (WAMW)": ["WAMW", "WAMM"],
    "Lanud J.A. Dimara (WAKK)": ["WAKK"],
}

# --- 3. MESIN PENGAMBIL DATA ---

def fetch_metar_raw(icao):
    """Fungsi dasar penarikan data dari BMKG & NOAA dengan Element-Level Isolation"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # Jalur Utama: BMKG Web Aviation
    try:
        url = "https://web-aviation.bmkg.go.id/web/metar_speci.php"
        res = requests.get(url, headers=headers, timeout=8, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Pindai baris demi baris elemen HTML secara terisolasi untuk menghindari kontaminasi teks stasiun lain
            for element in soup.find_all(['tr', 'td', 'div', 'p']):
                text = ' '.join(element.get_text(separator=' ').split())
                match = re.search(fr"\b({icao}\s+\d{{6}}Z\s+.*?)(?==|$)", text, re.IGNORECASE)
                if match:
                    return match.group(1).strip().upper(), "BMKG"
            
            # Cadangan BMKG Scan jika struktur web berubah
            full_text = ' '.join(soup.get_text(separator=' ').split())
            match_fallback = re.search(fr"\b({icao}\s+\d{{6}}Z\s+[^=]{{1,180}})", full_text, re.IGNORECASE)
            if match_fallback:
                return match_fallback.group(1).strip().upper(), "BMKG"
    except: pass
    
    # Jalur Cadangan: NOAA API resmi
    try:
        url = f"https://aviationweather.gov/api/data/metar?ids={icao}"
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200 and len(res.text) > 15:
            clean_noaa = ' '.join(res.text.split())
            match = re.search(fr"\b({icao}\s+\d{{6}}Z\s+.*?)(?=TAF|\b[A-Z]{{4}}\b|$)", clean_noaa, re.IGNORECASE)
            if match:
                return match.group(1).strip().upper(), "NOAA"
            return clean_noaa.strip().upper(), "NOAA"
    except: pass
    
    return None, None

def get_data_with_fallback(icao_list):
    """Mencoba setiap ICAO dalam daftar sampai ditemukan data"""
    for icao in icao_list:
        raw, src = fetch_metar_raw(icao)
        if raw: return raw, src, icao
    return None, None, None

def parse_metar(raw, original_icao):
    """Parsing METAR secara presisi dengan penanganan Case-Insensitive"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", 
        "tt_td": "NIL", "qnh": "1013 / 29.92", "qfe": "1012 / 29.88",
        "trend": "NOSIG", "rmk": "NIL"
    }
    if not raw: return data
    
    # Memastikan semua teks diubah menjadi huruf besar agar tidak miss saat pembacaan parameter
    raw = raw.upper()
    
    # 1. WIND (Termasuk Gusting data)
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w: 
        gust = f"G{w.group(3)}" if w.group(3) else ""
        data["wind"] = f"{w.group(1)} / {w.group(2)}{gust} KT"

    # 2. VISIBILITY
    v_match = re.search(r'\s(\d{4})\s', raw)
    if v_match:
        dist = int(v_match.group(1))
        data["vis"] = "10 KM" if dist == 9999 else f"{dist} M"
    elif "CAVOK" in raw: data["vis"] = "10 KM"

    # 3. WEATHER
    wx_codes = r'(?:VC|MI|BC|PR|DR|BL|SH|TS|FZ|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)'
    all_wx = re.findall(fr'\s([-+]?(?:{wx_codes})+)\s', raw)
    data["wx"] = " ".join(all_wx) if all_wx else "NIL"

    # 4. CLOUD
    c_layers = re.findall(r'(FEW|SCT|BKN|OVC|NSC|SKC)(\d{3})(CB|TCU)?', raw)
    if c_layers:
        data["cld"] = " ".join([f"{t}{' '+c if c else ''} {int(h)*100} FT" for t, h, c in c_layers])
    elif "CAVOK" in raw: data["cld"] = "NIL"

    # 5. TT/TD
    tt_td = re.search(r'(\d{2})/(\d{2})', raw)
    if tt_td: data["tt_td"] = f"{tt_td.group(1)} / {tt_td.group(2)}"

    # 6. QNH/QFE
    q = re.search(r'Q(\d{4})', raw)
    if q:
        val = int(q.group(1))
        data["qnh"] = f"{val} / {val*0.02953:.2f}"
        data["qfe"] = f"{val-5} / {(val-5)*0.02953:.2f}"

    # 7. REMARKS & TREND
    rmk = re.search(r'RMK\s(.*)', raw)
    if rmk: data["rmk"] = rmk.group(1).strip()
    
    for t_word in ["NOSIG", "TEMPO", "BECMG"]:
        if t_word in raw:
            if t_word == "NOSIG":
                data["trend"] = "NOSIG"
            else:
                t_match = re.search(fr'\b({t_word}\s+.*)', raw)
                if t_match: data["trend"] = t_match.group(1).strip()
            break
    
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

# --- 5. INTERFACE DASHBOARD (DESIGN PERMANEN) ---

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
