# Rosterizer Rulebook Toolkit — Handoff

Shared knowledge, patterns, and tooling for authoring Rosterizer rulebooks. Designed to live alongside the per-game rulebook repos in `RosterizerTestData/`.

## Why this exists

Three problems this toolkit aims to solve:

1. **Half-finished rulebooks are stuck.** Existing rulebooks in `RosterizerTestData/` were authored with partial knowledge of the rulebook format. They need diagnostics and worked examples to push to completion.
2. **Domain expertise is leaving.** The main contributor for 40k is stepping away. Future maintainers (human or AI) need pattern references to extend or fix games they don't know intimately.
3. **New games are slow to onboard.** Each new rulebook starts from scratch. A generator template + ingestion path for upstream data sources speeds this up.

## Status

This is a **handoff package** intended to be moved into a dedicated `RosterizerTestData/rz-rulebook-toolkit` repo (or similar). The owning repo will handle IP obfuscation for the 40k example.

## Build order

The pieces aren't independent. Build them in this sequence:

1. **`docs/RULEBOOK_AUTHORING.md`** — the missing manual, including canonical type definitions for stats, ranks, rules, evals, and actions.
2. **`docs/RULE_PATTERNS.md`** — cookbook of common idioms (mutex via Unique, gating via constraints, SUM-tracked points). References the authoring doc.
2b. **`docs/CAMPAIGN_TRACKING.md`** — campaign-style mini-games (counters, trackers, honour families, gates) and the engine facts they depend on, from the 40k 11e Crusade build.
3. **`docs/PATH_SYNTAX.md`** — eval/action path syntax reference, including the full writable path table derived from the engine's path option tree.
3. **`docs/RZ_DATA_FORMAT_PRINCIPLES.md`** — the rules that are easy to get wrong in the current format: the `Roster` class is the root (no `Roster§Roster` item), sparseness, child-list shapes, what the engine stamps and a book never writes, the legacy spellings the importer rewrites.
4. **`docs/BSDATA_INGESTION.md`** — BSData XML → Rosterizer concept map and notes for building a fresh ingestion tool. Includes `BS_schema.png` (BSData ER diagram, source unknown).
4. **`examples/bugWars/`** — obfuscated 40k chain (core → faction → army → sub-army). Worked example for inheritance/dependency rulebooks.
5. **`examples/cyberHits/`** — obfuscated Gaslands. Worked example for the flat single-file shape.
6. **`prompts/phase1-skeleton.md`** — question-driven prompt that produces an importable skeleton with one item per class.
7. **`prompts/phase2-data-ingestion.md`** — data-to-CSV prompt; outputs catalog rows with a rule-quirks checklist in each unit's text field.
8. **`prompts/phase3-rules.md`** — one-rule-at-a-time prompt with test-case protocol to prevent contradictory rule churn.
9. **`tools/rz_simulate.py`** — engine-core simulator for validating rulebook arithmetic without round-tripping through the live app.
10. **`tools/rz_lint.py`** — diagnostics: unresolved paths, dead rules, undefined stats referenced by rules. *(unbuilt)*
11. *(later)* **BattleScribe ingestion path** — back-burner until the toolkit shape is stable. The sibling `battlescribe-to-rosterizer` repo predates NewRecruit's data extensions; revisit when the toolkit shape settles.

## What's in this package

- `docs/` — distilled authoring knowledge; `BSDATA_INGESTION.md` + `BS_schema.png` salvaged from the deleted `battlescribe-to-rosterizer` repo
- `prompts/` — copy-paste prompts for each authoring phase
- `tools/` — `rz_simulate.py` engine core; future linter/diff
- `examples/bugWars/` — obfuscated 40k chain (core, faction, army, sub-army)
- `examples/cyberHits/` — obfuscated Gaslands (flat single-file shape)

The examples keep the shapes they shipped with, including a `Roster§Roster` catalog item as the root; the current Rosterizer lifts that item into the `Roster` class on import (`docs/RZ_DATA_FORMAT_PRINCIPLES.md`, "Legacy spellings"). Write new rulebooks with the `Roster` class as the root.

## Provenance notes

The authoring docs synthesize material scraped from:

- `_reference/client/src/app/data/help-content.ts` — user-facing help with the canonical vocabulary (Rule Wizard, Stat Wizard, Glossary sections)
- `_reference/client/src/app/data/rule-recipes.ts` — rule examples that the Rule Wizard ships
- `_reference/client/src/app/helpers/roster.process.ts` — `executeRule` and supporting code; authoritative behavior
- `_reference/client/src/app/models/rule.model.ts` — type definitions
- Shipped rulebooks: `RosterizerTestData/Warhammer40k10e/*.rulebook`, `RosterizerTestData/Gaslands/*.rulebook`, and `RosterizerTestData/Reign-in-Hell/*.rulebook`
- v1 fixtures at `client/src/assets/fixtures/rulebooks/{chess,chess-piecewise,fray}.input.json`
