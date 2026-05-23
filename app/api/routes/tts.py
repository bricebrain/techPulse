from fastapi import APIRouter, HTTPException, status

from app.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from app.services.tts_service import (
    TTSConfigurationError,
    TTSProviderError,
    tts_service,
)

router = APIRouter(prefix="/tts", tags=["TTS"])


@router.post("/synthesize", response_model=TTSSynthesizeResponse)
async def synthesize_tts(payload: TTSSynthesizeRequest) -> TTSSynthesizeResponse:
    try:
        return await tts_service.synthesize(payload)
    except TTSConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except TTSProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
