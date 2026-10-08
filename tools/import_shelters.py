#!/usr/bin/env python3
"""
আশ্রয়কেন্দ্রের তালিকা (shelters.csv) → data.csv এ ঢোকায়।

ব্যবহার:
  cp shelters_template.csv shelters.csv      # তারপর সারি যোগ করো
  python3 tools/import_shelters.py --check   # শুধু যাচাই, কিছু লেখে না
  python3 tools/import_shelters.py           # data.csv এ যোগ/হালনাগাদ

নিয়ম (জীবনঝুঁকির কারণে কড়া):
  • "সূত্র" ফাঁকা থাকলে সারি ঢোকে না (যেমন: ত্রাণ ও পুনর্বাসন কর্মকর্তার কার্যালয়, জেলা প্রশাসন তালিকা, ইউএনও অফিস)।
  • স্থানাঙ্ক ভোলার সীমার (অক্ষাংশ 21.5-23.2, দ্রাঘিমাংশ 90.0-91.5) বাইরে হলে ঢোকে না;
    স্থানাঙ্ক ফাঁকা থাকলে ঢোকে, কিন্তু "১ কিমির মধ্যে" সুবিধায় আসে না (সতর্কবার্তা দেয়)।
  • ধারণক্ষমতা পূর্ণসংখ্যা হতে হবে (জানা না থাকলে ফাঁকা রাখো; আন্দাজে লিখো না)।
  • একই (উপজেলা + নাম) আবার দিলে পুরনো সারি হালনাগাদ হয়, নকল হয় না।
  • এই টুল কখনো "নমুনা" সারি বানায় না।
স্থানাঙ্ক বের করা: Google Maps এ জায়গাটা চেপে ধরে রাখো → উপরে দেখা সংখ্যা (যেমন 22.6903, 90.6525) কপি করো; আগে অক্ষাংশ, পরে দ্রাঘিমাংশ।
"""
import csv
import io
import re
import sys

SRC = "shelters.csv"
DST = "data.csv"
UPAZILAS = {"ভোলা সদর", "বোরহানউদ্দিন", "চরফ্যাশন", "দৌলতখান", "লালমোহন", "মনপুরা", "তজুমদ্দিন"}
BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def read(path):
    raw = open(path, encoding="utf-8-sig", newline="").read()
    return list(csv.reader(io.StringIO(raw, newline="")))


def main():
    check = "--check" in sys.argv
    try:
        src = read(SRC)
    except FileNotFoundError:
        sys.exit(f"❌ {SRC} নেই। shelters_template.csv কপি করে {SRC} নাম দাও।")
    problems, ok, no_geo = [], [], 0
    seen = set()
    for i, r in enumerate(src[1:], start=2):
        r = [c.strip() for c in r] + [""] * (8 - len(r))
        up, union, name, cap, lat, lng, source, verified = r[:8]
        if not any(r):
            continue
        if up not in UPAZILAS:
            problems.append(f"সারি {i}: উপজেলা ঠিক নয় → \"{up}\" (বাংলায় হুবহু: {', '.join(sorted(UPAZILAS))})")
            continue
        if not name:
            problems.append(f"সারি {i}: নাম নেই")
            continue
        if not source:
            problems.append(f"সারি {i}: \"{name}\" এর সূত্র নেই। সূত্র ছাড়া আশ্রয়কেন্দ্র বসানো যাবে না")
            continue
        if (up, name) in seen:
            problems.append(f"সারি {i}: \"{name}\" ({up}) দুবার আছে")
            continue
        seen.add((up, name))
        cap = cap.translate(BN)
        if cap and not re.fullmatch(r"\d{1,6}", cap):
            problems.append(f"সারি {i}: ধারণক্ষমতা সংখ্যা হতে হবে → \"{cap}\"")
            continue
        if verified and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", verified):
            problems.append(f"সারি {i}: যাচাই তারিখ ২০২৬-১০-০৭ ফরম্যাটে → \"{verified}\"")
            continue
        if bool(lat) != bool(lng):
            problems.append(f"সারি {i}: অক্ষাংশ ও দ্রাঘিমাংশ দুটোই লাগবে")
            continue
        if lat:
            try:
                la, ln = float(lat), float(lng)
            except ValueError:
                problems.append(f"সারি {i}: স্থানাঙ্ক সংখ্যা নয় → {lat}, {lng}")
                continue
            if not (21.5 <= la <= 23.2 and 90.0 <= ln <= 91.5):
                problems.append(f"সারি {i}: স্থানাঙ্ক ভোলার বাইরে ({la}, {ln}); উল্টে যায়নি তো?")
                continue
        else:
            no_geo += 1
        address = f"{union}, {up}" if union else up
        note = "ধারণক্ষমতা: " + cap + " জন" if cap else ""
        note = (note + " · " if note else "") + "সূত্র: " + source
        ok.append([up, "আশ্রয়কেন্দ্র", name, address, "", note, "হ্যাঁ", "", verified, lat, lng, "", ""])

    if problems:
        print(f"❌ {len(problems)}টি সমস্যা; data.csv বদলানো হয়নি:")
        for p in problems:
            print("  • " + p)
        sys.exit(1)

    print(f"✅ {len(ok)}টি আশ্রয়কেন্দ্র ঠিক আছে।")
    if no_geo:
        print(f"⚠ {no_geo}টিতে স্থানাঙ্ক নেই; এগুলো \"১ কিমির মধ্যে\" হিসাবে আসবে না।")
    if check:
        print("(--check: কিছু লেখা হয়নি)")
        return

    rows = read(DST)
    hdr, body = rows[0], [r + [""] * (13 - len(r)) for r in rows[1:]]
    index = {(r[0], r[2]): k for k, r in enumerate(body) if r[1] == "আশ্রয়কেন্দ্র"}
    added = updated = 0
    for new in ok:
        k = index.get((new[0], new[2]))
        if k is None:
            body.append(new)
            added += 1
        else:
            body[k] = new
            updated += 1
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow(hdr)
    w.writerows(body)
    open(DST, "w", encoding="utf-8-sig", newline="").write(out.getvalue())
    print(f"📥 data.csv: নতুন {added}টি, হালনাগাদ {updated}টি। এখন git add -A → commit → push।")


if __name__ == "__main__":
    main()
