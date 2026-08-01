# Go Campaign Copilot

AI workflow prototype for destination campaign operations (Trip.com AI Marketing Engineer take-home case, Option D: end-to-end campaign ops workflow).

Turns fragmented campaign inputs (markets, cities, products, channels, assets, constraints) into reviewed, actionable ops documents — with humans as the final decision makers.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

No API key needed: **Demo mode** ships with pre-generated outputs for the Go China sample (global brief + Hong Kong + Korea packs), produced with the exact prompts in `core/prompts.py`. Add any OpenAI-compatible key (OpenAI / DeepSeek / Moonshot / vLLM...) or an Anthropic key in the sidebar to generate every market live.

## Deploy (Streamlit Community Cloud)

Push this folder to a public GitHub repo → share.streamlit.io → New app → select repo, main file `app.py`. Done — the app URL is your demo link.

## Workflow (4 steps, 2 human gates)

```
1 Upload template (.xlsx)      one template, any destination campaign
2 Data check (code, no AI)     missing/TBD/unknown-value flags, deterministic
3 Strategy brief              one filtered JSON call per market; code validates
                              locked facts and decision completeness; incomplete
                              CRM/readings cite a locked evidence catalog and get one targeted
                              repair when incomplete; one compact synthesis;
                              final tables are assembled deterministically
    HUMAN GATE                 PM resolves each decision point; packs stay locked
4 Market packs                reuse each validated market recommendation ->
                              page config, CRM, assets, localization checklist
```

## Architecture / abstraction (core requirement of the case)

| Layer | File | Destination-specific? |
|---|---|---|
| Input template & field dictionary | `core/schema.py` | No — generic dimensions: Market x City x Product x Channel x Asset x Constraint |
| Parsing + deterministic validation | `core/parser.py` | No |
| Context assembly (per-market data slicing, join on market/city keys) | `core/context.py` | No |
| Structured validation + deterministic document assembly | `core/orchestrator.py` | No |
| Prompts (rules reference fields, never destinations) | `core/prompts.py` | No |
| Model client (provider-switchable) | `core/llm.py` | No |
| Data | `data/go_china.xlsx`, `data/go_japan.xlsx` | **Yes — the ONLY destination-specific artifact** |

Proof of reuse: load `go_japan.xlsx` (deliberately ~60% filled). Parsing, validation, slicing and prompts run unchanged; missing table/TBD fields surface as review flags instead of breaking the flow or being silently invented.

## How missing / conflicting data is handled

Three-layer split — code catches what code can catch, the model interprets what needs judgment, humans decide:
1. **Code (deterministic):** required-field / TBD / unknown-vocabulary checks at load time → flags.
2. **Model (guided):** flags are injected into the context with hard rules: never invent values, never silently resolve conflicts, everything lands in a NEEDS CONFIRMATION table with a suggested handling and an owner. Soft conflicts (e.g. a city with high user interest but low supply readiness) are detected via decision rules in the prompt — these are *decision points*, not data errors.
3. **Human (gate):** the PM resolves each item in the UI; decisions propagate downstream as CONFIRMED conclusions that the model must execute, not re-litigate.

## Output tagging

Every statement in every generated document is tagged `[FACT - table X]`, `[ASSUMPTION]`, `[AI REC]`, or `[NEEDS CONFIRMATION]` — separating provided data, inference, recommendation, and items requiring human confirmation (case requirement 6.5).

## Repo map

```
app.py                  Streamlit UI (4-step flow, review gate, context inspector)
core/schema.py          template spec + field dictionary + decision rules + aliases
core/parser.py          xlsx/json parsing + deterministic validation
core/context.py         per-market context assembly with audit trace
core/prompts.py         per-market JSON + compact global-synthesis prompts
core/orchestrator.py    JSON repair, normalization and deterministic document assembly
core/llm.py             OpenAI-compatible / Anthropic / demo-mode client
core/demo_outputs.py    pre-generated sample outputs (= deliverable 5.3)
data/go_china.xlsx      full sample (case appendix data)
data/go_japan.xlsx      partial sample proving reuse + missing-data handling
```
