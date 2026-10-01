import io
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape as _xml_escape

from dateutil import parser as date_parser
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from src.models.schemas import NormalizedCase, RemedyEvaluation
from src.engine.eligibility import is_actionable

STATUS_TEXT = {
    "POTENTIALLY_ELIGIBLE": "May apply",
    "ELIGIBLE_PENDING_INSPECTION": "May apply, subject to inspection",
    "PENDING_SERIAL_VERIFICATION": "May apply: check the serial number first",
    "NEEDS_REVERIFICATION": "Source changed: re-verify first",
    "NEEDS_CONFIRMATION": "Confirm the details first",
    "OUTSIDE_WINDOW": "Window closed",
    "INSUFFICIENT_EVIDENCE": "Not enough evidence",
}

OGL_NOTICE = "Contains public sector information licensed under the Open Government Licence v3.0."
NON_AFFILIATION = (
    "RemedyAI is not affiliated with or endorsed by Apple, Google, Visa, Sony, Samsung, Best Buy, Currys or any "
    "retailer named. Names are used only to identify products and programs."
)


def e(value: Optional[object]) -> str:
    """Escape any dynamic text for ReportLab's Paragraph markup (it parses <b>, <img>, <link>, ...).

    Every value that is not a fixed literal in this file goes through here: user input, knowledge
    records and engine output alike. Unescaped text could make the server load files or URLs into
    the PDF, inject links, or crash the build.
    """
    return _xml_escape("" if value is None else str(value), {'"': "&quot;", "'": "&#39;"})


def human_date(iso: Optional[str]) -> str:
    if not iso:
        return "Not given"
    try:
        return date_parser.parse(iso).date().strftime("%d %b %Y").lstrip("0")
    except (ValueError, OverflowError):
        return iso


class ClaimPdfService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.title_style = ParagraphStyle(
            "DocTitle", parent=self.styles["Heading1"], fontSize=20, leading=24,
            textColor=colors.HexColor("#0f172a"), fontName="Helvetica-Bold",
        )
        self.subtitle_style = ParagraphStyle(
            "DocSubtitle", parent=self.styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#64748b"),
        )
        self.section_title = ParagraphStyle(
            "SectionTitle", parent=self.styles["Heading2"], fontSize=13, leading=17,
            textColor=colors.HexColor("#1e293b"), fontName="Helvetica-Bold", spaceAfter=6,
        )
        self.body_style = ParagraphStyle(
            "BodyDark", parent=self.styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#334155"),
        )
        self.bullet_style = ParagraphStyle("BulletText", parent=self.body_style, leftIndent=12, bulletIndent=4, spaceAfter=3)
        self.callout_style = ParagraphStyle(
            "Callout", parent=self.styles["Normal"], fontSize=9, leading=13,
            textColor=colors.HexColor("#0f766e"), fontName="Helvetica-Oblique",
        )
        self.disclaimer_style = ParagraphStyle(
            "LegalDisclaimer", parent=self.styles["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#64748b"),
        )

    def _table(self, rows, widths):
        t = Table(rows, colWidths=widths)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    def _row(self, label: str, value: str):
        return [Paragraph(f"<b>{label}</b>", self.body_style), Paragraph(value, self.body_style)]

    def generate_pdf(self, case: NormalizedCase, evaluation: RemedyEvaluation) -> bytes:
        """Generates an evidence-backed consumer claim package as a PDF binary."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        today = datetime.now(timezone.utc).strftime("%d %B %Y").lstrip("0")
        story = []

        # 1. Header
        story.append(Paragraph("RemedyAI: Claim Preparation Package", self.title_style))
        as_of = f" · Deadlines measured as of <b>{e(human_date(evaluation.evaluation_date))}</b>" if evaluation.evaluation_date else ""
        story.append(Paragraph(f"Generated on {e(today)} · Case ID: <b>{e(case.case_id)}</b>{as_of}", self.subtitle_style))
        story.append(Spacer(1, 12))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=14))

        # 2. Case summary
        story.append(Paragraph("1. Your case", self.section_title))
        region = {"england_wales": "England and Wales", "northern_ireland": "Northern Ireland", "scotland": "Scotland"}.get(
            case.uk_region or "", ""
        )
        origin = f"{case.purchase_country}{' (' + region + ')' if region else ''}"
        rows = [
            self._row("Product", e(case.product_name)),
            self._row("Store / country", f"{e(case.retailer or 'Not specified')} · {e(origin)}"),
            self._row("Paid with", e(case.payment_method or "Not recorded")),
            self._row("What went wrong", e(case.defect_description)),
        ]
        if case.visual_evidence and case.visual_evidence.visual_observations:
            obs = "<br/>".join(f"• {e(o)}" for o in case.visual_evidence.visual_observations)
            rows.append(self._row("Photo observations", obs))
        story.append(self._table(rows, [130, 400]))
        story.append(Spacer(1, 10))

        # 3. Timeline
        if evaluation.timeline:
            tl = evaluation.timeline
            story.append(Paragraph("2. Timeline", self.section_title))
            trows = [
                self._row("Purchase", e(human_date(tl.purchase_date))),
                self._row("Fault appeared", f"{e(human_date(tl.failure_date))} ({e(tl.months_before_failure)} months after purchase)"),
                self._row("Claim date", e(human_date(tl.claim_date))),
            ]
            for r in evaluation.matched_routes:
                if r.deadline:
                    trows.append(self._row(e(r.deadline_label or "Deadline"), f"{e(human_date(r.deadline))} ({e(r.title)})"))
            story.append(self._table(trows, [130, 400]))
            story.append(Spacer(1, 10))

        # 4. Consistency checks
        if evaluation.checks:
            story.append(Paragraph("3. Checks against your receipt", self.section_title))
            for c in evaluation.checks:
                state = "Confirmed by you" if c.confirmed else ("Needs confirmation" if c.severity == "hard" else "Please check")
                story.append(Paragraph(f"• <b>{e(state)}:</b> {e(c.message)}", self.bullet_style))
            story.append(Spacer(1, 10))

        # 5. Options
        story.append(Paragraph("Options found", self.section_title))
        if not evaluation.has_coverage or not evaluation.matched_routes:
            story.append(Paragraph(
                f"<b>No verified option found.</b> {e(evaluation.unmatched_reason or 'No matching source found.')}",
                self.body_style,
            ))
            if evaluation.notes:
                story.append(Spacer(1, 8))
                story.append(Paragraph("<b>Sources checked that did not apply:</b>", self.body_style))
                for note in evaluation.notes:
                    story.append(Paragraph(f"• {e(note)}", self.bullet_style))
            story.append(Spacer(1, 8))
            story.append(Paragraph("<b>What you can still try:</b>", self.body_style))
            for step in evaluation.next_steps:
                story.append(Paragraph(f"• {e(step)}", self.bullet_style))
        else:
            for idx, route in enumerate(evaluation.matched_routes, 1):
                ok = route.status in ("POTENTIALLY_ELIGIBLE", "ELIGIBLE_PENDING_INSPECTION", "PENDING_SERIAL_VERIFICATION")
                color = "#047857" if ok else "#b45309"
                story.append(Paragraph(
                    f"<b>Option {idx}: {e(route.title)}</b> &nbsp;[<font color='{color}'><b>{e(STATUS_TEXT.get(route.status, route.status))}</b></font>]",
                    ParagraphStyle("RouteH", parent=self.section_title, fontSize=11, leading=15),
                ))
                url = route.primary_source.get("url", "")
                story.append(Paragraph(
                    f"<b>From:</b> {e(route.provider)} · <b>Source:</b> "
                    f"<link href=\"{e(url)}\"><u>{e(route.primary_source.get('title'))}</u></link> "
                    f"(verified against the official page on {e(human_date(route.primary_source.get('verified_at')))})",
                    self.body_style,
                ))
                for rs in route.related_sources:
                    story.append(Paragraph(
                        f"<b>Related:</b> <link href=\"{e(rs.get('url'))}\"><u>{e(rs.get('title'))}</u></link>",
                        self.body_style,
                    ))
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"<b>Summary:</b> {e(route.summary)}", self.body_style))
                story.append(Paragraph(f"<b>What this may give you:</b> {e(route.provenance.claim)}", self.body_style))
                story.append(Spacer(1, 6))

                prov = route.provenance
                story.append(Paragraph("<b>Why this matched:</b>", self.body_style))
                story.append(Paragraph(e(prov.why_matched), self.callout_style))
                story.append(Spacer(1, 4))
                for heading, items, red in (
                    ("Evidence used", prov.evidence, False),
                    ("What you will need", prov.conditions, False),
                    ("What could stop it", prov.exceptions, True),
                ):
                    story.append(Paragraph(f"<b>{heading}:</b>", self.body_style))
                    for item in items:
                        text = f"<font color='#b91c1c'>{e(item)}</font>" if red else e(item)
                        story.append(Paragraph(f"• {text}", self.bullet_style))
                    story.append(Spacer(1, 4))
                if not is_actionable(route):
                    story.append(Paragraph(
                        "<b>Check this option first.</b> It is listed for information only and is not used in the "
                        "draft letter below.",
                        self.body_style,
                    ))
                story.append(Paragraph(f"<b>What to do next:</b> {e(route.recommended_action)}", self.body_style))
                story.append(Spacer(1, 10))

        story.append(Spacer(1, 10))

        # 6. Draft letter, only for an option the user can act on now
        top = next((r for r in evaluation.matched_routes if is_actionable(r)), None)
        if evaluation.has_coverage and top:
            story.append(Paragraph("Draft letter", self.section_title))
            letter_text = (
                f"<b>Date:</b> {e(today)}<br/>"
                f"<b>To:</b> Customer Support ({e(top.provider)})<br/>"
                f"<b>Subject:</b> Claim for {e(case.product_name)} (reference {e(case.case_id)})<br/><br/>"
                "Dear Sir or Madam,<br/><br/>"
                f"I am writing about my <b>{e(case.product_name)}</b>, bought on <b>{e(human_date(case.purchase_date))}</b>. "
                f"On <b>{e(human_date(case.failure_date))}</b> it developed this fault: <i>{e(case.defect_description)}</i>.<br/><br/>"
                f"Based on the published terms of <b>{e(top.title)}</b> ({e(top.primary_source.get('url'))}), I believe it may "
                "qualify for a remedy, subject to your inspection. I attach proof of purchase, photos of the fault and "
                "proof of payment.<br/><br/>"
                "Please confirm you have received this claim and tell me how to arrange an inspection, repair or replacement.<br/><br/>"
                "Yours faithfully,<br/>[Your name]"
            )
            lt = Table([[Paragraph(letter_text, self.body_style)]], colWidths=[530])
            lt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]))
            story.append(lt)
            story.append(Spacer(1, 14))

        # 7. Notices
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        story.append(Paragraph(f"<b>Not legal advice.</b> {e(evaluation.disclaimer)}", self.disclaimer_style))
        story.append(Spacer(1, 3))
        story.append(Paragraph(e(NON_AFFILIATION), self.disclaimer_style))
        if any(r.route_type == "statutory_consumer_law" for r in evaluation.matched_routes):
            story.append(Spacer(1, 3))
            story.append(Paragraph(e(OGL_NOTICE), self.disclaimer_style))

        doc.build(story)
        return buffer.getvalue()
