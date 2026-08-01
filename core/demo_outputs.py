"""
Pre-generated outputs for Demo mode (no API key required).
Generated from an earlier prompt snapshot against data/go_china.xlsx.
The current validator intentionally audits these frozen examples as regression fixtures.
Demo mode covers: global brief + Hong Kong + Korea packs.
"""

GLOBAL_BRIEF = """# Go China Round 7 — Campaign Strategy Brief
*AI-generated draft. Pending Campaign Ops PM review. Every statement is tagged with its source type.*

## 1. Campaign overview
[FACT - table A] 4-week destination campaign across 5 markets (Hong Kong, Korea, Singapore, Malaysia, Thailand), 10 focus cities, 6 product lines. Objective: destination awareness + campaign traffic + product conversion.

## 2. Decision logic & market tiering

[AI REC] Reading: the investment case splits cleanly - HK and KR carry conversion this round, MY and SG hold steady pending targeted fixes (deal mechanics, hotel trust), TH banks awareness for a future round.

Scoring [DERIVED - quantification standard]. Levels High=3, M-H=2.5, M=2, L-M=1.5, L=1. Product_norm = weighted mix of ALL lines (Hotel .30, Flight .25, A&T .20, Tours .15, Train .10) - never the single best line, so one High cannot mask weak conversion lines. Score = 0.40*UV_norm + 0.25*Growth_norm + 0.35*Product_norm. Tiers: >=0.75 P0, 0.60-0.74 P1, <0.60 P2. [ASSUMPTION] Weights and thresholds are configurable defaults - PM may adjust.

| Market | UV_norm | Growth_norm | Product_norm (weighted mix) | Score | Tier |
|---|---|---|---|---|---|
| Hong Kong | 1.00 | 1.00 | 0.73 (F3 H2 A2 T1 Tr3) | **0.91** | P0 |
| Korea | 0.82 | 0.67 | 0.78 (F2 H2 A3 T3 Tr2) | **0.77** | P0 |
| Malaysia | 0.73 | 0.83 | 0.65 (F2 H2 A2 T2 Tr1.5) | **0.73** | P1 |
| Singapore | 0.76 | 0.50 | 0.68 (F2 H1.5 A3 T2 Tr2) | **0.67** | P1 |
| Thailand | 0.67 | 0.33 | 0.54 (F1.5 H1 A2 T3 Tr1) | 0.54 | P2 |

[DERIVED] Thailand lands at P2 by score alone: the weighted mix prevents its single High (Tours) from masking hotel conversion Low and flight Low-Medium. No manual override needed - the note beside the tier table covers the qualitative context (education-first market).

| Tier | Market | Rationale |
|---|---|---|
| P0 conversion push | Hong Kong | [FACT - B] UV 95, growth +18%, lead time 7-14d. [ASSUMPTION] Short lead time lets the full search-to-book loop complete within the 4-week window. [AI REC] Lead with urgency + deals. |
| P0 conversion push | Korea | [FACT - B/C] Index 78, Attractions & Tours interest both High — clear monetization path beyond flights. [AI REC] Lead with bundled itineraries. |
| P1 steady | Malaysia | [FACT - B] 2nd-highest growth (+15%) but [FACT - C] price-sensitive; worth investment only with confirmed flight+hotel deal mechanics. |
| P1 steady | Singapore | [FACT - C] Good inspiration demand but hotel conversion Low-Medium; solve trust/premium-supply first. |
| P2 nurture | Thailand | [DERIVED] Score 0.54. [FACT - B/C] Lowest growth (+6%), hotel conversion Low. [AI REC] Content-seeding role; KPI = engagement, not GMV. [NEEDS CONFIRMATION] see C-3 below. |

[ASSUMPTION] Tiering assumes the five markets share one budget pool and trade off against each other. If budgets are independent per market, Thailand could run its own cadence. → PM to confirm budget structure.

## 3. Market x city matrix

Cross-market reading [AI REC]: (1) **Shanghai is the Conversion anchor in all five markets** - one shared shelf/KV strategy, localized angles only. (2) **The Chengdu/Chongqing cluster is Conditional in KR, SG and TH pending the same product-depth confirmation** - one sourcing pass unlocks three markets. (3) **Beijing draws interest in four markets but flight readiness caps it at Medium** - run it story-led, never fare-led.

| Market | Conversion cards | Conditional (pending) | Package angle | Content-only | Next action |
|---|---|---|---|---|---|
| Hong Kong | Shenzhen, Guangzhou, Shanghai | - | - | Beijing (story-led) | Confirm SZ/GZ bundles; lock Shanghai fresh angle |
| Korea | Shanghai, Beijing | Chengdu (sourcing depth) | Zhangjiajie (C-1) | - | One sourcing pass: Chengdu depth + Zhangjiajie tours |
| Singapore | Shanghai, Hangzhou (as add-on) | Chengdu (sourcing depth) | - | - | Premium framing; solve hotel trust before push |
| Malaysia | Guangzhou, Shanghai | - | Xi'an (flight readiness) | Beijing | Anchor on flight+hotel value (C-4) |
| Thailand | Shanghai, Guangzhou (supply-ready) | Chengdu, Chongqing (sourcing depth) | - | all others | Content-first per P2 tier (C-3) |

Full role derivations with readiness values: see Appendix (audit).

## 4. Product focus by market

[AI REC] Reading: East Asia buys experiences (attractions/tours lead in KR), Southeast Asia buys value (flight+hotel combos in MY); hotels underperform in three of five markets - that is a campaign-level sourcing intervention, not a per-market fix.

| Market | Lead lines | Secondary (bundle/attach) | Weak - avoid or wrap |
|---|---|---|---|
| Hong Kong | [FACT - C] Flights High, Train/Transfer High | Hotels (Medium) - bundle into city cards ("rail + 2 nights") [AI REC] | Tours (Low) - no standalone tour push |
| Korea | [FACT - C] Attractions & Tours both High | Hotels/Flights (Medium) - wrap into itinerary bundles [AI REC] | - |
| Singapore | [FACT - C] Attractions High | Tours (Medium) | Hotels (Low-Medium) - fix trust/premium supply before pushing [NEEDS CONFIRMATION - Sourcing] |
| Malaysia | [FACT - C] All lines Medium -> lead with flight+hotel value combos [AI REC] | Attractions | Train/Transfer (Low-Medium) |
| Thailand | [FACT - C] Tours High - content showcase only this round [AI REC per P2 tier] | Attractions (Medium) | Hotels (Low), Flights (Low-Medium) - no conversion push |

[AI REC] Sourcing dependencies: HK rail+hotel bundle supply, KR itinerary-bundle depth, SG premium hotel supply - all reflected in the confirmation list.

## 5. Channel and CRM strategy

[AI REC] Reading: KR and TH lack every deep-communication channel except the Content Channel, whose capacity is limited [FACT - H] - their plans depend on content slots being secured early, while HK/SG/MY can fall back on EDM.

[AI REC] App Homepage Banner: all markets (only High-reach channel). App Push: prioritize HK/KR (short lead time x high CTR) - [NEEDS CONFIRMATION] coverage is "Selected markets", per-market eligibility not confirmed (owner: CRM). EDM: SG/MY explanation-heavy messaging (payment trust, deal mechanics) — [FACT - E] EDM does not cover KR/TH. Content Channel: KR and TH only — [FACT - H] Content Center capacity is limited; SG deprioritized despite coverage. Social: awareness support only.

## 6. Resource allocation notes

[AI REC] Reading: the binding constraint this round is content/design capacity, not media reach - allocation below trades breadth for the two P0 markets.

[AI REC] Design capacity → P0 assets (Main KV x5 locales, Homepage Banner) + CRM Headers for HK/SG/MY. Content Center capacity → KR (itinerary guides) and TH (visual inspiration) only.

## 7. Risks and dependencies

[AI REC] Reading: the failure mode most likely to sink the campaign is pushing paid traffic toward cities whose supply is unconfirmed - every dependency below traces back to a sourcing confirmation.

- [FACT - D] Shanghai "too generic without fresh angle" → regional teams to supply local hooks (owner: Regional).
- [FACT - C] MY depends on flight deal mechanics → confirm promo inventory (owner: Flight Sourcing).
- [FACT - H] Push frequency caps + audience overlap → suppression logic required (owner: CRM).
- [ASSUMPTION] Visa/entry policy stable during campaign window → verify before launch (owner: PM).

## 8. NEEDS CONFIRMATION (gates downstream generation)

[AI REC] Highest-value blocker: C-1 and C-4 - they gate the city plans of both P0 markets.

| ID | Issue | Source | Suggested handling | Owner |
|---|---|---|---|---|
| C-1 | Zhangjiajie: KR interest High but hotel/flight readiness Low-Medium, transfer Low | B vs D conflict | Demote to content-only city; alternatively push packaged tours (tours readiness IS High) | Sourcing + PM |
| C-2 | Partner Banner required markets = TBD | G missing | Remove from asset list until partner supply confirmed | Sourcing |
| C-3 | Thailand is a target market but all conversion signals Low | A vs C tension | Confirm TH KPI as engagement/content, not GMV | PM + Regional |
| C-4 | MY flight deal depth unknown — no promo data provided | C (data gap) | Request promo inventory before committing P1 spend | Flight Sourcing |
| C-5 | App Push / Social Post coverage = "Selected markets" — eligibility per market unconfirmed | E (ambiguous) | Confirm eligible market list before committing CRM plans | CRM + Regional |

## 9. Campaign recommendation matrix

Full-dimension synthesis [DERIVED + AI REC] - one decision line per market x priority city. Page modules (table F) and creative assets (table G) are separate dimensions:

| Market | City (role) | Product / angle | Page modules | Channels | Creative assets | Constraint / dependency | Play |
|---|---|---|---|---|---|---|---|
| HK | Shenzhen+Guangzhou (Conversion) | Rail+hotel weekend bundle | Top City Deals, Flight+Rail Deals | Homepage Banner, EDM; Push pending eligibility (C-5) | zh-HK Main KV, CRM Header | Bundle supply - Hotel Sourcing (C-1/HK-1) | Conversion lead |
| HK | Shanghai (Conversion) | Weekend city-break, fresh angle | Top City Deals, Themed Cities (citywalk/food) | Homepage Banner, EDM | City Module Image | Fresh angle - Regional (HK-3) | Conversion #2 |
| KR | Shanghai (Conversion) | Follow-this-itinerary bundles | Attractions & Tickets, Top City Deals | Homepage Banner, Content Channel | Korean Main KV | - | Conversion anchor |
| KR | Zhangjiajie (Package) | Packaged tours only | Attractions & Tickets, Travel Guide | Content Channel, Homepage Banner | Content Cover Image (KO) | Tour depth - Sourcing (C-1) | Package-only |
| KR | Chengdu (Conditional Conversion) | Guided food/panda packages | Themed Cities | Content Channel | City Module Image (KO) | Product depth - Sourcing (KR-1) | Conditional push |
| SG | Shanghai (Conversion) | Premium city-break + attractions | Attractions & Tickets, Top City Deals | EDM, Homepage Banner | CRM Header (EN) | Hotel trust gap - Sourcing | Conversion anchor |
| MY | Guangzhou (Conversion) | Flight+hotel value combos | Flight Deals, Top City Deals | EDM, Homepage Banner, Flight Homepage Banner | CRM Header (EN/MY) | Flight deal depth - Flight Sourcing (C-4) | Value play |
| TH | Shanghai (Conversion supply, P2 market) | Visual inspiration first | Themed Cities, Travel Guide | Homepage Banner, Content Channel | Thai Main KV, City Module Image | Generic-angle risk; nurture KPI - PM (C-3) | Content anchor |

## 10. Launch checklist (campaign level)

| Checklist item | Owner | Why it needs confirmation | Blocking ID |
|---|---|---|---|
| Confirm Zhangjiajie activation role | Sourcing + PM | KR interest is high while hotel and flight readiness are Low-Medium [DERIVED - tables B/D] | C-1 |
| Confirm Partner Banner market coverage | Sourcing | Required markets are TBD [FACT - table G] | C-2 |
| Confirm Thailand campaign KPI | PM + Regional | Thailand is in scope while its conversion signals are weak [DERIVED - tables A/C] | C-3 |
| Confirm Malaysia flight deal depth | Flight Sourcing | Promo inventory is not provided in the source data [NEEDS CONFIRMATION] | C-4 |
| Confirm App Push and Social Post eligibility | CRM + Regional | Coverage is listed only as “Selected markets” [FACT - table E] | C-5 |
| Final campaign approval | PM | The workflow requires final human approval before launch [NEEDS CONFIRMATION] | — |

## Appendix: derived city-role detail (audit)

Role definitions [DERIVED - city role rules]: **Conversion** = in market's interest list AND hotel & flight readiness >= Medium. **Package** = interest present, attractions/tours >= Medium-High but hotel or flight < Medium (packaged tours only). **Content** = interest present, core supply below threshold (inspiration only). Interest City = what users search; Readiness Cluster = supply grouping; unsearched cluster members are extension candidates only.

- HK: Shenzhen, Guangzhou [cluster GZ/SZ] = Conversion (hotel Medium, flight High); Shanghai = Conversion (High/High); Beijing = Conversion by rule (hotel High, flight Medium) - demoted to story-led by risk note.
- KR: Shanghai (High/High), Beijing (High/Medium) = Conversion; Zhangjiajie = Package (attractions High, hotel & flight Low-Medium); Chengdu [cluster CD/CQ] = Conditional Conversion (Medium/Medium + product-depth risk); extension candidate: Chongqing.
- SG: Shanghai, Beijing = Conversion; Hangzhou [cluster HZ/SZ] = Conversion (Medium/Medium, add-on role per risk note); Chengdu = Conditional Conversion; extension candidate: Suzhou.
- MY: Guangzhou [cluster GZ/SZ], Shanghai, Beijing = Conversion; Xi'an = Package (attractions High, flight Low-Medium); extension candidate: Shenzhen.
- TH: Shanghai, Guangzhou = Conversion; Chengdu, Chongqing [cluster CD/CQ] = Conditional Conversion; extension candidate: none in interest gap.
"""

HK_PACK = """# Market Execution Pack — Hong Kong
*Inherits confirmed conclusions: HK = P0. AI-generated draft for Regional team review.*

## 1. Market positioning
[FACT - B] Users know China well; the barrier is "need fresh reasons to travel", not awareness. [AI REC] The play: **novelty + immediacy** — "new reason this weekend", not destination education. Theme: weekend flash trips, high-speed rail hops, limited-time deals.

## 2. City push plan

[AI REC] Reading: conversion is concentrated in the GBA corridor plus Shanghai and nothing waits on user education - this portfolio is deal-ready from day one.

1. **Shenzhen / Guangzhou — conversion lead.** [FACT - B/D] Interest rank #1-2 x flight High x transfer High. Highest-certainty combo.
2. **Shanghai — weekend city break.** [FACT - B/D] Interest #3, all readiness High. [FACT - D risk] "Too generic without fresh angle" → [AI REC] citywalk / new-openings hooks. [NEEDS CONFIRMATION] hook selection by Regional team.
3. **Beijing — content only.** [FACT - D] Flight readiness Medium; keep in Themed Cities, not deal cards.
[AI REC] Hangzhou/Suzhou: not pushed (absent from HK interest signals); mention only as Shanghai add-on in guide content.

## 3. Page module configuration

[AI REC] Reading: the page must answer "why go again, and why this weekend" within two screens - deals lead, inspiration is collapsed, education is demoted (barrier is novelty, not know-how).

1. Hero KV — Traditional Chinese, "週末快閃中國" angle
2. Top City Deals — directly under KV [FACT - F] highest conversion contribution; SZ/GZ/SH cards
3. Flight + Rail Deals — [FACT - C] flight demand High, train/transfer interest High; include cross-border rail (HK-specific configuration)
4. Themed Cities — narrowed to citywalk + food themes
5. Travel Guide — demoted [AI REC] low education value for familiar users
6. Partner Banners — excluded [upstream CONFIRMED C-2]
[AI REC] No standalone hotel module: [FACT - C] hotel conversion Medium with weak city-stay hook → bundle hotels into city cards ("rail + 2 nights") instead. [NEEDS CONFIRMATION] bundle supply w/ Hotel Sourcing.

## 4. CRM plan

[AI REC] Reading: the 7-14 day lead time makes CRM a weekly urgency loop aimed at the next-weekend decision, not a nurture program.

- Segments [ASSUMPTION - windows illustrative, CRM to calibrate]: (a) searched/browsed China content in 90d, no booking — high intent; (b) past-year GBA travelers — repeat. Ringfence: exclude users with existing bookings in window; serve them attractions add-on instead. [AI REC per H suppression constraint]
- Cadence: [FACT - B] lead time 7-14d. [ASSUMPTION] → Tuesday-evening pushes targeting weekend-after-next, all within the 4-week window; ≤1 push/user/week [FACT - H], EDM offset to Thursday. [NEEDS CONFIRMATION] App Push eligibility for HK ("Selected markets" not explicit — owner: CRM); exact recency thresholds for segments are illustrative, CRM to finalize.
- Push copy (zh-HK): 「這個週末,高鐵帶你去深圳食早茶 🥟 酒店快閃價低至7折」 (gloss: "This weekend, high-speed rail to Shenzhen for morning tea — flash hotel deals up to 30% off") [NEEDS CONFIRMATION] discount depth is placeholder.
- Push copy 2 (zh-HK): 「上海 citywalk 新路線出爐 週五夜機出發啱啱好」 (gloss: "New Shanghai citywalk routes — Friday night flight fits perfectly")
- EDM subject: 「香港人週末新去處:3條高鐵路線48小時玩轉大灣區」

## 5. Asset requests (HK-applicable only)

[AI REC] Reading: minimal set protecting design capacity - two P0, two P1; nothing speculative.

| Asset | Priority | Localization | Note |
|---|---|---|---|
| Main KV | P0 | High | zh-HK headline + CTA, weekend visual |
| Homepage Banner | P0 | Medium | "Go China + flash deal" in limited space |
| CRM Header | P1 | High | GBA visual, Tuesday push cadence |
| City Module Image x3 | P1 | Medium | SZ/GZ/SH, base image + localized text |
[AI REC] Content Cover NOT requested — [FACT - G] KR/TH/SG only; preserves design capacity.

## 6. Localization checklist

[AI REC] Highest-risk failure: zh-TW vocabulary leaking into zh-HK copy - it reads foreign to the exact audience this campaign targets.

- [ ] All copy in Traditional Chinese, zh-HK vocabulary (not zh-TW)
- [ ] Prices in HKD; dates DD/MM
- [ ] Weekend/short-trip angle across KV, push, modules [FACT - B]
- [ ] Cross-border rail booking flow notes included

## 7. Needs confirmation (market level)

[AI REC] Biggest blocker: HK-1 - without bundle supply the whole conversion-lead play degrades to plain banners.

| ID | Item | Owner |
|---|---|---|
| HK-1 | SZ/GZ "rail + hotel" bundle supply and discount depth | Hotel Sourcing |
| HK-2 | Cross-border rail inventory adequate for a top placement | Train Sourcing |
| HK-3 | Shanghai fresh-angle selection (citywalk / new openings / events) | Regional team |
| HK-4 | App Push eligibility for HK ("Selected markets") | CRM |
| HK-5 | Audience window definitions (90d search, past-year traveler) to calibrate | CRM |

## 8. Launch checklist (market level)

| Checklist item | Owner | Why it needs confirmation | Blocking ID |
|---|---|---|---|
| Confirm SZ/GZ rail + hotel bundle supply | Hotel Sourcing | Bundle supply and discount depth are not provided [NEEDS CONFIRMATION] | HK-1 |
| Confirm cross-border rail inventory | Train Sourcing | Inventory adequacy for top placement is not provided [NEEDS CONFIRMATION] | HK-2 |
| Select Shanghai fresh angle | Regional team | Shanghai may underperform with generic positioning [FACT - table D] | HK-3 |
| Confirm App Push eligibility for HK | CRM | Coverage is listed only as “Selected markets” [FACT - table E] | HK-4 |
| Confirm CRM audience definitions and windows | CRM | The proposed audience windows are model assumptions [ASSUMPTION] | HK-5 |
| Approve zh-HK localization | Regional team | Traditional Chinese and weekend / short-trip localization is required [FACT - table B] | — |
| Final market approval | PM | The workflow requires final human approval before launch [NEEDS CONFIRMATION] | — |
"""

KR_PACK = """# Market Execution Pack — Korea
*Inherits confirmed conclusions: KR = P0; Zhangjiajie demoted to content-only (PM decision). AI-generated draft.*

## 1. Market positioning
[FACT - B] Barrier: low familiarity with local transport and trip planning. [FACT - C] Attractions & Tours interest both High. [AI REC] The play: **guided confidence** — sell planned, bundled experiences, not raw inventory. Everything answers "how exactly do I do this trip?"

## 2. City push plan

[AI REC] Reading: two safe conversion anchors, one conditional bet (Chengdu) and one high-interest city that stays content-only until sourcing unlocks it - the portfolio converts through certainty, not breadth.

1. **Shanghai — conversion lead.** [FACT - B/D] Interest #1, all core readiness High.
2. **Beijing — conversion #2.** [FACT - D] Hotel High / flight Medium; [FACT - D risk] needs storytelling → pair deals with itinerary content.
3. **Chengdu — packaged angle.** [FACT - B/C] Interest #4 + tours interest High → sell as guided food/panda packages. [FACT - D] product depth may vary → [NEEDS CONFIRMATION] tour inventory w/ Sourcing.
4. **Zhangjiajie — content only** [upstream CONFIRMED]. Inspiration imagery in Themed Cities; no deal cards, no push traffic. [AI REC] If sourcing later confirms packaged-tour depth (tours readiness IS High [FACT - D]), revisit as tour-bundle-only push.

## 3. Page module configuration

[AI REC] Reading: the page must sell certainty - planned itineraries and bundles above raw inventory, guides elevated because the barrier is know-how.

1. Hero KV — Korean, itinerary-promise angle
2. Attractions & Tickets — elevated [FACT - F] "strong for Korea" + [FACT - C] High interest
3. Top City Deals — Shanghai/Beijing cards with "N-day plan" framing
4. Themed Cities — Zhangjiajie + Chengdu inspiration
5. Travel Guide — elevated (transport how-to, payment setup) [FACT - B barrier]
6. Flight Deals — standard position [FACT - C] flight demand Medium
[AI REC] Hotel Brand module: **Conditional** — include only if KA supply for KR is confirmed [FACT - F: "useful if sourcing has strong KA supply"]; not confirmed in provided data → [NEEDS CONFIRMATION] owner: Sourcing. Do not build until confirmed.

## 4. CRM plan

[AI REC] Reading: the 14-30 day lead time splits CRM into two phases - inspiration first, conversion later - a single urgency loop would fire before users are ready.

- Segments [ASSUMPTION - windows illustrative, CRM to calibrate]: (a) China searchers 90d; (b) attraction-page browsers — highest intent given C-table profile. Ringfence: suppress users mid-booking-flow; cap 1 push/week [FACT - H].
- Cadence: [FACT - B] lead time 14-30d → week 1-2 inspiration push (itinerary content), week 3-4 conversion push (deals). Two-phase, unlike HK's weekly urgency loop.
- Push copy (KO): 「상하이 3박4일, 이 일정 그대로 따라만 하세요 ✈️ 항공+호텔+입장권 한번에」 (gloss: "Shanghai 4 days 3 nights — just follow this exact itinerary. Flight + hotel + tickets in one")
- Push copy 2 (KO): 「장자제 그 절경, 가는 방법까지 다 정리했어요」 (gloss: "Zhangjiajie's famous views — we've mapped out exactly how to get there") → links to CONTENT, not deals [upstream CONFIRMED].
- EDM: not available for KR [FACT - E: coverage HK/SG/MY] — exclu

## 5. Asset requests (KR-applicable only)

[AI REC] Reading: Korean-localized minimum set; no CRM Header requested because EDM is not eligible for this market - assets follow channels, not habit.

| Asset | Priority | Localization | Note |
|---|---|---|---|
| Main KV | P0 | High | Korean headline; itinerary-promise angle |
| Homepage Banner | P0 | Medium | Korean |
| City Module Image x3 | P1 | Medium | SH/BJ/CD |
| Content Cover Image | P2 | Medium | [FACT - G] KR-applicable; supports itinerary guides |
[AI REC] CRM Header NOT requested — [FACT - G] HK/SG/MY only (consistent with no EDM for KR).

## 6. Localization checklist

[AI REC] Highest-risk failure: shipping deals without transport/payment guidance - the exact barrier that suppresses KR conversion.

- [ ] All copy in Korean; currency KRW
- [ ] Itinerary/package guidance angle throughout [FACT - B]
- [ ] Transport how-to content (metro apps, DiDi, rail booking) [FACT - B barrier]
- [ ] Payment setup guide (mobile pay for foreigners)

## 7. Needs confirmation (market level)

[AI REC] Biggest blocker: KR-1 - Chengdu is the only growth bet in the portfolio and it hinges on tour inventory.

| ID | Item | Owner |
|---|---|---|
| KR-1 | Chengdu guided-tour inventory depth | Sourcing |
| KR-2 | Content Channel slot for KR itinerary series (capacity limited) | Content Center |
| KR-3 | Zhangjiajie packaged-tour option — revisit trigger defined? | PM + Sourcing |
| KR-4 | App Push eligibility for KR ("Selected markets") | CRM |
| KR-5 | Hotel Brand module: KA supply for KR | Sourcing |
| KR-6 | Audience window definitions (90d search) to calibrate | CRM |

## 8. Launch checklist (market level)

| Checklist item | Owner | Why it needs confirmation | Blocking ID |
|---|---|---|---|
| Confirm Chengdu guided-tour inventory | Sourcing | Product depth may vary [FACT - table D] | KR-1 |
| Confirm Content Channel capacity | Content Center | Content Center capacity is limited [FACT - table H] | KR-2 |
| Define Zhangjiajie packaged-tour trigger | PM + Sourcing | Hotel and flight readiness are below Medium while tours readiness is High [DERIVED - table D] | KR-3 |
| Confirm App Push eligibility for KR | CRM | Coverage is listed only as “Selected markets” [FACT - table E] | KR-4 |
| Confirm Hotel Brand module supply | Sourcing | The module is useful only when KA supply is available [FACT - table F] | KR-5 |
| Confirm CRM audience definitions and windows | CRM | The proposed audience windows are model assumptions [ASSUMPTION] | KR-6 |
| Approve Korean localization | Regional team | Korean itinerary and transport guidance is required [FACT - table B] | — |
| Final market approval | PM | The workflow requires final human approval before launch [NEEDS CONFIRMATION] | — |
"""

DEMO = {"__global__": GLOBAL_BRIEF, "Hong Kong": HK_PACK, "Korea": KR_PACK}

DEMO_NOTE = ("Demo mode: frozen Go China reference output (global + Hong Kong + Korea). "
             "Connect an API key to run the v2.5 streaming evidence workflow live.")
