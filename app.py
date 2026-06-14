import streamlit as st
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from fpdf import FPDF
from datetime import datetime, timezone
import re
from bs4 import BeautifulSoup
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly.express as px

# =====================================
# 1. KONFIGURASI SISTEM UTAMA
# =====================================
st.set_page_config(page_title="Tactical Weather Ops — BMKG", page_icon="✈️", layout="wide")

# =====================================
# 2. CSS — MILITARY STYLE + RADAR ANIMATION
# =====================================
st.markdown("""
<style>
body {background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", "Roboto Mono", monospace;}
h1, h2, h3, h4 {color: #a9df52; text-transform: uppercase; letter-spacing: 1px;}
section[data-testid="stSidebar"] {background-color: #111; color: #d0d3ca;}
.stButton>button {background-color: #1a2a1f; color: #a9df52; border: 1px solid #3f4f3f; border-radius: 8px; font-weight: bold;}
.stButton>button:hover {background-color: #2b3b2b; border-color: #a9df52;}
div[data-testid="stMetricValue"] {color: #a9df52 !important;}
.radar {position: relative; width: 160px; height: 160px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%), radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%); background-size: 20px 20px; border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 20px #33ff55;}
.radar:before {content: ""; position: absolute; top: 0; left: 0; width: 50%; height: 2px; background: linear-gradient(90deg, #33ff55, transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite;}
@keyframes sweep {from { transform: rotate(0deg); } to { transform: rotate(360deg); }}
hr, .stDivider {border-top: 1px solid #2f3a2f;}
</style>
""", unsafe_allow_html=True)

# =====================================
# 3. DATABASE LANUD, ADM1, & KONSTANTA
# =====================================
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

# Mapping Provinsi ke Kode ADM1 (BPS/BMKG)
PROVINCE_ADM1_MAP = {
    "Aceh (11)": "11", "Sumatera Utara (12)": "12", "Sumatera Barat (13)": "13", 
    "Riau (14)": "14", "Jambi (15)": "15", "Sumatera Selatan (16)": "16", 
    "Bengkulu (17)": "17", "Lampung (18)": "18", "Kepulauan Bangka Belitung (19)": "19", 
    "Kepulauan Riau (21)": "21", "DKI Jakarta (31)": "31", "Jawa Barat (32)": "32", 
    "Jawa Tengah (33)": "33", "DI Yogyakarta (34)": "34", "Jawa Timur (35)": "35", 
    "Banten (36)": "36", "Bali (51)": "51", "Nusa Tenggara Barat (52)": "52", 
    "Nusa Tenggara Timur (53)": "53", "Kalimantan Barat (61)": "61", 
    "Kalimantan Tengah (62)": "62", "Kalimantan Selatan (63)": "63", 
    "Kalimantan Timur (64)": "64", "Kalimantan Utara (65)": "65", 
    "Sulawesi Utara (71)": "71", "Sulawesi Tengah (72)": "72", 
    "Sulawesi Selatan (73)": "73", "Sulawesi Tenggara (74)": "74", 
    "Gorontalo (75)": "75", "Sulawesi Barat (76)": "76", "Maluku (81)": "81", 
    "Maluku Utara (82)": "82", "Papua (91)": "91", "Papua Barat (92)": "92",
    "Papua Selatan (93)": "93", "Papua Tengah (94)": "94", 
    "Papua Pegunungan (95)": "95", "Papua Barat Daya (96)": "96"
}

API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
MS_TO_KT = 1.94384
METAR_API = "https://aviationweather.gov/api/data/metar"
SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

# =====================================
# 4. ENGINE PENGAMBIL DATA METAR/TAF (FALLBACK)
# =====================================
def get_robust_session():
    session = requests.Session()
    retry_strategy = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def fetch_metar_raw(icao):
    headers = {'User-Agent': 'Mozilla/5.0 OperationalWeatherClient'}
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
    headers = {'User-Agent': 'Mozilla/5.0 OperationalWeatherClient'}
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

def parse_metar(raw, original_icao):
    data = {"wind": "NIL", "vis": "NIL", "wx": "NIL", "cld": "NIL", "tt_td": "NIL", "qnh": "1013/29.92", "qfe": "NIL", "trend": "NOSIG", "rmk": "NIL"}
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

    w = re.search(r'\b(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT\b', main_part)
    if w:
        gust = w.group(3) if w.group(3) else ""
        data["wind"] = f"{w.group(1)}/{w.group(2)}{gust} KT"

    v_match = re.search(r'\b(\d{4})\b', main_part)
    if v_match:
        dist = int(v_match.group(1))
        data["vis"] = "10 KM" if dist == 9999 else f"{dist} M"
    elif "CAVOK" in main_part: data["vis"] = "10 KM"

    wx_codes = r'(?:VC|MI|BC|PR|DR|BL|SH|TS|FZ|DZ|RA|SN|SG|IC|PL|GR|GS|UP|BR|FG|FU|VA|DU|SA|HZ|PY|PO|SQ|FC|SS|DS)'
    all_wx = re.findall(fr'\b([-+]?(?:{wx_codes})+)\b', main_part)
    all_wx = [x for x in all_wx if x not in [original_icao, "TEMPO", "BECMG", "NOSIG"]]
    data["wx"] = " ".join(all_wx) if all_wx else "NIL"

    c_layers = re.findall(r'\b(FEW|SCT|BKN|OVC|NSC|SKC)(\d{3})(CB|TCU)?\b', main_part)
    if c_layers:
        data["cld"] = " ".join([f"{t} {int(h)*100} FT{'' if not c else ' '+c}" for t, h, c in c_layers])
    elif "CAVOK" in main_part: data["cld"] = "NIL"

    tt_td = re.search(r'\b(M?\d{2})/(M?\d{2})\b', main_part)
    if tt_td: data["tt_td"] = f"{tt_td.group(1).replace('M','-')}/{tt_td.group(2).replace('M','-')}"

    q = re.search(r'\bQ(\d{4})\b', main_part)
    if q:
        val = int(q.group(1))
        data["qnh"] = f"{val}/{val*0.02953:.2f}"
        data["qfe"] = "NIL"  
    
    return data

# =====================================
# 5. ENGINE PDF FPDF (QAM GENERATOR)
# =====================================
class QAM_PDF(FPDF):
    def header(self):
        self.set_font("helvetica", 'B', 11)
        self.cell(0, 5, "MARKAS BESAR ANGKATAN UDARA", ln=True, align='L')
        self.cell(0, 5, "DINAS PENGEMBANGAN OPERASI", ln=True, align='L')
        self.ln(6)
        self.set_font("helvetica", 'BU', 12)
        self.cell(0, 6, "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING", ln=True, align='C')
        self.ln(6)

def generate_pdf(data, raw_taf, icao, name=""):
    pdf = QAM_PDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 10)
    date_str = datetime.utcnow().strftime('%d-%m-%Y')
    time_str = datetime.utcnow().strftime('%H.%M')
    
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
        for line in label_lines: pdf.cell(91, 5, line, ln=2)
        pdf.set_font("helvetica", '', 10)
        pdf.set_xy(x + 97, y + 2)
        for line in value_lines: pdf.cell(91, 5, line, ln=2)
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

# =====================================
# 6. ENGINE METAR HISTORY & BMKG FORECAST
# =====================================
def fetch_metar():
    r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
    r.raise_for_status()
    return r.text.strip()

def fetch_metar_history(hours=24):
    r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
    r.raise_for_status()
    return r.text.strip().splitlines()

def fetch_metar_ogimet(hours=24):
    end = datetime.utcnow()
    start = end - pd.Timedelta(hours=hours)
    url = "https://www.ogimet.com/display_metars2.php"
    params = {"lang": "en", "lugar": "WIBB", "tipo": "ALL", "ord": "REV", "nil": "NO", "fmt": "txt", "ano": start.year, "mes": start.month, "day": start.day, "hora": start.hour, "anof": end.year, "mesf": end.month, "dayf": end.day, "horaf": end.hour, "minf": end.minute}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return [l.strip() for l in r.text.splitlines() if l.startswith("WIBB")]

def wind(m):
    x = re.search(r'(\d{3})(\d{2})KT', m)
    return f"{x.group(1)}° / {x.group(2)} kt" if x else "-"

def visibility(m):
    x = re.search(r' (\d{4}) ', m)
    return f"{x.group(1)} m" if x else "-"

def temp_dew(m):
    x = re.search(r' (M?\d{2})/(M?\d{2})', m)
    return f"{x.group(1)} / {x.group(2)} °C" if x else "-"

def qnh(m):
    x = re.search(r' Q(\d{4})', m)
    return f"{x.group(1)} hPa" if x else "-"

def parse_numeric_metar(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t: return None
    data = {"time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"), "wind": None, "temp": None, "dew": None, "qnh": None, "vis": None, "RA": "RA" in m, "TS": "TS" in m, "FG": "FG" in m}
    w = re.search(r'(\d{3})(\d{2})KT', m)
    if w: data["wind"] = int(w.group(2))
    td = re.search(r' (M?\d{2})/(M?\d{2})', m)
    if td:
        data["temp"] = int(td.group(1).replace("M", "-"))
        data["dew"] = int(td.group(2).replace("M", "-"))
    q = re.search(r' Q(\d{4})', m)
    if q: data["qnh"] = int(q.group(1))
    v = re.search(r' (\d{4}) ', m)
    if v: data["vis"] = int(v.group(1))
    return data

def generate_raw_pdf(lines):
    content = "BT\n/F1 10 Tf\n72 800 Td\n"
    for l in lines:
        safe = l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content += f"({safe}) Tj\n0 -14 Td\n"
    content += "ET"
    return (
        b"%PDF-1.4\n1 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
        b"2 0 obj<< /Length " + str(len(content)).encode() + b" >>stream\n" + content.encode() +
        b"\nendstream endobj\n3 0 obj<< /Type /Page /Parent 4 0 R /Contents 2 0 R "
        b"/Resources<< /Font<< /F1 1 0 R >> >> >>endobj\n4 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 "
        b"/MediaBox [0 0 595 842] >>endobj\n5 0 obj<< /Type /Catalog /Pages 4 0 R >>endobj\nxref\n0 6\n0000000000 65535 f \n"
        b"trailer<< /Size 6 /Root 5 0 R >>\n%%EOF"
    )

@st.cache_data(ttl=300)
def fetch_forecast(adm1: str):
    params = {"adm1": adm1}
    resp = requests.get(API_BASE, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def flatten_cuaca_entry(entry):
    rows = []
    lokasi = entry.get("lokasi", {})
    for group in entry.get("cuaca", []):
        for obs in group:
            r = obs.copy()
            r.update({"adm1": lokasi.get("adm1"), "adm2": lokasi.get("adm2"), "provinsi": lokasi.get("provinsi"), "kotkab": lokasi.get("kotkab"), "lon": lokasi.get("lon"), "lat": lokasi.get("lat")})
            try:
                r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"))
                r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"))
            except Exception:
                r["utc_datetime_dt"], r["local_datetime_dt"] = pd.NaT, pd.NaT
            rows.append(r)
    df = pd.DataFrame(rows)
    for c in ["t", "tcc", "tp", "wd_deg", "ws", "hu", "vs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# =====================================
# 7. SIDEBAR & NAVIGASI
# =====================================
with st.sidebar:
    st.title("🛰️ Tactical Controls")
    
    # ----------------------------------------------------
    # PEMBARUAN: Mengganti Text Input dengan Selectbox
    # ----------------------------------------------------
    provinsi_list = list(PROVINCE_ADM1_MAP.keys())
    # Mencari index "Riau (14)" untuk dijadikan default value
    default_idx = provinsi_list.index("Riau (14)") if "Riau (14)" in provinsi_list else 0
    
    selected_prov_label = st.selectbox(
        "📍 Province Code (ADM1)", 
        options=provinsi_list,
        index=default_idx
    )
    
    # Mengekstrak value ADM1 dari dictionary
    adm1 = PROVINCE_ADM1_MAP[selected_prov_label]
    # ----------------------------------------------------
    
    st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#5f5;'>Scanning Weather...</p>", unsafe_allow_html=True)
    refresh = st.button("🔄 Fetch Data")
    st.markdown("---")
    show_map = st.checkbox("Show Map", value=True)
    show_table = st.checkbox("Show Table", value=False)
    st.markdown("---")
    st.caption("Data Source: BMKG API\nTheme: Military Ops v1.0")

st.title("✈️ TNI AU Tactical Weather Operations Dashboard")

# TAB SYSTEM 
tab1, tab2, tab3, tab4 = st.tabs([
    "📡 QAM Multi-Station", 
    "📝 QAM Manual", 
    "📊 WIBB METAR & History", 
    "🛰️ BMKG Tactical Forecast"
])

# ==========================================
# TAB 1: MODE OTOMATIS (MULTI-STATION QAM)
# ==========================================
with tab1:
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

# ==========================================
# TAB 2: MODE INPUT MANUAL 
# ==========================================
with tab2:
    st.info("Input sandi observasi secara manual jika terjadi pemutusan jaringan komunikasi.")
    with st.form("form_manual_qam"):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            man_icao = st.text_input("AERODROME IDENTIFICATION (ICAO)", "WIBB")
            man_wind = st.text_input("SURFACE WIND (Dir/Speed)", "VRB02KT")
            man_vis = st.text_input("HORIZONTAL VISIBILITY", "8000 M")
            man_wx = st.text_input("PRESENT WEATHER", "NIL")
            man_cld = st.text_input("CLOUD (Amount & Height)", "FEW 015")
        with col_m2:
            man_tt_td = st.text_input("AIR TEMP / DEW POINT", "33/24")
            man_qnh = st.text_input("QNH (hPa/inHg)", "1010/29.83")
            man_qfe = st.text_input("QFE", "NIL")
            man_trend = st.text_input("TREND", "NOSIG")
            man_rmk = st.text_input("REMARKS (RMK)", "NIL")
            
        man_taf = st.text_area("TAFOR FORECAST DATA", "TAF WIBB 130500Z 1306/1406 ...")
        btn_manual_generate = st.form_submit_button("GENERATE PDF MANUAL", use_container_width=True)
        
    if btn_manual_generate:
        manual_data_dict = {"wind": man_wind, "vis": man_vis, "wx": man_wx, "cld": man_cld, "tt_td": man_tt_td, "qnh": man_qnh, "qfe": man_qfe, "trend": man_trend, "rmk": man_rmk}
        pdf_bytes_manual = generate_pdf(manual_data_dict, man_taf, man_icao)
        st.success("Dokumen QAM Manual Berhasil Di-generate!")
        st.download_button(
            label=f"📥 DOWNLOAD PDF QAM MANUAL - {man_icao}",
            data=pdf_bytes_manual,
            file_name=f"QAM_MANUAL_{man_icao}_{datetime.now().strftime('%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# ==========================================
# TAB 3: RIWAYAT WIBB & SATELIT
# ==========================================
with tab3:
    st.subheader("Lanud Roesmin Nurjadin — WIBB")
    now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
    try:
        metar_txt = fetch_metar()
        qam_text = [
            "METEOROLOGICAL REPORT (QAM)", f"DATE / TIME (UTC) : {now}", "AERODROME        : WIBB",
            f"SURFACE WIND     : {wind(metar_txt)}", f"VISIBILITY       : {visibility(metar_txt)}",
            f"TEMP / DEWPOINT  : {temp_dew(metar_txt)}", f"QNH              : {qnh(metar_txt)}", "", "RAW METAR:", metar_txt
        ]
        st.download_button("⬇️ Download QAM Text (PDF)", data=generate_raw_pdf(qam_text), file_name="QAM_WIBB_TEXT.pdf", mime="application/pdf")
        st.code(metar_txt)
    except Exception as e:
        st.error("Gagal menarik data WIBB METAR terkini.")

    st.divider()
    st.subheader("🛰️ Weather Satellite — Himawari-8 (Infrared)")
    st.caption("BMKG Himawari-8 | Reference only — not for tactical separation")
    try:
        img = requests.get(SATELLITE_HIMA_RIAU, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        img.raise_for_status()
        st.image(img.content, use_container_width=True)
    except Exception:
        st.warning("Satellite imagery temporarily unavailable.")

    st.divider()
    st.subheader("📊 Historical METAR Meteogram — Last 24h")
    try:
        raw_hist = fetch_metar_history(24)
        source_hist = "AviationWeather.gov"
        if not raw_hist or len(raw_hist) < 2:
            raw_hist = fetch_metar_ogimet(24)
            source_hist = "OGIMET Archive"
        df_hist = pd.DataFrame([parse_numeric_metar(m) for m in raw_hist if parse_numeric_metar(m)])
        st.caption(f"Data source: {source_hist} | Records: {len(df_hist)}")

        if not df_hist.empty:
            df_hist.sort_values("time", inplace=True)
            fig = make_subplots(rows=5, cols=1, shared_xaxes=True, subplot_titles=["Temperature / Dew Point (°C)","Wind Speed (kt)","QNH (hPa)","Visibility (m)","Weather Flags (RA / TS / FG)"])
            fig.add_trace(go.Scatter(x=df_hist["time"], y=df_hist["temp"], name="Temp"), 1, 1)
            fig.add_trace(go.Scatter(x=df_hist["time"], y=df_hist["dew"], name="Dew"), 1, 1)
            fig.add_trace(go.Scatter(x=df_hist["time"], y=df_hist["wind"], name="Wind"), 2, 1)
            fig.add_trace(go.Scatter(x=df_hist["time"], y=df_hist["qnh"], name="QNH"), 3, 1)
            fig.add_trace(go.Scatter(x=df_hist["time"], y=df_hist["vis"], name="Visibility"), 4, 1)
            fig.add_trace(go.Scatter(x=df_hist["time"], y=df_hist["RA"].astype(int), mode="markers", name="RA"), 5, 1)
            fig.add_trace(go.Scatter(x=df_hist["time"], y=df_hist["TS"].astype(int), mode="markers", name="TS"), 5, 1)
            fig.add_trace(go.Scatter(x=df_hist["time"], y=df_hist["FG"].astype(int), mode="markers", name="FG"), 5, 1)
            fig.update_layout(height=950, hovermode="x unified", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            df_hist["time"] = df_hist["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            st.download_button("⬇️ Download CSV", df_hist.to_csv(index=False), "WIBB_METAR_24H.csv")
    except Exception as e:
        st.warning("Data riwayat METAR tidak tersedia.")

# ==========================================
# TAB 4: BMKG TACTICAL FORECAST 
# ==========================================
with tab4:
    st.markdown("*Source: BMKG Forecast API — Live Data*")
    with st.spinner("🛰️ Acquiring weather intelligence..."):
        try:
            raw_fcst = fetch_forecast(adm1)
            entries = raw_fcst.get("data", [])
            if not entries:
                st.warning("No forecast data available.")
            else:
                mapping = {}
                for e in entries:
                    lok = e.get("lokasi", {})
                    label = lok.get("kotkab") or lok.get("adm2") or f"Location {len(mapping)+1}"
                    mapping[label] = {"entry": e}

                col1, col2 = st.columns([2, 1])
                with col1:
                    loc_choice = st.selectbox("🎯 Select Location", options=list(mapping.keys()))
                with col2:
                    st.metric("📍 Locations", len(mapping))

                selected_entry = mapping[loc_choice]["entry"]
                df_fcst = flatten_cuaca_entry(selected_entry)
                
                if not df_fcst.empty:
                    df_fcst["ws_kt"] = df_fcst["ws"] * MS_TO_KT
                    df_fcst = df_fcst.sort_values("utc_datetime_dt")

                    min_dt = df_fcst["local_datetime_dt"].dropna().min().to_pydatetime()
                    max_dt = df_fcst["local_datetime_dt"].dropna().max().to_pydatetime()

                    start_dt = st.slider("Time Range (Local)", min_value=min_dt, max_value=max_dt, value=(min_dt, max_dt), step=pd.Timedelta(hours=3))

                    mask = (df_fcst["local_datetime_dt"] >= pd.to_datetime(start_dt[0])) & (df_fcst["local_datetime_dt"] <= pd.to_datetime(start_dt[1]))
                    df_sel = df_fcst.loc[mask].copy()

                    st.markdown("---")
                    st.subheader("⚡ Tactical Weather Status")
                    now_fcst = df_sel.iloc[0]
                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("TEMP (°C)", f"{now_fcst.get('t', '—')}°C")
                    with c2: st.metric("HUMIDITY", f"{now_fcst.get('hu', '—')}%")
                    with c3: st.metric("WIND (KT)", f"{now_fcst.get('ws_kt', 0):.1f}")
                    with c4: st.metric("RAIN (mm)", f"{now_fcst.get('tp', '—')}")

                    st.markdown("---")
                    st.subheader("📊 Parameter Trends")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature (°C)", markers=True, color_discrete_sequence=["#a9df52"]), use_container_width=True)
                        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="hu", title="Humidity (%)", markers=True, color_discrete_sequence=["#00ffbf"]), use_container_width=True)
                    with c2:
                        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="ws_kt", title="Wind Speed (KT)", markers=True, color_discrete_sequence=["#00ffbf"]), use_container_width=True)
                        st.plotly_chart(px.bar(df_sel, x="local_datetime_dt", y="tp", title="Rainfall (mm)", color_discrete_sequence=["#ffbf00"]), use_container_width=True)

                    st.markdown("---")
                    st.subheader("🌪️ Windrose — Direction & Speed")
                    if "wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns:
                        df_wr = df_sel.dropna(subset=["wd_deg", "ws_kt"])
                        if not df_wr.empty:
                            bins_dir = np.arange(-11.25, 360, 22.5)
                            labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
                            df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)
                            speed_bins = [0,5,10,20,30,50,100]
                            speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
                            df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
                            freq = df_wr.groupby(["dir_sector","speed_class"], observed=False).size().reset_index(name="count")
                            freq["percent"] = freq["count"]/freq["count"].sum()*100
                            az_map = {"N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,"S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5}
                            freq["theta"] = freq["dir_sector"].map(az_map)
                            colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]
                            fig_wr = go.Figure()
                            for i, sc in enumerate(speed_labels):
                                subset = freq[freq["speed_class"]==sc]
                                fig_wr.add_trace(go.Barpolar(r=subset["percent"], theta=subset["theta"], name=f"{sc} KT", marker_color=colors[i], opacity=0.85))
                            fig_wr.update_layout(title="Windrose (KT)", polar=dict(angularaxis=dict(direction="clockwise", rotation=90, tickvals=list(range(0,360,45))), radialaxis=dict(ticksuffix="%", showline=True, gridcolor="#333")), legend_title="Wind Speed Class", template="plotly_dark")
                            st.plotly_chart(fig_wr, use_container_width=True)

                    if show_map:
                        st.markdown("---")
                        st.subheader("🗺️ Tactical Map")
                        try:
                            st.map(pd.DataFrame({"lat": [float(selected_entry.get("lokasi", {}).get("lat", 0))], "lon": [float(selected_entry.get("lokasi", {}).get("lon", 0))]}))
                        except Exception as e:
                            st.warning(f"Map unavailable: {e}")

                    if show_table:
                        st.markdown("---")
                        st.subheader("📋 Forecast Table")
                        st.dataframe(df_sel)

        except Exception as e:
            st.error(f"Failed to fetch tactical data: {e}")

st.markdown("""
---
<div style="text-align:center; color:#7a7; font-size:0.9rem;">
Tactical Weather Ops Dashboard — BMKG Data © 2026<br>
Designed with Military Precision | Powered by Streamlit + Plotly
</div>
""", unsafe_allow_html=True)
