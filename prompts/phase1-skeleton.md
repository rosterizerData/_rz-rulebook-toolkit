# Phase 1 — Skeleton Builder Prompt

Paste this prompt into a fresh Claude conversation. Replace the `[GAME]` block at the bottom with whatever you know about the game before you start. Claude will ask follow-up questions before producing anything.

---

You are helping author a **Rosterizer rulebook** — a JSON file that drives army/roster building for a tabletop game. Your job in this phase is to produce a **skeleton rulebook**: the class hierarchy, stat shapes, keyword categories, and one concrete catalog item per leaf class. No rules beyond structural validators. The output must be importable into Rosterizer and allow at least one unit to be added to a roster so a tester can verify the structure works.

## What you need to know first

Before writing anything, ask the user these questions. Ask them all at once; do not proceed until you have answers.

1. **Game name and publisher.** What is the official name? Who publishes it?
2. **Is there an online rulebook, Wahapedia page, BSData repo, or other authoritative data source?** Provide URLs if known.
3. **Is there a comparable existing Rosterizer rulebook to draw structure from?** (e.g. "it's like 40k10e but simpler", "it's like Gaslands — flat, no factions")
4. **What is the army-building container structure?** How does a player build a legal force? (e.g. "a Detachment of 1 HQ + 2 Troops", "a Warband with up to 10 models", "a list of up to 2000 points")
5. **What stat line do models have?** List the stats (Move, Attack, Toughness, etc.) and their types (number, pick-from-list, free text).
6. **Are there factions, sub-factions, or allegiances that filter what units are available?** If so, what are they and how do they nest?
7. **What are the major asset classes?** (e.g. Characters, Vehicles, Infantry, Weapons, Abilities, Wargear) Which ones are "game pieces" the player adds, and which are organizational containers?
8. **What is the points system?** Fixed per unit? Per model? Derived from stats? No points at all?
9. **Are there formation/detachment rules** that constrain which units can be taken together, or slot limits within a formation?
10. **Anything structurally unusual** that doesn't fit a standard "pick units, pick weapons" pattern?

## What to produce

Once you have answers, produce a single `.rulebook` JSON file with:

### `assetTaxonomy`
- One class per major asset type identified in Q7
- Each class has: `aspects`, `stats` (with correct `statType`, `visibility`, and `tracked` where needed), `keywords` category declarations, `allowed.classifications`
- The stat columns in the taxonomy define which columns will appear in Phase 2 CSVs — include every stat that will be needed for data entry, not just the ones needed for rules
- Use `templateClass` inheritance where classes share a stat line (e.g. Infantry and Vehicle both extend a base Unit class)
- The `Roster` class IS the roster root (there is no `Roster§Roster` catalog item in the current format): it declares `allowed.classifications` for all top-level containers, a Points budget stat if the game uses one, any faction/allegiance rank stats, `aspects.Label` for what the game calls a roster, and a `text` field with a brief build-order guide. Do not author `Type`, `Visibility`, `Rename`, `Describe`, `Collapse`, `Lock Qty`, `Unique` or `Assetless` on it; the app stamps those.

### `assetCatalog`
- **One concrete item per leaf class** — use placeholder stats, but use **real names from the game** for both the class and item designation (e.g. `Troops§Tactical Squad`, not `Unit§Example Unit`). These placeholders will be overwritten by the Phase 2 CSV import, so their stats don't need to be accurate — but their names and keyword values should be correct so the import target is obvious
- Each item must have: correct `keywords`, any `assets.traits` that are always present, and a `text` field noting what makes this item special (or "placeholder — will be replaced by CSV import" if unknown)

### Structural validators only
Limit rules to:
- "Select your Faction/Allegiance" warnings
- "Must have at least one [required unit type]" errors
- Points budget enforcement (`applyMaxPoints` pattern)
- Model count min/max on any unit with a variable size

Do **not** add per-unit wargear rules, cost formulas, or inter-unit constraint rules. Those are Phase 3.

## Format rules

- Use the exact JSON structure from the examples below
- `§` (section sign, U+00A7) separates class from item name in catalog keys
- Stat names that start with `_` are hidden scratch values (not displayed)
- `tracked: true` on a numeric stat means it auto-sums contributions from descendants
- `dynamic: true` means the user can edit the value in the roster
- `visibility` options: `"always"`, `"normal"`, `"active"`, `"hidden"`
- `failState: "pass"` on a rule means "silently skip if condition is not met" — use this for mutation rules
- `failState: "warning"` or `"error"` for validators — the rule's key name is the displayed message

## Reference shape (minimal working skeleton)

```json
{
  "name": "Game Name",
  "revision": "0.1.0",
  "game": "Game Name",
  "genre": "fantasy",
  "publisher": "Publisher Name",
  "wip": true,
  "rulebook": {
    "assetTaxonomy": {
      "Unit": {
        "aspects": { "Type": "game piece", "Rename": true },
        "keywords": { "Faction": [], "Role": [], "Tags": [] },
        "stats": {
          "Move":   { "statType": "numeric", "value": null, "visibility": "normal" },
          "Points": { "statType": "numeric", "tracked": true, "value": 0, "visibility": "normal" }
        }
      },
      "Roster": {
        "aspects": { "Label": "Army" },
        "allowed": { "classifications": ["Unit"] },
        "stats": {
          "Points": { "statType": "numeric", "tracked": true, "value": 0, "visibility": "always", "groupOrder": -1, "format": "{v} / {max}", "max": 1000 }
        },
        "text": "Build order placeholder."
      }
    },
    "assetCatalog": {
      "Unit§[Real Unit Name From Game]": {
        "keywords": { "Faction": ["[Real Faction Name]"], "Role": ["Troops"] },
        "stats": { "Move": { "value": 0 }, "Points": { "value": 0 } },
        "text": "Placeholder — will be replaced by CSV import."
      }
    }
  }
}
```

## Stopping condition

After producing the skeleton, tell the user:

> **Phase 1 complete.** Import this file into Rosterizer and verify that the structure behaves as expected. At minimum:
> - A new roster can be created
> - At least one unit from each leaf class can be added
> - Any faction/allegiance selectors are visible and filter correctly
> - The points total (if applicable) appears on the roster
> - Any structural slot limits (e.g. max 1 HQ, max 4 Troops) trigger correctly
>
> Test anything else the game's structure requires. Report what breaks. Do not proceed to Phase 2 until the skeleton passes your checks.

---

## Game info (fill this in before pasting the prompt)

```
Game name:
Publisher:
Data sources / URLs:
Comparable Rosterizer rulebook (if known):
Anything you already know about the structure:
```
