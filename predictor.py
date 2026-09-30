"""Load the trained bundle once and provide safe, URL-only predictions."""

from __future__ import annotations

import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

import joblib
import numpy as np
import pandas as pd
import streamlit as st

from features import configure_feature_extraction, extract_url_features


MODEL_PATH = Path(__file__).resolve().parent / "model" / "phishing_url_detector_v1.4.joblib"
MAX_URL_LENGTH = 2_000


@st.cache_resource(show_spinner=False)
def get_bundle():
    bundle = joblib.load(MODEL_PATH)
    required_keys = {
        "model",
        "feature_names",
        "suspicious_config",
        "typosquat_brands",
    }
    missing = required_keys.difference(bundle)
    if missing:
        raise ValueError(f"model bundle ขาด key: {sorted(missing)}")
    if len(bundle["feature_names"]) != 18:
        raise ValueError("model bundle ต้องมี feature_names 18 ตัว")

    configure_feature_extraction(bundle["feature_names"], bundle["typosquat_brands"])
    return bundle


def validate_url_input(value):
    if not isinstance(value, str):
        raise ValueError("กรุณากรอก URL เป็นข้อความ")
    if len(value) > MAX_URL_LENGTH:
        raise ValueError(f"URL ยาวเกิน {MAX_URL_LENGTH:,} ตัวอักษร")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError("กรุณากรอก URL ก่อนตรวจ")

    parse_target = cleaned if "://" in cleaned else "http://" + cleaned
    try:
        parsed = urlsplit(parse_target)
        hostname = (parsed.hostname or "").rstrip(".")
    except ValueError as exc:
        raise ValueError("รูปแบบ URL ไม่ถูกต้อง") from exc

    if not hostname or any(char.isspace() for char in hostname):
        raise ValueError("รูปแบบ URL ไม่ถูกต้องหรือไม่พบ domain")

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        if "." not in hostname:
            raise ValueError("กรุณากรอก URL ที่มี domain เช่น example.com")

    return cleaned


def predict_url(url):
    cleaned_url = validate_url_input(url)
    bundle = get_bundle()
    features = extract_url_features(cleaned_url)
    frame = pd.DataFrame([features], columns=bundle["feature_names"])

    classes = np.asarray(bundle["model"].classes_)
    phishing_columns = np.flatnonzero(classes == 0)
    if len(phishing_columns) != 1:
        raise ValueError("โมเดลไม่มี class 0 (Phishing) เพียงหนึ่ง class")
    score = float(bundle["model"].predict_proba(frame)[0, int(phishing_columns[0])])

    config = bundle["suspicious_config"]
    if score >= config["upper_threshold"]:
        level = "Phishing"
    elif score <= config["lower_threshold"]:
        level = "Legitimate"
    else:
        level = "Suspicious"
    return level, score, features


def try_predict_url(url):
    """UI-safe wrapper: malformed user input becomes a message, never a crash."""
    try:
        return predict_url(url), None
    except (TypeError, ValueError) as exc:
        return None, str(exc)
