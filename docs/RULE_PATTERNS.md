# Rule Patterns

Cookbook of common rulebook idioms. Every recipe here is taken from shipped rulebooks (40k10e, Reign-in-Hell, Fray, LANDWAR) — they're proven to work, not invented.

For underlying syntax, see `RULEBOOK_AUTHORING.md` and `PATH_SYNTAX.md`.

## 1. Points budget on the roster

Most rulebooks need a single "Points" total at the top of the roster, summed from descendants. Two halves: the tracked stat on the roster, and the contribution dictionaries on items.

**Roster (or whatever class is the root):**

```jsonc
"Roster": {
  "stats": {
    "Points": {
      "statType": "numeric",
      "tracked": true,
      "value": 0,
      "visibility": "always",
      "groupOrder": -1,
      "label": "Points"
    }
  }
}
```

**Items contribute via rank tracking:**

```jsonc
"Unit§Trooper": {
  "stats": {
    "Squad Size": {
      "statType": "rank",
      "value": "5",
      "ranks": {
        "5":  { "order": 0, "tracking": { "Points": 50 } },
        "10": { "order": 1, "tracking": { "Points": 95 } },
        "15": { "order": 2, "tracking": { "Points": 135 } }
      }
    }
  }
}
```

When the user picks "10", `Points: 95` bubbles up to the roster's tracked Points stat.

**Or items contribute via their own tracked stat:**

```jsonc
"Unit": {
  "stats": {
    "Points": {
      "statType": "numeric",
      "tracked": true,
      "value": 0
    }
  }
}

"Unit§Trooper": {
  "stats": {
    "Points": { "value": 50 }
  }
}
```

A descendant's `Points: 50` bubbles to the parent's tracked Points if the parent has a stat by the same name.

**Sum-of-multiple-stats** (LANDWAR-style derived points):

```jsonc
"Unit": {
  "stats": {
    "Move":   { "statType": "numeric", "value": 0, "dynamic": true },
    "Armor":  { "statType": "numeric", "value": 0, "dynamic": true },
    "Points": { "statType": "numeric", "value": 0, "tracked": true }
  },
  "rules": {
    "computePoints": {
      "evals": [
        // Move/2
        {
          "paths": [["{self}", "stats", "Move", "value"]],
          "equation": { "operator": "T/O", "value": 2 },
          "actionable": false
        },
        // Armor*1.5
        {
          "paths": [["{self}", "stats", "Armor", "value"]],
          "equation": { "operator": "T*O", "value": 1.5 },
          "actionable": false
        },
        // Sum the two
        {
          "paths": [
            ["{this}", "evals", "0", "result", "float"],
            ["{this}", "evals", "1", "result", "float"]
          ],
          "operator": "SUM",
          "actionable": false
        }
      ],
      "actions": [{
        "paths": [["{self}", "stats", "Points", "value"]],
        "actionType": "modify",
        "value": ["{this}", "evals", "2", "result", "float"]
      }],
      "order": 100
    }
  }
}
```

## 2. Mutex via `Unique` aspect

When a unit can have at most one of something (one Captain, one Warlord trait), use a category class with `Unique: true`. Cleaner than per-item disallow rules.

```jsonc
"WarlordTrait": {
  "aspects": {
    "Type": "add-on",
    "Lock Qty": true,
    "Unique": true        // ← max one per parent
  }
}
```

Items in `WarlordTrait§*` are then mutually exclusive automatically.

## 3. Gating allowed classes by a roster-level rank stat

Roster has a "Detachment" or "Tier" rank stat that opens or closes which sub-classes can be added.

```jsonc
"Roster": {
  "allowed": {
    "classifications": ["Squad—Basic"]      // default: only basic
  },
  "stats": {
    "Tier": {
      "statType": "rank",
      "value": "Basic",
      "ranks": {
        "Basic":        { "order": 0 },
        "Intermediate": { "order": 1 },
        "Advanced":     { "order": 2 }
      }
    }
  },
  "rules": {
    "allow_intermediate": {
      "evals": [{
        "paths": [["{self}", "stats", "Tier", "value"]],
        "value": "Intermediate",
        "actionable": true
      }],
      "actions": [{
        "paths": [["{self}", "allowed", "classifications"]],
        "actionType": "add",
        "value": "Squad—Intermediate"
      }],
      "order": 1
    },
    "allow_advanced": {
      "evals": [{
        "paths": [["{self}", "stats", "Tier", "value"]],
        "value": "Advanced",
        "actionable": true
      }],
      "actions": [{
        "paths": [["{self}", "allowed", "classifications"]],
        "actionType": "add",
        "value": "Squad—Advanced"
      }],
      "order": 1
    }
  }
}
```

If you also want Advanced to inherit Intermediate access, add a third rule that adds `Squad—Intermediate` when Tier=Advanced.

In practice this lives on the `Roster§Roster` catalog item rather than the `Roster` class. `{self}` and `{roster}` both resolve to the roster node when the rule is attached there; shipped rulebooks default to `{self}`.

## 4. Faction filter via constraint path-ref

Roster picks a Faction; only items keyworded with that Faction are allowed.

```jsonc
"Roster": {
  "stats": {
    "Faction": {
      "statType": "rank",
      "value": "Steel Lance",
      "ranks": {
        "Steel Lance":   { "order": 0 },
        "Crimson Order": { "order": 1 }
      }
    }
  },
  "rules": {
    "factionConstraint": {
      "evals": [],
      "actions": [{
        "paths": [["{self}", "constraints", "any"]],
        "actionType": "add",
        "value": ["{self}", "stats", "Faction", "value"]   // path-ref
      }],
      "order": 1
    }
  }
}
```

Only items with the chosen faction in their `keywords.Faction` will pass `constraints.any`. One rule, no per-faction switch. (Vanilla items with no Faction keyword always pass — that's by design.)

## 5. Conditional contribution (only when X is true)

A rule that fires only when a stat has a particular value.

```jsonc
{
  "evals": [{
    "paths": [["{roster}", "stats", "Game Size", "value"]],
    "value": "Tournament",
    "actionable": true
  }],
  "actions": [{
    "paths": [["{self}", "stats", "Points", "value"]],
    "actionType": "modify",
    "value": -10                         // tournament discount
  }],
  "failState": "pass"
}
```

`failState: "pass"` means "do nothing if the eval fails" — silent skip.

## 6. Validator that errors when something's wrong

A rule whose only job is to fire an error on invalid configurations. No actions; the rule's name is the error message.

```jsonc
"Squad must have at least one Sergeant": {
  "evals": [{
    "paths": [["{self}", "tally", "Sergeant"]],
    "min": 1,
    "actionable": true
  }],
  "evaluate": "AND",
  "failState": "error"
}
```

## 7. Mutually exclusive piecewise (if x ≥ 0 then A else B)

The engine has no `if/else`. Express as two rules with complementary actionable guards.

```jsonc
// Rule A: fires when computed value >= 5
"computePart_normal": {
  "evals": [
    /* ... compute the value into evals[N] ... */,
    {
      "paths": [["{this}", "evals", "N", "result", "float"]],
      "min": 5,
      "actionable": true
    }
  ],
  "actions": [{ /* commit the computed value */ }],
  "order": 100
}

// Rule B: fires when computed value < 5 — commits a constant 5 instead
"computePart_floor": {
  "evals": [
    /* ... compute the value into evals[N] ... */,
    {
      "paths": [["{this}", "evals", "N", "result", "float"]],
      "max": 4.999,
      "actionable": true
    }
  ],
  "actions": [{
    "paths": [["{self}", "stats", "x", "value"]],
    "actionType": "modify",
    "value": 5
  }],
  "order": 100
}
```

LANDWAR's `STBLFR` TAG (`max(5, move²/size)`) uses exactly this shape.

## 8. Excludes / mutex across categories

When two items in *different* categories must be mutex (e.g. you can't take both Heavy Armor and Cloak), each item carries an `Excludes` keyword listing what it disallows, and a rule on it adds those to the parent's `disallowed.items`.

```jsonc
"Ability§Cloaking Systems": {
  "keywords": {
    "Excludes": ["HeavyArmor"]
  },
  "rules": {
    "enforceExcl": {
      "evals": [],
      "actions": [{
        "paths": [["{parent}", "disallowed", "items"]],
        "actionType": "add",
        "value": "Armor§Heavy Armor"
      }],
      "order": 50
    }
  }
}
```

## 9. Trait that adds itself to the roster on selection

A rank stat with a `traits` field that fires on selection.

```jsonc
"Detachment": {
  "statType": "rank",
  "value": "Spearhead",
  "ranks": {
    "Spearhead": {
      "order": 1,
      "traits": [
        { "trait": "Detachment§Spearhead" }   // adds the named trait when this rank is chosen
      ]
    },
    "Anvil": {
      "order": 2,
      "traits": [
        { "trait": "Detachment§Anvil" }
      ]
    }
  }
}
```

The trait shows up in the roster as a sub-asset of whatever holds the rank stat.

## 10. Sub-class swapping via item set

When picking one item should swap out another (e.g. picking a Champion replaces the default Sergeant), `actionType: "set"` on `{self}.item`:

```jsonc
"Trooper§Champion": {
  "rules": {
    "replacesSergeant": {
      "evals": [],
      "actions": [{
        "paths": [["{self}", "item"]],
        "actionType": "set",
        "value": "Trooper§Sergeant"
      }]
    }
  }
}
```

This swaps the asset in place. **Note**: rule actions on the *old* asset are lost.

## 11. Computing a per-asset cost from upstream stats

LANDWAR-style derived points: a TAG item reads its parent unit's stats, computes a contribution, commits it to a tracked stat.

```jsonc
"Targeting§Advanced Gun Sights": {
  "rules": {
    "computeCost": {
      "evals": [
        // Move/4
        {
          "paths": [["{parent}", "stats", "Move", "value"]],
          "equation": { "operator": "T/O", "value": 4 },
          "actionable": false
        },
        // dmgRange/2
        {
          "paths": [["{parent}", "stats", "dmgRange", "value"]],
          "equation": { "operator": "T/O", "value": 2 },
          "actionable": false
        },
        // Sum the two
        {
          "paths": [
            ["{this}", "evals", "0", "result", "float"],
            ["{this}", "evals", "1", "result", "float"]
          ],
          "operator": "SUM",
          "actionable": false
        }
      ],
      "actions": [{
        "paths": [["{self}", "stats", "tagTotal", "value"]],
        "actionType": "modify",
        "value": ["{this}", "evals", "2", "result", "float"]
      }],
      "order": 110
    }
  }
}
```

The `tagTotal` stat on the TAG must match a tracked `tagTotal` stat on the parent Unit class for the value to bubble up.

## 12. Total from sub-totals

The classic Base + Add-ons = Total computation. Both contributions are tracked stats on different parts of the asset; a final rule sums them.

```jsonc
"Unit": {
  "stats": {
    "basePoints":    { "statType": "numeric", "tracked": true, "value": 0 },
    "addOnPoints":   { "statType": "numeric", "tracked": true, "value": 0 },
    "totalPoints":   { "statType": "numeric", "tracked": true, "value": 0 }
  },
  "rules": {
    "totalAdd_base": {
      "actions": [{
        "paths": [["{self}", "stats", "totalPoints", "value"]],
        "actionType": "modify",
        "value": ["{self}", "stats", "basePoints", "value"]
      }],
      "order": 200
    },
    "totalAdd_addons": {
      "actions": [{
        "paths": [["{self}", "stats", "totalPoints", "value"]],
        "actionType": "modify",
        "value": ["{self}", "stats", "addOnPoints", "value"]
      }],
      "order": 200
    }
  }
}
```

## What's missing from this cookbook

Patterns that don't have a clean idiom yet:

- **Conditional sub-totals across heterogeneous children** — e.g. "Sum points of all Wargear items, but cap at 50% of the unit's base." The cap requires a piecewise rule.
- **Pair-bonded items** — "If both A and B are present, add a bonus." Requires reading two tally counts and gating on both > 0.
- **Per-instance modifiers** — Rosterizer applies rules per-asset; "this rule fires once per X in the roster" is awkward.

If you encounter one of these, document the workaround you land on — it'll become a future entry here.
