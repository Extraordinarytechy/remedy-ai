import json
from pathlib import Path
from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any, Tuple
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

from src.models.schemas import (
    CaseTimeline,
    NormalizedCase,
    MatchedRoute,
    ProvenanceChain,
    RemedyEvaluation,
)
from src.engine.case_checks import run_checks

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
    """Safely parse ISO or common date strings to date objects."""
    return date_parser.parse(date_str).date()


def add_years(d: date, years: float) -> date:
    """Adds whole years (and any fractional remainder as months) to a date, handling Feb 29."""
    whole = int(years)
    months = int(round((years - whole) * 12))
    return d + relativedelta(years=whole, months=months)


class EligibilityEngine:
    def __init__(self, knowledge_dir: Optional[Path] = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self.records = load_knowledge_records(self.knowledge_dir)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def evaluate(
        self, case: NormalizedCase, source_status: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> RemedyEvaluation:
        """
        Evaluates a NormalizedCase against the closed-world knowledge corpus.
        Enforces strict evidence grounding: no routes are generated unless
        explicitly verified in primary-source records. `source_status` is the latest
        Source Watch result; a route whose source is unreachable or delisted is downgraded.
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
        except Exception as e:
            return self._invalid(case, now_iso, None, f"Date parsing failed: {e}")

        if f_date < p_date:
            return self._invalid(
                case, now_iso, as_of,
                f"Failure date ({f_date.isoformat()}) is before purchase date ({p_date.isoformat()}).",
            )
        if f_date > as_of:
            return self._invalid(
                case, now_iso, as_of,
                f"Failure date ({f_date.isoformat()}) is after the evaluation date ({as_of.isoformat()}).",
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
            route = self._evaluate_visa_extended_warranty(case, visa_record, years_elapsed, p_date, f_date)
            if route:
                matched_routes.append(route)

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
            self._apply_source_status(route, (source_status or {}).get(route.route_id))
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
        pdf_allowed = not pending_hard

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
    def _invalid(case: NormalizedCase, now_iso: str, as_of: Optional[date], reason: str) -> RemedyEvaluation:
        return RemedyEvaluation(
            case_id=case.case_id,
            evaluated_at=now_iso,
            evaluation_date=as_of.isoformat() if as_of else None,
            has_coverage=False,
            unmatched_reason=f"INVALID INPUT: {reason}",
            next_steps=["Please provide valid ISO dates (YYYY-MM-DD): purchase date <= failure date <= today."],
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
        if warnings:
            route.status = "NEEDS_REVERIFICATION"
            route.provenance.exceptions[:0] = warnings
        changed = (st.get("last_changed_at") or "")[:10]
        verified = (st.get("human_verified_at") or "")[:10]
        if changed and verified and changed > verified:
            route.provenance.exceptions.insert(
                0,
                f"The source page's text changed on {changed}, after it was last checked by a person on {verified}. "
                "The terms shown here may be out of date.",
            )

    @staticmethod
    def _device_matches(case: NormalizedCase, record: Dict[str, Any]) -> bool:
        name = f"{case.product_name} {case.product_model or ''}".lower()
        for excluded in record.get("excluded_devices", []):
            if excluded.lower() in name:
                return False
        return any(dev.lower() in name for dev in record.get("applicable_devices", []))

    @staticmethod
    def _symptom_matches(case: NormalizedCase, record: Dict[str, Any]) -> bool:
        desc = case.defect_description.lower()
        return any(k.lower() in desc for k in record.get("symptom_keywords", []))

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
        years = float(record.get("warranty_years", 1))
        warranty_end = add_years(p_date, years)
        if f_date > warranty_end:
            return None, None  # the fault appeared after the warranty; other routes may apply
        if as_of > warranty_end:
            return None, (
                f"{program}: the fault appeared on {f_date.isoformat()}, inside the warranty, but the warranty "
                f"ended on {warranty_end.isoformat()} and claims must be made during it. Contact Apple anyway, "
                "and check the other options below."
            )

        exceptions = list(record.get("exclusions_and_caveats", []))
        if case.visual_evidence and case.visual_evidence.visible_physical_damage:
            exceptions.insert(
                0,
                "Visible physical damage was recorded in the evidence photo. Apple's warranty does not cover damage "
                "caused by accident or other external causes; AppleCare coverage, if you have it, may.",
            )
        days_left = (warranty_end - as_of).days
        evidence_items = [
            f"Warranty ends {warranty_end.isoformat()} ({years:.0f} year from the {p_date.isoformat()} purchase); "
            f"{days_left} days remain as of the claim date {as_of.isoformat()}.",
            f"Dates: purchased {p_date.isoformat()}, fault appeared {f_date.isoformat()}, claim date {as_of.isoformat()}.",
            f"Device named in case: {case.product_name} (bought in {country}).",
            f"Reported fault: '{case.defect_description}'.",
        ]
        provenance = ProvenanceChain(
            claim=f"Covered by the {program} if the fault is a defect: Apple will repair, replace or refund at its option.",
            why_matched=(
                f"The case names a device this warranty covers ({case.product_name}), bought in {country}, and the claim "
                f"date {as_of.isoformat()} is inside the one-year Warranty Period, which ends {warranty_end.isoformat()}."
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
                    f"Contact Apple Support, or visit an Apple Store or Apple Authorized Service Provider, before "
                    f"{warranty_end.isoformat()}. To see your coverage, open Settings > General > AppleCare & Warranty "
                    "on the device, or sign in at mysupport.apple.com. Back up the device first and have proof of purchase ready."
                ),
                deadline=warranty_end.isoformat(),
                deadline_label="Apple's warranty ends",
                related_sources=[{
                    "title": "Apple Support: Find information about your warranty or AppleCare plan",
                    "url": "https://support.apple.com/102607",
                }],
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
        if not record.get("listed_on_apple_service_programs_index", True) and record.get("index_note"):
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
            action = (
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

        summary = (
            f"{record.get('issuer_or_brand')} states that affected devices manufactured {record.get('manufacturing_window')} "
            f"may show this issue: {record.get('symptom').lower()}. {record.get('remedy')}."
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
            ),
            None,
        )

    def _evaluate_visa_extended_warranty(
        self, case: NormalizedCase, record: Dict[str, Any], years_elapsed: float, p_date: date, f_date: date
    ) -> Optional[MatchedRoute]:
        payment_lower = (case.payment_method or "").lower()
        if "visa infinite" not in payment_lower:
            return None

        orig_warranty = case.original_warranty_years
        max_eligible = record.get("max_eligible_manufacturer_warranty_years", 3.0)
        extension = record.get("benefit_extension_years", 1.0)

        if orig_warranty > max_eligible:
            return None

        total_coverage_years = orig_warranty + extension
        if years_elapsed <= orig_warranty:
            return None  # still inside the original warranty
        if years_elapsed > total_coverage_years:
            return None  # outside the extended window

        warranty_end = add_years(p_date, orig_warranty)
        extended_end = add_years(p_date, total_coverage_years)
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
            exceptions=record.get("exclusions_and_caveats", []),
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
            deadline_label="Extended protection ends (approx., from purchase date)",
        )

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
        elif not region:
            exceptions.insert(0, "Region not given. If the item was bought in Scotland, the period is 5 years, not 6.")

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
                status="POTENTIALLY_ELIGIBLE",
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
                    f"Write to the store that sold it ({store}) asking for a repair or replacement under the Consumer "
                    "Rights Act 2015. Attach proof of purchase and evidence of the fault. After 6 months, the store can "
                    "ask you to show the item was faulty when you bought it."
                ),
                deadline=limitation_end.isoformat(),
                deadline_label=f"Deadline to make a claim ({place})",
                related_sources=list(record.get("related_sources", [])),
            ),
            None,
        )
