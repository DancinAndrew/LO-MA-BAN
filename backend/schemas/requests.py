from pydantic import BaseModel, HttpUrl, Field


class AnalyzeRequest(BaseModel):
    url: HttpUrl = Field(..., description="Target URL to analyze")
