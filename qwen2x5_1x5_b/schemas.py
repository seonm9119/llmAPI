from typing import Optional

from pydantic import BaseModel, Field

from config import AXES


class InferenceRequest(BaseModel):
    text: str = Field(..., min_length=1)
    max_new_tokens: Optional[int] = Field(None, ge=16, le=2048)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    include_raw: bool = False


class AxisResult(BaseModel):
    key: str
    signals: list[str]


class InferenceResponse(BaseModel):
    subject: AxisResult
    document_type: AxisResult
    business_domain: AxisResult
    modifier: AxisResult
    raw_output: Optional[str] = None
    elapsed_ms: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)


def unknown_axes():
    return {
        axis: {
            "key": "unknown",
            "signals": [],
        }
        for axis in AXES
    }
