import pandas as pd
import requests
import datetime
import time

# 1. Užkrauname incidentų duomenis
df = pd.read_csv('railway_incidents_cleaned.csv', sep=';')
df['incident_time'] = pd.to_datetime(df['incident'], errors='coerce')

# 2. Funkcija orų duomenims gauti iš oficialaus https://www.meteo.lt API
def fetch_meteo_lt_weather(timestamp, station_code="kaunas-ms"):
    if pd.isna(timestamp):
        return None, None, None
    
    date_str = timestamp.strftime('%Y-%m-%d')
    url = f"https://api.meteo.lt/v1/stations/{station_code}/observations/{date_str}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            observations = data.get('observations', [])
            target_hour = timestamp.hour
            
            for obs in observations:
                obs_time = datetime.datetime.strptime(obs['observationTime'], '%Y-%m-%d %H:%M:%S')
                if obs_time.hour == target_hour:
                    return (
                        obs.get('airTemperature'),
                        obs.get('windSpeed'),
                        obs.get('conditionCode')
                    )
    except Exception as e:
        print(f"Klaida jungiantis prie meteo.lt: {e}")
        
    return None, None, None

print("Siunčiamos užklausos į https://www.meteo.lt ir pildomi orų duomenys...")

temperatures = []
wind_speeds = []
conditions = []

for idx, row in df.iterrows():
    temp, wind, cond = fetch_meteo_lt_weather(row['incident_time'])
    temperatures.append(temp)
    wind_speeds.append(wind)
    conditions.append(cond)
    time.sleep(0.05)

# Pridedame naujus stulpelius su orais iš meteo.lt
df['air_temperature_meteo'] = temperatures
df['wind_speed_meteo'] = wind_speeds
df['weather_condition_meteo'] = conditions

# Išsaugome galutinį failą, kuriame jau bus ir incidentai, ir orai
output_file = 'railway_incidents_with_meteo_lt.csv'
df.to_csv(output_file, index=False, sep=';')
print(f"Atlikta! Naujas failas su orų duomenimis išsaugotas kaip: {output_file}")