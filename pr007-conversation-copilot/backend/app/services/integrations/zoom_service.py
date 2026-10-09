import re
import urllib.parse
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.models.models import IntegrationConnection

settings = get_settings()

ZOOM_URL_REGEX = re.compile(
    r"^https?://(?:[a-zA-Z0-9-]+\.)?zoom\.us/(?:j|w|wc|my)/([0-9a-zA-Z._-]+)(?:\?.*)?$",
    re.IGNORECASE
)


class ZoomService:
    provider_id = "zoom"
    name = "Zoom"
    icon_type = "zoom"
    description = "Layer Nimad intelligence over your Zoom calls. Ingest cloud recording audio transcripts or stream live via desktop companion."

    capabilities = [
        "Cloud Recording Transcript Ingestion",
        "Webhook Post-Meeting Sync",
        "Meeting ID & URL Deep-Linking",
        "Zero WebRTC / Audio Hijack (Privacy-First)",
    ]

    def is_configured(self) -> bool:
        return bool(settings.ZOOM_CLIENT_ID and settings.ZOOM_CLIENT_SECRET)

    def validate_meeting_url(self, url: str) -> bool:
        if not url:
            return False
        return bool(ZOOM_URL_REGEX.match(url.strip()))

    def extract_meeting_id(self, url: str) -> Optional[str]:
        match = ZOOM_URL_REGEX.match(url.strip())
        return match.group(1) if match else None

    def get_auth_url(self, redirect_base: Optional[str] = None) -> Optional[str]:
        if not self.is_configured():
            return None
        base = redirect_base or settings.OAUTH_REDIRECT_BASE_URL
        redirect_uri = f"{base.rstrip('/')}/api/v1/integrations/zoom/callback"
        params = {
            "response_type": "code",
            "client_id": settings.ZOOM_CLIENT_ID,
            "redirect_uri": redirect_uri,
        }
        return f"https://zoom.us/oauth/authorize?{urllib.parse.urlencode(params)}"

    async def get_connection(self, user_id: str, db: AsyncSession) -> Optional[IntegrationConnection]:
        result = await db.execute(
            select(IntegrationConnection).where(
                IntegrationConnection.user_id == user_id,
                IntegrationConnection.provider == self.provider_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_status_info(self, user_id: str, db: AsyncSession) -> dict:
        conn = await self.get_connection(user_id, db)
        configured = self.is_configured()

        if conn and conn.status.lower() == "connected":
            status = "Connected"
        elif not configured:
            status = "Configuration Required"
        else:
            status = "Not Connected"

        return {
            "provider": self.provider_id,
            "name": self.name,
            "icon_type": self.icon_type,
            "description": self.description,
            "status": status,
            "is_configured": configured,
            "account_email": conn.account_email if conn else None,
            "connected_account": conn.account_email if conn else None,
            "account_name": conn.account_name if conn else None,
            "capabilities": self.capabilities,
            "last_synced_at": conn.last_synced_at if conn else None,
            "last_sync": conn.last_synced_at if conn else None,
            "last_error": conn.last_error if conn else None,
            "auth_url": self.get_auth_url() if configured else None,
        }


zoom_service = ZoomService()
