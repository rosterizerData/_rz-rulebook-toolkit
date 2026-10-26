# Rosterizer Data Format Principles

What a rulebook author writes, what the app writes for them, and the
shapes the current Rosterizer (v1) reads. `RULEBOOK_AUTHORING.md` is the
manual with the field tables; this document is the set of rules that are
easy to get wrong because older rulebooks, and older copies of the
manual, did them another way.

When something here disagrees with a shipped rulebook, the rulebook is
the older spelling: v1 rewrites it on import (see "Legacy spellings" at
the end). Write new rulebooks as this document says.

---

## The roster root is the `Roster` class

A rulebook configures the roster itself through the **`Roster` class in
`assetTaxonomy`**. There is no `Roster§Roster` catalog item, and no
`Roster§<anything>` item: the root of every roster is the bare class
`Roster`, instantiated directly.

The `Roster` class carries what the root needs:

- `allowed.classifications` — the top-level containers a player adds
- `stats` — the budget stats (a tracked `Points` with its `max`), the
  faction or detachment selectors (rank stats), and anything else that
  belongs to the force as a whole
- `keywords` — the categories the root declares, if any
- `assets.traits` — pieces every roster starts with
- `rules` — the force-level logic; inside these rules `{self}` IS the
  root (`{roster}` resolves to the same node, but the shipped spelling on
  the root is `{self}`)
- `aspects` — **`Label` only** (what the game calls a roster: "Army",
  "Warband", "Team"), plus the grouping aspects when the root's list
  should be grouped or sorted (`Group Includes`, `Group By`,
  `Order Includes A–Z`, `Order Traits A–Z`)

```jsonc
"assetTaxonomy": {
  "Roster": {
    "aspects": { "Label": "Warband" },
    "allowed": { "classifications": ["Unit", "Detachment"] },
    "stats": {
      "Points": { "statType": "numeric", "tracked": true, "value": 0, "max": 1000, "visibility": "always", "groupOrder": -1 },
      "Faction": { "statType": "rank", "value": "-", "dynamic": true, "ranks": { "-": { "order": 0 }, "Steel Lance": { "order": 1 } } }
    }
  }
}
```

**The app owns the root's behaviour.** `Type`, `Visibility`, `Rename`,
`Describe`, `Collapse`, `Lock Qty`, `Unique` and `Assetless` on the
`Roster` class are stamped by the app at composition, the same for every
rulebook, and a value a book writes for them is stripped on import. Do
not author them on the root.

In a dependency chain each book's `Roster` class overlays the one below
it, like any other class: a faction book adds its selectors and allowed
classes to the core's root rather than replacing it.

---

## Sparse by default

Absence means "not authored". Write a field when it says something and
leave it out otherwise:

- no empty containers (`"stats": {}`, `"keywords": { "Faction": [] }` on
  an ITEM, `"assets": { "traits": [] }`) — a class declares an empty
  keyword category on purpose (`"Faction": []` on the class makes the
  category available to its items); an item does not
- no `null` to mean "unset", except where the manual's tables allow null
  (`value: null` on a stat that has no value yet; `format: null`)
- no copies of a class's values on its items — an item states what
  differs from its class
- no fields the engine stamps (see "Never author" below)

The engine composes a class chain into a flat shape at read time; the
file stays sparse.

## Child lists: a bare key or an asset, nothing else

A child in `assets.traits` or `assets.included` is either a **bare item
key** (`"Weapon§Rifle"`) or an **asset object** (`{ "item": "Weapon§Rifle",
"quantity": 2, "stats": { … } }`). A bare key stays bare: do not wrap it
in an object to carry nothing.

A rank's `traits` take the SAME shape: a list of bare keys or asset
objects. The older `{ "path": [...], "trait": "…" }` wrapper is a legacy
spelling (v1 adds a rank's traits to the asset that holds the stat; the
`path` was never read by v1 and is rewritten away on import).

```jsonc
"Loadout": {
  "statType": "rank",
  "dynamic": true,
  "value": "Rifle",
  "ranks": {
    "Rifle":  { "order": 0, "traits": ["Weapon§Rifle"] },
    "Launcher": { "order": 1, "tracking": { "Points": 15 }, "traits": [{ "item": "Weapon§Launcher", "quantity": 1 }] }
  }
}
```

A class that should be addable AS ITSELF, with no catalog item — a
generic "Pawn", a "Model" — carries `"aspects": { "Assetless": true }`.
Without the flag a class offers only its catalog items.

---

## Stats

- `statType` is required: `numeric`, `rank` or `term`. Older books spelt
  other types (`value`, `toggle`); v1 reads them as `numeric` and `rank`
  on import. Write the three.
- `dynamic: true` means the player edits the value in the roster.
  Absent means rule-pinned: the rulebook (or a rule) sets it. Absent and
  `false` are the same thing; write neither for a pinned stat.
- `customValue` is the engine's: when a rule pins a stat the player had
  edited, the player's value is parked there and restored if the pin
  lifts. Never author it.
- `increment: { "value": 5 }` is the step a player's edit moves by.
  Absent means the stat is not stepped (it may still be editable).
- `tracked: true` on a numeric stat sums contributions from descendants:
  a descendant's own tracked stat of the same name, or a selected rank's
  `tracking` dictionary. This is how budgets work; do not write rules to
  add up points.
- `multiSelect` on a rank stat is v1's: the greatest number of ranks a
  player may select at once. `2` or more makes the value an array of
  rank names; `0` means no limit; absent (or `1`) is a single selection.
- `format` is display only: `{v}` the value, `{n}` numeric, `{t}` term,
  `{r}` the rank's index, `{i}` icons. No arithmetic lives in a format.
- `processed` is the engine's scratchpad, rebuilt every time. Never
  author it; v1 drops it from a file on import.

---

## Aspects

The manual lists them. Three notes:

- `Type` has four values: `conceptual`, `game piece`, `add-on`, and v1's
  `datasheet` — the unit card that anchors its own document view. It is a
  type, not a flag: an item is one kind of thing.
- `Visibility` on an asset is `always` (a builder row, unconditionally),
  `edited` (surfaces once the player touched it), `active` (reads on its
  owner's datasheet only) or `hidden` (never in the builder or the
  datasheet).
- `Label` renames what the player SEES without changing the designation
  the engine counts by. Use it for the root's name ("Army") and for an
  item whose display name differs from its key.

---

## Rules

Everything in the manual's rule section stands. The principles:

- A rule's **key is its message**: a validator's failure shows the key
  (`"At least one Leader is required"`). Name mutation rules in words
  too (`"factionConstraint"` is fine, `"rule 3"` is not), and avoid
  spaces in a rule's name when another rule's path will reference it.
- **Mutations pass silently** (`failState: "pass"`), **validators have no
  actions** (`failState: "warning"` or `"error"`). A rule that does both
  is two rules.
- **Stage by order**: compute at one order, read at a later one. Do not
  reach into another rule's eval results across orders; stage through a
  stat (a `_scratch` stat whose name starts with `_` is hidden).
- **Paths address the shape in this document**: `["{self}", "stats",
  "Points", "value"]`, `["{roster}", "tally", "Leader"]`,
  `["{self}", "constraints", "any"]`. On the root, `{self}`.
- The engine stamps `result`, `evalTargets`, `return`, `source`,
  `problem` and `problemNote` on rules as they run. Never author them.

---

## Keys and names

- `§` (U+00A7) joins class and item in a catalog key, and appears nowhere
  else in a key. `Unit§Assault Squad` — the class name exactly as the
  taxonomy spells it, then the item's name.
- An item's class must exist in the taxonomy (of this book or a
  dependency). A key whose class is missing composes nowhere.
- Names are text as a reader sees them: capitals, apostrophes, accents
  and dashes as the game prints them (`Weapon—Mounted`, `Ork’s Choppa`).
  Typographic punctuation is welcome; keys are compared exactly.

---

## Taxonomy first

A rulebook's shape is its taxonomy. Settle the classes before any
catalog work:

- One class per kind of thing a player adds or a rule reasons about.
  Share a stat line through `templateClass` rather than repeating it,
  and split a class where entries differ in placement or rules, not
  where they differ only in a value (the manual's "When to split a
  class, and when not to").
- The class declares every stat its items will need, with `statType`,
  `visibility` and `tracked` where they apply; items fill values. A stat
  an item needs that its class lacks is a taxonomy change, not an item
  field.
- The class declares its keyword categories (`"Faction": []`); items
  carry the values.
- `allowed.classifications` on a container says what goes in it;
  `constraints` filter by keyword; `disallowed` names the exceptions.
- Modules: a shared core (`isModule: true` at the file's top level) holds
  the taxonomy and shared assets; each faction book declares
  `dependencies: [{ "id", "name", "game", "source" }]` on the core and
  adds its own items and overlays. Books in a chain compose class by
  class; a faction's `Roster` class adds to the core's.

---

## Never author

Fields the engine stamps at read or run time. A file that carries them
is only heavier; v1 strips the ones it knows on import.

| Where | Fields |
|---|---|
| any asset or class | `_layers`, `lineage`, `legacy`, `inheritance`, `errors`, `ruled`, `bareResourceKey` |
| a stat | `processed`, `customValue` |
| a rule | `result` (on evals), `evalTargets`, `return`, `source`, `problem`, `problemNote` |
| the `Roster` class | `Type`, `Visibility`, `Rename`, `Describe`, `Collapse`, `Lock Qty`, `Unique`, `Assetless` |

---

## The file

```jsonc
{
  "name": "Game Name",
  "revision": "0.1.0",          // semver, the author's
  "game": "Game Name",
  "genre": "sci-fi",            // sci-fi | fantasy | historical | generic …
  "publisher": "Publisher",
  "url": "https://…",           // the publisher's site, informational
  "notes": "",
  "wip": true,
  "isModule": false,            // true for a shared core other books depend on
  "dependencies": [],
  "rulebook": {
    "assetTaxonomy": { "Roster": { … }, "Unit": { … } },
    "assetCatalog":  { "Unit§Scout": { … } }
  }
}
```

No `schemaVersion` is needed on a file written by hand: the importer
stamps the version it migrates to. No `source`: where a copy came from
is the device's business, not the file's.

---

## Legacy spellings (what v1 rewrites on import)

For readers of older rulebooks, including the examples in this toolkit,
which keep the shapes they shipped with:

- `assetCatalog["Roster§Roster"]` (or `Roster§<label>`) is lifted into
  `assetTaxonomy["Roster"]`; `{roster}` at the root of its rules' paths
  becomes `{self}`.
- A class whose only item is `Class§Class` is collapsed into the class.
- A rank's `{ path, trait }` wrappers become bare keys or assets.
- Stat types outside `numeric | rank | term` are mapped; a quantity
  written as a string becomes a number.
- The app-owned aspects on the `Roster` class are stripped.
