# Tools

Shared scripts for working with Rosterizer rulebooks.

## What's here

### `rz_simulate.py`

A minimal Python port of the Rosterizer rule engine. Importable module — `Asset`, `instantiate_item`, `run_rule`, `run_all_rules`, plus the path/eval/action primitives.

**Status: usable engine core, intentionally narrow.** The shape is deliberate: build asset trees yourself, hand them to the runner. This is a template — generators copy/extend the imports and bolt on a per-game tree-builder.

What's implemented (see the module docstring for the full surface):
- Path roots `{self}` `{parent}` `{roster}` `{this}`
- Path tails: `stats.<name>.value`, `evals.N.result.<field>`, `keywords.<cat>`, `tracked.<name>`, `tally.<name>`, `aspects.<name>`, `allowed.<key>`, `constraints.<key>`, `designation`, `item`, `text`
- Evals: AND/OR/SUM, equation operators, min/max/value/contains/not/actionable
- Actions: set/modify/add/remove/info, literal or path-ref values, iterations
- Rule ordering: `order` ascending, then ACTION_TYPE_ORDER (info → set → modify → remove → add), then document order
- Class-level stat merge in `instantiate_item` (one level — no `templateClass` chain walk yet)

What's NOT yet implemented (extend as needed):
- `templateClass` inheritance chain flattening (multi-level)
- `included` / `traits` hydration from ranked-stat selections
- Branched path segments (array of strings inside a path)
- Cross-rule eval references (`{this}.rules.<name>.evals.N.result.<field>`)
- Keyword-driven constraint resolution against a child asset
- `tally` / `tracked` auto-population from descendant walks (set them yourself if you need them)

### Smoke test

```bash
python3 tools/rz_simulate.py path/to/rulebook.json
# prints: rulebook name, class count, item count
```

For real use:

```python
import json
import sys; sys.path.insert(0, "tools")
import rz_simulate as rz

rb = json.loads(open("examples/bugWars/bugwars_core.rulebook").read())

unit = rz.instantiate_item(rb, "Unit§SomeUnit", parent=None)
roster = rz.Asset(classification="Roster", designation="Roster")
roster.add_child(unit)

# Run the Unit class's rules against this asset
unit_rules = rz.get_class_rules(rb, "Unit")
rz.run_all_rules(unit_rules, ctx={"self": unit})

# Inspect the result
print(unit.stats)
```

### `relink_readmes.py`

Moves every README link in the data org from the retired `RosterizerTestData` org to `RosterizerData`, one commit per repo, through the GitHub CLI's login (which needs write access to the org's repos for `--apply`). Without `--apply` it only reports each link and whether the rewritten target exists; links mangled on purpose as dev notes answer 404 either way and are swapped all the same.

```bash
python3 tools/relink_readmes.py          # report
python3 tools/relink_readmes.py --apply  # commit
```

## Tools we need but haven't built

### `rz_lint.py`

Diagnostic for half-finished rulebooks. Walks taxonomy + catalog, reports:

- Catalog items whose class doesn't exist in the taxonomy
- Stats referenced by rules that don't exist on the asset or any ancestor
- Path-refs in actions that don't resolve
- Rules with empty `actions` and `failState: "pass"` (dead code)
- Rules whose `equation.value` references a stat that doesn't exist
- Rank `tracking` keys that don't match any tracked stat on a parent
- Items with `templateClass` pointing to nothing
- Cycles in `templateClass` chains

Most of this is structural. Most useful after the conceptual structure of a rulebook is settled — it's a finishing pass, not a discovery tool.

### `rz_diff.py`

Compare two rulebooks structurally. Useful when:

- A rulebook revision swaps something subtle and you want a changelog
- Porting between editions and you want to confirm equivalence

Skeleton: walk both rulebooks' taxonomy + catalog, report added/removed/changed items, deep-diff each item's stats/rules/aspects.

### BattleScribe ingestion *(deferred)*

`battlescribe-to-rosterizer/` (sibling repo) handles this. Predates the toolkit; some of NewRecruit's data extensions postdate it. Revisit when the toolkit shape settles.
