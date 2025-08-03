# --- Imports ---
import streamlit as st
import requests
import datetime as dt
from collections import defaultdict, Counter
from streamlit_folium import st_folium
import folium
import meteostat as ms
import pandas as pd
import os

# --- Config ---
appid = os.getenv("OPENWEATHER_API_KEY")  # Make sure your .env is loaded

curr_weather_url = "https://api.openweathermap.org/data/2.5/weather"
forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
coordinates_url = "http://api.openweathermap.org/geo/1.0/direct"

# --- UI Setup ---
st.set_page_config(page_title="Weather App", page_icon="🌤️", layout="centered")
st.title("🌦️ Welcome to Your Weather Companion")
st.markdown("Enter a city name or select a location on the map to get weather updates.")

# --- Input Options ---
city_name = st.text_input("📍 Enter City Name")

st.markdown("### 🗺️ Or choose a location on the map")
default_location = [32.0853, 34.7818]  # Tel Aviv
m = folium.Map(location=default_location, zoom_start=6)
folium.Marker(location=default_location, popup="Tel Aviv").add_to(m)
map_data = st_folium(m, width=700, height=500)

# --- Determine Coordinates ---
lat, lon = None, None

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.success(f"📌 Location Selected: Latitude {lat:.2f}, Longitude {lon:.2f}")
elif city_name:
    params_location = {"q": city_name, "limit": 1, "appid": appid}
    coordinates = requests.get(coordinates_url, params=params_location)
    coordinates.raise_for_status()
    coordinates_post = coordinates.json()
    if not coordinates_post:
        st.error("Location Not Found. Please Enter a City Name Again.")
        st.stop()
    lat = coordinates_post[0]['lat']
    lon = coordinates_post[0]['lon']
    st.success(f"📍 Found {city_name.title()} at Latitude {lat:.2f}, Longitude {lon:.2f}")
else:
    st.info("👆 Enter a city name or click on the map to begin.")
    st.stop()

# --- Weather API Calls ---
params_imperial = {"lat": lat, "lon": lon, 'units': 'imperial', "appid": appid}
params_metric = {"lat": lat, "lon": lon, 'units': 'metric', "appid": appid}

# Fetch current weather
curr_weather_imperial = requests.get(curr_weather_url, params=params_imperial)
curr_weather_metric = requests.get(curr_weather_url, params=params_metric)

# Check for errors
if curr_weather_imperial.status_code != 200:
    st.error(f"❌ Error fetching imperial weather data: {curr_weather_imperial.json().get('message', 'Unknown error')}")
    st.stop()

if curr_weather_metric.status_code != 200:
    st.error(f"❌ Error fetching metric weather data: {curr_weather_metric.json().get('message', 'Unknown error')}")
    st.stop()

# Parse JSON safely
curr_weather_imperial_post = curr_weather_imperial.json()
curr_weather_metric_post = curr_weather_metric.json()

# Validate expected keys
if 'dt' not in curr_weather_imperial_post or 'timezone' not in curr_weather_imperial_post:
    st.error("❌ Unexpected response format. Please try a different location.")
    st.json(curr_weather_imperial_post)  # Show the raw response for debugging
    st.stop()


# --- Time Conversion ---
utc_timestamp = curr_weather_imperial_post['dt']
timezone_offset = curr_weather_imperial_post['timezone']
utc_time = dt.datetime.fromtimestamp(utc_timestamp, dt.UTC)
local_time = utc_time + dt.timedelta(seconds=timezone_offset)

# --- Current Weather Summary ---
curr_weather_details = {
    'Country': curr_weather_imperial_post['sys']['country'],
    'City': curr_weather_imperial_post['name'],
    'Weather_Type': curr_weather_imperial_post['weather'][0]['main'],
    'Icon': curr_weather_imperial_post['weather'][0]['icon'],
    'Humidity': f"{int(round(curr_weather_imperial_post['main']['humidity']))} %"
}

curr_weather_metric = {
    'Temp_C': int(round(curr_weather_metric_post['main']['temp'])),
    'Feels_Like_C': int(round(curr_weather_metric_post['main']['feels_like'])),
    'Wind_Speed_KPH': int(round(curr_weather_metric_post['wind']['speed'] * 3.6)),
    'Local_Date': local_time.strftime('%d/%m/%Y'),
    'Local_Time': local_time.strftime('%H:%M')
}

# --- Forecast Summary (Metric) ---
date_list_metric = defaultdict(list)
for item in forecast_metric_post['list']:
    date = dt.datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S').date()
    date_list_metric[date].append(item)

daily_summary_metric = []
for date, items in date_list_metric.items():
    Temp_C_Min = [item['main']['temp_min'] for item in items]
    Temp_C_Max = [item['main']['temp_max'] for item in items]
    Wind_Speed_KPH = [item['wind']['speed'] for item in items]
    Weather_Type = [item['weather'][0]['main'] for item in items]
    Icon = [item['weather'][0]['icon'] for item in items]

    daily_metric = {
        'Date': date.strftime('%d/%m/%Y'),
        'Temp_C_Min': int(round(min(Temp_C_Min))),
        'Temp_C_Max': int(round(max(Temp_C_Max))),
        'Wind_Speed_KPH': int(round(sum(Wind_Speed_KPH) / len(Wind_Speed_KPH) * 3.6, 1)),
        'Weather_Type': Counter(Weather_Type).most_common(1)[0][0],
        'Icon': Counter(Icon).most_common(1)[0][0]
    }
    daily_summary_metric.append(daily_metric)

# --- Historic Averages ---
location = ms.Point(lat, lon)
date_to = dt.datetime.now()
date_from = date_to - dt.timedelta(days=365)
ms_data = ms.Daily(location, date_from, date_to)
df = ms_data.fetch().dropna(subset=['tavg']).reset_index()
df['month'] = df['time'].dt.strftime('%m-%Y')
df = df[['time', 'tavg', 'month']]
df_agg = df.groupby('month').agg({'tavg': 'mean'})
df_agg['tavg_f'] = df_agg['tavg'] * 9/5 + 32
df_agg = df_agg.round().astype(int).rename(columns={'tavg': 'Temp_C_Avg', 'tavg_f': 'Temp_F_Avg'})

# --- Display Results ---
st.subheader("📊 Current Weather")
st.write(curr_weather_details)
st.write(curr_weather_metric)

st.subheader("📅 5-Day Forecast")
st.write(pd.DataFrame(daily_summary_metric))

st.subheader("📈 Historic Monthly Averages")
st.write(df_agg)