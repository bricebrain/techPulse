from typing import Literal

from pydantic import BaseModel, Field


class TTSSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=6000)
    model: str | None = Field(default=None, max_length=200)
    voice: str | None = Field(default=None, max_length=100)
    provider: Literal["auto", "groq", "kokoro"] = "auto"
    lang: str = Field(default="en-us", max_length=20)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    response_format: Literal["wav", "mp3", "flac", "opus", "pcm"] = "wav"


class TTSSynthesizeResponse(BaseModel):
    audio_base64: str
    mime_type: str
    model: str
    voice: str
    response_format: str
    provider_used: Literal["groq", "kokoro"]
