from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, field_validator


# ──────────────────────────── Auth / User ────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    display_name: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ──────────────────────────── Session ────────────────────────────

class SessionCreate(BaseModel):
    title: str
    mode: str = "one_to_one"
    objective: Optional[str] = None
    audience: Optional[str] = None
    desired_outcome: Optional[str] = None
    tone: Optional[str] = None
    constraints: Optional[str] = None
    key_topics: Optional[str] = None
    important_questions: Optional[str] = None
    audio_consent: bool = False


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    objective: Optional[str] = None
    audience: Optional[str] = None
    desired_outcome: Optional[str] = None
    tone: Optional[str] = None
    constraints: Optional[str] = None
    key_topics: Optional[str] = None
    important_questions: Optional[str] = None
    status: Optional[str] = None
    audio_consent: Optional[bool] = None


class SessionOut(BaseModel):
    id: str
    title: str
    mode: str
    objective: Optional[str]
    audience: Optional[str]
    desired_outcome: Optional[str]
    tone: Optional[str]
    constraints: Optional[str]
    key_topics: Optional[str]
    important_questions: Optional[str] = None
    status: str
    created_at: datetime
    ended_at: Optional[datetime]
    audio_consent: bool

    model_config = {"from_attributes": True}


# ──────────────────────────── Transcript ────────────────────────────

class TranscriptSubmit(BaseModel):
    text: str
    speaker_label: Optional[str] = None
    source_type: str = "paste"  # paste | manual
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None


class TranscriptSegmentOut(BaseModel):
    id: str
    speaker_label: Optional[str]
    text: str
    timestamp_start: Optional[float]
    timestamp_end: Optional[float]
    source_type: str
    created_at: datetime
    easy_answer: Optional[str] = None
    talking_points: Optional[list[str]] = None

    model_config = {"from_attributes": True}


# ──────────────────────────── Meeting Q&A ────────────────────────────

class QuestionAnswerRequest(BaseModel):
    question: str
    speaker_label: Optional[str] = "Attender"


class QuestionAnswerResponse(BaseModel):
    id: str
    question: str
    speaker_label: str
    easy_answer: str
    talking_points: list[str] = []
    confidence_label: str = "high"
    objective_alignment: str = "supports_goal"
    created_at: datetime


# ──────────────────────────── Insights ────────────────────────────

class InsightOut(BaseModel):
    id: str
    type: str
    content: str
    confidence_label: str
    objective_alignment: Optional[str]
    evidence_refs: Optional[Any]
    user_edited: bool
    user_rating: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class InsightFeedback(BaseModel):
    rating: str  # useful | not_useful
    correction: Optional[str] = None


# ──────────────────────────── Action Items ────────────────────────────

class ActionItemCreate(BaseModel):
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = "medium"  # high | medium | low
    status: Optional[str] = "pending"   # pending | in_progress | completed | cancelled
    decision_id: Optional[str] = None
    evidence_ref: Optional[str] = None


class ActionItemUpdate(BaseModel):
    description: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    decision_id: Optional[str] = None
    evidence_ref: Optional[str] = None


class ActionItemOut(BaseModel):
    id: str
    description: str
    owner: Optional[str] = "Not specified"
    due_date: Optional[str] = "Not specified"
    priority: Optional[str] = "medium"
    status: str = "pending"
    decision_id: Optional[str] = None
    evidence_ref: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SummaryOut(BaseModel):
    id: str
    summary_text: str
    executive_summary: Optional[str] = None
    key_decisions: Optional[list] = None
    key_points: Optional[list] = None
    important_points: Optional[list] = None
    unresolved_questions: Optional[list] = None
    pending_questions: Optional[list] = None
    follow_up_draft: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SummaryUpdate(BaseModel):
    summary_text: Optional[str] = None
    executive_summary: Optional[str] = None
    key_points: Optional[list] = None
    important_points: Optional[list] = None
    key_decisions: Optional[list] = None
    unresolved_questions: Optional[list] = None
    follow_up_draft: Optional[str] = None


# ──────────────────────────── Decisions ────────────────────────────

class DecisionCreate(BaseModel):
    decision_text: str
    supporting_excerpt: Optional[str] = None
    status: str = "PROPOSED"  # PROPOSED | CONFIRMED | REJECTED | PENDING_CONFIRMATION
    category: Optional[str] = "General"


class DecisionUpdate(BaseModel):
    decision_text: Optional[str] = None
    supporting_excerpt: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None


class DecisionOut(BaseModel):
    id: str
    session_id: str
    decision_text: str
    supporting_excerpt: Optional[str] = None
    status: str = "PROPOSED"
    category: Optional[str] = "General"
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ──────────────────────────── Smart Suggestions ────────────────────

class SmartSuggestionItem(BaseModel):
    id: Optional[str] = None
    category: Optional[str] = "suggested_reply"  # suggested_reply | follow_up_question | clarification_request | objection_response | negotiation | next_step
    type: Optional[str] = "RECOMMENDED REPLY"
    title: Optional[str] = None
    suggestion_text: str
    objective_relevance: Optional[str] = None
    why_relevant: Optional[str] = None
    context_rationale: Optional[str] = None
    supporting_excerpt: Optional[str] = None
    is_dismissed: bool = False
    user_edited: bool = False


class SuggestionRegenerateRequest(BaseModel):
    category: Optional[str] = None
    focus_topic: Optional[str] = None


# ──────────────────────────── Integrations ────────────────────────────

class IntegrationCardOut(BaseModel):
    provider: str  # google_meet | zoom | microsoft_teams
    name: str
    icon_type: str
    description: str
    status: str  # not_connected | configuration_required | connected | sync_error | coming_soon
    is_configured: bool
    account_email: Optional[str] = None
    connected_account: Optional[str] = None
    account_name: Optional[str] = None
    capabilities: list[str] = []
    last_synced_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    auth_url: Optional[str] = None


class IntegrationConnectRequest(BaseModel):
    account_email: Optional[str] = None
    account_name: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    auth_code: Optional[str] = None


class IntegrationDisconnectResponse(BaseModel):
    success: bool
    provider: str
    message: str


# ──────────────────────────── Transcript Import & Analysis ────────────

class TranscriptImportRequest(BaseModel):
    import_method: Optional[str] = "paste"  # paste | upload | meeting_url
    content: Optional[str] = None
    raw_text: Optional[str] = None
    meeting_url: Optional[str] = None
    meeting_title: Optional[str] = None
    title: Optional[str] = None
    objective: Optional[str] = None
    session_id: Optional[str] = None
    source_type: Optional[str] = None
    platform_source: Optional[str] = None


class TranscriptImportResponse(BaseModel):
    session_id: str
    session_title: str
    title: Optional[str] = None
    segments_imported: int
    segments_count: int
    char_count: int
    platform_source: str
    status: str = "imported"
    message: str


class FullAnalysisResponse(BaseModel):
    session_id: str
    session_title: Optional[str] = None
    objective: Optional[str] = None
    platform_source: Optional[str] = None
    insights: list[InsightOut]
    smart_response_suggestions: list[dict]
    suggestions: Optional[list[dict]] = None
    decisions: list[DecisionOut]
    action_items: list[ActionItemOut]
    summary: Optional[SummaryOut]


# ──────────────────────────── Vector Database & Semantic Memory ───────

class SemanticMemoryOut(BaseModel):
    id: str
    session_id: str
    user_id: str
    category: str
    speaker_label: str
    speaker_role: str
    content: str
    semantic_context: Optional[str] = None
    semantic_tags: list[str] = []
    related_memory_ids: list[str] = []
    similarity_graph: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 6
    category: Optional[str] = None
    speaker_filter: Optional[str] = None
    exclude_session_id: Optional[str] = None


class SemanticSearchResultItem(BaseModel):
    id: str
    session_id: str
    session_title: str
    session_date: str
    category: str
    speaker_label: str
    speaker_role: str
    content: str
    semantic_context: Optional[str] = None
    semantic_tags: list[str] = []
    similarity: float
    related_memory_ids: list[str] = []
    similarity_graph: dict = {}


class SemanticSearchResponse(BaseModel):
    query: str
    results_count: int
    results: list[SemanticSearchResultItem]


class VectorizeSessionResponse(BaseModel):
    session_id: str
    indexed_count: int
    status: str


class MultiSpeakerUtteranceSubmit(BaseModel):
    speaker_label: str
    text: str
    speaker_role: Optional[str] = "screen_attender"  # screen_attender | host | participant | lead
    audio_channel: Optional[str] = "screen_audio"  # screen_audio | user_mic
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    confidence: Optional[float] = 0.95
    source_type: Optional[str] = "screen_attender"


# ──────────────────────────── Meeting Portal & Real-Time ────────────────────────────

class MeetingCreateRequest(BaseModel):
    title: Optional[str] = "Live Meeting Room"
    objective: Optional[str] = None
    host_name: Optional[str] = "Host"
    mode: Optional[str] = "group"


class MeetingJoinRequest(BaseModel):
    meeting_id_or_url: str
    display_name: Optional[str] = "Participant"


class MeetingJoinResponse(BaseModel):
    session_id: str
    title: str
    objective: Optional[str] = None
    mode: str = "one_to_one"
    display_name: str
    role: str
    access_token: str
    meeting_url: str
    meeting_code: str


class MeetingPublicInfo(BaseModel):
    id: str
    title: str
    objective: Optional[str] = None
    status: str
    owner_name: Optional[str] = "Host"
    created_at: datetime


class MeetingParticipantOut(BaseModel):
    id: str
    session_id: str
    user_id: str
    display_name: str
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}



