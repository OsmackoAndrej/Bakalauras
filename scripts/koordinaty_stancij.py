import pandas as pd
import requests


def fetch_lithuania_railway_stations():
  overpass_url = "http://overpass-api.de/api/interpreter"

  overpass_query = """
    [out:json][timeout:30];
    area[name="Lietuva"][admin_level=2]->.searchArea;
    (
      node["railway"~"station|halt"](area.searchArea);
      way["railway"~"station|halt"](area.searchArea);
      relation["railway"~"station|halt"](area.searchArea);
    );
    out center;
    """

  headers = {
      "User-Agent": "LithuaniaRailwayScript/1.0 (Educational/Research)",
      "Accept": "application/json",
  }

  print("Užklausa Overpass API...")
  response = requests.post(
      overpass_url, data={"data": overpass_query}, headers=headers
  )

  if response.status_code != 200:
    print(f"Klaida užklausoje: {response.status_code} — {response.text[:200]}")
    return None

  data = response.json()
  elements = data.get("elements", [])
  print(f"Rasta objektų: {len(elements)}")

  stations_data = []
  for el in elements:
    el_type = el.get("type")
    lat = el.get("lat")
    lon = el.get("lon")

    if el_type in ["way", "relation"] and "center" in el:
      lat = el["center"].get("lat")
      lon = el["center"].get("lon")

    tags = el.get("tags", {})
    if lat and lon:
      stations_data.append({
          "id": el.get("id"),
          "type": el_type,
          "railway": tags.get("railway", ""),
          "name": tags.get(
              "name", "Be pavadinimo"
          ),  
          "name_en": tags.get("name:en", ""),
          "lat": lat,
          "lon": lon,
      })

  return pd.DataFrame(stations_data)


if __name__ == "__main__":
  df_stations = fetch_lithuania_railway_stations()
  if df_stations is not None and not df_stations.empty:
    output_filename = "lithuania_railway_stations_osm.csv"

    df_stations.to_csv(output_filename, index=False, encoding="utf-8-sig")

    print(f"Duomenys sėkmingai išsaugoti į failą: {output_filename} (naudojant UTF-8 koduotę)")
