import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Text, DateTime, Boolean, ForeignKey,
    Integer, Float, JSON, Enum as SAEnum
)
from sqlalchemy.orm import mapped_column, Mapped, relationship
from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="owner", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="one_to_one")  # one_to_one | group
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    desired_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    important_questions: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="setup")  # setup | active | ended | deleted
    external_meeting_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    platform_source: Mapped[str | None] = mapped_column(String(50), default="manual_paste")  # google_meet | zoom | microsoft_teams | manual_paste | file_upload
    import_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    audio_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    owner: Mapped["User"] = relationship("User", back_populates="sessions")
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(
        "TranscriptSegment", back_populates="session", cascade="all, delete-orphan"
    )
    insights: Mapped[list["Insight"]] = relationship(
        "Insight", back_populates="session", cascade="all, delete-orphan"
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        "ActionItem", back_populates="session", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["Decision"]] = relationship(
        "Decision", back_populates="session", cascade="all, delete-orphan"
    )
    summary: Mapped["SessionSummary | None"] = relationship(
        "SessionSummary", back_populates="session", cascade="all, delete-orphan", uselist=False
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        "AuditEvent", back_populates="session", cascade="all, delete-orphan"
    )
    semantic_memories: Mapped[list["MeetingSemanticMemory"]] = relationship(
        "MeetingSemanticMemory", back_populates="session", cascade="all, delete-orphan"
    )
    participants: Mapped[list["SessionParticipant"]] = relationship(
        "SessionParticipant", back_populates="session", cascade="all, delete-orphan"
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    speaker_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    speaker_role: Mapped[str | None] = mapped_column(String(50), default="screen_attender")  # screen_attender | host | participant
    audio_channel: Mapped[str | None] = mapped_column(String(50), default="screen_audio")  # screen_audio | user_mic
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), default="screen_attender")  # screen_attender | mic_user | paste | audio
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="transcript_segments")


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_label: Mapped[str] = mapped_column(String(20), default="medium")  # high | medium | low
    objective_alignment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evidence_refs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    user_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)  # useful | not_useful
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="insights")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    decision_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("decisions.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), default="medium")  # high | medium | low
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | in_progress | completed | cancelled | open | done
    evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="action_items")


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False, unique=True)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    important_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    key_decisions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    unresolved_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    follow_up_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="summary")


class SessionParticipant(Base):
    __tablename__ = "session_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="attendee")  # host | attendee
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="participants")
    user: Mapped["User"] = relationship("User")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    metadata_minimal: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    session: Mapped["Session | None"] = relationship("Session", back_populates="audit_events")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    decision_text: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PROPOSED")  # PROPOSED | CONFIRMED | REJECTED | PENDING_CONFIRMATION
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="decisions")
    action_items: Mapped[list["ActionItem"]] = relationship(
        "ActionItem",
        foreign_keys=[ActionItem.decision_id],
        primaryjoin="Decision.id == ActionItem.decision_id"
    )


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # google_meet | zoom | microsoft_teams
    status: Mapped[str] = mapped_column(String(50), default="not_connected")  # not_connected | configuration_required | connected | sync_error | coming_soon
    account_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class MeetingSemanticMemory(Base):
    __tablename__ = "meeting_semantic_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # important_point | key_decision | action_item | qa_pair | speaker_statement | summary_point
    speaker_label: Mapped[str] = mapped_column(String(100), nullable=False, default="Attender")  # Person who said or committed (e.g. Sarah Chen (VP Engineering))
    speaker_role: Mapped[str] = mapped_column(String(50), default="screen_attender")  # screen_attender | host | lead | procurement | client
    content: Mapped[str] = mapped_column(Text, nullable=False)
    semantic_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)  # Dense vector embedding values
    embedding_dim: Mapped[int] = mapped_column(Integer, default=128)
    semantic_tags: Mapped[list | None] = mapped_column(JSON, nullable=True)  # Categorical tags / entity keywords
    related_memory_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)  # Semantic links to memories from past/current sessions
    similarity_graph: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {memory_id: similarity_score}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="semantic_memories")


class AttendeeVoiceProfile(Base):
    __tablename__ = "attendee_voice_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    speaker_name: Mapped[str] = mapped_column(String(150), nullable=False)
    speaker_title: Mapped[str | None] = mapped_column(String(150), nullable=True)  # e.g., "VP Engineering", "Procurement Lead"
    screen_position_index: Mapped[int | None] = mapped_column(Integer, default=0)
    voice_signature_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    total_utterances: Mapped[int] = mapped_column(Integer, default=0)
    total_key_points_spoken: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


