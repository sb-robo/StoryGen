"""Build prompt constraints for guided regenerate / critique."""

from __future__ import annotations


def format_existing_feature_constraints(
    approved: list[tuple[str, str]],
    *,
    edited_pending: list[tuple[str, str]] | None = None,
) -> str:
    """
    Format kept features so re-extraction avoids duplicates and respects edits.

    approved: (title, description) for approved features kept across regenerate.
    edited_pending: optional user-edited draft/pending items to treat as soft constraints
    before they are replaced.
    """
    blocks: list[str] = []
    if approved:
        lines = ["EXISTING APPROVED FEATURES (do not recreate; leave as covered):"]
        for title, description in approved:
            desc = (description or "").strip().replace("\n", " ")
            if len(desc) > 180:
                desc = desc[:177] + "..."
            lines.append(f"- {title.strip()}: {desc or '(no description)'}")
        blocks.append("\n".join(lines))

    if edited_pending:
        lines = [
            "USER-EDITED DRAFT FEATURES (soft constraints — prefer preserving intent "
            "if still valid; you may merge/rename if the BRD requires it):"
        ]
        for title, description in edited_pending:
            desc = (description or "").strip().replace("\n", " ")
            if len(desc) > 180:
                desc = desc[:177] + "..."
            lines.append(f"- {title.strip()}: {desc or '(no description)'}")
        blocks.append("\n".join(lines))

    if not blocks:
        return "(no existing feature constraints)"
    return "\n\n".join(blocks)
