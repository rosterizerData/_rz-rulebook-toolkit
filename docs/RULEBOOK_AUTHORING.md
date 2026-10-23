# Rosterizer Rulebook Authoring

The reference manual that doesn't exist anywhere else. Distilled from the in-app help, the runtime engine, and analysis of shipped rulebooks.

## What a rulebook is

A rulebook is a JSON file that describes a tabletop game's data model and rules. It gets imported into Rosterizer and drives every roster built against it. Two top-level structures:

```jsonc
{
  "name": "Game Name",
  "id": "game-name",
  "revision": "0.1.0",
  "game": "Game Name",
  "publisher": "...",
  "wip": false,
  "rulebook": {
    "assetTaxonomy": { /* classes (templates) */ },
    "assetCatalog":  { /* items (instances) */ }
  }
}
```

- **Asset taxonomy** is the set of *classes* — abstract types like `Unit`, `Weapon`, `Ability`. A class declares stats, allowed children, default aspects, and rules that apply to all of its items.
- **Asset catalog** is the set of *items* — concrete instances like `Unit§Goblin`, `Weapon§Energy Sword`. Catalog keys use `ClassName§ItemName` format. The `§` character is reserved.

A class can extend another class via `templateClass`. Inheritance flattens during composition — you don't write inheritance handling, the engine does.

The roster instance itself is configured by a catalog item keyed `Roster§Roster`. Stats, rules, allowed sub-classes, and constraints declared there shape the roster as a whole. Inside rules attached to that item, `{self}` and `{roster}` both resolve to the roster node (use `{self}` by convention — it's what shipped rulebooks use).

## The vocabulary

Most of the terminology comes from the in-app help. Use these names consistently.

- **Asset**: any thing in a roster (units, weapons, abilities). The roster itself is an asset too.
- **Class** / **classification**: an asset template. Catalog items derive from a class.
- **Item**: a concrete catalog entry, keyed `ClassName§ItemName`.
- **Stat**: a discrete property of an asset (Move, Attack, Points). Three statTypes: `numeric`, `rank` (a value selected from a list of options), `term` (free string).
- **Keyword**: a categorization tag. Keywords are grouped into named categories. Used for filtering, constraint matching, and display grouping.
- **Aspect**: a behavioral flag on an asset (`Unique`, `Lock Qty`, `Rename`, `Describe`, `Type`, etc.).
- **Trait**: a sub-asset that's intrinsic to its parent and can't be removed by the roster author.
- **Include**: a sub-asset that's added by default but *can* be removed.
- **Allowed**: what classes/items can be added to an asset as children.
- **Disallowed**: what specifically *cannot* be added, overriding `allowed`.
- **Constraints**: keyword-based filters on what's allowed (`any`, `all`, `none`, `not`).
- **Tally**: a count, bubbled up from descendants.
- **Tracked stat**: a numeric stat that automatically sums values from descendants of the same name.
- **Rule**: conditional logic. Has `evals` (conditions), `actions` (mutations), `failState` (what happens if evals fail), `evaluate` (AND/OR), `order` (execution priority).

## Stats

Three types:

```jsonc
{
  "Move": {
    "statType": "numeric",
    "value": 6,
    "min": 0,
    "max": 12,
    "dynamic": true        // user can edit in roster
  },
  "Attack": {
    "statType": "rank",
    "value": "3",
    "dynamic": true,
    "ranks": {
      "1": { "order": 1, "tracking": { "Points": 1 } },
      "2": { "order": 2, "tracking": { "Points": 2 } },
      "3": { "order": 3, "tracking": { "Points": 5 } }
    }
  },
  "Notes": {
    "statType": "term",
    "value": ""
  }
}
```

**`tracked: true`** on a numeric stat makes it sum contributions from descendants automatically. Two contribution sources:

1. A descendant asset has a stat with the same name + `tracked: true` → its value bubbles to the parent.
2. A descendant has a ranked stat whose selected rank has a `tracking: { ParentStatName: N }` dictionary → N gets added to the parent's tracked stat. **This is the canonical way to do "Points" budgets.**

**`dynamic: true`** lets the user edit the value in the roster. Without it, the value is locked to whatever the rulebook (or rules) sets.

**`visibility`**: `always`, `normal`, `active`, or `hidden`. Negative `groupOrder` puts a stat ahead of the asset name (highly visible), positive groupOrder puts it after.

**`format`**: a display string with `{v}` (value), `{n}` (numeric), `{t}` (term), `{r}` (rank index), `{i}` (icons). Display only — no arithmetic.

**`min` / `max`**: enforced bounds. Can be a number or a path-ref to another stat.

## Keywords

Keywords live in named categories. Category names are arbitrary; declare them on a class to make them available to its items:

```jsonc
"Unit": {
  "keywords": {
    "Faction": [],
    "Role": [],
    "Tags": []        // "Tags" category is hidden in the roster view
  }
}
```

Items add specific values:

```jsonc
"Unit§Scout": {
  "keywords": {
    "Faction": ["Steel Lance"],
    "Role": ["Recon"]
  }
}
```

Keywords drive: visual grouping in the inventory, constraint matching, and rule conditions.

## Allowed, disallowed, constraints

```jsonc
"Squad": {
  "allowed": {
    "classifications": ["Trooper", "Specialist"],
    "items": []
  },
  "disallowed": {
    "items": ["Trooper§Heavy Gunner"]
  },
  "constraints": {
    "any":  ["Steel Lance"],   // sub-asset must have at least one of these keywords
    "all":  [],                // sub-asset must have all of these
    "none": ["Daemonic"],      // sub-asset must have none of these
    "not":  []                 // sub-asset must not have all of these (NAND)
  }
}
```

Keyword constraints only filter assets that *have* keywords. Vanilla (keywordless) assets always pass.

## Aspects

Behavioral flags. The common ones:

- **`Type`**: `game piece` (model/card), `conceptual` (squad/ability), `add-on`. Affects default styling.
- **`Lock Qty`**: quantity can't be adjusted by the user.
- **`Unique`**: only one instance of this asset per parent allowed. Powers mutex enforcement.
- **`Rename`**: user can rename the asset.
- **`Describe`**: user can add free-text description.
- **`Group Traits`** / **`Group Includes`**: visually group sub-assets by class.
- **`Order Traits A–Z`** / **`Order Includes A–Z`**: alphabetize sub-assets.
- **`Visibility`**: `always`, `edited`, `active` — when to show the asset.
- **`Label`**: override the displayed name without changing the designation (preserves tally bookkeeping).

## Rules

The most complex part of the format. Every rule has the same shape:

```jsonc
{
  "evals":     [ /* conditions */ ],
  "actions":   [ /* mutations to apply if evals pass */ ],
  "evaluate":  "AND" | "OR",     // how to combine evals
  "failState": "pass" | "warning" | "error" | "disable" | "hide",
  "order":     0                  // execution bucket; lower runs first
}
```

### Eval

A condition. Evaluates one or more paths against bounds, equality, or contains.

```jsonc
{
  "paths":      [ ["{self}", "stats", "Move", "value"] ],
  "operator":   "AND",                  // "AND" | "OR" | "SUM"
  "value":      6,                      // equality target (literal or path-ref)
  "min":        0,                      // numeric lower bound
  "max":        10,                     // numeric upper bound
  "contains":   true,                   // substring/element match
  "not":        false,                  // invert truthiness
  "actionable": true,                   // counts toward rule pass/fail; if false, eval is informational
  "equation": {
    "operator": "T*O",                  // T/O, O/T, T*O, T+O, T-O, O-T
    "value": 0.5                        // operand (literal or path-ref)
  }
}
```

Eval results are stored in `evals[N].result` with fields `float`, `integer`, `string`, `array`, `truthy`. Subsequent evals (in the same rule or later rules) can read these via path syntax — see `PATH_SYNTAX.md`.

`operator: "SUM"` sums numeric values from multiple paths into `result.float`. For non-numeric paths, it counts truthy values. Combined with `equation`, you can do `SUM × constant`, `SUM ÷ N`, etc.

### Action

A mutation. Applied to one or more paths.

```jsonc
{
  "paths":      [ ["{self}", "stats", "Points", "value"] ],
  "actionType": "set" | "modify" | "add" | "remove" | "info",
  "value":      5,                      // literal OR path-ref to compute
  "iterations": 1                       // repeat count (literal or path-ref)
}
```

- **`set`** replaces the value.
- **`modify`** adds (numeric) or concatenates (string) to the value.
- **`add`** appends to an array (keywords, allowed lists, etc.).
- **`remove`** deletes from an array or zeros a value.
- **`info`** runs no mutation — used for diagnostic rules.

`value` can be a path-ref array. The engine resolves the path before applying. This is how you write derived values: `value: ["{self}", "stats", "computedTotal", "value"]`.

### Execution order

Rules run in **`order` buckets ascending**. Within a bucket, action types run in this order:

1. `info` (no mutation)
2. `set` (replace)
3. `modify` (mutate)
4. `remove`
5. `add`

Within a type, document order. Default `order` is `0`.

This is your most powerful structuring tool. Rules at order 100 can compute intermediate values; rules at order 200 can read those values. See `RULE_PATTERNS.md` for canonical staging patterns.

### failState

What happens if the evals don't pass:

- **`pass`** — silent; no errors, just skip the actions
- **`warning`** — yellow flag on the asset
- **`error`** — red flag; roster is invalid
- **`disable`** — error + the asset is disabled
- **`hide`** — error + the asset is hidden

The rule's name appears as the message text.

### Equation operators (the only arithmetic)

The engine supports six binary operations on eval results:

- `T+O`, `T-O`, `O-T` — addition / subtraction
- `T*O` — multiplication
- `T/O`, `O/T` — division

`T` = the value at the eval's path. `O` = the operand (`equation.value`, literal or path-ref). For multi-term expressions, chain evals: each eval's `float` result becomes a path-ref input to the next.

**No `Math.max`, `Math.min`, `Math.pow`, `floor`, `round`, `%` operators.** `max(0, x)` is implemented as a guard eval: `{ paths: [...x...], min: 0, actionable: true }` — the rule only fires when x ≥ 0. For mutually-exclusive piecewise (if-x-positive-then-A-else-B), use two rules with complementary guards.

## Templating

A class can declare `templateClass: "OtherClass"` to inherit. Inheritance is multi-level. The composition pipeline merges the chain into a flat resolved class.

```jsonc
{
  "Unit": { "stats": { "Move": { "value": 6 } } },
  "FastUnit": {
    "templateClass": "Unit",
    "stats": { "Move": { "value": 12 } }
  }
}
```

`removed`: explicit removals from the inherited chain. Use to "subtract" something a parent template added.

```jsonc
"NoMoveUnit": {
  "templateClass": "Unit",
  "removed": { "stats": { "Move": null } }
}
```

## What good rulebooks look like

A few patterns that show up in every shipped rulebook:

- **One root point budget on the Roster** as a tracked numeric stat — items contribute via rank `tracking` dicts.
- **Mutex** = a category class with `aspects.Unique: true`; only one item from that class per parent.
- **Faction/army filters** = roster-level rank stat, with rules that add the chosen value to `constraints.any`.
- **Detachments / formations** = catalog items selectable as roster traits, that themselves modify what other items are allowed.
- **Wargear options** = sub-classes allowed under units, often gated by parent unit's keywords.
- **Stat formulas** = chained evals reading parent stats via `{parent}` path-refs, committing via `modify` to a tracked-stat slot.

The patterns are documented in `RULE_PATTERNS.md` with concrete snippets.

## What rulebooks should *not* try to do

The rule engine is intentionally simple. Don't try to:

- Implement combat resolution (no dice rolls, no random)
- Maintain mutable state between rule executions outside of stat values
- Express recursive or self-referential formulas (Rosterizer composes once per change; no fixed-point iteration)
- Round numeric values (display them rounded via `format` if you can; otherwise accept the float)
- Define stats that compute from an unbounded number of children (use `tracked: true` for that)
- Reach across rosters (each roster is composed in isolation)

## Where to look next

- `RULE_PATTERNS.md` — concrete recipes for common needs
- `PATH_SYNTAX.md` — exact spelling of `{self}`, `{parent}`, `{roster}`, `{this}`, eval-result references
- `examples/landwar/` — full upstream-data-driven generator + validator
- `examples/bugWars/` — 40k-chain worked example (obfuscated)
- `examples/cyberHits/` — flat single-file worked example (obfuscated)

## Type reference

Canonical TypeScript types from the engine, preserved here as the authoritative source of truth for field names, allowed values, and defaults.

### Stat fields (`StatFormat`)

| Field | Type | Notes |
|---|---|---|
| `statType` | `numeric` \| `rank` \| `term` | Required |
| `value` | string \| number \| null | Current value; null = unset |
| `dynamic` | boolean | User can edit in roster |
| `format` | string | Display string; `{v}` = value, `{n}` = numeric, `{t}` = term, `{r}` = rank index, `{i}` = icons |
| `min` | number | Enforced lower bound |
| `max` | number | Enforced upper bound |
| `icons` | string[] | Icon names associated with this stat |
| `label` | string | Display name override (preserves internal name for tally/tracking) |
| `statOrder` | number | Sort order within group; ties broken alphabetically; null/undefined treated as 0 |
| `groupOrder` | number | Sort order of the group; negative = before asset name (always visible) |
| `group` | string | Visual grouping label |
| `text` | string | Text appended to parent asset |
| `visibility` | `normal` \| `always` \| `active` \| `hidden` | When the stat is shown |
| `increment` | `{ value: number }` | Step size for user editing |
| `tracked` | boolean | Auto-sums contributions from descendants |
| `ranks` | `{ [rank: string]: RankFormat }` | rank-type stats only |

### Rank fields (`RankFormat`)

| Field | Type | Notes |
|---|---|---|
| `order` | number | Sort order in the rank picker |
| `number` | number | Numeric value this rank represents |
| `term` | string | String value this rank represents |
| `icons` | string[] | Icons shown when this rank is selected |
| `traits` | `{ trait: string, path?: string[] }[]` | Assets added to parent when this rank is selected |
| `tracking` | `{ [statName: string]: number }` | Adds N to named tracked stat on ancestors when selected |
| `format` | string | Display string for this rank |
| `hotkey` | string | Keyboard shortcut for this rank in the picker |
| `text` | string | Text appended to parent asset when this rank is selected |
| `prepend` | boolean | Whether to prepend the previous rank's text |

### Rule fields (`RuleFormat`)

| Field | Type | Default | Notes |
|---|---|---|---|
| `evals` | `RuleEval[]` | `[]` | Conditions to evaluate |
| `actions` | `RuleAction[]` | — | Mutations to apply if evals pass |
| `evaluate` | `AND` \| `OR` \| `SUM` | `AND` | How to combine evals |
| `failState` | `pass` \| `warning` \| `error` \| `disable` \| `hide` \| `false` | `pass` | What happens if evals fail |
| `order` | number | `0` | Execution bucket; lower runs first |

### Eval fields (`RuleEval`)

| Field | Type | Notes |
|---|---|---|
| `paths` | `BranchingPath[]` | Paths to resolve; each is an array of string-or-string-array segments |
| `operator` | `AND` \| `OR` \| `SUM` | How to combine multiple paths |
| `value` | number \| boolean \| string \| path | Equality target |
| `min` | number \| path | Lower bound (inclusive) |
| `max` | number \| path | Upper bound (inclusive) |
| `contains` | boolean | Substring or element membership test |
| `not` | boolean | Invert the truthiness result |
| `actionable` | boolean | Whether this eval counts toward pass/fail and triggers actions |
| `equation` | `{ operator, value }` | Arithmetic transform applied before comparing; operators: `T/O`, `O/T`, `T*O`, `T+O`, `T-O`, `O-T` |
| `result` | object | Populated by engine: `float`, `integer`, `remainder`, `string`, `array`, `truthy` |

### Action fields (`RuleAction`)

| Field | Type | Notes |
|---|---|---|
| `actionType` | `set` \| `modify` \| `add` \| `remove` \| `null` | `set` = replace; `modify` = add/concatenate; `add` = append to array; `remove` = delete from array or zero value |
| `paths` | `BranchingPath[]` | Target paths |
| `value` | any \| path | Value to apply; path-refs are resolved before application |
| `iterations` | number \| path | How many times to apply the action |

### Rulebook top-level fields (`RulebookHistoryItem`)

| Field | Type | Notes |
|---|---|---|
| `name` | string | Display name |
| `revision` | string | Semver string, e.g. `"0.1.0"` |
| `game` | string | Game name |
| `genre` | string | e.g. `"sci-fi"`, `"fantasy"`, `"generic"` |
| `publisher` | string | |
| `url` | string | Canonical raw URL for this file |
| `notes` | string | Freeform notes |
| `wip` | boolean | Marks the rulebook as work-in-progress |
| `isModule` | boolean | If true, this rulebook is a dependency rather than a standalone game |
| `dependencies` | `{ slug, name, game, source }[]` | Other rulebooks this one depends on |
| `rulebook` | `{ assetTaxonomy, assetCatalog, gameModes?, theme? }` | The actual rulebook data |

## What this doc deliberately omits

- **The schema**: see `client/src/app/models/rulebook.schema.json` and `domain-primitives.model.ts` for type definitions. Write rulebooks against the docs here; trust the schema for validation.
- **The Stat Wizard / Rule Wizard UI**: most rulebook authors will never touch these. If you need them, they're documented in `_reference/client/src/app/data/help-content.ts`.
- **Auth, sharing, sync, dependencies**: orthogonal to rule authoring. The dependency mechanism (one rulebook importing another) is real but rare; cover it later if needed.
