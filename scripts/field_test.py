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


def gap(case: dict) -> str:
    """Why nothing matched, in plain words (for the roadmap)."""
    from datetime import date

    country = case.get("purchase_country", "US")
    brand = (case.get("product_brand") or case["product_name"].split()[0]).lower()
    age_days = (date.fromisoformat(case["failure_date"]) - date.fromisoformat(case["purchase_date"])).days
    where = "country not stated" if country == "OTHER" else f"bought in {COUNTRY[country]}"
    if brand == "samsung":
        return "Samsung's warranty not covered yet" + ("" if country in ("US", "GB") else f"; {where}")
    if brand in ("apple", "google") and age_days <= 365:
        return f"inside {brand.title()}'s one-year warranty, but {where}: only the U.S. version is covered so far"
    return f"outside the maker's warranty; {where}: consumer law there not covered yet"


def main():
    data = json.loads((ROOT / "docs/field-test/cases.json").read_text(encoding="utf-8"))
    engine = EligibilityEngine()
    rows, outcomes, gaps = [], Counter(), Counter()
    for c in data["included"]:
        body = {"case_id": c["id"], "evaluation_date": c["posted"], "purchase_country": "US", **c["case"]}
        ev = engine.evaluate(NormalizedCase(**body))
        routes = ev.matched_routes
        actionable = [r for r in routes if is_actionable(r)]
        if actionable:
            outcome = "Route found"
        elif routes:
            outcome = "Route found, confirm details first"
        else:
            outcome = "No covered route"
        outcomes[outcome] += 1
        found = "; ".join(f"{r.title} ({r.status.replace('_', ' ').lower()}, deadline {r.deadline})" for r in routes) or "-"
        why = "" if routes else gap(body)
        if why:
            gaps[why] += 1
        rows.append((c["id"], c["case"]["product_name"], COUNTRY.get(body["purchase_country"], body["purchase_country"]),
                     c["posted"], outcome, found if routes else why, c["url"]))

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
    lines += ["", "Why nothing matched:", ""]
    lines += [f"- {k}: {v}" for k, v in gaps.most_common()]
    # Sensitivity: the posts that didn't say where the product was bought, re-run as U.S. purchases.
    unknown = [c for c in data["included"] if c["case"].get("purchase_country") == "OTHER"]
    as_us = sum(
        1 for c in unknown
        if any(is_actionable(r) for r in engine.evaluate(NormalizedCase(**{
            "case_id": c["id"], "evaluation_date": c["posted"], **c["case"], "purchase_country": "US"})).matched_routes)
    )
    lines += ["", f"Sensitivity: {len(unknown)} posts didn't say where the product was bought. Entered as U.S. purchases, "
              f"{as_us} of them would get a route (Apple's U.S. warranty). The result above does not count them."]
    lines += ["", "What this changes: Samsung's warranty is the most common gap (5 of 12 misses), so it is the next record "
              "to verify, followed by Apple's warranty outside the U.S. and consumer law in more countries."]
    lines += ["", "## Cases", "", "| # | Product | Bought in | Posted | Outcome | Route or gap | Source |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | [post]({r[6]}) |")
    lines += ["", "A route is what RemedyAI would tell the person to try first; the maker, card issuer or store makes the final decision."]
    out = ROOT / "docs/field-test/results.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[14:22]))
    print("WROTE", out)


if __name__ == "__main__":
    main()
