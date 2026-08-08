"""Human-readable progress labels for async AI operations."""

from __future__ import annotations

from app.db.models.async_operation import OperationStatus
from app.db.models.llm_call_log import LlmCallLog

NODE_STEP_LABELS: dict[str, str] = {
    "feature_extract": "Extracting features",
    "feature_critique": "Checking feature coverage",
    "feature_revise": "Revising features",
    "feature_refine_from_answers": "Refining feature from answers",
    "sub_feature_generate": "Generating sub-features",
    "story_generate": "Generating stories",
    "story_invest_critique": "Checking INVEST quality",
    "story_revise": "Revising stories",
    "story_points_estimate": "Estimating story points",
    "story_points_critique": "Calibrating points",
    "story_points_revise": "Revising points",
    "test_case_generate": "Generating test cases",
    "test_case_critique": "Checking test coverage",
    "test_case_revise": "Revising test cases",
}

STATUS_LABELS: dict[str, str] = {
    OperationStatus.PENDING.value: "Queued…",
    OperationStatus.RUNNING.value: "Starting…",
    OperationStatus.SUCCEEDED.value: "Completed",
    OperationStatus.FAILED.value: "Failed",
    OperationStatus.CANCELLED.value: "Cancelled",
}


def format_operation_progress(
    *,
    status: str,
    latest_log: LlmCallLog | None = None,
) -> str:
    if status != OperationStatus.RUNNING.value:
        return STATUS_LABELS.get(status, status)

    if latest_log is None:
        return STATUS_LABELS[OperationStatus.RUNNING.value]

    label = NODE_STEP_LABELS.get(latest_log.node_name, latest_log.node_name)
    if latest_log.iteration and latest_log.iteration > 0:
        return f"{label} (round {latest_log.iteration})"
    return label
