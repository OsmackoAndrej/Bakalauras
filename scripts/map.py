import pandas as pd
import folium
from folium.plugins import MarkerCluster, HeatMap

df = pd.read_csv(
    "railway_incidents_cleaned.csv",
    sep=";",
    encoding="utf-8-sig"
)

df = df.rename(
    columns={
        "Unnamed: 17": "station_name"
    }
)

df["station_name"] = (
    df["station_name"]
    .astype(str)
    .str.strip()
)

bad_values = [
    "nan",
    "",
    "Other",
    "Collision of train with obstacle",
    "Port shunting yard",
    "Level-crossing accident",
    "Derailment of train"
]

df = df[
    ~df["station_name"].isin(bad_values)
]

danger = (
    df["station_name"]
    .value_counts()
    .rename_axis("station")
    .reset_index(name="incidents")
)

coords = pd.read_csv(
    "station_coordinates.csv",
    encoding="utf-8-sig"
)

coords["station"] = (
    coords["station"]
    .astype(str)
    .str.strip()
)

danger = danger.merge(
    coords,
    on="station",
    how="left"
)

danger = danger.dropna(
    subset=["lat", "lon"]
)


def risk_level(x):

    if x >= 10:
        return "HIGH"

    elif x >= 5:
        return "MEDIUM"

    return "LOW"


def marker_color(x):

    if x >= 10:
        return "red"

    elif x >= 5:
        return "orange"

    return "green"


danger["risk"] = (
    danger["incidents"]
    .apply(risk_level)
)


m = folium.Map(
    location=[55.25, 23.88],
    zoom_start=7,
    tiles=None
)

folium.TileLayer(
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="© OpenStreetMap",
    name="OSM"
).add_to(m)


heat_data = danger[
    ["lat", "lon", "incidents"]
].values.tolist()

HeatMap(
    heat_data,
    radius=25,
    blur=20
).add_to(m)


cluster = MarkerCluster().add_to(m)

for _, row in danger.iterrows():

    folium.CircleMarker(
        location=[
            row["lat"],
            row["lon"]
        ],
        radius=5 + row["incidents"] * 0.5,
        color=marker_color(
            row["incidents"]
        ),
        fill=True,
        fill_opacity=0.7,
        popup=f"""
        <b>{row['station']}</b><br>
        Incidents: {row['incidents']}<br>
        Risk: {row['risk']}
        """
    ).add_to(cluster)


legend = """
<div style="
position: fixed;
bottom: 50px;
left: 50px;
width: 180px;
height: 120px;
background:white;
border:2px solid grey;
z-index:9999;
padding:10px;
">

<b>Risk level</b><br>
🔴 HIGH (10+)<br>
🟠 MEDIUM (5-9)<br>
🟢 LOW (0-4)

</div>
"""

m.get_root().html.add_child(
    folium.Element(legend)
)


m.save(
    "railway_risk_map.html"
)

print("DONE")