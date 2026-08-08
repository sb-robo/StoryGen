"""Seed a local demo user + sample parsed BRD with a tiny approved pipeline.

Usage (from repo root):

    PYTHONPATH=backend uv run python backend/scripts/seed_demo.py

Login: demo@storygen.local / demo12345
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
SAMPLE_BRD = BACKEND_DIR / "samples" / "sample_brd.md"

# Ensure `app` imports resolve when run as a script.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.models.brd_document import BrdDocument, BrdStatus  # noqa: E402
from app.db.models.brd_feature import BrdFeature, FeatureStatus  # noqa: E402
from app.db.models.brd_story import BrdStory, PointsStatus, StoryReviewStatus  # noqa: E402
from app.db.models.brd_sub_feature import BrdSubFeature, ReviewStatus  # noqa: E402
from app.db.models.brd_test_case import BrdTestCase, TestCaseStatus, TestCaseType  # noqa: E402
from app.db.models.user import User  # noqa: E402
from app.db.session import async_session_local  # noqa: E402
from app.repositories.story_repository import encode_acceptance_criteria  # noqa: E402
from app.services.brd.storage_service import BrdStorageService  # noqa: E402
from app.utils.password_handler import hash_password  # noqa: E402

DEMO_EMAIL = "demo@storygen.local"
DEMO_PASSWORD = "demo12345"
DEMO_NAME = "Demo User"
BRD_NAME = "Sample Payments BRD"


async def _get_or_create_demo_user(db) -> User:
    result = await db.execute(select(User).where(User.email == DEMO_EMAIL))
    user = result.scalar_one_or_none()
    if user:
        return user

    # First user becomes admin if none exist yet — fine for local demos.
    count = (await db.execute(select(User.id))).scalars().first()
    user = User(
        name=DEMO_NAME,
        email=DEMO_EMAIL,
        hashed_password=hash_password(DEMO_PASSWORD),
        is_active=True,
        is_admin=count is None,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _seed_brd(db, user: User) -> BrdDocument:
    existing = await db.execute(
        select(BrdDocument).where(
            BrdDocument.user_id == user.id,
            BrdDocument.name == BRD_NAME,
            BrdDocument.deleted_at.is_(None),
        )
    )
    brd = existing.scalar_one_or_none()
    if brd:
        return brd

    if not SAMPLE_BRD.exists():
        raise FileNotFoundError(f"Missing sample BRD at {SAMPLE_BRD}")

    markdown = SAMPLE_BRD.read_text(encoding="utf-8")
    storage = BrdStorageService()

    brd = BrdDocument(
        user_id=user.id,
        name=BRD_NAME,
        original_filename="sample_brd.md",
        stored_filename="original.md",
        mime_type="text/markdown",
        file_extension=".md",
        file_size_bytes=len(markdown.encode("utf-8")),
        storage_path="",
        original_path="",
        status=BrdStatus.PARSED.value,
        page_count=1,
        table_count=0,
        image_count=0,
        pipeline_settings={
            "domain_context": "B2B payments portal for merchants",
            "feature_count": "fewer",
            "story_style": "classic",
            "pointing_scale": "fibonacci",
            "test_depth": "standard",
            "export_project_key": "PAY",
            "export_epic_prefix": "Payments",
        },
    )
    db.add(brd)
    await db.flush()
    await db.refresh(brd)

    brd_dir = await storage.ensure_brd_dir(user.id, brd.id)
    brd.storage_path = str(brd_dir)
    original_path = brd_dir / "original.md"
    parsed_path = brd_dir / "parsed.md"
    original_path.write_text(markdown, encoding="utf-8")
    parsed_path.write_text(markdown, encoding="utf-8")
    brd.original_path = str(original_path)
    brd.parsed_text_path = str(parsed_path)
    await db.flush()

    feature = BrdFeature(
        brd_id=brd.id,
        user_id=user.id,
        title="Authentication",
        description="Email/password sign-in with clear failure messaging and session expiry.",
        confidence=0.9,
        rationale="Seeded demo feature from sample BRD auth section.",
        source_excerpt="## 2. Authentication",
        status=FeatureStatus.APPROVED.value,
        sort_order=0,
    )
    db.add(feature)
    await db.flush()

    sub = BrdSubFeature(
        feature_id=feature.id,
        user_id=user.id,
        title="Merchant login",
        description="Allow merchants to authenticate with email and password.",
        confidence=0.88,
        rationale="Seeded demo sub-feature.",
        source_excerpt="Merchants must sign in with email and password.",
        status=ReviewStatus.APPROVED.value,
        sort_order=0,
    )
    db.add(sub)
    await db.flush()

    story = BrdStory(
        sub_feature_id=sub.id,
        user_id=user.id,
        title="As a merchant, I want to sign in so that I can access the portal",
        description=(
            "As a merchant, I want to sign in with email and password, "
            "so that I can access my payments portal securely."
        ),
        acceptance_criteria=encode_acceptance_criteria(
            [
                "Valid credentials open the dashboard",
                "Invalid credentials show an error and do not create a session",
            ]
        ),
        confidence=0.9,
        rationale="Seeded demo story.",
        source_excerpt="Merchants must sign in with email and password.",
        status=StoryReviewStatus.APPROVED.value,
        story_points=3,
        points_rationale="Straightforward auth flow.",
        points_status=PointsStatus.APPROVED.value,
        sort_order=0,
    )
    db.add(story)
    await db.flush()

    db.add(
        BrdTestCase(
            story_id=story.id,
            user_id=user.id,
            title="Happy path login",
            steps="1. Open login\n2. Enter valid email/password\n3. Submit",
            expected_result="User lands on the dashboard",
            test_type=TestCaseType.HAPPY_PATH.value,
            confidence=0.9,
            rationale="Seeded demo test.",
            status=TestCaseStatus.APPROVED.value,
            sort_order=0,
        )
    )
    db.add(
        BrdTestCase(
            story_id=story.id,
            user_id=user.id,
            title="Invalid credentials",
            steps="1. Open login\n2. Enter wrong password\n3. Submit",
            expected_result="Error is shown and no session is created",
            test_type=TestCaseType.NEGATIVE.value,
            confidence=0.9,
            rationale="Seeded demo test.",
            status=TestCaseStatus.APPROVED.value,
            sort_order=1,
        )
    )
    # One pending item so the review queue isn't empty on first open.
    db.add(
        BrdFeature(
            brd_id=brd.id,
            user_id=user.id,
            title="Settlements overview",
            description="List settlements with date, amount, and status.",
            confidence=0.75,
            rationale="Seeded pending feature for review practice.",
            source_excerpt="## 4. Settlements",
            status=FeatureStatus.PENDING_REVIEW.value,
            sort_order=1,
        )
    )
    await db.flush()
    return brd


async def main() -> None:
    async with async_session_local() as db:
        user = await _get_or_create_demo_user(db)
        brd = await _seed_brd(db, user)
        await db.commit()

    print("Demo seed complete.")
    print(f"  Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"  BRD:   {brd.name} (id={brd.id})")
    print(f"  Sample file: {SAMPLE_BRD}")
    print("Open the app, sign in, and open the Sample Payments BRD.")


if __name__ == "__main__":
    asyncio.run(main())
