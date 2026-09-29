import os
import boto3
from typing import Dict, Any, Optional
from src.models.schemas import ReceiptData


class TextractService:
    def __init__(self, region_name: Optional[str] = None):
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        try:
            self.client = boto3.client("textract", region_name=self.region_name)
        except Exception as e:
            self.client = None
            print(f"TextractService initialized in fallback mode: {e}")

    def analyze_receipt_bytes(self, image_bytes: bytes) -> ReceiptData:
        """
        Calls Amazon Textract AnalyzeExpense to extract structured receipt data:
        Vendor name, transaction date, line items, total amount, and payment details.
        """
        if not self.client:
            return ReceiptData(
                source="unavailable",
                raw_fields={"warning": "Amazon Textract is not available in this environment."},
            )

        try:
            response = self.client.analyze_expense(
                Document={"Bytes": image_bytes}
            )
            return self._parse_expense_response(response)
        except Exception as e:
            print(f"Error calling Textract AnalyzeExpense: {e}")
            return ReceiptData(
                source="unavailable",
                raw_fields={"error": type(e).__name__},
            )

    def _parse_expense_response(self, response: Dict[str, Any]) -> ReceiptData:
        extracted = ReceiptData(source="textract")
        raw_fields = {}

        expense_documents = response.get("ExpenseDocuments", [])
        if not expense_documents:
            return extracted

        doc = expense_documents[0]

        # Extract Summary Fields
        for field in doc.get("SummaryFields", []):
            field_type = field.get("Type", {}).get("Text", "")
            val_text = field.get("ValueDetection", {}).get("Text", "")
            raw_fields[field_type] = val_text

            if field_type == "VENDOR_NAME":
                extracted.store_name = val_text
            elif field_type in ["INVOICE_RECEIPT_DATE", "DOCUMENT_DATE"]:
                extracted.purchase_date = val_text
            elif field_type == "TOTAL":
                try:
                    # Clean currency symbols
                    clean_val = "".join(c for c in val_text if c.isdigit() or c == ".")
                    extracted.total_amount = float(clean_val)
                except ValueError:
                    pass
            elif field_type in ["PAYMENT_METHOD", "CARD_TYPE"]:
                extracted.payment_type = val_text

        # Extract line items: one name per line item. Textract returns both ITEM (the name) and
        # EXPENSE_ROW (the whole printed row); use ITEM and fall back to the row only when absent.
        item_names = []
        for group in doc.get("LineItemGroups", []):
            for line_item in group.get("LineItems", []):
                fields = {
                    f.get("Type", {}).get("Text", ""): f.get("ValueDetection", {}).get("Text", "").strip()
                    for f in line_item.get("LineItemExpenseFields", [])
                }
                name = fields.get("ITEM") or fields.get("EXPENSE_ROW")
                if name and name not in item_names:
                    item_names.append(name)

        if item_names:
            # First line item first: the UI pre-fills the product name from it.
            extracted.item_description = "; ".join(item_names)

        # Normalise the receipt date to ISO so it can pre-fill the purchase date.
        if extracted.purchase_date:
            try:
                from dateutil import parser as date_parser

                extracted.purchase_date = date_parser.parse(extracted.purchase_date, fuzzy=True).date().isoformat()
            except (ValueError, OverflowError):
                pass  # keep the raw text; the user confirms dates before evaluation

        # Confidence is Textract's own mean confidence over the fields we used, not a constant.
        used = [
            f.get("ValueDetection", {}).get("Confidence")
            for f in doc.get("SummaryFields", [])
            if f.get("Type", {}).get("Text") in ("VENDOR_NAME", "INVOICE_RECEIPT_DATE", "TOTAL")
        ]
        used = [c for c in used if isinstance(c, (int, float))]
        extracted.raw_fields = raw_fields
        extracted.confidence_score = round(sum(used) / len(used) / 100, 3) if used else 0.0
        return extracted
