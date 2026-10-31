# Path Syntax

How rules address values. Paths are arrays of segments; each segment is a string or an array of strings (branching).

## Roots

Every path starts with a root token:

| Token | Meaning |
|---|---|
| `{self}` | the asset the rule is attached to |
| `{parent}` | the asset's parent (chain `{parent}, {parent}` for grandparent) |
| `{roster}` | the roster root |
| `{this}` | the current rule itself; used to read prior eval results |

## Common targets

After the root, the next segments traverse the asset shape. The frequently-used patterns:

```jsonc
// A stat's value
["{self}", "stats", "Move", "value"]

// A rule's eval result (within the same rule)
["{this}", "evals", "2", "result", "float"]

// A keyword category's contents
["{self}", "keywords", "Faction"]

// The asset's allowed classifications
["{self}", "allowed", "classifications"]

// The asset's constraints
["{self}", "constraints", "any"]

// Tally (count of descendants by class)
["{roster}", "tally", "Trooper"]

// Tracked stat sums (numeric bubbled-up totals)
["{self}", "tracked", "Points"]

// An aspect
["{self}", "aspects", "Visibility"]

// The asset's designation (display name)
["{self}", "designation"]
```

## Branching

A segment can be an array of strings — the path resolves to *each* branch. Useful with `SUM` to aggregate, or `add`/`remove` actions to fan out:

```jsonc
// Read both Move and Speed values; result is two paths
["{self}", "stats", ["Move", "Speed"], "value"]

// Add a value to multiple keyword categories
{
  "actionType": "add",
  "paths": [["{self}", "keywords", ["Faction", "Allegiance"]]],
  "value": "Steel Lance"
}
```

## Eval result references (`{this}`)

The most powerful pattern. Any rule's eval stores its computed result in `result.<field>`, and subsequent evals can read it. This is how you chain arithmetic operations.

```jsonc
{
  "evals": [
    // Eval 0: T*O — multiply Move by 2
    {
      "paths": [["{self}", "stats", "Move", "value"]],
      "equation": { "operator": "T*O", "value": 2 },
      "actionable": false
    },
    // Eval 1: T+O — read eval 0's result, add Size to it
    {
      "paths": [["{this}", "evals", "0", "result", "float"]],
      "equation": {
        "operator": "T+O",
        "value": ["{self}", "stats", "Size", "value"]
      },
      "actionable": false
    }
  ],
  "actions": [
    // Write the chained result into Points
    {
      "paths": [["{self}", "stats", "Points", "value"]],
      "actionType": "modify",
      "value": ["{this}", "evals", "1", "result", "float"]
    }
  ]
}
```

### Result fields

| Field | Type | What it holds |
|---|---|---|
| `float` | number | numeric result (most common for arithmetic) |
| `integer` | number | `Math.floor(float)` |
| `remainder` | number | non-integer fractional part |
| `string` | string | string result (for term-typed operations) |
| `array` | string[] | array result |
| `truthy` | boolean | did the eval pass? |

### Cross-rule references

A rule can also read another rule's eval results — same syntax, different root. Useful when rule A computes something at order 100 and rule B at order 200 needs the value:

```jsonc
["{this}", "rules", "computePoints", "evals", "1", "result", "float"]
```

But: prefer staging via stat values rather than cross-rule eval refs. Cleaner, and survives rule reordering.

## Path-ref values in actions

Action `value` can be a path. The engine resolves the path before applying the action.

```jsonc
{
  "actionType": "modify",
  "paths": [["{self}", "stats", "Total", "value"]],
  "value": ["{self}", "stats", "Subtotal", "value"]   // adds Subtotal to Total
}
```

Path-refs work in `equation.value` too:

```jsonc
{
  "equation": {
    "operator": "T*O",
    "value": ["{roster}", "stats", "Multiplier", "value"]
  }
}
```

## Iterations as a path

`action.iterations` can be a path-ref to dynamically vary how many times the action runs:

```jsonc
{
  "actionType": "add",
  "paths": [["{self}", "traits"]],
  "value": "Trait§Reroll Token",
  "iterations": ["{self}", "stats", "TokenCount", "value"]
}
```

## Reading shipped rulebooks

If you need to confirm a path shape, the most reliable reference is a real rulebook. The 40k10e and Reign-in-Hell rulebooks (in `RosterizerData/`) and the v1 chess/fray fixtures (in `client/src/assets/fixtures/rulebooks/`) cover most patterns. Grep them for the segment you're unsure about.

## What doesn't work

- **Wildcards** (`*`, `**`) — not supported. Use branching arrays for known sets.
- **Computed indices** — can't write `evals[N]` where N is itself a path. Eval indices are literal strings (`"0"`, `"1"`, etc.).
- **Reaching outside the roster** — paths terminate at `{roster}`. There's no global state.
- **Rule-name path segments with spaces** — paths use literal rule names; if you name a rule `"my rule"` you have to spell that with the space. Avoid spaces in rule names.

## Writable path reference

Every path segment that can be targeted by a rule action, derived from the engine's path option tree. `writable` shows which `actionType` values are valid at that node.

| Path | Type | Writable |
|---|---|---|
| `quantity` | number | `set`, `modify` |
| `designation` | string | `set`, `modify` |
| `item` | string | `set` |
| `text` | string | `set`, `modify` |
| `traits` | string/Asset array | `add`, `remove` |
| `included` | string array | `remove` |
| `assets` | string array | `remove` |
| `keywords.[category]` | string array | `add`, `remove` |
| `stats.[name].value` | string/number | `set`, `modify` |
| `stats.[name].min` | number | `set`, `modify` |
| `stats.[name].max` | number | `set`, `modify` |
| `stats.[name].visibility` | `normal`/`always`/`active`/`hidden` | `set` |
| `stats.[name].group` | string | `set`, `modify` |
| `stats.[name].label` | string | `set`, `modify` |
| `stats.[name].format` | string | `set`, `modify` |
| `stats.[name].text` | string | `set`, `modify` |
| `stats.[name].dynamic` | boolean | `set` |
| `stats.[name].tracked` | boolean | `set` |
| `stats.[name].increment` | number | `set`, `modify` |
| `stats.[name].statOrder` | number | `set`, `modify` |
| `stats.[name].groupOrder` | number | `set`, `modify` |
| `stats.[name].ranks` | object | `remove` |
| `stats.[name].processed.numeric.current` | number | `set`, `modify` |
| `stats.[name].processed.term.current` | string | `set`, `modify` |
| `allowed.[classifications\|items]` | string array | `add`, `remove` |
| `disallowed.[classifications\|items]` | string array | `add`, `remove` |
| `constraints.[any\|all\|none\|not]` | string array | `add`, `remove` |
| `aspects.Type` | `conceptual`/`game piece`/`add-on` | `set` |
| `aspects.Visibility` | `always`/`edited`/`active` | `set` |
| `aspects.[Rename\|Describe\|Lock Qty\|Unique\|Collapse\|Group Traits\|Order Traits A–Z\|Group Includes\|Order Includes A–Z]` | boolean | `set` |
| `tally.[name]` | number | `set`, `modify` |
| `tracked.[name]` | number | `set`, `modify` |

Read-only (can appear in eval `paths` but not action `paths`):

| Path | Notes |
|---|---|
| `classification` | The class this asset belongs to |
| `classIdentity` | The class or its template if no template exists |
| `templateClass` | The template class |
| `lineage` | Array of all ancestor classes |
| `division` | `traits` or `included` |
| `index` | Position among siblings |
| `collapsed` | Whether the asset is collapsed in the UI |
| `custom` | Whether the asset was user-defined |
