"""
Model on-sale dates, used to refuse a purchase date from before the model existed
("iPhone 17 bought in January 2021"). The dates come from the makers' own announcements and are
kept in backend/data/, outside the knowledge corpus: they are input checks, not coverage sources.

The check errs toward not blocking. A model it does not know, an accessory for a model, a name
with a variant it has no entry for ("Galaxy S25 FE") or a different brand is never blocked.
"""
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.engine.matching import NOT_THE_DEVICE, phrase_pattern, product_text

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RELEASE_DATES_FILE = DATA_DIR / "model_release_dates.json"

# A word right after a matched model name that makes it a different model ("iPhone 16 Pro" is not
# "iPhone 16"). When no longer entry covers it, the model is treated as unknown.
VARIANT_TOKENS = {
    "e", "a", "fe", "edge", "lite", "mini", "plus", "pro", "max", "ultra", "xl", "fold", "flip", "air", "se", "+",
}
_NEXT_TOKEN = re.compile(r"\s*(\+|[a-z0-9]+)")

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def load_release_dates(path: Path = RELEASE_DATES_FILE) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return list(json.load(f).get("models", []))
    except Exception as e:
        print(f"Warning: Failed to load model release dates {path}: {type(e).__name__}")
        return []


def _names(entry: Dict[str, Any]) -> List[str]:
    return [entry["model"], *entry.get("aliases", [])]


def match_model(product_name: str, product_model: Optional[str], product_brand: Optional[str],
                entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The entry whose name matches the product most specifically, or None when the model is unknown."""
    text = product_text(product_name, product_model or "")
    if NOT_THE_DEVICE.search(text):
        return None  # an accessory for a model is not the model
    brand = (product_brand or "").lower()
    best = None  # (matched length, entry, end of match)
    for entry in entries:
        if brand and entry.get("brand", "").lower() not in brand:
            continue
        for name in _names(entry):
            for m in phrase_pattern(name).finditer(text):
                length = m.end() - m.start()
                if best is None or length > best[0]:
                    best = (length, entry, m.end())
    if best is None:
        return None
    _, entry, end = best
    nxt = _NEXT_TOKEN.match(text, end)
    if nxt and (nxt.group(1) in VARIANT_TOKENS or nxt.group(1).isdigit()):
        return None  # a variant or generation with no entry of its own, e.g. "Galaxy S25 FE", "iPhone Air 2"
    return entry


def on_sale_month(entry: Dict[str, Any]) -> date:
    """First day of the on-sale month. The value is YYYY-MM-DD, or YYYY-MM when the page gives the month only."""
    year, month = entry["on_sale"].split("-")[:2]
    return date(int(year), int(month), 1)


def earliest_plausible_purchase(entry: Dict[str, Any]) -> date:
    """First day of the announcement month (pre-orders open at announcement). With only an on-sale
    date, the first day of the month before it."""
    if entry.get("announced"):
        return date.fromisoformat(entry["announced"]).replace(day=1)
    s = on_sale_month(entry)
    return date(s.year - 1, 12, 1) if s.month == 1 else date(s.year, s.month - 1, 1)


def _month_year(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.year}"


def release_problem(case: Any, p_date: date, entries: List[Dict[str, Any]]) -> Optional[str]:
    """A plain message when the purchase date is clearly before the named model went on sale."""
    entry = match_model(case.product_name, case.product_model, case.product_brand, entries)
    if not entry or p_date >= earliest_plausible_purchase(entry):
        return None
    return (
        f"The {entry['model']} went on sale in {_month_year(on_sale_month(entry))}, so it can't have been bought in "
        f"{_month_year(p_date)}. Check the purchase date."
    )
