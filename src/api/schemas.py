from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    max_new_tokens: int = Field(default=128, ge=1, le=512)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class QARequest(BaseModel):
    question: str = Field(..., min_length=1)
    context: str = Field(..., min_length=1)
    max_new_tokens: int = Field(default=128, ge=1, le=512)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class RiskAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1)
    max_new_tokens: int = Field(default=128, ge=1, le=512)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class InferenceResponse(BaseModel):
    model_id: str
    output: str
