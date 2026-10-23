# bugWars — obfuscated 40k example

A reskinned 40k inheritance chain, used as the canonical worked example for "core game → broad faction → specific army → sub-army" rulebook layering. The mechanics are 1:1 with 40k 10e; only the proper nouns and flavor prose change.

## What's in here

The four-rulebook chain mirrors the source 40k 10e structure:

| Source rulebook | Reskinned as | Role |
|---|---|---|
| `Warhammer_40k_10e.rulebook` | `bugwars_core.rulebook` | Core mechanics, shared classes (Unit, Weapon, Ability, Battle Honour, etc.) |
| `Imperium.rulebook` | `ants.rulebook` | Broad-faction module — depends on core; defines Faction-level constraints, shared keywords |
| `Space_Marines.rulebook` | *TBD ant-marine name* | Specific army — depends on ants; full unit catalog, detachments, wargear |
| `SM_Black_Templars.rulebook` | *TBD Templar-equivalent name* | Sub-army — depends on the ant-marine book; chapter/sub-faction overrides |

Mechanics, stat structures, rule logic, point values, and force-org math are **identical** to the source. Only IP-bearing names and flavor text change.

## Why this is the canonical example

This is the shape that 30k, AoS, and most GW-derivative games share: a core book + faction modules + chapter modules. Get one obfuscated chain right, and every future GW-shape ingestion has a public reference to copy from.

It also exercises every pattern in `docs/RULE_PATTERNS.md`:

- **Module dependencies** (`dependencies` block, slug-referenced parents)
- **Detachments** as roster traits selectable via a roster-level rank stat
- **Faction filter** via constraint path-ref reading the roster's Faction value
- **Wargear** as sub-classes allowed under units, mutex enforced via `Unique`
- **Enhancements** (one per detachment) with their own Points contributions
- **Stratagems** as flat-cost catalog items
- **Force-org constraints** as validators (min Battleline, max Warlord, etc.)
- **Crusade-mode add-ons** (Battle Honours, Battle Scars, Blackstone economy) as a second points budget alongside the main one

## The reskin

**Theme: bugs fighting.** The Imperium-of-Man slot is filled by an ant civilization. The Space Marines slot is the ant soldier-caste; the Black Templars slot is some elite ant sub-caste.

The reskin is a name-and-prose swap, not a system change. Stat names that are generic (Move, Toughness, Save, Wounds, Leadership) stay. Stat names that are IP-coded (e.g. anything called "Astartes-X") get bug-themed replacements.

Flavor prose (rule `text` fields, eval `note` fields, ability descriptions) gets rewritten freely. **It does not have to make sense as a coherent universe.** The bar is "doesn't read as 40k." A rule that originally read "Once per battle, when this Captain leads a unit, the Emperor's gaze grants +1 attack" can become "Once per battle, when this Sergeant-Mandible commands a swarm, the Hive-Mother's chemical wash grants +1 sting" — silly is fine.

Naming map lives in `naming_map.json`. The reskin script (`reskin.py`) reads that map, walks the source rulebook JSON, and emits the obfuscated output. Re-runnable: edit the map, re-run.

## What gets rewritten

Per the Rz schema (see toolkit docs and the rosterizer schema diagram):

- **Designations** (display names of classes and items)
- **Item keys** (`ClassName§ItemName` — the `§`-delimited catalog keys)
- **Keyword values** (especially Faction, Chapter, sub-faction tags)
- **Eval `value` literals** that compare against keyword strings (these are fragile — a missed rename silently breaks the rule)
- **Rule `text` fields** (display text shown to the user)
- **Eval/action `note` fields** (author-facing notes, sometimes shown)
- **Ability text** (the prose body of `Ability` items)
- **Stratagem text**, **Detachment names**, **Enhancement names**
- **Top-level `name`, `game`, `publisher`, `url`, `notes`** (rulebook header)
- **`dependencies[].slug` / `name` / `source`** (chain pointers — must update so each reskinned book points to the previous reskinned book, not the 40k original)

## What does not get rewritten

- Numeric values (point costs, Move/T/Sv numbers, etc.)
- Stat structure (rank options, tracking dicts, min/max)
- Rule logic (eval shapes, action types, order, evaluate, failState)
- Aspect names (`Unique`, `Lock Qty`, `Type`, etc. — these are engine-recognized tokens)
- Path tokens (`{self}`, `{parent}`, `{roster}`, `{this}`)

## Files

| File | Purpose |
|---|---|
| `naming_map.json` | The full reskin dictionary. Source-name → bug-name mappings for factions, units, wargear, abilities, stratagems, prose touchstones. |
| `reskin.py` | One-off script. Reads `naming_map.json`, walks the source rulebooks, emits `bugwars_*.rulebook`. |
| `bugwars_core.rulebook` | Output: 40k 10e core, reskinned. |
| `ants.rulebook` | Output: Imperium, reskinned. |
| *(more outputs)* | Output: Space Marines + Black Templars equivalents. |

## Reproducing

```bash
cd examples/bugWars
python3 reskin.py
# Reads:  ../../../Warhammer40k10e/{Warhammer_40k_10e,Imperium,Space_Marines,SM_Black_Templars}.rulebook
# Reads:  naming_map.json
# Writes: bugwars_core.rulebook, ants.rulebook, <ant-marine>.rulebook, <templar>.rulebook
# Writes: reskin_diff.log (line-by-line list of all substitutions made, for spot-checking)
```

## Why a script and not a hand-pass

Rule logic frequently uses string literals as eval comparisons:

```jsonc
"evals": [{
  "paths": [["{roster}", "stats", "Faction", "value"]],
  "value": "Adeptus Mechanicus"     // <-- a renamed faction string MUST update here too
}]
```

A keyword renamed in one place but missed in an eval comparison silently breaks the rule. Doing the substitution from a single dictionary, deterministically, removes that risk and makes the obfuscation re-runnable when we discover names we want to tweak.
