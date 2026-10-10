import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from jose import jwt, JWTError

from app.core.config import get_settings
from app.db.database import get_db, AsyncSessionLocal
from app.models.models import Session, User, SessionParticipant, TranscriptSegment, Insight, ActionItem, SessionSummary
from app.schemas.schemas import (
    MeetingCreateRequest, MeetingJoinRequest, MeetingJoinResponse, MeetingPublicInfo, MeetingParticipantOut, SummaryOut
)
from app.security.auth import get_current_user, create_access_token, hash_password
from app.services.providers.ai_adapter import generate_easy_answer, generate_summary

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/v1/meetings", tags=["meetings"])


# ──────────────────────────── Room Connection Manager ────────────────────────────

class MeetingRoomManager:
    """Manages active WebRTC & WebSocket connections for live meetings."""

    def __init__(self):
        # session_id -> dict of client_id -> {"ws": WebSocket, "name": str, "role": str, "user_id": str}
        self.rooms: dict[str, dict[str, dict]] = defaultdict(dict)

    async def connect(self, session_id: str, client_id: str, name: str, role: str, user_id: str, ws: WebSocket):
        await ws.accept()
        self.rooms[session_id][client_id] = {
            "ws": ws,
            "name": name,
            "role": role,
            "user_id": user_id,
            "client_id": client_id,
        }
        logger.info("Client %s (%s) connected to meeting room %s", client_id, name, session_id)
        # Broadcast room state
        await self.broadcast_room_state(session_id, event="user_joined", joined_client={"client_id": client_id, "name": name, "role": role})

    def disconnect(self, session_id: str, client_id: str) -> Optional[dict]:
        if session_id in self.rooms and client_id in self.rooms[session_id]:
            user_info = self.rooms[session_id].pop(client_id)
            if not self.rooms[session_id]:
                del self.rooms[session_id]
            logger.info("Client %s disconnected from meeting room %s", client_id, session_id)
            return user_info
        return None

    def get_participants(self, session_id: str) -> list[dict]:
        if session_id not in self.rooms:
            return []
        return [
            {
                "client_id": cid,
                "name": info["name"],
                "role": info["role"],
                "user_id": info["user_id"]
            }
            for cid, info in self.rooms[session_id].items()
        ]

    async def broadcast(self, session_id: str, message: dict, exclude_client_id: Optional[str] = None):
        if session_id not in self.rooms:
            return
        dead = []
        for cid, info in list(self.rooms[session_id].items()):
            if exclude_client_id and cid == exclude_client_id:
                continue
            try:
                await info["ws"].send_json(message)
            except Exception as e:
                logger.warning("Error sending to client %s in room %s: %s", cid, session_id, e)
                dead.append(cid)
        for d in dead:
            self.disconnect(session_id, d)

    async def send_to_client(self, session_id: str, target_client_id: str, message: dict):
        if session_id in self.rooms and target_client_id in self.rooms[session_id]:
            try:
                await self.rooms[session_id][target_client_id]["ws"].send_json(message)
            except Exception as e:
                logger.warning("Error sending to target client %s: %s", target_client_id, e)
                self.disconnect(session_id, target_client_id)

    async def broadcast_room_state(self, session_id: str, event: str = "state_sync", joined_client: Optional[dict] = None, left_client: Optional[dict] = None):
        participants = self.get_participants(session_id)
        msg = {
            "type": "room_state",
            "event": event,
            "participant_count": len(participants),
            "participants": participants,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if joined_client:
            msg["joined_client"] = joined_client
        if left_client:
            msg["left_client"] = left_client
        await self.broadcast(session_id, msg)


room_manager = MeetingRoomManager()


def _clean_session_id(input_str: str) -> str:
    cleaned = input_str.strip()
    if "?id=" in cleaned:
        cleaned = cleaned.split("?id=")[-1].split("&")[0].split("#")[0]
    elif "?session_id=" in cleaned:
        cleaned = cleaned.split("?session_id=")[-1].split("&")[0].split("#")[0]
    elif "?meeting_id=" in cleaned:
        cleaned = cleaned.split("?meeting_id=")[-1].split("&")[0].split("#")[0]
    elif "/session/" in cleaned:
        cleaned = cleaned.split("/session/")[-1].split("?")[0].split("#")[0]
    elif "/sessions/" in cleaned:
        cleaned = cleaned.split("/sessions/")[-1].split("?")[0].split("#")[0]
    elif "/meeting/" in cleaned:
        cleaned = cleaned.split("/meeting/")[-1].split("?")[0].split("#")[0]
    elif "/" in cleaned:
        cleaned = cleaned.split("/")[-1].split("?")[0].split("#")[0]
    return cleaned.strip("/").strip()


# ──────────────────────────── REST Endpoints ────────────────────────────

@router.post("/create", response_model=MeetingJoinResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new instant meeting room and generate shareable meeting link.
    Supports authenticated users as host, or creates an instant host profile.
    """
    host_user = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            token_payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = token_payload.get("sub")
            if user_id:
                u_res = await db.execute(select(User).where(User.id == user_id))
                host_user = u_res.scalar_one_or_none()
        except JWTError:
            pass

    display_name = (payload.host_name or "").strip() or "Host"
    if not host_user:
        user_unique = uuid.uuid4().hex[:8]
        host_user = User(
            email=f"host_{user_unique}@meeting.copilot",
            display_name=display_name,
            hashed_password=hash_password(uuid.uuid4().hex),
            is_active=True,
        )
        db.add(host_user)
        await db.flush()
    else:
        display_name = host_user.display_name

    title = (payload.title or "").strip() or "Live Meeting Room"
    retention_until = datetime.now(timezone.utc) + timedelta(days=settings.SESSION_RETENTION_DAYS)
    meeting_session = Session(
        owner_id=host_user.id,
        title=title,
        mode=payload.mode or "group",
        objective=payload.objective,
        status="active",
        retention_until=retention_until,
    )
    db.add(meeting_session)
    await db.flush()

    participant = SessionParticipant(
        session_id=meeting_session.id,
        user_id=host_user.id,
        display_name=display_name,
        role="host",
    )
    db.add(participant)
    await db.commit()
    await db.refresh(meeting_session)

    token = create_access_token(host_user.id)

    return MeetingJoinResponse(
        session_id=meeting_session.id,
        title=meeting_session.title,
        objective=meeting_session.objective,
        mode=meeting_session.mode,
        display_name=display_name,
        role="host",
        access_token=token,
        meeting_url=f"/session/{meeting_session.id}",
        meeting_code=meeting_session.id[:8].upper(),
    )


@router.post("/join", response_model=MeetingJoinResponse)
async def join_meeting(
    payload: MeetingJoinRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Join a meeting using meeting URL or room code.
    Authenticates guest or signed-in user and grants access to the meeting session.
    """
    session_id = _clean_session_id(payload.meeting_id_or_url)
    if not session_id:
        raise HTTPException(status_code=400, detail="Please enter a valid meeting link or room code.")

    # Find session
    res = await db.execute(select(Session).where(Session.id == session_id))
    meeting_session = res.scalar_one_or_none()

    # Fallback: match by prefix (first 8 chars) if code entered
    if not meeting_session and len(session_id) <= 12:
        prefix_res = await db.execute(select(Session).where(Session.id.startswith(session_id.lower())))
        meeting_session = prefix_res.scalar_one_or_none()

    if not meeting_session:
        raise HTTPException(status_code=404, detail="Meeting room not found. Please verify your meeting link.")
    if meeting_session.status == "deleted":
        raise HTTPException(status_code=410, detail="This meeting has ended and was deleted.")

    # Ensure display name
    display_name = (payload.display_name or "").strip()
    if not display_name:
        display_name = "Guest Attendee"

    # Create/find attendee user
    user_unique = uuid.uuid4().hex[:8]
    guest_user = User(
        email=f"attendee_{user_unique}@meeting.copilot",
        display_name=display_name,
        hashed_password=hash_password(uuid.uuid4().hex),
        is_active=True,
    )
    db.add(guest_user)
    await db.flush()

    role = "host" if meeting_session.owner_id == guest_user.id else "attendee"

    # Register in SessionParticipant
    participant = SessionParticipant(
        session_id=meeting_session.id,
        user_id=guest_user.id,
        display_name=display_name,
        role=role,
    )
    db.add(participant)
    await db.commit()
    await db.refresh(guest_user)

    token = create_access_token(guest_user.id)

    return MeetingJoinResponse(
        session_id=meeting_session.id,
        title=meeting_session.title,
        objective=meeting_session.objective,
        mode=meeting_session.mode,
        display_name=display_name,
        role=role,
        access_token=token,
        meeting_url=f"/session/{meeting_session.id}",
        meeting_code=meeting_session.id[:8].upper(),
    )


@router.get("/{session_id}/public-info", response_model=MeetingPublicInfo)
async def get_meeting_public_info(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve public meeting title and status for invite preview."""
    clean_id = _clean_session_id(session_id)
    res = await db.execute(select(Session).where(Session.id == clean_id))
    meeting_session = res.scalar_one_or_none()
    if not meeting_session:
        raise HTTPException(status_code=404, detail="Meeting not found")

    owner_res = await db.execute(select(User).where(User.id == meeting_session.owner_id))
    owner = owner_res.scalar_one_or_none()

    return MeetingPublicInfo(
        id=meeting_session.id,
        title=meeting_session.title,
        objective=meeting_session.objective,
        status=meeting_session.status,
        owner_name=owner.display_name if owner else "Host",
        created_at=meeting_session.created_at,
    )


@router.get("/{session_id}/participants", response_model=list[MeetingParticipantOut])
async def get_session_participants(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List registered participants for the meeting."""
    res = await db.execute(
        select(SessionParticipant)
        .where(SessionParticipant.session_id == session_id)
        .order_by(SessionParticipant.joined_at)
    )
    return res.scalars().all()


@router.post("/{session_id}/summarize", response_model=SummaryOut)
async def summarize_meeting(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate or refresh important summary points from all participants' voiced transcripts.
    Broadcasts the updated summary points to everyone in the room via WebSocket.
    """
    # Verify session
    s_res = await db.execute(select(Session).where(Session.id == session_id))
    meeting_session = s_res.scalar_one_or_none()
    if not meeting_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch all transcripts
    t_res = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.session_id == session_id)
        .order_by(TranscriptSegment.created_at)
    )
    segments = t_res.scalars().all()
    full_transcript = "\n".join(f"[{s.speaker_label or 'Speaker'}]: {s.text}" for s in segments)

    # Fetch insights & action items
    i_res = await db.execute(select(Insight).where(Insight.session_id == session_id))
    insights = [{"type": i.type, "content": i.content} for i in i_res.scalars().all()]

    a_res = await db.execute(select(ActionItem).where(ActionItem.session_id == session_id))
    actions = [{"description": a.description, "owner": a.owner} for a in a_res.scalars().all()]

    summary_data = await generate_summary(
        transcript=full_transcript,
        objective=meeting_session.objective,
        insights=insights,
        action_items=actions,
    )

    important_pts = summary_data.get("important_points") or summary_data.get("key_points") or []
    exec_sum = summary_data.get("executive_summary") or ""

    existing = await db.execute(select(SessionSummary).where(SessionSummary.session_id == session_id))
    summary = existing.scalar_one_or_none()
    if summary:
        summary.summary_text = summary_data.get("summary_text", "")
        summary.executive_summary = exec_sum
        summary.key_points = important_pts
        summary.important_points = important_pts
        summary.key_decisions = summary_data.get("key_decisions", [])
        summary.unresolved_questions = summary_data.get("unresolved_questions", [])
        summary.follow_up_draft = summary_data.get("follow_up_draft", "")
    else:
        summary = SessionSummary(
            session_id=session_id,
            summary_text=summary_data.get("summary_text", ""),
            executive_summary=exec_sum,
            key_points=important_pts,
            important_points=important_pts,
            key_decisions=summary_data.get("key_decisions", []),
            unresolved_questions=summary_data.get("unresolved_questions", []),
            follow_up_draft=summary_data.get("follow_up_draft", ""),
        )
        db.add(summary)

    await db.commit()
    await db.refresh(summary)

    # Broadcast summary update to active participants
    await room_manager.broadcast(session_id, {
        "type": "summary_ready",
        "summary": {
            "summary_text": summary.summary_text,
            "executive_summary": summary.executive_summary,
            "important_points": summary.important_points,
            "key_decisions": summary.key_decisions,
            "unresolved_questions": summary.unresolved_questions,
            "follow_up_draft": summary.follow_up_draft,
        }
    })

    return summary


# ──────────────────────────── WebSocket Signaling & Sync ────────────────────────────

@router.websocket("/ws/{session_id}")
async def meeting_websocket(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
    name: Optional[str] = Query("Participant"),
    role: Optional[str] = Query("attendee"),
):
    """
    Real-time multi-user meeting WebSocket.
    Handles:
    - Attender presence & sync
    - WebRTC peer connection audio & video signaling (Offer, Answer, ICE candidates)
    - Live microphone voice transcription broadcast from all participants
    - Live speaking indicator rings
    - Real-time summary point delivery
    """
    user_id = f"guest-{uuid.uuid4().hex[:8]}"
    display_name = name or "Participant"
    user_role = role or "attendee"

    # Authenticate token if present
    if token:
        try:
            payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            extracted_uid = payload.get("sub")
            if extracted_uid:
                user_id = extracted_uid
                async with AsyncSessionLocal() as db:
                    u_res = await db.execute(select(User).where(User.id == user_id))
                    user_obj = u_res.scalar_one_or_none()
                    if user_obj:
                        display_name = user_obj.display_name
                    # Check if owner
                    s_res = await db.execute(select(Session).where(Session.id == session_id))
                    sess_obj = s_res.scalar_one_or_none()
                    if sess_obj and sess_obj.owner_id == user_id:
                        user_role = "host"
        except JWTError:
            pass

    client_id = f"{user_id}-{uuid.uuid4().hex[:6]}"
    await room_manager.connect(session_id, client_id, display_name, user_role, user_id, websocket)

    try:
        while True:
            raw_text = await websocket.receive_text()
            if not raw_text:
                continue
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            # 1. WebRTC Signaling (offer, answer, candidate)
            if msg_type == "signal":
                target_id = data.get("target_client_id")
                signal_data = data.get("signal_data")
                if target_id and signal_data:
                    await room_manager.send_to_client(session_id, target_id, {
                        "type": "signal",
                        "sender_client_id": client_id,
                        "sender_name": display_name,
                        "signal_data": signal_data,
                    })

            # 2. Live Spoken Voice Transcript Utterance
            elif msg_type == "transcript_utterance":
                text = (data.get("text") or "").strip()
                speaker = data.get("speaker") or display_name
                is_final = bool(data.get("is_final", False))

                if text:
                    # Broadcast to everyone in room immediately
                    await room_manager.broadcast(session_id, {
                        "type": "transcript_utterance",
                        "sender_client_id": client_id,
                        "speaker": speaker,
                        "text": text,
                        "is_final": is_final,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

                    # If final, persist segment and check for Q&A / Easy Answer
                    if is_final:
                        try:
                            async with AsyncSessionLocal() as db:
                                seg = TranscriptSegment(
                                    session_id=session_id,
                                    speaker_label=speaker,
                                    speaker_role=user_role,
                                    audio_channel="user_mic",
                                    text=text,
                                    source_type="voice_mic",
                                )
                                db.add(seg)
                                await db.commit()
                                await db.refresh(seg)

                                # Check for question
                                lower = text.lower()
                                is_q = ("?" in text or any(lower.startswith(w) for w in ["what", "how", "why", "when", "where", "can we", "could we", "is there", "will", "does", "do you"]))
                                if is_q:
                                    s_res = await db.execute(select(Session).where(Session.id == session_id))
                                    sess_obj = s_res.scalar_one_or_none()
                                    obj_goal = sess_obj.objective if sess_obj else None
                                    sess_mode = sess_obj.mode if sess_obj else "one_to_one"

                                    ans_data = await generate_easy_answer(
                                        question=text,
                                        objective=obj_goal,
                                        session_mode=sess_mode,
                                        speaker_label=speaker
                                    )
                                    await room_manager.broadcast(session_id, {
                                        "type": "easy_answer_ready",
                                        "question": text,
                                        "speaker": speaker,
                                        "easy_answer": ans_data.get("easy_answer"),
                                        "talking_points": ans_data.get("talking_points", []),
                                        "confidence_label": ans_data.get("confidence_label", "high"),
                                    })
                        except Exception as e:
                            logger.warning("Error persisting final transcript in websocket: %s", e)

            # 3. Live Speaking Indicator
            elif msg_type == "speaking_indicator":
                is_speaking = bool(data.get("is_speaking", False))
                await room_manager.broadcast(session_id, {
                    "type": "speaking_indicator",
                    "client_id": client_id,
                    "speaker": display_name,
                    "is_speaking": is_speaking,
                }, exclude_client_id=client_id)

            # 4. Request Summary Points
            elif msg_type == "request_summary":
                try:
                    async with AsyncSessionLocal() as db:
                        s_res = await db.execute(select(Session).where(Session.id == session_id))
                        sess_obj = s_res.scalar_one_or_none()
                        if sess_obj:
                            t_res = await db.execute(
                                select(TranscriptSegment)
                                .where(TranscriptSegment.session_id == session_id)
                                .order_by(TranscriptSegment.created_at)
                            )
                            segments = t_res.scalars().all()
                            full_transcript = "\n".join(f"[{s.speaker_label or 'Speaker'}]: {s.text}" for s in segments)

                            i_res = await db.execute(select(Insight).where(Insight.session_id == session_id))
                            insights = [{"type": i.type, "content": i.content} for i in i_res.scalars().all()]

                            a_res = await db.execute(select(ActionItem).where(ActionItem.session_id == session_id))
                            actions = [{"description": a.description, "owner": a.owner} for a in a_res.scalars().all()]

                            summary_data = await generate_summary(
                                transcript=full_transcript,
                                objective=sess_obj.objective,
                                insights=insights,
                                action_items=actions,
                            )
                            important_pts = summary_data.get("important_points") or summary_data.get("key_points") or []
                            exec_sum = summary_data.get("executive_summary") or ""

                            existing = await db.execute(select(SessionSummary).where(SessionSummary.session_id == session_id))
                            sum_obj = existing.scalar_one_or_none()
                            if sum_obj:
                                sum_obj.summary_text = summary_data.get("summary_text", "")
                                sum_obj.executive_summary = exec_sum
                                sum_obj.key_points = important_pts
                                sum_obj.important_points = important_pts
                                sum_obj.key_decisions = summary_data.get("key_decisions", [])
                                sum_obj.unresolved_questions = summary_data.get("unresolved_questions", [])
                                sum_obj.follow_up_draft = summary_data.get("follow_up_draft", "")
                            else:
                                sum_obj = SessionSummary(
                                    session_id=session_id,
                                    summary_text=summary_data.get("summary_text", ""),
                                    executive_summary=exec_sum,
                                    key_points=important_pts,
                                    important_points=important_pts,
                                    key_decisions=summary_data.get("key_decisions", []),
                                    unresolved_questions=summary_data.get("unresolved_questions", []),
                                    follow_up_draft=summary_data.get("follow_up_draft", ""),
                                )
                                db.add(sum_obj)
                            await db.commit()

                            await room_manager.broadcast(session_id, {
                                "type": "summary_ready",
                                "summary": {
                                    "summary_text": sum_obj.summary_text,
                                    "executive_summary": sum_obj.executive_summary,
                                    "important_points": sum_obj.important_points,
                                    "key_decisions": sum_obj.key_decisions,
                                    "unresolved_questions": sum_obj.unresolved_questions,
                                    "follow_up_draft": sum_obj.follow_up_draft,
                                }
                            })
                except Exception as e:
                    logger.warning("Error generating summary in websocket: %s", e)

    except WebSocketDisconnect:
        info = room_manager.disconnect(session_id, client_id)
        if info:
            await room_manager.broadcast_room_state(session_id, event="user_left", left_client={"client_id": client_id, "name": display_name})
    except Exception as exc:
        logger.warning("WebSocket error for client %s: %s", client_id, exc)
        info = room_manager.disconnect(session_id, client_id)
        if info:
            await room_manager.broadcast_room_state(session_id, event="user_left", left_client={"client_id": client_id, "name": display_name})
