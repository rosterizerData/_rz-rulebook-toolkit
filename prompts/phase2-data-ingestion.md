# Phase 2 — Data Ingestion Prompt

Paste this prompt into a fresh Claude conversation. Attach or paste the Phase 1 skeleton rulebook, the source data (Wahapedia export, BSData XML, screenshot table, or plain text), and fill in the `[CONTEXT]` block at the bottom.

---

You are helping author a **Rosterizer rulebook** by converting raw game data into a CSV import file. You have a skeleton rulebook (Phase 1 output) that establishes the class structure. Your job is to produce a CSV that populates the catalog with all real game units and assets.

## What you are producing

A CSV file where:
- **Each row** is one catalog item (one unit, weapon, ability, wargear piece, etc.)
- **Column headers** are derived from the skeleton's taxonomy — see the column reference below
- **`§` delimiters** are used inside multi-value fields (traits, keywords, constraints lists)
- **Empty cell** means "not set / not applicable for this item"

## Column reference

The header row is built from the skeleton, in this order:

| Column | Format | Notes |
|---|---|---|
| `designation` | `ClassName§Item Name` | e.g. `Troops§Tactical Squad` |
| `stats§X` | value matching statType | **One column per stat defined in the taxonomy for this item's class.** Include all stat columns that any item in the file might use; leave blank for items where a stat doesn't apply. |
| `keywords§CategoryName` | `Value1§Value2§...` | **One column per keyword category declared in the taxonomy.** Multiple values separated by `§`. |
| `allowed§classifications` | `Class1§Class2§...` | Leave blank unless this item overrides the class default. |
| `allowed§items` | `Class§Item§§Class§Item§...` | Specific allowed items. Pairs separated by `§§`. |
| `constraints§any` | `Keyword1§Keyword2§...` | |
| `constraints§all` | | |
| `constraints§none` | | |
| `constraints§not` | | |
| `disallowed§classifications` | | |
| `disallowed§items` | | |
| `assets§traits` | See trait encoding below | Always-present sub-assets. |
| `assets§included` | See trait encoding below | Default sub-assets (removable). |
| `text` | plain text or markdown | Human-readable breakdown + rule-implementation notes. See below. |

The exact set of `stats§X` and `keywords§X` columns depends entirely on the skeleton's taxonomy. Do not invent columns. Do not omit a stat column just because most items leave it blank — if any item in the file uses it, include it for all rows.

### Trait encoding in `assets§traits` / `assets§included`

Simple trait (no stat overrides):
```
ClassName§Item Name
```

Trait with stat overrides (JSON-encoded, escaped for CSV):
```
{"item":"ClassName§Item Name","stats":{"statName":{"value":"X"}}}
```

Multiple traits separated by `§§`.

### The `text` field

The text field is both a **human-readable reference** for editors and reviewers, and the **implementation brief for Phase 3**. Write it so a person unfamiliar with the source rules can understand what this unit does and what still needs to be built.

Structure:

```markdown
**[Unit Name]**

Base: [points] pts | [composition summary]

Default wargear: [list]

Options:
- [option]: [cost] — [any special constraint or note]
- ...

Special rules (for reference; not yet implemented in rulebook):
- [rule name]: [one-sentence mechanical summary]
- ...

Rule quirks to implement:
- [ ] [specific, actionable description of what the rulebook rule needs to do]
- [ ] ...
```

The rule quirks checklist is the Phase 3 input. Be precise: "Points cost scales by model count: base 100pts for 10 models, +10pts per additional model up to 20" not "variable cost".

If a unit has no rule quirks beyond what static stats and keyword constraints cover, write "No rule quirks — fully captured by stats and keywords."

## What NOT to do

- Do not edit the skeleton `.rulebook` file
- Do not write any JSON rule blocks
- Do not invent stat or keyword column names — only use what's declared in the skeleton
- If source data references a stat not in the skeleton, note it in `text` as "**Missing stat:** [name] — needed for [rule quirk]" and flag it in the post-CSV summary

## Source data handling

You will be given raw source data (Wahapedia HTML/text, BSData XML, book transcription, etc.). For each unit:

1. Map it to the correct class from the skeleton taxonomy
2. Extract all stat values and keywords
3. List all default wargear as traits (or included assets)
4. Write the text block
5. Output the CSV row

If a unit's wargear option requires a catalog item that doesn't exist yet (e.g. a weapon not in the skeleton), add a stub row for it — mark its `text` as `STUB — add stats and quirks`. Phase 3 will complete it.

## Output format

Produce one CSV file per class grouping, named `[GameDir]_[ClassName]_assets.csv` (e.g. `HorusHeresy_Troops_assets.csv`). Don't mix unrelated classes in the same file unless the total item count is very small.

Use standard CSV quoting: wrap any cell containing commas, newlines, or quotes in double-quotes; escape internal double-quotes as `""`.

After each CSV block, summarize:
- Count of items produced
- Any stats from source data with no column in the skeleton (flag for Phase 1 revision)
- Any units that couldn't be mapped to a class (flag for taxonomy discussion)

## Stopping condition

When all source data for this pass has been converted, tell the user:

> **Phase 2 complete for this pass.** Import each CSV into Rosterizer via the catalog import tool. Verify:
> - All units appear in the correct class
> - Points costs match the source data
> - A test roster with real units reaches the expected points total
> - The text fields are readable and the rule quirks checklists are accurate
>
> Report import errors or cost mismatches. Do not proceed to Phase 3 until imports are clean and text fields have been reviewed.

---

## Context (fill this in before pasting the prompt)

```
Game name:
Phase 1 skeleton: [attach file or paste inline]
Source data: [attach file, paste inline, or provide URL]
Which classes to process in this pass: [e.g. "Troops and Characters only — do Vehicles next"]
```
