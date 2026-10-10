"""
Comprehensive integration tests for Meeting Integrations & Clarivue AI Intelligence Layer.
Run with: pytest backend/tests/test_integrations.py -v
"""
import io
import os
import sys
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_FILE = "./test_integrations.db"
if os.path.exists(TEST_DB_FILE):
    try:
        os.remove(TEST_DB_FILE)
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
os.environ["APP_SECRET_KEY"] = "test-secret-key-32-chars-minimum-x"
os.environ["GROQ_API_KEY"] = ""

from app.main import app
from app.db.database import create_tables


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    await create_tables()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client):
    email = "integration_tester@example.com"
    pwd = "securepassword123"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "display_name": "Integration Tester",
        "password": pwd
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": pwd
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.mark.asyncio
async def test_get_integrations_list(auth_client):
    """Verify all 3 platform cards return with honest status."""
    resp = await auth_client.get("/api/v1/integrations")
    assert resp.status_code == 200
    cards = resp.json()
    assert len(cards) == 3

    providers = {c["provider"]: c for c in cards}
    assert "google_meet" in providers
    assert "zoom" in providers
    assert "microsoft_teams" in providers

    for provider, card in providers.items():
        assert card["name"] in ["Google Meet", "Zoom", "Microsoft Teams"]
        assert len(card["capabilities"]) > 0
        # Honest state checks
        assert card["status"] in ["Not Connected", "Configuration Required", "Connected", "Sync Error", "Coming Soon"]


@pytest.mark.asyncio
async def test_validate_meeting_urls(auth_client):
    """Test URL format validation across Google Meet, Zoom, and MS Teams."""
    # Google Meet
    r1 = await auth_client.post("/api/v1/transcripts/validate-url", json={
        "url": "https://meet.google.com/abc-defg-hij"
    })
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["valid"] is True
    assert data1["provider"] == "google_meet"
    assert data1["meeting_id"] == "abc-defg-hij"

    # Zoom
    r2 = await auth_client.post("/api/v1/transcripts/validate-url", json={
        "url": "https://zoom.us/j/9876543210?pwd=abc"
    })
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["valid"] is True
    assert data2["provider"] == "zoom"
    assert data2["meeting_id"] == "9876543210"

    # MS Teams
    r3 = await auth_client.post("/api/v1/transcripts/validate-url", json={
        "url": "https://teams.microsoft.com/l/meetup-join/19%3ameeting_xyz%40thread.v2/0"
    })
    assert r3.status_code == 200
    data3 = r3.json()
    assert data3["valid"] is True
    assert data3["provider"] == "microsoft_teams"

    # Invalid URL
    r4 = await auth_client.post("/api/v1/transcripts/validate-url", json={
        "url": "https://unknownsite.org/meeting/123"
    })
    assert r4.status_code == 200
    data4 = r4.json()
    assert data4["valid"] is False
    assert "Unrecognized" in data4["reason"]


@pytest.mark.asyncio
async def test_import_pasted_transcript(auth_client):
    """Option A: Test importing pasted transcript notes."""
    transcript_text = """
Alice [00:01]: Welcome team to our architecture review.
Bob [00:03]: We decided to migrate our caching layer to Redis cluster.
Alice [00:06]: Confirmed. Bob, can you benchmark redis latency by Friday?
Bob [00:09]: Yes, I will deliver the benchmark numbers by Friday afternoon.
"""
    resp = await auth_client.post("/api/v1/transcripts/import", json={
        "title": "Architecture Review Sync",
        "objective": "tech_review",
        "raw_text": transcript_text,
        "source_type": "paste",
        "platform_source": "manual"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["session_id"] is not None
    assert data["title"] == "Architecture Review Sync"
    assert data["segments_count"] >= 3
    assert data["status"] == "imported"


@pytest.mark.asyncio
async def test_upload_transcript_file_txt(auth_client):
    """Option B: Test uploading a text file transcript."""
    content = b"Speaker 1: Hello world\nSpeaker 2: We agreed on the timeline."
    files = {"file": ("test_transcript.txt", io.BytesIO(content), "text/plain")}
    resp = await auth_client.post("/api/v1/transcripts/upload-file", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "test_transcript.txt"
    assert data["file_type"] == "txt"
    assert "We agreed on the timeline" in data["text"]


@pytest.mark.asyncio
async def test_upload_unsupported_file_fails(auth_client):
    """Option B: Test uploading unsupported file format returns 400 error."""
    content = b"Binary exe content"
    files = {"file": ("malicious.exe", io.BytesIO(content), "application/octet-stream")}
    resp = await auth_client.post("/api/v1/transcripts/upload-file", files=files)
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_full_conversation_analysis_pipeline(auth_client):
    """Option A -> Clarivue Intelligence Layer analysis test."""
    # 1. Import
    transcript_text = """
Marcus [00:01]: Welcome everyone to the client sync.
Elena [00:04]: We've decided to proceed with the Enterprise plan starting next month.
Marcus [00:07]: That is confirmed. We agreed to provide 24/7 dedicated support.
Elena [00:11]: Marcus, please email the updated Service Level Agreement by Thursday.
Marcus [00:15]: Absolutely, I will have the SLA contract delivered by Thursday 5 PM.
"""
    import_resp = await auth_client.post("/api/v1/transcripts/import", json={
        "title": "Client Enterprise Sync",
        "objective": "sales_demo",
        "raw_text": transcript_text,
        "source_type": "paste"
    })
    session_id = import_resp.json()["session_id"]

    # 2. Analyze
    analyze_resp = await auth_client.post(f"/api/v1/sessions/{session_id}/analyze")
    assert analyze_resp.status_code == 200
    analysis = analyze_resp.json()

    assert analysis["session_id"] == session_id
    assert analysis["session_title"] == "Client Enterprise Sync"

    # Verify Intelligence Layer components
    assert "summary" in analysis
    assert "executive_summary" in analysis["summary"]
    assert len(analysis["summary"]["key_points"]) > 0

    assert "decisions" in analysis
    assert len(analysis["decisions"]) >= 1
    # Check decision content
    first_decision = analysis["decisions"][0]
    assert "decision_text" in first_decision
    assert first_decision["status"] in ["CONFIRMED", "PROPOSED", "PENDING_CONFIRMATION", "PENDING_REVIEW", "REJECTED"]

    assert "action_items" in analysis
    assert len(analysis["action_items"]) >= 1

    assert "suggestions" in analysis
    assert len(analysis["suggestions"]) >= 1

    assert "insights" in analysis
    assert len(analysis["insights"]) >= 1


@pytest.mark.asyncio
async def test_decision_ledger_crud(auth_client):
    """Test Decision Ledger create, list, and update endpoints."""
    # Create session first
    s_resp = await auth_client.post("/api/v1/sessions", json={
        "title": "Decisions Test Session",
        "objective": "tech_review"
    })
    session_id = s_resp.json()["id"]

    # 1. Create Decision
    d_create_resp = await auth_client.post(f"/api/v1/sessions/{session_id}/decisions", json={
        "decision_text": "Approved migration to distributed cache.",
        "supporting_excerpt": "Bob: We decided to approve the distributed cache.",
        "status": "CONFIRMED",
        "category": "architecture"
    })
    assert d_create_resp.status_code == 201
    created_d = d_create_resp.json()
    d_id = created_d["id"]
    assert created_d["decision_text"] == "Approved migration to distributed cache."
    assert created_d["status"] == "CONFIRMED"

    # 2. List Decisions
    d_list_resp = await auth_client.get(f"/api/v1/sessions/{session_id}/decisions")
    assert d_list_resp.status_code == 200
    decisions = d_list_resp.json()
    assert len(decisions) >= 1
    assert any(d["id"] == d_id for d in decisions)

    # 3. Update Decision
    d_update_resp = await auth_client.patch(f"/api/v1/sessions/{session_id}/decisions/{d_id}", json={
        "status": "SUPERSEDED",
        "decision_text": "Updated decision text"
    })
    assert d_update_resp.status_code == 200
    updated_d = d_update_resp.json()
    assert updated_d["status"] == "SUPERSEDED"
    assert updated_d["decision_text"] == "Updated decision text"


@pytest.mark.asyncio
async def test_connect_and_disconnect_integration(auth_client):
    """Test connecting and disconnecting an integration connection."""
    # Connect Google Meet
    conn_resp = await auth_client.post("/api/v1/integrations/google_meet/connect", json={
        "auth_code": "test_auth_code_123",
        "account_email": "engineer@workspace.com",
        "account_id": "google_12345"
    })
    assert conn_resp.status_code == 200
    assert conn_resp.json()["status"] == "Connected"

    # Verify status changed in list
    list_resp = await auth_client.get("/api/v1/integrations")
    gm_card = next(c for c in list_resp.json() if c["provider"] == "google_meet")
    assert gm_card["status"] == "Connected"
    assert gm_card["connected_account"] == "engineer@workspace.com"

    # Disconnect
    dis_resp = await auth_client.post("/api/v1/integrations/google_meet/disconnect")
    assert dis_resp.status_code == 200
    assert dis_resp.json()["success"] is True

    # Verify status changed back in integrations list
    list_resp2 = await auth_client.get("/api/v1/integrations")
    gm_card2 = next(c for c in list_resp2.json() if c["provider"] == "google_meet")
    assert gm_card2["status"] in ["Not Connected", "Configuration Required"]


@pytest.mark.asyncio
async def test_oauth_csrf_protection_and_callback(auth_client, monkeypatch):
    """Verify anti-CSRF OAuth state generation and callback verification."""
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "mock_google_id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "mock_google_secret")

    # 1. Get OAuth auth URL with signed state
    auth_url_resp = await auth_client.get("/api/v1/integrations/google_meet/auth-url")
    assert auth_url_resp.status_code == 200
    data = auth_url_resp.json()
    assert data["configured"] is True
    assert "auth_url" in data
    assert "state" in data
    valid_state = data["state"]

    # 2. Callback with invalid state redirects with error (CSRF protection)
    bad_cb = await auth_client.get(
        "/api/v1/integrations/google_meet/callback?code=testcode123&state=tampered_or_invalid_state",
        follow_redirects=False
    )
    assert bad_cb.status_code in [302, 307]
    assert "invalid_oauth_state" in bad_cb.headers.get("location", "")

    # 3. Callback with valid state redirects with authorized
    good_cb = await auth_client.get(
        f"/api/v1/integrations/google_meet/callback?code=mock_oauth_code&state={valid_state}",
        follow_redirects=False
    )
    assert good_cb.status_code in [302, 307]
    assert "status=authorized" in good_cb.headers.get("location", "")


@pytest.mark.asyncio
async def test_smart_suggestion_regeneration(auth_client):
    """Test smart suggestion regeneration endpoint."""
    s_resp = await auth_client.post("/api/v1/sessions", json={
        "title": "Suggestion Session",
        "objective": "sales_demo",
        "meeting_tone": "persuasive"
    })
    session_id = s_resp.json()["id"]

    regen_resp = await auth_client.post(
        f"/api/v1/sessions/{session_id}/suggestions/regenerate",
        json={
            "context_hint": "Client is worried about SLA pricing",
            "desired_tone": "persuasive"
        }
    )
    assert regen_resp.status_code == 200
    sug = regen_resp.json()
    assert "suggestion_text" in sug
    assert "category" in sug
    assert "why_relevant" in sug


@pytest.mark.asyncio
async def test_session_summary_export_markdown_and_text(auth_client):
    """Test session export in Markdown and Text formats."""
    # Create session with transcript and summary
    s_resp = await auth_client.post("/api/v1/sessions", json={
        "title": "Export Test Session",
        "objective": "Quarterly Business Review"
    })
    session_id = s_resp.json()["id"]

    await auth_client.post(f"/api/v1/sessions/{session_id}/transcript", json={
        "speaker_label": "CEO",
        "text": "We grew 45% YoY and reached profitability."
    })
    await auth_client.post(f"/api/v1/sessions/{session_id}/summary")

    # 1. Export as Markdown
    md_resp = await auth_client.get(f"/api/v1/sessions/{session_id}/export?format=markdown")
    assert md_resp.status_code == 200
    assert "text/markdown" in md_resp.headers.get("content-type", "")
    assert "Export Test Session" in md_resp.text
    assert "Executive Summary" in md_resp.text

    # 2. Export as Text
    txt_resp = await auth_client.get(f"/api/v1/sessions/{session_id}/export?format=text")
    assert txt_resp.status_code == 200
    assert "text/plain" in txt_resp.headers.get("content-type", "")
    assert "Export Test Session" in txt_resp.text


@pytest.mark.asyncio
async def test_session_cascade_deletion(auth_client):
    """Test session deletion cascades and removes session."""
    s_resp = await auth_client.post("/api/v1/sessions", json={
        "title": "Temporary Session",
        "objective": "To be deleted"
    })
    session_id = s_resp.json()["id"]

    # Add child items
    await auth_client.post(f"/api/v1/sessions/{session_id}/transcript", json={
        "speaker_label": "User",
        "text": "Some text to be cascade deleted."
    })
    await auth_client.post(f"/api/v1/sessions/{session_id}/actions", json={
        "description": "Follow up task"
    })

    # Delete session
    del_resp = await auth_client.delete(f"/api/v1/sessions/{session_id}")
    assert del_resp.status_code == 204

    # Verify session is gone (soft-deleted / inaccessible)
    get_resp = await auth_client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code in [404, 410]
