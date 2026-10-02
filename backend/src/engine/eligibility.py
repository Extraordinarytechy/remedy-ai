import json
import re
from pathlib import Path
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Tuple
from dateutil.relativedelta import relativedelta

from src.models.schemas import (
    CaseTimeline,
    InputError,
    NormalizedCase,
    MatchedRoute,
    NoMatchReason,
    ProvenanceChain,
    RemedyEvaluation,
)
from src.engine.case_checks import run_checks
from src.engine.matching import (
    NOT_THE_DEVICE,
    has_accessory_word,
    main_product,
    phrase_pattern,
    product_text,
    without_official_parts,
)
from src.engine.release_dates import load_family_floors, load_release_dates, release_problem

# Base path to knowledge corpus
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge"

DISCLAIMER_NEXT_STEPS_MATCHED = [
    "Review specific mandatory conditions and potential exceptions for each matched route.",
    "Download the Claim Summary PDF and attach verified receipts and photo evidence.",
    "Contact the designated provider (service center, claims administrator, or retailer) directly.",
]


def load_knowledge_records(knowledge_dir: Path = KNOWLEDGE_DIR) -> Dict[str, Dict[str, Any]]:
    """Loads all primary-source JSON knowledge records from the knowledge corpus."""
    records: Dict[str, Dict[str, Any]] = {}
    if not knowledge_dir.exists():
        return records

    for file_path in sorted(knowledge_dir.glob("**/*.json")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "id" in data:
                    records[data["id"]] = data
        except Exception as e:
            print(f"Warning: Failed to load knowledge record {file_path}: {e}")
    return records


def parse_date(date_str: str) -> date:
    """Strict calendar date, YYYY-MM-DD. Ambiguous forms such as 03/04/2024 are rejected,
    because reading them the wrong way round would move a deadline by months."""
    s = (date_str or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        raise ValueError(f"'{date_str}' is not a YYYY-MM-DD date")
    return date.fromisoformat(s)


# Symptom matching: a fault description is read clause by clause, and a keyword preceded (within five
# words) by one of these denials doesn't count. A bare "no" denies a keyword too ("there is no vertical
# line"), except a keyword that is itself a "no ..." symptom, such as "no preview".
CLAUSE_SPLIT = re.compile(r"[.;:!?,()]|\bbut\b|\band\b|\bthough\b|\balthough\b")
NEGATION = re.compile(
    r"\b(not|never|isn't|wasn't|aren't|doesn't|don't|didn't|hasn't|haven't|without|"
    r"no (?:problems?|issues?|sign) (?:with|of))\b"
)
BARE_NO = re.compile(r"\bno\b")

# Purchases older than this, measured from the claim date, are refused as input errors.
MAX_PURCHASE_AGE_YEARS = 30

# Statuses that describe a possible option the user must check before acting on it. They stay in the
# result with their explanation, but no claim PDF, letter or reminder is offered for them.
NOT_ACTIONABLE = {"NEEDS_REVERIFICATION", "NEEDS_CONFIRMATION"}


def is_actionable(route: MatchedRoute) -> bool:
    return route.status not in NOT_ACTIONABLE


_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_PLACE = {"US": "the U.S.", "GB": "the UK", "UK": "the UK", "CA": "Canada", "IN": "India", "AU": "Australia"}


def _day(d: date) -> str:
    """'25 Sep 2025': the same order in every country, so it can't be misread."""
    return f"{d.day} {_MONTH_ABBR[d.month - 1]} {d.year}"


def _place(code: str) -> str:
    return _PLACE.get((code or "").upper(), "this country")


def _join(items: List[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _places(codes: List[str]) -> str:
    return _join([_place(c) for c in codes]) if codes else "some countries"


def _brand(record: Dict[str, Any]) -> str:
    return record.get("brand_short") or (record.get("issuer_or_brand") or "The maker").split()[0]


def add_years(d: date, years: float) -> date:
    """Adds whole years (and any fractional remainder as months) to a date, handling Feb 29."""
    whole = int(years)
    months = int(round((years - whole) * 12))
    return d + relativedelta(years=whole, months=months)


class EligibilityEngine:
    def __init__(self, knowledge_dir: Optional[Path] = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self.records = load_knowledge_records(self.knowledge_dir)
        self.release_dates = load_release_dates()
        self.family_floors = load_family_floors()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def evaluate(
        self,
        case: NormalizedCase,
        source_status: Optional[Dict[str, Dict[str, Any]]] = None,
        source_status_unavailable: bool = False,
    ) -> RemedyEvaluation:
        """
        Evaluates a NormalizedCase against the closed-world knowledge corpus.
        Enforces strict evidence grounding: no routes are generated unless
        explicitly verified in primary-source records. `source_status` is the latest
        Source Watch result; a route whose source is unreachable or delisted is downgraded.
        `source_status_unavailable` means the status could not be read: every route is then
        treated as unverified rather than as healthy.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            p_date = parse_date(case.purchase_date)
            f_date = parse_date(case.failure_date)
            as_of = (
                parse_date(case.evaluation_date)
                if case.evaluation_date
                else datetime.now(timezone.utc).date()
            )
        except Exception:
            # The parser's own wording isn't shown: it means nothing to the person who typed the date.
            return self._invalid(
                case, now_iso, None,
                "We couldn't read one of the dates. Check the purchase and failure dates.",
                code="unreadable_date",
            )

        if p_date > as_of:
            return self._invalid(
                case, now_iso, as_of,
                f"The purchase date ({p_date.isoformat()}) is in the future. The claim date is {as_of.isoformat()}.",
                code="future_date",
            )
        if f_date < p_date:
            return self._invalid(
                case, now_iso, as_of,
                f"Failure date ({f_date.isoformat()}) is before purchase date ({p_date.isoformat()}).",
                code="failure_before_purchase",
            )
        if f_date > as_of:
            return self._invalid(
                case, now_iso, as_of,
                f"The failure date ({f_date.isoformat()}) is in the future. The claim date is {as_of.isoformat()}.",
                code="future_date",
            )
        earliest = as_of - relativedelta(years=MAX_PURCHASE_AGE_YEARS)
        if p_date < earliest:
            return self._invalid(
                case, now_iso, as_of,
                f"The purchase date ({p_date.isoformat()}) is more than {MAX_PURCHASE_AGE_YEARS} years before the "
                f"claim date. RemedyAI checks purchases made on or after {earliest.isoformat()}.",
                code="too_old",
            )
        release_issue = release_problem(case, p_date, self.release_dates, self.family_floors)
        if release_issue:
            return self._invalid(
                case, now_iso, as_of, release_issue,
                code="before_release",
                next_steps=["Check the purchase date and the model name."],
            )

        days_elapsed = (f_date - p_date).days
        years_elapsed = days_elapsed / 365.25
        months_elapsed = days_elapsed / 30.4375

        matched_routes: List[MatchedRoute] = []
        notes: List[str] = []

        # 0. Manufacturer's own warranty, while it still runs (data-driven)
        for record in self.records.values():
            if record.get("category") != "manufacturer_warranty":
                continue
            route, note = self._evaluate_manufacturer_warranty(case, record, p_date, f_date, as_of)
            if route:
                matched_routes.append(route)
            if note:
                notes.append(note)

        # 1. Manufacturer service programs (data-driven: every record in the category)
        for record in self.records.values():
            if record.get("category") != "manufacturer_service_program":
                continue
            route, note = self._evaluate_service_program(case, record, p_date, as_of, years_elapsed)
            if route:
                matched_routes.append(route)
            if note:
                notes.append(note)

        # 2. Payment-card extended warranty
        visa_record = self.records.get("visa_infinite_extended_warranty_us")
        if visa_record:
            route, note = self._evaluate_visa_extended_warranty(case, visa_record, years_elapsed, p_date, f_date, as_of)
            if route:
                matched_routes.append(route)
            if note:
                notes.append(note)

        # 3. Statutory consumer law
        uk_record = self.records.get("uk_cra_2015_goods")
        if uk_record:
            route, note = self._evaluate_uk_consumer_rights(
                case, uk_record, p_date, as_of, years_elapsed, months_elapsed
            )
            if route:
                matched_routes.append(route)
            if note:
                notes.append(note)

        for route in matched_routes:
            st = (source_status or {}).get(route.route_id)
            if st:
                self._apply_source_status(route, st)
            elif source_status_unavailable:
                route.status = "NEEDS_REVERIFICATION"
                route.provenance.exceptions.insert(
                    0,
                    "RemedyAI could not load a recent automatic check of this source (it is missing or "
                    "more than 36 hours old). Check the official page before relying on this option.",
                )
            elif source_status:
                # The latest check exists but has no entry for this source (for example a record added
                # after that run): it has never been checked automatically, so it isn't trusted yet.
                route.status = "NEEDS_REVERIFICATION"
                route.provenance.exceptions.insert(
                    0,
                    "This source has not been checked automatically yet. Check the official page before "
                    "relying on this option.",
                )
            if route.deadline:
                route.days_left = (parse_date(route.deadline) - as_of).days

        timeline = CaseTimeline(
            purchase_date=p_date.isoformat(),
            failure_date=f_date.isoformat(),
            claim_date=as_of.isoformat(),
            months_before_failure=round(months_elapsed, 1),
        )

        # Receipt vs form consistency. An unconfirmed hard check puts every option that depends on
        # where the item was bought on hold and blocks the claim PDF.
        checks = run_checks(case)
        pending_hard = [c for c in checks if c.severity == "hard" and not c.confirmed]
        for route in matched_routes:
            if route.route_type == "statutory_consumer_law" and any(c.id == "country_currency" for c in pending_hard):
                route.status = "NEEDS_CONFIRMATION"
                route.provenance.exceptions.insert(
                    0, next(c.message for c in pending_hard if c.id == "country_currency")
                )
        # The claim PDF needs every hard check confirmed and, when options were found, at least one
        # option the user can act on now. Options that must be checked first are never in the letter.
        pdf_allowed = not pending_hard and (not matched_routes or any(is_actionable(r) for r in matched_routes))

        # Closed-world determination
        if matched_routes:
            return RemedyEvaluation(
                case_id=case.case_id,
                evaluated_at=now_iso,
                evaluation_date=as_of.isoformat(),
                has_coverage=True,
                matched_routes=matched_routes,
                notes=notes,
                next_steps=list(DISCLAIMER_NEXT_STEPS_MATCHED),
                timeline=timeline,
                checks=checks,
                pdf_allowed=pdf_allowed,
            )

        next_steps = [
            "Contact the manufacturer to request an out-of-warranty courtesy inspection or goodwill repair.",
            "Verify if another credit card with extended warranty protections was used for the purchase.",
            "Check for independent certified repair options if official replacement cost exceeds item value.",
        ]
        warranty_record_applies = any(
            r.get("category") == "manufacturer_warranty"
            and (not r.get("countries") or (case.purchase_country or "").upper() in r["countries"])
            and self._device_matches(case, r)
            for r in self.records.values()
        )
        if years_elapsed <= case.original_warranty_years and not warranty_record_applies:
            notes.append(
                f"The failure occurred {years_elapsed:.2f} years after purchase, which appears to be inside the "
                f"{case.original_warranty_years:.1f}-year original manufacturer warranty. That warranty is not part of "
                "the RemedyAI source corpus, so it is not scored here; contact the manufacturer under the standard warranty."
            )
            next_steps.insert(0, "Contact the manufacturer first: the failure appears to fall within the original warranty period.")

        return RemedyEvaluation(
            case_id=case.case_id,
            evaluated_at=now_iso,
            evaluation_date=as_of.isoformat(),
            has_coverage=False,
            unmatched_reason=(
                "NO VERIFIED COVERAGE FOUND in current evidence corpus. "
                "No manufacturer service program, qualifying payment-card extended warranty benefit, "
                "or applicable statutory route in the verified source corpus matches the submitted documentation."
            ),
            no_match_reasons=self._no_match_reasons(case, p_date, f_date, as_of, years_elapsed),
            notes=notes,
            next_steps=next_steps,
            timeline=timeline,
            checks=checks,
            pdf_allowed=pdf_allowed,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _invalid(
        case: NormalizedCase,
        now_iso: str,
        as_of: Optional[date],
        reason: str,
        code: InputError,
        next_steps: Optional[List[str]] = None,
    ) -> RemedyEvaluation:
        return RemedyEvaluation(
            case_id=case.case_id,
            evaluated_at=now_iso,
            evaluation_date=as_of.isoformat() if as_of else None,
            has_coverage=False,
            unmatched_reason=f"INVALID INPUT: {reason}",
            input_error=code,
            next_steps=next_steps or ["Check the purchase and failure dates."],
            # Refused input never gets a claim PDF.
            pdf_allowed=False,
        )

    @staticmethod
    def _apply_source_status(route: MatchedRoute, st: Optional[Dict[str, Any]]) -> None:
        """Attach the latest Source Watch result and downgrade routes whose source is in doubt."""
        if not st:
            return
        route.source_check = {
            k: st.get(k)
            for k in ("checked_at", "http_status", "reachable", "last_changed_at", "human_verified_at", "listed_on_apple_index", "key_text_present")
            if k in st
        }
        checked = (st.get("checked_at") or "")[:10]
        warnings = []
        if st.get("reachable") is False:
            warnings.append(
                f"Source Watch could not load the source page on {checked} (HTTP {st.get('http_status')}). "
                "Re-verify the source before relying on this route."
            )
        if st.get("key_text_present") is False:
            warnings.append(
                f"Source Watch could not find the wording this option relies on in the source page on {checked}. "
                "The terms may have changed; re-verify before relying on this route."
            )
        if st.get("listed_on_apple_index") is False:
            warnings.append(
                f"Source Watch found that this program is not listed on Apple's service-program index as of {checked}. "
                "It may have ended; confirm with Apple before relying on it."
            )
        elif st.get("apple_index_ok") is False:
            warnings.append(
                f"Source Watch could not read Apple's service-program index on {checked}, so it could not confirm "
                "this program is still running. Confirm with Apple before relying on it."
            )
        changed = (st.get("last_changed_at") or "")[:10]
        verified = (st.get("human_verified_at") or "")[:10]
        if changed and verified and changed > verified:
            # Any change after the last verification, whole page or watched wording: the terms
            # haven't been re-read since, so the route can't be relied on until they are.
            warnings.append(
                f"The source page's text changed on {changed}, after it was last verified on {verified}. "
                "The terms may be different now; re-verify before relying on this route."
            )
        if warnings:
            route.status = "NEEDS_REVERIFICATION"
            route.provenance.exceptions[:0] = warnings

    @staticmethod
    def _device_matches(case: NormalizedCase, record: Dict[str, Any]) -> bool:
        # Only the product itself counts: in "iMac with Magic Keyboard" the iMac is the device, and
        # the keyboard that came with it neither rules it out nor gets its own record.
        name = main_product(product_text(case.product_name, case.product_model))
        # A brand the user named that isn't the record's brand rules the record out.
        record_brand = (record.get("issuer_or_brand") or "").split()[0].lower() if record.get("issuer_or_brand") else ""
        if case.product_brand and record_brand and record_brand not in case.product_brand.lower():
            return False
        for excluded in record.get("excluded_devices", []):
            if excluded.lower() in name:
                return False
        # Whole-word match, so "iPhone 12" doesn't match "iPhone 120" and "iPad" doesn't match a longer word.
        patterns = [phrase_pattern(dev) for dev in sorted(record.get("applicable_devices", []), key=len, reverse=True)]
        if not any(p.search(name) for p in patterns):
            return False
        # Accessory words count only outside the record's own terms and Apple's own product names:
        # "Magic Keyboard" is a device the accessory warranty names and "Aluminum Case" is part of an
        # Apple Watch's name, while "iPhone 17 case" and "Apple Watch band" are not the device.
        rest = name
        for p in patterns:
            rest = p.sub(" ", rest)
        return not NOT_THE_DEVICE.search(without_official_parts(rest, name))

    @staticmethod
    def _symptom_matches(case: NormalizedCase, record: Dict[str, Any]) -> bool:
        """
        A program symptom keyword counts only where it isn't denied earlier in the same clause: "not a vertical
        line", "the screen doesn't flicker" and "no problem with the rear camera" don't match. Keywords
        match at a word start, so "flicker" also matches "flickering" but "line" doesn't match "outline".
        """
        desc = case.defect_description.lower().replace("\u2019", "'")
        for clause in CLAUSE_SPLIT.split(desc):
            for k in record.get("symptom_keywords", []):
                for m in re.finditer(rf"(?<![a-z0-9]){re.escape(k.lower())}", clause):
                    before = " ".join(clause[: m.start()].split()[-5:])
                    if NEGATION.search(before):
                        continue
                    # "there is no vertical line" denies the symptom, unless the keyword is itself a
                    # "no ..." symptom such as "no preview" or "no power".
                    if not k.lower().startswith("no ") and BARE_NO.search(before):
                        continue
                    return True
        return False

    # ------------------------------------------------------------------
    # Why nothing matched
    # ------------------------------------------------------------------
    def _no_match_reasons(
        self, case: NormalizedCase, p_date: date, f_date: date, as_of: date, years_elapsed: float
    ) -> List[NoMatchReason]:
        """
        Plain reasons, one per option type, for a valid case with no route. Each reason re-applies the
        evaluators' own rules to the records, so it states only what the data says. It never implies
        coverage: it says what RemedyAI checked and why that did not fit.
        """
        reasons: List[NoMatchReason] = []
        country = (case.purchase_country or "").strip().upper()
        name = product_text(case.product_name, case.product_model)
        records = list(self.records.values())

        accessory = has_accessory_word(name) and not any(self._device_matches(case, r) for r in records)
        if accessory:
            reasons.append(NoMatchReason(
                code="accessory",
                message="This looks like an accessory or an app, not the device itself. If the device broke, enter its name.",
            ))
        else:
            reasons.append(self._maker_warranty_reason(case, records, country, p_date, f_date, as_of))
            reasons.append(self._repair_program_reason(case, records, name, p_date, as_of))

        card = self._card_reason(case, country, p_date, f_date, as_of, years_elapsed)
        if card:
            reasons.append(card)

        law = self._consumer_law_reason(case, country, p_date, as_of)
        if law:
            reasons.append(law)
        return reasons

    def _maker_warranty_reason(self, case, records, country, p_date, f_date, as_of) -> NoMatchReason:
        warranties = [r for r in records if r.get("category") == "manufacturer_warranty"]
        matched = [r for r in warranties if self._device_matches(case, r)]
        in_country = [r for r in matched if not r.get("countries") or country in r["countries"]]
        for r in in_country:
            years = float(r.get("warranty_years", 1))
            end = add_years(p_date, years)
            if f_date > end or as_of > end:
                return NoMatchReason(
                    code="maker_warranty_ended",
                    message=f"{_brand(r)}'s {years:g}-year warranty ended on {_day(end)}, "
                            f"{years:g} year{'s' if years != 1 else ''} after the purchase date.",
                )
        if matched and not in_country:
            r = matched[0]
            return NoMatchReason(
                code="maker_warranty_country",
                message=f"RemedyAI has {_brand(r)}'s warranty for purchases in {_places(r.get('countries', []))} only. "
                        f"Purchases in {_place(country)} are not covered yet.",
            )
        brands = sorted({_brand(r) for r in warranties})
        return NoMatchReason(
            code="no_maker_warranty",
            message=f"RemedyAI has no maker's warranty that names this product. It covers some "
                    f"{_join(brands)} products so far.",
        )

    def _repair_program_reason(self, case, records, name, p_date, as_of) -> NoMatchReason:
        programs = [r for r in records if r.get("category") == "manufacturer_service_program"]
        window, unclear, other_fault = None, None, None
        for r in programs:
            device = self._device_matches(case, r)
            symptom = self._symptom_matches(case, r)
            program = r["program_name"]
            if device and symptom and window is None:
                mfg_start = r.get("manufacturing_window_start")
                if mfg_start and p_date < parse_date(mfg_start):
                    window = (f"{program} matches this model and fault, but it covers only units made from "
                              f"{_day(parse_date(mfg_start))}, and this one was bought before then.")
                else:
                    end = add_years(p_date, float(r.get("coverage_window_years_from_sale", 3)))
                    if as_of > end:
                        window = (f"{program} matches this model and fault, but its "
                                  f"{float(r.get('coverage_window_years_from_sale', 3)):g}-year window closed on {_day(end)}.")
            family = r.get("model_family")
            if (not device and symptom and family and unclear is None
                    and phrase_pattern(family).search(name)
                    and not any(x.lower() in name for x in r.get("excluded_devices", []))):
                model = (r.get("display_names") or [family])[0]
                unclear = (f"{program} covers only the {model}. If yours is that model, "
                           "add the year or chip to the product name.")
            if device and not symptom and other_fault is None:
                other_fault = f"{program} covers only this fault: {r.get('symptom', '').rstrip('.')}."
        if window:
            return NoMatchReason(code="repair_program_window", message=window)
        if unclear:
            return NoMatchReason(code="repair_program_model_unclear", message=unclear)
        if other_fault:
            return NoMatchReason(code="repair_program_other_fault", message=other_fault)
        return NoMatchReason(
            code="no_repair_program",
            message="No free repair program RemedyAI knows of covers this model and fault.",
        )

    def _card_reason(self, case, country, p_date, f_date, as_of, years_elapsed) -> Optional[NoMatchReason]:
        record = self.records.get("visa_infinite_extended_warranty_us")
        if not record:
            return None
        if "visa infinite" not in (case.payment_method or "").lower() or (
            record.get("countries") and country not in record["countries"]
        ):
            return NoMatchReason(
                code="card_not_covered",
                message="Card benefit: RemedyAI checks Visa Infinite cards used for U.S. purchases only.",
            )
        orig = case.original_warranty_years
        max_eligible = float(record.get("max_eligible_manufacturer_warranty_years", 3.0))
        if orig > max_eligible:
            return NoMatchReason(
                code="card_warranty_too_long",
                message=f"Card benefit: Visa Infinite extends makers' warranties of {max_eligible:g} years or less. "
                        f"This item's warranty is {orig:g} years.",
            )
        if years_elapsed <= orig:
            return NoMatchReason(
                code="card_inside_warranty",
                message=f"Card benefit: the fault appeared during the original {orig:g}-year warranty. "
                        "The Visa Infinite extension covers faults only after that warranty ends.",
            )
        extended_end = add_years(p_date, orig + float(record.get("benefit_extension_years", 1.0)))
        return NoMatchReason(
            code="card_window_ended",
            message=f"Card benefit: the Visa Infinite extra year ended on {_day(extended_end)}.",
        )

    def _consumer_law_reason(self, case, country, p_date, as_of) -> Optional[NoMatchReason]:
        record = self.records.get("uk_cra_2015_goods")
        if not record:
            return None
        if country not in ("GB", "UK"):
            return NoMatchReason(
                code="consumer_law_uk_only",
                message="Consumer law: RemedyAI covers purchases from UK stores only so far.",
            )
        by_region = record.get("limitation_years_by_region", {})
        years = float(by_region.get(case.uk_region, record.get("claim_limitation_years", 6))) if case.uk_region \
            else float(record.get("claim_limitation_years", 6))
        end = add_years(p_date, years)
        if as_of > end:
            return NoMatchReason(
                code="consumer_law_time_limit",
                message=f"The {years:g}-year time limit to claim under UK consumer law ended on {_day(end)}.",
            )
        return None

    # ------------------------------------------------------------------
    # Route evaluators
    # ------------------------------------------------------------------
    def _evaluate_manufacturer_warranty(
        self,
        case: NormalizedCase,
        record: Dict[str, Any],
        p_date: date,
        f_date: date,
        as_of: date,
    ) -> Tuple[Optional[MatchedRoute], Optional[str]]:
        country = (case.purchase_country or "").strip().upper()
        if record.get("countries") and country not in record["countries"]:
            return None, None
        if not self._device_matches(case, record):
            return None, None

        program = record["program_name"]
        # Brand-specific wording lives in the record, so a new maker's warranty is a new JSON file.
        brand = record.get("brand_short") or (record.get("issuer_or_brand") or "The manufacturer").split()[0]
        years = float(record.get("warranty_years", 1))
        period = f"{years:g}-year"
        warranty_end = add_years(p_date, years)
        if f_date > warranty_end:
            return None, None  # the fault appeared after the warranty; other routes may apply
        if as_of > warranty_end:
            return None, (
                f"{program}: the fault appeared on {f_date.isoformat()}, inside the warranty, but the warranty "
                f"ended on {warranty_end.isoformat()} and claims must be made during it. Contact {brand} anyway, "
                "and check the other options below."
            )

        exceptions = list(record.get("exclusions_and_caveats", []))
        if case.visual_evidence and case.visual_evidence.visible_physical_damage:
            exceptions.insert(
                0,
                record.get("visible_damage_note")
                or f"Visible physical damage was recorded in the evidence photo. {brand}'s warranty does not cover "
                "damage caused by accident or other external causes.",
            )
        days_left = (warranty_end - as_of).days
        evidence_items = [
            f"Warranty ends {warranty_end.isoformat()} ({years:g} year{'s' if years != 1 else ''} from the "
            f"{p_date.isoformat()} purchase); {days_left} days remain as of the claim date {as_of.isoformat()}.",
            f"Dates: purchased {p_date.isoformat()}, fault appeared {f_date.isoformat()}, claim date {as_of.isoformat()}.",
            f"Device named in case: {case.product_name} (bought in {country}).",
            f"Reported fault: '{case.defect_description}'.",
        ]
        # The remedy promised is the record's own: a refund is named only when the warranty offers one.
        remedy = (record.get("remedy") or "").lower()
        promise = (
            f"{brand} will repair, replace or refund at its option" if "refund" in remedy
            else f"{brand} will repair or replace it"
        )
        provenance = ProvenanceChain(
            claim=f"Covered by the {program} if the fault is a defect: {promise}.",
            why_matched=(
                f"The case names a device this warranty covers ({case.product_name}), bought in {country}, and the claim "
                f"date {as_of.isoformat()} is inside the {period} warranty period, which ends {warranty_end.isoformat()}."
            ),
            evidence=evidence_items,
            source_citation=program,
            source_url=record["source_url"],
            conditions=record.get("mandatory_conditions", []),
            exceptions=exceptions,
        )
        return (
            MatchedRoute(
                route_id=record["id"],
                route_type="manufacturer_warranty",
                title=program,
                provider=record["issuer_or_brand"],
                status="POTENTIALLY_ELIGIBLE",
                summary=f"{record.get('issuer_or_brand')} warrants the product against {record.get('coverage', '').lower()}. "
                        f"Remedy: {record.get('remedy')}.",
                primary_source={"title": program, "url": record["source_url"], "verified_at": record.get("verified_at", "")},
                provenance=provenance,
                recommended_action=(
                    record.get("claim_action")
                    or f"Contact {brand} support before {{deadline}}. Back up the device first and have proof of purchase ready."
                ).replace("{deadline}", warranty_end.isoformat()),
                deadline=warranty_end.isoformat(),
                deadline_label=f"{brand}'s warranty ends",
                related_sources=list(record.get("related_sources", [])),
                claim_to=record.get("claim_to") or f"{brand} Support",
            ),
            None,
        )

    def _evaluate_service_program(
        self,
        case: NormalizedCase,
        record: Dict[str, Any],
        p_date: date,
        as_of: date,
        years_elapsed: float,
    ) -> Tuple[Optional[MatchedRoute], Optional[str]]:
        if not self._device_matches(case, record) or not self._symptom_matches(case, record):
            return None, None

        program = record["program_name"]

        # A unit sold before the affected manufacturing window started cannot be an affected unit.
        mfg_start = record.get("manufacturing_window_start")
        if mfg_start and p_date < parse_date(mfg_start):
            return None, (
                f"{program}: not applicable. Purchase date {p_date.isoformat()} is before the affected "
                f"manufacturing window ({record.get('manufacturing_window')}), so this unit cannot be an affected device."
            )

        window_years = float(record.get("coverage_window_years_from_sale", 3))
        coverage_end = add_years(p_date, window_years)
        if as_of > coverage_end:
            return None, (
                f"{program}: device and symptom match, but the {window_years:.0f}-year program window "
                f"from retail sale closed on {coverage_end.isoformat()} (evaluated as of {as_of.isoformat()})."
            )

        requires_serial = bool(record.get("requires_serial_check"))
        status = "PENDING_SERIAL_VERIFICATION" if requires_serial else "ELIGIBLE_PENDING_INSPECTION"

        exceptions = list(record.get("exclusions_and_caveats", []))

        # First retail sale can lag manufacture, so a later purchase is not ruled out, but more than a
        # year after the last affected unit was made it is unlikely. Without a serial check to settle
        # it, the status is lowered.
        mfg_end = record.get("manufacturing_window_end")
        if mfg_end and p_date > parse_date(mfg_end) + relativedelta(years=1):
            exceptions.insert(
                0,
                f"Bought on {p_date.isoformat()}, more than a year after the last affected units were made "
                f"({parse_date(mfg_end).isoformat()}). New stock from that period is unlikely by then, so this "
                "device may not be one of the affected units.",
            )
            if not requires_serial:
                status = "POTENTIALLY_ELIGIBLE"

        # A program the record itself marks as no longer listed by Apple is never presented as live,
        # whether or not the latest Source Watch result is available.
        if not record.get("listed_on_apple_service_programs_index", True):
            status = "NEEDS_REVERIFICATION"
            if record.get("index_note"):
                exceptions.insert(0, record["index_note"])
        if case.visual_evidence and case.visual_evidence.physical_damage_severity in ["screen_cracked", "severe"]:
            exceptions.insert(
                0,
                "Visible physical damage was recorded in the evidence photos. Per the program terms, damage that "
                "impairs the repair must be resolved first and may incur a separate fee.",
            )

        days_left = (coverage_end - as_of).days
        evidence_items = [
            f"Program window ({window_years:.0f} years from retail sale) ends {coverage_end.isoformat()}; "
            f"{days_left} days remain as of the claim date {as_of.isoformat()}.",
            f"Dates: purchased {p_date.isoformat()}, failed {case.failure_date}, claim date {as_of.isoformat()}.",
            f"Device model named in case: {case.product_name}.",
            f"Reported symptom: '{case.defect_description}' matches the program symptom: {record.get('symptom')}.",
        ]
        if case.visual_evidence and case.visual_evidence.visual_observations:
            evidence_items.extend(
                f"Visual defect observation: {obs}" for obs in case.visual_evidence.visual_observations
            )

        if requires_serial:
            claim = (
                f"Possible free service under {program}, pending Apple's serial number check."
            )
            action = (
                f"Run the serial number checker on the program page ({record['source_url']}). If it confirms "
                "eligibility, book service at an Apple Store, an Apple Authorized Service Provider, or by mail-in "
                "through Apple Support. Bring proof of purchase; the device is examined before service."
            )
        else:
            claim = f"Potentially eligible for free service under {program}."
            action = record.get("claim_action") or (
                "Book service at an Apple Store or Apple Authorized Service Provider. Present the device and proof "
                "of purchase for the mandatory pre-service inspection."
            )

        if case.already_paid_for_repair and record.get("refund_for_prior_paid_repair"):
            evidence_items.append("Case states the owner already paid for this repair.")
            action += (
                " Because you already paid for this repair, Apple's program page says you can contact Apple "
                "about a refund; keep the repair invoice."
            )

        provenance = ProvenanceChain(
            claim=claim,
            why_matched=(
                f"The case names an eligible device ({case.product_name}), the reported defect matches the program "
                f"symptom, and the claim date {as_of.isoformat()} is inside the {window_years:.0f}-year window from "
                f"the {p_date.isoformat()} purchase, which ends {coverage_end.isoformat()}."
            ),
            evidence=evidence_items,
            source_citation=program,
            source_url=record["source_url"],
            conditions=record.get("mandatory_conditions", []),
            exceptions=exceptions,
        )

        made = f"affected devices manufactured {record['manufacturing_window']}" if record.get("manufacturing_window") else "a limited number of devices"
        summary = (
            f"{record.get('issuer_or_brand')} states that {made} may show this issue: "
            f"{record.get('symptom').lower()}. {record.get('remedy')}."
        )

        return (
            MatchedRoute(
                route_id=record["id"],
                route_type="manufacturer_service_program",
                title=program,
                provider=record["issuer_or_brand"],
                status=status,
                summary=summary,
                primary_source={
                    "title": program,
                    "url": record["source_url"],
                    "verified_at": record.get("verified_at", ""),
                },
                provenance=provenance,
                recommended_action=action,
                deadline=coverage_end.isoformat(),
                deadline_label="Free repair program ends",
                claim_to=record.get("claim_to")
                or f"{record.get('brand_short') or (record.get('issuer_or_brand') or 'Manufacturer').split()[0]} Support",
            ),
            None,
        )

    def _evaluate_visa_extended_warranty(
        self,
        case: NormalizedCase,
        record: Dict[str, Any],
        years_elapsed: float,
        p_date: date,
        f_date: date,
        as_of: date,
    ) -> Tuple[Optional[MatchedRoute], Optional[str]]:
        payment_lower = (case.payment_method or "").lower()
        if "visa infinite" not in payment_lower:
            return None, None
        country = (case.purchase_country or "").strip().upper()
        if record.get("countries") and country not in record["countries"]:
            return None, None  # a U.S. card benefit on a U.S. manufacturer's warranty

        orig_warranty = case.original_warranty_years
        max_eligible = record.get("max_eligible_manufacturer_warranty_years", 3.0)
        extension = record.get("benefit_extension_years", 1.0)

        if orig_warranty > max_eligible:
            return None, None

        total_coverage_years = orig_warranty + extension
        if years_elapsed <= orig_warranty:
            return None, None  # still inside the original warranty
        if years_elapsed > total_coverage_years:
            return None, None  # outside the extended window

        warranty_end = add_years(p_date, orig_warranty)
        extended_end = add_years(p_date, total_coverage_years)
        if as_of > extended_end:
            return None, (
                f"{record['program_name']}: the fault appeared on {f_date.isoformat()}, inside the extended period, "
                f"but that period ended on {extended_end.isoformat()}. Your card issuer sets the deadline for reporting "
                "a claim; check your Guide to Benefits before relying on it."
            )
        evidence_items = [
            f"Dates: purchased {p_date.isoformat()}, original warranty ended about {warranty_end.isoformat()}, "
            f"failed {f_date.isoformat()}, extended protection runs to about {extended_end.isoformat()}.",
            f"Payment proof: Purchased via {case.payment_method}.",
            f"Original warranty: {orig_warranty:.1f} year(s) (eligible for extension; threshold is <= {max_eligible} years).",
            f"Defect description: '{case.defect_description}'.",
        ]

        provenance = ProvenanceChain(
            claim="Potentially eligible for Visa Infinite Extended Warranty Protection (+1 year extension).",
            why_matched=(
                f"Item was purchased using {case.payment_method}. The failure occurred at {years_elapsed:.2f} years, "
                f"which is beyond the original {orig_warranty:.1f}-year manufacturer warranty but within the "
                f"{total_coverage_years:.1f}-year total extended protection period."
            ),
            evidence=evidence_items,
            source_citation=record["program_name"],
            source_url=record["source_url"],
            conditions=record.get("mandatory_conditions", []),
            exceptions=[
                "Your issuer's Guide to Benefits sets a deadline to report a claim, usually counted from when the "
                "item failed. It can be much earlier than the date shown here, so check it now.",
                *record.get("exclusions_and_caveats", []),
            ],
        )

        return MatchedRoute(
            route_id=record["id"],
            route_type="card_benefit",
            title=record["program_name"],
            provider=record["issuer_or_brand"],
            status="POTENTIALLY_ELIGIBLE",
            summary=(
                "Extends the period of the original manufacturer's written warranty by up to one additional year "
                "on eligible warranties of three years or less for items purchased entirely with a covered card."
            ),
            primary_source={
                "title": record["program_name"],
                "url": record["source_url"],
                "verified_at": record.get("verified_at", ""),
            },
            provenance=provenance,
            recommended_action=(
                "Open a claim with your issuing bank's card benefit administrator. Have your itemized receipt, "
                "card statement showing the charge, and warranty document ready. Check your Guide to Benefits "
                "for the claim reporting deadline."
            ),
            deadline=extended_end.isoformat(),
            deadline_label="Extended protection ends (approx.; the deadline to report a claim may be earlier)",
            claim_to="Your card's benefit administrator (the contact in your Guide to Benefits)",
        ), None

    def _evaluate_uk_consumer_rights(
        self,
        case: NormalizedCase,
        record: Dict[str, Any],
        p_date: date,
        as_of: date,
        years_elapsed: float,
        months_elapsed: float,
    ) -> Tuple[Optional[MatchedRoute], Optional[str]]:
        country_code = (case.purchase_country or "").strip().upper()
        if country_code not in ["GB", "UK"]:
            return None, None

        if not case.defect_description.strip():
            return None, None

        by_region = record.get("limitation_years_by_region", {})
        labels = record.get("region_labels", {})
        region = case.uk_region
        if region:
            limitation_years = float(by_region.get(region, record.get("claim_limitation_years", 6)))
            place = labels.get(region, region)
        else:
            # No region given: use the 6-year period that GOV.UK states for the UK outside Scotland,
            # and say so. Scotland's 5 years is kept as a caveat below.
            limitation_years = float(record.get("claim_limitation_years", 6))
            place = "the UK outside Scotland (region not given)"
        limitation_end = add_years(p_date, limitation_years)
        if as_of > limitation_end:
            return None, (
                f"{record['program_name']}: the {limitation_years:.0f}-year period to make a claim in {place} "
                f"ended on {limitation_end.isoformat()} (evaluated as of {as_of.isoformat()})."
            )

        # Without a region, the 6-year period is only safe to use while Scotland's 5 years would also
        # still be running. After that, the option is held until the user says where they bought it.
        region_needed = not region and as_of > add_years(p_date, float(by_region.get("scotland", 5)))

        store = case.retailer or "the store that sold it"
        evidence_items = [
            f"Deadline to claim: {limitation_end.isoformat()} ({limitation_years:.0f} years from delivery in {place}; "
            f"the purchase date {p_date.isoformat()} is used as the delivery date). The claim date "
            f"{as_of.isoformat()} is inside it. This is a period to make a claim, not a {limitation_years:.0f}-year warranty.",
            f"Dates: purchased {p_date.isoformat()}, fault appeared {case.failure_date} "
            f"({months_elapsed:.1f} months after purchase), claim date {as_of.isoformat()}.",
            f"Where bought: {case.purchase_country}, from {store} (as entered).",
            f"Documented fault: '{case.defect_description}'.",
        ]

        exceptions = list(record.get("exclusions_and_caveats", []))
        if months_elapsed > 6.0:
            exceptions.insert(
                0,
                f"Fault timing: because the fault appeared more than six months after delivery ({months_elapsed:.1f} "
                "months), you may need to provide evidence that the goods did not conform to the contract when "
                "delivered. GOV.UK: the retailer can ask you to prove the item was faulty when you bought it.",
            )
        if region == "scotland":
            exceptions.insert(
                0,
                "Scotland: the 5-year period is prescription under Scots law, which can start from a different date. "
                "RemedyAI measures it from the purchase date; check the exact date if you are close to it.",
            )
        elif region_needed:
            exceptions.insert(
                0,
                "Choose which part of the UK you bought it in. In Scotland the period to claim is 5 years, which has "
                "already ended for this purchase; in the rest of the UK it is 6 years.",
            )
        elif not region:
            exceptions.insert(0, "Region not given. If the item was bought in Scotland, the period is 5 years, not 6.")
        if months_elapsed <= 6.0:
            exceptions.insert(
                0,
                "If one repair or replacement doesn't fix it, you can ask for a price reduction or reject it for a "
                "refund. Within 6 months of delivery the store can't usually take anything off the refund for your use.",
            )
        days_owned = (as_of - p_date).days
        within_reject_window = days_owned <= 30
        if within_reject_window:
            exceptions.insert(
                0,
                "The 30-day right to reject runs from delivery (the purchase date is used here). Asking for a repair "
                "first pauses it, but after one failed repair you can still reject it.",
            )

        provenance = ProvenanceChain(
            claim=(
                "Potential statutory remedy: depending on the circumstances, you may have rights to repair or "
                "replacement. Where the statutory conditions for those remedies have been met and the "
                "repair/replacement route has failed or is unavailable, a price reduction or final right to "
                "reject may apply."
            ),
            why_matched=(
                f"You entered a UK purchase ({place}) from {store}, and the claim date {as_of.isoformat()} is "
                f"inside the {limitation_years:.0f}-year period to make a claim, which ends {limitation_end.isoformat()}."
            ),
            evidence=evidence_items,
            source_citation=record["program_name"],
            source_url=record["source_url"],
            conditions=record.get("mandatory_conditions", []),
            exceptions=exceptions,
        )

        return (
            MatchedRoute(
                route_id=record["id"],
                route_type="statutory_consumer_law",
                title=record["program_name"],
                provider=record["issuer_or_brand"],
                status="NEEDS_CONFIRMATION" if region_needed else "POTENTIALLY_ELIGIBLE",
                summary=(
                    "Under the UK Consumer Rights Act 2015, goods must be of satisfactory quality, fit for purpose and as "
                    "described. The retailer must repair or replace an item that was faulty when bought, whether or not a "
                    "warranty has run out. GOV.UK gives up to 6 years to make a claim (5 years in Scotland)."
                ),
                primary_source={
                    "title": record["program_name"],
                    "url": record["source_url"],
                    "verified_at": record.get("verified_at", ""),
                },
                provenance=provenance,
                recommended_action=(
                    f"You bought it {days_owned} days ago. Within 30 days of delivery you can reject a faulty item "
                    f"and get a full refund under the Consumer Rights Act 2015. Tell {store} now that you're rejecting "
                    "it. If you'd rather have a repair or replacement, you can ask for that instead."
                    if within_reject_window else
                    f"Write to the store that sold it ({store}) asking for a repair or replacement under the Consumer "
                    "Rights Act 2015. Attach proof of purchase and evidence of the fault. After 6 months, the store can "
                    "ask you to show the item was faulty when you bought it."
                ),
                deadline=limitation_end.isoformat(),
                deadline_label=f"Legal time limit to claim ({place})",
                related_sources=list(record.get("related_sources", [])),
                claim_to=case.retailer or "The store that sold it",
                short_term_reject=within_reject_window,
            ),
            None,
        )
