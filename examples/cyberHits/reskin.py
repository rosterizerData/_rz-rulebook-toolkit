#!/usr/bin/env python3
"""
reskin.py — turn the Gaslands Refuelled rulebook into cyberHits.

Reads:
  ../../../Gaslands/Gaslands-Refuelled.rulebook
  ./naming_map.json

Writes:
  ./cyberhits.rulebook
  ./reskin_diff.log
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_PATH = HERE.parent.parent.parent / "Gaslands" / "Gaslands-Refuelled.rulebook"

NEVER_TOUCH_STAT_NAMES = {
    "abilityName", "x", "modelKey", "keyword", "keyword?",
    "thresh", "noTally", "unitID",
}

ASPECT_TOKENS = {
    "Type", "Lock Qty", "Unique", "Rename", "Describe",
    "Group Traits", "Group Includes", "Order Traits A-Z", "Order Includes A-Z",
    "Visibility", "Label", "Hide Qty",
}

PATH_ROOTS = {"{self}", "{parent}", "{roster}", "{this}"}

# Class-name → naming_map subkey, for §-key item-name dispatching
CLASS_TO_MAP_KEY = {
    "Vehicle":            "vehicles",
    "Weapon":             "weapons",
    "Weapon—Mounted":     "weapons",
    "Weapon—Crew Fired":  "weapons",
    "Weapon—Dropped":     "weapons",
    "Upgrade":            "upgrades",
    "Cargo":              "cargo",
    "Special Rule":       "specialRules",
    "Injury":             "injuries",
    "Damage":             "damages",
    "Sponsor Perk":       "sponsorPerks",
    "Perk":               "perks",
}


def load_map():
    with open(HERE / "naming_map.json", encoding="utf-8") as f:
        return json.load(f)


class Reskinner:
    def __init__(self, nmap):
        self.nmap = nmap
        self.diff = Counter()

        # Whole-string explicit map (factions/sponsors first; small priority pile)
        self.explicit_full = {}
        for kind in ("sponsors", "vehicles", "weapons", "upgrades", "cargo",
                     "specialRules", "injuries", "damages",
                     "sponsorPerks", "perks"):
            for k, v in (nmap.get(kind) or {}).items():
                if k.startswith("_"):
                    continue
                self.explicit_full[k] = (v, kind)

        # Class-keyed item-name maps for §-surgery
        self.classed_maps = {}
        for cls, mapkey in CLASS_TO_MAP_KEY.items():
            entries = {k: v for k, v in (nmap.get(mapkey) or {}).items()
                       if not k.startswith("_")}
            self.classed_maps[cls] = entries

        self.sponsor_map = {k: v for k, v in (nmap.get("sponsors") or {}).items()
                            if not k.startswith("_")}

        # Lexicon, longest-key-first, word-boundary aware where possible
        lex = {k: v for k, v in (nmap.get("lexicon") or {}).items()
               if not k.startswith("_")}
        self.lex_pairs = sorted(lex.items(), key=lambda kv: -len(kv[0]))
        self.lex_regexes = []
        for k, v in self.lex_pairs:
            if re.match(r"^[A-Za-z][A-Za-z0-9 \-'’]*$", k):
                pat = re.compile(r"\b" + re.escape(k) + r"\b")
            else:
                pat = re.compile(re.escape(k))
            self.lex_regexes.append((pat, v, k))

    def transform_str(self, s, *, is_key=False):
        if not isinstance(s, str) or not s:
            return s
        original = s

        if s in PATH_ROOTS or s in ASPECT_TOKENS:
            return s

        if "§" in s:
            cls, name = s.split("§", 1)
            new_name = self._subst_item_name(cls, name)
            result = f"{cls}§{new_name}"
            result = self._lexicon_pass(result)
            if result != original:
                self.diff[("itemKey", original, result)] += 1
            return result

        if s in self.explicit_full:
            new, kind = self.explicit_full[s]
            result = self._lexicon_pass(new)
            if result != original:
                self.diff[(kind, original, result)] += 1
            return result

        result = self._lexicon_pass(s)
        if result != original:
            self.diff[("lexicon", original, result)] += 1
        return result

    def _subst_item_name(self, cls, name):
        m = self.classed_maps.get(cls, {})
        if name in m:
            return m[name]
        if name in self.sponsor_map:
            return self.sponsor_map[name]
        return self._lexicon_pass(name)

    def _lexicon_pass(self, s):
        out = s
        for pat, repl, _key in self.lex_regexes:
            out = pat.sub(repl, out)
        return out

    def walk(self, node, *, ctx_key=None):
        if isinstance(node, dict):
            new = {}
            for k, v in node.items():
                new_k = self._transform_dict_key(k, ctx_key)
                new[new_k] = self.walk(v, ctx_key=k)
            return new
        elif isinstance(node, list):
            return [self.walk(x, ctx_key=ctx_key) for x in node]
        elif isinstance(node, str):
            return self.transform_str(node)
        else:
            return node

    def _transform_dict_key(self, k, parent_key):
        if not isinstance(k, str):
            return k
        original = k

        if "§" in k:
            return self.transform_str(k, is_key=True)

        if parent_key == "assetTaxonomy":
            # Class names left alone — Gaslands' classes (Vehicle, Weapon, etc.)
            # are generic labels, not IP-coded.
            return k

        if parent_key == "stats":
            if k in NEVER_TOUCH_STAT_NAMES:
                return k
            new = self._lexicon_pass(k)
            if new != original:
                self.diff[("statName", original, new)] += 1
            return new

        if parent_key == "tracking":
            if k in NEVER_TOUCH_STAT_NAMES:
                return k
            new = self._lexicon_pass(k)
            if new != original:
                self.diff[("trackingKey", original, new)] += 1
            return new

        if parent_key == "keywords":
            return k

        if parent_key in ("rules", "ranks"):
            # Explicit-map check first (for rank keys that are sponsor/vehicle names)
            if k in self.explicit_full:
                new, kind = self.explicit_full[k]
                # then lexicon over the result for any leftover
                new = self._lexicon_pass(new)
                if new != original:
                    self.diff[(parent_key + "Key/" + kind, original, new)] += 1
                return new
            new = self._lexicon_pass(k)
            if new != original:
                self.diff[(parent_key + "Key", original, new)] += 1
            return new

        return k


def patch_rulebook(doc, nmap):
    h = nmap["rulebookHeader"]
    doc["name"] = h["name"]
    doc["game"] = h["game"]
    doc["publisher"] = h["publisher"]
    doc["url"] = h["url"]
    doc["notes"] = h["notes"]
    return doc


def main():
    nmap = load_map()
    reskinner = Reskinner(nmap)

    if not SOURCE_PATH.exists():
        print(f"MISSING: {SOURCE_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {SOURCE_PATH.name} …")
    with open(SOURCE_PATH, encoding="utf-8") as f:
        doc = json.load(f)

    doc = reskinner.walk(doc)
    doc = patch_rulebook(doc, nmap)

    out_path = HERE / nmap["rulebookHeader"]["outputFile"]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print(f"  wrote {out_path.name}")

    # Diff log
    lines = ["=== ALL SUBSTITUTIONS (kind | count | original → replacement) ==="]
    for (kind, orig, repl), count in reskinner.diff.most_common():
        o = orig if len(orig) <= 80 else orig[:77] + "…"
        r = repl if len(repl) <= 80 else repl[:77] + "…"
        lines.append(f"  {kind:18s}  {count:5d}  {o!r}  →  {r!r}")
    log_path = HERE / "reskin_diff.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nWrote {log_path.name} "
          f"({len(reskinner.diff)} unique substitution pairs, "
          f"{sum(reskinner.diff.values())} total occurrences).")


if __name__ == "__main__":
    main()
