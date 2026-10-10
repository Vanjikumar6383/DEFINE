import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import create_tables
from app.services.vector_db_service import VectorDatabaseService


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    await create_tables()


@pytest.mark.asyncio
async def test_vector_embedding_math():
    # Test vector generation
    vec1 = VectorDatabaseService.generate_embedding("PostgreSQL failover architecture and SLA")
    vec2 = VectorDatabaseService.generate_embedding("PostgreSQL database replication and uptime guarantee")
    vec3 = VectorDatabaseService.generate_embedding("Marketing social media campaign budget")

    assert len(vec1) == 128
    assert len(vec2) == 128
    assert len(vec3) == 128

    sim_related = VectorDatabaseService.cosine_similarity(vec1, vec2)
    sim_unrelated = VectorDatabaseService.cosine_similarity(vec1, vec3)

    assert sim_related > sim_unrelated
    assert sim_related > 0.50
    assert sim_unrelated < 0.35


@pytest.mark.asyncio
async def test_multi_speaker_utterances_and_vector_search():
    import uuid
    uid = str(uuid.uuid4())[:8]
    test_email = f"vector_eng_{uid}@nimad.ai"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register & Login
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={"email": test_email, "display_name": "Senior Database Engineer", "password": "password123"}
        )
        assert reg_resp.status_code == 201
        
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": "password123"}
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Meeting 1 (Architecture Review)
        s1_resp = await client.post(
            "/api/v1/sessions",
            headers=headers,
            json={
                "title": "Enterprise Cloud Architecture & Failover Sync",
                "mode": "group",
                "objective": "Verify 99.9% uptime SLA and SOC2 compliance."
            }
        )
        assert s1_resp.status_code == 201
        s1_id = s1_resp.json()["id"]

        # 3. Ingest multi-speaker utterances for on-screen attendees and host
        # Utterance from on-screen attendee Sarah Chen (VP Engineering)
        u1_resp = await client.post(
            f"/api/v1/sessions/{s1_id}/speaker-utterance",
            headers=headers,
            json={
                "speaker_label": "Sarah Chen (VP Engineering)",
                "speaker_role": "screen_attender",
                "audio_channel": "screen_audio",
                "text": "What is your enterprise uptime guarantee, and how do you handle disaster recovery failovers in GCP?",
                "confidence": 0.98
            }
        )
        assert u1_resp.status_code == 201
        u1_data = u1_resp.json()
        assert u1_data["speaker_label"] == "Sarah Chen (VP Engineering)"
        assert u1_data["easy_answer"] is not None

        # Utterance from on-screen attendee David Miller (Procurement)
        u2_resp = await client.post(
            f"/api/v1/sessions/{s1_id}/speaker-utterance",
            headers=headers,
            json={
                "speaker_label": "David Miller (Procurement)",
                "speaker_role": "screen_attender",
                "audio_channel": "screen_audio",
                "text": "We require SOC2 Type II audit logs streamed directly into our Splunk SIEM for regulatory approval.",
                "confidence": 0.96
            }
        )
        assert u2_resp.status_code == 201

        # Host response
        u3_resp = await client.post(
            f"/api/v1/sessions/{s1_id}/speaker-utterance",
            headers=headers,
            json={
                "speaker_label": "You (Host)",
                "speaker_role": "host",
                "audio_channel": "user_mic",
                "text": "We provide active-passive failover with sub-30 second RTO and turnkey Splunk webhook streaming.",
                "confidence": 0.99
            }
        )
        assert u3_resp.status_code == 201

        # Add decision
        d_resp = await client.post(
            f"/api/v1/sessions/{s1_id}/decisions",
            headers=headers,
            json={
                "decision_text": "Approved 99.9% uptime SLA with Splunk connector for 30-day enterprise pilot.",
                "supporting_excerpt": "David Miller confirmed regulatory requirement satisfied.",
                "status": "CONFIRMED"
            }
        )
        assert d_resp.status_code == 201

        # 4. Trigger vectorization
        vec_resp = await client.post(
            f"/api/v1/sessions/{s1_id}/vectorize",
            headers=headers
        )
        assert vec_resp.status_code == 200
        assert vec_resp.json()["indexed_count"] >= 3

        # 5. Create Meeting 2 (Procurement & Security Follow-up)
        s2_resp = await client.post(
            "/api/v1/sessions",
            headers=headers,
            json={
                "title": "Vendor Contract & Security Assessment Review",
                "mode": "group",
                "objective": "Confirm pilot terms and SIEM logging."
            }
        )
        assert s2_resp.status_code == 201
        s2_id = s2_resp.json()["id"]

        # 6. Perform Vector Semantic Search from Meeting 2 querying Meeting 1
        search_resp = await client.post(
            "/api/v1/sessions/semantic-search",
            headers=headers,
            json={
                "query": "What did Sarah and David agree on regarding SOC2 SIEM logs and uptime SLA?",
                "top_k": 5
            }
        )
        assert search_resp.status_code == 200
        search_data = search_resp.json()
        assert search_data["results_count"] > 0

        # Verify semantic similarity matching and speaker attribution
        top_match = search_data["results"][0]
        assert top_match["session_id"] == s1_id
        assert top_match["similarity"] > 0.40
        assert top_match["speaker_label"] in ["Sarah Chen (VP Engineering)", "David Miller (Procurement)", "Consensus / Team Decision", "You (Host)"]

        # 7. Query specific speaker memory
        spk_search = await client.post(
            "/api/v1/sessions/semantic-search",
            headers=headers,
            json={
                "query": "Splunk audit logs",
                "speaker_filter": "David Miller"
            }
        )
        assert spk_search.status_code == 200
        assert len(spk_search.json()["results"]) > 0
        assert "David Miller" in spk_search.json()["results"][0]["speaker_label"]

        # 8. Check semantic memory endpoint for session 1
        mem_resp = await client.get(
            f"/api/v1/sessions/{s1_id}/semantic-memory",
            headers=headers
        )
        assert mem_resp.status_code == 200
        mems = mem_resp.json()
        assert len(mems) >= 3
