#!/usr/bin/env python3
"""
Firebase Cloud Messaging (HTTP v1) দিয়ে সতর্কবার্তা পাঠায় (topic: bhola_alerts)।

ব্যবহার:
  python3 send_fcm.py publish <alerts.json>   # সর্বশেষ সতর্কবার্তা পাঠায় (info মাত্রায় পুশ যায় না)
  python3 send_fcm.py clear                    # অ্যাপের সব সতর্কবার্তা মুছতে বলে
  python3 send_fcm.py test                     # পরীক্ষামূলক নোটিফিকেশন

পরিবেশ-চলক:
  FIREBASE_SERVICE_ACCOUNT  = Firebase সার্ভিস-অ্যাকাউন্টের JSON (GitHub Secret থেকে)। না থাকলে পুশ বাদ যায়, ভুল নয়।
  FCM_PROJECT_ID            = ঐচ্ছিক (ডিফল্ট: bholaonlineshebaapps)
"""
import json
import os
import sys
import urllib.error
import urllib.request

TOPIC = "bhola_alerts"
DEFAULT_PROJECT = "bholaonlineshebaapps"
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
ALERT_FIELDS = ("id", "level", "hazard", "verb", "when", "signal", "source", "issued_ms", "expires_ms")


def build_message(kind, alert=None):
    """FCM বার্তার কাঠামো। data-র সব মান স্ট্রিং হতে হয়।"""
    if kind == "alert":
        data = {k: str(alert.get(k, "")) for k in ALERT_FIELDS}
        data["type"] = "alert"
        ttl = "3600s"
    elif kind == "clear":
        data, ttl = {"type": "clear"}, "600s"
    elif kind == "test":
        data, ttl = {"type": "test"}, "600s"
    else:
        raise ValueError(f"অজানা ধরন: {kind}")
    return {"message": {
        "topic": TOPIC,
        "data": data,
        "android": {"priority": "HIGH", "ttl": ttl},
    }}


def pick_alert(path):
    """alerts.json থেকে সবচেয়ে নতুন সতর্কবার্তা; না থাকলে None।"""
    with open(path, encoding="utf-8") as f:
        alerts = json.load(f).get("alerts", [])
    alerts = [a for a in alerts if isinstance(a, dict)]
    return max(alerts, key=lambda a: a.get("issued_ms", 0)) if alerts else None


def access_token(info):
    from google.oauth2 import service_account          # pip install google-auth requests
    import google.auth.transport.requests as gr
    creds = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE])
    creds.refresh(gr.Request())
    return creds.token


def send(message, info, project):
    url = f"https://fcm.googleapis.com/v1/projects/{project}/messages:send"
    req = urllib.request.Request(
        url, data=json.dumps(message).encode("utf-8"), method="POST",
        headers={"Authorization": "Bearer " + access_token(info), "Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:                  # টোকেন কখনো প্রিন্ট হয় না
        return e.code, e.read().decode("utf-8")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    kind = argv[1]
    raw = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()
    if not raw:
        print("ℹ FIREBASE_SERVICE_ACCOUNT সেট করা নেই, তাই পুশ পাঠানো হয়নি (অ্যাপের ব্যানারে সতর্কবার্তা ঠিকই যাবে)।")
        return 0
    try:
        info = json.loads(raw)
    except ValueError:
        print("❌ FIREBASE_SERVICE_ACCOUNT ঠিক JSON নয়। পুরো ফাইলের লেখা Secret-এ বসানো হয়েছে তো?")
        return 1

    if kind == "publish":
        if len(argv) < 3:
            print("❌ alerts.json এর পথ দাও")
            return 2
        alert = pick_alert(argv[2])
        if not alert:
            print("ℹ পাঠানোর মতো সতর্কবার্তা নেই।")
            return 0
        if alert.get("level") == "info":
            print("ℹ 'info' মাত্রায় পুশ পাঠানো হয় না (শুধু অ্যাপের ব্যানারে দেখায়)।")
            return 0
        msg = build_message("alert", alert)
    else:
        msg = build_message(kind)

    status, body = send(msg, info, os.environ.get("FCM_PROJECT_ID", DEFAULT_PROJECT))
    if status == 200:
        print(f"✅ পুশ পাঠানো হয়েছে ({kind}) → topic {TOPIC}")
        return 0
    print(f"❌ FCM ব্যর্থ (HTTP {status}): {body[:400]}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
