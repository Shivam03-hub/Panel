"""All the data shapes. One place. Every AI answer must match one of these."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class Scorecard(BaseModel):
    """What ONE interviewer returns. Strict: the AI must fill every field, nothing extra."""
    model_config = ConfigDict(extra="forbid")
    score: int = Field(description="1 to 10, judged ONLY on this interviewer's focus area")
    recommendation: Literal["strong_hire", "hire", "no_hire", "strong_no_hire"]
    strengths: list[str] = Field(description="Specific strengths from this interviewer's focus")
    concerns: list[str] = Field(description="Specific concerns from this interviewer's focus")
    reasoning: str = Field(description="2-3 sentences explaining the score")


class Rebuttal(BaseModel):
    """What one interviewer says in a debate round."""
    model_config = ConfigDict(extra="forbid")
    argument: str = Field(description="2-4 sentences defending your score, answering the others")
    holds_position: bool = Field(description="True if you still stand by your score")


class ChairDecision(BaseModel):
    """What the chair agent decides after each debate round: continue or finish."""
    model_config = ConfigDict(extra="forbid")
    next_step: Literal["debate_again", "finish"]
    reason: str = Field(description="1-2 sentences explaining why")


class Verdict(BaseModel):
    """The moderator's final decision."""
    model_config = ConfigDict(extra="forbid")
    recommendation: Literal["strong_hire", "hire", "no_hire", "strong_no_hire"]
    overall_score: int = Field(description="1 to 10 overall fit for the role")
    confidence: Literal["high", "medium", "low"]
    rationale: str = Field(description="3-4 sentences. Do NOT just average the scores.")
    key_strengths: list[str] = Field(description="Main strengths that support hiring")
    key_risks: list[str] = Field(description="Main risks weighed against hiring")