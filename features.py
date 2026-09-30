"""Offline URL feature extraction copied from the v1.4 training notebook.

No function in this module performs network I/O.  The brand list is supplied by
the serialized model bundle so inference uses the same offline vocabulary as
training.
"""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit


BRAND_EDIT1_MIN_LEN = 6
BRAND_KEYWORD_MIN_LEN = 5

HOMOGLYPH_TO_LETTER = {
    "0": "o",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "$": "s",
    "@": "a",
}
SECOND_LEVEL_LABELS = {"co", "com", "net", "org", "gov", "edu", "ac", "or", "go", "in", "ne"}

TYPOSQUAT_FEATURE_NAMES = [
    "IsBrandDomain",
    "BrandLookalike",
    "BrandKeywordMisuse",
    "DigitBetweenLetters",
    "HyphenCountInHost",
]

MODEL_FEATURE_NAMES = [
    "URLLength",
    "DomainLength",
    "IsDomainIP",
    "TLDLength",
    "NoOfSubDomain",
    "HasObfuscation",
    "NoOfObfuscatedChar",
    "NoOfLettersInURL",
    "NoOfDegitsInURL",
    "NoOfEqualsInURL",
    "NoOfQMarkInURL",
    "NoOfAmpersandInURL",
    "NoOfOtherSpecialCharsInURL",
    "IsBrandDomain",
    "BrandLookalike",
    "BrandKeywordMisuse",
    "DigitBetweenLetters",
    "HyphenCountInHost",
]

PERCENT_ENCODED_PATTERN = re.compile(r"%[0-9A-Fa-f]{2}")
MARKDOWN_URL_PATTERN = re.compile(r"^\[[^\]]*\]\((https?://[^)]+)\)$", re.IGNORECASE)

BRAND_SET: set[str] = set()
BRAND_EDIT1: dict[str, str] = {}
BRAND_KEYWORD_PATTERN: re.Pattern[str] | None = None


def has_path_or_query(url):
    raw_url = str(url).strip()
    parse_target = raw_url if "://" in raw_url else "http://" + raw_url
    parsed = urlsplit(parse_target)
    return (parsed.path not in ("", "/")) or bool(parsed.query)


def edit1_variants(word):
    # ทุกคำที่ต่างจาก word ไม่เกิน 1 การแก้ (ลบ / สลับที่ / แทนที่ / แทรก)
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789-"
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = {left + right[1:] for left, right in splits if right}
    transposes = {left + right[1] + right[0] + right[2:] for left, right in splits if len(right) > 1}
    replaces = {left + ch + right[1:] for left, right in splits if right for ch in alphabet}
    inserts = {left + ch + right for left, right in splits for ch in alphabet}
    return (deletes | transposes | replaces | inserts) - {word}


def configure_feature_extraction(feature_names, brands):
    """Configure the exact feature order and offline brands stored in the bundle."""
    global MODEL_FEATURE_NAMES, BRAND_SET, BRAND_EDIT1, BRAND_KEYWORD_PATTERN

    MODEL_FEATURE_NAMES = list(feature_names)
    BRAND_SET = {str(name).lower() for name in brands if str(name).isalnum()}

    brand_edit1: dict[str, str] = {}
    for brand in BRAND_SET:
        if len(brand) >= BRAND_EDIT1_MIN_LEN:
            for variant in edit1_variants(brand):
                if variant not in BRAND_SET:
                    brand_edit1.setdefault(variant, brand)
    BRAND_EDIT1 = brand_edit1

    keyword_brands = sorted(
        (brand for brand in BRAND_SET if len(brand) >= BRAND_KEYWORD_MIN_LEN),
        key=len,
        reverse=True,
    )
    BRAND_KEYWORD_PATTERN = re.compile("|".join(re.escape(name) for name in keyword_brands))


def homoglyph_candidates(label):
    # แปลงตัวเลข/สัญลักษณ์ที่หน้าตาคล้ายตัวอักษรกลับเป็นตัวอักษร เช่น y0utube -> youtube, paypa1 -> paypal
    base = "".join(HOMOGLYPH_TO_LETTER.get(ch, ch) for ch in label).replace("rn", "m").replace("vv", "w")
    if "1" in base:
        return {base.replace("1", "l"), base.replace("1", "i")}
    return {base}


def registrable_label(hostname):
    # ชื่อหลักของ domain เช่น youtube จาก www.youtube.com, ktb จาก ktb.co.th
    parts = [part for part in hostname.split(".") if part]
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in SECOND_LEVEL_LABELS:
        return parts[-3]
    if len(parts) >= 2:
        return parts[-2]
    return parts[0] if parts else ""


def typosquat_features(hostname, is_domain_ip, path_query):
    if is_domain_ip or not hostname:
        return {name: 0 for name in TYPOSQUAT_FEATURE_NAMES}

    if BRAND_KEYWORD_PATTERN is None:
        raise RuntimeError("ยังไม่ได้ตั้งค่ารายชื่อแบรนด์จาก model bundle")

    label = registrable_label(hostname)
    is_brand = label in BRAND_SET

    lookalike = 0
    keyword_misuse = 0
    if not is_brand:
        normalized = [c for c in homoglyph_candidates(label) if c != label]
        lookalike = int(label in BRAND_EDIT1 or any(c in BRAND_SET or c in BRAND_EDIT1 for c in normalized))
        keyword_misuse = int(BRAND_KEYWORD_PATTERN.search(hostname + "/" + path_query.lower()) is not None)

    return {
        "IsBrandDomain": int(is_brand),
        "BrandLookalike": lookalike,
        "BrandKeywordMisuse": keyword_misuse,
        "DigitBetweenLetters": len(re.findall(r"(?<=[a-z])[0-9]+(?=[a-z])", label)),
        "HyphenCountInHost": hostname.count("-"),
    }


def normalize_url(url):
    raw_url = str(url).strip()
    if not raw_url:
        raise ValueError("URL ต้องไม่เป็นค่าว่าง")

    markdown_match = MARKDOWN_URL_PATTERN.fullmatch(raw_url)
    if markdown_match:
        raw_url = markdown_match.group(1)

    if "://" not in raw_url:
        raw_url = "http://" + raw_url

    parsed = urlsplit(raw_url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        raise ValueError("ไม่พบ Domain ใน URL")

    # ตัด www เพื่อไม่ให้โมเดลใช้รูปแบบการเก็บข้อมูลเป็นทางลัด
    if hostname.startswith("www."):
        hostname = hostname[4:]

    try:
        port = parsed.port
    except ValueError:
        port = None

    netloc = hostname
    is_default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    if port is not None and not is_default_port:
        netloc = f"{hostname}:{port}"

    # root slash ไม่มีความหมายเชิงโครงสร้าง จึงทำให้ / และค่าว่างเหมือนกัน
    path = "" if parsed.path == "/" and not parsed.query else parsed.path

    # fragment ไม่ถูกส่งไปยัง web server จึงไม่ใช้เป็น Feature
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def extract_url_features(url):
    # สร้าง features จากข้อความ URL เท่านั้น ไม่มี network request
    raw_url = normalize_url(url)
    parsed = urlsplit(raw_url)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    scheme = parsed.scheme.lower()

    try:
        ipaddress.ip_address(hostname)
        is_domain_ip = 1
    except ValueError:
        is_domain_ip = 0

    domain_parts = [part for part in hostname.split(".") if part]
    tld_length = 0 if is_domain_ip or not domain_parts else len(domain_parts[-1])
    no_of_subdomains = 0 if is_domain_ip else max(len(domain_parts) - 2, 0)

    lexical_text = raw_url.split("://", 1)[-1]

    denominator = max(len(lexical_text), 1)
    encoded_tokens = PERCENT_ENCODED_PATTERN.findall(lexical_text)
    no_of_obfuscated = len(encoded_tokens)
    no_of_letters = sum(char.isalpha() for char in lexical_text)
    no_of_digits = sum(char.isdigit() for char in lexical_text)

    excluded_special = {"=", "?", "&", "%"}
    no_of_other_special = sum(
        (not char.isalnum()) and char not in excluded_special
        for char in lexical_text
    )

    features = {
        "URLLength": len(raw_url),
        "DomainLength": len(hostname),
        "IsDomainIP": is_domain_ip,
        "TLDLength": tld_length,
        "NoOfSubDomain": no_of_subdomains,
        "HasObfuscation": int(no_of_obfuscated > 0),
        "NoOfObfuscatedChar": no_of_obfuscated,
        "ObfuscationRatio": no_of_obfuscated / denominator,
        "NoOfLettersInURL": no_of_letters,
        "LetterRatioInURL": no_of_letters / denominator,
        "NoOfDegitsInURL": no_of_digits,
        "DegitRatioInURL": no_of_digits / denominator,
        "NoOfEqualsInURL": lexical_text.count("="),
        "NoOfQMarkInURL": lexical_text.count("?"),
        "NoOfAmpersandInURL": lexical_text.count("&"),
        "NoOfOtherSpecialCharsInURL": no_of_other_special,
        "SpacialCharRatioInURL": no_of_other_special / denominator,
        "IsHTTPS": int(scheme == "https"),
    }
    # Typosquat features (เทียบกับรายชื่อแบรนด์ offline)
    path_query = parsed.path + ("?" + parsed.query if parsed.query else "")
    features.update(typosquat_features(hostname, bool(is_domain_ip), path_query))

    missing = [name for name in MODEL_FEATURE_NAMES if name not in features]
    if missing:
        raise ValueError(f"ไม่สามารถสร้าง feature ที่โมเดลต้องใช้: {missing}")
    return {name: features[name] for name in MODEL_FEATURE_NAMES}
