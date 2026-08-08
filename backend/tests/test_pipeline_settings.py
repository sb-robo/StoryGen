from app.schemas.pipeline_settings_schema import (
    BrdPipelineSettings,
    FeatureCountPreference,
    format_pipeline_context,
    parse_pipeline_settings,
)


def test_parse_defaults():
    settings = parse_pipeline_settings(None)
    assert settings.feature_count == FeatureCountPreference.AUTO
    assert settings.instructions is None


def test_blank_strings_become_none():
    settings = BrdPipelineSettings(instructions="  ", domain_context="Acme billing")
    assert settings.instructions is None
    assert settings.domain_context == "Acme billing"


def test_format_features_context_includes_count_and_scope():
    settings = BrdPipelineSettings(
        instructions="Ignore appendix",
        out_of_scope="Mobile app",
        feature_count=FeatureCountPreference.FEWER,
    )
    text = format_pipeline_context(settings, for_stage="features")
    assert "Ignore appendix" in text
    assert "Mobile app" in text
    assert "5–8" in text


def test_format_stories_uses_story_style():
    settings = BrdPipelineSettings(story_style="job_story", personas="Admin, Merchant")
    text = format_pipeline_context(settings, for_stage="stories")
    assert "When" in text
    assert "Admin, Merchant" in text
