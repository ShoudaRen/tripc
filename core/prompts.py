"""
Prompt templates. Deliberately campaign-agnostic:
no destination name appears anywhere - only field references and rules.
The same prompts serve Go China, Go Japan, or Monthly Super Destination.
"""
from .schema import FIELD_DICTIONARY

STRUCTURED_RULES = """\
## Structured decision rules
- Code owns all source facts, scores, tiers, city roles, eligibility, priorities and IDs. Use them
  exactly as supplied; never recalculate, rename or paraphrase them as new facts.
- The evidence catalog is the only factual source. Cite exact IDs and make recommendations from
  their immutable values; do not invent prices, inventory, discounts, capacity or availability.
  Preserve the source meaning of user barriers; never escalate wording into a stronger claim.
- Keep demand and supply distinct: market/product fields describe user demand or conversion;
  city-readiness fields describe platform fulfilment. A readiness cluster never creates interest
  in an unsearched city.
- Select only resources listed in the decision package. Conditional choices require a supplied
  confirmation ID; NEEDS DATA cities receive no committed resources.
- Treat eligibility and P0/P1/P2 as constraints, then use performance, user friction, journey role,
  localization effort and stakeholder limits to make a real business ranking.
- Every in-campaign week remains inside campaign attribution; booking lead time informs sequencing,
  not the attribution boundary. Numeric audience windows remain explicit assumptions.
- Write for campaign operations: recommend a concrete sequence and explain what the evidence
  changes. Avoid generic summaries, process narration, owners and unsupported certainty.
"""

SYSTEM = """You are a destination-campaign operations copilot for a global travel platform.
You turn structured campaign input data into actionable, meeting-ready operational documents.
You are an assistant, not the decision maker: the Campaign Ops PM approves everything.

""" + FIELD_DICTIONARY + "\n" + STRUCTURED_RULES


MARKET_RECOMMENDATION_JSON = """Analyze ONE market using only its compact evidence and decision package below.
Return ONLY valid JSON. Do not wrap it in markdown and do not repeat locked facts such as role,
cluster, priority or eligibility; code will join those fields later.

Required schema:
{{
  "market": "{market}",
  "readings": {{
    "positioning": {{"recommendation": "action-first recommended positioning", "rationale": "natural business explanation grounded in market evidence", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
    "city_portfolio": {{"recommendation": "how to sequence the locked city roles", "rationale": "natural business explanation for that sequence", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
    "modules": {{"recommendation": "module-order decision", "rationale": "natural explanation grounded in page job and user friction", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
    "crm": {{"recommendation": "CRM job and sequencing", "rationale": "natural explanation grounded in lead time, barrier and eligibility", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
    "assets": {{"recommendation": "smallest sufficient asset approach", "rationale": "natural explanation grounded in creative constraints", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
    "localization": {{"recommendation": "required localization action", "rationale": "natural explanation grounded in localization risk", "evidence_refs": ["all directly supporting exact catalog IDs"]}}
  }},
  "market_summary": "one concise recommended play",
  "immediate_next_action": "single highest-value next action",
  "product_focus": "product focus grounded in table C; do not invent price or inventory",
  "stakeholder_constraints": [
    {{"stakeholder": "exact Stakeholder name from table H", "impact": "how this source constraint changes the plan", "applies_to": ["crm", "localization"]}}
  ],
  "priority_plan": {{
    "cities": [{{"id": "exact supplied interest city", "decision": "what to do at this rank", "reason": "evidence-based reason", "evidence_refs": ["all directly supporting exact catalog IDs"]}}],
    "products": [{{"id": "exact table C product field name", "decision": "lead/support/defer decision", "reason": "evidence-based reason", "evidence_refs": ["all directly supporting exact catalog IDs"]}}],
    "channels": [{{"id": "exact channel selected in cities", "decision": "role in the journey", "reason": "evidence-based reason", "evidence_refs": ["all directly supporting exact catalog IDs"]}}],
    "modules": [{{"id": "exact module selected in cities", "decision": "page job at this position", "reason": "evidence-based reason", "evidence_refs": ["all directly supporting exact catalog IDs"]}}],
    "assets": [{{"id": "exact asset selected in cities", "decision": "production role", "reason": "evidence-based reason", "evidence_refs": ["all directly supporting exact catalog IDs"]}}]
  }},
  "crm": {{
    "objective": "specific nurture/convert objective",
    "rationale": "why this objective fits the market evidence",
    "evidence_refs": ["all directly supporting exact catalog IDs including booking lead time or main user barrier"],
    "segments": [{{"name": "audience definition", "window": "illustrative N-day window or non-numeric rule", "reason": "role in the journey", "assumption": true}}],
    "weekly_plan": [{{"week": 1, "objective": "stage objective", "audience": "target segment", "channel_ids": ["exact selected channel id"], "action": "concrete action", "gate": "confirmation ID or empty", "evidence_refs": ["all directly supporting exact catalog IDs, including every used channel and mentioned city role"]}}],
    "push_copy": [],
    "edm_copy": []
  }},
  "cities": [
    {{
      "city": "exact interest city name supplied by code",
      "product_angle": "AI recommendation",
      "modules": [{{"id": "exact module name", "justification": "why selected"}}],
      "channels": [{{"id": "exact eligible/ambiguous channel name", "justification": "why selected"}}],
      "assets": [{{"id": "exact eligible/ambiguous asset name", "justification": "required for every P2 asset"}}],
      "play": "AI recommendation"
    }}
  ]
}}

Decision readings must be compact, substantive and natural: lead with the recommended action, then
explain the business rationale in one or two fluent sentences. Do not use mechanical transitions such
as "Therefore" or "This maximizes", do not name an owner, do not restate the table, and do not use
generic text such as "execute within the rules". Recommendation + rationale should normally total
40-70 words and explain what the evidence changes operationally.
Evidence refs are internal grounding controls: select only exact IDs from the catalog below. Do not
invent IDs. Include every directly supporting ID needed by the decision; there is no numeric upper
limit, but do not add unrelated evidence.

Return every table H constraint that materially affects this market; there is no fixed number. Use
only exact Stakeholder names and source meanings from table H. `applies_to` may contain any relevant
values from city_product, crm, assets, content, localization and campaign. Do not invent a numeric
capacity or frequency limit when table H supplies only a qualitative constraint; explain the effect
qualitatively and leave the precise limit for human confirmation.

The order of every priority_plan array is the recommended execution order (first item = first
priority). Rank every supplied interest city and every supplied table C product performance signal
(Flight, Hotel, Attractions/Tickets, Tours and Train/Transfer; Suggested Product Tension is supporting
evidence, not a product). For channels,
modules and assets, rank exactly the unique resources selected across the city rows: do not add an
unselected item and do not omit a selected item. Each priority item must explain a real trade-off,
not merely say that it is first or eligible. Use D/DERIVED evidence for cities, C for products, E for
channels, F for modules and G for assets. Treat source Notes, reach, CTR, conversion contribution,
complexity, localization level and risk as decision evidence where present. Eligibility and P0/P1/P2
are constraints, not a complete business ranking.
City priority decisions must preserve the locked role: Conditional Conversion explicitly requires a
confirmation/gate; Package explicitly uses a packaged-tour approach; Content explicitly remains
content/inspiration only; NEEDS DATA explicitly holds activation and requests readiness data.

Campaign duration requires exactly these week numbers: {weeks}. Return exactly one weekly_plan
object for every listed week. Every week needs a distinct objective, audience and concrete action.
Use an empty channel_ids list only for an explicit hold; then action must explain the hold and gate
must contain the relevant confirmation ID. Never leave a week for "PM to calibrate".

Include every supplied interest city exactly once. For NEEDS DATA cities, return the city but no
modules, channels or assets. Select resources only from the supplied eligible/ambiguous lists.
Ambiguous selections remain conditional. Eligible does not mean requested: prefer P0/P1 assets;
select a P2 asset only when its non-empty justification explains why it is materially necessary.
Do not claim live inventory, prices, discounts, savings, scarcity or certification without source evidence.
Generate push_copy only if App Push is explicitly ELIGIBLE and edm_copy only if EDM is explicitly ELIGIBLE.

Evidence catalog (the only factual input; IDs and immutable values):
{evidence_catalog}

Compact decision package (legal choices and confirmation gates; factual values are not repeated):
{context}
"""


GLOBAL_SYNTHESIS_JSON = """You are given code-validated, structured recommendations for every market.
Return ONLY valid JSON with exactly these keys. Do not reproduce tables and do not change scores,
tiers, city roles, clusters, resource eligibility, priorities or confirmation IDs.

{{
  "overview_reading": {{"recommendation": "campaign-level choice", "rationale": "natural explanation grounded in the cross-market evidence pattern", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
  "core_tension": "single core tension",
  "tiering_reading": {{"recommendation": "investment choice", "rationale": "natural explanation grounded in the tier pattern", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
  "cross_market_insight": {{"recommendation": "shared portfolio action", "rationale": "natural explanation grounded in the validated market-city pattern", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
  "product_reading": {{"recommendation": "product strategy", "rationale": "natural explanation grounded in the product pattern", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
  "channel_reading": {{"recommendation": "channel strategy; never say full activation", "rationale": "natural explanation grounded in explicit eligibility", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
  "resource_reading": {{"recommendation": "allocation trade-off; P0/P1 prioritized and justified P2 allowed", "rationale": "natural explanation grounded in resource constraints", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
  "risk_reading": {{"recommendation": "mitigation for the highest-probability failure mode", "rationale": "natural explanation grounded in the validated dependencies", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
  "launch_reading": {{"recommendation": "human-gated next step", "rationale": "natural explanation grounded in the readiness state", "evidence_refs": ["all directly supporting exact catalog IDs"]}},
  "market_rationales": {{"each exact market name": "one concise rationale"}}
}}

For every reading, make recommendation + rationale specific, fluent and decision-useful in about
40-70 words total. Lead with the action, do not name an owner, and avoid mechanical transitions such
as "Therefore" or "This maximizes". Do not merely restate a table. Do not calculate or state numeric counts;
the code layer owns counts and locked facts.
Use only exact evidence IDs from the catalog. The final report will show their immutable display
values, not the technical IDs.

Use no unsupported price, inventory, discount, savings, scarcity, certification or availability claims.

Global evidence catalog:
{evidence_catalog}

Validated compact package:
{context}
"""


DOC_LEGEND = """## How to read this document

Every statement carries a tag showing where it comes from:

| Tag | Meaning | What you should do with it |
|---|---|---|
| [FACT - table X] | Value taken directly from the input data, traceable to the named table | Trust it (verify against source if needed) |
| [DERIVED] | Computed by the prototype's transparent rules (scores, tiers, city roles); weights and thresholds are configurable defaults | Audit the rule, adjust the config if you disagree |
| [ASSUMPTION] | An inference or illustrative parameter (e.g. audience windows, weight choices) with its basis stated | Calibrate before execution |
| [AI REC] | The model's judgment call (angles, ordering, copy) | Accept, adjust or reject - this is where your expertise applies |
| [NEEDS CONFIRMATION] | Missing/ambiguous data or a business trade-off | Blocked until the named owner confirms |

IDs: **C-N** = campaign-level confirmation items; **<market code>-N** (e.g. HK-1) = market-level items. "Blocked by <ID>" links a launch item to the confirmation gating it.

City roles: **Conversion** = push deals now; **Conditional Conversion** = deals after supply is confirmed; **Package** = packaged-tour angle only; **Content** = inspiration only, no conversion push.

Market tiers: **P0** = conversion push, **P1** = steady investment, **P2** = nurture (content/awareness KPI).

---

"""
