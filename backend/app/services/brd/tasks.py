import time

from app.db.session import async_session_local
from app.repositories.operation_repository import OperationRepository
from app.services.brd.service import BrdService
from app.utils.process_tracker import track, track_error


async def run_brd_parse_task(operation_id: str) -> None:
    """
    Background worker keyed by operation_id.

    Updates async_operations to succeeded/failed and parses the linked BRD.
    """
    from app.db.models.async_operation import OperationStatus

    started = time.perf_counter()
    async with async_session_local() as session:
        op_repo = OperationRepository(session)
        try:
            operation = await op_repo.get_by_id(operation_id)
            if not operation:
                track_error("operation not found")
                return
            if operation.status == OperationStatus.CANCELLED.value:
                track("skipped (cancelled)")
                return

            track(
                f"start {operation.operation_type}",
                brd_id=operation.resource_id,
            )

            await op_repo.mark_running(operation)
            await session.commit()

            operation = await op_repo.get_by_id(operation_id)
            if not operation or operation.status == OperationStatus.CANCELLED.value:
                track("cancelled before work started")
                return

            if operation.resource_id is None:
                await op_repo.mark_failed(operation, "Operation has no linked BRD")
                await session.commit()
                track_error("failed (no linked BRD)")
                return

            brd_service = BrdService(session)
            brd = await brd_service.complete_parse(operation.resource_id)

            operation = await op_repo.get_by_id(operation_id)
            if not operation or operation.status == OperationStatus.CANCELLED.value:
                track("cancelled during work")
                return

            if brd is None:
                await op_repo.mark_failed(operation, "BRD not found for operation")
                track_error("failed (BRD not found)")
            elif brd.status == "parse_failed":
                await op_repo.mark_failed(
                    operation, brd.error_message or "BRD parse failed"
                )
                track_error(
                    "parse failed",
                    brd_id=brd.id,
                    error=brd.error_message,
                )
            else:
                await op_repo.mark_succeeded(operation)
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                track(
                    f"done {operation.operation_type}",
                    brd_id=brd.id,
                    status="succeeded",
                    ms=elapsed_ms,
                )

            await session.commit()
        except Exception as exc:
            await session.rollback()
            track_error("failed", exc=exc)
            try:
                operation = await op_repo.get_by_id(operation_id)
                if operation and operation.status != OperationStatus.CANCELLED.value:
                    await op_repo.mark_failed(operation, str(exc))
                    await session.commit()
            except Exception as mark_exc:
                await session.rollback()
                track_error(
                    "could not mark operation failed",
                    exc=mark_exc,
                )
