"""
Campaign Copilot — destination campaign AI workflow prototype.
Streamlit app. Run: streamlit run app.py
"""
import hashlib
import importlib
import io
import json
import os
import re
import streamlit as st


def _load_dotenv(path=".env"):
    """Tiny .env loader (no extra dependency). Lines: KEY=value. Never commit .env."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except FileNotFoundError:
        pass


_load_dotenv()
from core import context, demo_outputs, llm, orchestrator, parser, plan, prompts, qa, schema, scoring

# Streamlit reruns app.py in a long-lived interpreter. Explicitly refresh local
# modules so edits to parser/LLM/prompt logic cannot remain hidden by sys.modules.
schema = importlib.reload(schema)
parser = importlib.reload(parser)
scoring = importlib.reload(scoring)
plan = importlib.reload(plan)
context = importlib.reload(context)
orchestrator = importlib.reload(orchestrator)
prompts = importlib.reload(prompts)
llm = importlib.reload(llm)
qa = importlib.reload(qa)
demo_outputs = importlib.reload(demo_outputs)
DEMO, DEMO_NOTE = demo_outputs.DEMO, demo_outputs.DEMO_NOTE

APP_VERSION = "v2.6-token-efficient"

st.set_page_config(page_title="Campaign Copilot", page_icon="✦", layout="wide")

ss = st.session_state
for k, v in [("tables", None), ("flags", []), ("source_name", ""), ("global_brief", ""),
             ("decisions", {}), ("unlocked", False), ("packs", {}), ("traces", {}),
             ("launch_checks", {}), ("source_id", ""), ("schema_report", None),
             ("schema_engine_version", ""), ("market_recommendations", {}),
             ("global_synthesis", {}), ("normalization_warnings", []),
             ("market_aliases", {}), ("token_usage", [])]:
    ss.setdefault(k, v)

# Do not reuse state created by an older workflow/schema contract.
if ss.schema_engine_version != APP_VERSION:
    for key, value in (("tables", None), ("flags", []), ("source_name", ""),
                       ("source_id", ""), ("schema_report", None), ("global_brief", ""),
                       ("decisions", {}), ("unlocked", False), ("packs", {}), ("traces", {}),
                       ("market_recommendations", {}), ("global_synthesis", {}),
                       ("normalization_warnings", []), ("market_aliases", {}),
                       ("token_usage", [])):
        ss[key] = value
    ss.schema_engine_version = APP_VERSION

# Local modules are reloaded above on every Streamlit rerun. Restore only this
# browser session's user-confirmed aliases before validation or context slicing.
schema.clear_session_aliases()
for alias_market, alias_tokens in ss.market_aliases.items():
    for alias_token in alias_tokens:
        schema.register_alias(alias_market, alias_token)

# ---------------- Sidebar: model provider ----------------
with st.sidebar:
    st.markdown("### ⚙️ Model provider")
    st.caption(f"engine {APP_VERSION}")
    provider = st.selectbox("Provider", llm.PROVIDERS, index=0)
    base_url, api_key, model = "", "", ""
    thinking = False
    if not provider.startswith("Demo"):
        d = llm.DEFAULTS.get(provider, {})
        base_url = st.text_input("Base URL", value=d.get("base_url", ""))
        model = st.text_input("Model", value=d.get("model", ""))
        env_key = d.get("env_key", "")
        api_key = st.text_input("API key", type="password",
                                value=os.environ.get(env_key, ""),
                                help=f"Auto-filled from env var {env_key} if set. "
                                     "On Streamlit Cloud, use Secrets instead of committing keys.")
        st.caption("Structured mode validates each market JSON and repairs JSON syntax once when needed.")
        if provider.startswith("Qwen") or provider == "DeepSeek":
            thinking = st.checkbox("Thinking mode (slower, cleaner final prose)", value=False,
                                   help="Routes the model's reasoning into a hidden channel so "
                                        "self-corrections are less likely to appear in the document.")
        if st.button("Test connection (1-token ping)"):
            r = llm.test_connection(provider, base_url, api_key, model)
            (st.success if r == "OK" else st.error)(r)
    else:
        st.caption(DEMO_NOTE)
    st.divider()
    st.markdown("### 🧱 Architecture")
    st.caption("1️⃣ Parse + validate (code)  \n2️⃣ Loop markets with filtered slices (LLM → JSON)  \n"
               "3️⃣ Validate + global synthesis  \n4️⃣ Assemble fixed tables (code)  \n"
               "5️⃣ Human review gate  \n\nThe same prompt and schema run for every market and destination.")

st.title("Campaign Copilot")
st.caption("Turns fragmented destination-campaign inputs into reviewed, actionable ops documents. "
           "Humans stay the decision makers.")

step_labels = ["1 · Upload data", "2 · Data check", "3 · Strategy brief + review", "4 · Market packs"]
schema_ready = ss.tables is not None and not (ss.schema_report or {}).get("blocking", False)
done = [ss.tables is not None, schema_ready, bool(ss.global_brief), ss.unlocked]
st.markdown(" → ".join(("✅ " if d else "⬜ ") + s for s, d in zip(step_labels, done)))
st.divider()

# ---------------- Step 1: upload ----------------
st.subheader("Step 1 · Upload campaign data")
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    up = st.file_uploader(
        "Upload the campaign input template (.xlsx)",
        type=None,
        key="campaign_upload",
        max_upload_size=50,
        help=("File names and browser MIME types are ignored. The server validates the "
              "actual Excel content, so Windows short names such as GO_JAP~2.XLS work."),
    )
with c2:
    load_china = st.button("Load sample: Go China (full)")
with c3:
    load_japan = st.button("Load sample: Go Japan (60% filled)")


def _activate_workbook(tables: dict, schema_report: dict,
                       source_name: str, source_id: str) -> None:
    ss.tables = tables
    ss.schema_report = schema_report
    ss.source_name = source_name
    ss.source_id = source_id
    # Alias confirmations belong to the campaign they were approved for, not to the app.
    schema.clear_session_aliases()
    ss.market_aliases = {}
    ss.flags = ([] if schema_report.get("blocking") else
                parser.validate(ss.tables) + scoring.detect_conflicts(ss.tables))
    ss.global_brief = ""
    ss.unlocked = False
    ss.packs = {}
    ss.decisions = {}
    for state_key in list(ss):
        if state_key.startswith(("decision_choice_", "decision_note_", "al_")):
            del ss[state_key]
    ss.market_recommendations = {}
    ss.global_synthesis = {}
    ss.normalization_warnings = []


if load_china:
    tables, schema_report = parser.load_workbook_with_report("data/go_china.xlsx")
    _activate_workbook(tables, schema_report, "go_china.xlsx", "sample:go_china")
elif load_japan:
    tables, schema_report = parser.load_workbook_with_report("data/go_japan.xlsx")
    _activate_workbook(tables, schema_report, "go_japan.xlsx", "sample:go_japan")
elif up is not None:
    payload = up.getvalue()
    try:
        parser.validate_xlsx_upload(payload)
        upload_id = "upload:" + hashlib.sha256(payload).hexdigest()
        if ss.source_id != upload_id:
            tables, schema_report = parser.load_workbook_with_report(io.BytesIO(payload))
            _activate_workbook(tables, schema_report, up.name, upload_id)
    except parser.WorkbookFormatError as exc:
        st.error(f"Upload rejected: {exc}")
        st.stop()
    except Exception:
        st.error(
            "Upload rejected: the file is a valid .xlsx container but its workbook "
            "content could not be parsed. Open it in Excel or LibreOffice, save a fresh "
            ".xlsx copy, and try again."
        )
        st.stop()

if ss.tables is None:
    st.info("Upload a template or load a sample to begin. The same template works for any destination campaign.")
    st.stop()

st.success(f"Loaded **{ss.source_name}**")

# ---------------- Schema gate: structure before business rules ----------------
st.subheader("Workbook schema validation")
schema_report = ss.schema_report or {
    "schema_version": schema.SCHEMA_VERSION, "blocking": True, "issues": []
}
schema_issues = schema_report.get("issues", [])
blockers = sum(i.get("severity") == "BLOCKER" for i in schema_issues)
warnings = sum(i.get("severity") == "WARNING" for i in schema_issues)
st.caption(
    f"Schema v{schema_report.get('schema_version', '?')} · "
    "columns are validated by count and position, then mapped to canonical internal fields"
)
if blockers:
    st.error(
        f"Schema check blocked analysis: {blockers} structural issue(s). "
        "Business validation, scoring, and AI generation were not run."
    )
elif warnings:
    st.warning(
        f"Schema accepted with {warnings} compatibility/data-gap warning(s). "
        "Approved aliases were normalized before validation and scoring."
    )
else:
    st.success("Schema check passed. All parsed columns use canonical internal field names.")

if schema_issues:
    with st.expander(f"Schema report ({len(schema_issues)} items)", expanded=bool(blockers)):
        st.dataframe(
            [{k: issue.get(k, "") for k in
              ("severity", "code", "table", "location", "expected", "actual", "action")}
             for issue in schema_issues],
            hide_index=True,
            column_config={
                "severity": st.column_config.TextColumn("Severity", pinned=True),
                "code": st.column_config.TextColumn("Code"),
                "table": st.column_config.TextColumn("Table"),
                "location": st.column_config.TextColumn("Location"),
                "expected": st.column_config.TextColumn("Expected"),
                "actual": st.column_config.TextColumn("Received"),
                "action": st.column_config.TextColumn("Action"),
            },
        )

if schema_report.get("blocking"):
    st.info("Fix the reported workbook structure and upload it again. No downstream result was produced from ambiguous columns.")
    st.stop()

# ---------------- Step 2: data check ----------------
st.divider()
st.subheader("Step 2 · Data check (deterministic pre-check, no AI)")
markets = parser.parse_markets(ss.tables)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Markets", len(markets))
m2.metric("Cities / clusters", len(ss.tables.get("D_Cities") or []))
m3.metric("Channels", len(ss.tables.get("E_Channels") or []))
m4.metric("Flags (deduped)", len(scoring.dedupe_flags(ss.flags)))

with st.expander("View parsed tables"):
    for key, t in ss.tables.items():
        st.markdown(f"**{key}**")
        if t is None:
            st.warning("Sheet missing or empty")
        elif isinstance(t, dict):
            st.table([{"Field": k, "Value": v} for k, v in t.items()])
        else:
            st.dataframe(t, width="stretch")

unmapped = sorted({f["raw"] for f in ss.flags if f["type"] == "UNMAPPED_MARKET"})
if unmapped:
    st.warning(f"{len(unmapped)} coverage token(s) match no target market. Unresolved tokens are "
               "excluded from matching, which would silently drop a channel or asset. Confirm the "
               "mapping below — this is a human decision, so nothing is guessed.")
    suggestions = {token: schema.suggest_market_alias(token, markets) for token in unmapped}
    st.dataframe(
        [{"Coverage token": token,
          "Suggested market": suggestions[token] or "No safe suggestion"}
         for token in unmapped],
        hide_index=True,
        width="stretch",
    )
    suggested = {token: market for token, market in suggestions.items() if market}
    if st.button(
        f"Apply all safe suggestions ({len(suggested)})",
        disabled=not suggested,
        help="Applies only unique exact-code, initials, or market-prefix matches. "
             "Ambiguous tokens are left for manual review.",
    ):
        for token, target in suggested.items():
            schema.register_alias(target, token)
            ss.market_aliases.setdefault(target.lower(), [])
            if token.lower() not in ss.market_aliases[target.lower()]:
                ss.market_aliases[target.lower()].append(token.lower())
        ss.flags = parser.validate(ss.tables) + scoring.detect_conflicts(ss.tables)
        st.rerun()
    with st.form("alias_form"):
        choices = {}
        for tok in unmapped:
            suggested_market = suggestions[tok]
            select_options = ["— leave unmapped —"] + markets
            choices[tok] = st.selectbox(
                f"Token '{tok}' refers to:", select_options,
                index=(select_options.index(suggested_market) if suggested_market else 0),
                key=f"al_{tok}",
            )
        if st.form_submit_button("Confirm mappings"):
            for tok, target in choices.items():
                if target != "— leave unmapped —":
                    schema.register_alias(target, tok)
                    ss.market_aliases.setdefault(target.lower(), [])
                    if tok.lower() not in ss.market_aliases[target.lower()]:
                        ss.market_aliases[target.lower()].append(tok.lower())
            ss.flags = parser.validate(ss.tables) + scoring.detect_conflicts(ss.tables)
            st.rerun()

if ss.market_aliases:
    lines = [f"- `{tok.upper()}` → **{mkt.title()}**"
             for mkt, toks in ss.market_aliases.items() for tok in sorted(toks)]
    snippet = "\n".join(f'    "{mkt}": {{{", ".join(repr(t) for t in sorted(toks))}}},'
                        for mkt, toks in ss.market_aliases.items())
    with st.expander(f"✅ {len(lines)} user-confirmed market mapping(s) active this session"):
        st.markdown("\n".join(lines))
        st.caption("Applied to slicing, eligibility and ID codes for this session. To make them "
                   "permanent for every run, add these entries to MARKET_ALIASES in core/schema.py:")
        st.code(snippet, language="python")

if ss.flags:
    deduped = scoring.dedupe_flags(ss.flags)
    with st.expander(f"⚠️ {len(deduped)} flags (missing / ambiguous / role tensions; cluster-level deduped) — injected into model context", expanded=True):
        for f in deduped:
            st.markdown(f"- `{f['type']}` **{f['table']}** — {f['detail']}")

# ---------------- Step 3: global brief + review gate ----------------
st.divider()
st.subheader("Step 3 · Campaign strategy brief + human review gate")

def _lint_doc(doc: str, market: str | None = None) -> list[str]:
    weeks = qa.parse_duration_weeks(ss.tables.get("A_Campaign"))
    required_ids = ([item["_id"] for item in _campaign_review_items()]
                    if market is None else None)
    return qa.lint_all(doc, weeks, ss.tables, market=market, required_ids=required_ids)


def _demo_output(demo_key: str) -> str:
    if ss.source_name == "go_china.xlsx" and demo_key in DEMO:
        return DEMO[demo_key]
    return ("*(Demo mode covers the Go China sample: global brief and all five market "
            "execution packs. Load the Go China sample to use these pre-generated outputs.)*")

def _campaign_review_items() -> list[dict]:
    """Stable campaign IDs shared by prompt, UI review and downstream packs."""
    items = [dict(flag, _id=f"C-{i}")
             for i, flag in enumerate(scoring.dedupe_flags(ss.flags), 1)]
    next_id = len(items) + 1
    for row in scoring.market_scores(ss.tables):
        if row["tier"] == "P2":
            items.append({
                "_id": f"C-{next_id}",
                "type": "TIER_KPI_REVIEW",
                "table": "B_Markets x C_Products",
                "detail": (f"{row['market']} tiered P2 (score {row['score']}): confirm nurture "
                           "KPI (engagement/content, not GMV)"),
            })
            next_id += 1
    return items


def _call_live_model(user_prompt: str, status_callback=None, usage_callback=None) -> str:
    return llm.generate(
        provider, base_url, api_key, model, prompts.SYSTEM, user_prompt,
        temperature=0.2, thinking=thinking, status_callback=status_callback,
        usage_callback=usage_callback,
    )


def _generate_structured_brief() -> str:
    """N market JSON calls + one compact global synthesis call."""
    campaign_flags = _campaign_review_items()
    recommendations, traces, all_warnings = {}, {}, []
    total = len(markets) + 1
    progress = st.progress(0, text=f"Preparing {len(markets)} market recommendations...")
    for index, market in enumerate(markets, 1):
        progress.progress((index - 1) / total,
                          text=f"Analyzing {market} ({index}/{len(markets)})...")
        market_context, trace = context.assemble_market_prompt(
            ss.tables, market, campaign_flags, upstream=""
        )
        evidence_catalog = orchestrator.market_evidence_catalog(ss.tables, market)
        repair_context = json.dumps(
            {"evidence_catalog": evidence_catalog,
             "decision_package": json.loads(market_context)},
            ensure_ascii=False, separators=(",", ":"),
        )
        attempt = {"count": 0}
        def market_call(prompt, current_market=market, current_index=index):
            attempt["count"] += 1
            stage = "initial" if attempt["count"] == 1 else "repair"
            return _call_live_model(
                prompt,
                lambda status: progress.progress(
                    (current_index - 1) / total,
                    text=(f"Analyzing {current_market} ({current_index}/{len(markets)}) · "
                          f"{status}"),
                ),
                lambda usage: ss.token_usage.append({
                    "scope": current_market, "stage": stage,
                    "attempt": attempt["count"], **usage,
                }),
            )

        raw = orchestrator.call_validated_json(
            market_call,
            prompts.MARKET_RECOMMENDATION_JSON.format(
                market=market,
                weeks=orchestrator.campaign_weeks(ss.tables),
                evidence_catalog=json.dumps(
                    evidence_catalog, ensure_ascii=False, indent=2
                ),
                context=market_context,
            ),
            lambda value, current_market=market: orchestrator.validate_market_json(
                value, ss.tables, current_market,
                orchestrator.market_evidence_catalog(ss.tables, current_market),
            ),
            repair_context=repair_context,
        )
        recommendation, warnings = orchestrator.normalize_market_recommendation(
            raw, ss.tables, market, campaign_flags
        )
        recommendations[market] = recommendation
        traces[market] = trace
        all_warnings.extend(warnings)

    progress.progress(len(markets) / total, text="Synthesizing cross-market trade-offs...")
    compact = orchestrator.compact_global_context(
        ss.tables, recommendations, campaign_flags
    )
    global_evidence = orchestrator.global_evidence_catalog(
        ss.tables, recommendations, campaign_flags
    )
    synthesis_attempt = {"count": 0}
    def synthesis_call(prompt):
        synthesis_attempt["count"] += 1
        stage = "initial" if synthesis_attempt["count"] == 1 else "repair"
        return _call_live_model(
            prompt,
            lambda status: progress.progress(
                len(markets) / total,
                text=f"Synthesizing cross-market trade-offs · {status}",
            ),
            lambda usage: ss.token_usage.append({
                "scope": "Global synthesis", "stage": stage,
                "attempt": synthesis_attempt["count"], **usage,
            }),
        )

    raw_synthesis = orchestrator.call_validated_json(
        synthesis_call,
        prompts.GLOBAL_SYNTHESIS_JSON.format(
            evidence_catalog=json.dumps(
                global_evidence, ensure_ascii=False, indent=2
            ),
            context=compact,
        ),
        lambda value: orchestrator.validate_global_json(value, markets, global_evidence),
        repair_context=json.dumps(global_evidence, ensure_ascii=False,
                                  separators=(",", ":")),
    )
    synthesis = orchestrator.normalize_global_synthesis(
        raw_synthesis, markets, global_evidence
    )
    all_warnings.extend(
        f"Global synthesis: {hint}" for hint in raw_synthesis.get("_validation_hints", [])
    )
    progress.progress(1.0, text="Assembling validated campaign brief...")

    ss.market_recommendations = recommendations
    ss.global_synthesis = synthesis
    ss.normalization_warnings = all_warnings
    ss.traces = traces
    return orchestrator.render_global_brief(
        ss.tables, recommendations, synthesis, campaign_flags
    )


colA, colB = st.columns([1, 3])
with colA:
    if st.button("Generate structured strategy brief", type="primary"):
        ss.global_brief = ""
        ss.market_recommendations = {}
        ss.global_synthesis = {}
        ss.normalization_warnings = []
        ss.token_usage = []
        try:
            if provider.startswith("Demo"):
                ss.global_brief = _demo_output("__global__")
            else:
                ss.global_brief = _generate_structured_brief()
        except Exception as exc:
            st.error(f"Structured workflow failed: {llm.explain_error(exc)}")
            st.caption("Each market call is isolated. Rerun after checking the provider connection; "
                       "an incomplete run is never assembled as a final brief.")
        ss.unlocked = False; ss.packs = {}
    if ss.global_brief:
        st.download_button("⬇ Download brief (.md)", prompts.DOC_LEGEND + ss.global_brief,
                           file_name="campaign_strategy_brief.md")
with colB:
    with st.expander("🔍 Multi-call context inspector"):
        st.caption("Each market call sees one compact evidence catalog plus legal choices for that "
                   "market. Source rows remain traceable below but are not duplicated in the prompt.")
        inspect_market = st.selectbox("Inspect market slice", markets, key="inspect_market_slice")
        inspected_context, inspected_trace = context.assemble_market_prompt(
            ss.tables, inspect_market, _campaign_review_items(), upstream=""
        )
        st.json(inspected_trace)
        st.code(inspected_context, language="json")

if ss.token_usage:
    with st.expander("Token diagnostics", expanded=False):
        exact_total = sum(row.get("total_tokens") or 0 for row in ss.token_usage)
        if exact_total:
            st.caption(
                f"Provider-reported total: {exact_total:,} tokens. Repair calls are shown separately."
            )
        else:
            st.caption(
                "This provider did not return exact usage; character counts and duration are still shown."
            )
        st.dataframe(ss.token_usage, hide_index=True)

def _show_diagnostics(doc: str, market: str | None = None,
                      model_hints: list[str] | None = None):
    """Keep non-blocking technical checks available without dominating the report."""
    lint_warnings = _lint_doc(doc, market)
    model_hints = model_hints or []
    total = len(lint_warnings) + len(model_hints)
    if not total:
        return
    with st.expander(f"Technical diagnostics ({total})", expanded=False):
        st.caption("Non-blocking checks for debugging and reviewer audit; the report was generated.")
        if lint_warnings:
            st.markdown("**Output checks**")
            for warning in lint_warnings:
                st.markdown(f"- {warning}")
        if model_hints:
            st.markdown("**Model-output normalization**")
            for hint in model_hints:
                st.markdown(f"- {hint}")


_COLLAPSIBLE_DETAIL = re.compile(
    r"<details>\s*<summary>(?P<title>Decision basis|Scoring methodology)</summary>\s*"
    r"(?P<body>.*?)\s*</details>",
    re.DOTALL,
)
_APPENDIX_SECTION = re.compile(
    r"^##\s+(?P<title>(?:\d+\.\s*)?Appendix[^\n]*)\n(?P<body>.*?)(?=^##\s+|\Z)",
    re.DOTALL | re.MULTILINE,
)


def _render_with_decision_basis(doc: str):
    """Render prose normally and optional audit detail in collapsed native expanders."""
    cursor = 0
    for match in _COLLAPSIBLE_DETAIL.finditer(doc):
        prose = doc[cursor:match.start()].strip()
        if prose:
            st.markdown(prose)
        with st.expander(match.group("title"), expanded=False):
            st.markdown(match.group("body").strip())
        cursor = match.end()
    remainder = doc[cursor:].strip()
    if remainder:
        st.markdown(remainder)


def _render_report(doc: str):
    """Render decision evidence and every Appendix section collapsed by default."""
    cursor = 0
    for match in _APPENDIX_SECTION.finditer(doc):
        _render_with_decision_basis(doc[cursor:match.start()])
        with st.expander(match.group("title").strip(), expanded=False):
            st.markdown(match.group("body").strip())
        cursor = match.end()
    _render_with_decision_basis(doc[cursor:])


if ss.global_brief:
    _show_diagnostics(ss.global_brief, model_hints=ss.normalization_warnings)
    with st.expander("📖 How to read this document (tags, IDs, roles, tiers)"):
        st.markdown(prompts.DOC_LEGEND)
    _render_report(ss.global_brief)
    st.divider()
    st.markdown("#### 🔒 Human review gate")
    st.caption("The PM resolves every decision point below. Stable C-N IDs and the exact "
               "decision status are inherited by market packs. Deferred items remain blockers.")
    review_items = _campaign_review_items()
    if not review_items:
        review_items = [{"_id": "C-1", "type": "REVIEW",
                         "detail": "No decision points - confirm brief to proceed"}]
    options = ["Pending", "Accept recommendation", "Override", "Defer to owner"]
    if st.button(
        "Apply all AI recommendations & unlock market packs",
        type="primary",
        help="Marks every item as reviewed and accepts the recommended handling. "
             "Missing source data and conditional eligibility remain visible blockers.",
    ):
        for item in review_items:
            cid = item["_id"]
            label = f"{cid} [{item['type']}] {item['detail']}"
            ss.decisions[cid] = {
                "issue": label,
                "choice": "Accept recommendation",
                "note": "",
            }
            ss[f"decision_choice_{cid}"] = "Accept recommendation"
        ss.unlocked = True
        st.rerun()
    current_ids = set()
    for item in review_items:
        cid = item["_id"]
        current_ids.add(cid)
        previous = ss.decisions.get(cid, {})
        label = f"{cid} [{item['type']}] {item['detail']}"
        old_choice = previous.get("choice", "Pending")
        choice_key = f"decision_choice_{cid}"
        choice_kwargs = {"key": choice_key}
        if choice_key not in ss:
            choice_kwargs["index"] = options.index(old_choice) if old_choice in options else 0
        choice = st.selectbox(
            label, options, **choice_kwargs,
        )
        note = previous.get("note", "")
        if choice in ("Override", "Defer to owner"):
            note = st.text_input(
                f"{cid} decision note" + (" (required)" if choice == "Override" else ""),
                value=note, key=f"decision_note_{cid}",
                help="State the replacement decision or the owner/follow-up. This is passed downstream.",
            )
        ss.decisions[cid] = {"issue": label, "choice": choice, "note": note.strip()}
    ss.decisions = {k: v for k, v in ss.decisions.items() if k in current_ids}
    pending = [k for k, v in ss.decisions.items()
               if v["choice"] == "Pending" or (v["choice"] == "Override" and not v["note"])]
    if st.button(f"✅ Confirm brief & unlock market packs ({len(pending)} pending)",
                 disabled=bool(pending)):
        ss.unlocked = True
    if pending:
        st.warning(f"{len(pending)} decision point(s) still pending — market packs remain locked.")

# ---------------- Step 4: market packs ----------------
st.divider()
st.subheader("Step 4 · Market execution packs")
if not ss.unlocked:
    st.info("🔒 Locked until the strategy brief is confirmed (Step 3). This gate IS the human-in-the-loop checkpoint.")
else:
    upstream_lines = []
    for cid, decision in ss.decisions.items():
        if decision["choice"] == "Accept recommendation":
            upstream_lines.append(
                f"- REVIEWED: {cid} - PM accepted the recommended handling. "
                f"Any underlying source gap or conditional eligibility remains visible. "
                f"{decision['issue']}")
        elif decision["choice"] == "Override":
            upstream_lines.append(f"- RESOLVED BY PM OVERRIDE: {cid} - {decision['note']}")
        elif decision["choice"] == "Defer to owner":
            suffix = f" Follow-up: {decision['note']}" if decision["note"] else ""
            upstream_lines.append(
                f"- UNRESOLVED / DEFERRED TO OWNER: {cid}. {decision['issue']}.{suffix}")
    upstream = "\n".join(upstream_lines)
    tabs = st.tabs(markets)
    for tab, mkt in zip(tabs, markets):
        with tab:
            ctx, trace = context.assemble_market(ss.tables, mkt, ss.flags, upstream)
            with st.expander(f"🔍 Context inspector — data slice fed to the model for {mkt}"):
                st.json(trace)
                st.code(ctx, language="markdown")
            if st.button(f"Generate {mkt} execution pack", key=f"gen_{mkt}"):
                if provider.startswith("Demo"):
                    ss.packs[mkt] = _demo_output(mkt)
                elif mkt in ss.market_recommendations:
                    ss.packs[mkt] = orchestrator.render_market_pack(
                        ss.tables,
                        ss.market_recommendations[mkt],
                        _campaign_review_items(),
                        upstream,
                    )
                else:
                    st.error("Structured market recommendation is unavailable. Regenerate the "
                             "strategy brief in Step 3; free-form fallback generation is disabled.")
                ss.traces[mkt] = trace
            if mkt in ss.packs:
                _show_diagnostics(ss.packs[mkt], mkt)
                with st.expander("📖 How to read this document (tags, IDs, roles, tiers)"):
                    st.markdown(prompts.DOC_LEGEND)
                _render_report(ss.packs[mkt])
                st.download_button(f"⬇ Download {mkt} pack (.md)", prompts.DOC_LEGEND + ss.packs[mkt],
                                   file_name=f"market_pack_{mkt.replace(' ', '_').lower()}.md",
                                   key=f"dl_{mkt}")


# ---------------- Step 5: launch gate + final export ----------------
st.divider()
st.subheader("Step 5 · Launch gate & final export")
if not ss.packs:
    st.info("🔒 Generate at least one market pack first.")
else:
    st.caption("Second human gate: the final campaign package can only be exported when every "
               "launch item is confirmed. AI fills the checklists; humans flip the switches.")
    GATE_ITEMS = [
        "All NEEDS CONFIRMATION items resolved with owners",
        "Sourcing: city/product supply confirmed for all push cities",
        "CRM: audience eligibility confirmed (incl. 'Selected markets' channels)",
        "Design: P0/P1 assets delivered and localized",
        "Regional teams: copy approved per market",
        "Tracking parameters configured and tested",
        "PM final approval",
    ]
    cols = st.columns(2)
    for i, item in enumerate(GATE_ITEMS):
        with cols[i % 2]:
            ss.launch_checks[item] = st.checkbox(item, value=ss.launch_checks.get(item, False),
                                                 key=f"gate{i}")
    all_ok = all(ss.launch_checks.get(i, False) for i in GATE_ITEMS)
    final_doc = prompts.DOC_LEGEND + "\n\n---\n\n".join(
        [ss.global_brief] + [ss.packs[m] for m in ss.packs])
    st.download_button("📦 Export FINAL campaign package (.md)", final_doc,
                       file_name="final_campaign_package.md", disabled=not all_ok,
                       help=None if all_ok else "Locked until every launch item is checked")
    if not all_ok:
        st.warning(f"{sum(1 for i in GATE_ITEMS if not ss.launch_checks.get(i))} launch item(s) unresolved - export locked.")
