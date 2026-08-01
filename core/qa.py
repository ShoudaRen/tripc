"""
Deterministic post-generation lint.

Prompt rules are guidance; models can still violate them. This layer catches
known failure modes in generated text with code - the same philosophy as the
input pre-check: code enforces hard rules, the model does judgment, humans decide.
"""
import re

ESCALATION_TERMS = [
    "payment security", "secure payment", "secure payments", "verified payment",
    "verified payments", "security badge", "security badges", "payment protection",
]

ALLOWED_STATUS_HINT = "Drafted / Pending validation / Blocked by #N / Needs confirmation"

SCRATCH_PATTERNS = [r"\bCorrection[:\s]", r"\bLet me re", r"\bWait[,:]", r"\brevised answer\b",
                    r"\bRe-?evaluat(ion|ing)\b", r"\bI will (include|now|add)\b",
                    r"\bOn second thought\b", r"\bupon reflection\b", r"\bActually[,:]"]

INVENTED_MECHANICS = [
    "dynamic pricing", "early bird", "price lock", "limited availability",
    "limited seats", "seasonal rates", "save on attractions",
]

UNSUPPORTED_AVAILABILITY = [
    r"\bdirect flights?\b.{0,30}\b(?:are|is)\s+(?:live|available|on sale)",
    r"\b(?:inventory|supply)\b.{0,20}\b(?:confirmed|available|live)\b",
]


def parse_duration_weeks(campaign_table: dict) -> int | None:
    if not campaign_table:
        return None
    m = re.search(r"(\d+)\s*week", str(campaign_table.get("Campaign Duration", "")), re.I)
    return int(m.group(1)) if m else None


def _source_text(tables: dict | None) -> str:
    if not tables:
        return ""
    values = []
    for table in tables.values():
        rows = [table] if isinstance(table, dict) else (table or [])
        for row in rows:
            values.extend(str(value) for value in row.values())
    return " ".join(values).lower()


def lint(text: str, duration_weeks: int | None = None,
         tables: dict | None = None) -> list[str]:
    warns = []
    low = text.lower()
    source_low = _source_text(tables)
    for term in ESCALATION_TERMS:
        if term in low and term not in source_low:
            warns.append(f"Wording escalation: '{term}' implies a platform security issue the data "
                         "does not state. Use 'payment familiarity/confidence/method guidance'.")
    if duration_weeks:
        for wk in {int(w) for w in re.findall(r"[Ww]eek\s*(\d+)", text)}:
            if wk > duration_weeks:
                warns.append(f"Timeline overrun: 'Week {wk}' exceeds the {duration_weeks}-week campaign. "
                             "Delete it or label it 'Post-campaign nurture (out of scope this round)'.")
    for pat in SCRATCH_PATTERNS:
        if re.search(pat, text):
            warns.append(f"Self-correction/scratch text detected (pattern '{pat}') - final documents "
                         "must contain conclusions only, regenerate or edit out.")
    for term in INVENTED_MECHANICS:
        if term in low and term not in source_low:
            warns.append(f"Execution mechanic '{term}' is not in the source data - tag it "
                         "[ASSUMPTION] or use neutral wording ('eligible deals', 'available offers').")
    for pattern in UNSUPPORTED_AVAILABILITY:
        match = re.search(pattern, text, re.I)
        if match and match.group(0).lower() not in source_low:
            warns.append("Unsupported availability claim detected. The input does not prove live "
                         "flight/inventory availability; use neutral demand language or gate it "
                         "behind sourcing confirmation.")
    for line in text.splitlines():
        if "|" in line and re.search(r"\|\s*Ready\s*\|?\s*$", line):
            warns.append(f"Overconfident status 'Ready' in checklist row: '{line.strip()[:80]}...' - "
                         f"allowed statuses: {ALLOWED_STATUS_HINT}.")
    return warns


def lint_campaign_weeks(text: str, duration_weeks: int | None) -> list[str]:
    """Market CRM calendars must cover every in-campaign week exactly by range."""
    if not duration_weeks or "crm plan" not in text.lower():
        return []
    found = {int(w) for w in re.findall(r"Campaign\s+Week\s*(\d+)", text, re.I)}
    expected = set(range(1, duration_weeks + 1))
    missing = sorted(expected - found)
    return ([f"Incomplete CRM calendar: missing Campaign Week(s) {', '.join(map(str, missing))} "
             f"from the {duration_weeks}-week campaign."] if missing else [])


ID_PATTERN = re.compile(r"\b([A-Z]{1,4}-\d{1,3})\b")


def lint_references(text: str) -> list[str]:
    """Dangling and self-referencing IDs. Definition = ID appearing at the start of a
    table row cell; reference = ID inside a 'Blocked by' / 'per' / 'see' phrase."""
    warns = []
    defined = set()
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("|")]
        for c in cells[:3]:
            m = re.fullmatch(r"([A-Z]{1,4}-\d{1,3})", c)
            if m:
                defined.add(m.group(1))
    for line in text.splitlines():
        row_ids = {m.group(1) for c in [x.strip() for x in line.split("|")][:3]
                   for m in [re.fullmatch(r"([A-Z]{1,4}-\d{1,3})", c)] if m}
        for phrase in re.findall(r"(?:Blocked by|per|see)\s+((?:[A-Z]{1,4}-\d{1,3}[,\s]*)+)", line):
            for ref in ID_PATTERN.findall(phrase):
                if ref in row_ids:
                    warns.append(f"Self-blocking reference: row {ref} is 'Blocked by' itself - "
                                 "use 'Needs confirmation' with the owner instead.")
                elif ref not in defined:
                    warns.append(f"Dangling reference: '{ref}' is cited but never defined in this "
                                 "document - fix the ID or add the missing item.")
    return warns


def lint_market_city(text: str, tables: dict) -> list[str]:
    """Table rows whose first cell is a market must not mention cities outside that
    market's interest list (catches cross-market city contamination in matrices)."""
    from .parser import split_list, _clean
    from .scoring import market_code
    b = tables.get("B_Markets") or []
    interest = {}
    for r in b:
        m = _clean(r.get("Market"))
        cities = split_list(r.get("Top City Interest Signals", ""))
        interest[m.lower()] = {c.lower() for c in cities}
        interest[market_code(m).lower()] = interest[m.lower()]
    all_cities = set()
    readiness_clusters = []
    for r in (tables.get("D_Cities") or []):
        cluster = _clean(r.get("City / Cluster")).lower()
        readiness_clusters.append(cluster)
        for part in cluster.split("/"):
            all_cities.add(part.strip().lower())
    for s in interest.values():
        all_cities |= s
    warns = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells:
            continue
        key = cells[0].lower()
        if key not in interest:
            continue
        rest = " ".join(cells[1:]).lower()
        for city in all_cities:
            if city and city in rest and not any(city in ic or ic in city for ic in interest[key]):
                # A non-interest city may legitimately appear inside the exact readiness
                # cluster label; cluster membership is supply metadata, not a recommendation.
                if any(city in cell.lower() and "readiness cluster" in cell.lower()
                       for cell in cells[1:]):
                    continue
                # A summary or dependency cell may cite the complete source cluster
                # (for example Chengdu / Chongqing product depth) without recommending
                # the unsearched cluster member as a destination.
                compact_rest = re.sub(r"\s*/\s*", "/", rest)
                if any(city in cluster and re.sub(r"\s*/\s*", "/", cluster) in compact_rest
                       for cluster in readiness_clusters):
                    continue
                warns.append(f"City outside market slice: row for '{cells[0]}' mentions '{city.title()}' "
                             "which is not in that market's interest list - likely cross-market "
                             "contamination; remove or justify explicitly.")
    return warns


def _section(text: str, title: str) -> str:
    match = re.search(rf"(?ims)^#+[^\n]*{re.escape(title)}[^\n]*$\n(.*?)(?=^#+\s|\Z)", text)
    return match.group(1) if match else ""


def lint_asset_priorities(text: str, tables: dict) -> list[str]:
    """Catch source Priority values copied incorrectly anywhere in an output table."""
    from .parser import _clean
    warns = []
    for row in (tables.get("G_Assets") or []):
        name, expected = _clean(row.get("Asset Type")), _clean(row.get("Priority"))
        if not name or not re.fullmatch(r"P[012]", expected):
            continue
        priority_pattern = re.compile(
            rf"(?<![\w]){re.escape(name)}\s*[\[(](P[012])[\])]", re.I
        )
        for line in text.splitlines():
            seen = {match.upper() for match in priority_pattern.findall(line)}
            if seen and expected.upper() not in seen:
                warns.append(f"Asset priority mismatch: '{name}' is {expected} in table G, "
                             f"but this row says {', '.join(sorted(seen))}.")
    return warns


def lint_recommendation_matrix(text: str, tables: dict) -> list[str]:
    """Validate locked dimensions while preserving the model's strategy freedom."""
    from . import scoring
    section = _section(text, "Campaign recommendation matrix")
    if not section:
        return ["Missing Campaign recommendation matrix section."]
    low = section.lower()
    warns = []
    for market_row in scoring.market_scores(tables):
        market = market_row["market"]
        for city in scoring.city_roles(tables, market):
            matches = [line for line in section.splitlines()
                       if "|" in line and market.lower() in line.lower()
                       and city["city"].lower() in line.lower()]
            if not matches:
                warns.append(f"Matrix coverage missing: no row for {market} x {city['city']}.")
                continue
            row_text = " ".join(matches).lower()
            if city["role"].lower() not in row_text:
                warns.append(f"Matrix role mismatch: {market} x {city['city']} must use locked "
                             f"role '{city['role']}'.")
            if city["role"] == "NEEDS DATA" and not any(
                    phrase in row_text for phrase in ("no committed", "readiness data required")):
                warns.append(f"Unsafe matrix commitment: {market} x {city['city']} is NEEDS DATA "
                             "and must state that no activation is committed.")

        channel_state = scoring.channel_eligibility(tables, market)
        asset_state = scoring.asset_eligibility(tables, market)
        market_lines = "\n".join(line for line in section.splitlines()
                                 if "|" in line and market.lower() in line.lower()).lower()
        for item in channel_state["not_eligible"]:
            name = item.split(" (", 1)[0]
            if name.lower() in market_lines:
                warns.append(f"Matrix channel violation: {market} selects not-eligible '{name}'.")
        for item in asset_state["not_eligible"]:
            name = item.split(" (", 1)[0]
            if name.lower() in market_lines:
                warns.append(f"Matrix asset violation: {market} selects not-eligible '{name}'.")
        for item in channel_state["ambiguous"] + asset_state["ambiguous"]:
            name = item.split(" (", 1)[0]
            for line in section.splitlines():
                if ("|" in line and market.lower() in line.lower()
                        and name.lower() in line.lower()
                        and not any(k in line.lower() for k in
                                    ("conditional", "pending", "confirm", "blocked"))):
                    warns.append(f"Matrix ambiguity violation: {market} uses '{name}' without an "
                                 "in-cell pending/confirmation condition.")
    return warns


def lint_ambiguous_push_copy(text: str, tables: dict, market: str | None) -> list[str]:
    if not market:
        return []
    from . import scoring
    ambiguous = {item.split(" (", 1)[0].lower()
                 for item in scoring.channel_eligibility(tables, market)["ambiguous"]}
    if "app push" not in ambiguous:
        return []
    crm = _section(text, "CRM plan").lower()
    if re.search(r"push\s+copy|copy\s+example|example\s+\d+", crm):
        return [f"Ambiguous-channel copy: App Push eligibility for {market} is unconfirmed, "
                "so the CRM plan must not generate push copy."]
    return []


def lint_ambiguous_modules(text: str, tables: dict) -> list[str]:
    from .parser import _clean, _is_missing
    matrix = _section(text, "Campaign recommendation matrix")
    if not matrix:
        return []
    warns = []
    for row in (tables.get("F_Modules") or []):
        name = _clean(row.get("Module"))
        if not name or not _is_missing(row.get("Conversion Contribution")):
            continue
        for line in matrix.splitlines():
            if ("|" in line and name.lower() in line.lower()
                    and not any(k in line.lower() for k in
                                ("conditional", "pending", "confirm", "blocked"))):
                warns.append(f"Matrix module ambiguity: '{name}' has missing/TBD Conversion "
                             "Contribution and must be conditional in the same row.")
    return warns


def lint_required_ids(text: str, required_ids: list[str] | None) -> list[str]:
    if not required_ids:
        return []
    defined = set()
    for line in text.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(r"[A-Z]{1,4}-\d{1,3}", cells[0]):
            defined.add(cells[0])
    return [f"Required confirmation ID missing from the confirmation table: {cid}."
            for cid in required_ids if cid not in defined]


def lint_all(text: str, duration_weeks: int | None = None, tables: dict | None = None,
             market: str | None = None,
             required_ids: list[str] | None = None) -> list[str]:
    warns = lint(text, duration_weeks, tables) + lint_references(text)
    warns += lint_campaign_weeks(text, duration_weeks)
    warns += lint_required_ids(text, required_ids)
    if tables:
        warns += lint_market_city(text, tables)
        warns += lint_asset_priorities(text, tables)
        warns += lint_ambiguous_push_copy(text, tables, market)
        if not market:
            warns += lint_recommendation_matrix(text, tables)
            warns += lint_ambiguous_modules(text, tables)
    return warns
