"""
Reusable data schema for destination campaigns.

Campaign-agnostic: nothing here references China, Japan or any specific
destination. Defines (1) the input template, (2) the field dictionary
injected into every prompt, (3) validation rules.

Reuse for Go Japan / Go Thailand / Monthly Super Destination = fill the same
template with different data. No code change needed.
"""

TABLE_SPECS = {
    "A_Campaign": {
        "title": "Campaign basic information",
        "dimension": None,
        "key_value": True,
        "required": [
            "Campaign Name", "Campaign Objective", "Campaign Duration",
            "Target Markets", "Key City Focus", "Product Scope",
        ],
    },
    "B_Markets": {
        "title": "Market demand signals",
        "dimension": "market",
        "columns": [
            "Market", "Search UV Index", "Search Growth vs Baseline",
            "Booking Lead Time", "Top City Interest Signals",
            "Main User Barrier", "Localization Need",
        ],
        "required": ["Market", "Search UV Index", "Top City Interest Signals"],
    },
    "C_Products": {
        "title": "Product performance by market",
        "dimension": "market",
        "columns": [
            "Market", "Flight Demand", "Hotel Conversion",
            "Attractions & Tickets Interest", "Tours Interest",
            "Train / Transfer Interest", "Suggested Product Tension",
        ],
        "required": ["Market"],
    },
    "D_Cities": {
        "title": "Destination city & product readiness",
        "dimension": "city",
        "columns": [
            "City / Cluster", "Destination Role", "Hotel Supply Readiness",
            "Flight Route Readiness", "Attractions / Tours Readiness",
            "Train / Transfer Readiness", "Campaign Risk",
        ],
        "required": ["City / Cluster", "Destination Role"],
    },
    "E_Channels": {
        "title": "Traffic channel performance",
        "dimension": "market",
        "coverage_column": "Market Coverage",
        "columns": [
            "Channel", "Market Coverage", "Estimated Reach", "CTR Index",
            "Conversion Quality", "Resource Owner", "Notes",
        ],
        "required": ["Channel", "Market Coverage", "Resource Owner"],
    },
    "F_Modules": {
        "title": "Campaign page module library",
        "dimension": None,
        "columns": [
            "Module", "Description", "CTR Index", "Conversion Contribution",
            "Design Complexity", "Notes",
        ],
        "required": ["Module"],
    },
    "G_Assets": {
        "title": "Creative asset requirements",
        "dimension": "market",
        "coverage_column": "Required Markets",
        "columns": [
            "Asset Type", "Usage", "Required Markets", "Localization Level",
            "Priority", "Notes",
        ],
        "required": ["Asset Type", "Required Markets", "Priority"],
    },
    "H_Constraints": {
        "title": "Stakeholder inputs and constraints",
        "dimension": None,
        "columns": ["Stakeholder", "Input / Requirement", "Impact on AI Workflow"],
        "required": ["Stakeholder", "Input / Requirement"],
    },
}

# Workbook contract. Excel labels are validated at ingestion and then converted
# to the canonical TABLE_SPECS names above. Business logic must only read the
# canonical names; it must never depend on destination-specific spreadsheet text.
SCHEMA_VERSION = "1.0"

# A campaign and its market rows are the minimum required to run the workflow.
# Other missing sheets remain visible data gaps, but do not make the rows that are
# present impossible to parse.
ANALYSIS_REQUIRED_TABLES = {"A_Campaign", "B_Markets"}

# Approved header aliases are deliberately narrow. Position identifies the target
# field, while the header/alias check protects against shifted or unrelated data.
COLUMN_ALIASES = {
    "B_Markets": {
        "Search UV Index": {
            "China Search UV Index",
            "Japan Search UV Index",
            "Destination Search UV Index",
        },
    },
    "F_Modules": {
        "Notes": {"Candidate Should Consider"},
    },
}

# Destination-specific variants such as "Thailand Search UV Index" are safe at
# this exact position and normalize to the same internal field.
COLUMN_ALIAS_PATTERNS = {
    "B_Markets": {
        "Search UV Index": [r"^.+\s+search\s+uv\s+index$"],
    },
}

ENUM_COLUMNS = {
    "Priority": {"P0", "P1", "P2"},
}

MISSING_VALUES = {"", "tbd", "n/a", "na", "none", "-", "?", "unknown"}

LEVEL_VALUES = {
    "high", "medium-high", "medium", "low-medium", "medium-low", "low",
    "indirect", "case by case",
}

LEVEL_COLUMNS = {
    "Hotel Supply Readiness", "Flight Route Readiness",
    "Attractions / Tours Readiness", "Train / Transfer Readiness",
    "Flight Demand", "Hotel Conversion", "Attractions & Tickets Interest",
    "Tours Interest", "Train / Transfer Interest",
    "Estimated Reach", "CTR Index", "Conversion Quality",
    "Conversion Contribution", "Design Complexity", "Localization Level",
}

FIELD_DICTIONARY = """\
## Field dictionary (how to read the data)
- Search UV Index: destination search interest index, 0-100, comparable ACROSS markets. Higher = stronger demand.
- Search Growth vs Baseline: momentum signal. High growth + mid index can outrank a flat high index.
- Booking Lead Time: typical days from search to booking. Short (<14d) = campaign window can capture full conversion; long (>21d) = front-load inspiration, conversion may land after campaign ends.
- Top City Interest Signals: cities this market's users actually search for, in rank order. Drives market x city matching.
- Main User Barrier: the #1 friction to solve in messaging for this market.
- Localization Need: required language + the content angle that resonates in this market.
- Readiness (Hotel / Flight / Attractions / Train-Transfer): supply strength ON OUR PLATFORM for that city (sellable inventory, route coverage, bookable transfers). NOT a statement about the city itself. Low readiness = pushing traffic there risks wasted clicks and poor UX.
- Destination Role: the strategic job of the city in the campaign (gateway / culture anchor / short-trip / nature etc.).
- Campaign Risk: known failure mode from previous rounds; treat as a hard warning.
- Estimated Reach / CTR Index / Conversion Quality: relative channel indicators for cross-channel comparison only, not absolute numbers.
- Market Coverage / Required Markets: which markets a channel or asset applies to. A market NOT listed cannot use that channel/asset.
- Resource Owner: the team that must approve use of that channel; a dependency, not a formality.
- Module CTR Index / Conversion Contribution: past page-module performance; use to order modules per market intent.
- Priority (P0/P1/P2): asset production priority. Design capacity is limited: request P0/P1 only unless strongly justified.
"""

DECISION_RULES = """\
## Decision rules (apply strictly)

### 0. Pre-computed decision results (you do NOT do arithmetic)
- The data package contains a scoring table and city roles computed BY CODE using the standard below. Use them AS-IS: reproduce the table, interpret it, caveat it. Never recompute, never alter a number or tier. If qualitative signals seem at odds with a computed result, raise it as a tagged discussion point [AI REC] - do not change the result.

### Quantification standard (for reference - executed in code)
- Level mapping: High=3, Medium-High=2.5, Medium=2, Low-Medium=1.5, Low=1.
- UV_norm = market UV index / highest UV index among markets. Growth_norm = market growth / highest growth.
- Product_norm = weighted mix of ALL product lines (never the single best line - one High cannot mask weak conversion lines): default weights Hotel 0.30, Flight 0.25, Attractions 0.20, Tours 0.15, Train/Transfer 0.10 (conversion-objective defaults; adjust if the campaign objective differs). Product_norm = sum(weight_i * level_i) / 3.
- Market score = 0.40*UV_norm + 0.25*Growth_norm + 0.35*Product_norm.
- Tiers: score >= 0.75 -> P0; 0.60-0.74 -> P1; < 0.60 -> P2 nurture. Safety override: if hotel AND flight signals are both <= Low-Medium, cap at P2 regardless of score.
- Qualitative factors (user barrier, lead time, city supply) do NOT silently adjust scores; discuss them as tagged notes next to the tier table.
- These weights and thresholds are CONFIGURABLE DEFAULTS, not truths: state this explicitly and invite the PM to adjust. The brief MUST include the full scoring table (inputs, normalized values, score, tier) so tiering is auditable.

### 1. City and cluster mapping
- Interest City (table B) and Readiness Cluster (table D) are two different layers. Supply data grouped as a cluster (e.g. "A / B") never implies users are interested in every member city. Recommend ONLY the searched city; other cluster members may appear solely as "same-cluster extension candidates", never as primary recommendations.
- A Conversion city whose Campaign Risk mentions supply/product depth is a CONDITIONAL Conversion city: keep it in the push plan but add a sourcing confirmation item to the needs-confirmation list.

### City role rules (computed in code, presented for reference)
- The output MUST open the market x city section with a 3-line definition block of the roles below (so readers never see an undefined "Rule 1"), then state each city's role as a result. NEVER show scratch work, threshold re-checks, or self-corrections in the final document - conclusions only.
- CONVERSION city: in this market's Top City Interest AND Hotel readiness >= 2 AND Flight readiness >= 2.
- PACKAGE city: in interest list, Attractions/Tours readiness >= 2.5, but Hotel or Flight < 2 -> packaged-tour angle only, flag supply confirmation.
- CONTENT city: in interest list but fails both above -> inspiration/content role only.
- Not in interest list -> exclude from this market (may appear as add-on mention only).
- Also check: relevant product interest (table C) supports the city role; note channel capacity and stakeholder constraints where they bite.

### 2. Fact hygiene
- [FACT - table X] statements must restate data values verbatim or near-verbatim. Any inference (e.g. "lead time fits the campaign window") is [ASSUMPTION] with its basis stated.
- Never conflate user-side demand fields (Flight Demand, Train/Transfer Interest - table C) with city-side supply readiness (table D). Name the exact field you are citing.
- Never escalate wording beyond the data. Example: "needs confidence on payment" must NOT become "payment security" or "verified payments" - that implies a platform safety problem the data does not state. Use "payment familiarity/confidence".

### 3. Channel eligibility
- Coverage "All markets" -> usable. Explicit market list -> usable only for listed markets.
- Two opposite cases, never confuse them:
  (a) Explicit market list that does NOT include this market (e.g. "HK, SG, MY" for a KR pack) -> hard exclusion: state "Not eligible based on current input data", produce no copy, no hedging like "if confirmed".
  (b) Coverage "Selected markets" -> UNKNOWN eligibility: [NEEDS CONFIRMATION] with the resource owner named. Never write "not eligible" here - the data does not exclude it - and never present it as committed.
- Never generate copy for a channel and then retract it later in the same document. Decide eligibility FIRST, then write only what is eligible.

### 4. CRM discipline
- Attribution rule, state it in this order: (1) bookings placed in ANY week of the campaign (Week 1 through the final week) all count as campaign conversions; (2) in particular, a final-week booking still counts even when the travel date falls after the campaign ends - Booking Lead Time is the search-to-travel gap and never moves the attribution boundary. Never label an in-duration week "post-campaign". Post-campaign nurture/measurement starts only AFTER the final week, under a separate heading "Post-campaign (out of scope this round)".
- ALL recency windows and thresholds (7d/14d/90d etc.) are illustrative: tag EVERY one [ASSUMPTION], and always add a needs-confirmation item "CRM team to calibrate audience window definitions".
- Express timing as "Campaign Week 1/2/3/4" (relative to launch), never as T-N or ambiguous relative dates.
- EDM/channel eligibility: if a channel does not appear in this market's available-channels slice, state plainly "Not eligible based on current input data (coverage per channel table)" and produce NO copy for it. Do not hedge with "if available".

### 5. Conditional recommendations
- Never hard-"drop" a module/asset whose value depends on unconfirmed supply (e.g. KA/partner supply). Output "Conditional - include if X is confirmed", and add X to the confirmation list with an owner.

### 6. Page modules
- Module ORDER and module CONTENT both derive from this market's data: order follows the product demand profile (conversion-ready markets get deal modules high; education-needed markets get themed/content modules high). Each top module's content brief must state which Main User Barrier it addresses.
- Never fill a module with generic friction topics (payment, visa, transport how-to) for a market whose stated barrier is something else - repurpose the module to serve the actual barrier or demote it.

### 7. Final-document voice
- Information hierarchy: every section LEADS with the operational takeaway (what the reader should do), then the supporting structure. Mechanism-level rationale (rule values, readiness levels, computation detail) belongs in a final "Appendix: derived detail (audit)" section, never in the body.
- You are writing a finished deliverable for management review, not solving a problem on paper. Complete ALL judgments internally before writing; each conclusion appears exactly once, in its final form.
- The register is declarative and settled: no process narration ("correction", "re-evaluation", "let me", "I will now", "actually"), no revisiting earlier statements, no visible reasoning residue. If a line proves wrong mid-draft, rewrite internally - the reader only ever sees the final state.

### 8. Output hygiene
- Tag taxonomy (use precisely):
  [FACT - table X] = value restated from provided data.
  [DERIVED] = result computed by the quantification standard or city-role rules (scores, tiers, city roles). Not an opinion - but auditable math. ANY reference to a market's tier ("X is P0") or a city's role, anywhere in any document, is [DERIVED] - never [FACT] and never mixed into a [FACT] tag.
  [ASSUMPTION] = your inference or illustrative parameter (recency windows, timing logic), basis stated.
  [AI REC] = judgment call (copy angles, module order, positioning).
  [NEEDS CONFIRMATION] = missing/ambiguous data or business trade-off, with owner.
- Confirmation-item IDs are namespaced so cross-references never collide: campaign-level items are C-1, C-2...; market-level items are <MARKET CODE>-1, <MARKET CODE>-2... (2-letter market code). Every "Blocked by" reference MUST cite an ID that exists in the same document set.
- Launch checklist statuses: ONLY use Drafted / Pending validation / Blocked by <ID> / Needs confirmation. NEVER mark an item "Ready" at generation time - readiness is a human's call after verification. Status must describe the actual state of the thing the row refers to: a generated request or plan is "<X> brief drafted - production pending" / "<X> plan drafted - implementation pending", never "delivered" or "configured".
- Never invent missing values; never silently resolve flagged conflicts.
- Never claim live inventory, live/direct flight availability, a discount, savings, scarcity, limited seats, or seasonal pricing unless that exact evidence exists in the input. Product demand is not proof of sellable supply. Use neutral angle language and a sourcing gate instead.
- Upstream decisions marked RESOLVED are human decisions: execute, do not re-litigate.
- Upstream decisions marked UNRESOLVED / DEFERRED remain blockers: never describe them as confirmed or committed.
"""

# Market alias vocabulary: input data often mixes full names ("Hong Kong")
# with codes ("HK"). Normalization lives here, not in campaign logic.
MARKET_ALIASES = {
    "hong kong": {"hk", "hongkong"},
    "korea": {"kr", "south korea", "korea south"},
    "south korea": {"kr", "korea"},
    "singapore": {"sg"},
    "malaysia": {"my"},
    "thailand": {"th"},
    "taiwan": {"tw"},
    "japan": {"jp"},
    "vietnam": {"vn"},
    "indonesia": {"id"},
    "philippines": {"ph"},
    "united states": {"us", "usa", "u.s.", "u.s.a."},
    "australia": {"au"},
    "france": {"fr"},
    "india": {"in"},
}

# Runtime alias overrides confirmed by the user for the current workbook. The app
# persists these in Streamlit session state and restores them on each rerun.
SESSION_ALIASES: dict[str, set[str]] = {}


def register_alias(market: str, token: str) -> None:
    SESSION_ALIASES.setdefault(market.strip().lower(), set()).add(token.strip().lower())


def clear_session_aliases() -> None:
    SESSION_ALIASES.clear()


def alias_map() -> dict[str, set[str]]:
    """Built-in vocabulary merged with user-confirmed session overrides."""
    merged = {k: set(v) for k, v in MARKET_ALIASES.items()}
    for k, v in SESSION_ALIASES.items():
        merged.setdefault(k, set()).update(v)
    return merged


def suggest_market_alias(token: str, markets: list[str]) -> str | None:
    """Return a unique conservative suggestion such as AUS -> Australia.

    Suggestions are limited to exact aliases, initials, or 2/3-character name
    prefixes. Fuzzy similarity is deliberately avoided because a wrong coverage
    mapping is more damaging than leaving a token unresolved.
    """
    import re

    raw = re.sub(r"[^a-z0-9]", "", token.lower())
    if not raw:
        return None
    matches = []
    aliases = alias_map()
    for market in markets:
        words = re.findall(r"[a-z0-9]+", market.lower())
        compact = "".join(words)
        initials = "".join(word[0] for word in words if word)
        forms = {compact, initials}
        if len(compact) >= 2:
            forms.add(compact[:2])
        if len(compact) >= 3:
            forms.add(compact[:3])
        forms |= {re.sub(r"[^a-z0-9]", "", value)
                  for value in aliases.get(market.lower(), set())}
        if raw in forms:
            matches.append(market)
    return matches[0] if len(matches) == 1 else None


# Scoring configuration - all knobs in one place, adjustable per campaign objective.
SCORING = {
    "level_map": {"high": 3, "medium-high": 2.5, "medium": 2,
                  "low-medium": 1.5, "medium-low": 1.5, "low": 1},
    "dim_weights": {"uv": 0.40, "growth": 0.25, "product": 0.35},
    "product_weights": {  # conversion-objective defaults
        "Hotel Conversion": 0.30, "Flight Demand": 0.25,
        "Attractions & Tickets Interest": 0.20, "Tours Interest": 0.15,
        "Train / Transfer Interest": 0.10,
    },
    "product_abbr": {  # display abbreviations; unknown columns fall back to first word uppercased
        "Hotel Conversion": "HTL", "Flight Demand": "FLT",
        "Attractions & Tickets Interest": "ATT", "Tours Interest": "TOUR",
        "Train / Transfer Interest": "TRANS",
    },
    "tier_thresholds": {"P0": 0.75, "P1": 0.60},   # below P1 -> P2
    "safety_cap_level": 1.5,   # hotel AND flight both <= this -> cap at P2
    "city_conversion_min": 2,  # hotel & flight readiness >= this -> Conversion city
    "city_package_min": 2.5,   # attractions/tours readiness >= this -> Package city
}
