import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Session, User, TranscriptSegment, Decision, ActionItem, Insight, MeetingSemanticMemory
from app.security.auth import hash_password
from app.services.vector_db_service import VectorDatabaseService

logger = logging.getLogger(__name__)


async def seed_demo_data_for_user(db: AsyncSession, user: User):
    """
    Seeds rich demo meetings with transcripts, decisions, and action items for a user.
    """
    s_res = await db.execute(select(Session).where(Session.owner_id == user.id, Session.status != "deleted"))
    existing_sessions = s_res.scalars().all()
    if len(existing_sessions) >= 3:
        logger.info("User %s already has %d meetings in database.", user.email, len(existing_sessions))
        return

    now = datetime.now(timezone.utc)
    two_days_ago = now - timedelta(days=2)
    tomorrow = now + timedelta(days=1)
    three_days_later = now + timedelta(days=3)

    # ── Meeting 1: Attended Architecture Review (Today) ──
    s1 = Session(
        owner_id=user.id,
        title="Acme Corp Technical Architecture & Procurement Review",
        mode="group",
        objective="Review high-availability failover architecture and confirm SOC2 SIEM export capability.",
        desired_outcome="Procurement sign-off on 99.9% uptime SLA and agreement on Splunk connector pilot.",
        audience="Sarah Chen (VP Engineering), David Miller (Procurement), Alex Mercer (Lead Engineer)",
        status="ended",
        platform_source="google_meet",
        external_meeting_url="https://meet.google.com/acme-arch-rev",
        created_at=now - timedelta(hours=3),
        ended_at=now - timedelta(hours=2),
    )
    db.add(s1)
    await db.flush()

    # Transcripts for Meeting 1
    t1_segments = [
        TranscriptSegment(
            session_id=s1.id,
            speaker_label="Sarah Chen (VP Engineering)",
            speaker_role="screen_attender",
            audio_channel="screen_audio",
            text="What is your enterprise uptime guarantee, and how do you handle disaster recovery failovers?",
            source_type="screen_attender",
            confidence=0.98,
        ),
        TranscriptSegment(
            session_id=s1.id,
            speaker_label="You (Host)",
            speaker_role="host",
            audio_channel="user_mic",
            text="We provide a 99.9% uptime SLA with active-passive multi-region failovers under 30 seconds across GCP us-central1 and us-east4.",
            source_type="mic_user",
            confidence=0.99,
        ),
        TranscriptSegment(
            session_id=s1.id,
            speaker_label="David Miller (Procurement)",
            speaker_role="screen_attender",
            audio_channel="screen_audio",
            text="Can you confirm if SOC2 Type II audit logs can be exported directly to our SIEM?",
            source_type="screen_attender",
            confidence=0.96,
        ),
        TranscriptSegment(
            session_id=s1.id,
            speaker_label="You (Host)",
            speaker_role="host",
            audio_channel="user_mic",
            text="Yes, complete SOC2 Type II audit logs stream automatically via webhook and our pre-built Splunk and Datadog connectors.",
            source_type="mic_user",
            confidence=0.99,
        ),
    ]
    for t in t1_segments:
        db.add(t)

    # Decisions for Meeting 1
    d1 = Decision(
        session_id=s1.id,
        decision_text="Architecture approved for 30-day enterprise pilot on Google Cloud.",
        status="CONFIRMED",
        supporting_excerpt="David Miller and Sarah Chen agreed to SLA and SOC2 logging specs.",
    )
    d2 = Decision(
        session_id=s1.id,
        decision_text="SOC2 Type II compliance audit packet forwarded to David Miller.",
        status="CONFIRMED",
        supporting_excerpt="Compliance export verified via Splunk connector.",
    )
    db.add(d1)
    db.add(d2)

    # Action Items for Meeting 1
    a1 = ActionItem(
        session_id=s1.id,
        description="Send Splunk webhook documentation to Sarah Chen",
        owner="Alex Mercer",
        due_date="Tomorrow",
        status="pending"
    )
    a2 = ActionItem(
        session_id=s1.id,
        description="Provide MSA and DPA agreement draft to Procurement",
        owner="Legal Team",
        due_date="Friday",
        status="pending"
    )
    db.add(a1)
    db.add(a2)

    # ── Meeting 2: Attended Review (2 Days Ago) ──
    s2 = Session(
        owner_id=user.id,
        title="Sprint 42 Architecture & Audio Diarization Review",
        mode="group",
        objective="Finalize real-time streaming latency SLA and database indexing strategy.",
        desired_outcome="Latency targets validated under 100ms.",
        audience="Engineering Team, Lead Architect, Product Lead",
        status="ended",
        platform_source="google_meet",
        external_meeting_url="https://meet.google.com/spr-42-arch",
        created_at=two_days_ago,
        ended_at=two_days_ago + timedelta(minutes=45),
    )
    db.add(s2)
    await db.flush()

    t2 = TranscriptSegment(
        session_id=s2.id,
        speaker_label="Lead Architect",
        speaker_role="screen_attender",
        audio_channel="screen_audio",
        text="How does speech-to-text handle concurrent background audio in loud conference rooms?",
        source_type="screen_attender",
        confidence=0.97,
    )
    t3 = TranscriptSegment(
        session_id=s2.id,
        speaker_label="You (Host)",
        speaker_role="host",
        audio_channel="user_mic",
        text="Dual-channel WebRTC audio processing with noise-suppression and speaker diarization isolates foreground voices with 96% accuracy.",
        source_type="mic_user",
        confidence=0.99,
    )
    db.add(t2)
    db.add(t3)

    d3 = Decision(
        session_id=s2.id,
        decision_text="Target sub-100ms response generation for Copilot suggestions.",
        status="CONFIRMED",
        supporting_excerpt="Validated during WebRTC stress test.",
    )
    db.add(d3)

    # ── Meeting 3: Upcoming Tomorrow ──
    s3 = Session(
        owner_id=user.id,
        title="Enterprise Security & Compliance Sign-off",
        mode="group",
        objective="Review end-to-end encryption in transit and rest; obtain sign-off for enterprise deployment.",
        desired_outcome="Approved security checklist and signed authorization.",
        important_questions="Where are customer transcription encryption keys stored and managed?",
        audience="Chief Information Security Officer (CISO), Compliance Director",
        status="active",
        platform_source="google_meet",
        external_meeting_url="https://meet.google.com/sec-signoff-2026",
        created_at=tomorrow,
    )
    db.add(s3)

    # ── Meeting 4: Upcoming in 3 Days ──
    s4 = Session(
        owner_id=user.id,
        title="Global Product Strategy & Executive Alignment",
        mode="group",
        objective="Align on H2 AI Copilot rollout across North America and APAC enterprise clients.",
        desired_outcome="Executive roadmap sign-off and cross-team commitment.",
        important_questions="What is the projected ROI for enterprise sales teams using live Copilot answers?",
        audience="Executive VP, Product Directors, Regional Leads",
        status="active",
        platform_source="google_meet",
        external_meeting_url="https://meet.google.com/prod-strat-sync",
        created_at=three_days_later,
    )
    db.add(s4)

    await db.commit()
    logger.info("Successfully seeded demo meetings for %s into database.", user.email)

    try:
        await VectorDatabaseService.vectorize_entire_session(s1.id, user.id, db)
        await VectorDatabaseService.vectorize_entire_session(s2.id, user.id, db)
    except Exception as e:
        logger.warning("Auto-vectorization on seed: %s", e)


async def seed_demo_data(db: AsyncSession):
    """
    Seeds rich demo meetings with transcripts, speaker diarization, decisions,
    and vector memory into the database for demo@copilot.ai.
    """
    # 1. Check or create demo user
    res = await db.execute(select(User).where(User.email == "demo@copilot.ai"))
    user = res.scalar_one_or_none()
    if not user:
        user = User(
            email="demo@copilot.ai",
            display_name="Demo Host",
            hashed_password=hash_password("demopassword123"),
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Created demo user demo@copilot.ai")

    await seed_demo_data_for_user(db, user)
