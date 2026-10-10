"""convert.py এর পরীক্ষা:  python3 -m unittest discover -s tests -v   (রিপোর মূল ফোল্ডার থেকে)"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = "উপজেলা,ক্যাটাগরি,নাম,ঠিকানা,ফোন,নোট,দেখাবে?,নমুনা?,যাচাই তারিখ,অক্ষাংশ,দ্রাঘিমাংশ,ছবি,ছবির সূত্র\n"
DAYS_HEADER = "তারিখ,শেষ তারিখ,শিরোনাম,বার্তা,আইকন,নিশ্চিত?,দেখাবে?\n"


def run(data_rows="", days_rows=None):
    d = tempfile.mkdtemp()
    shutil.copy(os.path.join(ROOT, "convert.py"), d)
    open(os.path.join(d, "data.csv"), "w", encoding="utf-8-sig").write(HEADER + data_rows)
    if days_rows is not None:
        open(os.path.join(d, "days.csv"), "w", encoding="utf-8-sig").write(DAYS_HEADER + days_rows)
    r = subprocess.run([sys.executable, "convert.py"], cwd=d, capture_output=True, text=True)
    data = days = None
    if os.path.exists(os.path.join(d, "data.json")):
        data = json.load(open(os.path.join(d, "data.json"), encoding="utf-8"))
    if os.path.exists(os.path.join(d, "days.json")):
        days = json.load(open(os.path.join(d, "days.json"), encoding="utf-8"))
    shutil.rmtree(d)
    return r, data, days


class Categories(unittest.TestCase):
    def test_removed_legal_category_is_rejected(self):
        for name in ("আইনি সহায়তা", "আইনজীবী"):
            r, _, _ = run(f"ভোলা সদর,{name},ক,খ,,,হ্যাঁ,,,,,,\n")
            self.assertNotEqual(r.returncode, 0, name)

    def test_new_categories(self):
        rows = ("ভোলা সদর,আশ্রয়কেন্দ্র,ক,খ,,,হ্যাঁ,,,22.69,90.65,,\n"
                "ভোলা সদর,ফার্মেসি,ফা,খ,,,হ্যাঁ,,,,,,\n"
                "ভোলা সদর,নৌ-যোগাযোগ,নৌ,খ,,,হ্যাঁ,,,,,,\n"
                "ভোলা সদর,সরকারি অফিস,অ,খ,,,হ্যাঁ,,,,,,\n")
        r, data, _ = run(rows)
        self.assertEqual(r.returncode, 0, r.stdout)
        up = data["data"]["bhola_sadar"]
        for k in ("shelter", "pharmacy", "waterway", "govoffice"):
            self.assertIn(k, up)
        self.assertNotIn("lawyer", up)

    def test_union_still_accepted_for_info_page(self):
        r, data, _ = run("চরফ্যাশন,ইউনিয়ন পরিষদ,আহম্মদপুর ইউনিয়ন পরিষদ,খ,,,হ্যাঁ,,,,,,\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("union", data["data"]["charfasson"])

    def test_demo_row_with_phone_rejected(self):
        r, _, _ = run("ভোলা সদর,ফার্মেসি,ক,খ,01712345678,,হ্যাঁ,হ্যাঁ,,,,,\n")
        self.assertNotEqual(r.returncode, 0)

    def test_coordinates_outside_bhola_rejected(self):
        r, _, _ = run("ভোলা সদর,আশ্রয়কেন্দ্র,ক,খ,,,হ্যাঁ,,,90.65,22.69,,\n")   # উল্টে যাওয়া
        self.assertNotEqual(r.returncode, 0)

    def test_shelter_without_coordinates_warns_but_passes(self):
        r, _, _ = run("ভোলা সদর,আশ্রয়কেন্দ্র,ক,খ,,,হ্যাঁ,,,,,,\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("স্থানাঙ্ক নেই", r.stdout)


class Photos(unittest.TestCase):
    def test_six_photos_ok_seven_rejected(self):
        six = "|".join(f"a{i}.jpg" for i in range(6))
        seven = "|".join(f"a{i}.jpg" for i in range(7))
        r, _, _ = run(f"চরফ্যাশন,ভ্রমণের স্থান,স্থান,খ,,,হ্যাঁ,,,,,{six},ক\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        r, _, _ = run(f"চরফ্যাশন,ভ্রমণের স্থান,স্থান,খ,,,হ্যাঁ,,,,,{seven},ক\n")
        self.assertNotEqual(r.returncode, 0)


class Days(unittest.TestCase):
    def test_days_converted_and_sorted(self):
        rows = ("2027-04-14,,পহেলা বৈশাখ,শুভ নববর্ষ,🌸,হ্যাঁ,হ্যাঁ\n"
                "2026-10-16,2026-10-20,দুর্গোৎসব,শুভেচ্ছা,🪔,হ্যাঁ,হ্যাঁ\n"
                "2027-03-10,,ঈদ (আনুমানিক),ঈদ মোবারক,🌙,না,হ্যাঁ\n"
                "2027-05-01,,লুকানো,বার্তা,,হ্যাঁ,না\n")
        r, _, days = run("", rows)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual([d["date"] for d in days["days"]], ["2026-10-16", "2027-03-10", "2027-04-14"])
        self.assertTrue(days["days"][0]["confirmed"])
        self.assertFalse(days["days"][1]["confirmed"])      # চাঁদ-নির্ভর দিন নিশ্চিত নয়
        self.assertEqual(days["days"][0]["end"], "2026-10-20")

    def test_bad_date_blocks_everything(self):
        r, data, days = run("", "21-10-2026,,শিরোনাম,বার্তা,,হ্যাঁ,হ্যাঁ\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertIsNone(data)                             # কিছু লেখা হয়নি

    def test_end_before_start_rejected(self):
        r, _, _ = run("", "2026-10-20,2026-10-16,শিরোনাম,বার্তা,,হ্যাঁ,হ্যাঁ\n")
        self.assertNotEqual(r.returncode, 0)


class RealRepoFiles(unittest.TestCase):
    def test_real_csvs_convert_cleanly(self):
        d = tempfile.mkdtemp()
        for f in ("convert.py", "data.csv", "days.csv"):
            shutil.copy(os.path.join(ROOT, f), d)
        r = subprocess.run([sys.executable, "convert.py"], cwd=d, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        real = json.load(open(os.path.join(ROOT, "data.json"), encoding="utf-8"))
        fresh = json.load(open(os.path.join(d, "data.json"), encoding="utf-8"))
        self.assertEqual(real, fresh, "data.json পুরনো; python3 convert.py চালিয়ে commit করো")
        real_d = json.load(open(os.path.join(ROOT, "days.json"), encoding="utf-8"))
        fresh_d = json.load(open(os.path.join(d, "days.json"), encoding="utf-8"))
        self.assertEqual(real_d, fresh_d, "days.json পুরনো")
        shutil.rmtree(d)



class ImportShelters(unittest.TestCase):
    HDR = "উপজেলা,ইউনিয়ন,নাম,ধারণক্ষমতা,অক্ষাংশ,দ্রাঘিমাংশ,সূত্র,যাচাই তারিখ\n"

    def _run(self, rows, *args):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "tools"))
        shutil.copy(os.path.join(ROOT, "tools/import_shelters.py"), os.path.join(d, "tools"))
        shutil.copy(os.path.join(ROOT, "data.csv"), d)
        open(os.path.join(d, "shelters.csv"), "w", encoding="utf-8-sig").write(self.HDR + rows)
        r = subprocess.run([sys.executable, "tools/import_shelters.py", *args], cwd=d, capture_output=True, text=True)
        before = open(os.path.join(ROOT, "data.csv"), "rb").read()
        after = open(os.path.join(d, "data.csv"), "rb").read()
        return r, before == after, d

    def test_good_rows_added_then_updated_not_duplicated(self):
        row = "চরফ্যাশন,ঢালচর,পরীক্ষা আশ্রয়কেন্দ্র,১২০,21.9,90.6,ত্রাণ অফিসের তালিকা,2026-10-07\n"
        r, same, d = self._run(row)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(same)
        subprocess.run([sys.executable, "tools/import_shelters.py"], cwd=d)      # আবার চালাও
        cnt = open(os.path.join(d, "data.csv"), encoding="utf-8-sig").read().count("পরীক্ষা আশ্রয়কেন্দ্র")
        self.assertEqual(cnt, 1)
        c = subprocess.run([sys.executable, "convert.py"], cwd=d, capture_output=True, text=True) if os.path.exists(os.path.join(d, "convert.py")) else None
        shutil.rmtree(d)

    def test_missing_source_blocks_everything(self):
        r, same, _ = self._run("চরফ্যাশন,ঢালচর,ক,১০০,21.9,90.6,,\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(same)

    def test_bad_coordinates_and_capacity_blocked(self):
        for row in ("চরফ্যাশন,ঢালচর,ক,১০০,90.6,21.9,সূত্র,\n", "চরফ্যাশন,ঢালচর,ক,অনেক,21.9,90.6,সূত্র,\n"):
            r, same, _ = self._run(row)
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(same)

    def test_check_mode_writes_nothing(self):
        r, same, _ = self._run("চরফ্যাশন,ঢালচর,ক,,,,সূত্র,\n", "--check")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(same)
        self.assertIn("স্থানাঙ্ক নেই", r.stdout)



class EnglishColumns(unittest.TestCase):
    def test_english_columns_flow_to_json(self):
        r, data, _ = run("ভোলা সদর,হাসপাতাল,ক,খ,,ন,হ্যাঁ,,,,,,,Hosp,Addr,Note\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        it = data["data"]["bhola_sadar"]["hospital"][0]
        self.assertEqual((it["name_en"], it["address_en"], it["note_en"]), ("Hosp", "Addr", "Note"))

    def test_no_english_means_no_keys(self):
        r, data, _ = run("ভোলা সদর,হাসপাতাল,ক,খ,,ন,হ্যাঁ,,,,,,\n")
        self.assertNotIn("name_en", data["data"]["bhola_sadar"]["hospital"][0])

    def test_days_english(self):
        r, _, days = run("", "2027-04-14,,পহেলা বৈশাখ,বার্তা,🌸,হ্যাঁ,হ্যাঁ,New Year,Happy new year\n")
        self.assertEqual(days["days"][0]["title_en"], "New Year")

    def test_every_real_row_has_english(self):
        d = json.load(open(os.path.join(ROOT, "data.json"), encoding="utf-8"))["data"]
        missing = [it["name"] for up in d.values() for items in up.values() for it in items
                   if not it.get("name_en")]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
