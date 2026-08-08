from typing import Literal

from pydantic import BaseModel, Field


class ExtractedTestCaseItem(BaseModel):
    title: str
    steps: str = Field(description="Numbered test steps")
    expected_result: str
    test_type: Literal["happy_path", "edge_case", "negative"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    source_excerpt: str | None = Field(
        default=None,
        description="Short BRD quote or section reference when relevant",
    )
    source_section_path: str | None = Field(
        default=None,
        description="Matching [Section Path] from retrieved BRD chunks when present",
    )


class TestCaseGenerationOutput(BaseModel):
    test_cases: list[ExtractedTestCaseItem]


class TestCaseCoverageCritique(BaseModel):
    passes: bool
    missing_types: list[str] = Field(
        default_factory=list,
        description="Coverage gaps: happy_path, edge_case, negative",
    )
    feedback: str


class TestCaseRevisionOutput(BaseModel):
    test_cases: list[ExtractedTestCaseItem]
