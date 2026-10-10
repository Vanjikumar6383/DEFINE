from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.db.database import get_db
from app.models.models import Session, User, TranscriptSegment, Insight, ActionItem, SessionSummary, MeetingSemanticMemory, AttendeeVoiceProfile
from app.schemas.schemas import (
    TranscriptSubmit, TranscriptSegmentOut,
    InsightOut, InsightFeedback,
    ActionItemCreate, ActionItemUpdate, ActionItemOut,
    SummaryOut, SummaryUpdate,
    QuestionAnswerRequest, QuestionAnswerResponse,
    SemanticMemoryOut, SemanticSearchRequest, SemanticSearchResponse, SemanticSearchResultItem,
    VectorizeSessionResponse, MultiSpeakerUtteranceSubmit
)
from app.security.auth import get_current_user
from app.services.providers.ai_adapter import generate_insights, generate_summary, generate_easy_answer
from app.services.vector_db_service import VectorDatabaseService

router = APIRouter(prefix="/api/v1/sessions", tags=["copilot"])


async def _check_session_access(session: Session, user: User, db: AsyncSession):
    if session.owner_id == user.id:
        return True
    from app.models.models import SessionParticipant
    res = await db.execute(
        select(SessionParticipant).where(
            SessionParticipant.session_id == session.id,
            SessionParticipant.user_id == user.id
        )
    )
    if res.scalar_one_or_none():
        return True
    raise HTTPException(status_code=403, detail="Access denied")


async def _get_active_session(session_id: str, user: User, db: AsyncSession) -> Session:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "deleted":
        raise HTTPException(status_code=410, detail="Session has been deleted")
    await _check_session_access(session, user, db)
    return session


# ──────────────────────────── Transcript ────────────────────────────

@router.post("/{session_id}/transcript", response_model=TranscriptSegmentOut, status_code=201)
async def submit_transcript(
    session_id: str,
    payload: TranscriptSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_active_session(session_id, current_user, db)
    seg = TranscriptSegment(
        session_id=session_id,
        speaker_label=payload.speaker_label,
        text=payload.text,
        source_type=payload.source_type,
        timestamp_start=payload.timestamp_start,
        timestamp_end=payload.timestamp_end,
    )
    db.add(seg)
    await db.commit()
    await db.refresh(seg)

    easy_answer_data = None
    lower = payload.text.strip().lower()
    tamil_q_markers = ["என்ன", "எப்படி", "எப்போது", "எங்கே", "ஏன்", "முடியுமா", "உள்ளதா", "எவ்வளவு", "யார்", "யாருக்கு", "எதற்கு", "தெரியுமா", "ஆகுமா", "வருமா", "இருக்கிறதா", "இருக்கா", "விலை", "கட்டணம்"]
    malayalam_q_markers = ["എന്ത്", "എങ്ങനെ", "എപ്പോൾ", "എവിടെ", "എന്തുകൊണ്ട്", "കഴിയുമോ", "ഉണ്ടോ", "എത്ര", "ആര്", "എന്താണ്", "പറയാമോ", "സാധിക്കുമോ", "ആണോ", "ഉണ്ടാകുമോ", "വില"]
    english_q_markers = ["what", "how", "why", "when", "where", "can we", "can you", "could we", "could you", "is there", "are there", "will", "do you", "does", "would", "pricing", "cost", "budget"]

    is_question = (
        "?" in payload.text
        or any(lower.startswith(w) for w in ["what", "how", "why", "when", "where", "can we", "could we", "is there", "will", "do you", "does"])
        or any(w in lower for w in english_q_markers)
        or any(w in payload.text for w in tamil_q_markers)
        or any(w in payload.text for w in malayalam_q_markers)
    )
    if is_question:
        easy_answer_data = await generate_easy_answer(
            question=payload.text,
            objective=session.objective,
            session_mode=session.mode,
            speaker_label=payload.speaker_label or "Attender"
        )
        qa_insight = Insight(
            session_id=session_id,
            type="response_suggestion",
            content=f"Q ({payload.speaker_label or 'Attender'}): {payload.text}\n→ Easy Answer: {easy_answer_data['easy_answer']}",
            confidence_label=easy_answer_data.get("confidence_label", "high"),
            objective_alignment=easy_answer_data.get("objective_alignment", "supports_goal"),
            evidence_refs={
                "question": payload.text,
                "speaker": payload.speaker_label or "Attender",
                "easy_answer": easy_answer_data["easy_answer"],
                "talking_points": easy_answer_data.get("talking_points", []),
            }
        )
        db.add(qa_insight)
        await db.commit()

    return TranscriptSegmentOut(
        id=seg.id,
        speaker_label=seg.speaker_label,
        text=seg.text,
        timestamp_start=seg.timestamp_start,
        timestamp_end=seg.timestamp_end,
        source_type=seg.source_type,
        created_at=seg.created_at,
        easy_answer=easy_answer_data["easy_answer"] if easy_answer_data else None,
        talking_points=easy_answer_data.get("talking_points") if easy_answer_data else None,
    )


@router.post("/{session_id}/qa/answer", response_model=QuestionAnswerResponse)
async def ask_easy_answer(
    session_id: str,
    payload: QuestionAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_active_session(session_id, current_user, db)
    ans = await generate_easy_answer(
        question=payload.question,
        objective=session.objective,
        session_mode=session.mode,
        speaker_label=payload.speaker_label or "Attender"
    )
    qa_insight = Insight(
        session_id=session_id,
        type="response_suggestion",
        content=f"Q ({payload.speaker_label or 'Attender'}): {payload.question}\n→ Easy Answer: {ans['easy_answer']}",
        confidence_label=ans.get("confidence_label", "high"),
        objective_alignment=ans.get("objective_alignment", "supports_goal"),
        evidence_refs={
            "question": payload.question,
            "speaker": payload.speaker_label or "Attender",
            "easy_answer": ans["easy_answer"],
            "talking_points": ans.get("talking_points", []),
        }
    )
    db.add(qa_insight)
    await db.commit()
    await db.refresh(qa_insight)
    return QuestionAnswerResponse(
        id=qa_insight.id,
        question=payload.question,
        speaker_label=payload.speaker_label or "Attender",
        easy_answer=ans["easy_answer"],
        talking_points=ans.get("talking_points", []),
        confidence_label=ans.get("confidence_label", "high"),
        objective_alignment=ans.get("objective_alignment", "supports_goal"),
        created_at=qa_insight.created_at,
    )


@router.get("/{session_id}/transcript", response_model=list[TranscriptSegmentOut])
async def get_transcript(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_active_session(session_id, current_user, db)
    result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
        .order_by(TranscriptSegment.created_at)
    )
    return result.scalars().all()


# ──────────────────────────── Insights ────────────────────────────

@router.post("/{session_id}/insights", response_model=list[InsightOut], status_code=201)
async def generate_session_insights(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_active_session(session_id, current_user, db)

    # Fetch recent transcript (last 3000 chars)
    result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
        .order_by(desc(TranscriptSegment.created_at))
        .limit(30)
    )
    segments = result.scalars().all()
    segments.reverse()
    transcript_window = "\n".join(
        f"[{s.speaker_label or 'Speaker'}]: {s.text}" for s in segments
    )[-3000:]

    raw_insights = await generate_insights(
        transcript_window=transcript_window,
        objective=session.objective,
        session_mode=session.mode,
    )

    created = []
    for raw in raw_insights:
        insight = Insight(
            session_id=session_id,
            type=raw["type"],
            content=raw["content"],
            confidence_label=raw.get("confidence_label", "medium"),
            objective_alignment=raw.get("objective_alignment"),
            evidence_refs=raw.get("evidence", []),
        )
        db.add(insight)
        created.append(insight)

    await db.commit()
    for ins in created:
        await db.refresh(ins)
    return created


@router.get("/{session_id}/insights", response_model=list[InsightOut])
async def get_insights(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_active_session(session_id, current_user, db)
    result = await db.execute(
        select(Insight)
        .where(Insight.session_id == session_id)
        .order_by(Insight.created_at)
    )
    return result.scalars().all()


@router.post("/{session_id}/insights/{insight_id}/feedback", status_code=204)
async def feedback_insight(
    session_id: str,
    insight_id: str,
    payload: InsightFeedback,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_active_session(session_id, current_user, db)
    result = await db.execute(
        select(Insight).where(Insight.id == insight_id, Insight.session_id == session_id)
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    insight.user_rating = payload.rating
    if payload.correction:
        insight.content = payload.correction
        insight.user_edited = True
    await db.commit()


# ──────────────────────────── Action Items ────────────────────────────

@router.post("/{session_id}/actions", response_model=ActionItemOut, status_code=201)
async def create_action_item(
    session_id: str,
    payload: ActionItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_active_session(session_id, current_user, db)
    action = ActionItem(
        session_id=session_id,
        description=payload.description,
        owner=payload.owner,
        due_date=payload.due_date,
        priority=payload.priority or "medium",
        evidence_ref=payload.evidence_ref,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


@router.get("/{session_id}/actions", response_model=list[ActionItemOut])
async def get_actions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_active_session(session_id, current_user, db)
    result = await db.execute(
        select(ActionItem)
        .where(ActionItem.session_id == session_id)
        .order_by(ActionItem.created_at)
    )
    return result.scalars().all()


@router.patch("/{session_id}/actions/{action_id}", response_model=ActionItemOut)
async def update_action(
    session_id: str,
    action_id: str,
    payload: ActionItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_active_session(session_id, current_user, db)
    result = await db.execute(
        select(ActionItem).where(ActionItem.id == action_id, ActionItem.session_id == session_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(action, field, value)
    await db.commit()
    await db.refresh(action)
    return action


@router.delete("/{session_id}/actions/{action_id}", status_code=204)
async def delete_action(
    session_id: str,
    action_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_active_session(session_id, current_user, db)
    result = await db.execute(
        select(ActionItem).where(ActionItem.id == action_id, ActionItem.session_id == session_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")
    await db.delete(action)
    await db.commit()


# ──────────────────────────── Summary ────────────────────────────

@router.post("/{session_id}/summary", response_model=SummaryOut, status_code=201)
async def generate_session_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await _get_active_session(session_id, current_user, db)

    # Gather full transcript
    t_result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
        .order_by(TranscriptSegment.created_at)
    )
    segments = t_result.scalars().all()
    full_transcript = "\n".join(
        f"[{s.speaker_label or 'Speaker'}]: {s.text}" for s in segments
    )

    # Gather insights
    i_result = await db.execute(
        select(Insight).where(Insight.session_id == session_id).order_by(Insight.created_at)
    )
    insights = [{"type": i.type, "content": i.content} for i in i_result.scalars().all()]

    # Gather action items
    a_result = await db.execute(
        select(ActionItem).where(ActionItem.session_id == session_id)
    )
    actions = [{"description": a.description, "owner": a.owner} for a in a_result.scalars().all()]

    summary_data = await generate_summary(
        transcript=full_transcript,
        objective=session.objective,
        insights=insights,
        action_items=actions,
    )

    # Upsert summary
    existing = await db.execute(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    )
    summary = existing.scalar_one_or_none()
    imp_pts = summary_data.get("important_points") or summary_data.get("key_points") or []
    exec_sum = summary_data.get("executive_summary") or ""
    if summary:
        summary.summary_text = summary_data.get("summary_text", "")
        summary.executive_summary = exec_sum
        summary.key_points = imp_pts
        summary.important_points = imp_pts
        summary.key_decisions = summary_data.get("key_decisions", [])
        summary.unresolved_questions = summary_data.get("unresolved_questions", [])
        summary.follow_up_draft = summary_data.get("follow_up_draft", "")
    else:
        summary = SessionSummary(
            session_id=session_id,
            summary_text=summary_data.get("summary_text", ""),
            executive_summary=exec_sum,
            key_points=imp_pts,
            important_points=imp_pts,
            key_decisions=summary_data.get("key_decisions", []),
            unresolved_questions=summary_data.get("unresolved_questions", []),
            follow_up_draft=summary_data.get("follow_up_draft", ""),
        )
        db.add(summary)

    await db.commit()
    await db.refresh(summary)
    return summary


@router.get("/{session_id}/summary", response_model=SummaryOut)
async def get_summary(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_active_session(session_id, current_user, db)
    result = await db.execute(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    )
    summary = result.scalar_one_or_none()
    if not summary:
        raise HTTPException(status_code=404, detail="No summary yet. Generate one first.")
    return summary


@router.patch("/{session_id}/summary", response_model=SummaryOut)
async def update_summary(
    session_id: str,
    payload: SummaryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_active_session(session_id, current_user, db)
    result = await db.execute(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    )
    summary = result.scalar_one_or_none()
    if not summary:
        raise HTTPException(status_code=404, detail="No summary to update")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(summary, field, value)
    await db.commit()
    await db.refresh(summary)
    return summary


# ──────────────────────────── Vector Database & Semantic Memory ────────

@router.post("/semantic-search", response_model=SemanticSearchResponse)
async def semantic_search_meetings(
    payload: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic Vector Search across previous meetings.
    Finds semantically related key points, decisions, commitments, Q&A, and speaker quotes
    using continuous-space vector embeddings and cosine similarity.
    """
    results = await VectorDatabaseService.semantic_search(
        db=db,
        user_id=current_user.id,
        query=payload.query,
        top_k=payload.top_k or 6,
        category=payload.category,
        speaker_filter=payload.speaker_filter,
        exclude_session_id=payload.exclude_session_id,
    )
    return SemanticSearchResponse(
        query=payload.query,
        results_count=len(results),
        results=[
            SemanticSearchResultItem(
                id=r["id"],
                session_id=r["session_id"],
                session_title=r["session_title"],
                session_date=r["session_date"],
                category=r["category"],
                speaker_label=r["speaker_label"],
                speaker_role=r["speaker_role"],
                content=r["content"],
                semantic_context=r["semantic_context"],
                semantic_tags=r["semantic_tags"],
                similarity=r["similarity"],
                related_memory_ids=r["related_memory_ids"],
                similarity_graph=r["similarity_graph"],
            )
            for r in results
        ],
    )


@router.post("/{session_id}/vectorize", response_model=VectorizeSessionResponse)
async def vectorize_session_memories(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Extracts all key points, decisions, actions, Q&As, and speaker transcripts from a session,
    generates dense vector embeddings, and stores them in the vector database with semantic links.
    """
    session = await _get_active_session(session_id, current_user, db)
    result = await VectorDatabaseService.vectorize_entire_session(
        db=db,
        session_id=session.id,
        user_id=current_user.id,
    )
    return VectorizeSessionResponse(
        session_id=session.id,
        indexed_count=result["indexed_count"],
        status=result["status"],
    )


@router.get("/{session_id}/semantic-memory", response_model=list[SemanticMemoryOut])
async def get_session_semantic_memory(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetches all vector memory records and their semantic relational links for a specific meeting.
    """
    await _get_active_session(session_id, current_user, db)
    stmt = select(MeetingSemanticMemory).where(
        MeetingSemanticMemory.session_id == session_id
    ).order_by(MeetingSemanticMemory.created_at.desc())
    result = await db.execute(stmt)
    memories = result.scalars().all()
    return memories


@router.post("/{session_id}/speaker-utterance", response_model=TranscriptSegmentOut, status_code=201)
async def ingest_speaker_utterance(
    session_id: str,
    payload: MultiSpeakerUtteranceSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ingests live spoken transcripts with precise speaker attribution (both for the host/user
    and for any on-screen attendee speaking in the meeting).
    Stores speaker labels, roles, and automatically indexes key statements into the Vector Database.
    """
    session = await _get_active_session(session_id, current_user, db)
    
    seg = TranscriptSegment(
        session_id=session_id,
        speaker_label=payload.speaker_label,
        speaker_role=payload.speaker_role or "screen_attender",
        audio_channel=payload.audio_channel or "screen_audio",
        text=payload.text,
        source_type=payload.source_type or "screen_attender",
        timestamp_start=payload.timestamp_start,
        timestamp_end=payload.timestamp_end,
        confidence=payload.confidence or 0.95,
    )
    db.add(seg)
    await db.commit()
    await db.refresh(seg)

    # Check for questions to surface instant Easy Answer
    easy_answer_data = None
    lower = payload.text.strip().lower()
    is_question = (
        "?" in payload.text
        or any(lower.startswith(w) for w in ["what", "how", "why", "when", "where", "can we", "could we", "is there", "will", "do you", "does", "would"])
        or any(w in lower for w in ["pricing", "cost", "sla", "budget", "compliance", "timeline", "architecture", "security", "failover"])
    )

    if is_question:
        easy_answer_data = await generate_easy_answer(
            question=payload.text,
            objective=session.objective,
            session_mode=session.mode,
            speaker_label=payload.speaker_label or "Attender"
        )
        qa_insight = Insight(
            session_id=session_id,
            type="response_suggestion",
            content=f"Q ({payload.speaker_label}): {payload.text}\n→ Easy Answer: {easy_answer_data['easy_answer']}",
            confidence_label=easy_answer_data.get("confidence_label", "high"),
            objective_alignment=easy_answer_data.get("objective_alignment", "supports_goal"),
            evidence_refs={
                "question": payload.text,
                "speaker": payload.speaker_label,
                "easy_answer": easy_answer_data["easy_answer"],
                "talking_points": easy_answer_data.get("talking_points", []),
            }
        )
        db.add(qa_insight)
        await db.commit()

        # Vectorize this Q&A into the vector DB immediately
        await VectorDatabaseService.index_semantic_memory(
            db=db,
            session_id=session_id,
            user_id=current_user.id,
            category="qa_pair",
            speaker_label=payload.speaker_label,
            speaker_role=payload.speaker_role or "screen_attender",
            content=f"Question: {payload.text}\nAnswer: {easy_answer_data['easy_answer']}",
            semantic_context=f"Meeting: {session.title} | Objective: {session.objective or ''}",
            semantic_tags=["qa", payload.speaker_label, "live_attender"]
        )

    # If it is a substantive statement (> 30 chars), index it into Vector DB
    elif len(payload.text.strip()) > 30:
        await VectorDatabaseService.index_semantic_memory(
            db=db,
            session_id=session_id,
            user_id=current_user.id,
            category="speaker_statement",
            speaker_label=payload.speaker_label,
            speaker_role=payload.speaker_role or "screen_attender",
            content=payload.text,
            semantic_context=f"Meeting: {session.title} | Speaker: {payload.speaker_label}",
            semantic_tags=["utterance", payload.speaker_label, payload.speaker_role or "screen_attender"]
        )

    return TranscriptSegmentOut(
        id=seg.id,
        speaker_label=seg.speaker_label,
        text=seg.text,
        timestamp_start=seg.timestamp_start,
        timestamp_end=seg.timestamp_end,
        source_type=seg.source_type,
        created_at=seg.created_at,
        easy_answer=easy_answer_data["easy_answer"] if easy_answer_data else None,
        talking_points=easy_answer_data.get("talking_points") if easy_answer_data else None,
    )

