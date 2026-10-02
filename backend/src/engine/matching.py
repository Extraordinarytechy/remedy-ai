"""Product-name matching shared by the eligibility engine and the model on-sale date check."""
import re

# Words that mean the product is an accessory, an app or a service, not the device a record covers
# ("iPhone 18 Pro case", "Apple TV app", "Apple Watch band").
NOT_THE_DEVICE = re.compile(
    r"\b(case|cases|cover|charger|cable|adapter|protector|strap|band|bands|stand|mount|holder|skin|sleeve|dock|"
    r"stylus|pencil|keyboard|app|subscription)\b"
)


def phrase_pattern(phrase: str) -> "re.Pattern[str]":
    """Whole-word pattern for a device name, so "iPhone 12" doesn't match "iPhone 120" or "iPhone 12e"."""
    return re.compile(rf"(?<![a-z0-9]){re.escape(phrase.lower())}(?![a-z0-9])")


def product_text(product_name: str, product_model: str = "") -> str:
    return f"{product_name} {product_model or ''}".lower()
