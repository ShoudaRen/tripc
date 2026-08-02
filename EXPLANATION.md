# Go Campaign Copilot — Explanation Document

*AI Marketing Engineer take-home case · Option D: End-to-end Campaign Ops Workflow*
Prototype: Streamlit app (`app.py`) 

---

## 1. Which workflow problem I chose

**The problem: campaign inputs are distributed across teams and tables, but campaign ops still has to connect them manually into one executable plan.**

Market demand, city and product readiness, channel coverage, page modules, creative assets, localization needs and stakeholder constraints are available as separate inputs. The difficult part is not reading any individual table; it is repeatedly reconciling them for each market and turning the result into a consistent strategy brief, page plan, CRM plan, asset request and launch checklist.

The recurring decision can be expressed as an intersection:

*For this market, which cities or city clusters show demand, which products are ready to convert, which channels are eligible, which modules and assets are justified, and which stakeholder constraints still require confirmation?*

Some parts of this reasoning are deterministic, such as market filtering, eligibility checks, missing-data validation and city-readiness classification. Other parts require judgment, such as positioning, execution priority and how to handle a trade-off. Performing both manually across multiple markets is repetitive and makes cross-table conflicts easy to miss.

**The workflow problem I chose is therefore to turn this intersection reasoning into a reusable and auditable pipeline: code handles deterministic checks, AI interprets the validated evidence, and unresolved decisions are routed to named human reviewers before downstream execution.**

This corresponds to Option D, the end-to-end Campaign Ops Workflow. It connects the strategy, page, CRM, asset, localization and launch outputs through one shared data model, while also incorporating the capabilities described in Options A, B and C. I chose this direction to demonstrate that the same underlying workflow logic can support multiple outputs and later be reused for other destination campaigns.

## 2. Why this problem matters for campaign ops

Campaign ops must manually combine market demand before producing an executable campaign plan. Although each input table is manageable on its own, the difficulty increases when these inputs must be evaluated together for every market. 

Without a consistent workflow, these relationships are easy to miss, and execution can become overly standardized across markets with different needs. Hong Kong users may respond to fresh short-trip reasons, while Korean users may need stronger itinerary and transport guidance. Applying the same city order, page structure or CRM approach to both markets would reduce the relevance of the campaign.

This problem also affects launch readiness because supply gaps, channel eligibility, asset capacity and localization requirements may remain unresolved until late in the process. The prototype addresses this by validating deterministic relationships in code, generating recommendations from market-specific data, and converting unresolved dependencies into visible confirmation items with responsible stakeholders. This gives campaign ops a repeatable way to move from fragmented inputs to a differentiated and reviewable execution plan.


## 3. How the AI workflow works
The workflow begins by converting the uploaded workbook into a canonical data structure. Code validates the schema, identifies missing or ambiguous values, and asks the user to confirm mappings that cannot be resolved safely. It then calculates deterministic results such as market scores, city roles, channel and asset eligibility, and prepares a filtered data package for each market.

Each market package is analyzed separately by the model. The model generates structured recommendations covering positioning, priorities, page modules, CRM strategy and creative assets. Code then validates the response against the available source data and decision rules, removes invalid choices, and restores fields that must remain source-controlled.

After all market recommendations have been validated, a global model call compares them and produces cross-market strategic insights. Code assembles these results into the campaign brief, recommendation matrix, risk summary and launch checklist. The Campaign Ops PM reviews the strategy and may accept, override or defer individual decisions. Reviewed recommendations are then rendered into market execution packs, while final export remains subject to a launch approval checklist.

The workflow follows a clear division of responsibility: code prepares and controls the data, AI interprets the evidence and recommends actions, and humans retain final decision authority.

![Screenshot 2026-08-02 153723](C:\Users\rensh\OneDrive\pmcv example\4\Screenshot 2026-08-02 153723.png)

## 4. Input data schema

A canonical workbook schema is defined in `core/schema.py`. It contains eight sheets representing the main campaign dimensions:

| Sheet | Dimension | Role |
|---|---|---|
| A_Campaign | Campaign | Objective, duration, scope and decision maker |
| B_Markets | Market | Demand, lead time, city interest, user barrier and localization |
| C_Products | Market × Product | Demand and conversion signals by product line |
| D_Cities | City / Cluster | Destination role, supply readiness and campaign risk |
| E_Channels | Channel × Market Coverage | Reach, performance, coverage and resource ownership |
| F_Modules | Page Module | Available modules and historical performance |
| G_Assets | Asset × Market Coverage | Asset requirements, localization level and priority |
| H_Constraints | Stakeholder Constraint | Operational requirements that influence recommendations |

Together, these tables implement the reusable abstraction **Market × City / City Cluster × Product × Channel × Asset × Stakeholder Constraint**. Tables B and C are filtered by market, table D is matched through the market's city-interest signals, and tables E and G are filtered by market coverage. Tables A, F and H provide campaign-level context shared across markets. A field dictionary defines the meaning of each column, while market aliases handle naming differences across tables. Interest cities and readiness clusters remain separate: cluster-level supply data can support an interested city, but it does not create demand for other cities in the same cluster.

After upload, the workbook is mapped to this schema and checked for missing fields, TBD values, unknown vocabulary, duplicate keys and conflicting information. The parser accepts common naming variations, but it does not guess when a value cannot be matched safely. Ambiguous market mappings are shown to the user for confirmation, while unresolved data remains visible as a review item.

### Data normalization and decision logic

Source values are preserved in business language for prompts, reports and human review, while code converts qualitative levels into an internal numeric scale for consistent calculation: High = 3, Medium-High = 2.5, Medium = 2, Low-Medium = 1.5 and Low = 1. Market priority is calculated with configurable weights: `Market score = 0.40 × normalized search demand + 0.25 × normalized growth + 0.35 × product score`. The product score combines Hotel, Flight, Attractions, Tours and Train/Transfer signals rather than relying on a single strong product. Scores of 0.75 or above are assigned P0, scores from 0.60 to 0.74 are P1, and lower scores are P2; incomplete inputs are withheld instead of being guessed.

City recommendations use a separate threshold-based rule rather than the market weighting formula. A city must first appear in the market's interest data. It becomes a Conversion city when both hotel and flight readiness are at least Medium; it becomes Package when attractions or tours readiness is at least Medium-High but hotel or flight readiness is below Medium; otherwise it is Content, NEEDS DATA, or Conditional Conversion when a known supply risk still requires confirmation. For example, if users in Korea search for Zhangjiajie and its attractions readiness is High while hotel or flight readiness is Low-Medium, code classifies it as Package rather than recommending an open-ended conversion push.

The model receives the original labels, the decision rules and the code-derived results. It explains how to activate each market and city, but it does not recalculate or change their scores and roles. Users therefore see operational language such as High, Medium, Conversion and Package, while the underlying comparison remains deterministic and auditable. The weights and thresholds are configurable defaults and should be calibrated with historical campaign performance in production.

For each market, code prepares a dedicated data package. Market demand and product performance are filtered by market, city readiness is matched through that market's interest cities, and channels and assets are filtered by confirmed market coverage. Campaign information, the module library and stakeholder constraints are shared as global context. This gives the model enough information to make a recommendation without exposing unrelated market data.

The model returns structured JSON containing recommendations, priorities and operational explanations. It does not control market scores, city roles, eligibility, asset priorities or confirmation IDs. These fields are defined by a typed decision contract and restored from source-controlled data during validation. Recommendations may reference only resources available in the current market package, while evidence IDs connect their rationale back to the original data.

If a response is malformed or incomplete, the model receives one repair attempt. Code then removes invalid choices, restores locked fields and records any remaining issues as non-blocking review hints. Final tables, matrices and checklists are assembled by code rather than transcribed by the model.

The global synthesis step receives validated market recommendations instead of the full raw workbook. It compares markets and proposes campaign-level trade-offs, while detailed source data remains controlled within each market analysis.

**The core principle is simple: preserve source data, filter context before generation, let AI make recommendations only within a validated choice space, and keep unresolved decisions visible for human review.**

## 5. Output structure

The workflow produces two connected outputs:

- **Campaign strategy brief** with 11 sections: campaign overview → market scoring and tiering → executive market × city summary → product focus → channel and CRM strategy → resource allocation → risks and dependencies → campaign-level confirmation list → full recommendation matrix → launch checklist → audit appendix.

- **Market execution pack** with 8 sections for each market: positioning and decision summary → city push plan → page module configuration → CRM plan → asset requests → localization checklist → market-level confirmation list → launch checklist. Localized CRM copy is generated only when the relevant channel is confirmed as eligible.

Major recommendation sections begin with a short operational reading that explains what the evidence means and what action it supports. Detailed scoring and city-role derivations are kept in methodology notes or audit appendices so that the main document remains focused on decisions.

Decision-bearing content is labelled as **[FACT – table X]**, **[DERIVED]**, **[ASSUMPTION]**, **[AI REC]** or **[NEEDS CONFIRMATION]**. This separates source data, deterministic results, model recommendations and unresolved human decisions. A reader legend is included with every exported document.

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

The prompt design separates market-level judgment from campaign-level comparison. Instead of sending the full workbook to the model in one request, the workflow first runs one recommendation call for each market and then runs a separate global synthesis call over the validated market results.
The per-market prompt receives only the current market’s filtered data, its available cities and resources, a typed decision contract, and a catalog of approved evidence.  This keeps the model focused on one market and reduces the risk of mixing cities, channels or assets across markets.

The global prompt performs a different task. It receives compact, validated recommendations rather than the original workbook, and compares markets to identify shared priorities, resource trade-offs and campaign-level risks. Separating these two reasoning tasks prevents a single large prompt from having to interpret detailed market data and make cross-market decisions at the same time.

The model is used as a constrained recommendation layer rather than a report generator. Market scores, city roles, resource eligibility, asset priorities and confirmation IDs are computed or locked by code. The model may rank legal choices and explain how they should be used, but it cannot redefine the available choice set. Its evidence references must match IDs in the supplied catalog, and code restores the corresponding source text when assembling the report. Final tables and checklists are therefore rendered from validated data structures instead of being copied from model prose.

The prompts are driven by schema definitions and field meanings rather than destination-specific instructions. They refer to dimensions such as market demand, city readiness, product performance, channel coverage, assets and stakeholder constraints; they do not contain campaign-specific city or market names. As a result, another destination campaign can use the same workflow when its workbook follows the canonical schema. New or incomplete inputs are handled through validation, alias mapping and human confirmation rather than changes to the prompt chain.

The main design principle is to give each layer a clear responsibility: code defines facts and legal choices, the model recommends and explains, and humans resolve ambiguity and approve execution. This combination provides more reliable outputs than a free-form prompt while preserving the model’s ability to make market-specific business judgments

## 7. Human review points

Human review is placed at three points where the system cannot safely make a business decision on its own.

**Gate 0 — Data mapping.** Before recommendation generation, the user reviews market or coverage values that cannot be matched to the schema. Confirmed mappings are applied to market filtering and eligibility checks, while unresolved values remain visible instead of being silently excluded.

**Gate 1 — Strategy review.** The Campaign Ops PM reviews every confirmation item raised during data validation and recommendation generation. Each item can be accepted, overridden or deferred to an operational owner. Market packs remain locked while any item is still pending. Deferred items allow planning to continue but remain visible as unresolved dependencies in downstream documents.

**Gate 2 — Launch approval.** Before final export, campaign ops confirms that supply, CRM eligibility, creative assets, localization, tracking and final PM approval are complete. The final campaign package remains locked until every launch-checklist item has been confirmed.

Operational teams such as Sourcing, CRM, Design and Regional Teams verify the information within their responsibility, while the Campaign Ops PM retains final decision authority. This keeps AI recommendations reviewable without allowing the workflow to silently resolve missing or conflicting business inputs.

## 8. Risks and limitations

**Decision rules are not historically calibrated.** Market-scoring weights, tier thresholds and city-role rules are configurable prototype assumptions rather than models fitted to past campaign performance. Production use would require calibration against historical campaign outcomes and available resource capacity.

**Model-authored recommendations still require review. **Structured JSON, decision contracts and evidence validation reduce unsupported choices, but positioning, rationale, CRM strategy and copy remain model-generated. Their business quality and wording can vary across models and runs, so human approval remains necessary.

**Current matching logic depends on controlled vocabulary.** Market aliases, city-cluster matching and several risk checks rely on configured names and English keywords. New naming conventions, languages or campaign dimensions may require updates to the schema and validation vocabulary.

**Multi-call generation has cost and scale limits. **The workflow makes one recommendation call per market followed by a global synthesis call. This improves market-level focus but increases latency and token usage. Thus, larger campaigns would require parallel execution, database-side filtering and smaller evidence retrieval sets. Moreover, I'm not very familiar with Trip's business processes and Ops focus, the project's generated reports contain a lot of redundant data (this was intentional), which also resulted in significant token consumption.

**Residual factual drift is reduced, not eliminated. **Scores, tiers, city roles, eligibility, priorities and confirmation IDs are computed and rendered by code, which prevents the model from changing these locked values. However, model-authored readings, rationale and copy may still introduce unsupported or incorrect numeric details. Evidence references, output linting and human review reduce this risk; a production version should additionally validate numeric claims in model-authored text against the source evidence catalog.

## 9. How this scales to other destination campaigns

The workflow is designed to support different destination campaigns through the same input schema. Swapping campaigns = swapping one data file. Markets, cities, products, channels, assets and stakeholder constraints are read from the uploaded workbook rather than hardcoded in the prompts or workflow logic.

To run another destination campaign, campaign ops replaces the input workbook. Missing or incomplete data is surfaced as confirmation items instead of preventing the workflow from running or being filled in by the model.

Because the prompts and decision logic operate on reusable campaign dimensions rather than destination names, the same workflow can be applied to Go China, Go Japan and other destination campaigns without redesigning the solution. In production, the data source can move from Excel to warehouse tables while preserving the same workflow structure.
