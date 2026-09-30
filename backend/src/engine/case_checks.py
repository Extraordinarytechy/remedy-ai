"""
Consistency checks between what the user entered and what their receipt shows.

These catch honest mistakes before a claim is prepared (for example a US receipt entered as a
UK purchase). They only run on receipts read by Amazon Textract, because sample data and
manual entry have nothing independent to compare against.

- hard: the claim PDF is refused until the user explicitly confirms the check.
- soft: shown to the user and printed on the PDF; never blocks. The user may have corrected
  an OCR misread, so after review the form is the source of truth.

Country is never inferred from currency. A mismatch only raises a check.
"""
import re
from typing import List, Optional

from dateutil import parser as date_parser

from src.models.schemas import CaseCheck, NormalizedCase

COUNTRY_NAMES = {
    "US": "the United States",
    "GB": "the United Kingdom",
    "UK": "the United Kingdom",
    "IN": "India",
    "CA": "Canada",
    "AU": "Australia",
}

# Currency markers that are consistent with each country. "$" is shared by several countries.
COUNTRY_CURRENCY = {
    "US": {"$", "USD", "US$"},
    "GB": {"£", "GBP"},
    "UK": {"£", "GBP"},
    "IN": {"₹", "INR", "RS"},
    "CA": {"$", "CAD", "C$", "CA$"},
    "AU": {"$", "AUD", "A$", "AU$"},
}

# What a currency marker suggests, for the message only.
CURRENCY_HINT = {
    "$": "dollars ($)",
    "USD": "US dollars",
    "US$": "US dollars",
    "£": "pounds (£)",
    "GBP": "pounds (GBP)",
    "€": "euros (€)",
    "EUR": "euros",
    "₹": "rupees (₹)",
    "INR": "rupees",
    "RS": "rupees",
    "CAD": "Canadian dollars",
    "C$": "Canadian dollars",
    "CA$": "Canadian dollars",
    "AUD": "Australian dollars",
    "A$": "Australian dollars",
    "AU$": "Australian dollars",
}

_MARKER_RE = re.compile(
    r"(?<![A-Za-z])(US\$|CA\$|AU\$|C\$|A\$|USD|GBP|EUR|INR|CAD|AUD|Rs\.?)(?![A-Za-z])|([$£€₹])",
    re.IGNORECASE,
)


def detect_currency_marker(text: Optional[str]) -> Optional[str]:
    """Returns the first currency symbol or ISO code printed in `text`, normalised, or None."""
    if not text:
        return None
    m = _MARKER_RE.search(text)
    if not m:
        return None
    return (m.group(1) or m.group(2)).upper().rstrip(".")


def _norm(s: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _iso(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    try:
        return date_parser.parse(s).date().isoformat()
    except (ValueError, OverflowError):
        return None


def run_checks(case: NormalizedCase) -> List[CaseCheck]:
    r = case.receipt_data
    if not r or r.source != "textract":
        return []

    checks: List[CaseCheck] = []
    confirmed = set(case.confirmed_checks or [])
    country = (case.purchase_country or "").strip().upper()

    # 1. Currency printed on the receipt vs the country chosen (hard).
    marker = (r.currency_evidence or "").upper() or None
    expected = COUNTRY_CURRENCY.get(country)
    if marker and expected and marker not in expected:
        place = COUNTRY_NAMES.get(country, country)
        checks.append(CaseCheck(
            id="country_currency",
            severity="hard",
            message=(
                f"Your receipt shows prices in {CURRENCY_HINT.get(marker, marker)}, but you chose {place} as the "
                "country of purchase. Consumer law depends on where you bought it, so please confirm the country."
            ),
            confirm_label=f"I confirm this was bought in {place}.",
            confirmed="country_currency" in confirmed,
        ))

    # 2. Receipt date vs purchase date entered (soft).
    receipt_date = _iso(r.purchase_date)
    entered_date = _iso(case.purchase_date)
    if receipt_date and entered_date and receipt_date != entered_date:
        checks.append(CaseCheck(
            id="receipt_date",
            severity="soft",
            message=(
                f"The receipt date reads {receipt_date}, but the purchase date entered is {entered_date}. "
                "The entered date is used. Check it matches your receipt."
            ),
        ))

    # 3. Receipt store vs store entered (soft).
    rs, es = _norm(r.store_name), _norm(case.retailer)
    if rs and es and rs not in es and es not in rs:
        checks.append(CaseCheck(
            id="receipt_store",
            severity="soft",
            message=(
                f"The receipt names the store as \"{r.store_name}\", but the store entered is \"{case.retailer}\". "
                "A claim under consumer law is made against the store that sold the item."
            ),
        ))

    return checks
