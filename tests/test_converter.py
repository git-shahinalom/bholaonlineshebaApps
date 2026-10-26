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



class SyncPhotos(unittest.TestCase):
    """tools/sync_photos.py ও photos.csv মেলানো (ইন্টারনেট ছাড়া, নকল ছবি দিয়ে)।"""

    def _env(self):
        from PIL import Image
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "tools"))
        os.makedirs(os.path.join(d, "images"))
        os.makedirs(os.path.join(d, "fake"))
        for f in ("tools/sync_photos.py", "tools/add_photo.py", "convert.py"):
            shutil.copy(os.path.join(ROOT, f), os.path.join(d, f))
        open(os.path.join(d, "data.csv"), "w", encoding="utf-8-sig").write(
            HEADER + "চরফ্যাশন,ভ্রমণের স্থান,জ্যাকব টাওয়ার,খ,,ন,হ্যাঁ,,,,,,\n")
        Image.effect_noise((1600, 900), 60).convert("RGB").save(os.path.join(d, "fake", "GOODID1234567890.jpg"))
        Image.new("RGB", (300, 200)).save(os.path.join(d, "fake", "TINYID1234567890.jpg"))
        return d

    def _run(self, d, rows):
        open(os.path.join(d, "sheet.csv"), "w", encoding="utf-8-sig").write("স্থান,ফাইল আইডি,ছবির সূত্র,অনুমোদনের তারিখ\n" + rows)
        env = dict(os.environ, SYNC_PHOTOS_LOCAL_DIR=os.path.join(d, "fake"))
        r = subprocess.run([sys.executable, "tools/sync_photos.py", "--csv-file", "sheet.csv"], cwd=d, env=env, capture_output=True, text=True)
        c = subprocess.run([sys.executable, "convert.py"], cwd=d, capture_output=True, text=True)
        return r, c

    def test_approve_then_remove_flow(self):
        d = self._env()
        r, c = self._run(d, "জ্যাকব টাওয়ার,GOODID1234567890,রহিম,2026-10-19\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(c.returncode, 0, c.stdout)
        item = json.load(open(os.path.join(d, "data.json"), encoding="utf-8"))["data"]["charfasson"]["tourism"][0]
        self.assertEqual(item["photos"], ["u-GOODID1234567890.jpg"])
        self.assertEqual(item["credit"], "রহিম")
        self.assertLess(os.path.getsize(os.path.join(d, "images", "u-GOODID1234567890.jpg")), 300 * 1024)
        # "সরানো হোক" = তালিকা থেকে বাদ → ছবিও মোছা, অ্যাপের ডেটা থেকেও
        r, c = self._run(d, "")
        self.assertEqual(c.returncode, 0, c.stdout)
        self.assertFalse(os.path.exists(os.path.join(d, "images", "u-GOODID1234567890.jpg")))
        item = json.load(open(os.path.join(d, "data.json"), encoding="utf-8"))["data"]["charfasson"]["tourism"][0]
        self.assertNotIn("photos", item)

    def test_tiny_photo_rejected_and_bad_place_blocks_build(self):
        d = self._env()
        r, c = self._run(d, "জ্যাকব টাওয়ার,TINYID1234567890,ক,2026-10-19\n")
        self.assertIn("বাদ", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(d, "images", "u-TINYID1234567890.jpg")))
        r, c = self._run(d, "অজানা স্থান,GOODID1234567890,ক,2026-10-19\n")
        self.assertNotEqual(c.returncode, 0)                     # নাম না মিললে ডেটা-বিল্ড আটকায়

    def test_wrong_tab_does_not_wipe_photos(self):
        d = self._env()
        self._run(d, "জ্যাকব টাওয়ার,GOODID1234567890,রহিম,2026-10-19\n")
        open(os.path.join(d, "sheet.csv"), "w", encoding="utf-8-sig").write("Timestamp,Email\n1,a@b.c\n")
        env = dict(os.environ, SYNC_PHOTOS_LOCAL_DIR=os.path.join(d, "fake"))
        r = subprocess.run([sys.executable, "tools/sync_photos.py", "--csv-file", "sheet.csv"], cwd=d, env=env, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(d, "images", "u-GOODID1234567890.jpg")))   # অক্ষত



class Spots(unittest.TestCase):
    """tools/sync_spots.py ও spots.csv মেলানো।"""

    SHEET_HDR = "ধরন,নাম,নাম (ইংরেজি),উপজেলা,এলাকা,অক্ষাংশ,দ্রাঘিমাংশ,বিবরণ,বিবরণ (ইংরেজি),সুবিধা,সময়/ফি,ফোন,প্রস্তাবক,অনুমোদনের তারিখ\n"

    def _env(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "tools"))
        os.makedirs(os.path.join(d, "images"))
        for f in ("tools/sync_spots.py", "convert.py"):
            shutil.copy(os.path.join(ROOT, f), os.path.join(d, f))
        open(os.path.join(d, "data.csv"), "w", encoding="utf-8-sig").write(
            HEADER.rstrip("\n") + ",নাম (ইংরেজি),ঠিকানা (ইংরেজি),নোট (ইংরেজি),ধরন\n"
            "চরফ্যাশন,ভ্রমণের স্থান,জ্যাকব টাওয়ার,খ,,ন,হ্যাঁ,,,,,,,,,,দর্শনীয়\n")
        return d

    def _run(self, d, rows):
        open(os.path.join(d, "sheet.csv"), "w", encoding="utf-8-sig").write(self.SHEET_HDR + rows)
        r = subprocess.run([sys.executable, "tools/sync_spots.py", "--csv-file", "sheet.csv"], cwd=d, capture_output=True, text=True)
        c = subprocess.run([sys.executable, "convert.py"], cwd=d, capture_output=True, text=True)
        data = json.load(open(os.path.join(d, "data.json"), encoding="utf-8"))["data"] if c.returncode == 0 else None
        return r, c, data

    def test_approved_spot_reaches_app_data(self):
        d = self._env()
        r, c, data = self._run(d, "রেস্টুরেন্ট,স্কাই ভিউ রুফটপ,Sky View Rooftop,ভোলা সদর,লঞ্চঘাট রোড,22.6850,90.6480,"
                                  "নদীর ধারে রুফটপ রেস্টুরেন্ট,Riverside rooftop restaurant,পার্কিং;পরিবার-বান্ধব,বিকাল ৪টা–রাত ১০টা,01712345678,রহিম,2026-10-21\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(c.returncode, 0, c.stdout)
        item = [x for x in data["bhola_sadar"]["tourism"] if x["name"] == "স্কাই ভিউ রুফটপ"][0]
        self.assertEqual(item["type"], "restaurant")
        self.assertEqual(item["by"], "রহিম")
        self.assertEqual(item["name_en"], "Sky View Rooftop")
        self.assertEqual(item["phone"], "01712345678")
        self.assertTrue(item["spot"])
        self.assertAlmostEqual(item["lat"], 22.685)
        self.assertIn("চরফ্যাশন", [k for k in data if any(i["name"] == "জ্যাকব টাওয়ার" for i in data[k]["tourism"])][0] and "চরফ্যাশন")
        jt = [x for x in data["charfasson"]["tourism"] if x["name"] == "জ্যাকব টাওয়ার"][0]
        self.assertEqual(jt["type"], "landmark")                  # data.csv এর ধরন-কলাম

    def test_bad_rows_dropped_and_links_stripped(self):
        d = self._env()
        rows = ("পার্ক,ভুল জায়গা,,ভোলা সদর,,40.0,10.0,x,,,,,,2026-10-21\n"                    # ভোলার বাইরে
                "পার্ক,স্প্যাম পার্ক,,ভোলা সদর,,22.7,90.6,দেখুন https://spam.example/buy এখানে,,,,,,2026-10-21\n"
                "অজানা-ধরন,ধরন ভুল,,মনপুরা,,22.3,90.98,ভালো জায়গা,,,,,,2026-10-21\n"
                "পার্ক,,,ভোলা সদর,,22.7,90.6,নাম নেই,,,,,,2026-10-21\n")
        r, c, data = self._run(d, rows)
        self.assertEqual(c.returncode, 0, c.stdout)
        names = [x["name"] for x in data["bhola_sadar"]["tourism"]] + [x["name"] for x in data["monpura"]["tourism"]]
        self.assertNotIn("ভুল জায়গা", names)
        spam = [x for x in data["bhola_sadar"]["tourism"] if x["name"] == "স্প্যাম পার্ক"][0]
        self.assertNotIn("http", spam["note"])
        odd = [x for x in data["monpura"]["tourism"] if x["name"] == "ধরন ভুল"][0]
        self.assertEqual(odd["type"], "other")

    def test_duplicate_of_existing_place_skipped(self):
        d = self._env()
        r, c, data = self._run(d, "দর্শনীয়,জ্যাকব টাওয়ার,,চরফ্যাশন,,22.18,90.75,নকল,,,,,,2026-10-21\n")
        self.assertEqual(c.returncode, 0, c.stdout)
        self.assertEqual(len([x for x in data["charfasson"]["tourism"] if x["name"] == "জ্যাকব টাওয়ার"]), 1)

    def test_wrong_tab_keeps_old_file(self):
        d = self._env()
        self._run(d, "পার্ক,ভালো পার্ক,,ভোলা সদর,,22.7,90.6,ঠিক,,,,,,2026-10-21\n")
        open(os.path.join(d, "sheet.csv"), "w", encoding="utf-8-sig").write("Timestamp,Email\n1,a@b.c\n")
        r = subprocess.run([sys.executable, "tools/sync_spots.py", "--csv-file", "sheet.csv"], cwd=d, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ভালো পার্ক", open(os.path.join(d, "spots.csv"), encoding="utf-8-sig").read())

    def test_photo_for_spot_by_name(self):
        from PIL import Image
        d = self._env()
        Image.new("RGB", (800, 500)).save(os.path.join(d, "images", "u-abc1234567890xyz.jpg"))
        open(os.path.join(d, "photos.csv"), "w", encoding="utf-8-sig").write(
            "স্থান,ফাইল,ছবির সূত্র,অনুমোদনের তারিখ,ড্রাইভ আইডি\nভালো লেক,u-abc1234567890xyz.jpg,করিম,2026-10-21,abc1234567890xyz\n")
        r, c, data = self._run(d, "জলাশয়,ভালো লেক,,তজুমদ্দিন,,22.3,90.87,সুন্দর লেক,,,,,,2026-10-21\n")
        self.assertEqual(c.returncode, 0, c.stdout)
        lake = [x for x in data["tazumuddin"]["tourism"] if x["name"] == "ভালো লেক"][0]
        self.assertEqual(lake["photos"], ["u-abc1234567890xyz.jpg"])
        self.assertEqual(lake["credit"], "করিম")


if __name__ == "__main__":
    unittest.main()
