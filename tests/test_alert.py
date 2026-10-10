"""make_alert.py: ইংরেজি ঐচ্ছিক ক্ষেত্র সহ।  python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def publish(**extra):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "alerts.json")
    env = dict(os.environ, ALERT_ACTION="publish", LEVEL="warning", HAZARD="ঘূর্ণিঝড়",
               WHEN="আজ রাত থেকে", SIGNAL="", SOURCE="আবহাওয়া অধিদপ্তর", HOURS="24", CONFIRM="false")
    env.update(extra)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "make_alert.py"), path],
                       env=env, capture_output=True, text=True)
    data = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    return r, data


class MakeAlert(unittest.TestCase):
    def test_english_fields_included_when_given(self):
        r, d = publish(WHEN_EN="from tonight", SIGNAL_EN="Danger signal 4")
        self.assertEqual(r.returncode, 0, r.stdout)
        a = d["alerts"][0]
        self.assertEqual(a["when_en"], "from tonight")
        self.assertEqual(a["signal_en"], "Danger signal 4")
        self.assertEqual(a["hazard"], "ঘূর্ণিঝড়")          # বাংলা অপরিবর্তিত

    def test_no_english_means_no_english_keys(self):
        r, d = publish()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("when_en", d["alerts"][0])

    def test_too_long_english_rejected(self):
        r, _ = publish(WHEN_EN="x" * 61)
        self.assertNotEqual(r.returncode, 0)

    def test_fcm_payload_carries_english(self):
        sys.path.insert(0, ROOT)
        import send_fcm
        msg = send_fcm.build_message("alert", {"id": "1", "hazard": "বন্যা", "when_en": "from tomorrow"})
        self.assertEqual(msg["message"]["data"]["when_en"], "from tomorrow")


if __name__ == "__main__":
    unittest.main()
