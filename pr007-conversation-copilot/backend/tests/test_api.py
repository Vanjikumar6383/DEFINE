"""
Basic tests for auth and sessions API.
Run with: pytest backend/tests/ -v
"""
import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_FILE = "./test_api.db"
if os.path.exists(TEST_DB_FILE):
    try:
        os.remove(TEST_DB_FILE)
    except Exception:
        pass

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
os.environ["APP_SECRET_KEY"] = "test-secret-key-32-chars-minimum-x"
os.environ["GROQ_API_KEY"] = ""

from app.main import app  # noqa: E402
from app.db.database import create_tables  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    await create_tables()
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client):
    """Returns a client with a valid JWT."""
    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "password123"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_and_login(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "display_name": "New User",
        "password": "securepassword"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newuser@example.com"

    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "newuser@example.com",
        "password": "securepassword"
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


@pytest.mark.asyncio
async def test_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "pwtest@example.com",
        "display_name": "PW Test",
        "password": "correctpassword"
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "pwtest@example.com",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_and_get_session(auth_client):
    resp = await auth_client.post("/api/v1/sessions", json={
        "title": "Test Session",
        "mode": "one_to_one",
        "objective": "Close the deal"
    })
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    get_resp = await auth_client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Test Session"


@pytest.mark.asyncio
async def test_session_isolation(client):
    """User A cannot read User B's session."""
    # Register user B
    await client.post("/api/v1/auth/register", json={
        "email": "userb@example.com",
        "display_name": "User B",
        "password": "passwordB"
    })
    b_resp = await client.post("/api/v1/auth/login", json={
        "email": "userb@example.com",
        "password": "passwordB"
    })
    b_token = b_resp.json()["access_token"]

    # User B creates a session
    create_resp = await client.post("/api/v1/sessions",
        json={"title": "B's private session"},
        headers={"Authorization": f"Bearer {b_token}"}
    )
    b_session_id = create_resp.json()["id"]

    # Register user A and try to access B's session
    await client.post("/api/v1/auth/register", json={
        "email": "usera_iso@example.com",
        "display_name": "User A",
        "password": "passwordA"
    })
    a_resp = await client.post("/api/v1/auth/login", json={
        "email": "usera_iso@example.com",
        "password": "passwordA"
    })
    a_token = a_resp.json()["access_token"]

    access_resp = await client.get(f"/api/v1/sessions/{b_session_id}",
        headers={"Authorization": f"Bearer {a_token}"}
    )
    assert access_resp.status_code == 403


@pytest.mark.asyncio
async def test_transcript_submission(auth_client):
    session = await auth_client.post("/api/v1/sessions", json={"title": "Transcript Test"})
    sid = session.json()["id"]

    t_resp = await auth_client.post(f"/api/v1/sessions/{sid}/transcript", json={
        "text": "The client mentioned they need delivery by end of October.",
        "speaker_label": "Client",
        "source_type": "paste"
    })
    assert t_resp.status_code == 201
    assert t_resp.json()["text"] == "The client mentioned they need delivery by end of October."


@pytest.mark.asyncio
async def test_delete_session(auth_client):
    session = await auth_client.post("/api/v1/sessions", json={"title": "To Delete"})
    sid = session.json()["id"]

    del_resp = await auth_client.delete(f"/api/v1/sessions/{sid}")
    assert del_resp.status_code == 204

    get_resp = await auth_client.get(f"/api/v1/sessions/{sid}")
    assert get_resp.status_code == 410


@pytest.mark.asyncio
async def test_multilingual_easy_answer(auth_client):
    session = await auth_client.post("/api/v1/sessions", json={"title": "Multilingual QA Test"})
    sid = session.json()["id"]

    # English QA
    en_resp = await auth_client.post(f"/api/v1/sessions/{sid}/qa/answer", json={
        "question": "What is the pricing tier for enterprise seats?",
        "speaker_label": "Attender Sarah"
    })
    assert en_resp.status_code == 200
    assert "pricing" in en_resp.json()["easy_answer"].lower() or len(en_resp.json()["easy_answer"]) > 10

    # Tamil QA
    ta_resp = await auth_client.post(f"/api/v1/sessions/{sid}/qa/answer", json={
        "question": "உங்கள் விலை அல்லது கட்டண முறை என்ன?",
        "speaker_label": "Attender Ramesh"
    })
    assert ta_resp.status_code == 200
    assert len(ta_resp.json()["easy_answer"]) > 10

    # Malayalam QA
    ml_resp = await auth_client.post(f"/api/v1/sessions/{sid}/qa/answer", json={
        "question": "സിസ്റ്റത്തിന്റെ സുരക്ഷ എങ്ങനെയാണ്?",
        "speaker_label": "Attender Vishnu"
    })
    assert ml_resp.status_code == 200
    assert len(ml_resp.json()["easy_answer"]) > 10


@pytest.mark.asyncio
async def test_transcript_question_auto_answer(auth_client):
    session = await auth_client.post("/api/v1/sessions", json={"title": "Auto Answer Test"})
    sid = session.json()["id"]

    # Submit Tamil question in transcript
    ta_tr = await auth_client.post(f"/api/v1/sessions/{sid}/transcript", json={
        "text": "பாதுகாப்பு விதிகள் மற்றும் SOC2 உள்ளதா?",
        "speaker_label": "Sarah Chen",
        "source_type": "audio"
    })
    assert ta_tr.status_code == 201
    assert ta_tr.json()["easy_answer"] is not None
    assert len(ta_tr.json()["easy_answer"]) > 10

