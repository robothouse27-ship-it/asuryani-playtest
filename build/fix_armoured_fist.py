#!/usr/bin/env python3
"""Armoured Fist detachment = 4 Transports + 4 Heavy Transports (was 4 Transports
+ 4 Armour — a misread of the chart pictogram; the bottom-row icon is the long
low Land Raider/Spartan hull, not a turreted Predator). Rulebook p284 chart.

The detachment is copied into every bundle, so patch: data/detachments.json (source),
all data_*/bundle.json, and the Asuryani app/data.js. Idempotent. Re-encrypt after.

Usage:  python3 build/fix_armoured_fist.py [--check]
"""
import json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW_SLOTS = [{"role": "Transports", "count": 4}, {"role": "Heavy Transports", "count": 4}]
CHECK = "--check" in sys.argv


def patch_dets(dets):
    """Patch armoured-fist inside a detachments dict. Returns True if changed."""
    if not isinstance(dets, dict):
        return False
    for t in dets.get("auxiliary", []):
        if t.get("id") == "armoured-fist":
            if t.get("slots") != NEW_SLOTS:
                if not CHECK:
                    t["slots"] = NEW_SLOTS
                return True
    return False


def patch_json_file(path, dets_getter):
    data = json.load(open(path))
    if patch_dets(dets_getter(data)):
        if not CHECK:
            json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)
        print(("would patch " if CHECK else "patched ") + path)
        return 1
    return 0


def patch_data_js(path):
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"(window\.GAME_DATA\s*=\s*)(\{.*\})(\s*;?\s*)$", txt, re.S)
    if not m:
        print("!! could not parse " + path); return 0
    data = json.loads(m.group(2))
    if patch_dets(data.get("detachments", {})):
        if not CHECK:
            header = txt[:m.start()]
            open(path, "w", encoding="utf-8").write(header + m.group(1) + json.dumps(data, ensure_ascii=False) + ";\n")
        print(("would patch " if CHECK else "patched ") + path)
        return 1
    return 0


def main():
    n = 0
    n += patch_json_file(os.path.join(ROOT, "data", "detachments.json"), lambda d: d)
    for f in sorted(glob.glob(os.path.join(ROOT, "data_*", "bundle.json"))):
        n += patch_json_file(f, lambda d: d.get("detachments", {}))
    dj = os.path.join(ROOT, "app", "data.js")
    if os.path.exists(dj):
        n += patch_data_js(dj)
    print("\n%s %d file(s). Armoured Fist -> 4 Transports + 4 Heavy Transports." %
          ("Would change" if CHECK else "Changed", n))


if __name__ == "__main__":
    main()
