#!/usr/bin/env python3
"""
data.csv  →  data.json   (Bhola Online Seba)

কোনো ভুল থাকলে data.json বদলায় না (পুরনো ডেটাই অ্যাপে থাকে) এবং ভুলগুলো তালিকা করে দেখায়।
"""
import csv
import io
import json
import re
import sys
import unicodedata

CSV_FILE = "data.csv"
JSON_FILE = "data.json"

# শীটে বাংলা নাম লিখলেও চলবে, ইংরেজি কী (key) লিখলেও চলবে
UPAZILAS = {
    "ভোলা সদর": "bhola_sadar",
    "বোরহানউদ্দিন": "borhanuddin",
    "চরফ্যাশন": "charfasson",
    "দৌলতখান": "dowlatkhan",
    "লালমোহন": "lalmohon",
    "মনপুরা": "monpura",
    "তজুমদ্দিন": "tazumuddin",
    "জাতীয়": "national",          # সারা দেশের জরুরি হটলাইন (৯৯৯ ইত্যাদি)
}

CATEGORIES = {
    "হাসপাতাল": "hospital",
    "এ্যাম্বুলেন্স": "ambulance",
    "পুলিশ": "police",
    "আইনজীবী": "lawyer",              # পুরনো নাম, চলবে
    "আইনি সহায়তা": "lawyer",         # নতুন দেখানোর নাম (কী বদলায়নি)
    "আশ্রয়কেন্দ্র": "shelter",
    "সরকারি অফিস": "govoffice",
    "নৌ-যোগাযোগ": "waterway",
    "ফার্মেসি": "pharmacy",
    "ভ্রমণের স্থান": "tourism",
    "ইউনিয়ন পরিষদ": "union",
    "জরুরি বিদ্যুৎ": "electricity",
    "রেন্ট-এ-কার": "rentcar",
    "ফায়ার সার্ভিস": "fire",
    "হটলাইন": "hotline",
}

# অ্যাপে কোন উপজেলায় কোন কার্ড আছে
ALL12 = ["hospital", "ambulance", "police", "fire", "shelter", "electricity",
         "pharmacy", "waterway", "govoffice", "tourism", "lawyer", "rentcar"]
# "union" অ্যাপের গ্রিডে কার্ড নয়; ডেটা থাকে, দেখায় "তথ্য বাতায়ন" পাতায়।
UPAZILA_KEYS = ALL12 + ["union"]
AVAILABLE = {
    "bhola_sadar": UPAZILA_KEYS,
    "borhanuddin": UPAZILA_KEYS,
    "charfasson": UPAZILA_KEYS,
    "dowlatkhan": UPAZILA_KEYS,
    "lalmohon": UPAZILA_KEYS,
    "monpura": UPAZILA_KEYS,
    "tazumuddin": UPAZILA_KEYS,
    "national": ["hotline"],
}
# অ্যাপের প্রতিটি উপজেলায় এখন ১২টি ক্যাটাগরির কার্ড আছে।

MAX_PHOTOS_PER_PLACE = 6      # অ্যাপ ও GitHub-এর সংরক্ষণ-ভারসাম্য: এক স্থানে সর্বোচ্চ ৬টি ছবি
DAYS_CSV = "days.csv"
DAYS_JSON = "days.json"

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def fail(msg):
    print("❌ " + msg)
    sys.exit(1)


def norm(s):
    s = unicodedata.normalize("NFC", str(s))
    s = re.sub(r"[\s\u200c\u200d]+", "", s)          # স্পেস ও অদৃশ্য অক্ষর বাদ
    s = re.sub(r"উপজেলা$", "", s)
    return s.replace("ভ্রমন", "ভ্রমণ").replace("-", "")


def lookup(table, value):
    v = norm(value)
    for bn, key in table.items():
        if norm(bn) == v or key == str(value).strip().lower():
            return key
    return None


def clean_phone(raw):
    p = unicodedata.normalize("NFC", str(raw)).strip().replace(" ", "").translate(BN_DIGITS)
    if re.fullmatch(r"1\d{9}", p):                    # Excel শুরুর ০ কেটে ফেললে ফিরিয়ে আনি
        p = "0" + p
    return p


def read_rows():
    try:
        raw = open(CSV_FILE, "rb").read()
    except FileNotFoundError:
        fail(f"{CSV_FILE} ফাইল পাওয়া যায়নি।")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        fail("ফাইলটা UTF-8 এ সেভ করা হয়নি, বাংলা অক্ষর নষ্ট হয়েছে। "
             "Excel এ Save As করার সময় 'CSV UTF-8 (Comma delimited)' বেছে নাও।")
    first = text.splitlines()[0] if text.strip() else ""
    delim = ";" if first.count(";") > first.count(",") else ","
    return list(csv.reader(io.StringIO(text, newline=""), delimiter=delim))


def build_days(problems):
    """days.csv → days.json এর ভেতরের তালিকা। ফাইল না থাকলে None।"""
    try:
        raw = open(DAYS_CSV, "rb").read()
    except FileNotFoundError:
        return None
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        problems.append(f"{DAYS_CSV}: UTF-8 এ সেভ করা হয়নি")
        return None
    rows = list(csv.reader(io.StringIO(text, newline="")))
    out = []
    for i, r in enumerate(rows[1:], start=2):
        r = [c.strip() for c in r] + [""] * (7 - len(r))
        date, end, title, message, icon, confirmed, show = r[:7]
        if not any(r) or show.lower() in ("না", "no", "false", "0"):
            continue
        if not title or not message:
            problems.append(f"{DAYS_CSV} সারি {i}: শিরোনাম ও বার্তা দুটোই লাগবে")
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            problems.append(f"{DAYS_CSV} সারি {i}: তারিখ 2026-10-21 ফরম্যাটে হতে হবে → \"{date}\"")
            continue
        if end and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", end) or end < date):
            problems.append(f"{DAYS_CSV} সারি {i}: শেষ তারিখ ঠিক নয় → \"{end}\"")
            continue
        ok = confirmed.lower() in ("হ্যাঁ", "yes", "true", "1")
        item = {"date": date, "title": title, "message": message, "confirmed": ok}
        if end:
            item["end"] = end
        if icon:
            item["icon"] = icon
        out.append(item)
    out.sort(key=lambda d: d["date"])
    return out


def main():
    rows = read_rows()
    data, problems, count, demo_count = {}, [], 0, 0

    for i, r in enumerate(rows[1:], start=2):              # ১ নম্বর সারি হেডার
        r = [c.strip() for c in r] + [""] * (13 - len(r))
        (up_raw, cat_raw, name, address, phone, note, show, demo_raw, verified,
         lat_raw, lng_raw, photos_raw, credit) = r[:13]
        is_demo = demo_raw.strip().lower() in ("হ্যাঁ", "yes", "true", "1")
        if not any(r):
            continue                                       # পুরো ফাঁকা সারি
        if not name:
            continue                                       # নাম ছাড়া সারি বাদ
        if show.lower() in ("না", "no", "false", "0"):
            continue                                       # লুকানো সারি

        up, cat = lookup(UPAZILAS, up_raw), lookup(CATEGORIES, cat_raw)
        if not up:
            problems.append(f"সারি {i}: উপজেলা বোঝা যায়নি → \"{up_raw}\"")
            continue
        if not cat:
            problems.append(f"সারি {i}: ক্যাটাগরি বোঝা যায়নি → \"{cat_raw}\"")
            continue
        if cat not in AVAILABLE[up]:
            problems.append(f"সারি {i}: অ্যাপে \"{up_raw}\" উপজেলায় \"{cat_raw}\" কার্ড নেই, তাই দেখা যাবে না")
            continue

        ph = clean_phone(phone)
        if ph and not re.fullmatch(r"[0-9+\-]{3,20}", ph):
            problems.append(f"সারি {i}: ফোন নম্বর ঠিক নয় → \"{phone}\"")
            continue

        if is_demo and ph:
            problems.append(f"সারি {i}: নমুনা সারিতে ফোন নম্বর রাখা যাবে না (কেউ ভুল নম্বরে কল করতে পারে)")
            continue

        if verified and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified):
            problems.append(f"সারি {i}: যাচাই তারিখ ২০২৬-১০-০৫ ফরম্যাটে লিখতে হবে → \"{verified}\"")
            continue

        # স্থানাঙ্ক: দুটোই একসাথে থাকতে হবে, আর ভোলার আশপাশের সীমার ভেতরে
        lat = lng = None
        if lat_raw or lng_raw:
            try:
                lat, lng = float(lat_raw), float(lng_raw)
            except ValueError:
                problems.append(f"সারি {i}: অক্ষাংশ/দ্রাঘিমাংশ সংখ্যা হতে হবে → \"{lat_raw}\", \"{lng_raw}\"")
                continue
            if not (21.5 <= lat <= 23.2 and 90.0 <= lng <= 91.5):
                problems.append(f"সারি {i}: স্থানাঙ্ক ভোলা এলাকার বাইরে ({lat}, {lng}); অক্ষাংশ-দ্রাঘিমাংশ উল্টে যায়নি তো?")
                continue

        # ছবি: '|' দিয়ে আলাদা; প্রতিটি https লিংক অথবা images/ ফোল্ডারের ফাইলের নাম
        photos = []
        for ph_item in [x.strip() for x in photos_raw.split("|") if x.strip()]:
            if re.fullmatch(r"https://\S+", ph_item) or re.fullmatch(r"[\w\-. ]+\.(?:jpe?g|png|webp)", ph_item, re.I):
                photos.append(ph_item)
            else:
                problems.append(f"সারি {i}: ছবির নাম/লিংক ঠিক নয় → \"{ph_item}\" (https লিংক বা image.jpg ধরনের নাম দাও)")
        if len(photos) != len([x for x in photos_raw.split("|") if x.strip()]):
            continue
        if len(photos) > MAX_PHOTOS_PER_PLACE:
            problems.append(f"সারি {i}: \"{name}\" এ {len(photos)}টি ছবি; সর্বোচ্চ {MAX_PHOTOS_PER_PLACE}টি রাখা যায় (সংরক্ষণ বাঁচাতে)")
            continue

        item = {"name": name, "address": address, "phone": ph, "note": note}
        if verified:
            item["verified"] = verified
        if lat is not None:
            item["lat"], item["lng"] = round(lat, 6), round(lng, 6)
        if photos:
            item["photos"] = photos
            if credit:
                item["credit"] = credit
        if is_demo:
            item["demo"] = True
            demo_count += 1
        data.setdefault(up, {}).setdefault(cat, []).append(item)
        count += 1

    # কোনো উপজেলা-ক্যাটাগরিতে আসল তথ্য থাকলে সেখানকার নমুনা সারি নিজে থেকে সরে যায়
    dropped = 0
    for up_k, cats in data.items():
        for cat_k, items in cats.items():
            if any(not it.get("demo") for it in items) and any(it.get("demo") for it in items):
                kept = [it for it in items if not it.get("demo")]
                dropped += len(items) - len(kept)
                cats[cat_k] = kept
    count -= dropped
    demo_count -= dropped

    days = build_days(problems)
    shelters = [it for up_c in data.values() for it in up_c.get("shelter", []) if not it.get("demo")]
    no_geo = [it["name"] for it in shelters if "lat" not in it]

    if problems:
        print(f"❌ {len(problems)}টি সমস্যা পাওয়া গেছে। data.json বদলানো হয়নি:\n")
        for p in problems:
            print("  • " + p)
        sys.exit(1)

    out = json.dumps({"version": 1, "data": data}, ensure_ascii=False, indent=2) + "\n"
    with open(JSON_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)

    if days is not None:
        with open(DAYS_JSON, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"version": 1, "days": days}, ensure_ascii=False, indent=2) + "\n")
        print(f"✅ {len(days)}টি বিশেষ দিন {DAYS_JSON} এ লেখা হয়েছে।")
    if no_geo:
        print(f"⚠ {len(no_geo)}টি আশ্রয়কেন্দ্রে স্থানাঙ্ক নেই; \"১ কিমির মধ্যে\" সুবিধায় এগুলো আসবে না।")
    print(f"✅ {count}টি তথ্য data.json এ লেখা হয়েছে (আসল {count - demo_count}টি, নমুনা {demo_count}টি)।")
    if dropped:
        print(f"ℹ {dropped}টি নমুনা সারি বাদ গেছে, কারণ ওই উপজেলা-ক্যাটাগরিতে আসল তথ্য আছে।")
    if demo_count:
        print(f"⚠ {demo_count}টি নমুনা সারি আছে। আসল তথ্য জোগাড় হলে এগুলো মুছে দাও।")
    for up, cats in data.items():
        print(f"   {up}: " + ", ".join(f"{c}({len(v)})" for c, v in cats.items()))


if __name__ == "__main__":
    main()
