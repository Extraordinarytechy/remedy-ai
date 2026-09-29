import io
from datetime import datetime, timezone
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
    KeepTogether,
)
from backend.src.models.schemas import NormalizedCase, RemedyEvaluation


class ClaimPdfService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.title_style = ParagraphStyle(
            "DocTitle",
            parent=self.styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            fontName="Helvetica-Bold",
        )
        self.subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
        )
        self.section_title = ParagraphStyle(
            "SectionTitle",
            parent=self.styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica-Bold",
            spaceAfter=6,
        )
        self.body_style = ParagraphStyle(
            "BodyDark",
            parent=self.styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        self.bullet_style = ParagraphStyle(
            "BulletText",
            parent=self.body_style,
            leftIndent=12,
            bulletIndent=4,
            spaceAfter=3,
        )
        self.callout_style = ParagraphStyle(
            "Callout",
            parent=self.styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#0f766e"),
            fontName="Helvetica-Oblique",
        )
        self.disclaimer_style = ParagraphStyle(
            "LegalDisclaimer",
            parent=self.styles["Normal"],
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#94a3b8"),
        )

    def generate_pdf(self, case: NormalizedCase, evaluation: RemedyEvaluation) -> bytes:
        """Generates an evidence-backed consumer claim package as a PDF binary."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("RemedyAI — Claim Preparation Package", self.title_style))
        as_of = f" • Windows evaluated as of <b>{evaluation.evaluation_date}</b>" if evaluation.evaluation_date else ""
        story.append(
            Paragraph(
                f"Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y')} • Case ID: <b>{case.case_id}</b>{as_of}",
                self.subtitle_style,
            )
        )
        story.append(Spacer(1, 12))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=14))

        # 2. Case Summary Table
        story.append(Paragraph("1. Submitted Case Evidence Summary", self.section_title))
        case_data = [
            [Paragraph("<b>Product</b>", self.body_style), Paragraph(case.product_name, self.body_style)],
            [Paragraph("<b>Purchase Date</b>", self.body_style), Paragraph(case.purchase_date, self.body_style)],
            [Paragraph("<b>Failure Date</b>", self.body_style), Paragraph(case.failure_date, self.body_style)],
            [Paragraph("<b>Retailer / Origin</b>", self.body_style), Paragraph(f"{case.retailer or 'Not specified'} ({case.purchase_country})", self.body_style)],
            [Paragraph("<b>Payment Method</b>", self.body_style), Paragraph(case.payment_method or "Not recorded", self.body_style)],
            [Paragraph("<b>Defect Description</b>", self.body_style), Paragraph(case.defect_description, self.body_style)],
        ]

        if case.visual_evidence and case.visual_evidence.visual_observations:
            obs_text = "<br/>".join([f"• {obs}" for obs in case.visual_evidence.visual_observations])
            case_data.append([Paragraph("<b>Visual Evidence</b>", self.body_style), Paragraph(obs_text, self.body_style)])

        table = Table(case_data, colWidths=[130, 400])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(table)
        story.append(Spacer(1, 16))

        # 3. Coverage Routes Evaluation
        story.append(Paragraph("2. Verified Coverage Determination", self.section_title))
        if not evaluation.has_coverage or not evaluation.matched_routes:
            story.append(
                Paragraph(
                    f"<b>NO VERIFIED COVERAGE FOUND:</b> {evaluation.unmatched_reason or 'No matching active programs found.'}",
                    self.body_style,
                )
            )
            if evaluation.notes:
                story.append(Spacer(1, 8))
                story.append(Paragraph("<b>Sources checked that did not qualify:</b>", self.body_style))
                for note in evaluation.notes:
                    story.append(Paragraph(f"• {note}", self.bullet_style))
            story.append(Spacer(1, 8))
            story.append(Paragraph("<b>Recommended Consumer Actions:</b>", self.body_style))
            for step in evaluation.next_steps:
                story.append(Paragraph(f"• {step}", self.bullet_style))
        else:
            for idx, route in enumerate(evaluation.matched_routes, 1):
                route_color = colors.HexColor("#047857") if "ELIGIBLE" in route.status else colors.HexColor("#d97706")
                story.append(
                    Paragraph(
                        f"<b>Route {idx}: {route.title}</b> &nbsp;&nbsp;[<font color='{route_color}'><b>{route.status}</b></font>]",
                        ParagraphStyle("RouteH", parent=self.section_title, fontSize=11, leading=15),
                    )
                )
                story.append(
                    Paragraph(
                        f"<b>Issuer / Program Authority:</b> {route.provider} • "
                        f"<b>Primary Source:</b> <a href='{route.primary_source.get('url')}'><u>{route.primary_source.get('title')}</u></a>",
                        self.body_style,
                    )
                )
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"<b>Summary:</b> {route.summary}", self.body_style))
                story.append(Spacer(1, 6))

                # Provenance block
                prov = route.provenance
                story.append(Paragraph("<b>Why This Matched (Evidence Verification):</b>", self.body_style))
                story.append(Paragraph(prov.why_matched, self.callout_style))
                story.append(Spacer(1, 4))

                story.append(Paragraph("<b>Submitted Evidence Alignment:</b>", self.body_style))
                for ev in prov.evidence:
                    story.append(Paragraph(f"• {ev}", self.bullet_style))
                story.append(Spacer(1, 4))

                story.append(Paragraph("<b>Mandatory Program Conditions:</b>", self.body_style))
                for cond in prov.conditions:
                    story.append(Paragraph(f"• {cond}", self.bullet_style))
                story.append(Spacer(1, 4))

                story.append(Paragraph("<b>Exceptions & Invalidating Factors:</b>", self.body_style))
                for exc in prov.exceptions:
                    story.append(Paragraph(f"• <font color='#b91c1c'>{exc}</font>", self.bullet_style))
                story.append(Spacer(1, 6))

                story.append(Paragraph(f"<b>Recommended Action:</b> {route.recommended_action}", self.body_style))
                story.append(Spacer(1, 10))

        story.append(Spacer(1, 10))

        # 4. Draft Formal Notice / Claim Letter
        if evaluation.has_coverage and evaluation.matched_routes:
            top_route = evaluation.matched_routes[0]
            story.append(Paragraph("3. Draft Formal Consumer Notice Letter", self.section_title))
            letter_text = (
                f"<b>Date:</b> {datetime.now(timezone.utc).strftime('%B %d, %Y')}<br/>"
                f"<b>To:</b> Claims Department / Customer Support ({top_route.provider})<br/>"
                f"<b>Subject:</b> Formal Claim Notice for {case.product_name} (Case ID: {case.case_id})<br/><br/>"
                f"Dear Sir/Madam,<br/><br/>"
                f"I am writing to formally request remedy regarding my <b>{case.product_name}</b>, purchased on <b>{case.purchase_date}</b>. "
                f"On <b>{case.failure_date}</b>, the item developed the following defect: <i>{case.defect_description}</i>.<br/><br/>"
                f"Based on the published criteria of <b>{top_route.title}</b>, I believe this product may qualify for remedy, "
                f"subject to your inspection and verification (Source reference: {top_route.primary_source.get('url')}). "
                f"Attached to this letter please find itemized proof of purchase, "
                f"photographic documentation of the defect, and all relevant payment confirmation.<br/><br/>"
                f"I request that you confirm receipt of this notice and provide written instructions for inspection, authorized repair, or replacement at your earliest convenience.<br/><br/>"
                f"Sincerely,<br/>"
                f"Consumer / Claimant"
            )
            letter_table = Table([[Paragraph(letter_text, self.body_style)]], colWidths=[530])
            letter_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ])
            )
            story.append(letter_table)
            story.append(Spacer(1, 14))

        # 5. Statutory Disclaimer
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        story.append(
            Paragraph(
                f"<b>Legal Notice & Disclaimer:</b> {evaluation.disclaimer}",
                self.disclaimer_style,
            )
        )

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
