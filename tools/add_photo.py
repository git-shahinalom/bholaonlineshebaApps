#!/usr/bin/env python3
"""
ভ্রমণের স্থানে ছবি যোগ: একটি ছবি ছোট করে images/ এ রাখে এবং data.csv এর সারিতে লিখে দেয়।

ব্যবহার:
  pip install pillow
  python3 tools/add_photo.py ছবি.jpg --place "জ্যাকব টাওয়ার" --slug jacob-tower --credit "রহিম উদ্দিন"

কী করে:
  • চওড়া ১২০০px, ৩০০KB এর নিচে নামায়, EXIF (অবস্থান, ক্যামেরার তথ্য) মুছে দেয়
  • এক স্থানে সর্বোচ্চ ৬টি ছবি (সংরক্ষণ-ভারসাম্য); বেশি হলে আটকে দেয়
  • data.csv এর ছবি ও ছবির সূত্র কলাম হালনাগাদ করে
  • ইমেইল কোথাও লেখে না (ইমেইল শুধু তোমার ফর্ম-শীটে থাকে)

ছবি সরাতে:  python3 tools/add_photo.py --remove ফাইল.jpg --place "জ্যাকব টাওয়ার"
"""
import argparse
import csv
import io
import os
import re
import sys

CSV_FILE = "data.csv"
IMG_DIR = "images"
MAX_PHOTOS = 6
MAX_BYTES = 300 * 1024


def load():
    raw = open(CSV_FILE, encoding="utf-8-sig", newline="").read()
    rows = list(csv.reader(io.StringIO(raw, newline="")))
    rows = [rows[0]] + [r + [""] * (13 - len(r)) for r in rows[1:]]
    return rows


def save(rows):
    out = io.StringIO()
    csv.writer(out, lineterminator="\r\n").writerows(rows)
    open(CSV_FILE, "w", encoding="utf-8-sig", newline="").write(out.getvalue())


def find_place(rows, place):
    hits = [r for r in rows[1:] if r[1] == "ভ্রমণের স্থান" and r[2].strip() == place.strip()]
    if not hits:
        sys.exit(f"❌ \"{place}\" নামে কোনো ভ্রমণের স্থান data.csv তে নেই। নামটা হুবহু মেলাও।")
    if len(hits) > 1:
        sys.exit(f"❌ \"{place}\" নামে একাধিক সারি আছে; আগে নাম আলাদা করো।")
    return hits[0]


def slug(text):
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return s or "place"


def shrink(src, dst):
    from PIL import Image, ImageOps
    img = Image.open(src)
    img = ImageOps.exif_transpose(img).convert("RGB")      # ঘোরানো ছবি সোজা করে
    if img.width > 1200:
        img = img.resize((1200, round(img.height * 1200 / img.width)))
    for q in (85, 78, 70, 62, 55, 48):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True)     # নতুন ফাইলে EXIF থাকে না
        if buf.tell() <= MAX_BYTES:
            break
    open(dst, "wb").write(buf.getvalue())
    return buf.tell()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo", nargs="?")
    ap.add_argument("--place", required=True)
    ap.add_argument("--credit", default="")
    ap.add_argument("--remove", metavar="FILE")
    ap.add_argument("--slug", default="", help="ফাইলের নামের ইংরেজি অংশ, যেমন jacob-tower")
    a = ap.parse_args()
    rows = load()
    row = find_place(rows, a.place)
    photos = [p for p in row[11].split("|") if p.strip()]

    if a.remove:
        if a.remove not in photos:
            sys.exit(f"❌ {a.remove} এই স্থানের ছবির তালিকায় নেই। আছে: {photos}")
        photos.remove(a.remove)
        row[11] = "|".join(photos)
        if not photos:
            row[12] = ""
        path = os.path.join(IMG_DIR, a.remove)
        if os.path.exists(path):
            os.remove(path)
        save(rows)
        print(f"🗑 {a.remove} সরানো হয়েছে। এখন git add -A, commit, push করো।")
        return

    if not a.photo:
        sys.exit("❌ ছবির ফাইল দাও।")
    if len(photos) >= MAX_PHOTOS:
        sys.exit(f"❌ এই স্থানে ইতিমধ্যে {len(photos)}টি ছবি আছে (সর্বোচ্চ {MAX_PHOTOS})। আগে একটা সরাও বা বদলাও।")
    os.makedirs(IMG_DIR, exist_ok=True)
    base = slug(a.slug or a.place)
    n = len(photos) + 1
    name = f"{base}-{n}.jpg"
    while os.path.exists(os.path.join(IMG_DIR, name)):
        n += 1
        name = f"{base}-{n}.jpg"
    size = shrink(a.photo, os.path.join(IMG_DIR, name))
    photos.append(name)
    row[11] = "|".join(photos)
    if a.credit:
        credits = [c.strip() for c in row[12].split(",") if c.strip()]
        if a.credit not in credits:
            credits.append(a.credit)
        row[12] = ", ".join(credits)
    save(rows)
    print(f"✅ {name} ({size // 1024} KB) রাখা হয়েছে; {a.place} এ এখন {len(photos)}টি ছবি।")
    print("➡ এখন: git add -A → git commit → git push")


if __name__ == "__main__":
    main()
