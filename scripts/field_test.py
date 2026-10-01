"""
Field test: runs real, publicly described cases (docs/field-test/cases.json) through the same engine
the live API uses, with the claim date set to the day each post was written. Writes
docs/field-test/results.md. Usage (from the repo root): python scripts/field_test.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from src.engine.eligibility import EligibilityEngine, is_actionable  # noqa: E402
from src.models.schemas import NormalizedCase  # noqa: E402

COUNTRY = {"US": "U.S.", "GB": "UK", "IN": "India", "AU": "Australia", "CA": "Canada", "OTHER": "other / not stated"}
# Records added after the first run of this test (2026-10-01), to show what each one changed.
ADDED_AFTER_FIRST_RUN = {"samsung_galaxy_limited_warranty_us": "Samsung's U.S. phone warranty"}


def body_of(c: dict, **override) -> dict:
    return {"case_id": c["id"], "evaluation_date": c["posted"], "purchase_country": "US", **c["case"], **override}


def has_route(engine: EligibilityEngine, body: dict) -> bool:
    return any(is_actionable(r) for r in engine.evaluate(NormalizedCase(**body)).matched_routes)


def gap(engine: EligibilityEngine, body: dict) -> str:
    """Why nothing matched, in plain words, worked out by re-running the case (not guessed)."""
    country = body["purchase_country"]
    brand = (body.get("product_brand") or body["product_name"].split()[0]).title()
    if country != "US" and has_route(engine, {**body, "purchase_country": "US"}):
        where = "the poster didn't say where it was bought" if country == "OTHER" else f"bought in {COUNTRY[country]}"
        return f"would match if bought in the U.S.; {where}, and {brand}'s warranty there isn't covered yet"
    if country == "OTHER":
        return "the poster didn't say where it was bought, and it wouldn't match as a U.S. purchase either"
    if country in ("IN", "AU", "CA"):
        return f"bought in {COUNTRY[country]}: {brand}'s warranty and consumer law there aren't covered yet"
    return f"bought in the {COUNTRY[country]}: no record covers this product at this age yet"


def main():
    data = json.loads((ROOT / "docs/field-test/cases.json").read_text(encoding="utf-8"))
    engine = EligibilityEngine()
    before = EligibilityEngine()
    for rid in ADDED_AFTER_FIRST_RUN:
        before.records.pop(rid, None)

    rows, outcomes, gaps = [], Counter(), Counter()
    first_run_hits = 0
    for c in data["included"]:
        body = body_of(c)
        routes = engine.evaluate(NormalizedCase(**body)).matched_routes
        first_run_hits += has_route(before, body)
        if any(is_actionable(r) for r in routes):
            outcome = "Route found"
        elif routes:
            outcome = "Route found, confirm details first"
        else:
            outcome = "No covered route"
        outcomes[outcome] += 1
        found = "; ".join(f"{r.title} ({r.status.replace('_', ' ').lower()}, deadline {r.deadline})" for r in routes)
        why = "" if routes else gap(engine, body)
        if why:
            gaps[why] += 1
        rows.append((c["id"], c["case"]["product_name"], COUNTRY.get(body["purchase_country"], body["purchase_country"]),
                     c["posted"], outcome, found or why, c["url"]))

    n = len(rows)
    lines = [
        "# Field test: real cases from public posts",
        "",
        f"{n} people described a broken product in a public forum or a newspaper consumer column. Each case was",
        "entered using only what the poster said, and run through the same engine as the live site, with the",
        "claim date set to the day of the post. Inputs, sources and the exclusion list: [`cases.json`](cases.json).",
        "Reproduce with `python scripts/field_test.py`.",
        "",
        "How the cases were chosen: searches for broken-device posts on Apple Community, Samsung Community, Sky",
        "News's Money Problem column and the MoneySavingExpert forum, taken in search order. A post was skipped",
        f"only if it gave no purchase date or did not load ({len(data['excluded'])} skipped, listed in `cases.json`).",
        "Where a poster gave a month or 'about N months', the date is approximate. A country the poster didn't",
        "state was entered as 'other', so it can't create a match.",
        "",
        "## Result",
        "",
    ]
    for k in ("Route found", "Route found, confirm details first", "No covered route"):
        lines.append(f"- **{k}:** {outcomes[k]} of {n}")
    added = ", ".join(ADDED_AFTER_FIRST_RUN.values())
    lines += ["", f"Before and after: the first run (2026-10-01) found a route for {first_run_hits} of {n}. The biggest gap "
              f"was Samsung, so the next record verified and added was {added}; with it, {outcomes['Route found']} of {n}."]
    lines += ["", "Why nothing matched:", ""]
    lines += [f"- {k}: {v}" for k, v in gaps.most_common()]
    unknown = [c for c in data["included"] if c["case"].get("purchase_country") == "OTHER"]
    as_us = sum(has_route(engine, body_of(c, purchase_country="US")) for c in unknown)
    lines += ["", f"Sensitivity: {len(unknown)} posts didn't say where the product was bought. Entered as U.S. purchases, "
              f"{as_us} of them would get a route. The result above does not count them."]
    lines += ["", "## Cases", "", "| # | Product | Bought in | Posted | Outcome | Route or gap | Source |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | [post]({r[6]}) |")
    lines += ["", "A route is what RemedyAI would tell the person to try first; the maker, card issuer or store makes the final decision."]
    out = ROOT / "docs/field-test/results.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[14:30]))
    print("WROTE", out)


if __name__ == "__main__":
    main()
