import pandas as pd

# 1. Užkrauname duomenis iš CSV failo
df = pd.read_csv('railway_incidents_cleaned.csv', sep=';')

# 2. Konvertuojame incidento datą ir laiką į datetime formatą
df['incident_time'] = pd.to_datetime(df['incident'], errors='coerce')

# 3. Išskiriame valandą ir suskirstome į paros laiko intervalus
df['hour'] = df['incident_time'].dt.hour
bins = [-1, 6, 12, 18, 24]
labels = ['Naktis (00-06)', 'Rytas (06-12)', 'Diena (12-18)', 'Vakaras (18-24)']
df['time_of_day'] = pd.cut(df['hour'], bins=bins, labels=labels)

# 4. Pateikiame pagrindinę statistiką ir pasiskirstymą pagal paros laiką
print("--- INCIDENTŲ PASISKIRSTYMAS PAGAL PAROS LAIKĄ ---")
print(df['time_of_day'].value_counts())

print("\n--- DUOMENŲ PAVYZDYS ---")
print(df[['incident_id', 'incident', 'hour', 'time_of_day', 'infrastructure_manager', 'casualties']].head(10))