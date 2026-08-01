"""
Context assembly: the query layer between raw tables and prompts.

Each generation step declares WHICH slices of data it may see.
Join keys: market_id (B,C,E,G filter on it) and city_id (D filtered by the
city-interest list read from B). F/H/A are global config tables (no market
dimension) and are loaded in full.

In production these filters become SQL WHERE clauses; the logic is identical.
"""
from __future__ import annotations
from .parser import split_list, _clean
from .schema import TABLE_SPECS


def _row_md(row: dict) -> str:
    return " | ".join(f"{k}: {v}" for k, v in row.items() if _clean(v))


def _table_md(title: str, rows) -> str:
    if not rows:
        return f"### {title}\n(no data)\n"
    if isinstance(rows, dict):
        body = "\n".join(f"- {k}: {v}" for k, v in rows.items())
    else:
        body = "\n".join(f"- {_row_md(r)}" for r in rows)
    return f"### {title}\n{body}\n"


def _market_tokens(market: str) -> set:
    from .schema import alias_map
    aliases_all = alias_map()
    m = _clean(market).lower()
    toks = {m}
    toks |= aliases_all.get(m, set())
    for full, aliases in aliases_all.items():
        if m in aliases:
            toks.add(full); toks |= aliases
    return toks


def _mcode(market: str) -> str:
    from . import scoring
    return scoring.market_code(market)


def _covers(cell: str, market: str) -> bool:
    c = _clean(cell).lower()
    if "all" in c:
        return True
    if "selected" in c:          # ambiguous coverage -> include; the raw value
        return True              # stays visible so the model can flag it
    tokens = {t.strip() for t in c.replace(";", ",").split(",") if t.strip()}
    return bool(tokens & _market_tokens(market))


def _city_match(cluster_name: str, interest_cities: list[str]) -> bool:
    cl = _clean(cluster_name).lower()
    return any(c.lower() in cl or cl in c.lower() for c in interest_cities)


def flags_md(flags: list[dict], ns: str = "C") -> str:
    if not flags:
        return "### Review pre-check (code layer)\nNo confirmation items found.\n"
    lines = [f"- {f.get('_id', f'{ns}-{i}')}: [{f['type']}] {f['detail']}"
             for i, f in enumerate(flags, 1)]
    return ("### Pre-assigned confirmation items (code layer) - MUST be addressed\n"
            + "\n".join(lines)
            + f"\nID rules: the {ns}-N IDs above are PRE-ASSIGNED by code. Use them verbatim in "
              "your 'Needs confirmation' table. Items you add beyond this list continue the same "
              f"sequence ({ns}-{len(flags)+1}, {ns}-{len(flags)+2}...). Never invent a different "
              "numbering scheme, never reference an ID that is not defined in this document set, "
              "and a row can never be 'Blocked by' its own ID. Do NOT fill in missing values "
              "yourself. Do NOT include flagged items in main recommendations.\n")


def assemble_global(tables: dict, flags: list[dict]) -> str:
    """Context for the campaign-level strategy brief: all markets compared,
    full city/channel/module/asset/constraint picture."""
    from .plan import recommendation_contract_md
    parts = [
        _table_md("Campaign info (table A)", tables.get("A_Campaign")),
        _table_md("Market demand signals (table B)", tables.get("B_Markets")),
        _table_md("Product performance by market (table C)", tables.get("C_Products")),
        _table_md("City readiness (table D)", tables.get("D_Cities")),
        _table_md("Channels (table E)", tables.get("E_Channels")),
        _table_md("Page module library (table F)", tables.get("F_Modules")),
        _table_md("Creative assets (table G)", tables.get("G_Assets")),
        _table_md("Stakeholder constraints (table H)", tables.get("H_Constraints")),
        _derived_md(tables),
        recommendation_contract_md(tables),
        flags_md(flags),
    ]
    return "\n".join(parts)


def _derived_md(tables: dict, market: str | None = None) -> str:
    from . import scoring
    from .parser import parse_markets
    rows = scoring.market_scores(tables)
    if market:
        rows = [r for r in rows if r["market"].lower() == market.lower()]
        roles = scoring.roles_md(tables, [market])
    else:
        roles = scoring.roles_md(tables, parse_markets(tables))
    mkts = [market] if market else parse_markets(tables)
    return ("### Pre-computed decision results [DERIVED by code - use as-is, do NOT recompute]\n"
            + scoring.scores_md(rows) + "\n\n" + roles + "\n\n"
            + scoring.eligibility_md(tables, mkts) + "\n")


def assemble_market(tables: dict, market: str, flags: list[dict],
                    upstream: str) -> tuple[str, dict]:
    """Context for one market's execution pack.
    Returns (context_markdown, trace) where trace records exactly which rows
    were selected — shown in the UI 'context inspector' and kept for audit."""
    b = [r for r in (tables.get("B_Markets") or [])
         if _clean(r.get("Market")).lower() == market.lower()]
    c = [r for r in (tables.get("C_Products") or [])
         if _clean(r.get("Market")).lower() == market.lower()]

    interest = split_list(b[0].get("Top City Interest Signals", "")) if b else []
    d_all = tables.get("D_Cities") or []
    d = [r for r in d_all if _city_match(r.get("City / Cluster", ""), interest)]

    e = [r for r in (tables.get("E_Channels") or [])
         if _covers(r.get("Market Coverage", ""), market)]
    g = [r for r in (tables.get("G_Assets") or [])
         if _covers(r.get("Required Markets", ""), market)]

    def _annotate(rows, col):
        out = []
        for r in rows:
            r = dict(r)
            if "selected" in _clean(r.get(col, "")).lower():
                r["COVERAGE STATUS"] = ("AMBIGUOUS: 'Selected markets' does not explicitly "
                                         "include this market - owner confirmation required")
            out.append(r)
        return out
    e = _annotate(e, "Market Coverage")
    g = _annotate(g, "Required Markets")

    f = tables.get("F_Modules")
    h = tables.get("H_Constraints")

    mkt_flags = [fl for fl in flags
                 if market.lower() in (fl.get("row", "") + fl.get("detail", "")).lower()
                 or fl["table"] in ("A_Campaign",)
                 or any(_city_match(fl.get("row", ""), interest) for _ in [0])
                 and fl["table"] == "D_Cities"]

    parts = [
        f"### Target market\n{market}\n",
        _table_md("Campaign configuration (table A, global)", tables.get("A_Campaign")),
        _table_md("Market demand (table B, this market only)", b),
        _table_md("Product performance (table C, this market only)", c),
        _table_md(f"City readiness (table D, only cities this market searches for: {', '.join(interest)})", d),
        _table_md("Available channels (table E, filtered by coverage)", e),
        _table_md("Page module library (table F, full)", f),
        _table_md("Assets applicable to this market (table G, filtered)", g),
        _table_md("Stakeholder constraints (table H, full)", h),
        _derived_md(tables, market),
        flags_md(mkt_flags, ns=_mcode(market)),
        "### Upstream human-review decisions\n"
        "RESOLVED items are authoritative. UNRESOLVED/DEFERRED items remain blockers and "
        "must never be described as confirmed.\n" + (upstream or "(none)") + "\n",
    ]
    trace = {
        "A campaign configuration": "full (global campaign scope, objective and duration)",
        "B rows": [r.get("Market") for r in b],
        "C rows": [r.get("Market") for r in c],
        "D rows (via city-interest join)": [r.get("City / Cluster") for r in d],
        "D rows excluded": [r.get("City / Cluster") for r in d_all if r not in d],
        "E rows (coverage filter)": [r.get("Channel") for r in e],
        "E rows excluded": [r.get("Channel") for r in (tables.get("E_Channels") or []) if r not in e],
        "G rows (coverage filter)": [r.get("Asset Type") for r in g],
        "F/H": "full (global config tables, no market dimension)",
    }
    return "\n".join(parts), trace
