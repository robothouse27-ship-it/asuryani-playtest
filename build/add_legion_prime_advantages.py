#!/usr/bin/env python3
"""Each Legion's unique Prime Advantage (Liber Astartes / Liber Hereticus, the
"Rite of War: Legiones Astartes <Legion>" pages). Every legion bundle currently
ships only the 5 core advantages; this appends each legion's 6th, legion-specific
one to its detachments.primeAdvantages.

App support (index.html renderPrime): `roleOnly` (array of Battlefield Roles —
disabled unless the prime slot's role matches) and `oncePerArmy`. Only Command/
Troops are gated, since those are the only prime-slot roles that exist; other
restrictions (Centurion-only, Elites, Infantry, etc.) are stated in the text but
not hard-gated so the advantage stays selectable. Idempotent. Re-encrypt after.

Usage:  python3 build/add_legion_prime_advantages.py [--check]
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = "--check" in sys.argv

# key, name, text, [roleOnly], [oncePerArmy]
ADV = {
 "dark-angels": {"key": "paladin-of-the-hekatonystika", "name": "Paladin of the Hekatonystika", "oncePerArmy": True,
   "text": "Centurion or Centurion with Jump Pack only. Once per Army. One Model in the Unit gains +1 Weapon Skill, must exchange its bolter for a Terranic greatsword (Free), and gains the Orders of the Hekatonystika Special Rule."},
 "white-scars": {"key": "the-sagyar-mazan", "name": "The Sagyar Mazan",
   "text": "All Models in the Unit gain the Expendable (2) Special Rule. The Sagyar Mazan are the exiled, seeking an honourable death to wash away dishonour."},
 "space-wolves": {"key": "pack-thegn", "name": "Pack Thegn",
   "text": "One Model gains +1 Attacks and +1 Weapon Skill, and may exchange its power sword for a frost sword or frost axe (Free), or a frost claw (+5 points)."},
 "imperial-fists": {"key": "castellan", "name": "Castellan",
   "text": "Centurion only. The Model gains an augury scanner and, instead of its listed options, must exchange its bolter (Free) for a heavy bolter, autocannon, or Iliastus assault cannon."},
 "blood-angels": {"key": "revenants", "name": "Revenants",
   "text": "The Unit must include only Blood Angels Models. All Models in the Unit gain the Fear (1) Special Rule."},
 "iron-hands": {"key": "the-iron-clad", "name": "The Iron-clad", "roleOnly": ["Command"], "oncePerArmy": True,
   "text": "Command Battlefield Role only. Once per Army. Add one additional War-Engine Battlefield Role Slot to this Detachment; a Unit filling that Slot gains the Champion Sub-Type if it did not already have it."},
 "ultramarines": {"key": "logisticae", "name": "Logisticae", "roleOnly": ["Command"],
   "text": "Command Battlefield Role only. Add one additional Transport or Heavy Transport Battlefield Role Slot to this Detachment; a Unit filling that Slot modifies its Transport Capacity by +2."},
 "salamanders": {"key": "duty-before-death", "name": "Duty Before Death", "roleOnly": ["Troops"],
   "text": "Troops Battlefield Role only. All Models in the Unit gain the Feel No Pain (6+) Special Rule."},
 "raven-guard": {"key": "wraiths", "name": "Wraiths", "roleOnly": ["Troops"],
   "text": "Troops Battlefield Role only. All Models gain Wraiths: after a Rush Move, the Unit may make a Willpower Check — if passed, Charges targeting it in the following Player Turn are Disordered; if failed, the Unit instead gains the Stunned Tactical Status."},
 "emperors-children": {"key": "phoenix-warden", "name": "Phoenix Warden",
   "text": "Tartaros Centurion only. The Model must exchange its combi-bolter and power weapon for a Phoenix power spear (Free) and gains the Skill Unmatched Special Rule."},
 "iron-warriors": {"key": "the-unfavoured", "name": "The Unfavoured",
   "text": "The Unit must include only Infantry-type Models. All Models in the Unit gain the Expendable (1) Special Rule."},
 "night-lords": {"key": "atramentar", "name": "Atramentar",
   "text": "Terminator command units only (Centurion in Terminator Armour, Cataphractii or Tartaros Command Squad). All Models in the Unit gain the Deep Strike and Impact (1) Special Rules."},
 "world-eaters": {"key": "chain-bonded", "name": "Chain-bonded", "roleOnly": ["Command"], "oncePerArmy": True,
   "text": "Command Battlefield Role only. Once per Army. Select another World Eaters Command Unit from your Army; one Model in each gains Chain-brothers — while within Unit Coherency of its partner, +1 to Hit Tests in the Assault Phase (and counts as in the same Combat for Challenges)."},
 "death-guard": {"key": "unnatural-resilience", "name": "Unnatural Resilience", "oncePerArmy": True,
   "text": "Centurion or Cataphractii Centurion only. Once per Army. The Model gains +1 Wound and the Eternal Warrior (2) Special Rule."},
 "thousand-sons": {"key": "telekine-shift", "name": "Telekine Shift", "roleOnly": ["Troops"],
   "text": "Troops Battlefield Role only. All Models gain Telekine Shift: when making a Rush Move the Unit may make a Willpower Check — if passed, it gains the Antigrav Sub-Type and Move Through Cover until the end of the Movement Phase; if failed, it may not Move during that phase."},
 "sons-of-horus": {"key": "martial-supremacy", "name": "Martial Supremacy",
   "text": "Elites Battlefield Role only. One Model in the Unit gains the Champion Sub-Type and the Duellist's Edge (1) Special Rule."},
 "word-bearers": {"key": "zealous-assault", "name": "Zealous Assault", "roleOnly": ["Troops"],
   "text": "Troops Battlefield Role only. All Models in the Unit gain the Impact (S) Special Rule."},
 "alpha-legion": {"key": "rewards-of-treachery", "name": "Rewards of Treachery", "roleOnly": ["Command"],
   "text": "Command Battlefield Role only. Add one additional Battlefield Role Slot (not High Command, Command, Warlord or Lord of War) to this Detachment. Fill it with a Legiones Astartes Unit that does NOT have the Alpha Legion Trait and includes no Unique Models."},
}

# Traitor-allegiance-wide advantage (Liber Hereticus p18 "Corrupted Legions") — added to
# every traitor Legion. The app has no allegiance tracking, so Traitor-only is stated in text.
TRAITORS = ["alpha-legion", "death-guard", "emperors-children", "iron-warriors", "night-lords",
            "sons-of-horus", "thousand-sons", "word-bearers", "world-eaters"]
TRUE_BELIEVERS = {"key": "true-believers", "name": "True Believers",
   "text": "Traitor Allegiance only. All Models in the Unit gain the Malefic Sub-Type. "
           "Malefic: when a Unit composed entirely of Malefic Models would gain any Tactical Status, it is not "
           "applied — instead the Unit suffers D3 automatic wounds (AP 2, Damage 1, no Saving Throws), then no "
           "Status is applied. Malefic Models are unaffected by Special Rules that lower their Leadership, Cool, "
           "Willpower or Intelligence. A non-Malefic Model may not join or be joined by a Unit containing Malefic Models."}


def main():
    changed = 0
    for aid, adv in ADV.items():
        path = os.path.join(ROOT, "data_%s" % aid, "bundle.json")
        if not os.path.exists(path):
            print("  !! missing", path); continue
        b = json.load(open(path))
        pa = b.setdefault("detachments", {}).setdefault("primeAdvantages", [])
        if any(isinstance(x, dict) and x.get("key") == adv["key"] for x in pa):
            continue
        if not CHECK:
            pa.append(adv)
            json.dump(b, open(path, "w"), ensure_ascii=False, indent=1)
        print("%-22s + %s" % (aid, adv["name"]))
        changed += 1
    # traitor-wide True Believers
    for aid in TRAITORS:
        path = os.path.join(ROOT, "data_%s" % aid, "bundle.json")
        if not os.path.exists(path):
            continue
        b = json.load(open(path))
        pa = b.setdefault("detachments", {}).setdefault("primeAdvantages", [])
        if any(isinstance(x, dict) and x.get("key") == TRUE_BELIEVERS["key"] for x in pa):
            continue
        if not CHECK:
            pa.append(TRUE_BELIEVERS)
            json.dump(b, open(path, "w"), ensure_ascii=False, indent=1)
        print("%-22s + %s" % (aid, TRUE_BELIEVERS["name"]))
        changed += 1
    print("\n%s %d advantage(s)." % ("Would add" if CHECK else "Added", changed))


if __name__ == "__main__":
    main()
