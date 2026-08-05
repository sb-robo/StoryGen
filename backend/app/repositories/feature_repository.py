import json

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.brd_feature import BrdFeature, FeatureStatus


class FeatureRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, feature: BrdFeature) -> BrdFeature:
        self.db.add(feature)
        await self.db.flush()
        await self.db.refresh(feature)
        return feature

    async def create_many(self, features: list[BrdFeature]) -> list[BrdFeature]:
        for feature in features:
            self.db.add(feature)
        await self.db.flush()
        for feature in features:
            await self.db.refresh(feature)
        return features

    async def get_by_id(self, feature_id: int) -> BrdFeature | None:
        result = await self.db.execute(
            select(BrdFeature).where(BrdFeature.id == feature_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self, feature_id: int, user_id: int
    ) -> BrdFeature | None:
        result = await self.db.execute(
            select(BrdFeature).where(
                BrdFeature.id == feature_id,
                BrdFeature.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    def _filtered_query(
        self,
        user_id: int,
        brd_id: int,
        *,
        status: str | None = None,
    ) -> Select:
        query = select(BrdFeature).where(
            BrdFeature.user_id == user_id,
            BrdFeature.brd_id == brd_id,
        )
        if status:
            query = query.where(BrdFeature.status == status)
        return query

    async def list_for_brd(
        self,
        user_id: int,
        brd_id: int,
        *,
        status: str | None = None,
    ) -> list[BrdFeature]:
        query = self._filtered_query(user_id, brd_id, status=status)
        result = await self.db.execute(
            query.order_by(BrdFeature.sort_order.asc(), BrdFeature.id.asc())
        )
        return list(result.scalars().all())

    async def count_for_brd(
        self,
        user_id: int,
        brd_id: int,
        *,
        status: str | None = None,
    ) -> int:
        base = self._filtered_query(user_id, brd_id, status=status)
        result = await self.db.execute(select(func.count()).select_from(base.subquery()))
        return result.scalar_one()

    async def delete_non_finalized_for_brd(self, brd_id: int) -> None:
        """Remove draft/pending_review features before a re-extraction run."""
        await self.db.execute(
            delete(BrdFeature).where(
                BrdFeature.brd_id == brd_id,
                BrdFeature.status.in_(
                    [FeatureStatus.DRAFT.value, FeatureStatus.PENDING_REVIEW.value]
                ),
            )
        )
        await self.db.flush()

    async def update(self, feature: BrdFeature) -> BrdFeature:
        self.db.add(feature)
        await self.db.flush()
        await self.db.refresh(feature)
        return feature


def encode_clarifying_questions(questions: list[str] | None) -> str | None:
    if not questions:
        return None
    return json.dumps(questions)


def decode_clarifying_questions(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def encode_clarifying_answers(
    answers: list[dict[str, str]] | None,
) -> str | None:
    if not answers:
        return None
    return json.dumps(answers)


def decode_clarifying_answers(raw: str | None) -> list[dict[str, str]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        result: list[dict[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if question and answer:
                result.append({"question": question, "answer": answer})
        return result
    except json.JSONDecodeError:
        return []


def format_clarifying_qa_for_prompt(
    questions: list[str],
    answers: list[dict[str, str]],
) -> str:
    if not questions:
        return "(none)"
    answer_map = {item["question"]: item["answer"] for item in answers}
    blocks: list[str] = []
    for question in questions:
        answer = answer_map.get(question, "").strip()
        if answer:
            blocks.append(f"Q: {question}\nA: {answer}")
        else:
            blocks.append(f"Q: {question}\nA: (not answered)")
    return "\n\n".join(blocks)
