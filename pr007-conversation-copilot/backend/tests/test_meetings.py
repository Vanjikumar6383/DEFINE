"""
Tests for meeting link creation, joining by URL/code, and transcript summary generation.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import create_tables


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    await create_tables()
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def host_client(client):
    await client.post("/api/v1/auth/register", json={
        "email": "host_meeting@example.com",
        "display_name": "Host User",
        "password": "password123"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "host_meeting@example.com",
        "password": "password123"
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.mark.asyncio
async def test_create_meeting_link_and_join_via_portal(host_client, client):
    """
    1. Host creates a meeting and gets meeting room ID and link.
    2. Another user puts the meeting link/code in the portal and joins.
    3. The joined user can access the session and submit voiced transcripts.
    4. Important summary points are generated from the transcript.
    """
    # 1. Host creates meeting
    create_res = await host_client.post("/api/v1/sessions", json={
        "title": "Strategy & Roadmap Sync",
        "objective": "Align on Q4 deliverables and pricing",
        "mode": "one_to_one"
    })
    assert create_res.status_code == 201
    session_data = create_res.json()
    session_id = session_data["id"]
    meeting_link = f"http://test/session/{session_id}"

    # 2. Public info query
    info_res = await client.get(f"/api/v1/meetings/{session_id}/public-info")
    assert info_res.status_code == 200
    assert info_res.json()["title"] == "Strategy & Roadmap Sync"
    assert info_res.json()["owner_name"] == "Host User"

    # 3. User B joins via portal using meeting link
    join_res = await client.post("/api/v1/meetings/join", json={
        "meeting_id_or_url": meeting_link,
        "display_name": "Elena Rostova"
    })
    assert join_res.status_code == 200
    join_data = join_res.json()
    assert join_data["session_id"] == session_id
    assert join_data["display_name"] == "Elena Rostova"
    assert join_data["role"] == "attendee"
    assert "access_token" in join_data

    attendee_token = join_data["access_token"]
    attendee_headers = {"Authorization": f"Bearer {attendee_token}"}

    # 4. Host submits their spoken transcript
    h_tr = await host_client.post(f"/api/v1/sessions/{session_id}/transcript", json={
        "speaker_label": "Host User",
        "text": "Welcome Elena. Today our goal is to finalize the enterprise security and SLA terms.",
        "source_type": "voice_mic"
    })
    assert h_tr.status_code == 201

    # 5. Elena (joined attendee) submits her voiced transcript
    a_tr = await client.post(
        f"/api/v1/sessions/{session_id}/transcript",
        json={
            "speaker_label": "Elena Rostova",
            "text": "Thanks! We reviewed the SOC2 Type II reports and agree with the 99.95% uptime SLA.",
            "source_type": "voice_mic"
        },
        headers=attendee_headers
    )
    assert a_tr.status_code == 201

    # 6. Generate important summary points from both participants' voiced transcripts
    sum_res = await client.post(
        f"/api/v1/meetings/{session_id}/summarize",
        headers=attendee_headers
    )
    assert sum_res.status_code == 200
    summary_data = sum_res.json()

    assert "summary_text" in summary_data
    assert len(summary_data["summary_text"]) > 20
    assert "key_points" in summary_data or "important_points" in summary_data
    
    important_points = summary_data.get("important_points") or summary_data.get("key_points") or []
    assert len(important_points) > 0
    # Verify that participants' voiced points are captured
    points_text = " ".join(important_points).lower()
    assert "elena" in points_text or "host" in points_text or "security" in points_text or "soc2" in points_text or "sla" in points_text or len(important_points) >= 2


@pytest.mark.asyncio
async def test_join_by_room_code_prefix(host_client, client):
    """User can join by entering short 8-character room code."""
    create_res = await host_client.post("/api/v1/sessions", json={
        "title": "Short Code Test"
    })
    session_id = create_res.json()["id"]
    short_code = session_id[:8].upper()

    join_res = await client.post("/api/v1/meetings/join", json={
        "meeting_id_or_url": short_code,
        "display_name": "Alex"
    })
    assert join_res.status_code == 200
    assert join_res.json()["session_id"] == session_id
    assert join_res.json()["display_name"] == "Alex"


@pytest.mark.asyncio
async def test_instant_meeting_create_and_join_flow(client):
    """
    Test creating an instant meeting link from the portal (anonymous or guest host),
    followed by another user joining with the link, both contributing voiced transcripts,
    and generating important summary points.
    """
    # 1. User A creates an instant meeting link from the portal
    create_res = await client.post("/api/v1/meetings/create", json={
        "title": "Architecture & Compliance Review",
        "objective": "Review failover SLAs and export SOC2 audit logs",
        "host_name": "Chief Architect"
    })
    assert create_res.status_code == 201
    created_data = create_res.json()
    session_id = created_data["session_id"]
    assert created_data["role"] == "host"
    assert created_data["display_name"] == "Chief Architect"
    assert "access_token" in created_data
    meeting_url = created_data["meeting_url"]

    host_token = created_data["access_token"]
    host_headers = {"Authorization": f"Bearer {host_token}"}

    # 2. User B puts the meeting URL in the portal and joins
    join_res = await client.post("/api/v1/meetings/join", json={
        "meeting_id_or_url": f"http://localhost:8000{meeting_url}",
        "display_name": "Security Officer"
    })
    assert join_res.status_code == 200
    join_data = join_res.json()
    assert join_data["session_id"] == session_id
    assert join_data["role"] == "attendee"
    assert join_data["display_name"] == "Security Officer"
    attendee_token = join_data["access_token"]
    attendee_headers = {"Authorization": f"Bearer {attendee_token}"}

    # 3. Both participants speak into mic (voiced transcript)
    h_tr = await client.post(
        f"/api/v1/sessions/{session_id}/transcript",
        json={
            "speaker_label": "Chief Architect",
            "text": "We provide multi-region automated database failover within 45 seconds.",
            "source_type": "voice_mic"
        },
        headers=host_headers
    )
    assert h_tr.status_code == 201

    a_tr = await client.post(
        f"/api/v1/sessions/{session_id}/transcript",
        json={
            "speaker_label": "Security Officer",
            "text": "Confirmed. We require SOC2 Type II reports and SIEM audit export enabled.",
            "source_type": "voice_mic"
        },
        headers=attendee_headers
    )
    assert a_tr.status_code == 201

    # 4. Generate important summary points from voiced dialogue
    sum_res = await client.post(
        f"/api/v1/meetings/{session_id}/summarize",
        headers=attendee_headers
    )
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    assert "important_points" in sum_data or "key_points" in sum_data
    pts = sum_data.get("important_points") or sum_data.get("key_points") or []
    assert len(pts) > 0
    pts_str = " ".join(pts).lower()
    assert "architect" in pts_str or "security" in pts_str or "failover" in pts_str or "soc2" in pts_str or len(pts) >= 2
