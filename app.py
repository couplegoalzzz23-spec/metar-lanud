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

# --- 3. LOGIKA PARSING METAR (PENYEMPURNAAN) ---

def parse_metar_pro(raw, icao):
    data = {
        "wind": "NIL", "vis": "NIL", "wx": "NIL", 
        "cld": "NIL", "tt_td": "NIL", "qnh_mb": "1013", 
        "qnh_ins": "29.92", "qfe_mb": "1012", "qfe_ins": "29.88",
        "trend": "NOSIG", "rmk": "NIL"
    }
    if not raw: return data

    # 1. WIND
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w: data["wind"] = f"{w.group(1)} / {w.group(2)} KT"

    # 2. VISIBILITY
    v_match = re.search(r'\s(\d{4})\s', raw)
    if v_match:
        data["vis"] = f"{v_match.group(1)} M"
    elif "CAVOK" in raw:
        data["vis"] = "10 KM"

    # 3. WEATHER (Kunci Perbaikan: Menghindari ICAO)
    # Daftar fenomena cuaca resmi METAR
    wx_patterns = r'(VC|MI|BC|PR|DR|BL|SH|TS|FZ|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)'
    # Cari yang mengandung pola cuaca dan BUKAN ICAO yang sedang dipilih
    matches = re.findall(fr'\b([-+]?{wx_patterns}+)\b', raw)
    valid_wx = [m for m in matches if m != icao]
    if valid_wx:
        data["wx"] = " ".join(valid_wx)

    # 4. CLOUD (Mendukung CB dan Multiple Layers)
    c_matches = re.findall(r'(FEW|SCT|BKN|OVC|NSC|SKC)(\d{3})(CB|TCU)?', raw)
    if c_matches:
        cld_parts = []
        for c in c_matches:
            type_c = f" {c[2]}" if c[2] else ""
            cld_parts.append(f"{c[0]}{type_c} {int(c[1])*100} FT")
        data["cld"] = " ".join(cld_parts)
    elif "CAVOK" in raw:
        data["cld"] = "NIL"

    # 5. TT/TD
    tt_td_match = re.search(r'(\d{2})/(\d{2})', raw)
    if tt_td_match:
        data["tt_td"] = f"{tt_td_match.group(1)} / {tt_td_match.group(2)}"

    # 6. PRESSURE (QNH & QFE Calculation)
    q_match = re.search(r'Q(\d{4})', raw)
    if q_match:
        q_mb = int(q_match.group(1))
        q_ins = q_mb * 0.02953
        data["qnh_mb"] = str(q_mb)
        data["qnh_ins"] = f"{q_ins:.2f}"
        
        # QFE (Estimasi standar -4 mb dari QNH atau sesuai elevasi)
        qfe_mb = q_mb - 1 
        qfe_ins = qfe_mb * 0.02953
        data["qfe_mb"] = str(qfe_mb)
        data["qfe_ins"] = f"{qfe_ins:.2f}"

    # 7. TREND
    if "NOSIG" in raw: data["trend"] = "NOSIG"
    elif "TEMPO" in raw: data["trend"] = "TEMPO"
    elif "BECMG" in raw: data["trend"] = "BECMG"

    # 8. REMARKS
    rmk_match = re.search(r'RMK\s(.*)', raw)
    if rmk_match: data["rmk"] = rmk_match.group(1)

    return data

# --- 4. ENGINE PDF (FORMAT SESUAI REVISI USER) ---

class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(10)

def create_qam_report(data, icao, name):
    pdf = QAM_PDF()
    pdf.add_page()
    
    # Judul
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 7, "MET REPORT (QAM)", ln=True)
    pdf.cell(0, 7, f"LANUD {name.upper()} ({icao})", ln=True)
    
    # Identitas Waktu
    pdf.set_font("helvetica", '', 11)
    pdf.cell(30, 7, "DATE", border=0)
    pdf.cell(5, 7, ":", border=0)
    pdf.cell(0, 7, datetime.now().strftime("%d/%m/%Y"), ln=True)
    
    pdf.cell(30, 7, "TIME", border=0)
    pdf.cell(5, 7, ":", border=0)
    pdf.cell(0, 7, f"{datetime.utcnow().strftime('%H.%M')} UTC", ln=True)
    
    pdf.cell(0, 5, "=" * 45, ln=True)
    pdf.ln(2)

    # Isi Laporan (Key-Value)
    rows = [
        ("WIND", data['wind']),
        ("VISIBILITY", data['vis']),
        ("WEATHER", data['wx']),
        ("CLOUD", data['cld']),
        ("TT / TD", data['tt_td']),
        ("QNH", f"{data['qnh_mb']} / {data['qnh_ins']}"),
        ("QFE", f"{data['qfe_mb']} / {data['qfe_ins']}"),
        ("REMARKS", data['rmk']),
        ("TREND", data['trend']),
    ]

    for label, val in rows:
        pdf.set_font("helvetica", 'B', 11)
        pdf.cell(35, 8, label, border=0)
        pdf.set_font("helvetica", '', 11)
        pdf.cell(5, 8, ":", border=0)
        pdf.cell(0, 8, str(val), border=0, ln=True)
    
    pdf.ln(15)
    pdf.set_font("helvetica", 'B', 11)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    
    return bytes(pdf.output())

# --- 5. INTERFACE UTAMA ---

def fetch_raw_metar(icao):
    """Fungsi helper tarik data dari BMKG/NOAA"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        url = f"https://web-aviation.bmkg.go.id/web/metar_speci.php?i={icao}"
        res = requests.get(url, headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text(separator=" ")
        match = re.search(fr"({icao}\s\d{{6}}Z\s.*?)(?==|$)", text)
        if match: return match.group(1).strip()
    except: pass
    
    try:
        url_noaa = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=raw"
        res = requests.get(url_noaa, headers=headers, timeout=10)
        if res.status_code == 200: return res.text.strip()
    except: pass
    return None

st.title("✈️ Mil-Aero QAM Generator Pro")
st.markdown("---")

pilihan = st.selectbox("Pilih Pangkalan TNI AU:", list(LANUD_DB.keys()))
icao_target = LANUD_DB[pilihan]
nama_target = pilihan.split(" (")[0].replace("Lanud ", "")

if st.button("TARIK DATA & GENERATE QAM", use_container_width=True):
    with st.spinner(f"Sinkronisasi METAR {icao_target}..."):
        raw_metar = fetch_raw_metar(icao_target)
        
        if raw_metar:
            st.info(f"**Raw METAR:** `{raw_metar}`")
            
            # Proses Data
            parsed_data = parse_metar_pro(raw_metar, icao_target)
            
            # Preview di Layar
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**WIND:** {parsed_data['wind']}")
                st.write(f"**WEATHER:** {parsed_data['wx']}")
                st.write(f"**TT / TD:** {parsed_data['tt_td']}")
            with col2:
                st.write(f"**QNH:** {parsed_data['qnh_mb']} / {parsed_data['qnh_ins']}")
                st.write(f"**CLOUD:** {parsed_data['cld']}")
            
            # Create PDF
            pdf_out = create_qam_report(parsed_data, icao_target, nama_target)
            
            st.download_button(
                label="📥 DOWNLOAD PDF QAM RESMI",
                data=pdf_out,
                file_name=f"QAM_{icao_target}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.error("Data tidak ditemukan di server BMKG maupun NOAA.")
