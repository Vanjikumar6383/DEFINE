import io
import os
import re
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import RedirectResponse, PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.database import get_db
from app.models.models import Session, User, TranscriptSegment, Insight, ActionItem, SessionSummary, Decision, IntegrationConnection
from app.schemas.schemas import (
    IntegrationCardOut, IntegrationConnectRequest, IntegrationDisconnectResponse,
    TranscriptImportRequest, TranscriptImportResponse, FullAnalysisResponse,
    DecisionOut, DecisionCreate, DecisionUpdate,
    InsightOut, ActionItemOut, SummaryOut, SuggestionRegenerateRequest
)
from app.security.auth import get_current_user
from app.services.integrations.integration_manager import integration_manager
from app.services.providers.ai_adapter import analyze_conversation_full, regenerate_smart_suggestion

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["integrations"])


# ─────────────────────────────────────────────────────────────────────────────
# Integration Cards & Connection Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/integrations", response_model=list[IntegrationCardOut])
async def list_integrations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return honest connection states for Google Meet, Zoom, and Microsoft Teams."""
    cards = await integration_manager.get_all_cards(current_user.id, db)
    return cards


@router.post("/integrations/{provider}/connect", response_model=IntegrationCardOut)
async def connect_integration(
    provider: str,
    payload: IntegrationConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Connect an authorized integration or configure custom platform settings."""
    if provider not in integration_manager.providers:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' is not supported.")

    try:
        await integration_manager.connect_provider(
            provider_id=provider,
            user_id=current_user.id,
            payload=payload.model_dump(),
            db=db,
        )
        card = await integration_manager.get_card(provider, current_user.id, db)
        return card
    except Exception as exc:
        logger.error("Failed to connect %s: %s", provider, exc)
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/integrations/{provider}/auth-url")
async def get_provider_auth_url(
    provider: str,
    current_user: User = Depends(get_current_user),
):
    """Generate authorized OAuth URL with secure anti-CSRF state token."""
    if provider not in integration_manager.providers:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' is not supported.")
    service = integration_manager.providers[provider]
    if not service.is_configured():
        return {
            "provider": provider,
            "configured": False,
            "auth_url": None,
            "message": f"{service.name} credentials are not configured in environment.",
        }
    state = integration_manager.generate_oauth_state(current_user.id, provider)
    base_auth_url = service.get_auth_url()
    sep = "&" if "?" in (base_auth_url or "") else "?"
    full_url = f"{base_auth_url}{sep}state={state}"
    return {
        "provider": provider,
        "configured": True,
        "auth_url": full_url,
        "state": state,
    }


@router.get("/integrations/{provider}/callback")
async def integration_oauth_callback(
    provider: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth redirect callback from Google, Zoom, or Microsoft with CSRF state verification."""
    if error:
        return RedirectResponse(url=f"/integrations?status=error&provider={provider}&msg={error}")
    if not code:
        return RedirectResponse(url=f"/integrations?status=cancelled&provider={provider}")

    if state:
        user_id = integration_manager.verify_oauth_state(state, provider)
        if not user_id:
            logger.warning("Invalid or expired OAuth state parameter for provider %s", provider)
            return RedirectResponse(url=f"/integrations?status=error&provider={provider}&msg=invalid_oauth_state")

    # In production, code is exchanged for token using provider client secrets
    return RedirectResponse(url=f"/integrations?status=authorized&provider={provider}")


@router.post("/integrations/{provider}/disconnect", response_model=IntegrationDisconnectResponse)
async def disconnect_integration(
    provider: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect an integration connection."""
    if provider not in integration_manager.providers:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' is not supported.")

    removed = await integration_manager.disconnect_provider(provider, current_user.id, db)
    if not removed:
        raise HTTPException(status_code=404, detail="No active connection found to disconnect.")

    return IntegrationDisconnectResponse(
        success=True,
        provider=provider,
        message=f"Successfully disconnected from {provider.replace('_', ' ').title()}.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Transcript Validation & File Upload (Options A, B, C)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/transcripts/validate-url")
async def validate_meeting_url(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """Validate a meeting reference URL and explain real access capabilities."""
    url = payload.get("url", "")
    info = integration_manager.detect_and_validate_meeting_url(url)
    return info


@router.post("/transcripts/upload-file")
async def upload_transcript_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload and extract text from TXT, VTT, SRT, JSON, CSV, or PDF transcript files (<10MB)."""
    # 1. Enforce size limit (10 MB)
    max_bytes = 10 * 1024 * 1024
    content_bytes = await file.read()
    if len(content_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large. Transcripts must be under 10MB.")

    filename = (file.filename or "transcript.txt").lower()
    ext = os.path.splitext(filename)[1].lower()
    allowed_extensions = {".txt", ".vtt", ".srt", ".json", ".csv", ".pdf"}
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Transcripts must be TXT, VTT, SRT, JSON, CSV, or PDF."
        )
    extracted_text = ""

    try:
        # PDF Extraction
        if filename.endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content_bytes))
                pages = []
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t:
                        pages.append(t)
                extracted_text = "\n\n".join(pages).strip()
                if not extracted_text:
                    raise ValueError("No text could be extracted from PDF (file may be scanned/image-only).")
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"PDF extraction error: {str(e)}")

        # JSON Extraction (e.g. Zoom or Teams transcript payload)
        elif filename.endswith(".json"):
            try:
                data = json.loads(content_bytes.decode("utf-8", errors="replace"))
                if isinstance(data, list):
                    # List of segments
                    extracted_text = "\n".join(
                        f"[{item.get('speaker', 'Speaker')}]: {item.get('text', '')}"
                        if isinstance(item, dict) else str(item)
                        for item in data
                    )
                elif isinstance(data, dict):
                    if "segments" in data and isinstance(data["segments"], list):
                        extracted_text = "\n".join(
                            f"[{s.get('speaker', 'Speaker')}]: {s.get('text', '')}"
                            for s in data["segments"] if isinstance(s, dict)
                        )
                    else:
                        extracted_text = data.get("text", "") or data.get("transcript", "") or json.dumps(data, indent=2)
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"Invalid JSON transcript: {str(e)}")

        # VTT / SRT Subtitles Extraction
        elif filename.endswith(".vtt") or filename.endswith(".srt"):
            raw_str = content_bytes.decode("utf-8", errors="replace")
            # Strip timestamps like 00:01:20.000 --> 00:01:25.000 or numbering
            cleaned_lines = []
            for line in raw_str.splitlines():
                line = line.strip()
                if not line or line == "WEBVTT" or line.isdigit() or "-->" in line:
                    continue
                cleaned_lines.append(line)
            extracted_text = "\n".join(cleaned_lines)

        # Standard TXT / CSV Text
        else:
            extracted_text = content_bytes.decode("utf-8", errors="replace").strip()

        if not extracted_text:
            raise HTTPException(status_code=422, detail="The uploaded transcript file appears to be empty.")

        return {
            "filename": file.filename,
            "file_type": ext.lstrip("."),
            "char_count": len(extracted_text),
            "lines_count": len(extracted_text.splitlines()),
            "text": extracted_text,
            "content": extracted_text,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to process uploaded file: %s", exc)
        raise HTTPException(status_code=422, detail=f"Failed to parse file: {str(exc)}")


@router.post("/transcripts/import", response_model=TranscriptImportResponse, status_code=201)
async def import_transcript(
    payload: TranscriptImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import transcript content from Paste (Option A), File Upload (Option B), or Meeting URL Reference (Option C)."""
    raw_content = (payload.content or payload.raw_text or "").strip()

    # Determine platform
    platform = payload.platform_source or "manual_paste"
    if payload.import_method == "upload" or payload.source_type == "upload":
        platform = "file_upload"
    elif payload.meeting_url:
        detect = integration_manager.detect_and_validate_meeting_url(payload.meeting_url)
        if detect["is_valid"]:
            platform = detect["platform"]

    # If meeting URL was given with empty content, provide a starter notice
    if not raw_content and payload.meeting_url:
        raise HTTPException(
            status_code=400,
            detail="A meeting URL alone cannot fetch private meeting transcripts. Please paste the transcript text or upload a transcript file."
        )

    if not raw_content:
        raise HTTPException(status_code=400, detail="Transcript content cannot be empty.")

    # Find or create Session
    session = None
    if payload.session_id:
        res = await db.execute(select(Session).where(Session.id == payload.session_id, Session.owner_id == current_user.id))
        session = res.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Target session not found.")
    else:
        title = payload.meeting_title or payload.title or f"Meeting ({platform.replace('_', ' ').title()})"
        session = Session(
            owner_id=current_user.id,
            title=title,
            mode="group",
            objective=payload.objective or "Review discussion, capture decisions, and confirm deliverables",
            external_meeting_url=payload.meeting_url,
            platform_source=platform,
            status="active",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Parse raw content into segments
    lines = [l.strip() for l in raw_content.splitlines() if l.strip()]
    segments_to_add = []
    current_speaker = "Speaker"
    source_type = payload.source_type or payload.import_method or "paste"

    for idx, line in enumerate(lines):
        text = line
        speaker = current_speaker

        # Check speaker tag pattern like [Sarah Chen]: or Sarah Chen:
        speaker_match = re.match(r"^\[?([a-zA-Z0-9\s._-]+)\]?:\s*(.+)$", line)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            text = speaker_match.group(2).strip()
            current_speaker = speaker

        seg = TranscriptSegment(
            session_id=session.id,
            speaker_label=speaker,
            text=text,
            source_type=source_type,
            timestamp_start=float(idx * 5),
            timestamp_end=float(idx * 5 + 4),
        )
        segments_to_add.append(seg)

    db.add_all(segments_to_add)
    await db.commit()

    return TranscriptImportResponse(
        session_id=session.id,
        session_title=session.title,
        title=session.title,
        segments_imported=len(segments_to_add),
        segments_count=len(segments_to_add),
        char_count=len(raw_content),
        platform_source=platform,
        status="imported",
        message=f"Successfully imported {len(segments_to_add)} transcript segment(s) into NIMAD.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# NIMAD Full Conversation Analysis Pipeline
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/analyze", response_model=FullAnalysisResponse)
async def analyze_session_conversation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run full NIMAD AI Intelligence: Insights, Smart Replies, Decision Ledger, Action Items, Summary."""
    res = await db.execute(select(Session).where(Session.id == session_id, Session.owner_id == current_user.id))
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Retrieve all transcript segments
    t_res = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
        .order_by(TranscriptSegment.created_at.asc())
    )
    segments = t_res.scalars().all()

    if not segments:
        raise HTTPException(status_code=400, detail="Cannot analyze an empty session. Please import transcript text first.")

    full_transcript = "\n".join(f"[{s.speaker_label or 'Participant'}]: {s.text}" for s in segments)

    # Run AI Analysis (LLM with deterministic heuristic fallback)
    analysis = await analyze_conversation_full(
        transcript_text=full_transcript,
        objective=session.objective,
        session_mode=session.mode,
    )

    # 1. Clear old auto-generated insights/decisions/actions for this run if re-analyzing
    await db.execute(delete(Insight).where(Insight.session_id == session_id, Insight.user_edited == False))
    await db.execute(delete(Decision).where(Decision.session_id == session_id))
    await db.execute(delete(ActionItem).where(ActionItem.session_id == session_id))

    # 2. Save Insights
    saved_insights = []
    for ins in analysis.get("insights", []):
        row = Insight(
            session_id=session_id,
            type=ins.get("type", "key_point"),
            content=ins.get("content", ""),
            confidence_label=ins.get("confidence_label", "high"),
            objective_alignment=ins.get("objective_alignment", "supports_goal"),
            evidence_refs={"evidence": ins.get("evidence", [])},
        )
        db.add(row)
        saved_insights.append(row)

    # 3. Save Decisions
    saved_decisions = []
    for d in analysis.get("decisions", []):
        dec_row = Decision(
            session_id=session_id,
            decision_text=d.get("decision_text", ""),
            supporting_excerpt=d.get("supporting_excerpt"),
            status=(d.get("status") or "CONFIRMED").upper(),
            category=d.get("category", "General"),
        )
        db.add(dec_row)
        saved_decisions.append(dec_row)

    # 4. Save Action Items
    saved_actions = []
    for a in analysis.get("action_items", []):
        act_row = ActionItem(
            session_id=session_id,
            description=a.get("description", ""),
            owner=a.get("owner") or "Not specified",
            due_date=a.get("due_date") or "Not specified",
            priority=a.get("priority") or "medium",
            status=a.get("status") or "pending",
            evidence_ref=a.get("evidence_ref") or a.get("supporting_excerpt"),
        )
        db.add(act_row)
        saved_actions.append(act_row)

    # 5. Save Summary
    summary_data = analysis.get("summary", {})
    s_res = await db.execute(select(SessionSummary).where(SessionSummary.session_id == session_id))
    summary_row = s_res.scalar_one_or_none()
    if not summary_row:
        summary_row = SessionSummary(
            session_id=session_id,
            summary_text=summary_data.get("summary_text", "Meeting analysis complete."),
            key_decisions=summary_data.get("key_decisions", []),
            unresolved_questions=summary_data.get("unresolved_questions", []),
            follow_up_draft=summary_data.get("follow_up_draft", ""),
        )
        db.add(summary_row)
    else:
        summary_row.summary_text = summary_data.get("summary_text", summary_row.summary_text)
        summary_row.key_decisions = summary_data.get("key_decisions", summary_row.key_decisions)
        summary_row.unresolved_questions = summary_data.get("unresolved_questions", summary_row.unresolved_questions)
        summary_row.follow_up_draft = summary_data.get("follow_up_draft", summary_row.follow_up_draft)

    await db.commit()

    # Refresh items for response
    for i in saved_insights:
        await db.refresh(i)
    for d in saved_decisions:
        await db.refresh(d)
    for a in saved_actions:
        await db.refresh(a)
    await db.refresh(summary_row)

    sugg_list = analysis.get("smart_response_suggestions", []) or []
    formatted_suggestions = []
    for idx, s in enumerate(sugg_list):
        if isinstance(s, dict):
            s_text = s.get("suggestion_text") or s.get("suggestion") or s.get("text", "")
            s_why = s.get("why_relevant") or s.get("objective_relevance") or s.get("rationale") or s.get("context_rationale") or f"Directly advances objective: {session.objective or 'meeting outcomes'}"
            s_excerpt = s.get("supporting_excerpt") or s.get("excerpt")
            formatted_suggestions.append({
                "id": s.get("id") or f"sugg-{idx+1}",
                "category": s.get("category", "suggested_reply"),
                "type": s.get("type", "RECOMMENDED REPLY"),
                "title": s.get("title", f"Suggestion #{idx+1}"),
                "suggestion_text": s_text,
                "objective_relevance": s_why,
                "why_relevant": s_why,
                "context_rationale": s_why,
                "supporting_excerpt": s_excerpt,
                "is_dismissed": False,
                "user_edited": False,
            })

    return FullAnalysisResponse(
        session_id=session_id,
        session_title=session.title,
        objective=session.objective,
        platform_source=session.platform_source,
        insights=[
            InsightOut(
                id=i.id,
                type=i.type,
                content=i.content,
                confidence_label=i.confidence_label,
                objective_alignment=i.objective_alignment,
                evidence_refs=i.evidence_refs,
                user_edited=i.user_edited,
                user_rating=i.user_rating,
                created_at=i.created_at,
            )
            for i in saved_insights
        ],
        smart_response_suggestions=formatted_suggestions,
        suggestions=formatted_suggestions,
        decisions=[
            DecisionOut(
                id=d.id,
                session_id=d.session_id,
                decision_text=d.decision_text,
                supporting_excerpt=d.supporting_excerpt,
                status=d.status,
                category=d.category,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in saved_decisions
        ],
        action_items=[
            ActionItemOut(
                id=a.id,
                description=a.description,
                owner=a.owner or "Not specified",
                due_date=a.due_date or "Not specified",
                priority=a.priority or "medium",
                status=a.status or "pending",
                evidence_ref=a.evidence_ref,
                decision_id=a.decision_id,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in saved_actions
        ],
        summary=SummaryOut(
            id=summary_row.id,
            summary_text=summary_row.summary_text,
            executive_summary=summary_row.summary_text,
            key_decisions=summary_row.key_decisions,
            key_points=summary_row.key_decisions or [],
            unresolved_questions=summary_row.unresolved_questions,
            pending_questions=summary_row.unresolved_questions or [],
            follow_up_draft=summary_row.follow_up_draft,
            created_at=summary_row.created_at,
            updated_at=summary_row.updated_at,
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Decision Ledger CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/decisions", response_model=list[DecisionOut])
async def list_decisions(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List decisions identified for this conversation."""
    res = await db.execute(
        select(Decision).where(Decision.session_id == session_id).order_by(Decision.created_at.asc())
    )
    return res.scalars().all()


@router.post("/sessions/{session_id}/decisions", response_model=DecisionOut, status_code=201)
async def create_decision(
    session_id: str,
    payload: DecisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually add a confirmed decision to the ledger."""
    dec = Decision(
        session_id=session_id,
        decision_text=payload.decision_text,
        supporting_excerpt=payload.supporting_excerpt,
        status=payload.status,
        category=payload.category or "General",
    )
    db.add(dec)
    await db.commit()
    await db.refresh(dec)
    return dec


@router.patch("/sessions/{session_id}/decisions/{decision_id}", response_model=DecisionOut)
async def update_decision(
    session_id: str,
    decision_id: str,
    payload: DecisionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a decision's text, category, or confirmation status."""
    res = await db.execute(select(Decision).where(Decision.id == decision_id, Decision.session_id == session_id))
    dec = res.scalar_one_or_none()
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found.")

    if payload.decision_text is not None:
        dec.decision_text = payload.decision_text
    if payload.supporting_excerpt is not None:
        dec.supporting_excerpt = payload.supporting_excerpt
    if payload.status is not None:
        dec.status = payload.status
    if payload.category is not None:
        dec.category = payload.category

    await db.commit()
    await db.refresh(dec)
    return dec


@router.delete("/sessions/{session_id}/decisions/{decision_id}", status_code=204)
async def delete_decision(
    session_id: str,
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a decision from the ledger."""
    res = await db.execute(select(Decision).where(Decision.id == decision_id, Decision.session_id == session_id))
    dec = res.scalar_one_or_none()
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found.")
    # Verify session ownership
    s_res = await db.execute(select(Session).where(Session.id == session_id, Session.owner_id == current_user.id))
    if not s_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied.")
    await db.delete(dec)
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Suggestion Regeneration & Summary Export
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/suggestions/regenerate")
async def regenerate_suggestion_endpoint(
    session_id: str,
    payload: SuggestionRegenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate a smart response suggestion based on current objective and transcript."""
    res = await db.execute(select(Session).where(Session.id == session_id, Session.owner_id == current_user.id))
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    t_res = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
        .order_by(TranscriptSegment.created_at.desc())
        .limit(6)
    )
    segs = t_res.scalars().all()
    recent_text = " ".join(s.text for s in reversed(segs))

    sugg = await regenerate_smart_suggestion(
        category=payload.category or "suggested_reply",
        focus_topic=payload.focus_topic,
        objective=session.objective,
        transcript_window=recent_text,
        tone=session.tone,
    )
    return sugg


@router.get("/sessions/{session_id}/export")
async def export_session_summary(
    session_id: str,
    format: str = Query("markdown", pattern="^(markdown|text|transcript|json)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export executive meeting report or full transcript in Markdown, Plain Text, Transcript, or JSON."""
    res = await db.execute(select(Session).where(Session.id == session_id, Session.owner_id == current_user.id))
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    s_res = await db.execute(select(SessionSummary).where(SessionSummary.session_id == session_id))
    summary = s_res.scalar_one_or_none()

    d_res = await db.execute(select(Decision).where(Decision.session_id == session_id).order_by(Decision.created_at.asc()))
    decisions = d_res.scalars().all()

    a_res = await db.execute(select(ActionItem).where(ActionItem.session_id == session_id).order_by(ActionItem.created_at.asc()))
    actions = a_res.scalars().all()

    t_res = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
        .order_by(TranscriptSegment.created_at.asc())
    )
    transcript_segments = t_res.scalars().all()

    date_str = session.created_at.strftime('%Y-%m-%d %H:%M UTC') if session.created_at else 'N/A'

    # Dedicated Transcript Text Export
    if format == "transcript":
        lines = [
            f"NIMAD MEETING TRANSCRIPT: {session.title}",
            f"Objective: {session.objective or 'N/A'}",
            f"Date: {date_str}",
            "═" * 60,
            "",
        ]
        if transcript_segments:
            for s in transcript_segments:
                t_str = s.created_at.strftime('%H:%M:%S') if s.created_at else ''
                t_prefix = f"[{t_str}] " if t_str else ""
                speaker = s.speaker_label or "Participant"
                lines.append(f"{t_prefix}{speaker}: {s.text}")
        else:
            lines.append("No transcript entries recorded for this session.")

        return PlainTextResponse(
            content="\n".join(lines),
            headers={"Content-Disposition": f"attachment; filename=\"transcript-{session_id[:8]}.txt\""}
        )

    # JSON export
    if format == "json":
        data = {
            "session_id": session.id,
            "title": session.title,
            "objective": session.objective,
            "date": date_str,
            "transcript": [
                {
                    "id": s.id,
                    "speaker": s.speaker_label or "Participant",
                    "text": s.text,
                    "source_type": s.source_type,
                    "timestamp": s.created_at.isoformat() if s.created_at else None,
                }
                for s in transcript_segments
            ],
            "decisions": [
                {"id": d.id, "text": d.decision_text, "status": d.status, "category": d.category}
                for d in decisions
            ],
            "action_items": [
                {"id": a.id, "description": a.description, "owner": a.owner, "status": a.status, "due_date": a.due_date}
                for a in actions
            ],
            "summary": summary.summary_text if summary else None,
        }
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=\"meeting-{session_id[:8]}.json\""}
        )

    if format == "text":
        decisions_txt = "\n".join(f"- [{d.status}] {d.decision_text} (Evidence: {d.supporting_excerpt or 'Direct agreement'})" for d in decisions) if decisions else "No recorded decisions."
        actions_txt = "\n".join(f"- [{a.status.upper()}] {a.description} | Owner: {a.owner or 'Not specified'} | Due: {a.due_date or 'Not specified'}" for a in actions) if actions else "No open action items."

        transcript_txt = ""
        if transcript_segments:
            transcript_txt = "\n\nFULL TRANSCRIPT:\n" + "\n".join(
                f"[{s.speaker_label or 'Participant'}]: {s.text}" for s in transcript_segments
            )

        content = f"""NIMAD MEETING REPORT
Title: {session.title}
Objective: {session.objective or 'N/A'}
Date: {date_str}

EXECUTIVE SUMMARY:
{summary.summary_text if summary else 'No summary recorded.'}

DECISIONS:
{decisions_txt}

ACTION ITEMS:
{actions_txt}{transcript_txt}
"""
        return PlainTextResponse(
            content=content,
            headers={"Content-Disposition": f"attachment; filename=\"meeting-{session_id[:8]}.txt\""}
        )

    # Markdown format
    md_lines = [
        f"# {session.title}",
        "",
        f"> **Meeting Objective:** {session.objective or 'Not specified'}  ",
        f"> **Date:** {date_str} | **Status:** {session.status.upper()}  ",
        "",
        "## Executive Summary",
        summary.summary_text if summary else "_No summary generated yet._",
        "",
        "## ⚖️ Decision Ledger",
    ]
    if decisions:
        md_lines.append("| Status | Decision | Category | Supporting Evidence |")
        md_lines.append("|---|---|---|---|")
        for d in decisions:
            excerpt = (d.supporting_excerpt or '').replace('|', '\\|')
            md_lines.append(f"| **{d.status}** | {d.decision_text} | {d.category or 'General'} | {excerpt} |")
    else:
        md_lines.append("_No decisions recorded._")

    md_lines.extend(["", "## ☑️ Action Items & Deliverables"])
    if actions:
        md_lines.append("| Status | Priority | Deliverable | Owner | Deadline |")
        md_lines.append("|---|---|---|---|---|")
        for a in actions:
            md_lines.append(f"| **{a.status.title()}** | {a.priority or 'Medium'} | {a.description} | {a.owner or 'Not specified'} | {a.due_date or 'Not specified'} |")
    else:
        md_lines.append("_No action items recorded._")

    if transcript_segments:
        md_lines.extend(["", "## 🎙️ Transcript Record", ""])
        for s in transcript_segments:
            t_str = s.created_at.strftime('%H:%M:%S') if s.created_at else ''
            t_badge = f"`{t_str}` " if t_str else ""
            md_lines.append(f"- {t_badge}**{s.speaker_label or 'Participant'}:** {s.text}")

    if summary and summary.follow_up_draft:
        md_lines.extend(["", "## ✉️ Follow-Up Draft", "```text", summary.follow_up_draft, "```"])

    return PlainTextResponse(
        content="\n".join(md_lines),
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=\"meeting-{session_id[:8]}.md\""}
    )
