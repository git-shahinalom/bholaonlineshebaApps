#!/usr/bin/env python3
"""
সতর্কবার্তা প্রকাশ বা মুছে ফেলা (GitHub Actions থেকে চলে)।
ব্যবহার:  python3 make_alert.py <alerts.json>
ইনপুট আসে পরিবেশ-চলক (ENV) থেকে: ALERT_ACTION, LEVEL, HAZARD, WHEN, SIGNAL, SOURCE, HOURS, CONFIRM
"""
import json
import os
import sys
import time

HAZARDS = {            # বিপদ -> বাক্যের ক্রিয়া
    "বন্যা": "হবে",
    "জলোচ্ছ্বাস": "হবে",
    "ঘূর্ণিঝড়": "হবে",
    "ভারী বৃষ্টি": "হবে",
    "তাপদাহ": "থাকবে",
}
LEVELS = ("info", "warning", "severe")
MAX_ALERTS = 3


def fail(msg):
    print("❌ " + msg)
    sys.exit(1)


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return [a for a in d.get("alerts", []) if isinstance(a, dict)]
    except (FileNotFoundError, ValueError):
        return []


def main():
    if len(sys.argv) < 2:
        fail("আউটপুট ফাইলের নাম দাও")
    path = sys.argv[1]
    env = os.environ.get
    action = env("ALERT_ACTION", "publish").strip()
    now_ms = int(time.time() * 1000)
    alerts = [a for a in load(path) if a.get("expires_ms", 0) > now_ms]   # মেয়াদোত্তীর্ণ বাদ

    if action == "clear":
        alerts = []
        print("✅ সব সতর্কবার্তা মুছে ফেলা হয়েছে।")
    elif action == "publish":
        level, hazard = env("LEVEL", "").strip(), env("HAZARD", "").strip()
        when, signal = env("WHEN", "").strip(), env("SIGNAL", "").strip()
        source = env("SOURCE", "আবহাওয়া অধিদপ্তর").strip() or "আবহাওয়া অধিদপ্তর"
        if level not in LEVELS:
            fail(f"মাত্রা ঠিক নয়: {level!r}")
        if hazard not in HAZARDS:
            fail(f"বিপদের ধরন ঠিক নয়: {hazard!r}")
        if not when or len(when) > 60:
            fail("'কখন' ফাঁকা বা ৬০ অক্ষরের বেশি")
        try:
            hours = int(env("HOURS", "24"))
        except ValueError:
            fail("মেয়াদ (ঘণ্টা) সংখ্যা হতে হবে")
        if not 1 <= hours <= 72:
            fail("মেয়াদ ১ থেকে ৭২ ঘণ্টার মধ্যে হতে হবে")
        if level == "severe" and env("CONFIRM", "false").lower() != "true":
            fail("'ভয়াবহ' (severe) মাত্রার জন্য নিশ্চিতকরণ টিক দিতে হবে। আবহাওয়া অধিদপ্তরের সংকেত যাচাই করেছ তো?")

        alert = {
            "id": str(now_ms),
            "level": level,
            "hazard": hazard,
            "verb": HAZARDS[hazard],
            "when": when,
            "signal": signal,
            "source": source,
            "issued_ms": now_ms,
            "expires_ms": now_ms + hours * 3600 * 1000,
        }
        alerts.append(alert)
        alerts = alerts[-MAX_ALERTS:]
        print(f"✅ সতর্কবার্তা প্রকাশ: [{level}] {when} {hazard} {HAZARDS[hazard]} ({hours} ঘণ্টা)")
    else:
        fail(f"অজানা action: {action!r}")

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"updated_ms": now_ms, "alerts": alerts}, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
