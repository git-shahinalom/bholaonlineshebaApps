"""Apps Script ফাইল (forms/*.gs) পরীক্ষা: নামের সংঘর্ষ নেই, মেনু ঠিক, যুক্তি Node-এ নকল Sheet দিয়ে পাস।"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GS = sorted((ROOT / "forms").glob("*.gs"))


def names(text):
    out = set(re.findall(r"^function\s+(\w+)", text, re.M))
    out |= set(re.findall(r"^(?:var|let|const)\s+(\w+)", text, re.M))
    return out


class Structure(unittest.TestCase):
    def test_no_duplicate_global_names_across_files(self):
        """একই প্রজেক্টে সব .gs ফাইল বসালেও যেন একে অন্যকে ভাঙে না।"""
        seen = {}
        clashes = []
        for f in GS:
            for n in names(f.read_text(encoding="utf-8")):
                if n in seen:
                    clashes.append(f"{n}: {seen[n]} ও {f.name}")
                seen[n] = f.name
        self.assertEqual(clashes, [])

    def test_exactly_one_onopen(self):
        defs = [f.name for f in GS if re.search(r"^function\s+onOpen\b", f.read_text(encoding="utf-8"), re.M)]
        self.assertEqual(defs, ["Menu.gs"])

    def test_menu_handlers_exist_and_are_public(self):
        allnames = set()
        for f in GS:
            allnames |= names(f.read_text(encoding="utf-8"))
        for f in GS:
            for h in re.findall(r"addItem\('[^']*',\s*'(\w+)'\)", f.read_text(encoding="utf-8")):
                self.assertIn(h, allnames, f"{f.name}: মেনুর {h} নেই")
                self.assertFalse(h.endswith("_"), f"{h}: মেনুর ফাংশনের নামের শেষে _ থাকা ঠিক নয়")

    def test_menu_calls_every_menu_builder(self):
        menu = (ROOT / "forms/Menu.gs").read_text(encoding="utf-8")
        for f in GS:
            for b in re.findall(r"^function\s+(\w+Menu_)\b", f.read_text(encoding="utf-8"), re.M):
                self.assertIn(b, menu, f"Menu.gs {b} ডাকছে না")

    @unittest.skipUnless(shutil.which("node"), "node নেই")
    def test_syntax(self):
        for f in GS:
            tmp = Path(tempfile.mkdtemp()) / (f.stem + ".js")
            shutil.copy(f, tmp)
            r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{f.name}: {r.stderr}")


@unittest.skipUnless(shutil.which("node"), "node নেই")
class Logic(unittest.TestCase):
    def test_mocked_sheet_flow(self):
        from PIL import Image
        d = Path(tempfile.mkdtemp())
        Image.effect_noise((1000, 600), 40).convert("RGB").save(d / "big.jpg")
        Image.effect_noise((300, 200), 40).convert("RGB").save(d / "tiny.jpg")
        Image.new("RGB", (800, 500)).save(d / "x.png")
        r = subprocess.run(["node", str(ROOT / "tests/gas_mock_test.js"), str(d / "big.jpg"), str(d / "tiny.jpg"), str(d / "x.png")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-1500:])


if __name__ == "__main__":
    unittest.main()
