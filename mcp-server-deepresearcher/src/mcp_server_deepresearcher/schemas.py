from pydantic import BaseModel, Field


class DeepResearchRequest(BaseModel):
    """Input schema for the deep_research tool."""

    research_topic: str = Field(..., description="The research topic to investigate")
