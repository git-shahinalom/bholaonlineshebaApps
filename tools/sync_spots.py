#!/usr/bin/env python3
"""
অনুমোদিত ইউজার-স্পট Google Sheet থেকে এনে spots.csv বানায় (GitHub Actions প্রতি ৬ ঘণ্টায় বা হাতে চালায়)।

Sheet-এর "স্পট-প্রকাশিত" ট্যাব (Publish to web → CSV) থেকে পড়ে। ওই ট্যাবে ইমেইল কখনো থাকে না।
এই টুল আবারও যাচাই করে (Sheet ভুল হলেও রিপো নিরাপদ থাকে):
  • ধরন চেনা তালিকার ভেতরে, নাম ও উপজেলা আছে, স্থানাঙ্ক ভোলার সীমার ভেতরে
  • লেখা থেকে লিংক (http…) মুছে ফেলে (স্প্যাম/বিজ্ঞাপন ঠেকাতে), অক্ষর-সীমা প্রয়োগ করে
  • একই (উপজেলা+নাম) দুবার থাকলে একটি রাখে
ভুল সারি বাদ যায় (সতর্কবার্তাসহ), বাকিগুলো চলে। CSV ভুল ট্যাবের হলে পুরনো spots.csv অক্ষত থাকে।

চালানো:  SPOT_SHEET_CSV_URL="https://docs.google.com/.../pub?output=csv" python3 tools/sync_spots.py
পরীক্ষা:  python3 tools/sync_spots.py --csv-file local.csv
"""
import argparse
import csv
import io
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import convert  # TOUR_TYPES, UPAZILAS, lookup, clean_phone

OUT = "spots.csv"
MAX_SPOTS = 300
HEADER = ["ধরন", "নাম", "নাম (ইংরেজি)", "উপজেলা", "এলাকা", "অক্ষাংশ", "দ্রাঘিমাংশ", "বিবরণ", "বিবরণ (ইংরেজি)",
          "সুবিধা", "সময়/ফি", "ফোন", "প্রস্তাবক", "অনুমোদনের তারিখ"]
LIMITS = [20, 80, 80, 20, 60, 12, 12, 300, 300, 120, 80, 20, 40, 10]
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.I)


def clean(text, limit):
    t = re.sub(r"[\x00-\x1f\x7f]+", " ", str(text))
    t = URL_RE.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit].strip()


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "BholaOnlineSeba-spot-sync/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def process(csv_text):
    rows = list(csv.reader(io.StringIO(csv_text, newline="")))
    out, seen, warns = [], set(), []
    for n, r in enumerate(rows[1:], start=2):
        r = [c for c in r] + [""] * (14 - len(r))
        if not any(c.strip() for c in r):
            continue
        r = [clean(c, LIMITS[i]) for i, c in enumerate(r[:14])]
        ttype, name, up_raw, lat, lng = r[0], r[1], r[3], r[5], r[6]
        if ttype not in convert.TOUR_TYPES:
            warns.append(f"সারি {n} (\"{name}\"): ধরন \"{ttype}\" চেনা নয়, \"অন্যান্য\" ধরা হলো")
            r[0] = "অন্যান্য"
        up = convert.lookup(convert.UPAZILAS, up_raw)
        if not name or up in (None, "national"):
            warns.append(f"সারি {n}: নাম বা উপজেলা ঠিক নয় → \"{name}\", \"{up_raw}\", বাদ")
            continue
        try:
            la, ln = float(lat), float(lng)
        except ValueError:
            warns.append(f"সারি {n} (\"{name}\"): স্থানাঙ্ক ঠিক নয়, বাদ")
            continue
        if not (21.5 <= la <= 23.2 and 90.0 <= ln <= 91.5):
            warns.append(f"সারি {n} (\"{name}\"): স্থানাঙ্ক ভোলার বাইরে, বাদ")
            continue
        key = (up, name)
        if key in seen:
            warns.append(f"সারি {n} (\"{name}\"): দুবার আছে, বাদ")
            continue
        seen.add(key)
        r[5], r[6] = f"{la:.6f}", f"{ln:.6f}"
        r[11] = convert.clean_phone(r[11]) if re.fullmatch(r"[0-9+\-\s]{3,20}", r[11]) else ""
        out.append(r)
        if len(out) >= MAX_SPOTS:
            warns.append(f"সর্বোচ্চ {MAX_SPOTS}টি স্পট; বাকিগুলো বাদ")
            break
    return out, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-file")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.csv_file:
        text = open(a.csv_file, encoding="utf-8-sig").read()
    else:
        url = os.environ.get("SPOT_SHEET_CSV_URL", "").strip()
        if not url:
            print("ℹ SPOT_SHEET_CSV_URL সেট করা নেই, তাই স্পট-সিঙ্ক বাদ। (Settings → Secrets → Actions এ বসাও)")
            return 0
        try:
            text = http_get(url).decode("utf-8-sig")
        except Exception as e:
            print(f"❌ তালিকা আনা যায়নি: {e!r} (পুরনো spots.csv অক্ষত আছে)")
            return 1
    if not text.lstrip().startswith("ধরন"):
        print("❌ CSV এর প্রথম ঘর \"ধরন\" নয়; ভুল ট্যাবের লিংক? (পুরনো spots.csv অক্ষত আছে)")
        return 1
    spots, warns = process(text)
    for w in warns:
        print("⚠ " + w)
    if not a.dry_run:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\r\n")
        w.writerow(HEADER)
        w.writerows(spots)
        open(OUT, "w", encoding="utf-8-sig", newline="").write(buf.getvalue())
    print(f"👥 অনুমোদিত স্পট {len(spots)}টি, বাদ {len(warns)}টি সতর্কবার্তা")
    return 0


if __name__ == "__main__":
    sys.exit(main())
