import logging
import hmac
import hashlib
import time
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.config import get_settings
from app.models.models import IntegrationConnection
from app.services.integrations.google_meet_service import google_meet_service
from app.services.integrations.zoom_service import zoom_service
from app.services.integrations.microsoft_teams_service import microsoft_teams_service

logger = logging.getLogger(__name__)
settings = get_settings()


class IntegrationManager:
    providers = {
        "google_meet": google_meet_service,
        "zoom": zoom_service,
        "microsoft_teams": microsoft_teams_service,
    }

    def generate_oauth_state(self, user_id: str, provider: str) -> str:
        timestamp = str(int(time.time()))
        payload = f"{user_id}:{provider}:{timestamp}"
        sig = hmac.new(settings.APP_SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload}:{sig}"

    def verify_oauth_state(self, state: str, provider: str, max_age_seconds: int = 600) -> Optional[str]:
        try:
            parts = state.split(":")
            if len(parts) != 4:
                return None
            user_id, p_id, timestamp_str, sig = parts
            if p_id != provider:
                return None
            payload = f"{user_id}:{p_id}:{timestamp_str}"
            expected_sig = hmac.new(settings.APP_SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            if time.time() - int(timestamp_str) > max_age_seconds:
                return None
            return user_id
        except Exception:
            return None

    async def get_all_cards(self, user_id: str, db: AsyncSession) -> list[dict]:
        cards = []
        for provider_id, service in self.providers.items():
            info = await service.get_status_info(user_id, db)
            cards.append(info)
        return cards

    async def get_card(self, provider_id: str, user_id: str, db: AsyncSession) -> Optional[dict]:
        service = self.providers.get(provider_id)
        if not service:
            return None
        return await service.get_status_info(user_id, db)

    async def connect_provider(
        self,
        provider_id: str,
        user_id: str,
        payload: dict,
        db: AsyncSession,
    ) -> IntegrationConnection:
        service = self.providers.get(provider_id)
        if not service:
            raise ValueError(f"Unknown integration provider: {provider_id}")

        # Check existing connection
        conn = await service.get_connection(user_id, db)
        if not conn:
            conn = IntegrationConnection(
                user_id=user_id,
                provider=provider_id,
            )
            db.add(conn)

        # Update connection attributes
        conn.status = "connected"
        conn.account_email = payload.get("account_email") or f"{user_id[:8]}@{provider_id}.internal"
        conn.account_name = payload.get("account_name") or f"{service.name} User"
        if payload.get("client_id") and payload.get("client_secret"):
            conn.settings_json = {
                "client_id": payload["client_id"],
                "has_custom_credentials": True,
            }
        conn.last_error = None
        await db.commit()
        await db.refresh(conn)
        return conn

    async def disconnect_provider(self, provider_id: str, user_id: str, db: AsyncSession) -> bool:
        service = self.providers.get(provider_id)
        if not service:
            return False

        result = await db.execute(
            delete(IntegrationConnection).where(
                IntegrationConnection.user_id == user_id,
                IntegrationConnection.provider == provider_id,
            )
        )
        await db.commit()
        return result.rowcount > 0

    def detect_and_validate_meeting_url(self, url: str) -> dict:
        clean = (url or "").strip()
        if not clean:
            return {
                "valid": False,
                "is_valid": False,
                "provider": "unknown",
                "platform": "unknown",
                "meeting_id": None,
                "normalized_url": "",
                "notice": "No URL provided.",
                "reason": "No URL provided.",
            }

        if google_meet_service.validate_meeting_url(clean):
            meeting_id = google_meet_service.extract_meeting_code(clean)
            notice = "Recognized Google Meet URL. Note: A URL alone does not grant access to private meeting audio or transcripts. Use the Nimad Browser Extension or paste transcripts below."
            return {
                "valid": True,
                "is_valid": True,
                "provider": "google_meet",
                "platform": "google_meet",
                "meeting_id": meeting_id,
                "platform_name": "Google Meet",
                "normalized_url": clean,
                "notice": notice,
                "reason": notice,
            }

        if zoom_service.validate_meeting_url(clean):
            meeting_id = zoom_service.extract_meeting_id(clean)
            notice = "Recognized Zoom Meeting URL. Note: A URL alone does not grant access to private meeting audio or transcripts. Use the Nimad Companion or paste transcripts below."
            return {
                "valid": True,
                "is_valid": True,
                "provider": "zoom",
                "platform": "zoom",
                "meeting_id": meeting_id,
                "platform_name": "Zoom Meetings",
                "normalized_url": clean,
                "notice": notice,
                "reason": notice,
            }

        if microsoft_teams_service.validate_meeting_url(clean):
            meeting_id = microsoft_teams_service.extract_meeting_hint(clean)
            notice = "Recognized Microsoft Teams URL. Note: A URL alone does not grant access to private meeting audio or transcripts without Azure Graph authorization. Use manual paste or the companion extension."
            return {
                "valid": True,
                "is_valid": True,
                "provider": "microsoft_teams",
                "platform": "microsoft_teams",
                "meeting_id": meeting_id,
                "platform_name": "Microsoft Teams",
                "normalized_url": clean,
                "notice": notice,
                "reason": notice,
            }

        notice = "Unrecognized meeting platform URL format. Nimad supports Google Meet (meet.google.com), Zoom (zoom.us), and Microsoft Teams (teams.microsoft.com)."
        return {
            "valid": False,
            "is_valid": False,
            "provider": "unknown",
            "platform": "unknown",
            "meeting_id": None,
            "platform_name": "Unknown Meeting Platform",
            "normalized_url": clean,
            "notice": notice,
            "reason": notice,
        }


integration_manager = IntegrationManager()
