# cyberHits — obfuscated Gaslands example

A reskinned Gaslands rulebook, used as the toolkit's worked example for the **flat single-file** rulebook shape (no inheritance chain). Mechanics are 1:1 with the source; only proper nouns and prose change.

| Source | Reskinned as |
|---|---|
| `Gaslands/Gaslands-Refuelled.rulebook` | `cyberhits.rulebook` |

## Why this shape matters

The bugWars chain demonstrates 40k-style **module dependencies + inheritance** (core → faction → army → sub-army). cyberHits demonstrates the opposite: a single self-contained rulebook with all mechanics in one place.

What it exercises that bugWars doesn't:

- **Path branching** — `["{self}", "included", "classification", ["Vehicle—Restricted", "Vehicle—Standard"], "traits"]` shows array-branched path segments resolving to multiple targets.
- **Sponsor-driven constraint mutation** — selecting a sponsor closes off and opens up which Perks/Vehicles can be taken. Different from the 40k Detachment pattern (which adds Stratagems).
- **Per-vehicle weight class** — a rank stat that gates which Upgrades fit, via constraint matching on the Weight keyword.
- **Generous use of `Special Rule` items** — small reusable trait packets attached to vehicles or weapons. The 40k books don't lean on this pattern as hard.

## Theme

**Cyberpunk corporate hit-squads.** Each post-apocalyptic-racing sponsor becomes a corporate paramilitary contractor; vehicles become urban-combat transports; the gonzo-Mad-Max prose becomes hard-edged corporate-warfare prose. The reskin is a name-and-prose swap, not a system change.

| Source sponsor | cyberHits equivalent |
|---|---|
| Highway Patrol | Tac-Response Division |
| Military | Corporate Defense Forces |
| Mishkin | Mishkin Heavy Industries |
| Rusty's Bootleggers | Coyote Cartel |
| The Warden | The Warden Conglomerate |
| Verney | Verney Black-Ops |

(Mishkin and Verney aren't real-world IP terms, so they survive intact with light corporate framing.)

The reskin map covers sponsors, vehicles, cargo, perks, and the prose lexicon (Mad-Max-isms → cyberpunk-isms: chrome, neon, ICE, jack, decker, runner, blacknet, megacorp, etc.).

## Files

| File | Purpose |
|---|---|
| `naming_map.json` | The full reskin dictionary. Edit and re-run `reskin.py` to iterate. |
| `reskin.py` | One-off script. Reads `naming_map.json`, walks the source rulebook, emits `cyberhits.rulebook` and a diff log. |
| `cyberhits.rulebook` | Output rulebook. |
| `reskin_diff.log` | Every substitution made, with frequency. Spot-check fodder. |

## Reproducing

```bash
cd examples/cyberHits
python3 reskin.py
# Reads:  ../../../Gaslands/Gaslands-Refuelled.rulebook
# Reads:  naming_map.json
# Writes: cyberhits.rulebook
# Writes: reskin_diff.log
```

## See also

- `examples/bugWars/` — the inheritance-chain example (40k → bugs)
- `docs/RULE_PATTERNS.md` — patterns that both examples reference
