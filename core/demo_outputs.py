"""Current pre-generated Go China outputs for Demo mode (no API call required)."""

from pathlib import Path


_CONTENT_DIR = Path(__file__).with_name("demo_content")


def _load(name: str) -> str:
    return (_CONTENT_DIR / name).read_text(encoding="utf-8").strip()


GLOBAL_BRIEF = _load("campaign_strategy_brief.md")
HK_PACK = _load("hong_kong.md")
KR_PACK = _load("korea.md")
SG_PACK = _load("singapore.md")
MY_PACK = _load("malaysia.md")
TH_PACK = _load("thailand.md")

DEMO = {
    "__global__": GLOBAL_BRIEF,
    "Hong Kong": HK_PACK,
    "Korea": KR_PACK,
    "Singapore": SG_PACK,
    "Malaysia": MY_PACK,
    "Thailand": TH_PACK,
}

DEMO_NOTE = (
    "Demo mode: current pre-generated Go China output, including the global brief and all "
    "five market execution packs. No API key or model call is used."
)
