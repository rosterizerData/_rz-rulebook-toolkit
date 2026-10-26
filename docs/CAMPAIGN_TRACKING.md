# Campaign tracking (Crusade-style mini-games)

Patterns and engine facts from building the Warhammer 40k 11e Crusade mini-games (October 2026). The worked code is
`Warhammer40k11e/script_archive/rulebook_scripts/crusade_lib.py` with one spec per faction in `crusade_specs/`; the
headless scenario helper is `rz_headless/scen.py`. Read this with [RULE_PATTERNS.md](RULE_PATTERNS.md) and
[PATH_SYNTAX.md](PATH_SYNTAX.md).

A campaign mini-game is a ledger the player keeps between battles: counters, a few state machines, and lists of
honours that are only reachable when the ledger says so. The engine never rolls dice for the player. Everything below
hangs off a mode stat (`Play = Narrative`) and disappears in the normal mode.

## The eight shapes

| | Shape | Mechanics |
|---|---|---|
| P1 | **Tracker trait** | A roster rule adds `<Class>§<Item>` to the roster's `traits` when the mode stat says so. The tracker class has `templateClass: ""`, `aspects.Visibility: always`, its counters as class stats. The adding rule needs an explicit low `order` (see facts). |
| P2 | **Counter with derived level** | A numeric stat with `dynamic: true` and `increment` for the player; rules read it and `set`/`modify` a derived stat, add an `Ability§` trait per band, or `modify {roster} tracked <key>` so other assets can gate on the level. |
| P3 | **Currency** | An "earned" counter; a cost stat on the purchasable class (tracked so it sums upward); a rule that errors when spent exceeds earned. |
| P4 | **Role flag** | A `-`/`✓` rank on eligible units with `tracking: {<role>: 1}`; the roster errors on `tracked.<role> > 1`; rules on the unit show extra counters and grant allowances while ticked. |
| P5 | **Tag-gated lists** | Honours carry `keywords.Tags`; unit rules add the matching tag to `constraints.any` from keywords, ranks or tracker state. No tags on the child means no constraint. |
| P6 | **Fixed child sets** | Small structures (three threats, twelve districts, four gods) as child trait assets of the tracker, each with its own class and stats; the tracker item lists them in `assets.traits`. |
| P7 | **Units outside the economy** | A keyword-gated rule hides Experience and sets the honour cap to 0 for summoned or expendable units. |
| P8 | **Mode-specific pick-lists** | Faction Agendas appended to a core rank list through a per-book taxonomy override of the class's stat ranks (rank lists merge by union across the chain). |

## Engine facts that bit

- **Rules of a rule-added asset run only when their `order` is greater than the adding rule's.** `addRules` treats
  anything at or below the current order as stale ("added too late"), and an unordered adder (ORDER_LAST) makes every
  rule of the added asset stale, including unordered ones. Add trackers at `order: 0` (or 1, like the core's Campaign)
  and keep their rules at order ≥ 1 or unordered.
- **`set` and `modify` on a stat land in `processed.*.current`; `value` keeps the stored number.** Read `current` in
  tests; a `value` that never changes is not a bug.
- **`failState: 'error'` fires when the evals are NOT met.** A "this situation is illegal" rule is written as the legal
  condition (or as the negation under `evaluate: OR`).
- **A child's Keywords count as Tags for constraints.** `isAllowedUnder` flattens every keyword array on the child and
  checks the union against `constraints.any/all/none/not`; a child with no keywords at all is exempt. A grouping label
  in `Keywords` therefore blocks the item unless the parent's `any` also contains it or a granted Tag is present.
- **`aspects.Unique` is per parent**, not per roster. Roster-wide uniqueness is a roster rule on the roster's `tally`
  of the item's designation (`unique_in_roster`).
- **An allowance on a classification admits every class templated on it.** Never allow a parent class (Battle
  Honour, Crusade Honour, Battle Trait, Crusade Relic) when a family must stay gated; give each family its own class
  templated on the parent and its own allowance rule.
- **A ✓ flag with `tracked: true` and `tracking: {<same name>: 1}` counts twice.** Use the tracking key and leave
  `tracked` off, or track under a different key.
- **Keywords added by a rule are invisible to other assets' keyword gates**, but visible to the same asset's rules and to
  tallies. Gate across assets on stats, `tracked`, or designations.
- **Rank numbers**: a rank only has a numeric value when it carries `number`; a `SUM` eval over
  `stats.<flag>.processed.numeric.current` counts ticks only if ✓ has `number: 1`.
- **Path-form operands**: `min`, `max`, `value` and `equation.value` may be paths, and an eval's `equation` is applied
  before the predicate. "A has strictly more than B" is `paths: [A], equation: {T-O, 1}, min: [B]`. Four such rules
  per item derive a ranking (the Daemons' Great Game positions).
- **Stat `tracked`** bubbles the stat's number under its own name to every ancestor's `tracked`; a child asset's
  tracked `Crusade Pts` therefore adds to the roster's. That is how a tracker contributes points.
- **Validations on stored unit stats need the mode guard**: stat values survive a switch back to the normal mode, so a
  rule that errors on them must also pass when `Play != Narrative`.

- **A promotion economy is reusable.** The Space Marines `Promotion` class (a cost stat, a `Selection` rank whose term
  is the ability or the replacement unit, a roster "earned minus spent" rule) served Dark Angels, Blood Angels and
  Space Wolves unchanged; a new currency only needs its own counter.
- **Tallies count children's keywords and classes**, so "one per suit location" or "one of each type" caps are
  `tally.<keyword> ≤ 1` rules on the parent.
- **Re-runs must replace, not merge, keyword lists** when a spec re-keys old items; a merge keeps the old Tags and
  the fix never lands.
- **Supplement pages repeat headings** (each chapter has its own Agendas / Requisitions / Crusade Badges); address
  blocks by occurrence number, never by title alone.

## Working method

1. Read the ruleset once and write down the ledger: counters, states, lists, gates, currency. Decide which random
   tables persist (pick-lists) and which are one-offs (text).
2. Write a spec: generic lists first (agendas, requisitions, badges parsed from the source text), then the bespoke
   tracker, then the honour families (own classes), then the gates.
3. Dry-run, apply, and prove it in the headless runner with four rosters: the tracker in the game mode, the gates
   accepting the right units and refusing the wrong ones, the caps, and the normal mode showing none of it.
4. Run the merge checker and the all-units regression before committing.

## Source handling

- A list builder's data (BSData) carries the items but not the economies, de-duplicates by name (tiered rewards with
  repeated tier names collapse), and files shared content under one library. Expect to re-key.
- Rules pages encode some table values as images (icons for points, dice faces). The raw HTML keeps the image names
  (`QT_3.png`, `d6.png`); decode from there before giving up.
- Keep a dated copy of every page pulled, with the converter, next to the data sources; cite the source in commits.
