import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import plotly.graph_objects as go

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

.metric-box {
    background-color: #132238;
    padding: 15px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# =====================================
# DATABASE LANUD (EMBEDDED)
# =====================================
LANUD_DATA = [
    {"Nama":"Lanud Halim Perdanakusuma","ICAO":"WIHH","WMO":"96749"},
    {"Nama":"Lanud Roesmin Nurjadin","ICAO":"WIBB","WMO":"96109"},
    {"Nama":"Lanud Supadio","ICAO":"WIOO","WMO":"96413"},
    {"Nama":"Lanud Adisutjipto","ICAO":"WARJ","WMO":"96839"},
    {"Nama":"Lanud Abdulrachman Saleh","ICAO":"WARA","WMO":"96881"},
    {"Nama":"Lanud Iswahyudi","ICAO":"WARI","WMO":"96877"},
    {"Nama":"Lanud Juanda","ICAO":"WARR","WMO":"96935"},
    {"Nama":"Lanud Husein Sastranegara","ICAO":"WICC","WMO":"96781"},
    {"Nama":"Lanud Sultan Hasanuddin","ICAO":"WAAA","WMO":"97180"},
    {"Nama":"Lanud Sam Ratulangi","ICAO":"WAMM","WMO":"97014"},
    {"Nama":"Lanud Pattimura","ICAO":"WAPP","WMO":"97724"},
    {"Nama":"Lanud El Tari","ICAO":"WATT","WMO":"97372"},
    {"Nama":"Lanud Ngurah Rai","ICAO":"WADD","WMO":"97230"},
    {"Nama":"Lanud Silas Papare","ICAO":"WAJJ","WMO":"97690"},
    {"Nama":"Lanud Frans Kaisiepo","ICAO":"WABB","WMO":"97560"},
    {"Nama":"Lanud Dhomber","ICAO":"WALL","WMO":"96633"},
    {"Nama":"Lanud Tarakan","ICAO":"WAQQ","WMO":"96509"}
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
# HEADER
# =====================================
st.title("✈️ LANUD TNI AU METAR DASHBOARD")
st.caption("Realtime METAR/QAM Monitoring")

# =====================================
# SIDEBAR
# =====================================
selected_lanud = st.sidebar.selectbox(
    "Pilih Lanud",
    df["Nama"]
)

selected_row = df[df["Nama"] == selected_lanud].iloc[0]

icao = selected_row["ICAO"]
wmo = selected_row["WMO"]

st.sidebar.info(f"""
ICAO : {icao}

WMO : {wmo}
""")

# =====================================
# FETCH DATA
# =====================================
metar = fetch_metar(icao)

# =====================================
# DISPLAY
# =====================================
if metar:

    st.success("METAR berhasil dimuat")

    st.subheader(f"{selected_lanud} ({icao})")

    st.code(metar["raw_text"])

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Temperature", f"{metar['temp_c']} °C")
    c2.metric("Dew Point", f"{metar['dewpoint_c']} °C")
    c3.metric("Wind", f"{metar['wind_speed']} kt")
    c4.metric("Visibility", f"{metar['visibility']} mi")

    c5, c6, c7 = st.columns(3)

    c5.metric("Wind Dir", f"{metar['wind_dir']}°")
    c6.metric("Altimeter", metar["altimeter"])
    c7.metric("Flight Category", metar["flight_category"])

    # Gauge Wind
    st.subheader("Wind Speed")

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(metar["wind_speed"] or 0),
        title={'text': "KT"},
        gauge={
            'axis': {'range': [0, 80]}
        }
    ))

    st.plotly_chart(fig, use_container_width=True)

    st.write("### Observation Time")
    st.write(metar["obs_time"])

else:
    st.warning("Data METAR tidak tersedia.")
