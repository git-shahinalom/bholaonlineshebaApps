"""weather.py এর পরীক্ষা (ইন্টারনেট ছাড়া, Open-Meteo এর উত্তরের মতো নকল ডেটা দিয়ে)।"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weather  # noqa: E402


def fake(temp=29.0, gust=30.0, rain=2.0, tmax=33.0):
    return {
        "current": {"temperature_2m": temp, "apparent_temperature": temp + 3, "relative_humidity_2m": 80,
                    "precipitation": 0.0, "weather_code": 2, "wind_speed_10m": 14.0,
                    "wind_gusts_10m": gust, "wind_direction_10m": 200},
        "daily": {"time": ["2026-10-08", "2026-10-09", "2026-10-10"], "weather_code": [2, 61, 3],
                  "temperature_2m_max": [tmax] * 3, "temperature_2m_min": [26.0] * 3,
                  "precipitation_sum": [rain, 5.0, 0.0], "precipitation_probability_max": [40, 70, 10],
                  "wind_gusts_10m_max": [gust] * 3},
    }


class Weather(unittest.TestCase):
    def test_all_regions_and_old_app_compat(self):
        out = weather.build([fake(temp=20 + i) for i in range(len(weather.REGIONS))])
        self.assertEqual(set(out["regions"]), {r[0] for r in weather.REGIONS})
        # পুরনো অ্যাপ যা পড়ে: উপরের স্তরে current/daily/auto ভোলা সদরেরই
        self.assertEqual(out["current"]["temp"], 20.0)
        self.assertEqual(out["current"], out["regions"]["bhola_sadar"]["current"])
        self.assertEqual(len(out["daily"]), 3)
        self.assertEqual(out["regions"]["monpura"]["current"]["temp"], 26.0)
        self.assertIn("lat", out["regions"]["charfasson"])

    def test_region_keys_match_converter(self):
        import convert
        for key, *_ in weather.REGIONS:
            self.assertIn(key, convert.AVAILABLE, f"{key} convert.py তে নেই")

    def test_coordinates_inside_bhola_and_distinct(self):
        pts = set()
        for key, name, lat, lon in weather.REGIONS:
            self.assertTrue(21.5 <= lat <= 23.2 and 90.0 <= lon <= 91.5, key)
            pts.add((lat, lon))
        self.assertEqual(len(pts), len(weather.REGIONS))

    def test_each_region_gets_its_own_warning(self):
        raws = [fake() for _ in weather.REGIONS]
        raws[4] = fake(gust=70.0)                       # শুধু চরফ্যাশনে ঝড়ো হাওয়া
        out = weather.build(raws)
        self.assertEqual(out["regions"]["charfasson"]["auto"][0]["hazard"], "ঝোড়ো হাওয়া")
        self.assertEqual(out["regions"]["lalmohon"]["auto"], [])
        self.assertEqual(out["auto"], [])               # ভোলা সদর শান্ত

    def test_wrong_number_of_regions_fails(self):
        with self.assertRaises(ValueError):
            weather.build([fake()] * 3)

    def test_request_has_all_points(self):
        self.assertEqual(weather.PARAMS["latitude"].count(","), len(weather.REGIONS) - 1)


if __name__ == "__main__":
    unittest.main()
