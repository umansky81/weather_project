# import modules
import string
import streamlit as st
import pandas as pd
import seaborn as sns
import datetime as dt
import meteostat as ms
import requests
import os
import json
import folium
from collections import defaultdict, Counter
from dotenv import load_dotenv
from streamlit_folium import st_folium

# add url addresses
appid = "9c52e999ca8280b5b1b549f0bf56dc82"
curr_weather_url = "https://api.openweathermap.org/data/2.5/weather"
forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
coordinates_url = "http://api.openweathermap.org/geo/1.0/direct"

# --- Session State Setup ---
if 'input_source' not in st.session_state:
    st.session_state.input_source = None
if 'city_name' not in st.session_state:
    st.session_state.city_name = None
if 'city_input' not in st.session_state:
    st.session_state.city_input = ""
if 'clear_city_input' not in st.session_state:
    st.session_state.clear_city_input = False


# UI Setup
st.set_page_config(page_title="Weather App", page_icon="🌤️", layout="centered")
st.title("🌦️ Welcome to Your Weather Companion")
st.markdown("Enter a city name or select a location on the map to get weather updates.")

# --- Input Options ---
if st.session_state.clear_city_input:
    st.session_state.city_input = ""
    st.session_state.clear_city_input = False

city_name_input = st.text_input("📍 Enter City Name", key="city_input")


if city_name_input:
    st.session_state.input_source = 'city'
    st.session_state.city_name = city_name_input

st.markdown("### 🗺️ Or choose a location on the map")
default_location = [32.0853, 34.7818]  # Tel Aviv
m = folium.Map(location=default_location, zoom_start=6)
folium.Marker(location=default_location, popup="Tel Aviv").add_to(m)
map_data = st_folium(m, width=700, height=500)

# --- Determine Coordinates ---
lat, lon = None, None
use_coordinates_directly = False

if map_data and map_data.get("last_clicked"):
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]
    st.session_state.input_source = 'map'
    st.session_state.city_name = None  # Clear previous city name
    st.success(f"📌 Location Selected: Latitude {lat:.2f}, Longitude {lon:.2f}")
    if "city_input" in st.session_state:
        st.session_state.clear_city_input = True
        st.experimental_rerun()

# Only proceed if city_name is entered
elif st.session_state.input_source == 'city' and st.session_state.city_name:
    params_location = {"q": st.session_state.city_name, "limit": 1, "appid": appid}
    coordinates = requests.get(coordinates_url, params=params_location)
    coordinates.raise_for_status()
    coordinates_post = coordinates.json()
    if not coordinates_post:
        st.error("Location Not Found. Please Enter a City Name Again: ")
        st.stop()
    lat = coordinates_post[0]['lat']
    lon = coordinates_post[0]['lon']
    st.success(f"📍 Found {st.session_state.city_name.title()} at Latitude {lat:.2f}, Longitude {lon:.2f}")
else:
    st.info("👆 Enter a City Name or Click on the Map to See Weather Data")
    st.stop()

params_imperial = {"lat": lat, "lon": lon, 'units': 'imperial', "appid": appid}
params_metric = {"lat": lat, "lon": lon, 'units': 'metric', "appid": appid}

# current weather data
curr_weather_imperial = requests.get(curr_weather_url,params=params_imperial)
curr_weather_imperial.raise_for_status()
curr_weather_imperial_post = curr_weather_imperial.json()
curr_weather_metric = requests.get(curr_weather_url,params=params_metric)
curr_weather_metric.raise_for_status()
curr_weather_metric_post = curr_weather_metric.json()

# weather forecast data
forecast_imperial = requests.get(forecast_url,params=params_imperial)
forecast_imperial.raise_for_status()
forecast_imperial_post = forecast_imperial.json()
forecast_metric = requests.get(forecast_url,params=params_metric)
forecast_metric.raise_for_status()
forecast_metric_post = forecast_metric.json()

# add time conversion for local time
utc_timestamp = curr_weather_imperial_post['dt']
timezone_offset = curr_weather_imperial_post['timezone']
utc_time = dt.datetime.fromtimestamp(utc_timestamp, dt.UTC)
local_time = utc_time + dt.timedelta(seconds=timezone_offset)

# summarize main weather figures
curr_weather_details = {
    'Country': curr_weather_imperial_post['sys']['country'],
    'City': curr_weather_imperial_post['name'],
    'Weather_Type': curr_weather_imperial_post['weather'][0]['main'],
    'Icon': curr_weather_imperial_post['weather'][0]['icon'],
    'Humidity': f"{int(round(curr_weather_imperial_post['main']['humidity']))} %"
}

curr_weather_imperial = {
    'Temp_F': int(round((curr_weather_imperial_post['main']['temp']))),
    'Feels_Like_F': int(round((curr_weather_imperial_post['main']['feels_like']))),
    'Wind_Speed_MPH': int(round(curr_weather_imperial_post['wind']['speed'])),
    'Local_Date': local_time.strftime('%m/%d/%Y'),
    'Local_Time': local_time.strftime('%I:%M %p')
}

curr_weather_metric = {
    'Temp_C': int(round(curr_weather_metric_post['main']['temp'])),
    'Feels_Like_C': int(round(curr_weather_metric_post['main']['feels_like'])),
    'Wind Speed_KPH': int(round(curr_weather_metric_post['wind']['speed'] * 3.6)),
    'Local_Date': local_time.strftime('%d/%m/%Y'),
    'Local_Time': local_time.strftime('%H:%M')
}

# summarize daily forecasts - imperial

# create a list of dates
date_list_imperial = defaultdict(list)
for item in forecast_imperial_post['list']:
    date = dt.datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S').date()
    date_list_imperial[date].append(item)

# populate forecast data items
daily_summary_imperial = []
for date, items in date_list_imperial.items():
    Temp_F_Min = [item['main']['temp_min'] for item in items]
    Temp_F_Max = [item['main']['temp_max'] for item in items]
    Wind_Speed_MPH = [item['wind']['speed'] for item in items]
    Weather_Type = [item['weather'][0]['main'] for item in items]
    Icon = [item['weather'][0]['icon'] for item in items]

# aggregate forecast data to get min, max, average per day
    daily_imperial = {
        'Date': date.strftime('%m/%d/%Y'),
        'Temp_F_Min': int(round(min(Temp_F_Min))),
        'Temp_F_Max': int(round(max(Temp_F_Max))),
        'Wind_Speed_MPH': int(round(sum(Wind_Speed_MPH) / len(Wind_Speed_MPH), 1)),
        'Weather_Type': Counter(Weather_Type).most_common(1)[0][0],
        'Icon': Counter(Icon).most_common(1)[0][0]
    }

    daily_summary_imperial.append(daily_imperial)

# summarize daily forecasts - metric

# create a list of dates
date_list_metric = defaultdict(list)
for item in forecast_metric_post['list']:
    date = dt.datetime.strptime(item['dt_txt'], '%Y-%m-%d %H:%M:%S').date()
    date_list_metric[date].append(item)

# populate forecast data items
daily_summary_metric = []
for date, items in date_list_metric.items():
    Temp_C_Min = [item['main']['temp_min'] for item in items]
    Temp_C_Max = [item['main']['temp_max'] for item in items]
    Wind_Speed_KPH = [item['wind']['speed'] for item in items]
    Weather_Type = [item['weather'][0]['main'] for item in items]
    Icon = [item['weather'][0]['icon'] for item in items]

# aggregate forecast data to get min, max, average per day
    daily_metric = {
        'Date': date.strftime('%d/%m/%Y'),
        'Temp_C_Min': int(round(min(Temp_C_Min))),
        'Temp_C_Max': int(round(max(Temp_C_Max))),
        'Wind_Speed_KPH': int(round(sum(Wind_Speed_KPH) / len(Wind_Speed_KPH) * 3.6, 1)),
        'Weather_Type': Counter(Weather_Type).most_common(1)[0][0],
        'Icon': Counter(Icon).most_common(1)[0][0]
    }

    daily_summary_metric.append(daily_metric)

# Find nearest weather station
stations = ms.Stations()
stations = stations.nearby(lat, lon)
station = stations.fetch(1)

if station.empty:
    st.warning("⚠️ No nearby weather station found for historical data.")
else:
    station_id = station.index[0]
    date_to = dt.datetime.now()
    date_from = date_to - dt.timedelta(days=365)
    ms_data = ms.Daily(station_id, date_from, date_to)
    df = ms_data.fetch()

    if df.empty or 'tavg' not in df.columns:
        st.warning("⚠️ No historical temperature data available for this location.")
    else:
        df = df.dropna(subset=['tavg'])
        df = df.reset_index()
        df['month'] = df['time'].dt.strftime('%m-%Y')
        df = df[['time', 'tavg', 'month']]

        df_agg = df.groupby('month').agg({'tavg': 'mean'})
        df_agg['tavg_f'] = df_agg['tavg'] * 9/5 + 32
        df_agg['tavg'] = df_agg['tavg'].round().astype(int)
        df_agg['tavg_f'] = df_agg['tavg_f'].round().astype(int)
        df_agg.rename(columns={
            'tavg': 'Temp_C_Avg',
            'tavg_f': 'Temp_F_Avg'
        }, inplace=True)
        if st.session_state.input_source == 'city' and st.session_state.city_name:
            st.write(f"Weather for: **{st.session_state.city_name.title()}**")
        elif st.session_state.input_source == 'map':
            st.write(f"Weather for coordinates: **{lat:.2f}, {lon:.2f}**")

        st.write(daily_summary_metric)