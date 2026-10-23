#!/usr/bin/env python3
"""
reskin.py — turn the 40k 10e core/Imperium/Space Marines/Black Templars
rulebook chain into the bugWars chain.

Reads:
  ../../../Warhammer40k10e/{Warhammer_40k_10e,Imperium,Space_Marines,SM_Black_Templars}.rulebook
  ./naming_map.json

Writes:
  ./bugwars_core.rulebook
  ./formica_dominion.rulebook
  ./mandible_legion.rulebook
  ./bullet_ant_crusade.rulebook
  ./reskin_diff.log

Re-runnable: edit naming_map.json, re-run.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_DIR = HERE.parent.parent.parent / "Warhammer40k10e"

SOURCE_FILES = {
    "40k10e":         SOURCE_DIR / "Warhammer_40k_10e.rulebook",
    "Imperium":       SOURCE_DIR / "Imperium.rulebook",
    "Space Marines":  SOURCE_DIR / "Space_Marines.rulebook",
    "Black Templars": SOURCE_DIR / "SM_Black_Templars.rulebook",
}

DEP_CHAIN = [
    ("40k10e",         None),
    ("Imperium",       "40k10e"),
    ("Space Marines",  "Imperium"),
    ("Black Templars", "Space Marines"),
]

# Stat names left alone (engine reads them; safe defaults to keep)
NEVER_TOUCH_STAT_NAMES = {
    "abilityName", "x", "modelKey", "keyword", "keyword?",
    "thresh", "noTally", "unitID",
    "model1stTally", "model2ndTally", "model3rdTally", "model4thTally",
    "model2ndCost", "model3rdCost", "model4thCost",
    "main1","main2","main3","main4","main5","main6","main7","main8","main9","main10",
    "secondary1","secondary2","secondary3","secondary4","secondary5","secondary6",
    "initiates1stTally","neophytes1stTally","neophytes2ndTally",
}

# Aspect names recognized by the engine — never substitute
ASPECT_TOKENS = {
    "Type", "Lock Qty", "Unique", "Rename", "Describe",
    "Group Traits", "Group Includes", "Order Traits A-Z", "Order Includes A-Z",
    "Visibility", "Label", "Hide Qty",
}

# Path roots — never substitute
PATH_ROOTS = {"{self}", "{parent}", "{roster}", "{this}"}


def load_map():
    with open(HERE / "naming_map.json", encoding="utf-8") as f:
        return json.load(f)


# ── substitution machinery ──────────────────────────────────────────────────


def _case_match(matched: str, replacement: str) -> str:
    """Return `replacement` with its casing matched to `matched`.
    Cases handled: ALL-CAPS, Title-Case, lower; mixed case falls through
    to the replacement as-written.
    """
    if matched.isupper() and any(c.isalpha() for c in matched):
        return replacement.upper()
    if matched.islower():
        return replacement.lower()
    # Title case detection: every word starts capital
    words = matched.split()
    if words and all(w[:1].isupper() and (w[1:].islower() or len(w) <= 1) for w in words):
        return replacement
    return replacement


class Reskinner:
    def __init__(self, nmap):
        self.nmap = nmap
        self.diff = Counter()  # (kind, original, replacement) -> count

        # whole-string explicit maps (matched first)
        self.explicit_full = {}
        for kind in ("factions", "sources", "stats", "taxonomyClasses",
                     "detachments", "namedCharacters", "stratagems", "enhancements"):
            for k, v in nmap.get(kind, {}).items():
                if k.startswith("_"):  # skip _comment
                    continue
                self.explicit_full[k] = (v, kind)

        # union of all explicit names by category for §-key surgery
        self.tax_map = {k: v for k, v in nmap.get("taxonomyClasses", {}).items()
                        if not k.startswith("_")}
        self.detach_map = {k: v for k, v in nmap.get("detachments", {}).items()
                           if not k.startswith("_")}
        self.strat_map = {k: v for k, v in nmap.get("stratagems", {}).items()
                          if not k.startswith("_")}
        self.enh_map = {k: v for k, v in nmap.get("enhancements", {}).items()
                        if not k.startswith("_")}
        self.char_map = {k: v for k, v in nmap.get("namedCharacters", {}).items()
                         if not k.startswith("_")}
        self.faction_map = {k: v for k, v in nmap.get("factions", {}).items()
                            if not k.startswith("_")}

        # lexicon: long keys first
        lex = {k: v for k, v in nmap.get("lexicon", {}).items()
               if not k.startswith("_")}
        self.lex_pairs = sorted(lex.items(), key=lambda kv: -len(kv[0]))

        # precompiled regexes for word-boundary substitution.
        # For "word-shaped" keys we ALSO compile a case-insensitive variant
        # that preserves the matched text's case style on substitution
        # (so source ALL-CAPS emphasis like "ADEPTUS ASTARTES" gets an
        # ALL-CAPS replacement). The exact-case match runs first; the
        # case-insensitive sweep cleans up any residue.
        self.lex_regexes = []
        for k, v in self.lex_pairs:
            if re.match(r"^[A-Za-z][A-Za-z0-9 \-'’]*$", k):
                pat = re.compile(r"\b" + re.escape(k) + r"\b")
                pat_ci = re.compile(r"\b" + re.escape(k) + r"\b", re.IGNORECASE)
            else:
                pat = re.compile(re.escape(k))
                pat_ci = None
            self.lex_regexes.append((pat, pat_ci, v, k))

    # ─── core string transformer ────────────────────────────────────────────

    def transform_str(self, s, *, is_key=False):
        """Transform a single string value or a dict-key string."""
        if not isinstance(s, str) or not s:
            return s

        original = s

        # path roots / aspects pass through untouched
        if s in PATH_ROOTS or s in ASPECT_TOKENS:
            return s

        # 1. §-keyed item refs ("Class§Name") get class+name substitution
        if "§" in s:
            parts = s.split("§", 1)
            if len(parts) == 2:
                cls, name = parts
                new_cls = self.tax_map.get(cls, cls)
                new_name = self._subst_item_name(cls, name)
                result = f"{new_cls}§{new_name}"
                # then run lexicon over the whole result for any leftover tokens
                result = self._lexicon_pass(result)
                if result != original:
                    self.diff[("itemKey", original, result)] += 1
                return result

        # 2. Whole-string match against the explicit maps
        if s in self.explicit_full:
            new, kind = self.explicit_full[s]
            # may still benefit from lexicon (rarely — explicit is usually final)
            result = self._lexicon_pass(new)
            if result != original:
                self.diff[(kind, original, result)] += 1
            return result

        # 3. Lexicon pass on prose / leftover strings
        result = self._lexicon_pass(s)
        if result != original:
            self.diff[("lexicon", original, result)] += 1
        return result

    def _subst_item_name(self, cls, name):
        """Substitute an item name based on its class context."""
        # Class-specific explicit overrides first
        if cls == "Detachment" and name in self.detach_map:
            return self.detach_map[name]
        if cls == "Stratagem" and name in self.strat_map:
            return self.strat_map[name]
        if cls == "Enhancement" and name in self.enh_map:
            return self.enh_map[name]
        if cls == "Character" and name in self.char_map:
            return self.char_map[name]
        # Faction-classed items (rare but possible)
        if name in self.faction_map:
            return self.faction_map[name]
        if name in self.char_map:
            return self.char_map[name]
        # Fall through to lexicon
        return self._lexicon_pass(name)

    def _lexicon_pass(self, s):
        out = s
        for pat, pat_ci, repl, _key in self.lex_regexes:
            # First the exact-case substitution
            out = pat.sub(repl, out)
            # Then case-insensitive cleanup for word-shaped keys, preserving
            # the matched text's case style (ALL-CAPS / Title / lower).
            if pat_ci is not None:
                out = pat_ci.sub(lambda m, r=repl: _case_match(m.group(0), r), out)
        return out

    # ─── tree walker ────────────────────────────────────────────────────────

    def walk(self, node, *, ctx_key=None):
        """Recursively transform a JSON tree in place. Returns the (possibly
        new) node — caller should reassign."""
        if isinstance(node, dict):
            new = {}
            for k, v in node.items():
                # Decide whether to transform the dict key.
                # Catalog item keys ("Class§Name") and class names need transformation.
                # Stat names: transform unless on the never-touch list.
                # Most other keys are engine-recognized identifiers; leave them.
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
        """Transform a dict key when the key itself is content-bearing."""
        if not isinstance(k, str):
            return k

        original = k

        # §-keyed catalog/asset keys
        if "§" in k:
            new = self.transform_str(k, is_key=True)
            return new

        # Taxonomy class names live as keys directly under "assetTaxonomy".
        # We detect this via parent_key.
        if parent_key == "assetTaxonomy" and k in self.tax_map:
            new = self.tax_map[k]
            self.diff[("taxonomyClasses", original, new)] += 1
            return new

        # Stat names (under any "stats" dict). Apply explicit map first, then
        # lexicon for the long-tail loadout/weapon-line stat names.
        if parent_key == "stats":
            if k in NEVER_TOUCH_STAT_NAMES:
                return k
            stat_map = self.nmap.get("stats", {})
            if k in stat_map and not k.startswith("_"):
                new = stat_map[k]
                self.diff[("statName", original, new)] += 1
                return new
            new = self._lexicon_pass(k)
            if new != original:
                self.diff[("statNameLex", original, new)] += 1
            return new

        # Keyword categories (under "keywords") — leave alone (Faction, Category, etc.)
        if parent_key == "keywords":
            return k

        # Tracking-dict keys (under ranks/<rank>/tracking) are stat names —
        # apply the same logic as parent_key=="stats".
        if parent_key == "tracking":
            if k in NEVER_TOUCH_STAT_NAMES:
                return k
            stat_map = self.nmap.get("stats", {})
            if k in stat_map and not k.startswith("_"):
                new = stat_map[k]
                self.diff[("trackingKey", original, new)] += 1
                return new
            new = self._lexicon_pass(k)
            if new != original:
                self.diff[("trackingKeyLex", original, new)] += 1
            return new

        # Rule names (under "rules") and rank keys (under "ranks") get the
        # lexicon pass. Their cross-rule and eval-value references are strings
        # that the walker substitutes the same way, so the rename stays
        # consistent.
        if parent_key in ("rules", "ranks"):
            new = self._lexicon_pass(k)
            if new != original:
                self.diff[(parent_key + "Key", original, new)] += 1
            return new

        # Default: leave key alone
        return k


# ── per-rulebook header / dependency patching ──────────────────────────────

def patch_rulebook(book_key, doc, nmap):
    headers = nmap["rulebookHeaders"][book_key]
    doc["name"] = headers["name"]
    doc["game"] = headers["game"]
    doc["publisher"] = headers["publisher"]
    doc["url"] = headers["url"]
    doc["notes"] = headers["notes"]

    # Dependency chain: rewrite each dep to point at the bug version
    new_deps = []
    for dep in doc.get("dependencies", []) or []:
        # Find the source-side parent name
        src_name = dep.get("name")
        # Resolve source name -> bug name via headers map (reverse lookup by key)
        for src_key, h in nmap["rulebookHeaders"].items():
            if src_key == src_name:
                new_dep = {
                    "slug": h["newSlug"],
                    "name": h["name"],
                    "game": h["game"],
                    "source": h["url"],
                }
                new_deps.append(new_dep)
                break
        else:
            # Unknown dep — keep but warn
            print(f"  WARN: unknown dependency '{src_name}' in {book_key}; "
                  f"keeping as-is", file=sys.stderr)
            new_deps.append(dep)
    doc["dependencies"] = new_deps

    return doc


# ── main ────────────────────────────────────────────────────────────────────

def main():
    nmap = load_map()
    reskinner = Reskinner(nmap)

    diff_log_lines = []

    for book_key, _parent in DEP_CHAIN:
        src_path = SOURCE_FILES[book_key]
        if not src_path.exists():
            print(f"MISSING: {src_path}", file=sys.stderr)
            continue

        print(f"Reading {src_path.name} …")
        with open(src_path, encoding="utf-8") as f:
            doc = json.load(f)

        # Capture original deps BEFORE the walker rewrites them; we'll
        # rebuild them from the source-side names.
        original_deps = doc.get("dependencies", []) or []

        # Walk-and-rewrite the entire tree first
        before_diff_count = len(reskinner.diff)
        doc = reskinner.walk(doc)

        # Restore originals so patch_rulebook can do the source→bug mapping
        doc["dependencies"] = original_deps

        # Patch rulebook headers + deps last (overrides anything the walker did
        # to the top-level fields)
        doc = patch_rulebook(book_key, doc, nmap)

        # Write output
        out_name = nmap["rulebookHeaders"][book_key]["outputFile"]
        out_path = HERE / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        print(f"  wrote {out_path.name}")

        diff_log_lines.append(f"\n=== {book_key} → {out_name} ===")
        per_book_count = sum(reskinner.diff.values()) - before_diff_count
        diff_log_lines.append(f"  total substitutions in this book "
                              f"(cumulative across run): {sum(reskinner.diff.values())}")

    # Diff log: every (kind, original, replacement) and its frequency
    diff_log_lines.append("\n=== ALL SUBSTITUTIONS (kind | count | original → replacement) ===")
    for (kind, orig, repl), count in reskinner.diff.most_common():
        # truncate long prose for readability
        o = orig if len(orig) <= 80 else orig[:77] + "…"
        r = repl if len(repl) <= 80 else repl[:77] + "…"
        diff_log_lines.append(f"  {kind:18s}  {count:5d}  {o!r}  →  {r!r}")

    log_path = HERE / "reskin_diff.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(diff_log_lines) + "\n")
    print(f"\nWrote {log_path.name} "
          f"({len(reskinner.diff)} unique substitution pairs, "
          f"{sum(reskinner.diff.values())} total occurrences).")


if __name__ == "__main__":
    main()
