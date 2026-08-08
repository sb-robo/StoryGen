"""User-provided BRD pipeline settings that steer AI generation (not the AI itself)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeatureCountPreference(StrEnum):
    AUTO = "auto"
    FEWER = "fewer"  # ~5–8
    BALANCED = "balanced"  # ~8–12
    GRANULAR = "granular"  # ~12–20


class SubFeatureCountPreference(StrEnum):
    AUTO = "auto"
    FEWER = "fewer"  # 2–3
    BALANCED = "balanced"  # 3–5
    MORE = "more"  # 5–8


class StoryStyle(StrEnum):
    CLASSIC = "classic"  # As a… I want… so that…
    JOB_STORY = "job_story"  # When… I want… so I can…
    PLAIN = "plain"


class PointingScale(StrEnum):
    FIBONACCI = "fibonacci"
    T_SHIRT = "t_shirt"
    LINEAR = "linear"


class TestDepth(StrEnum):
    HAPPY_PATH = "happy_path"
    STANDARD = "standard"
    THOROUGH = "thorough"


class BrdChunkStrategy(StrEnum):
    """How parsed BRD markdown is split before embedding / retrieval."""

    SECTION = "section"
    SUBSECTION = "subsection"
    REQUIREMENT = "requirement"
    FIXED_SIZE = "fixed_size"
    HYBRID = "hybrid"


# Backward-compatible alias
BrdChunkLevel = BrdChunkStrategy


CHUNK_STRATEGY_GUIDE: dict[BrdChunkStrategy, dict[str, str]] = {
    BrdChunkStrategy.SECTION: {
        "label": "Section (H1 + H2)",
        "summary": "Split on major section headings — recommended default.",
        "when_to_use": (
            "Standard BRDs with clear headings. Best for feature extraction and "
            "first-pass review on most documents."
        ),
        "tradeoffs": "Broader chunks; may merge related sub-topics under one section.",
    },
    BrdChunkStrategy.SUBSECTION: {
        "label": "Subsection (H1 + H2 + H3)",
        "summary": "Finer splits at third-level headings.",
        "when_to_use": (
            "Long BRDs where H2 sections are still too large, or when you need tighter "
            "grounding for stories and test cases."
        ),
        "tradeoffs": "More chunks; slightly higher indexing cost.",
    },
    BrdChunkStrategy.REQUIREMENT: {
        "label": "Requirement-aware",
        "summary": "Split on numbered requirements and shall/must bullet items.",
        "when_to_use": (
            "Enterprise BRDs with REQ-001 / 1.2.3 numbering or explicit shall/must "
            "statements. Best traceability from story → requirement."
        ),
        "tradeoffs": "Weak when the BRD has no numbered requirements or IDs.",
    },
    BrdChunkStrategy.FIXED_SIZE: {
        "label": "Fixed-size windows",
        "summary": "Even-sized chunks (~1500 chars) with overlap.",
        "when_to_use": (
            "Unstructured or flat documents with poor headings, pasted specs, or legacy "
            "Word exports where structure-aware splitting fails."
        ),
        "tradeoffs": "May cut mid-requirement; use only when headings are unreliable.",
    },
    BrdChunkStrategy.HYBRID: {
        "label": "Hybrid (best quality)",
        "summary": "Sections → table extraction → semantic split for large sections.",
        "when_to_use": (
            "Production BRDs with tables, long sections, and mixed formatting. Best "
            "overall retrieval quality when OpenAI embeddings are configured."
        ),
        "tradeoffs": "Slowest indexing; uses embedding API during parse/reparse.",
    },
}


FEATURE_COUNT_GUIDANCE = {
    FeatureCountPreference.AUTO: "Choose a natural count from the BRD; prefer fewer high-quality features over many overlapping ones.",
    FeatureCountPreference.FEWER: "Aim for about 5–8 epic-level features. Merge related capabilities aggressively.",
    FeatureCountPreference.BALANCED: "Aim for about 8–12 features with clear boundaries.",
    FeatureCountPreference.GRANULAR: "Aim for about 12–20 more granular features when the BRD supports it. Avoid inventing scope.",
}

SUB_FEATURE_COUNT_GUIDANCE = {
    SubFeatureCountPreference.AUTO: "Prefer 2–6 sub-features unless the parent feature is trivial.",
    SubFeatureCountPreference.FEWER: "Prefer 2–3 larger sub-features.",
    SubFeatureCountPreference.BALANCED: "Prefer 3–5 sub-features.",
    SubFeatureCountPreference.MORE: "Prefer 5–8 finer-grained sub-features when justified.",
}

STORY_STYLE_GUIDANCE = {
    StoryStyle.CLASSIC: "Write each story description as: As a [role], I want [goal], so that [benefit].",
    StoryStyle.JOB_STORY: "Write each story description as a job story: When [situation], I want to [motivation], so I can [outcome].",
    StoryStyle.PLAIN: "Write plain imperative story descriptions (no fixed template). Keep them user-valued and testable.",
}

POINTING_SCALE_GUIDANCE = {
    PointingScale.FIBONACCI: "Use modified Fibonacci points: 1, 2, 3, 5, 8, 13, 21.",
    PointingScale.T_SHIRT: (
        "Use t-shirt sizing mapped to points: XS=1, S=2, M=3, L=5, XL=8, XXL=13. "
        "Return the numeric point value (not the letter)."
    ),
    PointingScale.LINEAR: "Use a linear 1–10 scale (integers only). Prefer mid-range for typical work.",
}

TEST_DEPTH_GUIDANCE = {
    TestDepth.HAPPY_PATH: "Focus on happy-path tests. Add edge/negative only when critical.",
    TestDepth.STANDARD: "Cover happy path plus relevant edge and negative cases.",
    TestDepth.THOROUGH: "Be thorough: happy path, edge cases, negatives, and validation/boundary scenarios.",
}


class BrdPipelineSettings(BaseModel):
    """Stored on the BRD and injected into generation prompts."""

    model_config = ConfigDict(extra="ignore")

    instructions: str | None = Field(
        default=None,
        max_length=4000,
        description="Free-form guidance for feature/sub-feature generation",
    )
    domain_context: str | None = Field(
        default=None,
        max_length=500,
        description="Product/domain one-liner",
    )
    in_scope: str | None = Field(default=None, max_length=2000)
    out_of_scope: str | None = Field(default=None, max_length=2000)
    personas: str | None = Field(
        default=None,
        max_length=1000,
        description="Comma-separated or short list of roles/personas",
    )
    feature_count: FeatureCountPreference = FeatureCountPreference.AUTO
    sub_feature_count: SubFeatureCountPreference = SubFeatureCountPreference.AUTO
    story_style: StoryStyle = StoryStyle.CLASSIC
    pointing_scale: PointingScale = PointingScale.FIBONACCI
    test_depth: TestDepth = TestDepth.STANDARD
    chunk_level: BrdChunkStrategy = Field(
        default=BrdChunkStrategy.SECTION,
        description="BRD chunking strategy applied on parse/reparse",
    )
    export_project_key: str | None = Field(default=None, max_length=32)
    export_epic_prefix: str | None = Field(default=None, max_length=64)

    @field_validator(
        "instructions",
        "domain_context",
        "in_scope",
        "out_of_scope",
        "personas",
        "export_project_key",
        "export_epic_prefix",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


def parse_pipeline_settings(raw: object | None) -> BrdPipelineSettings:
    if raw is None:
        return BrdPipelineSettings()
    if isinstance(raw, BrdPipelineSettings):
        return raw
    if isinstance(raw, dict):
        data = dict(raw)
        # Accept legacy key names
        if "chunk_strategy" in data and "chunk_level" not in data:
            data["chunk_level"] = data.pop("chunk_strategy")
        return BrdPipelineSettings.model_validate(data)
    return BrdPipelineSettings()


def format_pipeline_context(
    settings: BrdPipelineSettings | dict | None,
    *,
    for_stage: str,
) -> str:
    """
    Build a prompt block for a pipeline stage.

    for_stage: features | sub_features | stories | points | tests
    """
    s = parse_pipeline_settings(settings)
    lines: list[str] = ["--- USER PIPELINE SETTINGS ---"]

    if s.domain_context:
        lines.append(f"Domain / product: {s.domain_context}")
    if s.personas:
        lines.append(f"Personas / roles: {s.personas}")
    if s.in_scope:
        lines.append(f"In scope: {s.in_scope}")
    if s.out_of_scope:
        lines.append(f"Out of scope (do not invent features for these): {s.out_of_scope}")
    if s.instructions:
        lines.append(f"User instructions (authoritative): {s.instructions}")

    if for_stage == "features":
        lines.append(f"Feature count preference: {FEATURE_COUNT_GUIDANCE[s.feature_count]}")
    elif for_stage == "sub_features":
        lines.append(
            f"Sub-feature count preference: {SUB_FEATURE_COUNT_GUIDANCE[s.sub_feature_count]}"
        )
    elif for_stage == "stories":
        lines.append(f"Story style: {STORY_STYLE_GUIDANCE[s.story_style]}")
        if s.personas:
            lines.append("Prefer the listed personas as story roles when applicable.")
    elif for_stage == "points":
        lines.append(f"Pointing scale: {POINTING_SCALE_GUIDANCE[s.pointing_scale]}")
    elif for_stage == "tests":
        lines.append(f"Test depth: {TEST_DEPTH_GUIDANCE[s.test_depth]}")

    if len(lines) == 1:
        lines.append("(none provided — use defaults)")

    lines.append("--- END SETTINGS ---")
    return "\n".join(lines)
