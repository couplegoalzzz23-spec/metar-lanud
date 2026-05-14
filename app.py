import streamlit as st
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import re

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="QAM Generator TNI AU", page_icon="✈️")

# --- 2. FUNGSI AMBIL & PARSE DATA ---
def get_metar_data(icao):
    """Mengambil data dari Aviation Weather API"""
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
    """Ekstraksi data METAR ke format QAM"""
    data = {"wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", "temp": "NIL", "qnh": "1013"}
    if not raw: return data
    
    # Wind & Variation
    w = re.search(r'(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT', raw)
    if w:
        data["wind"] = f"{w.group(1)}/{w.group(2)} KT"
        v = re.search(r'(\d{3})V(\d{3})', raw)
        if v: data["wind"] += f" VAR {v.group(1)}V{v.group(2)}"
    
    # Visibility
    if "CAVOK" in raw: data["vis"] = "10 KM OR MORE"
    else:
        v = re.search(r'\s(\d{4})\s', raw)
        if v: data["vis"] = f"{v.group(1)} M"

    # Cloud
    c = re.findall(r'([A-Z]{3})(\d{3})', raw)
    if c: data["cld"] = ", ".join([f"{l[0]} {int(l[1])*100} FT" for l in c])

    # Weather (Present Weather)
    wx = re.search(r'\s([-+]?[A-Z]{2,4})\s', raw)
    if wx: data["wx"] = wx.group(1)

    # Temp & QNH
    td = re.search(r'(\d{2})/(\d{2})', raw)
    if td: data["temp"] = f"{td.group(1)}/{td.group(2)}"
    q = re.search(r'Q(\d{4})', raw)
    if q: data["qnh"] = q.group(1)

    return data

# --- 3. FORMAT PDF QAM MABES AU ---
class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 10)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True)
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True)
        self.ln(8)
        self.set_font("helvetica", 'B', 12)
        self.cell(0, 7, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", align='C', ln=True)
        self.ln(5)

def generate_qam_pdf(data, icao, nama_lanud):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    # Kalkulasi Tekanan (mbs, ins, mm Hg)
    qnh = float(data['qnh'])
    qfe = qnh - 4 
    def fmt_p(v):
        return f"{int(v)} mbs / {v*0.02953:.2f} ins / {v*0.75006:.1f} mm Hg"

    time_now = datetime.utcnow().strftime("%H.%M")
    
    # Baris Tabel Sesuai PDF Mabes AU
    rows = [
        ("METEOROLOGICAL OBS AT", nama_lanud),
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
        curr_y = pdf.get_y()
        # Kolom Kiri (Label)
        pdf.multi_cell(85, 8, label, border=1)
        end_y = pdf.get_y()
        # Kolom Kanan (Data)
        pdf.set_xy(85 + 10, curr_y)
        pdf.multi_cell(105, end_y - curr_y, str(val), border=1)
        pdf.set_y(end_y)
    
    pdf.ln(10)
    pdf.cell(0, 10, "OBSERVER: ........................................", align='R', ln=True)
    return bytes(pdf.output())

# --- 4. TAMPILAN APLIKASI ---
st.title("✈️ QAM Generator")
st.write("Format Resmi Dinas Pengembangan Operasi TNI AU")

# Load Database Lanud
try:
    df = pd.read_csv('lanud_tni_au_indonesia.csv')
    options = {f"{r['Nama_Lanud']} ({r['ICAO']})": r for _, r in df.iterrows()}
    pilihan = st.selectbox("Pilih Pangkalan TNI AU:", list(options.keys()))
    target_icao = options[pilihan]['ICAO']
    target_name = options[pilihan]['Nama_Lanud']
except:
    st.error("File 'lanud_tni_au_indonesia.csv' tidak ditemukan.")
    target_icao = st.text_input("Atau Masukkan Kode ICAO Manual (WIBB, WIII, dll):").upper()
    target_name = target_icao

if st.button("Tarik Data & Generate PDF"):
    with st.spinner(f"Menghubungi server untuk {target_icao}..."):
        raw_metar = get_metar_raw(target_icao)
        
        if raw_metar:
            st.success("Data Berhasil Ditemukan")
            st.code(raw_metar) # Menampilkan sandi METAR asli untuk validasi petugas
            
            p_data = parse_metar(raw_metar)
            pdf_out = generate_qam_pdf(p_data, target_icao, target_name)
            
            st.download_button(
                label="📥 Unduh PDF QAM",
                data=pdf_out,
                file_name=f"QAM_{target_icao}_{datetime.now().strftime('%H%M')}.pdf",
                mime="application/pdf"
            )
        else:
            st.error("Gagal menarik data. Kemungkinan stasiun sedang offline atau ICAO salah.")
            st.warning("Catatan: Beberapa pangkalan militer murni memang tidak mempublikasikan datanya ke internet.")
