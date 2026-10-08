#!/usr/bin/env python3
"""
Open-Meteo থেকে ভোলার ৭ উপজেলার আবহাওয়া এনে weather.json বানায় (উপরের স্তরে ভোলা সদর, "regions" এ সব অঞ্চল)।
ব্যবহার:  python3 weather.py [আউটপুট-ফাইল]

আবহাওয়ার তথ্য: Open-Meteo.com (অ-বাণিজ্যিক ব্যবহার, CC BY 4.0) - অ্যাপে এই উৎসের লিংক দেখানো হয়।
এখানে বানানো "auto" সতর্কতাগুলো শুধু আবহাওয়া-মডেলের হিসাব, সরকারি সতর্কবার্তা নয়।
"""
import json
import sys
import time
import urllib.parse
import urllib.request

LOCATION = "ভোলা"

# (অ্যাপের উপজেলা-কী, নাম, অক্ষাংশ, দ্রাঘিমাংশ)। কী অবশ্যই convert.py র AVAILABLE এর সাথে মিলতে হবে।
# স্থানাঙ্ক উপজেলা সদরের আনুমানিক; আবহাওয়া-মডেলের গ্রিড প্রায় ১০ কিমি, তাই এতটুকু অমিলে কিছু যায় আসে না।
REGIONS = [
    ("bhola_sadar", "ভোলা সদর", 22.685, 90.648),
    ("borhanuddin", "বোরহানউদ্দিন", 22.490, 90.720),
    ("dowlatkhan", "দৌলতখান", 22.570, 90.730),
    ("lalmohon", "লালমোহন", 22.330, 90.740),
    ("charfasson", "চরফ্যাশন", 22.180, 90.750),
    ("tazumuddin", "তজুমদ্দিন", 22.300, 90.870),
    ("monpura", "মনপুরা", 22.2983, 90.980),
]

PARAMS = {
    "latitude": ",".join(str(r[2]) for r in REGIONS),
    "longitude": ",".join(str(r[3]) for r in REGIONS),
    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,"
               "weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
             "precipitation_probability_max,wind_gusts_10m_max",
    "timezone": "Asia/Dhaka",
    "forecast_days": 3,
    "wind_speed_unit": "kmh",
}
URL = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(PARAMS, safe=",/")

# অটো-সতর্কতার সীমা (শুধু তথ্যমূলক)
GUST_KMH = 50       # দমকা হাওয়া
RAIN_MM = 50        # ২৪ ঘণ্টায় বৃষ্টি
HEAT_C = 38         # সর্বোচ্চ তাপমাত্রা


def fetch():
    req = urllib.request.Request(URL, headers={
        "User-Agent": "BholaOnlineSeba/1.0 (github.com/git-shahinalom/bholaonlineshebaApps)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def num(v, nd=0, default=0):
    try:
        x = round(float(v), nd)
        return int(x) if nd == 0 else x
    except (TypeError, ValueError):
        return default


def build_one(raw):
    """একটি অঞ্চলের current, daily ও auto।"""
    cur = raw["current"]
    d = raw["daily"]
    days = []
    for i in range(len(d["time"])):
        days.append({
            "date": d["time"][i],
            "code": num(d["weather_code"][i]),
            "max": num(d["temperature_2m_max"][i]),
            "min": num(d["temperature_2m_min"][i]),
            "rain": num(d["precipitation_sum"][i], 1),
            "rainProb": num(d["precipitation_probability_max"][i]),
            "gustMax": num(d["wind_gusts_10m_max"][i]),
        })

    auto = []
    near = days[:2]                                   # আজ ও আগামীকাল
    gust = max([num(cur.get("wind_gusts_10m"))] + [x["gustMax"] for x in near])
    rain = max([x["rain"] for x in near] + [0])
    tmax = max([x["max"] for x in near] + [0])
    if gust >= GUST_KMH:
        auto.append({"hazard": "ঝোড়ো হাওয়া", "text": f"দমকা হাওয়া প্রায় {gust} কিমি/ঘণ্টা পর্যন্ত হতে পারে"})
    if rain >= RAIN_MM:
        auto.append({"hazard": "ভারী বৃষ্টি", "text": f"২৪ ঘণ্টায় প্রায় {int(rain)} মিমি বৃষ্টির সম্ভাবনা"})
    if tmax >= HEAT_C:
        auto.append({"hazard": "গরম", "text": f"তাপমাত্রা {tmax}° পর্যন্ত উঠতে পারে"})

    return {
        "current": {
            "temp": num(cur["temperature_2m"], 1),
            "feels": num(cur["apparent_temperature"], 1),
            "humidity": num(cur["relative_humidity_2m"]),
            "rain": num(cur["precipitation"], 1),
            "code": num(cur["weather_code"]),
            "wind": num(cur["wind_speed_10m"]),
            "gust": num(cur["wind_gusts_10m"]),
            "dir": num(cur["wind_direction_10m"]),
        },
        "daily": days,
        "auto": auto,
    }


def build(raw):
    """raw: Open-Meteo এর উত্তর। একাধিক স্থান চাইলে সেটা একটি তালিকা (একটিতে শুধু ডিকশনারি)।"""
    if isinstance(raw, dict):
        raw = [raw]
    if len(raw) != len(REGIONS):
        raise ValueError(f"{len(REGIONS)}টি অঞ্চল চাওয়া হয়েছিল, এসেছে {len(raw)}টি")
    regions = {}
    for (key, name, lat, lon), r in zip(REGIONS, raw):
        one = build_one(r)
        one.update({"name": name, "lat": lat, "lon": lon})
        regions[key] = one
    main = regions[REGIONS[0][0]]                    # ভোলা সদর; আগের অ্যাপ-সংস্করণ এটাই পড়ে
    return {
        "updated_ms": int(time.time() * 1000),
        "source": "Open-Meteo.com",
        "location": LOCATION,
        "current": main["current"],
        "daily": main["daily"],
        "auto": main["auto"],
        "regions": regions,
    }


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "weather.json"
    try:
        data = build(fetch())
    except Exception as e:                      # নেটওয়ার্ক/ফরম্যাট সমস্যা: পুরনো ফাইল অক্ষত থাকে
        print(f"❌ আবহাওয়া আনা যায়নি: {e!r}")
        sys.exit(1)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"✅ {out} লেখা হয়েছে: ভোলা {data['current']['temp']}°, {len(data['regions'])}টি অঞ্চল, ভোলার অটো-সতর্কতা {len(data['auto'])}টি")


if __name__ == "__main__":
    main()
