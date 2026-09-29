import os
import boto3
from typing import Dict, Any, Optional
from backend.src.models.schemas import ReceiptData


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
                confidence_score=0.5,
                raw_fields={"warning": "AWS Textract client not available; using fallback."},
            )

        try:
            response = self.client.analyze_expense(
                Document={"Bytes": image_bytes}
            )
            return self._parse_expense_response(response)
        except Exception as e:
            print(f"Error calling Textract AnalyzeExpense: {e}")
            return ReceiptData(
                confidence_score=0.0,
                raw_fields={"error": str(e)},
            )

    def _parse_expense_response(self, response: Dict[str, Any]) -> ReceiptData:
        extracted = ReceiptData()
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

        # Extract Line Items
        item_names = []
        for group in doc.get("LineItemGroups", []):
            for line_item in group.get("LineItems", []):
                for expense_field in line_item.get("LineItemExpenseFields", []):
                    field_type = expense_field.get("Type", {}).get("Text", "")
                    if field_type in ["ITEM", "EXPENSE_ROW"]:
                        item_names.append(expense_field.get("ValueDetection", {}).get("Text", ""))

        if item_names:
            extracted.item_description = ", ".join(item_names)

        extracted.raw_fields = raw_fields
        extracted.confidence_score = 0.95
        return extracted
