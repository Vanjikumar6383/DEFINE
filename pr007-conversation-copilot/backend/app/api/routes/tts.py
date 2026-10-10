import logging
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
import httpx
from app.core.config import get_settings
from app.models.models import User
from app.security.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tts", tags=["tts"])
settings = get_settings()


class TTSRequest(BaseModel):
    text: str
    voice_id: str | None = None


@router.post("/speak")
async def generate_speech(
    payload: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate neural speech from text using ElevenLabs API.
    Falls back cleanly if key is not configured or rate-limited.
    """
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    api_key = settings.ELEVENLABS_API_KEY
    voice_id = payload.voice_id or settings.ELEVENLABS_VOICE_ID or "JBFqnCBsd6RMkjVDRZzb"

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="ELEVENLABS_API_KEY not configured. Falling back to browser Web Speech API."
        )

    # ElevenLabs text-to-speech endpoint
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": text[:1500],
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                logger.warning("ElevenLabs API responded with status %s: %s", resp.status_code, resp.text)
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"ElevenLabs TTS service error ({resp.status_code})"
                )
            return Response(content=resp.content, media_type="audio/mpeg")
        except httpx.RequestError as exc:
            logger.error("Failed to connect to ElevenLabs: %s", exc)
            raise HTTPException(
                status_code=502,
                detail="Could not connect to ElevenLabs API."
            )
