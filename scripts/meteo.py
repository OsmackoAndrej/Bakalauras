#!/usr/bin/env python3
"""
    pip install requests
    python fill_meteo.py railway_incidents_with_meteo_lt.csv -o railway_incidents_filled.csv
    python fill_meteo.py railway_incidents_with_meteo_lt.csv --geocode      
    python fill_meteo.py railway_incidents_with_meteo_lt.csv --limit 5     

"""
import argparse
import csv
import math
import sys
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

API = "https://api.meteo.lt/v1"
LOCAL_TZ = ZoneInfo("Europe/Vilnius")  
MAX_GAP = timedelta(minutes=90)         
PAUSE = 0.4                            
EXTRA_COLS = ["meteo_station", "meteo_station_distance_km",
              "meteo_observation_time_utc", "meteo_location_source"]

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def detect_encoding(path: str) -> str:
    raw = open(path, "rb").read()
    try:
        raw.decode("utf-8")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "cp1257"


session = requests.Session()
session.headers["User-Agent"] = "railway-incidents-meteo/1.0 (research script)"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.strip().lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def api_get(path: str):
    url = f"{API}{path}"
    for attempt in range(4):
        time.sleep(PAUSE)
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            if attempt == 3:
                raise
            print(f"  ! {e}; kartojimas {attempt + 1}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))


def haversine(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


geocode_cache = {}


def geocode(name: str):
    if name in geocode_cache:
        return geocode_cache[name]
    time.sleep(1.1)  
    try:
        r = session.get("https://nominatim.openstreetmap.org/search",
                        params={"q": f"{name}, Lithuania", "format": "json",
                                "limit": 1, "countrycodes": "lt"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        res = (float(data[0]["lat"]), float(data[0]["lon"])) if data else None
    except (requests.RequestException, ValueError, KeyError):
        res = None
    geocode_cache[name] = res
    return res


class Meteo:
    def __init__(self, use_geocode: bool):
        self.use_geocode = use_geocode
        self.stations = []
        for s in api_get("/stations") or []:
            c = s.get("coordinates") or {}
            if "latitude" in c:
                self.stations.append((s["code"], s["name"], c["latitude"], c["longitude"]))
        self.places = {}
        for p in api_get("/places") or []:
            c = p.get("coordinates") or {}
            if "latitude" in c:
                self.places.setdefault(norm(p["name"]), (c["latitude"], c["longitude"]))
        self.obs_cache = {}
        print(f"Stočiu: {len(self.stations)}, vietu: {len(self.places)}")

    def locate(self, station: str, region: str):
        key = norm(station)
        if key in self.places:
            return self.places[key], "places"
        if self.use_geocode and station:
            xy = geocode(station)
            if xy:
                return xy, "geocode"
        rkey = norm(region.lstrip("#").replace(" region", ""))
        if rkey in self.places:
            return self.places[rkey], "region"
        return None, None

    def nearest_stations(self, lat, lon, n=3):
        ranked = sorted(self.stations, key=lambda s: haversine(lat, lon, s[2], s[3]))
        return [(s[0], s[1], haversine(lat, lon, s[2], s[3])) for s in ranked[:n]]

    def day(self, code: str, date_str: str):
        key = (code, date_str)
        if key not in self.obs_cache:
            data = api_get(f"/stations/{code}/observations/{date_str}")
            self.obs_cache[key] = (data or {}).get("observations", [])
        return self.obs_cache[key]

    def observation(self, code: str, utc_dt: datetime):
        days = {utc_dt.date()}
        if utc_dt.hour == 0:
            days.add((utc_dt - timedelta(days=1)).date())
        if utc_dt.hour == 23:
            days.add((utc_dt + timedelta(days=1)).date())
        best, best_gap = None, None
        for d in days:
            for o in self.day(code, d.isoformat()):
                t = datetime.fromisoformat(o["observationTimeUtc"].replace(" ", "T"))
                t = t.replace(tzinfo=timezone.utc)
                gap = abs(t - utc_dt)
                if best_gap is None or gap < best_gap:
                    best, best_gap = (o, t), gap
        if best and best_gap <= MAX_GAP:
            return best
        return None


def fmt(v):
    return "" if v is None else str(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", default="railway_incidents_with_meteo_lt.csv",
                    help="įvesties CSV (pagal nutylėjimą railway_incidents_with_meteo_lt.csv esant dabartinei direktorijai)")
    ap.add_argument("-o", "--output", default="railway_incidents_filled.csv")
    ap.add_argument("--geocode", action="store_true", help="tikslinti koordinates per Nominatim (OSM)")
    ap.add_argument("--limit", type=int, default=0, help="apdoroti tik pirmas N eilutes")
    ap.add_argument("--encoding", default="utf-8-sig",
                    help="išvesties CSV kodavimas: utf-8-sig (pagal nutylėjimą, Excel rodo ąčęėįšųūž "
                         "teisingai) arba cp1257 (lietuviška Windows-koduotė, Excel rodo ąčęėįšųūž teisingai tik Windows)")
    args = ap.parse_args()

    meteo = Meteo(args.geocode)
    ok = fail = 0

    with open(args.input, encoding=detect_encoding(args.input), newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        rows = [r for r in reader if r]
    if args.limit:
        rows = rows[:args.limit]

    out_rows = []
    for i, row in enumerate(rows, 1):
        region, station, t_str = row[-6], row[-5], row[-4]
        status = "nėra duomenų"
        extra = ["", "", "", ""]
        try:
            local = datetime.fromisoformat(t_str.strip().replace(" ", "T")).replace(tzinfo=LOCAL_TZ)
            utc_dt = local.astimezone(timezone.utc)
            xy, src = meteo.locate(station, region)
            if xy:
                for code, name, dist in meteo.nearest_stations(*xy):
                    hit = meteo.observation(code, utc_dt)
                    if hit:
                        o, t = hit
                        row[-3] = fmt(o.get("airTemperature"))
                        row[-2] = fmt(o.get("windSpeed"))
                        row[-1] = fmt(o.get("conditionCode"))
                        extra = [name, f"{dist:.1f}", t.strftime("%Y-%m-%d %H:%M"), src]
                        status = f"{name} ({dist:.0f} км, {src})"
                        break
            else:
                status = "vieta nerasta"
        except ValueError:
            status = f"laikas neapdorotas: {t_str!r}"
        ok, fail = (ok + 1, fail) if extra[0] else (ok, fail + 1)
        print(f"[{i}/{len(rows)}] {station or '-'} {t_str}: {status}")
        row += [""] * max(0, len(header) - len(row))
        out_rows.append(row + extra)

    with open(args.output, "w", encoding=args.encoding, errors="replace", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header + EXTRA_COLS)
        w.writerows(out_rows)

    print(f"\nГотовo: {ok} užpildyta, {fail} be duomenų -> {args.output}")
    print("duomenu šaltinis: Lietuvos hidrometeorologijos tarnyba (Meteo LT), CC BY-SA 4.0")


if __name__ == "__main__":  
    main()