import base64

from app.core.config import settings
from app.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from app.services.tts_providers.groq_provider import GroqTTSProvider
from app.services.tts_providers.kokoro_provider import KokoroTTSProvider
from app.services.tts_providers.parler_provider import ParlerHFProvider


class TTSConfigurationError(Exception):
    pass


class TTSProviderError(Exception):
    pass


class TTSService:
    def __init__(self) -> None:
        self._providers = {
            "groq": GroqTTSProvider(),
            "kokoro": KokoroTTSProvider(),
            "parler_hf": ParlerHFProvider(),
        }

    @staticmethod
    def _normalize_provider_name(name: str | None) -> str:
        raw_name = (name or "").strip().lower()
        return raw_name if raw_name in {"groq", "kokoro", "parler_hf"} else "parler_hf"

    def _resolve_provider_order(self, requested_provider: str) -> list[str]:
        if requested_provider in {"groq", "kokoro", "parler_hf"}:
            return [requested_provider]

        preferred = self._normalize_provider_name(settings.tts_provider)
        fallback = "kokoro" if preferred == "groq" else "groq"
        return [preferred, fallback]

    async def synthesize(self, payload: TTSSynthesizeRequest) -> TTSSynthesizeResponse:
        errors: list[str] = []
        provider_order = self._resolve_provider_order(payload.provider)

        for provider_name in provider_order:
            provider = self._providers[provider_name]

            try:
                result = await provider.synthesize(payload)
                audio_base64 = base64.b64encode(result.audio_bytes).decode("utf-8")
                return TTSSynthesizeResponse(
                    audio_base64=audio_base64,
                    mime_type=result.mime_type,
                    model=result.model,
                    voice=result.voice,
                    response_format=result.response_format,
                    provider_used=result.provider,
                )
            except ValueError as exc:
                errors.append(f"{provider_name}: {exc}")
                if payload.provider in {"groq", "kokoro"}:
                    raise TTSConfigurationError(str(exc)) from exc
            except RuntimeError as exc:
                errors.append(f"{provider_name}: {exc}")
                if payload.provider in {"groq", "kokoro"}:
                    raise TTSProviderError(str(exc)) from exc

        if errors:
            raise TTSProviderError(" | ".join(errors))

        raise TTSProviderError("Aucun provider TTS disponible.")


tts_service = TTSService()
