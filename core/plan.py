"""Typed campaign decision contract used to constrain LLM recommendations.

The contract is destination-agnostic.  It freezes source/derived facts while
leaving strategy choices (angle, ordering and play) to the model and reviewer.
"""
from __future__ import annotations

from .parser import _clean, _is_missing, parse_markets
from . import scoring


def _named_rows(rows, name_col: str) -> list[dict]:
    return [dict(r, _name=_clean(r.get(name_col))) for r in (rows or [])
            if _clean(r.get(name_col))]


def recommendation_contract(tables: dict) -> dict:
    """Return the exact facts and legal choices for recommendation rows."""
    modules = _named_rows(tables.get("F_Modules"), "Module")
    assets = _named_rows(tables.get("G_Assets"), "Asset Type")
    channels = _named_rows(tables.get("E_Channels"), "Channel")
    products_by_market: dict[str, list[dict]] = {}
    for row in (tables.get("C_Products") or []):
        products_by_market.setdefault(_clean(row.get("Market")).lower(), []).append(row)

    markets = []
    for market in parse_markets(tables):
        channel_state = scoring.channel_eligibility(tables, market)
        asset_state = scoring.asset_eligibility(tables, market)
        eligible_channel_names = set(channel_state["eligible"])
        ambiguous_channel_names = {
            item.split(" (", 1)[0] for item in channel_state["ambiguous"]
        }
        eligible_asset_names = set(asset_state["eligible"])
        ambiguous_asset_names = {
            item.split(" (", 1)[0] for item in asset_state["ambiguous"]
        }
        markets.append({
            "market": market,
            "code": scoring.market_code(market),
            "tier": next((r["tier"] for r in scoring.market_scores(tables)
                          if r["market"].lower() == market.lower()), "NEEDS DATA"),
            "cities": scoring.city_roles(tables, market),
            "product_rows": products_by_market.get(market.lower(), []),
            "channels": {
                "eligible": [r for r in channels if r["_name"] in eligible_channel_names],
                "ambiguous": [r for r in channels if r["_name"] in ambiguous_channel_names],
                "not_eligible": [r for r in channels
                                 if r["_name"] not in eligible_channel_names
                                 and r["_name"] not in ambiguous_channel_names],
            },
            "assets": {
                "eligible": [r for r in assets if r["_name"] in eligible_asset_names],
                "ambiguous": [r for r in assets if r["_name"] in ambiguous_asset_names],
                "not_eligible": [r for r in assets
                                 if r["_name"] not in eligible_asset_names
                                 and r["_name"] not in ambiguous_asset_names],
            },
        })
    return {"markets": markets, "modules": modules}


def recommendation_contract_md(tables: dict) -> str:
    """Compact prompt representation of locked facts and permitted choices."""
    contract = recommendation_contract(tables)
    lines = [
        "### Campaign recommendation matrix decision contract [CODE-LOCKED]",
        "Create exactly one matrix row per market x interest city. The Market, City, Role, "
        "Tier, channel eligibility, asset eligibility/priority and module names below are "
        "locked facts. The model may choose and explain product angle, module order, a subset "
        "of ELIGIBLE channels/assets, dependencies and Play. AMBIGUOUS channels, assets or modules "
        "may appear only as "
        "conditional/pending confirmation; NOT ELIGIBLE items may not be selected. NEEDS DATA "
        "cities cannot receive a committed product, channel, asset or conversion play.",
    ]
    module_items = []
    for r in contract["modules"]:
        contribution = _clean(r.get("Conversion Contribution")) or "missing"
        status = ("AMBIGUOUS - contribution missing/TBD"
                  if _is_missing(r.get("Conversion Contribution")) else "ELIGIBLE")
        module_items.append(f"{r['_name']} [conversion={contribution}; {status}]")
    lines.append("- Module library (select/order only; do not rename): " +
                 ("; ".join(module_items) or "none"))
    for m in contract["markets"]:
        city_text = "; ".join(f"{r['city']} = {r['role']}" for r in m["cities"]) or "none"
        products = []
        for r in m["product_rows"]:
            products.append(", ".join(f"{k}={_clean(v)}" for k, v in r.items()
                                      if k != "Market" and _clean(v)))
        ch = m["channels"]
        ast = m["assets"]
        eligible_assets = ", ".join(
            f"{r['_name']} [{_clean(r.get('Priority')) or 'priority missing'}]"
            for r in ast["eligible"]
        ) or "none"
        ambiguous_assets = ", ".join(
            f"{r['_name']} [{_clean(r.get('Priority')) or 'priority missing'}]"
            for r in ast["ambiguous"]
        ) or "none"
        lines.extend([
            f"- {m['market']} (code {m['code']}, tier {m['tier']}):",
            f"  - LOCKED city roles: {city_text}.",
            f"  - Product evidence (do not invent availability/price): {' | '.join(products) or 'none'}.",
            f"  - Channels ELIGIBLE: {', '.join(r['_name'] for r in ch['eligible']) or 'none'}; "
            f"AMBIGUOUS: {', '.join(r['_name'] for r in ch['ambiguous']) or 'none'}; "
            f"NOT ELIGIBLE: {', '.join(r['_name'] for r in ch['not_eligible']) or 'none'}.",
            f"  - Assets ELIGIBLE: {eligible_assets}; AMBIGUOUS: {ambiguous_assets}; "
            f"NOT ELIGIBLE: {', '.join(r['_name'] for r in ast['not_eligible']) or 'none'}.",
        ])
    return "\n".join(lines) + "\n"
