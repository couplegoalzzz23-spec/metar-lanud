import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import io

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="LANUD TNI AU METAR",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# STYLE
# =====================================
st.markdown("""
<style>
.stApp {
    background-color: #08111f;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =====================================
# DATA LANUD
# =====================================
LANUD_DATA = [
    {"Nama":"Lanud Halim Perdanakusuma","ICAO":"WIHH","WMO":"96749"},
    {"Nama":"Lanud Roesmin Nurjadin","ICAO":"WIBB","WMO":"96109"},
    {"Nama":"Lanud Supadio","ICAO":"WIOO","WMO":"96413"},
    {"Nama":"Lanud Adisutjipto","ICAO":"WARJ","WMO":"96839"},
    {"Nama":"Lanud Abdulrachman Saleh","ICAO":"WARA","WMO":"96881"},
    {"Nama":"Lanud Iswahyudi","ICAO":"WARI","WMO":"96877"},
    {"Nama":"Lanud Juanda","ICAO":"WARR","WMO":"96935"},
    {"Nama":"Lanud Sultan Hasanuddin","ICAO":"WAAA","WMO":"97180"},
    {"Nama":"Lanud Ngurah Rai","ICAO":"WADD","WMO":"97230"},
    {"Nama":"Lanud Roesmin Nurjadin","ICAO":"WIBB","WMO":"96109"}
]

df = pd.DataFrame(LANUD_DATA)

# =====================================
# FETCH METAR
# =====================================
@st.cache_data(ttl=300)
def fetch_metar(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()

        root = ET.fromstring(r.text)
        metar = root.find(".//METAR")

        if metar is None:
            return None

        return {
            "raw_text": metar.findtext("raw_text"),
            "temp_c": metar.findtext("temp_c"),
            "dewpoint_c": metar.findtext("dewpoint_c"),
            "wind_dir": metar.findtext("wind_dir_degrees"),
            "wind_speed": metar.findtext("wind_speed_kt"),
            "visibility": metar.findtext("visibility_statute_mi"),
            "altimeter": metar.findtext("altim_in_hg"),
            "flight_category": metar.findtext("flight_category"),
            "obs_time": metar.findtext("observation_time")
        }

    except Exception as e:
        st.error(f"Error: {e}")
        return None

# =====================================
# PDF GENERATOR
# =====================================
def generate_pdf(lanud, icao, wmo, metar):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("LAPORAN METAR/QAM LANUD TNI AU", styles["Title"]))
    story.append(Spacer(1, 20))

    story.append(Paragraph(f"Lanud : {lanud}", styles["Normal"]))
    story.append(Paragraph(f"ICAO : {icao}", styles["Normal"]))
    story.append(Paragraph(f"WMO : {wmo}", styles["Normal"]))
    story.append(Spacer(1, 20))

    data = [
        ["Parameter", "Nilai"],
        ["RAW METAR", metar["raw_text"]],
        ["Temperature", f"{metar['temp_c']} °C"],
        ["Dew Point", f"{metar['dewpoint_c']} °C"],
        ["Wind", f"{metar['wind_speed']} kt"],
        ["Wind Direction", f"{metar['wind_dir']}°"],
        ["Visibility", f"{metar['visibility']} mi"],
        ["Altimeter", metar["altimeter"]],
        ["Flight Category", metar["flight_category"]],
        ["Observation Time", metar["obs_time"]],
    ]

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.navy),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("BACKGROUND",(0,1),(-1,-1),colors.whitesmoke)
    ]))

    story.append(table)

    doc.build(story)
    buffer.seek(0)

    return buffer

# =====================================
# HEADER
# =====================================
st.title("✈️ LANUD TNI AU METAR DASHBOARD")
st.caption("Realtime METAR/QAM Monitoring")

# =====================================
# SIDEBAR
# =====================================
selected = st.sidebar.selectbox("Pilih Lanud", df["Nama"])

row = df[df["Nama"] == selected].iloc[0]

icao = row["ICAO"]
wmo = row["WMO"]

st.sidebar.info(f"""
ICAO : {icao}

WMO : {wmo}
""")

# =====================================
# FETCH
# =====================================
metar = fetch_metar(icao)

# =====================================
# DISPLAY
# =====================================
if metar:

    st.success("Data METAR berhasil dimuat")

    st.code(metar["raw_text"])

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Temp", f"{metar['temp_c']} °C")
    c2.metric("Dew", f"{metar['dewpoint_c']} °C")
    c3.metric("Wind", f"{metar['wind_speed']} kt")
    c4.metric("Vis", f"{metar['visibility']} mi")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(metar["wind_speed"] or 0),
        title={"text":"Wind Speed"},
        gauge={"axis":{"range":[0,80]}}
    ))

    st.plotly_chart(fig, use_container_width=True)

    # PDF DOWNLOAD
    pdf = generate_pdf(selected, icao, wmo, metar)

    st.download_button(
        label="⬇️ Download PDF Laporan",
        data=pdf,
        file_name=f"{icao}_METAR_Report.pdf",
        mime="application/pdf"
    )

else:
    st.warning("Data METAR tidak tersedia")
