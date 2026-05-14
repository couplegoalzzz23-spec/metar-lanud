import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
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
    {"Nama":"Lanud Ngurah Rai","ICAO":"WADD","WMO":"97230"}
]

df = pd.DataFrame(LANUD_DATA)

# =====================================
# FETCH METAR
# =====================================
@st.cache_data(ttl=300)
def fetch_metar(icao):
    url = f"https://aviationweather.gov/api/data/metar?ids={icao}&format=xml"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        root = ET.fromstring(response.text)
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
        st.error(f"Fetch Error: {e}")
        return None

# =====================================
# GENERATE REPORT
# =====================================
def generate_report(lanud, icao, wmo, metar):
    report = f"""
========================================
LAPORAN METAR/QAM LANUD TNI AU
========================================

LANUD : {lanud}
ICAO  : {icao}
WMO   : {wmo}

RAW METAR:
{metar['raw_text']}

----------------------------------------
PARAMETER
----------------------------------------
Temperature     : {metar['temp_c']} °C
Dew Point       : {metar['dewpoint_c']} °C
Wind Speed      : {metar['wind_speed']} kt
Wind Direction  : {metar['wind_dir']}°
Visibility      : {metar['visibility']} mi
Altimeter       : {metar['altimeter']}
Flight Category : {metar['flight_category']}
Observation Time: {metar['obs_time']}

Source:
https://aviationweather.gov
"""
    return report

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

# =====================================
# FETCH
# =====================================
metar = fetch_metar(icao)

# =====================================
# DISPLAY
# =====================================
if metar:

    st.success("METAR berhasil dimuat")

    st.code(metar["raw_text"])

    c1,c2,c3,c4 = st.columns(4)

    c1.metric("Temp", f"{metar['temp_c']} °C")
    c2.metric("Dew", f"{metar['dewpoint_c']} °C")
    c3.metric("Wind", f"{metar['wind_speed']} kt")
    c4.metric("Visibility", f"{metar['visibility']} mi")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(metar["wind_speed"] or 0),
        title={'text': "Wind Speed"},
        gauge={'axis': {'range': [0,80]}}
    ))

    st.plotly_chart(fig, use_container_width=True)

    report = generate_report(selected, icao, wmo, metar)

    st.download_button(
        "⬇️ Download Report",
        data=report,
        file_name=f"{icao}_METAR_Report.txt",
        mime="text/plain"
    )

else:
    st.warning("Data METAR tidak tersedia")
