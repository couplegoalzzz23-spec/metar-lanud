import streamlit as st
import requests
from fpdf import FPDF
from datetime import datetime
import re
from bs4 import BeautifulSoup

# --- 1. KONFIGURASI SISTEM ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️", layout="wide")

# --- 2. DATABASE LANUD LENGKAP (KOOPSUD I, II, III) ---
LANUD_DB = {
    # KOOPSUD I
    "Lanud Halim Perdanakusuma (WIHH)": "WIHH",
    "Lanud Atang Sendjaja (WIAJ)": "WIAJ",
    "Lanud Suryadarma (WIAK)": "WIAK",
    "Lanud Roesmin Nurjadin (WIBB)": "WIBB",
    "Lanud Supadio (WIOO)": "WIOO",
    "Lanud Sultan Iskandar Muda (WITT)": "WITT",
    "Lanud Soewondo (WIMK)": "WIMK",
    "Lanud Sutan Sjahrir (WIMG)": "WIMG",
    "Lanud Sri Mulyono Herlambang (WIPP)": "WIPP",
    "Lanud Radin Inten II (WILL)": "WILL",
    "Lanud Maimun Saleh (WITN)": "WITN",
    "Lanud Raja Haji Fisabilillah (WIDN)": "WIDN",
    "Lanud Hang Nadim (WIDD)": "WIDD",
    "Lanud Husein Sastranegara (WICC)": "WICC",
    "Lanud Sugiri Sukani (WIER)": "WIER",
    "Lanud Wiriadinata (WIIE)": "WIIE",
    "Lanud Harry Hadisoemantri (WIOP)": "WIOP",
    "Lanud Raden Sadjad (WION)": "WION",
    # KOOPSUD II
    "Lanud Iswahjudi (WARI)": "WARI",
    "Lanud Abdulrachman Saleh (WARA)": "WARA",
    "Lanud Sultan Hasanuddin (WAAA)": "WAAA",
    "Lanud Adisutjipto (WARJ)": "WARJ",
    "Lanud Juanda (WARR)": "WARR",
    "Lanud I Gusti Ngurah Rai (WADD)": "WADD",
    "Lanud El Tari (WATT)": "WATT",
    "Lanud Sam Ratulangi (WAMM)": "WAMM",
    "Lanud Syamsudin Noor (WAOO)": "WAOO",
    "Lanud Dhomber (WALL)": "WALL",
    "Lanud Iskandar (WAOI)": "WAOI",
    "Lanud Anang Busra (WAIL)": "WAIL",
    "Lanud J.B. Soedirman (WICP)": "WICP",
    "Lanud Muljono (WARR)": "WARR",
    # KOOPSUD III
    "Lanud Silas Papare (WAJJ)": "WAJJ",
    "Lanud Manuhua (WABB)": "WABB",
    "Lanud Johanes Kapiyau (WABI)": "WABI",
    "Lanud Pattimura (WAPP)": "WAPP",
    "Lanud Leo Wattimena (WAMW)": "WAMW",
    "Lanud J.A. Dimara (WAKK)": "WAKK",
    "Lanud Dumatubun (WAPL)": "WAPL",
}

# --- 3. MESIN PENGAMBIL DATA ---

def fetch_metar_valid(icao):
    headers = {'User-Agent': 'Mozilla/5.0'}
    # Sumber 1: BMKG
    url_bmkg = f"https://web-aviation.bmkg.go.id/web/metar_speci.php?i={icao}"
    try:
        response = requests.get(url_bmkg, headers=headers, timeout=12, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            all_text = soup.get_text(separator=" ")
            match = re.search(fr"({icao}\s\d{{6}}Z\s.*?)(?==|$)", all_text)
            if match: return match.group(1).strip(), "BMKG"
    except: pass

    # Sumber 2: NOAA
    url_noaa = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
    try:
        response = requests.get(url_noaa, headers=headers, timeout=10)
        if response.status_code == 200 and len(response.text) > 15:
            return response.text.strip(), "NOAA"
    except: pass
    return None, None

def parse_metar(raw):
    """Parsing METAR secara presisi sesuai format QAM"""
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", 
        "cld": "NIL", "tt_td": "NIL", "qnh": "1013 / 29.92", 
        "qfe": "1012 / 29.88", "trend": "NOSIG", "rmk": "NIL"
    }
    if not raw: return data
    
    # 1. WIND
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w: data["wind"] = f"{w.group(1)} / {w.group(2)} KT"

    # 2. VISIBILITY
    if "CAVOK" in raw:
        data["vis"] = "10 KM"
    else:
        v_match = re.search(r'\s(\d{4})\s', raw)
        if v_match:
            dist = int(v_match.group(1))
            data["vis"] = "10 KM" if dist == 9999 else f"{dist} M"

    # 3. WEATHER (Perbaikan Non-Capturing Group untuk menghindari TypeError)
    wx_codes = r'(?:VC|MI|BC|PR|DR|BL|SH|TS|FZ|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)'
    all_wx = re.findall(fr'\s([-+]?(?:{wx_codes})+)\s', raw)
    if all_wx:
        data["wx"] = " ".join(all_wx)
    else:
        data["wx"] = "NIL"

    # 4. CLOUD (Mendukung CB/TCU)
    c_layers = re.findall(r'(FEW|SCT|BKN|OVC|NSC|SKC)(\d{3})(CB|TCU)?', raw)
    if c_layers:
        formatted = []
        for typ, hgt, char in c_layers:
            h_val = f"{int(hgt)*100} FT"
            char_val = f" {char}" if char else ""
            formatted.append(f"{typ}{char_val} {h_val}")
        data["cld"] = " ".join(formatted)
    elif "CAVOK" in raw:
        data["cld"] = "NIL"

    # 5. TT/TD
    tt_td_match = re.search(r'(\d{2})/(\d{2})', raw)
    if tt_td_match:
        data["tt_td"] = f"{tt_td_match.group(1)} / {tt_td_match.group(2)}"

    # 6. QNH & QFE (mbs / ins)
    q_match = re.search(r'Q(\d{4})', raw)
    if q_match:
        qnh_mb = int(q_match.group(1))
        qnh_ins = qnh_mb * 0.02953
        qfe_mb = qnh_mb - 4 # Koreksi QFE rata-rata (disesuaikan stasiun)
        qfe_ins = qfe_mb * 0.02953
        data["qnh"] = f"{qnh_mb} / {qnh_ins:.2f}"
        data["qfe"] = f"{qfe_mb} / {qfe_ins:.2f}"

    # 7. REMARKS
    rmk_match = re.search(r'RMK\s(.*)', raw)
    if rmk_match:
        data["rmk"] = rmk_match.group(1)

    # 8. TREND
    if "NOSIG" in raw: data["trend"] = "NOSIG"
    elif "TEMPO" in raw: data["trend"] = "TEMPO"
    elif "BECMG" in raw: data["trend"] = "BECMG"

    return data

# --- 4. ENGINE PDF ---

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(8)

def create_pdf_file(data, icao, name):
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

    rows = [
        ("WIND", data['wind']),
        ("VISIBILITY", data['vis']),
        ("WEATHER", data['wx']),
        ("CLOUD", data['cld']),
        ("TT/TD", data['tt_td']),
        ("QNH", data['qnh']),
        ("QFE", data['qfe']),
        ("REMARKS", data['rmk']),
        ("TREND", data['trend']),
    ]

    for label, val in rows:
        pdf.set_font("helvetica", 'B', 11)
        pdf.cell(35, 8, label, border=0)
        pdf.cell(5, 8, ":", border=0)
        pdf.set_font("helvetica", '', 11)
        pdf.cell(0, 8, str(val), border=0, ln=True)
    
    pdf.ln(10)
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- 5. INTERFACE DASHBOARD ---

st.title("✈️ TNI AU QAM Generator")
st.info("Sistem ini mengekstrak data METAR secara real-time dari BMKG & NOAA.")

col1, col2 = st.columns([1, 1])

with col1:
    # Mengurutkan nama Lanud secara alfabetis untuk kemudahan navigasi
    sorted_lanuds = dict(sorted(LANUD_DB.items()))
    pilihan = st.selectbox("Pilih Pangkalan / Lanud:", list(sorted_lanuds.keys()))
    target_icao = LANUD_DB[pilihan]
    target_name = pilihan.split(" (")[0].replace("Lanud ", "")
    generate_btn = st.button("TARIK DATA & GENERATE QAM", use_container_width=True)

with col2:
    st.info("Status Jaringan: BMKG (Primary), NOAA (Secondary)")

if generate_btn:
    with st.spinner(f"Sinkronisasi data {target_icao}..."):
        raw_metar, sumber = fetch_metar_valid(target_icao)
        
        if raw_metar:
            st.success(f"DATA VALID DITEMUKAN (Sumber: {sumber})")
            st.code(raw_metar, language="bash")
            
            p_data = parse_metar(raw_metar)
            
            st.markdown(f"**Preview Hasil Parsing {target_icao}:**")
            st.text(f"WEATHER: {p_data['wx']}\nCLOUD: {p_data['cld']}\nQNH: {p_data['qnh']}")
            
            pdf_out = create_pdf_file(p_data, target_icao, target_name)
            
            st.download_button(
                label=f"📥 DOWNLOAD PDF QAM - {target_icao}",
                data=pdf_out,
                file_name=f"QAM_{target_icao}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error(f"Gagal menarik data. ICAO {target_icao} mungkin sedang offline atau tidak mempublikasikan METAR.")
