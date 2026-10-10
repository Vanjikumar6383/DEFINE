import math
import re
import hashlib
import json
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.models import MeetingSemanticMemory, Session, User, Decision, ActionItem, Insight, TranscriptSegment


class VectorDatabaseService:
    """
    High-performance Semantic Vector Database and Relational Memory Engine for Nimad Copilot.
    
    Provides:
    1. Dense vector embedding generation with semantic term hashing and continuous space normalization.
    2. Cosine similarity vector search and nearest-neighbor semantic retrieval across past meetings.
    3. Multi-speaker semantic relationship linking (tracks what each on-screen attendee and host stated/decided).
    4. Semantic Memory Graph Construction (connects related decisions and points across meeting history).
    """

    DEFAULT_DIM: int = 128
    SIMILARITY_THRESHOLD: float = 0.62  # Semantic link threshold

    @classmethod
    def generate_embedding(cls, text: str, dim: int = DEFAULT_DIM) -> list[float]:
        """
        Generates a normalized dense vector embedding for semantic text representation.
        Uses subword term frequency hashing, semantic concept clustering, and L2 unit-norm sphere projection.
        """
        if not text or not text.strip():
            return [0.0] * dim

        clean = re.sub(r"[^\w\s]", " ", text.lower()).strip()
        words = [w for w in clean.split() if len(w) > 1]
        if not words:
            return [0.0] * dim

        vector = [0.0] * dim

        # Semantic concept clusters to boost semantic relationships
        CONCEPT_CLUSTERS = {
            "database_infra": ["postgres", "postgresql", "sql", "database", "failover", "replication", "cluster", "uptime", "sla", "latency", "storage", "cloud", "gcp", "aws", "server"],
            "security_compliance": ["soc2", "soc", "audit", "siem", "splunk", "security", "compliance", "log", "logs", "encryption", "policy", "regulatory"],
            "procurement_biz": ["procurement", "vendor", "contract", "pilot", "budget", "pricing", "cost", "marketing", "campaign", "finance", "approval", "terms"],
            "action_task": ["action", "task", "follow", "todo", "assigned", "decision", "approved", "deadline", "deliverable"]
        }

        # Project concept clusters
        for c_idx, (concept, terms) in enumerate(CONCEPT_CLUSTERS.items()):
            matches = sum(1 for w in words if any(t in w for t in terms))
            if matches > 0:
                base_slot = (c_idx * 20) % dim
                for offset in range(12):
                    slot = (base_slot + offset) % dim
                    vector[slot] += matches * 2.5

        # Subword and token hashing
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")
        for w in words:
            if len(w) >= 3:
                tokens.append(w[:3])
                tokens.append(w[-3:])

        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16)
            idx = h % dim
            vector[idx] += 1.0 + (len(token) * 0.1)

        # L2 Normalization onto unit sphere
        squared_sum = sum(x * x for x in vector)
        norm = math.sqrt(squared_sum)
        if norm > 1e-9:
            vector = [round(x / norm, 6) for x in vector]
        else:
            vector = [0.0] * dim

        return vector

    @classmethod
    def cosine_similarity(cls, vec_a: list[float], vec_b: list[float]) -> float:
        """
        Calculates cosine similarity between two dense embedding vectors:
        CosineSim(A, B) = (A . B) / (||A|| * ||B||)
        """
        if not vec_a or not vec_b:
            return 0.0
        
        min_len = min(len(vec_a), len(vec_b))
        if min_len == 0:
            return 0.0

        dot_product = sum(vec_a[i] * vec_b[i] for i in range(min_len))
        norm_a = math.sqrt(sum(vec_a[i] * vec_a[i] for i in range(min_len)))
        norm_b = math.sqrt(sum(vec_b[i] * vec_b[i] for i in range(min_len)))

        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0

        sim = dot_product / (norm_a * norm_b)
        return max(0.0, min(1.0, round(sim, 5)))

    @classmethod
    async def index_semantic_memory(
        cls,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        category: str,
        speaker_label: str,
        speaker_role: str,
        content: str,
        semantic_context: str | None = None,
        semantic_tags: list[str] | None = None,
    ) -> MeetingSemanticMemory:
        """
        Embeds, stores, and links a semantic memory item in the vector database.
        Automatically links against all previous meeting memories with semantic similarity.
        """
        embedding = cls.generate_embedding(f"{speaker_label}: {content} Context: {semantic_context or ''}")

        # Search existing memories for this user to build semantic relations graph
        stmt = select(MeetingSemanticMemory).where(
            and_(
                MeetingSemanticMemory.user_id == user_id,
                MeetingSemanticMemory.session_id != session_id
            )
        )
        existing_result = await db.execute(stmt)
        existing_memories = existing_result.scalars().all()

        related_ids = []
        similarity_graph = {}

        for past_mem in existing_memories:
            if past_mem.embedding:
                sim = cls.cosine_similarity(embedding, past_mem.embedding)
                if sim >= cls.SIMILARITY_THRESHOLD:
                    related_ids.append(past_mem.id)
                    similarity_graph[past_mem.id] = sim

                    # Bi-directionally update past memory's relational graph
                    past_graph = dict(past_mem.similarity_graph or {})
                    past_related = list(past_mem.related_memory_ids or [])
                    # We will append current memory ID after creation

        memory_item = MeetingSemanticMemory(
            session_id=session_id,
            user_id=user_id,
            category=category,
            speaker_label=speaker_label,
            speaker_role=speaker_role,
            content=content,
            semantic_context=semantic_context,
            embedding=embedding,
            embedding_dim=len(embedding),
            semantic_tags=semantic_tags or [],
            related_memory_ids=related_ids,
            similarity_graph=similarity_graph
        )
        db.add(memory_item)
        await db.commit()
        await db.refresh(memory_item)

        # Update reciprocal relations in previous memories
        for past_mem in existing_memories:
            if past_mem.id in similarity_graph:
                past_related = list(past_mem.related_memory_ids or [])
                if memory_item.id not in past_related:
                    past_related.append(memory_item.id)
                    past_mem.related_memory_ids = past_related
                past_graph = dict(past_mem.similarity_graph or {})
                past_graph[memory_item.id] = similarity_graph[past_mem.id]
                past_mem.similarity_graph = past_graph
                db.add(past_mem)

        await db.commit()
        return memory_item

    @classmethod
    async def vectorize_entire_session(cls, db: AsyncSession, session_id: str, user_id: str) -> dict[str, Any]:
        """
        Extracts and vectorizes all important takeaways from a completed or ongoing session:
        1. Decisions
        2. Action Deliverables
        3. Q&A and Easy Answers
        4. Speaker Utterances (attender on screen and host)
        5. Session Executive Objectives
        """
        sess_stmt = select(Session).where(Session.id == session_id)
        sess_res = await db.execute(sess_stmt)
        session = sess_res.scalar_one_or_none()
        if not session:
            return {"indexed_count": 0, "status": "session_not_found"}

        indexed_count = 0
        context_prefix = f"Meeting: {session.title} | Objective: {session.objective or 'General'}"

        # 1. Vectorize Decisions
        dec_stmt = select(Decision).where(Decision.session_id == session_id)
        dec_res = await db.execute(dec_stmt)
        decisions = dec_res.scalars().all()
        for d in decisions:
            await cls.index_semantic_memory(
                db=db,
                session_id=session_id,
                user_id=user_id,
                category="key_decision",
                speaker_label="Consensus / Team Decision",
                speaker_role="consensus",
                content=d.decision_text,
                semantic_context=f"{context_prefix} | Excerpt: {d.supporting_excerpt or ''}",
                semantic_tags=["decision", d.category or "consensus", d.status]
            )
            indexed_count += 1

        # 2. Vectorize Action Items
        act_stmt = select(ActionItem).where(ActionItem.session_id == session_id)
        act_res = await db.execute(act_stmt)
        actions = act_res.scalars().all()
        for a in actions:
            await cls.index_semantic_memory(
                db=db,
                session_id=session_id,
                user_id=user_id,
                category="action_item",
                speaker_label=a.owner or "Assigned Owner",
                speaker_role="action_owner",
                content=f"Task: {a.description} (Due: {a.due_date or 'TBD'})",
                semantic_context=f"{context_prefix} | Owner: {a.owner or 'Unassigned'}",
                semantic_tags=["action_item", a.priority or "medium", a.status]
            )
            indexed_count += 1

        # 3. Vectorize Q&A Insights
        ins_stmt = select(Insight).where(
            and_(Insight.session_id == session_id, Insight.type == "response_suggestion")
        )
        ins_res = await db.execute(ins_stmt)
        insights = ins_res.scalars().all()
        for ins in insights:
            ev = ins.evidence_refs or {}
            speaker = ev.get("speaker", "Attender")
            question = ev.get("question", ins.content)
            easy_answer = ev.get("easy_answer", "")
            await cls.index_semantic_memory(
                db=db,
                session_id=session_id,
                user_id=user_id,
                category="qa_pair",
                speaker_label=speaker,
                speaker_role="screen_attender" if "host" not in speaker.lower() else "host",
                content=f"Question: {question}\nAnswer: {easy_answer}",
                semantic_context=context_prefix,
                semantic_tags=["qa", "easy_answer", speaker]
            )
            indexed_count += 1

        # 4. Vectorize Significant Speaker Utterances (Diarized on-screen & host speech)
        trans_stmt = select(TranscriptSegment).where(TranscriptSegment.session_id == session_id)
        trans_res = await db.execute(trans_stmt)
        transcripts = trans_res.scalars().all()
        for t in transcripts:
            # Index substantial statements (> 25 characters)
            if len(t.text.strip()) > 25:
                await cls.index_semantic_memory(
                    db=db,
                    session_id=session_id,
                    user_id=user_id,
                    category="speaker_statement",
                    speaker_label=t.speaker_label or "Attender",
                    speaker_role=t.speaker_role or "screen_attender",
                    content=t.text,
                    semantic_context=f"{context_prefix} at timestamp {t.timestamp_start or 0.0}s",
                    semantic_tags=["transcript", t.speaker_label or "Attender", t.source_type]
                )
                indexed_count += 1

        return {
            "session_id": session_id,
            "indexed_count": indexed_count,
            "status": "success"
        }

    @classmethod
    async def semantic_search(
        cls,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: int = 6,
        category: str | None = None,
        speaker_filter: str | None = None,
        exclude_session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Searches all past meeting memories using vector cosine similarity.
        Returns matching memories enriched with speaker names, session titles, and similarity scores.
        """
        query_embedding = cls.generate_embedding(query)

        conditions = [MeetingSemanticMemory.user_id == user_id]
        if category:
            conditions.append(MeetingSemanticMemory.category == category)
        if speaker_filter:
            conditions.append(MeetingSemanticMemory.speaker_label.ilike(f"%{speaker_filter}%"))
        if exclude_session_id:
            conditions.append(MeetingSemanticMemory.session_id != exclude_session_id)

        stmt = select(MeetingSemanticMemory, Session.title, Session.created_at).join(
            Session, MeetingSemanticMemory.session_id == Session.id
        ).where(and_(*conditions))

        result = await db.execute(stmt)
        rows = result.all()

        scored_items = []
        for mem, session_title, session_date in rows:
            if mem.embedding:
                sim = cls.cosine_similarity(query_embedding, mem.embedding)
                scored_items.append({
                    "id": mem.id,
                    "session_id": mem.session_id,
                    "session_title": session_title,
                    "session_date": session_date.strftime("%Y-%m-%d %H:%M") if session_date else "",
                    "category": mem.category,
                    "speaker_label": mem.speaker_label,
                    "speaker_role": mem.speaker_role,
                    "content": mem.content,
                    "semantic_context": mem.semantic_context,
                    "semantic_tags": mem.semantic_tags or [],
                    "similarity": sim,
                    "related_memory_ids": mem.related_memory_ids or [],
                    "similarity_graph": mem.similarity_graph or {}
                })

        # Sort descending by cosine similarity score
        scored_items.sort(key=lambda x: x["similarity"], reverse=True)
        return scored_items[:top_k]
