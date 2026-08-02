"""Multi-call workflow: per-market AI judgment, deterministic document assembly.

The model never owns source/derived identifiers.  It proposes angles and plays
against a market slice; this module joins those proposals back onto the typed
campaign contract and renders the final Markdown.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from . import scoring
from .parser import _clean, _is_missing, parse_markets
from .plan import recommendation_contract


class StructuredOutputError(ValueError):
    pass


def extract_json(text: str) -> dict:
    """Extract one JSON object from a provider response, tolerating code fences."""
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise StructuredOutputError("Model did not return a JSON object.") from None
        try:
            value = json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError as exc:
            raise StructuredOutputError(f"Invalid model JSON: {exc.msg} at position {exc.pos}.") from None
    if not isinstance(value, dict):
        raise StructuredOutputError("Model JSON must be an object.")
    return value


def call_json(call_model: Callable[[str], str], prompt: str) -> dict:
    """One normal call plus one JSON-only repair call when syntax is invalid."""
    first = call_model(prompt)
    try:
        return extract_json(first)
    except StructuredOutputError as exc:
        repair = ("Return ONLY a valid JSON object. Repair the syntax of the response below; "
                  "do not add fields or change its intended decisions.\n\n"
                  f"Parser error: {exc}\n\n{first}")
        return extract_json(call_model(repair))


def campaign_weeks(tables: dict) -> list[int]:
    campaign = tables.get("A_Campaign") or {}
    match = re.search(r"(\d+)\s*week", _clean(campaign.get("Campaign Duration")), re.I)
    return list(range(1, int(match.group(1)) + 1)) if match else []


def _slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", _clean(value).upper()).strip("_")


def _evidence_item(display: str, tag: str, kind: str) -> dict:
    return {"display": display, "tag": tag, "kind": kind}


def _row_evidence(name: str, row: dict, fields: tuple[str, ...]) -> str:
    """Compact all decision-relevant source attributes into one immutable evidence item."""
    details = [f"{field} = {_clean(row.get(field))}" for field in fields
               if _clean(row.get(field))]
    return f"{name}: " + ("; ".join(details) if details else "no supporting attributes supplied")


def market_evidence_catalog(tables: dict, market: str) -> dict[str, dict]:
    """Whitelisted evidence IDs for one market; the model selects IDs, never rewrites facts."""
    contract = _find_market_contract(tables, market)
    campaign = tables.get("A_Campaign") or {}
    b = next((r for r in (tables.get("B_Markets") or [])
              if _clean(r.get("Market")).lower() == market.lower()), {})
    c = next((r for r in (tables.get("C_Products") or [])
              if _clean(r.get("Market")).lower() == market.lower()), {})
    catalog = {}

    def add(eid, display, tag, kind):
        if _clean(display):
            catalog[eid] = _evidence_item(display, tag, kind)

    add("A.CAMPAIGN_DURATION", f"Campaign Duration = {_clean(campaign.get('Campaign Duration'))}",
        "FACT - table A", "A")
    add("A.CAMPAIGN_OBJECTIVE", f"Campaign Objective = {_clean(campaign.get('Campaign Objective'))}",
        "FACT - table A", "A")
    for field in ("Search UV Index", "Search Growth vs Baseline", "Booking Lead Time",
                  "Top City Interest Signals", "Main User Barrier", "Localization Need"):
        add(f"B.{_slug(field)}", f"{field} = {_clean(b.get(field))}", "FACT - table B", "B")
    for field, value in c.items():
        if field != "Market":
            add(f"C.{_slug(field)}", f"{field} = {_clean(value)}", "FACT - table C", "C")
    for city in contract["cities"]:
        risk = f"; campaign risk = {_clean(city.get('risk'))}" if _clean(city.get("risk")) else ""
        cluster = f"; readiness cluster = {_clean(city.get('cluster'))}" if _clean(city.get("cluster")) else ""
        display = f"{city['city']} role = {city['role']}; {city['why']}{cluster}{risk}"
        add(f"DERIVED.CITY_ROLE.{_slug(city['city'])}", display, "DERIVED", "DERIVED")
    for status in ("eligible", "ambiguous"):
        for row in contract["channels"][status]:
            add(f"E.CHANNEL.{_slug(row['_name'])}",
                _row_evidence(
                    row["_name"], row,
                    ("Estimated Reach", "CTR Index", "Conversion Quality", "Resource Owner", "Notes"),
                ) + f"; eligibility = {'eligible' if status == 'eligible' else 'conditional'} for {market}",
                "DERIVED", "E")
        for row in contract["assets"][status]:
            add(f"G.ASSET.{_slug(row['_name'])}",
                _row_evidence(
                    row["_name"], row,
                    ("Priority", "Usage", "Localization Level", "Notes"),
                ) + f"; eligibility = {status} for {market}",
                "FACT - table G", "G")
    for row in recommendation_contract(tables)["modules"]:
        add(f"F.MODULE.{_slug(row['_name'])}",
            _row_evidence(
                row["_name"], row,
                ("Description", "CTR Index", "Conversion Contribution", "Design Complexity", "Notes"),
            ), "FACT - table F", "F")
    for row in (tables.get("H_Constraints") or []):
        add(f"H.CONSTRAINT.{_slug(row.get('Stakeholder'))}",
            _row_evidence(
                _clean(row.get("Stakeholder")), row,
                ("Input / Requirement", "Impact on AI Workflow"),
            ),
            "FACT - table H", "H")
    return catalog


def global_evidence_catalog(tables: dict, recommendations: dict[str, dict],
                            flags: list[dict]) -> dict[str, dict]:
    catalog = {}
    campaign = tables.get("A_Campaign") or {}
    catalog["A.CAMPAIGN_OBJECTIVE"] = _evidence_item(
        f"Campaign Objective = {_clean(campaign.get('Campaign Objective'))}", "FACT - table A", "A")
    catalog["A.CAMPAIGN_DURATION"] = _evidence_item(
        f"Campaign Duration = {_clean(campaign.get('Campaign Duration'))}", "FACT - table A", "A")
    for score in scoring.market_scores(tables):
        value = "withheld" if score["score"] is None else score["score"]
        catalog[f"SCORE.{_slug(score['market'])}"] = _evidence_item(
            f"{score['market']} score = {value}; tier = {score['tier']}", "DERIVED", "SCORE")
    for market, rec in recommendations.items():
        channels = sorted({x["id"] for city in rec["cities"] for x in city["channels"]})
        assets = sorted({f"{x['id']} [{x.get('priority')}]" for city in rec["cities"] for x in city["assets"]})
        roles = ", ".join(f"{c['city']}={c['role']}" for c in rec["cities"])
        catalog[f"REC.{_slug(market)}.CITY_ROLES"] = _evidence_item(
            f"{market} city roles: {roles}", "DERIVED", "REC")
        catalog[f"REC.{_slug(market)}.CHANNELS"] = _evidence_item(
            f"{market} selected channels: {', '.join(channels) or 'none'}", "AI REC", "REC")
        catalog[f"REC.{_slug(market)}.ASSETS"] = _evidence_item(
            f"{market} requested assets: {', '.join(assets) or 'none'}", "AI REC", "REC")
    for flag in flags:
        if flag.get("_id"):
            catalog[f"FLAG.{flag['_id']}"] = _evidence_item(
                f"{flag['_id']}: {_clean(flag.get('detail'))}", "NEEDS CONFIRMATION", "FLAG")
    for row in (tables.get("H_Constraints") or []):
        catalog[f"H.CONSTRAINT.{_slug(row.get('Stakeholder'))}"] = _evidence_item(
            _row_evidence(
                _clean(row.get("Stakeholder")), row,
                ("Input / Requirement", "Impact on AI Workflow"),
            ),
            "FACT - table H", "H")
    return catalog


def _decision_reading_issues(value, path: str, evidence_catalog: dict | None = None,
                             required_kinds: tuple[str, ...] = ()) -> list[str]:
    if not isinstance(value, dict):
        return [f"{path} must be an object with recommendation, rationale and evidence_refs."]
    issues = []
    generic = ("execute within", "follow the rules", "review the data", "use eligible")
    for field in ("recommendation", "rationale"):
        text = _clean(value.get(field))
        if not text:
            issues.append(f"{path}.{field} is required.")
        elif len(text.split()) < 4 or any(x in text.lower() for x in generic):
            issues.append(f"{path}.{field} is too generic; make it evidence-based and operational.")
    refs = [_clean(x) for x in _items(value.get("evidence_refs")) if _clean(x)]
    if evidence_catalog is not None:
        if not refs:
            issues.append(f"{path}.evidence_refs must contain at least one evidence ID.")
        invalid = [ref for ref in refs if ref not in evidence_catalog]
        if invalid:
            issues.append(f"{path}.evidence_refs contains invalid IDs: {invalid}.")
        kinds = {evidence_catalog[ref]["kind"] for ref in refs if ref in evidence_catalog}
        if required_kinds and not kinds.intersection(required_kinds):
            issues.append(f"{path}.evidence_refs must include evidence from one of {required_kinds}.")
    return issues


def _product_ids(contract: dict) -> list[str]:
    """Product signal names in source-column order, deduplicated across duplicate rows."""
    allowed = set(scoring.SCORING["product_weights"])
    out = []
    for row in contract.get("product_rows", []):
        for field in row:
            if field in allowed and field not in out:
                out.append(field)
    return out


def validate_market_json(raw: dict, tables: dict, market: str,
                         evidence_catalog: dict | None = None) -> list[str]:
    """Semantic completeness checks for AI-owned fields before normalization."""
    contract = _find_market_contract(tables, market)
    issues = []
    for field in ("market_summary", "immediate_next_action", "product_focus"):
        if len(_clean(raw.get(field)).split()) < 4:
            issues.append(f"{field} must contain a specific decision, not a label or slogan.")

    evidence_catalog = evidence_catalog or market_evidence_catalog(tables, market)
    readings = raw.get("readings") if isinstance(raw.get("readings"), dict) else {}
    reading_kinds = {
        "positioning": ("B", "C"), "city_portfolio": ("DERIVED",),
        "modules": ("B", "F"), "crm": ("B", "E"),
        "assets": ("G", "H"), "localization": ("B", "H"),
    }
    for name, kinds in reading_kinds.items():
        issues += _decision_reading_issues(
            readings.get(name), f"readings.{name}", evidence_catalog, kinds
        )

    locked_cities = {c["city"].lower(): c for c in contract["cities"]}
    rows = [r for r in _items(raw.get("cities")) if isinstance(r, dict)]
    returned = [_clean(r.get("city")).lower() for r in rows if _clean(r.get("city"))]
    if len(returned) != len(set(returned)):
        issues.append("cities contains duplicate city rows.")
    if set(returned) != set(locked_cities):
        issues.append("cities must contain every supplied interest city exactly once and no others.")

    module_rows = {r["_name"]: r for r in recommendation_contract(tables)["modules"]}
    channel_state = {r["_name"]: "eligible" for r in contract["channels"]["eligible"]}
    channel_state.update({r["_name"]: "conditional" for r in contract["channels"]["ambiguous"]})
    asset_rows = {r["_name"]: r for group in ("eligible", "ambiguous")
                  for r in contract["assets"][group]}
    selected_channels = set()
    for row in rows:
        city = _clean(row.get("city"))
        locked = locked_cities.get(city.lower())
        if not locked:
            continue
        if len(_clean(row.get("product_angle")).split()) < 3 or len(_clean(row.get("play")).split()) < 3:
            issues.append(f"cities[{city}] needs a specific product_angle and play.")
        resources = sum((_resource_requests(row.get(key)) for key in ("modules", "channels", "assets")), [])
        if locked["role"] == "NEEDS DATA" and resources:
            issues.append(f"cities[{city}] is NEEDS DATA and must not select resources.")
        for request in _resource_requests(row.get("modules")):
            if request["id"] not in module_rows:
                issues.append(f"cities[{city}].modules contains unknown id '{request['id']}'.")
        for request in _resource_requests(row.get("channels")):
            if request["id"] not in channel_state:
                issues.append(f"cities[{city}].channels contains ineligible id '{request['id']}'.")
            else:
                selected_channels.add(request["id"])
        for request in _resource_requests(row.get("assets")):
            asset = asset_rows.get(request["id"])
            if not asset:
                issues.append(f"cities[{city}].assets contains ineligible id '{request['id']}'.")
            elif _clean(asset.get("Priority")) == "P2" and len(request["justification"].split()) < 5:
                issues.append(f"cities[{city}] P2 asset '{request['id']}' needs a material justification.")

    # Resource priority lists remain advisory: normalization intersects them with the locked
    # selections and safely removes unknown IDs. Product priority is different because the
    # execution table labels it as an AI recommendation. Require a complete decision for every
    # table-C signal so a missing model array cannot be mistaken for a recommended ranking.
    priority_plan = raw.get("priority_plan") if isinstance(raw.get("priority_plan"), dict) else {}
    product_rows = [row for row in _items(priority_plan.get("products"))
                    if isinstance(row, dict)]
    expected_products = _product_ids(contract)
    returned_products = [_clean(row.get("id")) for row in product_rows
                         if _clean(row.get("id"))]
    if len(returned_products) != len(set(returned_products)):
        issues.append("priority_plan.products contains duplicate product IDs.")
    if set(returned_products) != set(expected_products):
        issues.append(
            "priority_plan.products must contain every supplied table C product field exactly "
            f"once: {expected_products}."
        )
    for row in product_rows:
        product_id = _clean(row.get("id"))
        if product_id not in expected_products:
            continue
        if len(_clean(row.get("decision")).split()) < 3:
            issues.append(
                f"priority_plan.products[{product_id}].decision must state lead, support or defer action."
            )
        if len(_clean(row.get("reason")).split()) < 3:
            issues.append(
                f"priority_plan.products[{product_id}].reason must explain the evidence-based trade-off."
            )
        refs = [_clean(ref) for ref in _items(row.get("evidence_refs")) if _clean(ref)]
        expected_ref = f"C.{_slug(product_id)}"
        if expected_ref not in refs:
            issues.append(
                f"priority_plan.products[{product_id}].evidence_refs must include {expected_ref}."
            )

    crm = raw.get("crm") if isinstance(raw.get("crm"), dict) else {}
    for field in ("objective", "rationale"):
        if len(_clean(crm.get(field)).split()) < 5:
            issues.append(f"crm.{field} must explain the market-specific CRM decision.")
    crm_refs = [_clean(x) for x in _items(crm.get("evidence_refs")) if _clean(x)]
    if not crm_refs:
        issues.append("crm.evidence_refs must contain at least one evidence ID.")
    invalid_crm_refs = [ref for ref in crm_refs if ref not in evidence_catalog]
    if invalid_crm_refs:
        issues.append(f"crm.evidence_refs contains invalid IDs: {invalid_crm_refs}.")
    if not any(ref in ("B.BOOKING_LEAD_TIME", "B.MAIN_USER_BARRIER") for ref in crm_refs):
        issues.append("crm.evidence_refs must include B.BOOKING_LEAD_TIME or B.MAIN_USER_BARRIER.")
    segments = [s for s in _items(crm.get("segments")) if isinstance(s, dict)]
    if not segments:
        issues.append("crm.segments must contain at least one structured audience segment.")
    for index, segment in enumerate(segments, 1):
        if not _clean(segment.get("name")) or not _clean(segment.get("reason")):
            issues.append(f"crm.segments[{index}] requires name and reason.")
        if segment.get("assumption") is not True:
            issues.append(f"crm.segments[{index}] must set assumption=true.")
        window = _clean(segment.get("window"))
        if re.search(r"\d", window) and not any(x in window.lower() for x in ("illustrative", "assumption")):
            issues.append(f"crm.segments[{index}].window must label numeric windows illustrative.")

    plans = [p for p in _items(crm.get("weekly_plan")) if isinstance(p, dict)]
    expected_weeks = campaign_weeks(tables)
    returned_weeks = [p.get("week") for p in plans]
    if returned_weeks != expected_weeks:
        issues.append(f"crm.weekly_plan must contain exactly weeks {expected_weeks} in order.")
    for plan in plans:
        week = plan.get("week", "?")
        for field in ("objective", "audience", "action"):
            if len(_clean(plan.get(field)).split()) < 3:
                issues.append(f"crm.weekly_plan[{week}].{field} is missing or too generic.")
        action = _clean(plan.get("action")).lower()
        if "pm to calibrate" in action or "no activation scheduled" in action:
            issues.append(f"crm.weekly_plan[{week}] cannot use a placeholder action.")
        ids = [_clean(x) for x in _items(plan.get("channel_ids")) if _clean(x)]
        refs = [_clean(x) for x in _items(plan.get("evidence_refs")) if _clean(x)]
        gate = _clean(plan.get("gate"))
        if not ids and not (gate and any(x in action for x in ("hold", "defer", "wait", "block"))):
            issues.append(f"crm.weekly_plan[{week}] needs selected channels or an explicit gated hold.")
        for channel in ids:
            if channel not in channel_state:
                issues.append(f"crm.weekly_plan[{week}] uses ineligible channel '{channel}'.")
            elif channel not in selected_channels:
                issues.append(f"crm.weekly_plan[{week}] uses '{channel}' but no city recommendation selects it.")
            elif channel_state[channel] == "conditional" and not gate:
                issues.append(f"crm.weekly_plan[{week}] uses conditional '{channel}' without a gate ID.")

    eligible = {r["_name"] for r in contract["channels"]["eligible"]}
    if _items(crm.get("push_copy")) and ("App Push" not in eligible or "App Push" not in selected_channels):
        issues.append("crm.push_copy requires App Push to be explicitly eligible and selected.")
    if _items(crm.get("edm_copy")) and ("EDM" not in eligible or "EDM" not in selected_channels):
        issues.append("crm.edm_copy requires EDM to be explicitly eligible and selected.")
    return issues


def validate_global_json(raw: dict, markets: list[str],
                         evidence_catalog: dict | None = None) -> list[str]:
    issues = []
    fields = ("overview_reading", "tiering_reading", "cross_market_insight",
              "product_reading", "channel_reading", "resource_reading", "risk_reading",
              "launch_reading")
    for field in fields:
        issues += _decision_reading_issues(raw.get(field), field, evidence_catalog)
    if len(_clean(raw.get("core_tension")).split()) < 6:
        issues.append("core_tension must state a specific campaign trade-off.")
    rationales = raw.get("market_rationales") if isinstance(raw.get("market_rationales"), dict) else {}
    if set(rationales) != set(markets):
        issues.append("market_rationales must contain every exact market name and no others.")
    return issues


def call_validated_json(call_model: Callable[[str], str], prompt: str,
                        validator: Callable[[dict], list[str]]) -> dict:
    """Normalize semantic drift, but never invent a report when model JSON is unavailable."""
    first = call_model(prompt)
    try:
        value = extract_json(first)
    except StructuredOutputError as first_error:
        syntax_repair = (
            "Return ONLY valid JSON. Repair the response syntax without changing its intended "
            f"content. Parser error: {first_error}\n\nPrevious response:\n{first}"
        )
        try:
            repaired = extract_json(call_model(syntax_repair))
        except Exception as second_error:
            raise StructuredOutputError(
                "Model returned invalid JSON twice; no report was generated. "
                f"First error: {first_error}; repair error: {second_error}"
            ) from None
        remaining = validator(repaired)
        if remaining:
            repaired["_validation_hints"] = remaining
        return repaired

    issues = validator(value)
    if not issues:
        return value
    repair = (f"{prompt}\n\nYour previous response failed validation. Return the FULL corrected JSON "
              "object only. Preserve valid strategy choices and fix every issue below. Do not "
              "change locked facts.\n- " + "\n- ".join(issues) + "\n\nPrevious response:\n" + first)
    try:
        repaired = extract_json(call_model(repair))
        remaining = validator(repaired)
    except Exception as exc:
        value["_validation_hints"] = issues + [
            f"Semantic repair failed; original parseable model output was normalized: {exc}"
        ]
        return value
    if remaining:
        repaired["_validation_hints"] = remaining
    return repaired


def _items(value) -> list:
    return value if isinstance(value, list) else []


def _resource_requests(value) -> list[dict]:
    out = []
    for item in _items(value):
        if isinstance(item, str):
            out.append({"id": item, "justification": ""})
        elif isinstance(item, dict) and _clean(item.get("id")):
            out.append({"id": _clean(item.get("id")),
                        "justification": _clean(item.get("justification"))})
    return out


def _find_market_contract(tables: dict, market: str) -> dict:
    return next(m for m in recommendation_contract(tables)["markets"]
                if m["market"].lower() == market.lower())


def _flag_ids_for_city(flags: list[dict], market: str, city: str) -> list[str]:
    out = []
    for flag in flags:
        haystack = " ".join(str(flag.get(k, "")) for k in ("market", "city", "row", "detail")).lower()
        if market.lower() in haystack and city.lower() in haystack and flag.get("_id"):
            out.append(flag["_id"])
    return out


def _flag_ids_for_market(flags: list[dict], market: str) -> list[str]:
    return [f["_id"] for f in flags
            if f.get("_id") and market.lower() in
            " ".join(str(f.get(k, "")) for k in ("market", "row", "detail")).lower()]


def _normalize_reading(value, fallback: str = "PM review is required before execution.",
                       evidence_catalog: dict | None = None) -> dict:
    if isinstance(value, str):
        value = {"recommendation": value,
                 "rationale": "The available evidence requires human review."}
    value = value if isinstance(value, dict) else {}
    # Accept old in-session model output after a hot reload, but all new calls use the
    # action-first recommendation/rationale contract above.
    recommendation = (_clean(value.get("recommendation")) or
                      _clean(value.get("decision")) or fallback)
    rationale = _clean(value.get("rationale"))
    if not rationale:
        rationale = " ".join(filter(None, (
            _clean(value.get("finding")), _clean(value.get("reason"))
        ))) or "The available evidence requires human review."
    refs = [_clean(x) for x in _items(value.get("evidence_refs"))
            if _clean(x) and (evidence_catalog is None or _clean(x) in evidence_catalog)]
    return {
        "recommendation": recommendation,
        "rationale": rationale,
        "evidence_refs": refs,
        "evidence_basis": [evidence_catalog[ref] for ref in refs]
                          if evidence_catalog is not None else [],
    }


def _first_unique_resource_ids(cities: list[dict], key: str) -> list[str]:
    out = []
    for city in cities:
        for item in city[key]:
            if item["id"] not in out:
                out.append(item["id"])
    return out


def _normalize_priority_dimension(value, expected_ids: list[str], evidence_catalog: dict,
                                  evidence_id: Callable[[str], str]) -> list[dict]:
    """Preserve valid model order; safely append any missing locked candidates."""
    raw_rows = {str(item.get("id", "")).strip(): item for item in _items(value)
                if isinstance(item, dict) and _clean(item.get("id")) in expected_ids}
    raw_order = [_clean(item.get("id")) for item in _items(value)
                 if isinstance(item, dict) and _clean(item.get("id")) in expected_ids]
    ordered_ids = list(dict.fromkeys(raw_order + expected_ids))
    out = []
    for item_id in ordered_ids:
        item = raw_rows.get(item_id, {})
        decision = _clean(item.get("decision"))
        reason = _clean(item.get("reason"))
        model_recommended = bool(decision and reason)
        refs = [_clean(ref) for ref in _items(item.get("evidence_refs"))
                if _clean(ref) in evidence_catalog]
        fallback_ref = evidence_id(item_id)
        if not refs and fallback_ref in evidence_catalog:
            refs = [fallback_ref]
        out.append({
            "id": item_id,
            "decision": decision or "AI priority decision unavailable",
            "reason": reason or "Source signal retained for review; no model ranking was accepted",
            "model_recommended": model_recommended,
            "evidence_refs": refs,
            "evidence_basis": [evidence_catalog[ref] for ref in refs],
        })
    return out


def _normalize_priority_plan(raw, contract: dict, cities: list[dict],
                             evidence_catalog: dict) -> dict[str, list[dict]]:
    raw = raw if isinstance(raw, dict) else {}
    expected = {
        "cities": [city["city"] for city in cities],
        "products": _product_ids(contract),
        "channels": _first_unique_resource_ids(cities, "channels"),
        "modules": _first_unique_resource_ids(cities, "modules"),
        "assets": _first_unique_resource_ids(cities, "assets"),
    }
    prefixes = {
        "cities": lambda item: f"DERIVED.CITY_ROLE.{_slug(item)}",
        "products": lambda item: f"C.{_slug(item)}",
        "channels": lambda item: f"E.CHANNEL.{_slug(item)}",
        "modules": lambda item: f"F.MODULE.{_slug(item)}",
        "assets": lambda item: f"G.ASSET.{_slug(item)}",
    }
    return {name: _normalize_priority_dimension(
        raw.get(name), expected[name], evidence_catalog, prefixes[name]
    ) for name in expected}


_CONSTRAINT_SCOPES = {
    "city_product", "crm", "assets", "content", "localization", "campaign",
}


def _source_constraint_scopes(row: dict) -> list[str]:
    """Route a qualitative H-row to report dimensions without changing its meaning."""
    text = " ".join(_clean(row.get(field)).lower() for field in (
        "Stakeholder", "Input / Requirement", "Impact on AI Workflow",
    ))
    scopes = []
    rules = (
        ("city_product", ("supply", "inventory", "product depth", "over-promis")),
        ("crm", ("crm", "push", "frequency", "audience", "segment", "suppression")),
        ("assets", ("ued", "design", "creative", "asset", "p0", "p1")),
        ("content", ("content center", "content resource", "content is truly needed")),
        ("localization", ("regional", "localiz", "copy angle", "market-level override")),
    )
    for scope, markers in rules:
        if any(marker in text for marker in markers):
            scopes.append(scope)
    return scopes or ["campaign"]


def _market_uses_content(cities: list[dict]) -> bool:
    markers = ("content", "editorial", "creator", "inspiration", "themed", "guide")
    values = []
    for city in cities:
        values += [city.get("role"), city.get("product_angle"), city.get("play")]
        for dimension in ("modules", "channels", "assets"):
            values += [item.get("id") for item in city.get(dimension, [])]
    text = " ".join(_clean(value).lower() for value in values)
    return any(marker in text for marker in markers)


def _normalize_stakeholder_constraints(raw: dict, tables: dict, cities: list[dict],
                                       warnings: list[str], market: str) -> list[dict]:
    """Keep every mechanically relevant H constraint; tolerate the legacy singular field."""
    source_rows = [row for row in (tables.get("H_Constraints") or [])
                   if _clean(row.get("Stakeholder"))]
    by_name = {_clean(row.get("Stakeholder")): row for row in source_rows}
    requested = [item for item in _items(raw.get("stakeholder_constraints"))
                 if isinstance(item, dict)]
    legacy = raw.get("stakeholder_constraint")
    if not requested and isinstance(legacy, dict):
        requested = [legacy]

    requested_by_name = {}
    for item in requested:
        name = _clean(item.get("stakeholder"))
        if name not in by_name:
            if name:
                warnings.append(f"{market}: unknown stakeholder constraint '{name}' removed.")
            continue
        requested_by_name[name] = item

    has_assets = any(city.get("assets") for city in cities)
    uses_content = _market_uses_content(cities)
    out = []
    for row in source_rows:
        name = _clean(row.get("Stakeholder"))
        inferred = _source_constraint_scopes(row)
        model_item = requested_by_name.get(name, {})
        model_scopes = [_clean(scope) for scope in _items(model_item.get("applies_to"))
                        if _clean(scope) in _CONSTRAINT_SCOPES]
        scopes = inferred if inferred != ["campaign"] else (model_scopes or inferred)
        mechanically_relevant = bool(
            set(scopes) & {"city_product", "crm", "localization", "campaign"}
            or ("assets" in scopes and has_assets)
            or ("content" in scopes and uses_content)
        )
        if not mechanically_relevant and not model_item:
            continue
        out.append({
            "stakeholder": name,
            "source_requirement": _clean(row.get("Input / Requirement")),
            "source_impact": _clean(row.get("Impact on AI Workflow")),
            "application": (_clean(model_item.get("impact"))
                            or _clean(row.get("Impact on AI Workflow"))
                            or "Apply this source constraint without inventing missing limits."),
            "applies_to": scopes,
        })
    return out


def normalize_market_recommendation(raw: dict, tables: dict, market: str,
                                    campaign_flags: list[dict]) -> tuple[dict, list[str]]:
    """Join AI-only fields onto locked facts; missing/illegal choices are repaired safely."""
    contract = _find_market_contract(tables, market)
    warnings = [f"{market}: {hint}" for hint in _items(raw.get("_validation_hints"))
                if _clean(hint)]
    raw_cities = {str(r.get("city", "")).strip().lower(): r for r in _items(raw.get("cities"))
                  if isinstance(r, dict) and _clean(r.get("city"))}

    module_rows = recommendation_contract(tables)["modules"]
    modules = {r["_name"]: r for r in module_rows}
    eligible_channels = {r["_name"]: "eligible" for r in contract["channels"]["eligible"]}
    eligible_channels.update({r["_name"]: "conditional" for r in contract["channels"]["ambiguous"]})
    asset_rows = {r["_name"]: r for group in ("eligible", "ambiguous")
                  for r in contract["assets"][group]}
    asset_status = {r["_name"]: "eligible" for r in contract["assets"]["eligible"]}
    asset_status.update({r["_name"]: "conditional" for r in contract["assets"]["ambiguous"]})

    normalized_cities = []
    for locked in contract["cities"]:
        proposal = raw_cities.get(locked["city"].lower(), {})
        if not proposal:
            warnings.append(f"{market} x {locked['city']}: model row missing; code inserted a safe row.")
        normalized = {
            "city": locked["city"],
            "cluster": locked.get("cluster"),
            "role": locked["role"],
            "why": locked["why"],
            "product_angle": _clean(proposal.get("product_angle")) or "Recommendation pending PM review",
            "play": _clean(proposal.get("play")) or "Recommendation pending PM review",
            "modules": [], "channels": [], "assets": [],
            "blocker_ids": _flag_ids_for_city(campaign_flags, market, locked["city"]),
        }
        if locked["role"] == "NEEDS DATA":
            normalized["product_angle"] = "No committed activation - readiness data required"
            normalized["play"] = "Hold activation until the readiness gap is resolved"
            normalized_cities.append(normalized)
            continue

        for request in _resource_requests(proposal.get("modules")):
            row = modules.get(request["id"])
            if not row:
                warnings.append(f"{market} x {locked['city']}: unknown module '{request['id']}' removed.")
                continue
            conditional = _is_missing(row.get("Conversion Contribution"))
            normalized["modules"].append({"id": request["id"], "conditional": conditional,
                                          "justification": request["justification"]})
        for request in _resource_requests(proposal.get("channels")):
            status = eligible_channels.get(request["id"])
            if not status:
                warnings.append(f"{market} x {locked['city']}: ineligible channel '{request['id']}' removed.")
                continue
            normalized["channels"].append({"id": request["id"], "conditional": status == "conditional",
                                           "justification": request["justification"]})
        for request in _resource_requests(proposal.get("assets")):
            row, status = asset_rows.get(request["id"]), asset_status.get(request["id"])
            if not row or not status:
                warnings.append(f"{market} x {locked['city']}: ineligible asset '{request['id']}' removed.")
                continue
            priority = _clean(row.get("Priority"))
            if priority == "P2" and not request["justification"]:
                warnings.append(f"{market} x {locked['city']}: P2 asset '{request['id']}' removed without justification.")
                continue
            normalized["assets"].append({"id": request["id"], "priority": priority,
                                         "conditional": status == "conditional",
                                         "justification": request["justification"]})
        normalized_cities.append(normalized)

    evidence_catalog = market_evidence_catalog(tables, market)
    raw_readings = raw.get("readings") if isinstance(raw.get("readings"), dict) else {}
    readings = {name: _normalize_reading(raw_readings.get(name), evidence_catalog=evidence_catalog) for name in
                ("positioning", "city_portfolio", "modules", "crm", "assets", "localization")}
    priority_plan = _normalize_priority_plan(
        raw.get("priority_plan"), contract, normalized_cities, evidence_catalog
    )
    stakeholder_constraints = _normalize_stakeholder_constraints(
        raw, tables, normalized_cities, warnings, market
    )
    return {
        "market": market,
        "code": contract["code"],
        "tier": contract["tier"],
        "positioning": readings["positioning"]["recommendation"],
        "readings": readings,
        "market_summary": _clean(raw.get("market_summary")) or "Execute within the locked role and eligibility boundaries.",
        "immediate_next_action": _clean(raw.get("immediate_next_action")) or "PM to review the validated market recommendation.",
        "product_focus": _clean(raw.get("product_focus")) or "Use the strongest complete product signals in table C.",
        "stakeholder_constraints": stakeholder_constraints,
        "crm": _normalize_crm(raw.get("crm"), tables, market, contract, normalized_cities,
                              evidence_catalog),
        "priority_plan": priority_plan,
        "cities": normalized_cities,
        "market_blocker_ids": _flag_ids_for_market(campaign_flags, market),
        "normalization_warnings": warnings,
    }, warnings


def _normalize_crm(value, tables: dict, market: str, contract: dict,
                   normalized_cities: list[dict], evidence_catalog: dict) -> dict:
    value = value if isinstance(value, dict) else {}
    eligible = {r["_name"] for r in contract["channels"]["eligible"]}
    selected = {item["id"] for city in normalized_cities for item in city["channels"]}
    raw_plans = {p.get("week"): p for p in _items(value.get("weekly_plan"))
                 if isinstance(p, dict)}
    legacy = value.get("cadence") if isinstance(value.get("cadence"), dict) else {}
    weekly_plan = []
    for week in campaign_weeks(tables):
        plan = raw_plans.get(week, {})
        legacy_action = _clean(legacy.get(str(week)))
        channel_ids = [_clean(x) for x in _items(plan.get("channel_ids"))
                       if _clean(x) in selected]
        action = _clean(plan.get("action")) or legacy_action or "Plan completion required"
        refs = [_clean(x) for x in _items(plan.get("evidence_refs"))
                if _clean(x) in evidence_catalog]
        for channel in channel_ids:
            ref = f"E.CHANNEL.{_slug(channel)}"
            if ref in evidence_catalog:
                refs.append(ref)
        action_low = action.lower()
        for city in normalized_cities:
            if city["city"].lower() in action_low:
                ref = f"DERIVED.CITY_ROLE.{_slug(city['city'])}"
                if ref in evidence_catalog:
                    refs.append(ref)
        if not refs:
            for fallback_ref in ("B.BOOKING_LEAD_TIME", "B.MAIN_USER_BARRIER",
                                 "A.CAMPAIGN_DURATION"):
                if fallback_ref in evidence_catalog:
                    refs.append(fallback_ref)
                    break
        refs = list(dict.fromkeys(refs))
        weekly_plan.append({
            "week": week,
            "objective": _clean(plan.get("objective")) or "Plan completion required",
            "audience": _clean(plan.get("audience")) or "Audience definition required",
            "channel_ids": channel_ids,
            "action": action,
            "gate": _clean(plan.get("gate")),
            "evidence_basis": [evidence_catalog[ref] for ref in refs],
        })
    segments = []
    for segment in _items(value.get("segments")):
        if isinstance(segment, dict):
            segments.append({"name": _clean(segment.get("name")),
                             "window": _clean(segment.get("window")),
                             "reason": _clean(segment.get("reason")),
                             "assumption": segment.get("assumption") is True})
        elif _clean(segment):
            segments.append({"name": _clean(segment), "window": "",
                             "reason": "Audience role pending review", "assumption": True})
    return {
        "objective": _clean(value.get("objective")) or _clean(value.get("job")) or "CRM objective requires completion.",
        "rationale": _clean(value.get("rationale")) or "CRM rationale requires completion.",
        "job": _clean(value.get("objective")) or _clean(value.get("job")) or "CRM objective requires completion.",
        "segments": segments,
        "weekly_plan": weekly_plan,
        "evidence_basis": [evidence_catalog[ref] for ref in
                           [_clean(x) for x in _items(value.get("evidence_refs"))]
                           if ref in evidence_catalog],
        "push_copy": ([_clean(x) for x in _items(value.get("push_copy")) if _clean(x)]
                      if "App Push" in eligible and "App Push" in selected else []),
        "edm_copy": ([_clean(x) for x in _items(value.get("edm_copy")) if _clean(x)]
                     if "EDM" in eligible and "EDM" in selected else []),
    }


def normalize_global_synthesis(raw: dict, markets: list[str],
                               evidence_catalog: dict | None = None) -> dict:
    fields = ("overview_reading", "tiering_reading", "cross_market_insight",
              "product_reading", "channel_reading", "resource_reading", "risk_reading",
              "launch_reading")
    out = {field: _normalize_reading(raw.get(field), evidence_catalog=evidence_catalog)
           for field in fields}
    out["core_tension"] = (_clean(raw.get("core_tension")) or
                           "Campaign trade-off requires Campaign Ops PM review.")
    rationales = raw.get("market_rationales") if isinstance(raw.get("market_rationales"), dict) else {}
    out["market_rationales"] = {m: _clean(rationales.get(m)) or "Use the code-derived tier as the planning baseline."
                                for m in markets}
    return out


def compact_global_context(tables: dict, recommendations: dict[str, dict],
                           flags: list[dict]) -> str:
    def compact(value):
        if isinstance(value, dict):
            return {key: compact(item) for key, item in value.items()
                    if key not in ("evidence_basis", "normalization_warnings")}
        if isinstance(value, list):
            return [compact(item) for item in value]
        return value

    payload = {
        "campaign": tables.get("A_Campaign"),
        "market_scores": scoring.market_scores(tables),
        "market_recommendations": compact(recommendations),
        "stakeholder_constraints": tables.get("H_Constraints"),
        "confirmation_items": [{"id": f.get("_id"), "type": f.get("type"),
                                "detail": f.get("detail")} for f in flags],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _md(value) -> str:
    return (_clean(value) or "—").replace("|", "\\|").replace("\n", " ")


def _reading(value) -> str:
    if not isinstance(value, dict):
        return f"[AI REC] {_md(value)}"
    text = (f"[AI REC] {_md(value.get('recommendation'))} "
            f"{_md(value.get('rationale'))}")
    basis = _format_basis(value.get("evidence_basis", []))
    if not basis:
        return text
    return (text + "\n\n<details>\n<summary>Decision basis</summary>\n\n"
            + basis + "\n\n</details>")


def _format_basis(items: list[dict]) -> str:
    return "; ".join(f"{_md(item.get('display'))} [{item.get('tag')}]" for item in items)


def _list_resources(items: list[dict], asset: bool = False) -> str:
    if not items:
        return "—"
    rendered = []
    for item in items:
        name = item["id"] + (f" [{item.get('priority')}]" if asset and item.get("priority") else "")
        if item.get("conditional"):
            name += " (Conditional - pending owner confirmation)"
        rendered.append(name)
    return ", ".join(rendered)


def _priority_ids(rec: dict, dimension: str) -> list[str]:
    return [item["id"] for item in rec.get("priority_plan", {}).get(dimension, [])]


def _ordered_cities(rec: dict) -> list[dict]:
    by_id = {city["city"]: city for city in rec["cities"]}
    ordered = [by_id[item_id] for item_id in _priority_ids(rec, "cities") if item_id in by_id]
    return ordered + [city for city in rec["cities"] if city not in ordered]


def _ordered_resources(items: list[dict], rec: dict, dimension: str) -> list[dict]:
    rank = {item_id: index for index, item_id in enumerate(_priority_ids(rec, dimension))}
    return sorted(items, key=lambda item: rank.get(item["id"], len(rank)))


def _ranked_summary(rec: dict, dimension: str, asset: bool = False) -> str:
    rows = rec.get("priority_plan", {}).get(dimension, [])
    if not rows:
        return "—"
    resource_map = {item["id"]: item for city in rec["cities"]
                    for item in city.get(dimension, [])} if dimension in ("channels", "modules", "assets") else {}
    rendered = []
    for index, item in enumerate(rows, 1):
        label = item["id"]
        meta = resource_map.get(item["id"], {})
        if asset and meta.get("priority"):
            label += f" [{meta['priority']}]"
        if meta.get("conditional"):
            label += " (conditional)"
        rendered.append(f"{index}. {label}")
    return "; ".join(rendered)


def _constraints_for(rec: dict, scopes: set[str] | None = None) -> list[dict]:
    constraints = rec.get("stakeholder_constraints", [])
    if scopes is None:
        return constraints
    return [item for item in constraints if set(item.get("applies_to", [])) & scopes]


def _constraint_summary(rec: dict, scopes: set[str] | None = None,
                        names_only: bool = False) -> str:
    constraints = _constraints_for(rec, scopes)
    if names_only:
        return ", ".join(item["stakeholder"] for item in constraints) or "—"
    return "; ".join(
        f"{item['stakeholder']}: {item['source_requirement']}"
        for item in constraints
    ) or "—"


def _constraint_note(rec: dict, scopes: set[str]) -> str | None:
    constraints = _constraints_for(rec, scopes)
    if not constraints:
        return None
    details = "; ".join(
        f"{item['stakeholder']}: {item['source_requirement']} [FACT - table H]; "
        f"market application: {item['application']} [AI REC]"
        for item in constraints
    )
    return f"**Applicable stakeholder constraints:** {details}"


def _unique_resources_in_priority(rec: dict, dimension: str) -> list[dict]:
    first = {}
    for city in rec["cities"]:
        for item in city.get(dimension, []):
            first.setdefault(item["id"], item)
    ordered = [first[item_id] for item_id in _priority_ids(rec, dimension) if item_id in first]
    return ordered + [item for item_id, item in first.items() if item not in ordered]


def _execution_priority_lines(rec: dict) -> list[str]:
    labels = {"cities": "City", "products": "Product", "channels": "Channel",
              "modules": "Page module", "assets": "Creative asset"}
    asset_meta = {item["id"]: item for city in rec["cities"] for item in city["assets"]}
    lines = ["### Execution priority [AI REC]", "",
             "Ranked rows reflect accepted model recommendations. A row with no rank was restored from source data after an incomplete model response and is not an AI recommendation.", "",
             "| Dimension | Rank | Item | Operational decision | Why | Decision basis |",
             "|---|---:|---|---|---|---|"]
    for dimension in ("cities", "products", "channels", "modules", "assets"):
        for rank, item in enumerate(rec.get("priority_plan", {}).get(dimension, []), 1):
            item_label = item["id"]
            display_rank = rank if item.get("model_recommended", True) else "—"
            if dimension == "assets" and asset_meta.get(item["id"], {}).get("priority"):
                item_label += f" [{asset_meta[item['id']]['priority']}]"
            lines.append("| " + " | ".join(_md(value) for value in (
                labels[dimension], display_rank, item_label, item["decision"], item["reason"],
                _format_basis(item["evidence_basis"]),
            )) + " |")
    return lines


def _flag_label(flag: dict) -> str:
    """Human-readable meaning beside an enumeration-based C-N identifier."""
    kind = _clean(flag.get("type"))
    target = (_clean(flag.get("city")) or _clean(flag.get("row")) or
              _clean(flag.get("market")) or "campaign")
    field = _clean(flag.get("field"))
    if kind == "MISSING_FIELD" and field:
        return f"{target} {field} missing"
    if kind == "DUPLICATE_KEY" and field:
        return f"{target} {field} duplicate"
    if kind == "UNKNOWN_VALUE" and field:
        return f"{target} {field} invalid"
    if kind == "SCORING_INPUT_MISSING" and field:
        return f"{target} {field} scoring input"
    labels = {
        "AMBIGUOUS_COVERAGE": "eligibility",
        "UNMAPPED_MARKET": "market mapping",
        "ROLE_TENSION": "city role",
        "CONFLICT": "city role",
        "READINESS_GAP": "readiness gap",
        "SUPPLY_RISK": "supply depth",
        "TIER_KPI_REVIEW": "nurture KPI",
    }
    return f"{target} {labels.get(kind, kind.replace('_', ' ').lower() or 'confirmation')}"


def _flag_ref(flag: dict) -> str:
    fid = _clean(flag.get("_id"))
    return f"{fid} — {_flag_label(flag)}" if fid else _flag_label(flag)


def _flag_refs(ids: list[str], flags: list[dict]) -> str:
    by_id = {_clean(flag.get("_id")): flag for flag in flags}
    return ", ".join(_flag_ref(by_id[item]) if item in by_id else item for item in ids)


def _owner(flag: dict) -> str:
    table, ftype = flag.get("table", ""), flag.get("type", "")
    if ftype in ("READINESS_GAP", "SUPPLY_RISK") or table == "D_Cities": return "Sourcing Team"
    if table == "E_Channels": return "CRM / Regional owner"
    if table == "G_Assets": return "UED / Partnerships"
    if table == "F_Modules": return "Product Analytics"
    if table in ("B_Markets", "C_Products"): return "Data / Product owner"
    return "Campaign Ops PM"


def _flag_source_tag(flag: dict) -> str:
    """Describe whether a confirmation reason is copied from one table or derived across tables."""
    table = _clean(flag.get("table"))
    if " x " in table:
        return f"[DERIVED - {table}]"
    table_code = table.split("_", 1)[0] if table else "source data"
    return f"[FACT - table {table_code}]"


def _flag_confirmation_reason(flag: dict) -> str:
    return f"{_clean(flag.get('detail'))} {_flag_source_tag(flag)}".strip()


def _relevant_flags(flags: list[dict], rec: dict) -> list[dict]:
    selected = {x["id"] for city in rec["cities"] for key in ("modules", "channels", "assets")
                for x in city[key]}
    cities = {c["city"].lower() for c in rec["cities"]}
    out = []
    for flag in flags:
        hay = " ".join(str(flag.get(k, "")) for k in ("market", "city", "row", "detail")).lower()
        direct = rec["market"].lower() in hay or any(city in hay for city in cities)
        resource = any(name.lower() in hay for name in selected)
        if direct or resource:
            out.append(flag)
    return out


def render_global_brief(tables: dict, recommendations: dict[str, dict],
                        synthesis: dict, flags: list[dict]) -> str:
    campaign = tables.get("A_Campaign") or {}
    markets = parse_markets(tables)
    lines = [f"# {_md(campaign.get('Campaign Name') or 'Destination campaign')} — Campaign Strategy Brief", "",
             "## 1. Campaign overview", _reading(synthesis["overview_reading"]), ""]
    for key in ("Campaign Objective", "Campaign Duration", "Target Markets", "Destination Scope",
                "Key City Focus", "Product Scope", "Main Challenge"):
        if _clean(campaign.get(key)):
            lines.append(f"- **{key}**: {_md(campaign[key])} [FACT - table A]")
    lines += [f"- **Core tension**: {_md(synthesis['core_tension'])} [AI REC]", "",
              "## 2. Decision logic & market tiering", _reading(synthesis["tiering_reading"]), "",
              scoring.scores_md(scoring.market_scores(tables), collapse_methodology=True), ""]
    for row in scoring.market_scores(tables):
        lines.append(f"- **{row['market']} — {row['tier']} [DERIVED]**: "
                     f"{_md(synthesis['market_rationales'][row['market']])} [AI REC]")

    lines += ["", "## 3. Executive market x city summary", _reading(synthesis["cross_market_insight"]), "",
              "| Market | Convert now [DERIVED] | Conditional conversion [DERIVED] | Package only [DERIVED] | Content only [DERIVED] | Needs data [DERIVED] | Immediate next action [AI REC] |",
              "|---|---|---|---|---|---|---|"]
    for market in markets:
        rec = recommendations[market]
        groups = {k: [] for k in ("Conversion", "Conditional Conversion", "Package", "Content", "NEEDS DATA")}
        for rank, city in enumerate(_ordered_cities(rec), 1):
            blocker_text = _flag_refs(city["blocker_ids"], flags)
            label = f"#{rank} {city['city']}" + ((" [" + blocker_text + "]") if blocker_text else "")
            groups[city["role"]].append(label)
        lines.append("| " + " | ".join(_md(x) for x in [market,
                     ", ".join(groups["Conversion"]), ", ".join(groups["Conditional Conversion"]),
                     ", ".join(groups["Package"]), ", ".join(groups["Content"]),
                     ", ".join(groups["NEEDS DATA"]), rec["immediate_next_action"]]) + " |")

    lines += ["", "## 4. Product focus by market", _reading(synthesis["product_reading"]), "",
              "| Market | Product focus [AI REC] | Applicable stakeholder constraints |",
              "|---|---|---|"]
    for market in markets:
        rec = recommendations[market]
        lines.append(f"| {_md(market)} | {_md(rec['product_focus'])} | "
                     f"{_md(_constraint_summary(rec, {'city_product'}))} [FACT - table H] |")

    lines += ["", "## 5. Channel and CRM strategy", _reading(synthesis["channel_reading"]), ""]
    for market in markets:
        rec = recommendations[market]
        chosen = _ranked_summary(rec, "channels")
        lines.append(f"- **{market}**: {chosen if chosen != '—' else 'No channel committed'}; "
                     f"CRM job: {_md(rec['crm']['job'])} [AI REC]")

    lines += ["", "## 6. Resource allocation notes", _reading(synthesis["resource_reading"]), "",
              "| Market | Requested assets |",
              "|---|---|"]
    for market in markets:
        rendered = _ranked_summary(recommendations[market], "assets", asset=True)
        lines.append(f"| {_md(market)} | {_md(rendered)} |")

    lines += ["", "## 7. Risks and dependencies", _reading(synthesis["risk_reading"]), "",
              "| ID | Risk / dependency | Owner |", "|---|---|---|"]
    for flag in flags:
        lines.append(f"| {_md(_flag_ref(flag))} | {_md(flag.get('detail'))} | {_owner(flag)} |")

    lines += ["", "## 8. NEEDS CONFIRMATION list",
              "The following IDs are assigned by code and remain open until a human owner resolves them.", "",
              "| ID | Issue | Source | Owner |", "|---|---|---|---|"]
    for flag in flags:
        lines.append(f"| {_md(flag.get('_id'))} | {_md(flag.get('detail'))} | {_md(flag.get('table'))} | {_owner(flag)} |")

    lines += ["", "## 9. Campaign recommendation matrix",
              "[AI REC] Each row combines model judgment with code-locked market, city, role, cluster, eligibility and priority fields.", "",
              "| Market | City priority [AI REC] | City / readiness cluster | Locked role | Product / angle [AI REC] | Page modules [AI REC] | Channels [AI REC] | Creative assets [AI REC] | Constraint / dependency | Play [AI REC] |",
              "|---|---:|---|---|---|---|---|---|---|---|"]
    for market in markets:
        rec = recommendations[market]
        for rank, city in enumerate(_ordered_cities(rec), 1):
            city_label = city["city"] + (f" (readiness cluster: {city['cluster']})" if city.get("cluster") else "")
            blockers = _flag_refs(city["blocker_ids"], flags)
            scopes = {"city_product"}
            if city.get("channels"):
                scopes.add("crm")
            if city.get("assets"):
                scopes.add("assets")
            if _market_uses_content([city]):
                scopes.add("content")
            constraint_names = _constraint_summary(rec, scopes, names_only=True)
            dependencies = "; ".join(value for value in (blockers, constraint_names)
                                     if value and value != "—") or "—"
            lines.append("| " + " | ".join(_md(x) for x in [market, rank, city_label, city["role"],
                         city["product_angle"], _list_resources(_ordered_resources(city["modules"], rec, "modules")),
                         _list_resources(_ordered_resources(city["channels"], rec, "channels")),
                         _list_resources(_ordered_resources(city["assets"], rec, "assets"), asset=True),
                         dependencies, city["play"]]) + " |")

    lines += ["", "## 10. Launch checklist (campaign level)", _reading(synthesis["launch_reading"]), "",
               "| Checklist item | Owner | Why it needs confirmation | Blocking ID |",
               "|---|---|---|---|"]
    for flag in flags:
        lines.append("| " + " | ".join(_md(x) for x in [
            _flag_label(flag), _owner(flag), _flag_confirmation_reason(flag),
            _clean(flag.get("_id")) or "—",
        ]) + " |")
    lines += ["| Final campaign approval | Campaign Ops PM | The workflow requires final human approval before launch [NEEDS CONFIRMATION] | — |", "",
               "## 11. Appendix: derived city-role detail (audit)",
              "City roles below are rendered directly from the code layer; the model does not rewrite them.", "",
              scoring.roles_md(tables, markets)]
    return "\n".join(lines)


def render_market_pack(tables: dict, rec: dict, flags: list[dict], upstream: str = "") -> str:
    market, code = rec["market"], rec["code"]
    market_row = next((r for r in (tables.get("B_Markets") or [])
                       if _clean(r.get("Market")).lower() == market.lower()), {})
    selected_assets = _unique_resources_in_priority(rec, "assets")
    city_summary = "; ".join(
        f"{rank}. {c['city']}" +
        (f" (readiness cluster: {c['cluster']})" if c.get("cluster") else "") +
        f" — {c['role']}"
        for rank, c in enumerate(_ordered_cities(rec), 1)
    )
    lines = [f"# MARKET EXECUTION PACK: {market} ({code})", "",
             "## 1. Market positioning & decision-chain summary", _reading(rec["readings"]["positioning"]), "",
             "| Market | City / readiness cluster [CODE-LOCKED] | Product focus [AI REC] | Channel choice [AI REC] | Asset choice [AI REC] | Stakeholder constraint | Recommended play [AI REC] |",
             "|---|---|---|---|---|---|---|",
             "| " + " | ".join(_md(x) for x in [market, city_summary, rec["product_focus"],
                    _ranked_summary(rec, "channels"),
                    _ranked_summary(rec, "assets", asset=True),
                    f"{_constraint_summary(rec)} [FACT - table H]",
                    rec["market_summary"]]) + " |", ""]
    lines += _execution_priority_lines(rec)
    lines += ["", "## 2. City push plan", _reading(rec["readings"]["city_portfolio"]), ""]
    city_constraint_note = _constraint_note(rec, {"city_product"})
    if city_constraint_note:
        lines += [city_constraint_note, ""]
    for rank, city in enumerate(_ordered_cities(rec), 1):
        cluster = f" (readiness cluster: {city['cluster']})" if city.get("cluster") else ""
        lines.append(f"{rank}. **{city['city']}**{cluster} — **{city['role']} [DERIVED]**: "
                     f"{_md(city['product_angle'])} [AI REC]. {_md(city['play'])} [AI REC].")

    lines += ["", "## 3. Page module configuration",
              _reading(rec["readings"]["modules"]), ""]
    content_constraint_note = _constraint_note(rec, {"content"})
    if content_constraint_note:
        lines += [content_constraint_note, ""]
    modules = _unique_resources_in_priority(rec, "modules")
    module_priorities = {item["id"]: item for item in rec["priority_plan"]["modules"]}
    for i, item in enumerate(modules, 1):
        status = "Conditional - pending benchmark confirmation" if item["conditional"] else "Selected"
        priority = module_priorities.get(item["id"], {})
        lines.append(f"{i}. **{item['id']}** — {status}. {_md(priority.get('decision'))} "
                     f"{_md(priority.get('reason'))} [AI REC]")
    if not modules: lines.append("No module committed; PM review required.")

    lines += ["", "## 4. CRM plan", _reading(rec["readings"]["crm"]), "",
              f"- **Objective:** {_md(rec['crm']['objective'])} [AI REC]",
              f"- **Rationale:** {_md(rec['crm']['rationale'])} [AI REC]",
              f"- **Decision basis:** {_format_basis(rec['crm']['evidence_basis'])}", "",
              "**Audience segments [ASSUMPTION]**"]
    crm_constraint_note = _constraint_note(rec, {"crm"})
    if crm_constraint_note:
        lines += [crm_constraint_note, ""]
    lines += [f"- **{_md(segment['name'])}**"
              + (f" ({_md(segment['window'])})" if segment.get("window") else "")
              + f": {_md(segment['reason'])} [ASSUMPTION]"
              for segment in rec["crm"]["segments"]] or ["- CRM audience plan incomplete."]
    lines += ["", "**Campaign cadence**", "",
              "| Week | Objective | Audience | Channel | Action | Gate | Decision basis |",
              "|---|---|---|---|---|---|---|"]
    for plan in rec["crm"]["weekly_plan"]:
        channels = ", ".join(plan["channel_ids"]) or "Explicit hold"
        lines.append("| " + " | ".join(_md(x) for x in [plan["week"], plan["objective"],
                     plan["audience"], channels, plan["action"], plan["gate"],
                     _format_basis(plan["evidence_basis"])]) + " |")
    if rec["crm"]["push_copy"]:
        lines += ["", "**App Push copy [AI REC]**"] + [f"- {_md(x)}" for x in rec["crm"]["push_copy"]]
    else:
        lines += ["", "**App Push**: No copy selected under the validated channel plan."]
    if rec["crm"]["edm_copy"]:
        lines += ["", "**EDM copy [AI REC]**"] + [f"- {_md(x)}" for x in rec["crm"]["edm_copy"]]

    lines += ["", "## 5. Asset requests", _reading(rec["readings"]["assets"]), "",
               "| Asset | Priority | Selection rationale |", "|---|---|---|"]
    asset_constraint_note = _constraint_note(rec, {"assets"})
    if asset_constraint_note:
        lines += [asset_constraint_note, ""]
    asset_priorities = {item["id"]: item for item in rec["priority_plan"]["assets"]}
    for item in selected_assets:
        priority_rec = asset_priorities.get(item["id"], {})
        rationale = " ".join(filter(None, (_clean(priority_rec.get("decision")),
                                             _clean(priority_rec.get("reason")))))
        if item["conditional"]:
            rationale = (rationale + " Source eligibility requires confirmation before use.").strip()
        lines.append(f"| {_md(item['id'])} | {_md(item.get('priority'))} | "
                     f"{_md(rationale)} |")

    lines += ["", "## 6. Localization checklist", _reading(rec["readings"]["localization"]), ""]
    localization_constraint_note = _constraint_note(rec, {"localization"})
    if localization_constraint_note:
        lines += [localization_constraint_note, ""]
    lines += [f"- [ ] {_md(market_row.get('Localization Need'))} [FACT - table B]",
              "- [ ] Regional team reviews language, imagery and CTA before launch [NEEDS CONFIRMATION]", "",
              "## 7. Market-level NEEDS CONFIRMATION list",
              "Market IDs below are local execution tasks; campaign IDs are referenced as blockers and are not duplicated.", "",
              "| Local ID | Task | Owner | Status |", "|---|---|---|---|"]
    relevant = _relevant_flags(flags, rec)
    for i, flag in enumerate(relevant, 1):
        cid = _flag_ref(flag)
        lines.append(f"| {code}-{i} | {_md(flag.get('detail'))} | {_owner(flag)} | "
                     f"Blocked by {cid} |")
    crm_id = len(relevant) + 1
    lines.append(f"| {code}-{crm_id} | CRM audience windows and suppression logic | CRM Team | Needs confirmation |")

    lines += ["", "## 8. Launch checklist (market level)",
               "| Checklist item | Owner | Why it needs confirmation | Blocking ID |",
               "|---|---|---|---|"]
    for flag in relevant:
        lines.append("| " + " | ".join(_md(x) for x in [
            _flag_label(flag), _owner(flag), _flag_confirmation_reason(flag),
            _clean(flag.get("_id")) or "—",
        ]) + " |")

    segments = [f"{_clean(x.get('name'))}: {_clean(x.get('window'))}"
                for x in rec["crm"].get("segments", []) if isinstance(x, dict)]
    segment_reason = ("Audience definitions and windows are model assumptions: "
                      + "; ".join(segments) + " [ASSUMPTION]")
    lines.append("| " + " | ".join(_md(x) for x in [
        "Confirm CRM audience definitions and windows", "CRM Team", segment_reason, "—",
    ]) + " |")

    selected_modules = ", ".join(
        item["id"] for item in _unique_resources_in_priority(rec, "modules")
    )
    if selected_modules:
        lines.append("| " + " | ".join(_md(x) for x in [
            "Implement selected page modules", "UED / Design",
            f"Selected modules ({selected_modules}) are AI recommendations; implementation evidence is not present in the uploaded data [AI REC]",
            "—",
        ]) + " |")

    if selected_assets:
        asset_names = ", ".join(f"{item['id']} [{item.get('priority')}]" for item in selected_assets)
        lines.append("| " + " | ".join(_md(x) for x in [
            "Produce selected creative assets", "UED / Design",
            f"Selected assets ({asset_names}) are AI recommendations; production evidence is not present in the uploaded data [AI REC]",
            "—",
        ]) + " |")

    localization_need = _clean(market_row.get("Localization Need"))
    lines.append("| " + " | ".join(_md(x) for x in [
        "Approve market localization", "Regional Teams",
        f"Localization need = {localization_need} [FACT - table B]; regional approval is required before launch [NEEDS CONFIRMATION]",
        "—",
    ]) + " |")
    lines.append("| Final market approval | Campaign Ops PM | The workflow requires final human approval before launch [NEEDS CONFIRMATION] | — |")
    if upstream:
        relevant_ids = {flag.get("_id") for flag in relevant}
        relevant_upstream = "\n".join(
            line for line in upstream.splitlines()
            if any(re.search(rf"\b{re.escape(cid)}\b", line) for cid in relevant_ids if cid)
        )
        if relevant_upstream:
            lines += ["", "## Human-review decision addendum", relevant_upstream]
    lines += ["", "## Appendix: derived detail (audit)", scoring.scores_md(
        [r for r in scoring.market_scores(tables) if r["market"].lower() == market.lower()]),
        "", scoring.roles_md(tables, [market])]
    return "\n".join(lines)
