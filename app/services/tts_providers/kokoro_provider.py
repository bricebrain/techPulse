import io
import wave
from pathlib import Path

import httpx

from app.core.config import settings
from app.schemas.tts import TTSSynthesizeRequest
from app.services.tts_providers.base import BaseTTSProvider, ProviderSynthesisResult


class KokoroTTSProvider(BaseTTSProvider):
    name = "kokoro"

    def __init__(self) -> None:
        self._kokoro = None

    def _resolve_model_path(self) -> Path:
        return Path(settings.tts_kokoro_model_path)

    def _resolve_voices_path(self) -> Path:
        return Path(settings.tts_kokoro_voices_path)

    async def _download_if_missing(self, target: Path, url: str | None) -> None:
        if target.exists():
            return

        if not settings.tts_kokoro_auto_download:
            raise ValueError(
                f"Fichier Kokoro introuvable: {target}. Active TTS_KOKORO_AUTO_DOWNLOAD ou fournis le fichier."
            )

        if not url:
            raise ValueError(
                f"Fichier Kokoro introuvable: {target}. Definis une URL de telechargement."
            )

        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Echec du telechargement Kokoro: {url}") from exc

        target.write_bytes(response.content)

    async def _ensure_assets(self) -> tuple[Path, Path]:
        model_path = self._resolve_model_path()
        voices_path = self._resolve_voices_path()

        await self._download_if_missing(model_path, settings.tts_kokoro_model_url)
        await self._download_if_missing(voices_path, settings.tts_kokoro_voices_url)

        return model_path, voices_path

    async def _ensure_engine(self):
        if self._kokoro is not None:
            return self._kokoro

        model_path, voices_path = await self._ensure_assets()

        try:
            from kokoro_onnx import Kokoro
        except Exception as exc:  # pragma: no cover - importe runtime dependant
            raise ValueError(
                "Le package kokoro-onnx n'est pas installe sur le backend."
            ) from exc

        self._kokoro = Kokoro(str(model_path), str(voices_path))
        return self._kokoro

    @staticmethod
    def _to_wav_bytes(samples, sample_rate: int) -> bytes:
        try:
            import numpy as np
        except Exception as exc:  # pragma: no cover - importe runtime dependant
            raise ValueError("Le package numpy est requis pour Kokoro TTS.") from exc

        audio = np.asarray(samples, dtype=np.float32)
        audio = np.clip(audio, -1.0, 1.0)
        pcm16 = (audio * 32767).astype(np.int16)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm16.tobytes())

        return buffer.getvalue()

    @staticmethod
    def _normalize_voice(requested_voice: str | None, available_voices: list[str]) -> str:
        if requested_voice and requested_voice in available_voices:
            return requested_voice

        mapped_aliases = {
            "autumn": "af_sarah",
            "alloy": "af_sarah",
            "nova": "af_bella",
            "echo": "am_adam",
        }

        if requested_voice:
            mapped = mapped_aliases.get(requested_voice.lower())
            if mapped and mapped in available_voices:
                return mapped

        default_voice = settings.tts_kokoro_default_voice
        if default_voice in available_voices:
            return default_voice

        if not available_voices:
            raise RuntimeError("Aucune voix Kokoro disponible.")

        return available_voices[0]

    async def synthesize(self, payload: TTSSynthesizeRequest) -> ProviderSynthesisResult:
        text = payload.text.strip()
        if not text:
            raise RuntimeError("Le texte a synthetiser est vide.")

        if payload.response_format != "wav":
            raise ValueError("Kokoro TTS supporte uniquement le format wav.")

        kokoro = await self._ensure_engine()
        available_voices = kokoro.get_voices()
        voice = self._normalize_voice(payload.voice, available_voices)
        speed = payload.speed
        lang = payload.lang

        try:
            samples, sample_rate = kokoro.create(
                text,
                voice=voice,
                speed=speed,
                lang=lang,
            )
        except AssertionError as exc:
            raise ValueError(str(exc)) from exc
        except Exception as exc:
            raise RuntimeError("Echec de generation audio avec Kokoro.") from exc

        wav_bytes = self._to_wav_bytes(samples, sample_rate)

        return ProviderSynthesisResult(
            audio_bytes=wav_bytes,
            mime_type="audio/wav",
            model=payload.model.strip() if payload.model else settings.tts_kokoro_model_name,
            voice=voice,
            response_format="wav",
            provider=self.name,
        )
