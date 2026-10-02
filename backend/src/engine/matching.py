"""Product-name matching shared by the eligibility engine and the model on-sale date check."""
import re

# Words that mean the product is an accessory, an app or a service, not the device a record covers
# ("iPhone 18 Pro case", "Apple TV app", "Apple Watch band").
NOT_THE_DEVICE = re.compile(
    r"\b(case|cases|cover|charger|cable|adapter|protector|strap|band|bands|stand|mount|holder|skin|sleeve|dock|"
    r"stylus|pencil|keyboard|app|subscription)\b"
)

# What comes with the device: "iMac with Magic Keyboard", "Apple Watch Series 10 ... with Sport Band".
WITH_CLAUSE = re.compile(r"\bwith\b")

# Case words that are part of an Apple device's own name, each read only for its family:
# "Apple Watch Series 10 Aluminum Case" is the watch, "AirPods Pro 3 Charging Case" is the AirPods.
# A plain "AirPods case" or "iPhone 17 aluminum case" is still an accessory.
OFFICIAL_NAME_PARTS = [
    (re.compile(r"(?<![a-z0-9])apple watch(?![a-z0-9])"),
     re.compile(r"\b(aluminum|aluminium|titanium|stainless steel|ceramic) case\b")),
    (re.compile(r"(?<![a-z0-9])airpods(?![a-z0-9])"),
     re.compile(r"\b(magsafe |wireless |lightning |usb-c )?charging case\b")),
]


def phrase_pattern(phrase: str) -> "re.Pattern[str]":
    """Whole-word pattern for a device name, so "iPhone 12" doesn't match "iPhone 120" or "iPhone 12e"."""
    return re.compile(rf"(?<![a-z0-9]){re.escape(phrase.lower())}(?![a-z0-9])")


def product_text(product_name: str, product_model: str = "") -> str:
    return f"{product_name} {product_model or ''}".lower()


def main_product(text: str) -> str:
    """The product itself: the text before any "with ..." clause."""
    return WITH_CLAUSE.split(text, maxsplit=1)[0]


def without_official_parts(rest: str, text: str) -> str:
    """`rest` with the case words of an Apple device's own name removed, when `text` names that device."""
    for family, part in OFFICIAL_NAME_PARTS:
        if family.search(text):
            rest = part.sub(" ", rest)
    return rest


def has_accessory_word(text: str) -> bool:
    """True when the product itself (not what comes with it) reads as an accessory or an app."""
    main = main_product(text)
    return bool(NOT_THE_DEVICE.search(without_official_parts(main, main)))
