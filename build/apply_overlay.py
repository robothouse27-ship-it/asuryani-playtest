#!/usr/bin/env python3
"""Apply build/overlay_<aid>.json onto the already-built data_<aid>/{units,bundle}.json.

Used when the BSData source catalogues aren't checked out locally (so bsdata.py
can't be re-run from scratch) but we still want the hand-authored, book-accurate
overlay reflected in the shipped artifacts. Keep this in step with bsdata.py's
overlay handling. Usage: python3 build/apply_overlay.py space-wolves
"""
import json, os, sys

aid = sys.argv[1] if len(sys.argv) > 1 else "space-wolves"
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# templated trait keywords the books print get resolved to this Legion's values
LOYAL = {"dark-angels", "white-scars", "space-wolves", "imperial-fists", "blood-angels",
         "iron-hands", "ultramarines", "salamanders", "raven-guard"}
LEGION_NAMES = {
    "alpha-legion": "Alpha Legion", "blood-angels": "Blood Angels", "dark-angels": "Dark Angels",
    "death-guard": "Death Guard", "emperors-children": "Emperor's Children",
    "imperial-fists": "Imperial Fists", "iron-hands": "Iron Hands", "iron-warriors": "Iron Warriors",
    "night-lords": "Night Lords", "raven-guard": "Raven Guard", "salamanders": "Salamanders",
    "sons-of-horus": "Sons of Horus", "space-wolves": "Space Wolves", "thousand-sons": "Thousand Sons",
    "ultramarines": "Ultramarines", "white-scars": "White Scars", "word-bearers": "Word Bearers",
    "world-eaters": "World Eaters",
}
_allegiance = "Loyalist" if aid in LOYAL else "Traitor"
_legion_name = LEGION_NAMES.get(aid, aid)

def resolve_placeholders(u):
    """Replace [Allegiance] -> Loyalist/Traitor and [Legiones Astartes] -> legion name in traits."""
    tr = u.get("traits")
    if isinstance(tr, list):
        u["traits"] = [_allegiance if t == "[Allegiance]"
                       else _legion_name if t == "[Legiones Astartes]"
                       else t for t in tr]

def _load(name):
    p = os.path.join(root, "build", name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}

# shared generic Legiones Astartes datasheets + this Legion's unique units (legion wins)
_common = _load("overlay_legion-common.json")
_legion = _load(f"overlay_{aid}.json")
ov_units = {**_common.get("units", {}), **_legion.get("units", {})}
ov_lists = {**_common.get("wargearLists", {}), **_legion.get("wargearLists", {})}

# scalar/array fields copied verbatim from the overlay onto each unit. The variant_*
# fields link armour/configuration variants (Power / Terminator / Saturnine) into one
# group the app shows as a swap selector; name/slot/profiles/types let the overlay define
# wholly NEW units (the variant datasheets) that aren't in the BSData import.
DIRECT = ["lore", "wargear", "traits", "options", "composition", "sizeRules",
          "baseCost", "pointsValue", "upgrades", "name", "slot", "profiles", "types",
          "variantGroup", "variantPrimary", "variantLabel", "variantOrder"]

def patch_unit(u):
    ov_u = ov_units[u["id"]]
    for k in DIRECT:
        if k in ov_u:
            u[k] = ov_u[k]
    if "specialRules" in ov_u:
        u["specialRules"] = {"_": ov_u["specialRules"]}

def build_unit(uid):
    """Construct a brand-new unit dict from an overlay entry (variant datasheets)."""
    ov_u = ov_units[uid]
    u = {"id": uid}
    for k in DIRECT:
        if k in ov_u:
            u[k] = ov_u[k]
    u["specialRules"] = {"_": ov_u.get("specialRules", [])}
    u.setdefault("wargear", {})
    u.setdefault("traits", [])
    u.setdefault("options", [])
    return u

def patch_file(path, is_bundle):
    d = json.load(open(path, encoding="utf-8"))
    arr = d["units"] if is_bundle else d
    present = {u.get("id") for u in arr}
    n = 0
    for u in arr:
        if u.get("id") in ov_units:
            patch_unit(u); n += 1
    # append variant datasheets that don't exist in the base import
    added = 0
    for uid, ov_u in ov_units.items():
        if uid not in present and "name" in ov_u and "slot" in ov_u:
            arr.append(build_unit(uid)); added += 1
    # resolve [Allegiance]/[Legiones Astartes] trait placeholders for this Legion
    for u in arr:
        resolve_placeholders(u)
    if is_bundle and ov_lists:
        d.setdefault("wargearLists", {}).update(ov_lists)
    json.dump(d, open(path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"  patched {n} units (+{added} new) in {os.path.relpath(path, root)}")

base = os.path.join(root, "data_" + aid)
patch_file(os.path.join(base, "units.json"), False)
patch_file(os.path.join(base, "bundle.json"), True)
print(f"done ({len(ov_units)} units defined in overlay)")
