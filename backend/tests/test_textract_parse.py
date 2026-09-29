from src.services.textract_service import TextractService


def field(t, text, conf=99.0):
    return {"Type": {"Text": t}, "ValueDetection": {"Text": text, "Confidence": conf}}


RESPONSE = {
    "ExpenseDocuments": [{
        "SummaryFields": [
            field("VENDOR_NAME", "BEST BUY", 98.0),
            field("INVOICE_RECEIPT_DATE", "11/24/2023", 96.0),
            field("TOTAL", "$885.58", 94.0),
        ],
        "LineItemGroups": [{
            "LineItems": [
                {"LineItemExpenseFields": [field("ITEM", "Apple iPhone 14 Plus 128GB"), field("EXPENSE_ROW", "Apple iPhone 14 Plus 128GB 799.99")]},
                {"LineItemExpenseFields": [field("EXPENSE_ROW", "Screen protector 19.99")]},
            ]
        }],
    }]
}


def test_parse_expense_uses_item_name_once_and_iso_date():
    svc = TextractService.__new__(TextractService)  # no AWS client needed for parsing
    r = svc._parse_expense_response(RESPONSE)
    assert r.source == "textract"
    assert r.store_name == "BEST BUY"
    assert r.purchase_date == "2023-11-24"
    assert r.total_amount == 885.58
    assert r.item_description == "Apple iPhone 14 Plus 128GB; Screen protector 19.99"
    assert r.confidence_score == round((98 + 96 + 94) / 3 / 100, 3)
