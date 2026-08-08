import logging

from app.db.session import async_session_local
from app.repositories.operation_repository import OperationRepository
from app.services.brd.service import BrdService

logger = logging.getLogger(__name__)


async def run_brd_parse_task(operation_id: str) -> None:
    """
    Background worker keyed by operation_id.

    Updates async_operations to succeeded/failed and parses the linked BRD.
    """
    from app.db.models.async_operation import OperationStatus

    async with async_session_local() as session:
        op_repo = OperationRepository(session)
        try:
            operation = await op_repo.get_by_id(operation_id)
            if not operation:
                logger.error("Operation not found: %s", operation_id)
                return
            if operation.status == OperationStatus.CANCELLED.value:
                logger.info("Skipping cancelled BRD parse: %s", operation_id)
                return

            await op_repo.mark_running(operation)
            await session.commit()

            operation = await op_repo.get_by_id(operation_id)
            if not operation or operation.status == OperationStatus.CANCELLED.value:
                logger.info("BRD parse cancelled before work: %s", operation_id)
                return

            if operation.resource_id is None:
                await op_repo.mark_failed(operation, "Operation has no linked BRD")
                await session.commit()
                return

            brd_service = BrdService(session)
            brd = await brd_service.complete_parse(operation.resource_id)

            operation = await op_repo.get_by_id(operation_id)
            if not operation or operation.status == OperationStatus.CANCELLED.value:
                logger.info("BRD parse cancelled during work: %s", operation_id)
                return

            if brd is None:
                await op_repo.mark_failed(operation, "BRD not found for operation")
            elif brd.status == "parse_failed":
                await op_repo.mark_failed(
                    operation, brd.error_message or "BRD parse failed"
                )
            else:
                await op_repo.mark_succeeded(operation)

            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.exception("Background BRD parse failed for operation_id=%s", operation_id)
            try:
                operation = await op_repo.get_by_id(operation_id)
                if operation and operation.status != OperationStatus.CANCELLED.value:
                    await op_repo.mark_failed(operation, str(exc))
                    await session.commit()
            except Exception:
                await session.rollback()
                logger.exception(
                    "Failed to mark operation as failed: %s", operation_id
                )
