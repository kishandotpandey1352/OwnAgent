from typing import Literal

from pydantic import BaseModel, Field


class GroundingValidation(BaseModel):
    confidence: Literal["high", "medium", "low"]
    cited_source_numbers: list[int] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    should_refuse: bool = False
    reason: str | None = None