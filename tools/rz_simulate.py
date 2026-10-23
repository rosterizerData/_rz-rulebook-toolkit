"""
rz_simulate.py — minimal Rosterizer rule-engine simulator.

A reduced port of the engine that runs rules against an in-memory asset
tree, sufficient for validating arithmetic and constraint logic without
booting the live Rosterizer app.

Status: engine core. Build asset trees yourself via `Asset(...)` and feed
in a rulebook's rule dicts; the runner executes them per Rosterizer's
order-bucket / action-type semantics.

Use this module as a TEMPLATE. Per-game generators historically have a
"build-an-asset-tree-from-CSV-or-source-data" layer on top of this; see
`tools/README.md` for the seams that typically need extending.

Engine surface implemented:
  - Path roots: {self}, {parent}, {roster}, {this}
  - Path tails: stats.<name>.value, evals.N.result.<field>, tracked.<name>,
    tally.<name>, keywords.<cat>, allowed.classifications,
    constraints.{any,all,none,not}
  - Eval ops: AND/OR/SUM, equation T+O / T-O / O-T / T*O / T/O / O/T
  - Eval bounds: min, max, value (equality), contains, not, actionable
  - Action types: set, modify, add, remove, info
  - Action value: literal or path-ref
  - Rule order: by `order` ascending, then ACTION_TYPE_ORDER, then doc order

Engine surface NOT yet implemented (extend as specific rulebooks demand):
  - templateClass inheritance flattening (assume rulebook has been
    pre-flattened, or flatten in your generator)
  - included / traits hydration from ranked-stat selections
  - branched path segments (array-of-strings inside a path)
  - cross-rule eval references ({this}.rules.<name>.evals.N....)
  - keyword-driven constraint resolution against a child asset
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── data shape ──────────────────────────────────────────────────────────────

@dataclass
class Asset:
    """A live, in-memory asset node. Mirrors the runtime shape Rosterizer
    composes from the catalog/taxonomy, but kept minimal here."""
    classification: str = ""
    designation: str = ""
    item: str = ""                                     # "Class§Name" key, if instantiated from a catalog item
    stats: dict = field(default_factory=dict)          # {name: {"value": x, ...}}
    keywords: dict = field(default_factory=dict)      # {category: [values]}
    aspects: dict = field(default_factory=dict)
    allowed: dict = field(default_factory=lambda: {"classifications": [], "items": []})
    disallowed: dict = field(default_factory=lambda: {"classifications": [], "items": []})
    constraints: dict = field(default_factory=lambda: {"any": [], "all": [], "none": [], "not": []})
    children: list = field(default_factory=list)
    parent: 'Asset | None' = None
    tally: dict = field(default_factory=dict)         # populated by composition
    tracked: dict = field(default_factory=dict)       # populated by composition

    def add_child(self, child: 'Asset'):
        child.parent = self
        self.children.append(child)


# ── path resolution ─────────────────────────────────────────────────────────

def resolve_root(token: str, ctx: dict) -> Asset:
    if token == "{self}":
        return ctx["self"]
    if token == "{parent}":
        p = ctx["self"].parent
        if p is None:
            raise ValueError("{parent} requested on a root asset")
        return p
    if token == "{roster}":
        node = ctx["self"]
        while node.parent is not None:
            node = node.parent
        return node
    raise ValueError(f"unknown path root: {token!r}")


def resolve_path(path, ctx: dict, rule_evals_results: list):
    """Resolve a path (list of segments) to its terminal value.
    {this}.evals.N.result.<field> reads the in-progress rule's eval results.
    """
    if not path:
        raise ValueError("empty path")
    head = path[0]

    if head == "{this}":
        if len(path) < 5 or path[1] != "evals" or path[3] != "result":
            raise ValueError(f"unsupported {{this}} path: {path}")
        idx = int(path[2])
        field_name = path[4]
        if idx >= len(rule_evals_results):
            return 0
        res = rule_evals_results[idx]
        return res.get(field_name, 0 if field_name in ("float", "integer") else "")

    asset = resolve_root(head, ctx)
    return _walk_asset_path(asset, path[1:])


def _walk_asset_path(node: Any, segs: list):
    """Walk asset-shape segments. Tolerant of unknown stats (returns 0)."""
    if not segs:
        return node

    seg, rest = segs[0], segs[1:]

    if seg == "stats":
        if not rest:
            return node.stats
        name = rest[0]
        stat = node.stats.get(name)
        if stat is None:
            return 0
        if len(rest) == 1:
            return stat
        return stat.get(rest[1], 0 if rest[1] in ("value", "min", "max") else "")

    if seg == "keywords":
        if not rest:
            return node.keywords
        return node.keywords.get(rest[0], [])

    if seg == "tracked":
        if not rest:
            return node.tracked
        return node.tracked.get(rest[0], 0)

    if seg == "tally":
        if not rest:
            return node.tally
        return node.tally.get(rest[0], 0)

    if seg == "aspects":
        if not rest:
            return node.aspects
        return node.aspects.get(rest[0])

    if seg == "allowed":
        if not rest:
            return node.allowed
        return node.allowed.get(rest[0], [])

    if seg == "disallowed":
        if not rest:
            return node.disallowed
        return node.disallowed.get(rest[0], [])

    if seg == "constraints":
        if not rest:
            return node.constraints
        return node.constraints.get(rest[0], [])

    if seg == "designation":
        return node.designation

    if seg == "item":
        return node.item

    if seg == "text":
        # ability/stratagem prose body
        return getattr(node, "text", "")

    # Unknown segment: return empty rather than crashing; generators that need
    # specific tails should extend this function. Return type tries to be
    # consistent with the most common usage (string vs numeric).
    return 0


def resolve_operand(value_spec, ctx, rule_evals_results):
    """An action `value` or equation `value` may be a literal or a path-ref."""
    if isinstance(value_spec, list):
        return resolve_path(value_spec, ctx, rule_evals_results)
    return value_spec


# ── arithmetic ──────────────────────────────────────────────────────────────

def run_equation(T, op, O):
    if op == "T+O": return (T or 0) + (O or 0)
    if op == "T-O": return (T or 0) - (O or 0)
    if op == "O-T": return (O or 0) - (T or 0)
    if op == "T*O": return (T or 0) * (O or 0)
    if op == "T/O": return (T / O) if O else 0
    if op == "O/T": return (O / T) if T else 0
    raise ValueError(f"unknown equation op: {op!r}")


# ── eval execution ──────────────────────────────────────────────────────────

def run_eval(e: dict, ctx: dict, rule_evals_results: list):
    """Execute a single eval. Returns (truthy, actionable, result_dict)."""
    operator = e.get("operator", "AND")
    paths = e.get("paths", []) or []
    actionable = e.get("actionable", True)
    equation = e.get("equation")
    eq_value = e.get("value")
    eq_min = e.get("min")
    eq_max = e.get("max")
    contains = e.get("contains", False)
    not_ = e.get("not", False)

    result: dict = {"float": 0, "integer": 0, "string": "", "array": [], "truthy": False}
    truthy = True

    if operator == "SUM":
        total = 0.0
        truthy_count = 0
        for p in paths:
            v = resolve_path(p, ctx, rule_evals_results)
            if isinstance(v, (int, float)):
                total += v
            elif v:
                truthy_count += 1
        if total == 0 and truthy_count > 0:
            total = float(truthy_count)
        if equation:
            operand = resolve_operand(equation["value"], ctx, rule_evals_results)
            total = run_equation(total, equation["operator"], operand)
        result["float"] = total
        result["integer"] = int(total)
        result["truthy"] = bool(total)
        T = total
    else:
        values = [resolve_path(p, ctx, rule_evals_results) for p in paths]
        T = values[0] if values else 0
        if equation:
            operand = resolve_operand(equation["value"], ctx, rule_evals_results)
            T = run_equation(T, equation["operator"], operand)
        if isinstance(T, (int, float)):
            result["float"] = float(T)
            result["integer"] = int(T)
        if isinstance(T, str):
            result["string"] = T
        if isinstance(T, list):
            result["array"] = T
        result["truthy"] = bool(T)

    if actionable:
        target = T
        if contains and eq_value is not None:
            resolved = resolve_operand(eq_value, ctx, rule_evals_results)
            if isinstance(target, (list, tuple, set)):
                truthy = resolved in target
            elif isinstance(target, str):
                truthy = isinstance(resolved, str) and resolved in target
            else:
                truthy = (target == resolved)
        elif eq_value is not None:
            resolved = resolve_operand(eq_value, ctx, rule_evals_results)
            truthy = (target == resolved)
        if eq_min is not None:
            mn = resolve_operand(eq_min, ctx, rule_evals_results)
            if isinstance(target, (int, float)):
                truthy = truthy and (target >= mn)
        if eq_max is not None:
            mx = resolve_operand(eq_max, ctx, rule_evals_results)
            if isinstance(target, (int, float)):
                truthy = truthy and (target <= mx)
    if not_:
        truthy = not truthy

    return truthy, actionable, result


# ── action execution ────────────────────────────────────────────────────────

ACTION_TYPE_ORDER = ["info", "set", "modify", "remove", "add"]


def run_action(a: dict, ctx: dict, rule_evals_results: list):
    atype = a.get("actionType", "set")
    if atype == "info":
        return
    apaths = a.get("paths", []) or []
    aval = a.get("value")
    iterations = a.get("iterations", 1)
    if isinstance(iterations, list):
        iterations = resolve_path(iterations, ctx, rule_evals_results) or 0
    iterations = int(iterations)

    for _ in range(iterations):
        for p in apaths:
            resolved = resolve_operand(aval, ctx, rule_evals_results)
            _apply_action(p, atype, resolved, ctx, rule_evals_results)


def _apply_action(path, atype, value, ctx, rule_evals_results):
    """Apply an action to its path target. Supports common write targets;
    extend as needed."""
    if not path:
        return

    head = path[0]
    asset = resolve_root(head, ctx)
    rest = path[1:]
    if not rest:
        return

    seg = rest[0]
    tail = rest[1:]

    # stats.<name>.<field> writes
    if seg == "stats":
        if len(tail) < 1:
            return
        name = tail[0]
        if name not in asset.stats:
            asset.stats[name] = {"value": 0}
        fld = tail[1] if len(tail) > 1 else "value"
        cur = asset.stats[name].get(fld, 0 if fld in ("value", "min", "max") else "")
        if atype == "set":
            asset.stats[name][fld] = value
        elif atype == "modify":
            if isinstance(cur, (int, float)) or cur is None:
                asset.stats[name][fld] = (cur or 0) + (value or 0)
            else:
                asset.stats[name][fld] = (cur or "") + (value or "")
        elif atype == "remove":
            if isinstance(cur, (int, float)):
                asset.stats[name][fld] = 0
        elif atype == "add":
            asset.stats[name][fld] = (cur or 0) + (value or 0)
        return

    # list-shaped writes
    list_targets = {
        "keywords": asset.keywords,
        "allowed": asset.allowed,
        "disallowed": asset.disallowed,
        "constraints": asset.constraints,
    }
    if seg in list_targets and tail:
        bucket = list_targets[seg]
        key = tail[0]
        lst = bucket.setdefault(key, [])
        if atype == "add":
            if value is not None and value != "" and value not in lst:
                lst.append(value)
        elif atype == "remove":
            while value in lst:
                lst.remove(value)
        elif atype == "set":
            bucket[key] = list(value) if isinstance(value, list) else [value]
        return

    if seg == "designation":
        if atype == "set":
            asset.designation = value
        elif atype == "modify":
            asset.designation = (asset.designation or "") + (value or "")
        return

    # silently ignore unimplemented path tails so simulation can proceed;
    # extend this function for paths your rulebook needs


# ── rule execution ──────────────────────────────────────────────────────────

def run_rule(rule_def: dict, ctx: dict):
    evals = rule_def.get("evals", []) or []
    actions = rule_def.get("actions", []) or []
    evaluate = rule_def.get("evaluate", "AND")

    rule_results: list = []
    actionable_truthies = []
    for e in evals:
        truthy, actionable, res = run_eval(e, ctx, rule_results)
        rule_results.append(res)
        if actionable:
            actionable_truthies.append(truthy)

    if not actionable_truthies:
        passes = True
    elif evaluate == "OR":
        passes = any(actionable_truthies)
    else:
        passes = all(actionable_truthies)

    if not passes:
        return

    for a in actions:
        run_action(a, ctx, rule_results)


def apply_rank_tracking(asset: 'Asset'):
    """For each rank stat on the asset, if the selected rank has a `tracking`
    dict, apply each (statName: delta) into the asset's matching stats.
    This mirrors Rosterizer's implicit rank-tracking composition step.
    Idempotent: tracks an applied marker per stat to avoid double-application
    when called repeatedly (e.g. before each rule pass).
    """
    applied = asset.stats.setdefault("__rank_tracking_applied__", {"value": {}})
    applied_map = applied["value"] if isinstance(applied.get("value"), dict) else {}
    if not isinstance(applied_map, dict):
        applied_map = {}

    for stat_name, stat_def in list(asset.stats.items()):
        if not isinstance(stat_def, dict):
            continue
        ranks = stat_def.get("ranks")
        if not isinstance(ranks, dict):
            continue
        selected = stat_def.get("value")
        if selected is None:
            continue
        rank_def = ranks.get(selected)
        if not isinstance(rank_def, dict):
            continue
        tracking = rank_def.get("tracking") or {}
        # Skip if already applied for this (stat_name, selected) pair
        prev = applied_map.get(stat_name)
        if prev == selected:
            continue
        # Reverse a previous selection's tracking if any
        if prev is not None:
            prev_tracking = (ranks.get(prev) or {}).get("tracking") or {}
            for tn, tv in prev_tracking.items():
                if isinstance(tv, (int, float)) and tn in asset.stats:
                    cur = asset.stats[tn].get("value", 0) or 0
                    if isinstance(cur, (int, float)):
                        asset.stats[tn]["value"] = cur - tv
        # Apply the new selection
        for tn, tv in tracking.items():
            if not isinstance(tv, (int, float)):
                continue
            if tn not in asset.stats:
                asset.stats[tn] = {"value": 0}
            cur = asset.stats[tn].get("value", 0) or 0
            if isinstance(cur, (int, float)):
                asset.stats[tn]["value"] = cur + tv
        applied_map[stat_name] = selected

    applied["value"] = applied_map


def run_all_rules(rules_dict: dict, ctx: dict):
    """Run a dict of rules respecting Rosterizer's order/type bucketing.
    Applies rank-stat tracking to the asset before rule execution begins."""
    apply_rank_tracking(ctx["self"])

    buckets: dict = {}
    for name, r in rules_dict.items():
        order = r.get("order", 0)
        actions = r.get("actions") or []
        atype = actions[0].get("actionType", "set") if actions else "info"
        buckets.setdefault(order, {}).setdefault(atype, []).append(r)

    for order in sorted(buckets):
        for atype in ACTION_TYPE_ORDER:
            for r in buckets[order].get(atype, []):
                run_rule(r, ctx)


# ── helpers for building asset trees from a rulebook ────────────────────────

def instantiate_item(rulebook: dict, item_key: str, parent: 'Asset | None' = None) -> Asset:
    """Construct an Asset from a catalog item key. Merges class-level
    stats/keywords/aspects from the immediate class with the item-level
    overrides (item wins). Does NOT walk templateClass inheritance chains —
    pre-flatten the rulebook if you need that.
    """
    catalog = rulebook["rulebook"]["assetCatalog"]
    taxonomy = rulebook["rulebook"]["assetTaxonomy"]
    item_def = catalog.get(item_key, {}) or {}
    cls, _, name = item_key.partition("§")
    class_def = taxonomy.get(cls, {}) or {}

    # Merge: class-level first, item-level on top
    stats = {}
    for source in (class_def, item_def):
        for sn, sd in (source.get("stats") or {}).items():
            if sn not in stats:
                stats[sn] = dict(sd) if isinstance(sd, dict) else {"value": sd}
            else:
                # item overrides shallow-merge over class
                if isinstance(sd, dict):
                    stats[sn].update(sd)
                else:
                    stats[sn]["value"] = sd

    def merge_dict_lists(*sources):
        out = {}
        for s in sources:
            for k, v in (s or {}).items():
                out.setdefault(k, [])
                if isinstance(v, list):
                    for item in v:
                        if item not in out[k]:
                            out[k].append(item)
        return out

    keywords = merge_dict_lists(class_def.get("keywords"), item_def.get("keywords"))
    aspects = {**(class_def.get("aspects") or {}), **(item_def.get("aspects") or {})}
    allowed = {
        **{"classifications": [], "items": []},
        **(class_def.get("allowed") or {}),
        **(item_def.get("allowed") or {}),
    }
    disallowed = {
        **{"classifications": [], "items": []},
        **(class_def.get("disallowed") or {}),
        **(item_def.get("disallowed") or {}),
    }
    constraints = {
        **{"any": [], "all": [], "none": [], "not": []},
        **(class_def.get("constraints") or {}),
        **(item_def.get("constraints") or {}),
    }

    return Asset(
        classification=cls,
        designation=name,
        item=item_key,
        stats=stats,
        keywords=keywords,
        aspects=aspects,
        allowed=allowed,
        disallowed=disallowed,
        constraints=constraints,
        parent=parent,
    )


def get_class_rules(rulebook: dict, class_name: str) -> dict:
    """Fetch a class's rules from the taxonomy."""
    return (rulebook["rulebook"]["assetTaxonomy"].get(class_name) or {}).get("rules", {}) or {}


def get_item_rules(rulebook: dict, item_key: str) -> dict:
    return ((rulebook["rulebook"]["assetCatalog"].get(item_key) or {}).get("rules", {})) or {}


# ── module CLI for ad-hoc dumps ─────────────────────────────────────────────

def main():
    """Stub CLI: load a rulebook, print top-level structure. Real generators
    should `import rz_simulate` and use the engine functions directly."""
    import sys
    if len(sys.argv) < 2:
        print("usage: python3 rz_simulate.py <rulebook.json>")
        sys.exit(1)
    rb = json.loads(Path(sys.argv[1]).read_text())
    tax = rb["rulebook"]["assetTaxonomy"]
    cat = rb["rulebook"]["assetCatalog"]
    print(f"rulebook: {rb.get('name')} (rev {rb.get('revision')})")
    print(f"  taxonomy classes: {len(tax)}")
    print(f"  catalog items:    {len(cat)}")


if __name__ == "__main__":
    main()
