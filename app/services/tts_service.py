import base64

from app.core.config import settings
from app.schemas.tts import TTSSynthesizeRequest, TTSSynthesizeResponse
from app.services.tts_providers.groq_provider import GroqTTSProvider
from app.services.tts_providers.parler_provider import ParlerHFProvider


class TTSConfigurationError(Exception):
    pass


class TTSProviderError(Exception):
    pass


class TTSService:
    def __init__(self) -> None:
        # Kokoro supprimé : trop lourd pour Render free tier (512MB).
        # Parler-TTS via HF Inference API remplace Kokoro pour le podcast Worker.
        # "kokoro" dans le schéma est redirigé vers "parler_hf" pour compatibilité.
        self._providers = {
            "groq": GroqTTSProvider(),
            "parler_hf": ParlerHFProvider(),
        }

    @staticmethod
    def _normalize_provider_name(name: str | None) -> str:
        raw_name = (name or "").strip().lower()
        # "kokoro" redirigé vers parler_hf (compat API mobile)
        if raw_name == "kokoro":
            return "parler_hf"
        return raw_name if raw_name in {"groq", "parler_hf"} else "parler_hf"

    def _resolve_provider_order(self, requested_provider: str) -> list[str]:
        normalized = self._normalize_provider_name(requested_provider)
        if normalized in {"groq", "parler_hf"}:
            return [normalized]

        preferred = self._normalize_provider_name(settings.tts_provider)
        fallback = "groq" if preferred == "parler_hf" else "parler_hf"
        return [preferred, fallback]

    async def synthesize(self, payload: TTSSynthesizeRequest) -> TTSSynthesizeResponse:
        errors: list[str] = []
        provider_order = self._resolve_provider_order(payload.provider)

        for provider_name in provider_order:
            provider = self._providers.get(provider_name)
            if not provider:
                errors.append(f"{provider_name}: provider non disponible")
                continue

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
                if payload.provider == "groq":
                    raise TTSConfigurationError(str(exc)) from exc
            except RuntimeError as exc:
                errors.append(f"{provider_name}: {exc}")
                if payload.provider == "groq":
                    raise TTSProviderError(str(exc)) from exc

        if errors:
            raise TTSProviderError(" | ".join(errors))

        raise TTSProviderError("Aucun provider TTS disponible.")


tts_service = TTSService()
