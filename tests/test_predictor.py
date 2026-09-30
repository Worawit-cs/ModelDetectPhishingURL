import pytest

from predictor import predict_url, try_predict_url


@pytest.mark.parametrize("url", ["google.com", "youtube.com"])
def test_real_brand_domains_are_legitimate(url):
    level, score, features = predict_url(url)

    assert level == "Legitimate"
    assert 0.0 <= score <= 1.0
    assert len(features) == 18


@pytest.mark.parametrize("url", ["y0utube.com", "paypa1.com"])
def test_synthetic_typosquats_are_phishing(url):
    level, _, _ = predict_url(url)

    assert level == "Phishing"


@pytest.mark.parametrize(
    "url",
    [
        "docs.python.org/3/tutorial/",
        "github.com/openai/openai-python",
    ],
)
def test_known_dataset_path_bias_is_documented(url):
    """Regression record: these normal URLs are known false positives."""
    level, _, _ = predict_url(url)

    assert level == "Phishing"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "x" * 2_001,
        None,
        123,
        "://",
        "https://",
    ],
)
def test_invalid_input_is_handled_without_crashing(value):
    result, error = try_predict_url(value)

    assert result is None
    assert isinstance(error, str)
    assert error
