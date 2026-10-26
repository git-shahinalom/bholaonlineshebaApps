#!/usr/bin/env python3
"""
অনুমোদিত ইউজার-ছবি Google Sheet থেকে এনে রিপোতে রাখে (GitHub Actions প্রতি ৬ ঘণ্টায় বা হাতে চালায়)।

কীভাবে কাজ করে:
  ১. Sheet-এর "প্রকাশিত" ট্যাব (Publish to web → CSV) থেকে অনুমোদিত তালিকা পড়ে।
     এই ট্যাবে শুধু: স্থান, ফাইল আইডি, ছবির সূত্র (নাম), অনুমোদনের তারিখ। ইমেইল কখনো থাকে না।
  ২. নতুন ছবি Google Drive থেকে নামায়, মান যাচাই করে (কমপক্ষে 700×400),
     ১২০০px ও ≤৩০০KB এ ছোট করে, EXIF (লোকেশন ইত্যাদি) মুছে images/u-<আইডি>.jpg রাখে।
  ৩. তালিকা থেকে সরে গেছে এমন ছবি images/ থেকে মুছে দেয় (সরানো = Sheet-এ "সরানো হোক")।
  ৪. photos.csv নতুন করে লেখে; convert.py এটা data.json এ মিলিয়ে নেয়।

চালানো:  PHOTO_SHEET_CSV_URL="https://docs.google.com/.../pub?output=csv" python3 tools/sync_photos.py
পরীক্ষা:  python3 tools/sync_photos.py --csv-file local.csv     (ইন্টারনেট ছাড়া; ছবি SYNC_PHOTOS_LOCAL_DIR/<আইডি>.jpg থেকে)
"""
import argparse
import csv
import io
import os
import re
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

IMG_DIR = "images"
PHOTOS_CSV = "photos.csv"
MAX_PER_PLACE = 6
MIN_W, MIN_H = 700, 400          # এর চেয়ে ছোট ছবি নেওয়া হয় না ("সুন্দর ছবি" এর ন্যূনতম শর্ত)
ID_RE = re.compile(r"[A-Za-z0-9_-]{10,}")
HEADER = ["স্থান", "ফাইল", "ছবির সূত্র", "অনুমোদনের তারিখ", "ড্রাইভ আইডি"]


def fname_for(file_id):
    return f"u-{file_id[:16]}.jpg"


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "BholaOnlineSeba-photo-sync/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), r.headers.get("Content-Type", "")


def fetch_image(file_id):
    """ছবির বাইট। পরীক্ষার সময় SYNC_PHOTOS_LOCAL_DIR থেকে; নাহলে Drive থেকে।"""
    local = os.environ.get("SYNC_PHOTOS_LOCAL_DIR")
    if local:
        return open(os.path.join(local, file_id + ".jpg"), "rb").read()
    last = None
    for url in (f"https://drive.google.com/thumbnail?id={file_id}&sz=w1600",
                f"https://drive.usercontent.google.com/download?id={file_id}&export=download"):
        try:
            data, ctype = http_get(url)
            if ctype.startswith("image/") or data[:3] == b"\xff\xd8\xff":
                return data
            last = RuntimeError(f"ছবি নয় (Content-Type: {ctype}); ফাইল কি 'লিংকধারী সবাই দেখতে পারবে' করা আছে?")
        except Exception as e:
            last = e
    raise last


def read_approved(csv_text):
    """CSV → [(স্থান, আইডি, সূত্র, তারিখ)] (ভুল সারি বাদ, স্থানপ্রতি সীমা প্রয়োগ)।"""
    rows = list(csv.reader(io.StringIO(csv_text, newline="")))
    out, per_place = [], {}
    for n, r in enumerate(rows[1:], start=2):
        r = [c.strip() for c in r] + [""] * (4 - len(r))
        place, fid, credit, date = r[:4]
        if not any(r):
            continue
        if not place or not ID_RE.fullmatch(fid):
            print(f"⚠ সারি {n} বাদ: স্থানের নাম বা ফাইল আইডি ঠিক নয়")
            continue
        credit = re.sub(r"[,|\n\r]+", " ", credit).strip()[:40] or "ব্যবহারকারী"
        per_place[place] = per_place.get(place, 0) + 1
        if per_place[place] > MAX_PER_PLACE:
            print(f"⚠ সারি {n} বাদ: \"{place}\" এ ইতিমধ্যে {MAX_PER_PLACE}টি ছবি")
            continue
        out.append((place, fid, credit, date))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-file", help="URL এর বদলে স্থানীয় CSV (পরীক্ষার জন্য)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.csv_file:
        text = open(a.csv_file, encoding="utf-8-sig").read()
    else:
        url = os.environ.get("PHOTO_SHEET_CSV_URL", "").strip()
        if not url:
            print("ℹ PHOTO_SHEET_CSV_URL সেট করা নেই, তাই ছবি-সিঙ্ক বাদ। (Settings → Secrets → Actions এ বসাও)")
            return 0
        try:
            text = http_get(url)[0].decode("utf-8-sig")
        except Exception as e:
            print(f"❌ তালিকা আনা যায়নি: {e!r} (পুরনো ছবি অক্ষত আছে)")
            return 1
    if not text.lstrip().startswith("স্থান"):
        print("❌ CSV এর প্রথম ঘর \"স্থান\" নয়; ভুল ট্যাবের লিংক দেওয়া হয়নি তো? (পুরনো ছবি অক্ষত আছে)")
        return 1

    approved = read_approved(text)
    os.makedirs(IMG_DIR, exist_ok=True)
    wanted, rows_out, added, rejected = set(), [], 0, 0
    for place, fid, credit, date in approved:
        fname = fname_for(fid)
        path = os.path.join(IMG_DIR, fname)
        if not os.path.exists(path):
            try:
                from add_photo import shrink
                from PIL import Image
                data = fetch_image(fid)
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as t:
                    t.write(data)
                    tmp = t.name
                try:
                    w, h = Image.open(tmp).size
                    if w < MIN_W or h < MIN_H:
                        print(f"✖ {fid[:8]}… ({place}) বাদ: {w}×{h}, কমপক্ষে {MIN_W}×{MIN_H} লাগে")
                        rejected += 1
                        continue
                    if not a.dry_run:
                        size = shrink(tmp, path)
                        print(f"✅ নতুন: {fname} ({size // 1024} KB) → {place}")
                    added += 1
                finally:
                    os.unlink(tmp)
            except Exception as e:
                print(f"⚠ {fid[:8]}… ({place}) আনা যায়নি: {e!r}; পরের বার আবার চেষ্টা হবে")
                continue
        wanted.add(fname)
        rows_out.append([place, fname, credit, date, fid])

    removed = 0
    for f in sorted(os.listdir(IMG_DIR)):
        if f.startswith("u-") and f.endswith(".jpg") and f not in wanted:
            if not a.dry_run:
                os.remove(os.path.join(IMG_DIR, f))
            print(f"🗑 সরানো: {f}")
            removed += 1

    if not a.dry_run:
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\r\n")
        w.writerow(HEADER)
        w.writerows(rows_out)
        open(PHOTOS_CSV, "w", encoding="utf-8-sig", newline="").write(out.getvalue())
    print(f"📷 অনুমোদিত {len(rows_out)}টি · নতুন {added}টি · মান-যাচাইয়ে বাদ {rejected}টি · সরানো {removed}টি")
    return 0


if __name__ == "__main__":
    sys.exit(main())
