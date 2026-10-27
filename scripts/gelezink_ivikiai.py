import pandas as pd

url = "https://get.data.gov.lt/datasets/gov/ltsa/gelezinkeliu_eismo_ivykiai/RailwayIncident/:format/csv"

df = pd.read_csv(url, on_bad_lines='skip', engine='python')

df.columns = [col.replace(';', '').strip() for col in df.columns]

df = df.dropna(subset=['incident_id'])

df.to_csv("railway_incidents_cleaned.csv", index=False, encoding="utf-8-sig")

print(f"Pabaga išsaugota: {len(df)}")
print(df[['incident_id', 'incident', 'type', 'casualties']].head())