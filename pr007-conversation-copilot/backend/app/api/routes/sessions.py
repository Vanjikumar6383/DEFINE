from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.database import get_db
from app.models.models import Session, User, AuditEvent
from app.schemas.schemas import SessionCreate, SessionUpdate, SessionOut
from app.security.auth import get_current_user
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])
settings = get_settings()


def _check_ownership(session: Session, user: User):
    if session.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")


async def _get_session(session_id: str, user: User, db: AsyncSession, require_owner: bool = False) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "deleted":
        raise HTTPException(status_code=410, detail="Session has been deleted")
    if require_owner:
        _check_ownership(session, user)
    return session


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    retention_until = datetime.now(timezone.utc) + timedelta(days=settings.SESSION_RETENTION_DAYS)
    session = Session(
        owner_id=current_user.id,
        title=payload.title,
        mode=payload.mode,
        objective=payload.objective,
        audience=payload.audience,
        desired_outcome=payload.desired_outcome,
        tone=payload.tone,
        constraints=payload.constraints,
        key_topics=payload.key_topics,
        audio_consent=payload.audio_consent,
        status="active",
        retention_until=retention_until,
    )
    db.add(session)
    audit = AuditEvent(actor_id=current_user.id, session_id=session.id, event_type="session_created")
    db.add(audit)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Session)
        .where(Session.owner_id == current_user.id, Session.status != "deleted")
        .order_by(desc(Session.created_at))
        .limit(100)
    )
    return result.scalars().all()


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_session(session_id, current_user, db, require_owner=True)


@router.patch("/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: str,
    payload: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_session(session_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(session, field, value)
    if payload.status == "ended" and not session.ended_at:
        session.ended_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import delete as sql_delete
    from app.models.models import TranscriptSegment, Insight, ActionItem, Decision, SessionSummary
    session = await _get_session(session_id, current_user, db)
    # Cascade-delete all child rows physically
    await db.execute(sql_delete(TranscriptSegment).where(TranscriptSegment.session_id == session_id))
    await db.execute(sql_delete(Insight).where(Insight.session_id == session_id))
    await db.execute(sql_delete(ActionItem).where(ActionItem.session_id == session_id))
    await db.execute(sql_delete(Decision).where(Decision.session_id == session_id))
    await db.execute(sql_delete(SessionSummary).where(SessionSummary.session_id == session_id))
    # Soft-delete the session record (preserves audit trail)
    session.status = "deleted"
    session.ended_at = datetime.now(timezone.utc)
    audit = AuditEvent(actor_id=current_user.id, session_id=session.id, event_type="session_deleted")
    db.add(audit)
    await db.commit()
