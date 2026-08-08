from types import SimpleNamespace

from app.db.models.async_operation import OperationStatus
from app.utils.operation_progress import format_operation_progress


def test_progress_queued_when_pending():
    assert (
        format_operation_progress(status=OperationStatus.PENDING.value, latest_log=None)
        == "Queued…"
    )


def test_progress_starting_when_running_without_log():
    assert (
        format_operation_progress(status=OperationStatus.RUNNING.value, latest_log=None)
        == "Starting…"
    )


def test_progress_uses_node_label_and_iteration():
    log = SimpleNamespace(node_name="story_invest_critique", iteration=2)
    assert (
        format_operation_progress(status=OperationStatus.RUNNING.value, latest_log=log)
        == "Checking INVEST quality (round 2)"
    )


def test_progress_falls_back_to_node_name():
    log = SimpleNamespace(node_name="custom_node", iteration=0)
    assert (
        format_operation_progress(status=OperationStatus.RUNNING.value, latest_log=log)
        == "custom_node"
    )
