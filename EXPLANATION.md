# Go Campaign Copilot — Explanation Document

*AI Marketing Engineer take-home case · Option D: End-to-end Campaign Ops Workflow*
*Prototype: Streamlit app (`app.py`) · Demo mode works without any API key · Live mode: any OpenAI-compatible or Anthropic API*

---

## 1. Which workflow problem I chose

**The problem: campaign inputs are fragmented across teams, and the decisions that connect them are made in people's heads.**

Market demand sits with regional teams, supply readiness with sourcing, channel capacity with CRM and content, asset priorities with design, and the constraints that bind them all are spoken rather than written. To launch one round of a destination campaign, campaign ops has to hold every one of these in mind at once, per market, and reconcile them into a strategy, a page plan, a CRM plan, an asset request and a launch checklist — repeating the same reasoning next round, for the next destination, from scratch.

Concretely, the reasoning that has to happen is a repeated intersection check: *for this market, which cities do users actually want, which of those can we fulfil, with which products, through which channels we are allowed to use, needing which assets, under whose constraints?* It is mechanical, high-volume and easy to get wrong — and precisely because it is mechanical, most of it does not need a human, while the small residue that does is exactly what gets rushed today.

**So the workflow problem I chose is: turn that intersection reasoning into a reusable, auditable pipeline — and route what genuinely needs judgment to a named human at a gate that blocks progress until it is answered.**

This spans strategy, page planning, CRM, asset briefing, localization and launch discipline, which corresponds to prototype direction D (end-to-end campaign ops workflow). Directions A, B and C are each one segment of the same pipeline; taking the whole of it was deliberate, because the case's core requirement — abstraction — is only really testable when all these outputs must run off one shared data model rather than one hand-tuned prompt each.

## 2. Why this problem matters for campaign ops

Campaign ops today coordinates these inputs manually. Three failure modes are expensive and recurring:

- **Missed cross-table tensions.** 5 markets × 7 city clusters = 35 combinations to check by hand. The costly mistakes live at intersections: a market's users search for a city whose supply cannot fulfil (Korea × Zhangjiajie), a channel plan built on a channel that does not cover that market (EDM × Korea).
- **Undifferentiated execution.** Without per-market logic, the same page order, push cadence and copy angle get reused across markets whose barriers are opposite (Hong Kong needs novelty; Korea needs planning confidence).
- **Launch-day surprises.** Dependencies (supply confirmations, asset delivery, channel eligibility) live in people's heads until they fail publicly.

The prototype attacks all three: code checks every intersection automatically, per-market data slices force differentiated outputs, and confirmations become tracked, owned, gate-keeping items.

## 3. How the AI workflow works

```
Excel workbook (one template, any destination campaign)
  │
  ├─ CODE  parse · validate · compute
  │        schema check, missing/TBD, unknown vocabulary, ambiguous coverage,
  │        market scores & tiers, city roles, channel/asset eligibility,
  │        cross-table tensions (cluster-deduped), confirmation IDs pre-assigned
  │
  ├─ HUMAN  confirm unmapped market tokens  ← e.g. "AUS" → Australia
  │         unresolved tokens would silently drop a channel, so the system asks
  │         instead of guessing; confirmations apply to slicing, eligibility and IDs
  │
  ├─ MODEL  for each market, one call:
  │           market's B/C rows + interest-matched D rows + eligible E/G rows
  │           + global A/F/H + whitelisted evidence catalog
  │         → MarketRecommendation JSON (angles, orderings, plays only)
  │
  ├─ CODE  per-market validation and normalization
  │        illegal or missing choices repaired against the typed contract;
  │        every fact re-joined from source, never from model text
  │
  ├─ MODEL  one global call over the N validated summaries:
  │         cross-market trade-offs, resource allocation, tiering narrative
  │
  ├─ CODE  assemble the documents
  │        scoring table, city-role matrix, recommendation matrix, confirmation
  │        list and launch checklists are rendered from validated data structures
  │
  ├─ HUMAN GATE 1  PM resolves every confirmation item (accept / override / defer)
  │                market packs stay locked until resolved
  │
  ├─ REUSE  market packs render from the already-validated recommendations;
  │         only markets touched by an override are regenerated
  │
  └─ HUMAN GATE 2  launch checklist; final export unlocks only when all items clear
```

Two structural choices are worth calling out. **The model is called per market, not once for everything**: each call sees one market's slice, so cross-market contamination is impossible by construction, and a failure in one market does not corrupt the others. **The global call reads validated summaries rather than raw tables**: by then the per-market facts are already fixed, so the global step is doing what it is uniquely needed for — comparison and resource trade-offs — on a small, clean input.

The division of labour is strict and is the system's central design idea:

**Code computes, the model interprets, humans decide.**

- *Code* owns everything deterministic: parsing, validation, market scoring, tier assignment, city-role classification, tension detection, channel/asset eligibility, ID assignment, structural validation of model output, and document assembly.
- *The model* owns judgment and language: readings ("what this data means"), positioning, orderings, module content briefs, localized copy, and how it proposes to handle each flagged tension. It returns structured JSON referencing whitelisted evidence IDs — it selects facts, it never rewrites them.
- *Humans* own decisions: ambiguous data mappings at ingestion, every tension and trade-off at gate 1, the launch call at gate 2. Each routes to a named owner and blocks progress until answered.

Two mechanisms enforce that division rather than merely asking for it. **A typed decision contract** (`core/plan.py`) freezes source and derived facts and enumerates the legal choices for each row, so the model's output space contains only decisions it is entitled to make. **An evidence catalog** gives every fact a whitelisted ID; the model cites IDs, and assembly re-joins the underlying text from source. A fact the model never had permission to phrase cannot be misphrased.

## 4. Input data schema

One template (`core/schema.py`), eight sheets mirroring the campaign's dimension model:

| Sheet | Dimension | Role |
|---|---|---|
| A_Campaign | — | Objective, duration, scope, decision maker |
| B_Markets | Market | Demand signals, lead time, city interest, barrier, localization |
| C_Products | Market × Product | Demand/conversion per product line |
| D_Cities | City/Cluster | Role + supply readiness per product line + known risk |
| E_Channels | Market (coverage) | Reach/CTR/quality, resource owner |
| F_Modules | — (global library) | Page module performance |
| G_Assets | Market (coverage) | Asset types, localization level, priority |
| H_Constraints | Stakeholder | Constraints that shape all outputs |

This implements the case's abstraction target — **Market × City/Cluster × Product × Channel × Asset × Stakeholder Constraint** — as join keys: B/C/E/G slice by market, D joins to B through city-interest, F/H are global. A field dictionary (injected into every prompt) fixes each column's semantics; a market-alias vocabulary absorbs real-world inconsistency ("Korea" vs "KR"). Interest City and Readiness Cluster are modelled as two layers: supply data grouped as "Chengdu / Chongqing" never implies user interest in both cities.

## 4b. Data ingestion, normalization and adaptation

**Ingestion is deliberately tolerant, because real campaign inputs are not clean.** Sheet matching accepts several naming conventions; a market-alias vocabulary reconciles the fact that one table writes "Korea" while another writes "KR"; level words, percentages and day ranges are parsed leniently. What the system refuses to do is guess: anything it cannot resolve becomes a flag, never a filled-in value.

**Original text is preserved; numbers live only inside the code.** An early design question was whether to normalize "High / Medium / Low" into 3 / 2 / 1 at ingestion. The answer depends on the consumer:

- *For the model*, numeric conversion is a loss — an LLM reads "Low-Medium" natively, and a bare 1.5 tells it less than the original word does.
- *For the code*, numeric conversion is mandatory — scoring, thresholds and role rules are arithmetic.

So the parser keeps every original value verbatim and derives numbers internally, on demand. The model never sees a 1.5; the arithmetic never sees a string. This also keeps flags readable in ops language ("hotel readiness is Low-Medium") instead of leaking internal scales into the UI.

**Adaptation points are declarative and centralized.** Adding a market alias, a product line, a scoring weight, a threshold, a display abbreviation or a validation vocabulary is a config edit in `core/schema.py`; parsing, slicing, scoring and generation code stays untouched. That is what makes "swap the data file to run Go Japan" a factual claim rather than an aspiration.

**Ambiguous mappings are escalated to the user, not guessed.** Coverage columns are written by humans and will not always match the built-in vocabulary — a channel may be scoped to "AUS" while the market table says "Australia". An unresolved token is dangerous precisely because it fails quietly: the channel simply never matches, and a plan is built without it. So the load step cross-checks every coverage token against the target markets and their aliases, and surfaces the unknown ones in the UI with a one-click mapping: *token "AUS" refers to → [market list]*. Confirmed mappings apply immediately to slicing, eligibility and ID codes, and the pre-check re-runs. They are held as session overrides — scoped to the campaign they were approved for, cleared when a new workbook loads — and the UI prints the config snippet for adopting a recurring mapping permanently. The principle is the same one that governs the rest of the system: the machine detects, the human decides, and nothing silently defaults.

**Validation runs before anything else.** Five deterministic checks at load time: missing or TBD required fields; values outside the known vocabulary; market tokens matching no target market (which would otherwise silently exclude a channel); coverage strings that are ambiguous rather than exclusive; and cross-table role tensions, deduplicated at cluster level so one sourcing question does not appear four times. The output is a typed, owner-attributed flag list feeding three consumers — the UI, the model context and the human review gate — from one source of truth.

## 4c. What each generation step is allowed to see

Slicing is a declared query, not a convenience. The rule for filtering versus full loading is mechanical:

**Does the table carry a market or city dimension?** If yes, it is per-entity data and is filtered by that key. If no, it is campaign-level configuration and loads in full.

| Table | Dimension | Handling |
|---|---|---|
| B Markets, C Products | Market (one row per market) | filter by market |
| D Cities | City | filter by the interest-city list read from B (the one cross-table join) |
| E Channels, G Assets | Market (coverage column) | filter by alias-aware coverage match |
| A Campaign, F Modules, H Constraints | none | load in full |

The intuition: F and H answer *"what building blocks and limits does this campaign have"* — shared context for every market. B/C/D/E/G answer *"what is true of this market"* — that is what needs slicing.

**The one cross-table join, in full.** Cities are not filtered by any property of their own; they are filtered by demand. For a given market, the system reads that market's `Top City Interest Signals` from table B, then keeps only the rows of table D whose city or cluster matches that list. So a Korea pack sees Shanghai, Beijing, Zhangjiajie and the Chengdu/Chongqing row — and never sees Guangzhou/Shenzhen or Xi'an, because Korean users do not search for them. This join is also where the two-layer city model matters: supply data may be grouped as "Chengdu / Chongqing", but only the searched city becomes a recommendation; the unsearched cluster member is carried separately as an extension candidate, never promoted into demand it has no evidence for.

**Two different steps, two different context strategies.** Per-market calls get the slice above: detail, but only for one entity. The cross-market synthesis call gets something else entirely — not the raw tables, but the N validated market recommendations compacted into summaries, plus the code-computed scoring table and flag list. It needs breadth to do its job (tiering markets against each other, noticing that one sourcing question blocks three markets, allocating scarce content capacity), but it does not need row-level detail to do it. The rule generalizes as: *detail flows to the step that acts on one entity; summaries flow to the step that compares across entities* — which is also why this shape survives scale: the comparison step's input grows with the number of markets, not with the size of the underlying tables.

**Why this reduces hallucination.** A Korea pack's context contains no Thai rows, no EDM row (EDM does not cover Korea), and no cities Korean users do not search for. The model cannot mis-assign an entity it was never shown. Combined with code-computed results injected as finished conclusions — scores, tiers, city roles, eligibility lists, pre-assigned confirmation IDs — the model's remaining job is interpretation and language, which is what it is good at. In testing, every entity-level error class was closed either by narrowing the slice or by moving a computation into code.

**Why this suits production scale.** The three mechanisms change shape rather than break:

- *Filtered tables*: the Python predicates map one-to-one onto SQL `WHERE` / `JOIN` clauses. Seven cities or three thousand, the condition is identical and the database absorbs the volume.
- *Full-load tables*: valid only while those tables are small (here, under ten rows each). If a module library grew to hundreds of entries the framework holds — slice by dimension first, then rank and truncate what cannot be sliced (top-N by past performance, or relevance retrieval against the market profile).
- *Computed results*: because scoring and conflict detection are deterministic arithmetic, they translate directly into scheduled SQL or dbt models whose results are read, not recomputed. Computation that lives inside a prompt cannot make that move — the second, less obvious reason for taking arithmetic away from the model.

The dependency graph is one-directional — raw tables → global brief → (human confirmation) → market packs → launch gate — and each step consumes only its declared inputs plus upstream conclusions. Nothing is recomputed downstream, so a decision made at gate 1 cannot be quietly reversed at step 4.

## 4d. Working with what a language model is bad at

A model summarizes well and transcribes badly. Long tables, exact figures, ID sequences and verbatim reproduction are exactly where it drifts — a digit changes, a row disappears, a label gets "improved". The documents here are full of such material, and the architecture's answer is not to ask the model to be careful. **The model never writes the tables at all.**

- **The model returns structured JSON, code renders the document.** Each market call produces a `MarketRecommendation` object — angles, orderings, plays, readings, copy — and nothing else. The scoring table, city-role matrix, recommendation matrix, confirmation list and launch checklists are rendered by `core/orchestrator.py` from validated data structures. Transcription is not verified; it is designed out.
- **Facts are selected by ID, never phrased.** Every market call carries an evidence catalog: each admissible fact has an ID and its exact source text. The model cites IDs to justify a decision; assembly substitutes the original text. A fact the model was never allowed to phrase cannot be paraphrased into something the data does not say — which is what the earlier "payment confidence" → "payment security" drift actually was.
- **The choice space is typed and closed.** The decision contract (`core/plan.py`) enumerates, per market, exactly which cities, products, channels, modules and assets are legal choices. Anything outside the contract is not a subtle error to be caught later; it fails validation immediately and is repaired against the contract.
- **Validation is layered, and the model gets one repair attempt.** Malformed JSON triggers one JSON-only retry; semantically incomplete JSON triggers one targeted correction call; whatever remains is normalized deterministically (illegal choices dropped, missing ones appended from the contract) with every repair recorded as a warning for the reviewer. Rendered documents then pass a final lint (`core/qa.py`) for the residue that only shows up in prose: timeline weeks beyond the campaign duration, statuses outside the allowed vocabulary, escalated wording, visible self-correction.
- **Volume stays below the drift threshold.** One market's slice per call rather than eight tables at once; audit detail confined to one appendix rather than restated in the body.

The general principle: *don't ask the model for anything that has a right answer in the data — ask it only for the judgment, then assemble the rest yourself.* This is the endpoint of a progression the project actually walked: prompt rules → output linting → auto-correction → structured output with code assembly. Each step moved a class of error from "detected after the fact" to "impossible by construction."

## 5. Output structure

- **Campaign strategy brief** (11 sections): overview → scoring table and tiering → market × city action matrix → product focus → channel/CRM strategy → resource allocation → risks → needs-confirmation list (C-N IDs) → full-dimension recommendation matrix (Market | City | Product | Page modules | Channels | Assets | Constraint | Play) → launch checklist → audit appendix.
- **Market execution pack** per market (8 sections): positioning → city plan → page modules → CRM plan with localized copy → asset requests → localization checklist → needs-confirmation (market-code IDs) → launch checklist.
- Every section opens with a 1–2 sentence operational reading; mechanism detail sits in an audit appendix — decisions first, evidence after.
- Every statement is tagged — **[FACT – table X] / [DERIVED] / [ASSUMPTION] / [AI REC] / [NEEDS CONFIRMATION]** — implementing the case's requirement to separate provided data, inference, recommendation and items needing human confirmation. A reader legend is prepended to every document.

## 6. Prompt / workflow design

**Module map** — each concern isolated so it can be changed or migrated independently:

| Module | Owns |
|---|---|
| `core/schema.py` | Input template, field dictionary, decision rules, aliases, scoring config |
| `core/parser.py` | Tolerant ingestion + deterministic validation |
| `core/scoring.py` | Scores, tiers, city roles, eligibility, tension detection, dedup |
| `core/plan.py` | Typed decision contract: locked facts, legal choices per market |
| `core/context.py` | Declared query layer: what each call may see, with audit trace |
| `core/prompts.py` | System prompt, JSON schemas for market and global calls, reader legend |
| `core/orchestrator.py` | Evidence catalogs, JSON validation/normalization, document rendering |
| `core/qa.py` | Post-render lint on the prose residue |
| `core/llm.py` | Provider abstraction (OpenAI-compatible / Anthropic / DashScope-Qwen) |

Design notes:

- **Prompts are destination-agnostic by construction.** They reference field names, rules and evidence IDs; the word "China" appears nowhere in `prompts.py` or `schema.py`. The same prompt text runs Go Japan.
- **Two prompt shapes, both JSON.** A per-market recommendation prompt (one market's slice + evidence catalog + campaign weeks) and a cross-market synthesis prompt (compacted validated recommendations + global evidence). Prose lives only inside declared fields; structure lives in code.
- **Guardrails, in the order they were added as live testing exposed each failure class:** input pre-checks → prompt rules → deterministic output lint → auto-correction pass → typed contract with evidence IDs and code-side assembly. The later layers made several earlier ones redundant, which is the point: each iteration converted a rule the model *should* follow into a structure it *cannot* violate.
- **Provider-switchable, demo-capable.** Any OpenAI-compatible endpoint (including DashScope/Qwen with an optional thinking-mode toggle) or Anthropic; a no-key demo mode ships pre-generated outputs so the workflow can be reviewed without credentials.

## 7. Human review points

- **Gate 0 (ingestion):** coverage tokens that match no known market are shown for one-click mapping before anything is computed. The system will not guess a mapping whose failure mode is a silently dropped channel.
- **Gate 1 (strategy):** every pre-check flag and tier decision point is presented for explicit resolution (accept / override / defer, with a note). Market packs stay locked until all are resolved; resolutions propagate downstream as CONFIRMED / OVERRIDDEN / DEFERRED conclusions that later steps execute rather than re-litigate. Market packs render from the already-validated recommendations, so only markets touched by an override need regeneration — review is cheap, and re-running does not silently reshuffle unrelated markets.
- **Gate 2 (launch):** final export unlocks only when supply, CRM eligibility, assets, copy approval, tracking and PM sign-off are all confirmed.
- **Owner vs decision-maker:** flags carry both — the team that must *verify* a fact (Sourcing, CRM, Regional) and the role that *decides* (Campaign Ops PM). CONFLICT items ask for adjudication; SUPPLY_RISK items ask for verification.

## 8. Risks and limitations

- **Configured, not calibrated.** Scoring weights, tier thresholds and city-role bars are explicit, configurable defaults reasoned from the campaign objective — not fitted to historical performance. Production should calibrate against past campaign ROI or use quantile/top-N cuts. (Stated inside the generated documents themselves.)
- **Prompt rules are guidance, not enforcement.** Live testing repeatedly showed the model violating written rules (timeline overruns, wording escalation such as "payment security", visible self-correction, invented IDs). That evidence drove the architecture toward structured output and code-side assembly, which removes those classes rather than policing them. What remains model-authored is prose inside declared fields — judgment, readings, copy — where lint plus human review is the appropriate control, not structural enforcement.
- **Multi-call cost and latency.** One call per market plus a synthesis call is more expensive and slower than a single mega-prompt. It buys isolation (no cross-market contamination), targeted regeneration (an override re-runs one market), and small validated units. For campaigns with many markets this becomes a real cost consideration; batching or parallelizing the per-market calls is the obvious next step.
- **Rules only catch patterns someone wrote down.** Code detects the tension types it has rules for; a novel one — a city whose risk note is about seasonality, say — passes through. The backstop is that the model also reads the raw risk fields and is instructed to surface business tensions it notices, so the confirmation list is *known patterns caught by code plus new tensions raised by the model*. The intended operating loop: the model surfaces something new → it recurs → it gets encoded as a rule. That is how the rule library grows.
- **Keyword heuristics.** Supply-risk detection and the escalation word-list are English-vocabulary heuristics; they need extension for other input languages.
- **Demo-scale context strategy.** Injecting full eligibility lists and evidence catalogs works at this data size. With large entity spaces, bounded vocabularies stay in-context while the rest moves to database-side validation and retrieval-limited catalogs; the structured-output shape itself already scales, since the model's output is bounded by the contract rather than by how much data exists.
- **Sample outputs disclosure.** Sample documents are prototype-generated; a small number of spots found in human review were manually corrected and are logged — which is the human-in-the-loop process working as designed.

## 9. How this scales to other destination campaigns

Swapping campaigns = swapping one data file. Included in the repo: `go_japan.xlsx`, deliberately ~60% filled — parsing, validation, scoring, slicing and prompts run unchanged; missing tables and TBD fields surface as review flags instead of breaking or being silently invented. Adapting further:

- **Different objective** (awareness vs conversion): adjust scoring weights in config — one dict, no code.
- **New product line / market**: add a column + weight / an alias entry.
- **Unfamiliar vocabulary** (a market token the built-in aliases do not know): confirmed once in the UI, optionally promoted to config — no code path changes.
- **Production migration is translation, not redesign:** template → warehouse tables; slice filters → SQL WHERE/JOIN; scoring → scheduled jobs on configurable rules; pre-checks → data-quality checks with alerts; the decision contract and evidence catalogs → built from the same queries; prompts → unchanged, plus versioning; document assembly → unchanged (it already consumes validated structures, not model prose); gates → approval workflow with audit trail.

The prototype's decision assets — data contract, query logic, computation rules, validation rules, prompts, and gate placement — are environment-independent. That is what makes it a workflow, not a demo.
