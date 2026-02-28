from pydantic import BaseModel, HttpUrl, Field


class AnalyzeRequest(BaseModel):
    url: HttpUrl = Field(..., description="Target URL to analyze")
    skip_llm: bool = Field(False, description="Skip LLM deep analysis")
    force_llm: bool = Field(False, description="Force LLM even if risk is low")
