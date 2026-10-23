# Phase 3 — Rules Authoring Prompt

Paste this prompt into a fresh Claude conversation. Attach the current `.rulebook` file (post Phase 2 import) and the CSV files whose `text` fields contain the rule quirks checklists. You don't need to pre-select which rules to work on — Claude will survey the outstanding work and propose batches.

---

You are adding rules to a Rosterizer rulebook. The skeleton and catalog already exist and import cleanly. Your job is to survey the outstanding rule quirks across all catalog items, group similar behaviors into batches, and implement them one batch at a time.

## Starting protocol

Before writing any rules:

1. **Read all `text` fields** in the rulebook's `assetCatalog` and extract every unchecked item from "Rule quirks to implement" checklists.
2. **Group them by structural similarity.** Examples of natural groups:
   - All units with "points scale by model count above minimum N at X pts/model"
   - All units with "sergeant/champion gets a wargear selection from a shared list"
   - All units with "squad-wide weapon selection where cost = rate × model count"
   - All units with a conditional visibility rule (show stat only when faction = X)
   - All units where a wargear option excludes another
3. **Report the batches** to the user before writing anything:

   > **Outstanding rule quirks — proposed batches:**
   >
   > **Batch A — Per-model scaling cost** (12 units): Tactical Squad, Veteran Squad, ...
   > **Batch B — Squad-wide weapon rate** (6 units): Tactical Support Squad, ...
   > **Batch C — Sergeant wargear selection** (8 units): ...
   > **Batch D — Complex / unusual** (3 units): [unit] — [one-line reason it needs individual attention]
   >
   > Confirm which batch(es) to start with, or redirect. Flag anything that looks like it will need 5+ rules to implement — those warrant a separate conversation.

4. Wait for user confirmation before implementing anything.

## Implementation protocol

For each batch:

1. **Describe the shared rule shape** in plain English — one sentence covering what all items in the batch have in common.
2. **Identify whether the rule belongs on the class or per-item.** If the rule shape is identical across all items, it goes on the class in `assetTaxonomy`. If items vary (different rates, different wargear lists), it goes on each catalog item separately but can still be written once and applied as a template.
3. **Write the rule(s)** for one representative item first.
4. **State the test case** for that item: given these input values, these stats should change to these values.
5. **Apply the same pattern** to the remaining items in the batch, noting any variations.
6. **After the batch**, report what was implemented and what checklist items are now checked off.
7. **Pause** — wait for the user to test before starting the next batch. If testing reveals a problem, fix it before moving on.

Do not implement rules from two different batches in the same response.

## Bailout conditions

Stop and ask for user input if:
- A quirk requires more than ~5 rules to implement
- A quirk interacts with rules from a different batch in a non-obvious way
- A quirk requires a stat that doesn't exist in the taxonomy (would need a Phase 1 revision)
- You aren't confident the engine supports what the quirk requires

When you bail out, describe specifically what the problem is and what decision the user needs to make.

## Rule placement

- Rules that are **identical across all items of a class** → `assetTaxonomy["ClassName"].rules`
- Rules that vary per item (different values, different wargear lists) → `assetCatalog["ClassName§ItemName"].rules`
- Rules that **modify what the roster allows** → `assetCatalog["Roster§Roster"].rules`
- When in doubt, prefer the catalog item — it's easier to promote to the taxonomy later than to unpick a class-level rule that's wrong for some items

## Rule ordering

- `order: 1–49` — setup: visibility resets, faction gates
- `order: 50–99` — constraint/allow mutations
- `order: 100–149` — cost computation: base costs, per-model costs, per-model rates
- `order: 150–199` — cost aggregation: summing sub-totals
- `order: 200+` — derived stats that depend on finalized costs

Always use `failState: "pass"` for mutation rules. Only use `"warning"` or `"error"` for validation rules (no actions).

## The only arithmetic available

The engine has no `if/else`, no `Math.max/min`, no `%`. Work within these constraints:

- **Multiplication**: `equation: { "operator": "T*O", "value": N }`
- **Division**: `equation: { "operator": "T/O", "value": N }`
- **Addition/subtraction**: chain evals, commit with `modify`
- **Floor**: use `result.integer` instead of `result.float`
- **Conditional**: two rules with complementary `min`/`max` guards on the actionable eval
- **Piecewise minimum (max(0, x))**: guard with `min: 0` on the actionable eval — the rule only fires when x ≥ 0
- **Sum of multiple values**: `operator: "SUM"` across multiple paths in one eval

Chain arithmetic across evals within a rule using `["{this}", "evals", "N", "result", "float"]`. Prefer staging through a named `_scratch` stat when the chain gets longer than 3 steps.

## Path syntax reference

```jsonc
["{self}", "stats", "StatName", "value"]       // this asset's stat
["{parent}", "stats", "StatName", "value"]      // parent asset's stat
["{roster}", "stats", "StatName", "value"]      // roster root stat
["{this}", "evals", "0", "result", "float"]     // eval result within this rule
["{self}", "tally", "ClassName"]                // count of descendant class
["{self}", "tracked", "StatName"]               // sum of tracked stat from descendants
["{self}", "constraints", "any"]                // constraint list
["{self}", "allowed", "classifications"]        // allowed class list
```

## Common rule shapes

### Per-model cost (above minimum)

"Units start at N models (base cost). Each additional model costs X points."

```jsonc
"additionalModelCost": {
  "evals": [
    {
      "actionable": false,
      "equation": { "operator": "T-O", "value": MIN_MODELS },
      "operator": "AND",
      "paths": [["{self}", "stats", "Models", "value"]]
    },
    {
      "actionable": false,
      "equation": { "operator": "T*O", "value": COST_PER_MODEL },
      "operator": "AND",
      "paths": [["{this}", "evals", "0", "result", "integer"]]
    },
    {
      "actionable": true,
      "min": 1,
      "operator": "AND",
      "paths": [["{this}", "evals", "1", "result", "integer"]]
    }
  ],
  "actions": [{
    "actionType": "modify",
    "iterations": 1,
    "paths": [["{self}", "stats", "Points", "value"]],
    "value": ["{this}", "evals", "1", "result", "integer"]
  }],
  "evaluate": "AND",
  "failState": "pass",
  "order": 100
}
```

### Visibility gate + reset

"Show stat X only when faction Y is selected. Reset it when another faction is chosen."

```jsonc
"hideStatWhenNotFaction": {
  "actions": [
    {
      "actionType": "set",
      "paths": [["{self}", "stats", "StatName", "value"]],
      "value": "-"
    },
    {
      "actionType": "set",
      "paths": [["{self}", "stats", "StatName", "visibility"]],
      "value": "hidden"
    }
  ],
  "evals": [{
    "actionable": true,
    "not": true,
    "operator": "AND",
    "paths": [["{self}", "stats", "Faction", "value"]],
    "value": "FactionName"
  }],
  "evaluate": "AND",
  "failState": "pass"
}
```

### Rank-based option that adds a trait

Use rank `tracking` to add points and a `traits` array to attach the item. No rule needed — this is declarative:

```jsonc
"StatName": {
  "statType": "rank",
  "dynamic": true,
  "value": "-",
  "visibility": "active",
  "ranks": {
    "-":        { "order": 0, "tracking": {} },
    "Option A": {
      "order": 1,
      "tracking": { "Points": 10 },
      "traits": [{ "trait": "WeaponClass§Option A" }]
    }
  }
}
```

### Squad-wide weapon cost (rate × model count)

When every model in a squad gets the same upgrade and you store a per-model rate in a hidden stat:

```jsonc
"squadWeaponCost": {
  "evals": [
    {
      "actionable": false,
      "equation": { "operator": "T*O", "value": ["{self}", "stats", "Models", "value"] },
      "operator": "AND",
      "paths": [["{self}", "stats", "_weaponRatePerModel", "value"]]
    },
    {
      "actionable": true,
      "min": 1,
      "operator": "AND",
      "paths": [["{this}", "evals", "0", "result", "integer"]]
    }
  ],
  "actions": [{
    "actionType": "modify",
    "paths": [["{self}", "stats", "Points", "value"]],
    "value": ["{this}", "evals", "0", "result", "integer"]
  }],
  "evaluate": "AND",
  "failState": "pass",
  "order": 101
}
```

## Hard constraints

- Do not modify rules outside the current batch. If you spot a problem elsewhere, flag it and wait for permission.
- Do not reference `{this}` results from a *previous rule* via path — stage intermediate values through a named `_scratch` stat instead.
- Do not use `order: 0` for mutation rules — reserve 0 for engine defaults.
- Do not add rules without a test case.

---

## Context (fill this in before pasting the prompt)

```
Game name:
Current rulebook: [attach file]
CSVs with rule quirks text fields: [attach files or paste text fields inline]
Any rules already implemented that Claude should be aware of: [optional]
```
