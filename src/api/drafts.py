"""/drafts — CRUD + HITL workflow (save/approve/reject/push)."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.pipeline.push import push_draft
from src.schemas.api import DraftListResponse, DraftUpdate
from src.schemas.article import ArticleRecord, HealthScore
from src.storage.db import get_session
from src.storage.models import Article

router = APIRouter()


def _to_record(a: Article) -> ArticleRecord:
    score = None
    if a.score_overall is not None:
        score = HealthScore(
            accuracy=float(a.score_accuracy or 0),
            recency=float(a.score_recency or 0),
            coverage=float(a.score_coverage or 0),
            overall=float(a.score_overall or 0),
        )
    return ArticleRecord(
        id=a.id,
        source_ticket_id=a.source_ticket_id,
        itsm_provider=a.itsm_provider,
        itsm_kb_id=a.itsm_kb_id,
        title=a.title,
        summary=a.summary,
        problem=a.problem,
        steps_md=a.steps_md,
        tags=a.tags or [],
        category=a.category,
        status=a.status,
        source=a.source,
        model=a.model,
        prompt_version=a.prompt_version,
        confidence=float(a.confidence) if a.confidence is not None else None,
        score=score,
        reviewer=a.reviewer,
        review_notes=a.review_notes,
        reviewed_at=a.reviewed_at,
        pushed_at=a.pushed_at,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


async def _get_or_404(db: AsyncSession, draft_id: UUID) -> Article:
    a = (await db.execute(select(Article).where(Article.id == draft_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="draft not found")
    return a


@router.get("/drafts", response_model=DraftListResponse)
async def list_drafts(
    status: str | None = None,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
) -> DraftListResponse:
    stmt = select(Article)
    if status:
        stmt = stmt.where(Article.status == status.upper())
    if source:
        stmt = stmt.where(Article.source == source)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(Article.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return DraftListResponse(items=[_to_record(a) for a in rows], total=total)


@router.get("/drafts/{draft_id}", response_model=ArticleRecord)
async def get_draft(draft_id: UUID, db: AsyncSession = Depends(get_session)) -> ArticleRecord:
    return _to_record(await _get_or_404(db, draft_id))


@router.get("/drafts/{draft_id}/coverage")
async def draft_coverage(
    draft_id: UUID, db: AsyncSession = Depends(get_session)
) -> dict:
    """All tickets connected to this article — the master ticket that spawned
    the draft, plus every subsequent ticket the dedup step marked COVERED by
    it. This is how "one KB serves many tickets" surfaces in the UI.
    """
    from src.storage.models import ProcessedTicket

    article = await _get_or_404(db, draft_id)

    # The "primary" ticket — the one whose resolution notes birthed the draft.
    primary = None
    if article.source_ticket_id:
        primary_row = (
            await db.execute(
                select(ProcessedTicket).where(
                    ProcessedTicket.itsm_ticket_id == article.source_ticket_id
                )
            )
        ).scalar_one_or_none()
        if primary_row:
            primary = {
                "itsm_ticket_id": primary_row.itsm_ticket_id,
                "itsm_provider": primary_row.itsm_provider,
                "title": primary_row.title,
                "topic": primary_row.topic,
                "resolved_at": primary_row.resolved_at,
                "relation": "primary_source",
            }

    # "Covered" tickets — every ticket the dedup matched against this article.
    # Exclude the master's own ticket id defensively: in rare race conditions
    # (two overlapping poll cycles for the same ticket) the master row can end
    # up with matched_article_id pointing at its own freshly-drafted article,
    # which would otherwise render it twice in the UI.
    covered_rows = (
        await db.execute(
            select(ProcessedTicket)
            .where(ProcessedTicket.matched_article_id == article.id)
            .order_by(ProcessedTicket.matched_score.desc().nulls_last())
        )
    ).scalars().all()
    covered = [
        {
            "itsm_ticket_id": r.itsm_ticket_id,
            "itsm_provider": r.itsm_provider,
            "title": r.title,
            "topic": r.topic,
            "resolved_at": r.resolved_at,
            "matched_score": float(r.matched_score) if r.matched_score is not None else None,
            "relation": "covered_by",
        }
        for r in covered_rows
        if r.itsm_ticket_id != article.source_ticket_id
    ]

    return {
        "article_id": str(article.id),
        "title": article.title,
        "status": article.status,
        "primary_ticket": primary,
        "covered_tickets": covered,
        "total_tickets": (1 if primary else 0) + len(covered),
    }


@router.patch("/drafts/{draft_id}", response_model=ArticleRecord)
async def update_draft(
    draft_id: UUID,
    update: DraftUpdate,
    db: AsyncSession = Depends(get_session),
) -> ArticleRecord:
    a = await _get_or_404(db, draft_id)
    if a.status in ("PUSHED", "REJECTED"):
        raise HTTPException(status_code=400, detail=f"cannot edit draft in status {a.status}")
    data = update.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(a, k, v)
    # Any edit transitions DRAFT → EDITED so reviewers can see it changed.
    if data and a.status == "DRAFT":
        a.status = "EDITED"
    await db.commit()
    await db.refresh(a)
    return _to_record(a)


@router.post("/drafts/{draft_id}/approve", response_model=ArticleRecord)
async def approve_draft(
    draft_id: UUID,
    reviewer: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> ArticleRecord:
    a = await _get_or_404(db, draft_id)
    if a.status not in ("DRAFT", "EDITED"):
        raise HTTPException(status_code=400, detail=f"cannot approve from status {a.status}")
    a.status = "APPROVED"
    a.reviewer = reviewer
    a.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(a)
    return _to_record(a)


@router.post("/drafts/{draft_id}/reject", response_model=ArticleRecord)
async def reject_draft(
    draft_id: UUID,
    reviewer: str | None = None,
    reason: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> ArticleRecord:
    a = await _get_or_404(db, draft_id)
    if a.status in ("PUSHED",):
        raise HTTPException(status_code=400, detail=f"cannot reject from status {a.status}")
    a.status = "REJECTED"
    a.reviewer = reviewer
    a.review_notes = reason or a.review_notes
    a.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(a)
    return _to_record(a)


@router.post("/drafts/{draft_id}/push")
async def push_to_itsm(
    draft_id: UUID,
    reviewer: str | None = None,
    db: AsyncSession = Depends(get_session),
) -> dict:
    try:
        return await push_draft(db, draft_id, reviewer=reviewer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
