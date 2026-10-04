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
}

CATEGORIES = {
    "হাসপাতাল": "hospital",
    "এ্যাম্বুলেন্স": "ambulance",
    "পুলিশ": "police",
    "আইনজীবী": "lawyer",
    "ভ্রমণের স্থান": "tourism",
    "ইউনিয়ন পরিষদ": "union",
    "জরুরি বিদ্যুৎ": "electricity",
    "রেন্ট-এ-কার": "rentcar",
    "ফায়ার সার্ভিস": "fire",
}

# অ্যাপে কোন উপজেলায় কোন কার্ড আছে (এর বাইরের ডেটা অ্যাপে দেখা যাবে না)
AVAILABLE = {
    "bhola_sadar": ["hospital", "ambulance", "police", "lawyer", "tourism", "union", "electricity", "rentcar", "fire"],
    "borhanuddin": ["hospital", "ambulance", "police", "fire", "electricity", "rentcar"],
    "charfasson":  ["hospital", "ambulance", "police", "lawyer", "tourism", "union", "electricity", "rentcar", "fire"],
    "dowlatkhan":  ["hospital", "ambulance", "police", "fire", "rentcar"],
    "lalmohon":    ["hospital", "ambulance", "police", "fire", "electricity", "rentcar"],
    "monpura":     ["hospital", "ambulance", "police", "lawyer", "tourism", "union", "fire"],
    "tazumuddin":  ["hospital", "ambulance", "police", "fire", "rentcar"],
}

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


def main():
    rows = read_rows()
    data, problems, count = {}, [], 0

    for i, r in enumerate(rows[1:], start=2):              # ১ নম্বর সারি হেডার
        r = [c.strip() for c in r] + [""] * (7 - len(r))
        up_raw, cat_raw, name, address, phone, note, show = r[:7]
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
        if ph and not re.fullmatch(r"[0-9+\-]{5,20}", ph):
            problems.append(f"সারি {i}: ফোন নম্বর ঠিক নয় → \"{phone}\"")
            continue

        data.setdefault(up, {}).setdefault(cat, []).append(
            {"name": name, "address": address, "phone": ph, "note": note})
        count += 1

    if problems:
        print(f"❌ {len(problems)}টি সমস্যা পাওয়া গেছে। data.json বদলানো হয়নি:\n")
        for p in problems:
            print("  • " + p)
        sys.exit(1)

    out = json.dumps({"version": 1, "data": data}, ensure_ascii=False, indent=2) + "\n"
    with open(JSON_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(out)

    print(f"✅ {count}টি তথ্য data.json এ লেখা হয়েছে।")
    for up, cats in data.items():
        print(f"   {up}: " + ", ".join(f"{c}({len(v)})" for c, v in cats.items()))


if __name__ == "__main__":
    main()
