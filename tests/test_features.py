from predictor import get_bundle
from features import extract_url_features


def test_feature_count_and_order_match_bundle():
    bundle = get_bundle()
    features = extract_url_features("https://google.com")

    assert len(features) == 18
    assert list(features) == bundle["feature_names"]


def test_offline_brand_list_matches_bundle():
    bundle = get_bundle()

    assert len(bundle["typosquat_brands"]) == 136
    assert extract_url_features("google.com")["IsBrandDomain"] == 1
    assert extract_url_features("y0utube.com")["BrandLookalike"] == 1
