# BSData Ingestion Reference

See also: [BS_schema.png](BS_schema.png) — an entity-relationship diagram of the BSData XML schema. Source unknown; provenance unverified, but it's consistent with the structure the original tool handled. Useful for orienting in the node graph before writing a parser.

How BSData XML structures map to Rosterizer rulebook concepts. Derived from the now-deleted `battlescribe-to-rosterizer` Angular app (`app.component.ts`), preserved here as the reference for anyone building a fresh ingestion tool.

## BSData XML → Rosterizer concept map

| BSData element | Rosterizer equivalent | Notes |
|---|---|---|
| `CATALOGUE` / `GAMESYSTEM` | Rulebook | Top-level container |
| `SELECTIONENTRY` | `assetCatalog` item | The core data unit; `$.TYPE` → class, `$.NAME` → designation |
| `SELECTIONENTRYGROUP` | `rank` stat | Group name → stat name; member entries → rank options |
| `PROFILE` (shared) | `assetCatalog` item | `$.TYPENAME` → class, `$.NAME` → designation |
| `PROFILE` (inline) | Stats merged into parent item | `$.TYPENAME === 'profile'` → stats go on the parent, not a child |
| `CHARACTERISTIC` with short value | Stat | `$.NAME` → stat name; numeric string → `numeric` statType, else `term` |
| `CHARACTERISTIC` with long value (>15 chars) | `text` field | Rule description text goes here |
| `RULE` (shared) | `assetCatalog` item, class `Rule` | `$.NAME` → designation; `DESCRIPTION` → `text` |
| `INFOLINK` (type=profile) | Stats merged into parent | The linked profile's characteristics are applied directly to the linking item |
| `INFOLINK` (type=rule) | `assets.traits` entry | Adds the linked rule as a trait on the linking item |
| `ENTRYLINK` | `assets.traits` entry | Adds the linked entry as a trait |
| `CATEGORYLINK` | `keywords` | `$.NAME` or resolved name from IDResult; if contains `: `, splits into category + value; otherwise goes into `Keywords` category |
| `COSTS` / `COST` | Tracked Points stat | `$.NAME` → stat name; value → item stat value; always `numeric`, always `tracked: true` |
| `FORCEENTRY` | Conceptual container class `Force` | Roster-level force org structure |
| `SHAREDSELECTIONENTRYGROUP` | Class-level rank stat | Same as SELECTIONENTRYGROUP but defined once and referenced |

## ID resolution

BSData uses `TARGETID` references instead of inline nesting. The original tool built a flat ID lookup table (`findIDs`) by recursively walking the entire parsed XML tree and indexing every object with an `ID` property. Path: resolve `TARGETID` → lookup in IDResult → get the target object's type and name.

When resolving a linked item's class, the lookup chain was:
```
IDResult[IDResult[link.$.TARGETID]?.ID]?.$.TYPE
  || IDResult[IDResult[link.$.TARGETID]?.ID]?.$.TYPENAME
  || IDResult[link.$.TARGETID]?.$.TYPE
  || IDResult[link.$.TARGETID]?.$.TYPENAME
  || link.$.TYPE
  || link.$.TYPENAME
```
(The double-lookup handles cases where IDResult points to a wrapper object containing the actual node.)

## SELECTIONENTRYGROUP → rank stat

A group with multiple member entries becomes a rank stat where the user picks one:

```
SELECTIONENTRYGROUP (name = "Weapon")
  ENTRYLINK (name = "Bolter")
  ENTRYLINK (name = "Plasma gun")
  ENTRYLINK (name = "Flamer")
```

Becomes:

```json
"Weapon": {
  "statType": "rank",
  "ranks": {
    "-":          { "order": 0 },
    "Bolter":     { "order": 1 },
    "Plasma gun": { "order": 2 },
    "Flamer":     { "order": 3 }
  }
}
```

The `-` default rank is added automatically when the group has more than one member. The original tool did not wire up `tracking` (points costs) or `traits` (the actual weapon items) — those require post-import authoring in Phase 3.

## What the original tool produced vs. what's needed

The original tool output a rough **rulebook JSON** directly from BSData. This is the wrong target for the current workflow. The Phase 2 CSV format is better because:

1. It separates data entry from rule authoring — the rulebook doesn't get rules until Phase 3
2. It's reviewable by a human without understanding the rulebook format
3. Import errors are easier to diagnose per-row than per-JSON-object

A rewrite of this tool should output **Phase 2 CSVs** instead of rulebook JSON. The mapping above still applies for extracting stats, keywords, traits, and text — but instead of writing `assetCatalog[itemKey].stats[name].value = X`, write a CSV cell at column `stats§[name]` with value `X`.

## What the original tool got wrong / left incomplete

- **No `tracking` on rank stats** — weapon selection groups had rank options but no points costs wired up
- **No `traits` on rank stats** — selecting a weapon didn't attach the weapon item as a trait
- **No `allowed`/`constraints`** — force org slot rules were not translated
- **`text` threshold of 15 chars** was arbitrary — some rule descriptions are short
- **Keyword splitting on `: `** was a heuristic that works for GW games (e.g. `Faction: Imperium`) but not universally
- **`ucFirst` only** — no other name normalization; BSData names are generally already title-cased
- **Angular + xml2js dependency** — uppercase XML keys (`CATALOGUE`, `SELECTIONENTRY`, etc.) are artifacts of `xml2js`'s `strict: false` mode; a Python rewrite using `lxml` or `xmltodict` would produce lowercase keys and be cleaner

## Suggested Python rewrite entry points

If rebuilding this as a Python tool in `tools/`:

```python
import xmltodict  # produces lowercase keys, no strict-mode weirdness

def parse_catalogue(xml_path):
    with open(xml_path) as f:
        data = xmltodict.parse(f.read())
    # top level: data['catalogue'] or data['gameSystem']
    ...

def build_id_index(node, index=None):
    # recursively walk, index anything with @id attribute
    ...

def map_selection_entry(entry, id_index) -> dict:
    # returns a dict of CSV field values for one row
    ...
```

Output: one CSV per class, matching the Phase 2 column format from `prompts/phase2-data-ingestion.md`.
