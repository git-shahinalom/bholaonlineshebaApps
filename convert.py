#!/usr/bin/env python3
"""
data.csv  →  data.json   (Bhola Online Seba)

কোনো ভুল থাকলে data.json বদলায় না (পুরনো ডেটাই অ্যাপে থাকে) এবং ভুলগুলো তালিকা করে দেখায়।
"""
import csv
import os
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
ALL11 = ["hospital", "ambulance", "police", "fire", "shelter", "electricity",
         "pharmacy", "waterway", "govoffice", "tourism", "rentcar"]
# "union" অ্যাপের গ্রিডে কার্ড নয়; ডেটা থাকে, দেখায় "তথ্য বাতায়ন" পাতায়।
UPAZILA_KEYS = ALL11 + ["union"]
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
# অ্যাপের প্রতিটি উপজেলায় এখন ১১টি ক্যাটাগরির কার্ড আছে।

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


PHOTOS_CSV = "photos.csv"
SPOTS_CSV = "spots.csv"          # অনুমোদিত ইউজার-স্পট (tools/sync_spots.py বানায়)

# ভ্রমণের স্থানের ধরন: দেখানোর বাংলা নাম → অ্যাপের কী
TOUR_TYPES = {
    "পার্ক": "park",
    "জলাশয়": "waterside",        # নদীতীর, লেক, দিঘি, পুকুর
    "প্রকৃতি": "nature",         # চর, দ্বীপ, বন, প্রাকৃতিক এলাকা
    "রিসোর্ট": "resort",
    "রেস্টুরেন্ট": "restaurant",   # রুফটপ রেস্টুরেন্ট, ক্যাফে
    "সৈকত": "beach",
    "দর্শনীয়": "landmark",        # ঐতিহাসিক বা বিখ্যাত স্থাপনা
    "অন্যান্য": "other",
}


def read_user_photos(problems):
    """photos.csv (অনুমোদিত ইউজার-ছবি) → {স্থানের নাম: [(ফাইল, ছবির সূত্র), ...]}। ফাইল না থাকলে বা নাম অজানা হলে সমস্যা।"""
    try:
        raw = open(PHOTOS_CSV, "rb").read().decode("utf-8-sig")
    except FileNotFoundError:
        return {}
    out = {}
    for i, r in enumerate(list(csv.reader(io.StringIO(raw, newline="")))[1:], start=2):
        r = [c.strip() for c in r] + [""] * (5 - len(r))
        place, fname, credit = r[0], r[1], r[2]
        if not any(r):
            continue
        if not place or not fname:
            problems.append(f"{PHOTOS_CSV} সারি {i}: স্থানের নাম ও ফাইলের নাম দুটোই লাগবে")
            continue
        if not re.fullmatch(r"[\w\-.]+\.(?:jpe?g|png|webp)", fname, re.I):
            problems.append(f"{PHOTOS_CSV} সারি {i}: ফাইলের নাম ঠিক নয় → \"{fname}\"")
            continue
        if not os.path.exists(os.path.join("images", fname)):
            problems.append(f"{PHOTOS_CSV} সারি {i}: images/{fname} ফাইলটি নেই")
            continue
        out.setdefault(place, []).append((fname, credit))
    return out


def read_spots():
    """spots.csv → অনুমোদিত স্পটের তালিকা। ভুল সারি পুরো বিল্ড আটকায় না: সতর্কবার্তা দিয়ে বাদ যায়।"""
    try:
        raw = open(SPOTS_CSV, "rb").read().decode("utf-8-sig")
    except FileNotFoundError:
        return [], []
    spots, warns = [], []
    for i, r in enumerate(list(csv.reader(io.StringIO(raw, newline="")))[1:], start=2):
        r = [c.strip() for c in r] + [""] * (14 - len(r))
        (ttype_raw, name, name_en, up_raw, area, lat_raw, lng_raw, desc, desc_en,
         facilities, hours, phone, by, approved) = r[:14]
        if not any(r):
            continue
        ttype = TOUR_TYPES.get(ttype_raw, "other")
        up = lookup(UPAZILAS, up_raw)
        if not name or up in (None, "national"):
            warns.append(f"{SPOTS_CSV} সারি {i}: নাম বা উপজেলা ঠিক নয় → \"{name}\", \"{up_raw}\"")
            continue
        try:
            lat, lng = float(lat_raw), float(lng_raw)
        except ValueError:
            warns.append(f"{SPOTS_CSV} সারি {i} (\"{name}\"): স্থানাঙ্ক নেই বা সংখ্যা নয়, বাদ")
            continue
        if not (21.5 <= lat <= 23.2 and 90.0 <= lng <= 91.5):
            warns.append(f"{SPOTS_CSV} সারি {i} (\"{name}\"): স্থানাঙ্ক ভোলার বাইরে ({lat}, {lng}), বাদ")
            continue
        ph = clean_phone(phone)
        if ph and not re.fullmatch(r"[0-9+\-]{3,20}", ph):
            ph = ""
        spots.append(dict(type=ttype, name=name, name_en=name_en, up=up, area=area, lat=lat, lng=lng,
                          desc=desc, desc_en=desc_en, facilities=facilities, hours=hours, phone=ph,
                          by=by, approved=approved))
    return spots, warns


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
        r = [c.strip() for c in r] + [""] * (9 - len(r))
        date, end, title, message, icon, confirmed, show, title_en, message_en = r[:9]
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
        if title_en and message_en:
            item["title_en"], item["message_en"] = title_en, message_en
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
    user_photos = read_user_photos(problems)
    matched_places = set()

    for i, r in enumerate(rows[1:], start=2):              # ১ নম্বর সারি হেডার
        r = [c.strip() for c in r] + [""] * (17 - len(r))
        (up_raw, cat_raw, name, address, phone, note, show, demo_raw, verified,
         lat_raw, lng_raw, photos_raw, credit, name_en, address_en, note_en, ttype_raw) = r[:17]
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

        # শীট-থেকে-অনুমোদিত ছবি (photos.csv) যোগ: শুধু ভ্রমণের স্থানে, নাম হুবহু মিললে
        if cat == "tourism" and name in user_photos:
            matched_places.add(name)
            credits = [c.strip() for c in credit.split(",") if c.strip()]
            for fname, cr in user_photos[name]:
                if fname not in photos:
                    photos.append(fname)
                if cr and cr not in credits:
                    credits.append(cr)
            credit = ", ".join(credits)
            if len(photos) > MAX_PHOTOS_PER_PLACE:
                problems.append(f"সারি {i}: \"{name}\" এ ডেটা ও photos.csv মিলিয়ে {len(photos)}টি ছবি; সর্বোচ্চ {MAX_PHOTOS_PER_PLACE}টি")
                continue

        ttype = ""
        if ttype_raw:
            if cat != "tourism":
                problems.append(f"সারি {i}: ধরন শুধু ভ্রমণের স্থানে দেওয়া যায়")
                continue
            ttype = TOUR_TYPES.get(ttype_raw)
            if ttype is None:
                problems.append(f"সারি {i}: ধরন \"{ttype_raw}\" ঠিক নয়; হতে পারে: {', '.join(TOUR_TYPES)}")
                continue

        item = {"name": name, "address": address, "phone": ph, "note": note}
        if ttype:
            item["type"] = ttype
        # ইংরেজি সংস্করণ (ঐচ্ছিক): ফাঁকা থাকলে অ্যাপ বাংলা লেখাই দেখায়
        if name_en:
            item["name_en"] = name_en
        if address_en:
            item["address_en"] = address_en
        if note_en:
            item["note_en"] = note_en
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

    # ---- অনুমোদিত ইউজার-স্পট (spots.csv) ভ্রমণের স্থানে যোগ ----
    spots, spot_warns = read_spots()
    spot_added = 0
    taken = {(u, it["name"]) for u, cats in data.items() for it in cats.get("tourism", [])}
    for sp in spots:
        if (sp["up"], sp["name"]) in taken:
            spot_warns.append(f"{SPOTS_CSV}: \"{sp['name']}\" ({sp['up']}) আগে থেকেই আছে, বাদ")
            continue
        taken.add((sp["up"], sp["name"]))
        note = " · ".join(x for x in (sp["desc"], sp["facilities"], sp["hours"]) if x)
        item = {"name": sp["name"], "address": (sp["area"] + ", " if sp["area"] else "") + next(k for k, v in UPAZILAS.items() if v == sp["up"]),
                "phone": sp["phone"], "note": note, "type": sp["type"],
                "lat": round(sp["lat"], 6), "lng": round(sp["lng"], 6), "spot": True}
        if sp["name_en"]:
            item["name_en"] = sp["name_en"]
        if sp["desc_en"]:
            item["note_en"] = sp["desc_en"]
        if sp["by"]:
            item["by"] = sp["by"]
        if sp["name"] in user_photos:
            matched_places.add(sp["name"])
            item["photos"] = [f for f, _ in user_photos[sp["name"]]][:MAX_PHOTOS_PER_PLACE]
            crs = []
            for _, cr in user_photos[sp["name"]]:
                if cr and cr not in crs:
                    crs.append(cr)
            if crs:
                item["credit"] = ", ".join(crs)
        data.setdefault(sp["up"], {}).setdefault("tourism", []).append(item)
        count += 1
        spot_added += 1

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

    for place in sorted(set(user_photos) - matched_places):
        problems.append(f"{PHOTOS_CSV}: \"{place}\" নামে কোনো ভ্রমণের স্থান data.csv তে নেই (নাম হুবহু মেলাও)")
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
    for w in spot_warns:
        print("⚠ " + w)
    if spot_added:
        print(f"👥 {spot_added}টি ইউজার-প্রস্তাবিত স্পট যোগ হয়েছে।")
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
