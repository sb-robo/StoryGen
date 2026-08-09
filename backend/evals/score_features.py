"""Structural scorer for feature-extraction golden sets (no live LLM required)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def score_feature_list(
    features: list[dict[str, Any]],
    expected: dict[str, Any],
) -> dict[str, Any]:
    """
    Score a feature list against golden structural expectations.

    Returns {passed, score, checks: [{name, ok, detail}]}.
    """
    checks: list[dict[str, Any]] = []
    count = len(features)
    min_f = int(expected.get("min_features", 1))
    max_f = int(expected.get("max_features", 50))
    checks.append(
        {
            "name": "feature_count_range",
            "ok": min_f <= count <= max_f,
            "detail": f"{count} features (want {min_f}-{max_f})",
        }
    )

    titles = [str(f.get("title") or "") for f in features]
    lowered = " ".join(t.lower() for t in titles)
    for theme in expected.get("required_themes", []):
        ok = theme.lower() in lowered
        checks.append(
            {
                "name": f"theme:{theme}",
                "ok": ok,
                "detail": "present in titles" if ok else "missing from titles",
            }
        )

    forbidden = expected.get("forbidden_title_substrings", [])
    bad = []
    for title in titles:
        tl = title.lower()
        for frag in forbidden:
            if frag.lower() in tl:
                bad.append(title)
                break
    checks.append(
        {
            "name": "no_story_shaped_titles",
            "ok": not bad,
            "detail": "ok" if not bad else f"bad titles: {bad}",
        }
    )

    rules = expected.get("rules", {})
    min_desc = int(rules.get("require_description_min_chars", 0))
    short = [
        f.get("title")
        for f in features
        if len(str(f.get("description") or "")) < min_desc
    ]
    checks.append(
        {
            "name": "description_length",
            "ok": not short,
            "detail": "ok" if not short else f"too short: {short}",
        }
    )

    if rules.get("require_rationale"):
        missing_r = [f.get("title") for f in features if not str(f.get("rationale") or "").strip()]
        checks.append(
            {
                "name": "rationale_present",
                "ok": not missing_r,
                "detail": "ok" if not missing_r else f"missing: {missing_r}",
            }
        )

    if rules.get("prefer_source_excerpt"):
        with_excerpt = sum(1 for f in features if str(f.get("source_excerpt") or "").strip())
        ok = with_excerpt >= max(1, count // 2) if count else False
        checks.append(
            {
                "name": "source_excerpt_coverage",
                "ok": ok,
                "detail": f"{with_excerpt}/{count} have source_excerpt",
            }
        )

    max_q_high = rules.get("max_clarifying_questions_when_high_confidence")
    if max_q_high is not None:
        offenders = []
        for f in features:
            conf = float(f.get("confidence") or 0)
            qs = f.get("clarifying_questions") or []
            if conf >= 0.85 and len(qs) > int(max_q_high):
                offenders.append(f.get("title"))
        checks.append(
            {
                "name": "high_confidence_few_questions",
                "ok": not offenders,
                "detail": "ok" if not offenders else f"offenders: {offenders}",
            }
        )

    passed = all(c["ok"] for c in checks)
    score = sum(1 for c in checks if c["ok"]) / len(checks) if checks else 0.0
    return {"passed": passed, "score": round(score, 3), "checks": checks}


def load_expected(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
