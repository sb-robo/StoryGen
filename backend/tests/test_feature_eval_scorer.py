from pathlib import Path

from evals.score_features import load_expected, score_feature_list

GOLDEN = Path(__file__).resolve().parents[1] / "evals" / "golden"


def test_golden_expected_fixture_loads():
    expected = load_expected(GOLDEN / "sample_features.expected.json")
    assert expected["min_features"] >= 1
    assert "auth" in expected["required_themes"]


def test_scorer_passes_well_structured_features():
    expected = load_expected(GOLDEN / "sample_features.expected.json")
    features = [
        {
            "title": "Authentication",
            "description": "Merchants and admins sign in securely with MFA for admin roles.",
            "confidence": 0.9,
            "rationale": "Covered in Authentication section",
            "source_excerpt": "Multi-factor authentication is required",
            "clarifying_questions": [],
        },
        {
            "title": "Payment Collection",
            "description": "Merchants collect card payments and retry failed charges with clear errors.",
            "confidence": 0.85,
            "rationale": "Core payment capability",
            "source_excerpt": "collect card payments",
            "clarifying_questions": [],
        },
        {
            "title": "Settlement Reporting",
            "description": "Admins export settlement reports as CSV for a selected date range.",
            "confidence": 0.8,
            "rationale": "Reporting section",
            "source_excerpt": "export settlement reports",
            "clarifying_questions": [],
        },
    ]
    result = score_feature_list(features, expected)
    assert result["passed"] is True
    assert result["score"] == 1.0


def test_scorer_fails_story_shaped_titles():
    expected = load_expected(GOLDEN / "sample_features.expected.json")
    features = [
        {
            "title": "As a merchant I want to pay",
            "description": "Short",
            "confidence": 0.9,
            "rationale": "x",
            "source_excerpt": None,
            "clarifying_questions": [],
        }
    ]
    result = score_feature_list(features, expected)
    assert result["passed"] is False
    names = {c["name"]: c["ok"] for c in result["checks"]}
    assert names["no_story_shaped_titles"] is False
