"""
Prompt templates. Deliberately campaign-agnostic:
no destination name appears anywhere - only field references and rules.
The same prompts serve Go China, Go Japan, or Monthly Super Destination.
"""
from .schema import FIELD_DICTIONARY, DECISION_RULES

SYSTEM = """You are a Trip.com destination-campaign operations copilot for a global travel platform.
You turn structured campaign input data into actionable, meeting-ready operational documents.
You are an assistant, not the decision maker: the Campaign Ops PM approves everything.

""" + FIELD_DICTIONARY + "\n" + DECISION_RULES


MARKET_RECOMMENDATION_JSON = """Analyze ONE market using only its filtered data package below.
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

Evidence catalog (IDs and immutable values):
{evidence_catalog}

Filtered data package:
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

GLOBAL_BRIEF = """Using ONLY the data below, produce the campaign-level STRATEGY BRIEF in English, markdown format.

Universal section pattern: every numbered section OPENS with a 1-2 sentence operational reading tagged [AI REC] - what this data means for the campaign and what action it supports - followed by the supporting table or list. Do not name an owner in the reading; ownership belongs in dependency and checklist tables. A section that only lists data is incomplete.

1. **Campaign overview** - facts only (objective, duration, scope), closing with one sentence naming the core tension the campaign must solve.
2. **Decision logic & market tiering** - reading first (where the investment goes and why), then reproduce verbatim the scoring table computed by this prototype [DERIVED] (state that scores come from the prototype's configurable rules, NOT the source data), then the P0/P1/P2 table with one-line tagged rationale per market. Qualitative notes sit beside, never inside, the scores.
3. **Market x city summary** - this is the management scan, NOT the detailed execution matrix. Open with 2-3 sentences of cross-market insight, then output EXACTLY ONE row per market with these columns: Market | Convert now [DERIVED] | Conditional conversion [DERIVED] | Package only [DERIVED] | Content only [DERIVED] | Needs data [DERIVED] | Immediate next action [AI REC]. Group all cities for the same market into the appropriate cell as a comma-separated list; use an em dash when empty. Never output one row per city here and do not repeat role definitions or readiness calculations. Map roles mechanically: Conversion -> Convert now; Conditional Conversion -> Conditional conversion; Package -> Package only; Content -> Content only; NEEDS DATA -> Needs data. Put confirmation IDs beside affected cities when supplied. "Immediate next action" is the only model-judgment column. Detailed market x city execution belongs in section 9; full derivations belong in section 11.
4. **Product focus by market** - reading first (the campaign's product story across markets and where sourcing must intervene), then per-market table: lead lines / secondary (bundle) / weak - avoid or wrap, tagged, with sourcing dependencies noted.
5. **Channel and CRM strategy** - reading first (what the eligibility pattern implies - e.g. which markets lack deep-communication channels and what compensates), then the per-market plan strictly inside the eligibility classification (eligible / ambiguous-needs-confirmation / not eligible). Never assign a channel outside those lists.
6. **Resource allocation notes** - reading first (the binding constraint and the trade-off being made), then where limited content/design capacity goes.
7. **Risks and dependencies** - reading first (the single failure mode most likely to sink the campaign), then the list with an owner per dependency.
8. **NEEDS CONFIRMATION list** - one sentence naming which unconfirmed item blocks the most value, then the table: ID | issue | source | suggested handling | owner. IDs are C-1, C-2... This list gates downstream generation.
9. **Campaign recommendation matrix** - this is a constrained recommendation layer, not a fact-reconstruction task. Use the CODE-LOCKED decision contract in the data package. Write exactly one row per market x interest city: Market | City priority | City | Locked role | Product / angle | Page modules | Channels | Creative assets (include source Priority beside every selected asset) | Constraint / dependency | Play. Copy Market, City, role, tier and asset Priority exactly. Choose only named modules and ELIGIBLE channels/assets. AMBIGUOUS modules/channels/assets must say "Conditional - pending owner confirmation" in the same cell. A NEEDS DATA city must show "No committed activation - readiness data required" and no committed channel/asset. Product angle, ordering, eligible subset, dependency framing and Play are [AI REC]. Page modules and creative assets are different dimensions and must never be mixed.
10. **Launch checklist (campaign level)** - use exactly four columns: Checklist item | Owner | Why it needs confirmation | Blocking ID. The reason must come from a source fact, a code-derived conflict, an explicitly tagged assumption, or the human-review workflow. Never infer or invent execution status.
11. **Appendix: derived city-role detail (audit)** - the 3-line role definitions plus the full pre-computed roles with reasons, reproduced as provided.

Data package:

{context}
"""

MARKET_PACK = """Using ONLY the data below, produce the MARKET EXECUTION PACK for the target market, in English, markdown format.

Universal section pattern: every numbered section OPENS with a 1-2 sentence operational reading tagged [AI REC] - what the data means for this market and what action it supports - then the supporting structure. Do not name an owner in the reading; ownership belongs in dependency and checklist tables. Never output a bare list without its reading.

1. **Market positioning & decision-chain summary** - first write one positioning paragraph grounded in barrier + demand data. Then add a compact subsection named **Decision chain summary** with EXACTLY ONE data row and these columns: Market | City / readiness cluster | Product focus | Channel choice | Asset choice | Stakeholder constraint | Recommended play. This row must visibly express the reusable abstraction Market x City / City Cluster x Product x Channel x Asset x Stakeholder Constraint. In the City / readiness cluster cell, list only this market's interest cities with their pre-computed roles [DERIVED]; mention a readiness cluster in parentheses only when it differs from the interest city, and never promote an unsearched cluster member. Product focus, the selected eligible subset of channels/assets, and Recommended play are [AI REC] grounded in tables C/E/G. An AMBIGUOUS channel or asset may appear only as "Conditional - pending owner confirmation"; never select a NOT ELIGIBLE item. Stakeholder constraint must come from table H or an upstream human-review decision and retain its [FACT] or [NEEDS CONFIRMATION] status. This is a summary only; later sections provide the execution detail.
2. **City push plan** - reading first (the shape of the city portfolio: where conversion comes from, what waits on confirmation), then the ordered list with per-city rationale using the pre-computed roles [DERIVED].
3. **Page module configuration** - reading first (what the page must accomplish for THIS market's stated barrier), then the ordered module list; each top module states which Main User Barrier it addresses; note dropped or conditional modules and why.
4. **CRM plan** - reading first (the CRM job here - nurture vs convert - and the cadence logic derived from lead time), then: audience segments with every recency window tagged [ASSUMPTION] (include ringfencing/suppression), and a cadence containing every Campaign Week 1 through the final campaign week. Write 2 push copy examples (localization language per data, with English gloss) ONLY when App Push is ELIGIBLE. If App Push is AMBIGUOUS or NOT ELIGIBLE, state its status and generate no push copy. EDM: only if EDM is ELIGIBLE; if AMBIGUOUS, treat it as pending and write no copy; if not eligible, state "EDM not eligible based on current input data" and write none.
5. **Asset requests** - reading first (the smallest asset set that serves the plan, and what was deliberately NOT requested to protect design capacity), then the table - only assets from this market's eligible/ambiguous lists, with priority and localization notes.
6. **Localization checklist** - one sentence naming the highest-risk localization failure for this market, then the checkbox list from the Localization Need data.
7. **Market-level NEEDS CONFIRMATION list** - one sentence naming the biggest blocker, then the table with owner. IDs use the market's 2-letter code: <CODE>-1, <CODE>-2...; references to campaign-level items use their C-N IDs.
8. **Launch checklist (market level)** - use exactly four columns: Checklist item | Owner | Why it needs confirmation | Blocking ID. Include only this market's relevant C-IDs plus explicitly tagged assumptions and human-review gates. Never infer or invent execution status.

Tag every statement. Respect upstream human-review decisions: execute RESOLVED items and keep UNRESOLVED / DEFERRED items blocked.

Data package:

{context}
"""
