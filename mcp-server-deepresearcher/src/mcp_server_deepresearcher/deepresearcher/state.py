import operator
from dataclasses import dataclass, field
from typing import List, Annotated, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ConfigDict, ConfigDict


class ToolDescription(BaseModel):
    """Pydantic model for tool description."""
    name: str
    description: str
    server: Optional[str] = None
    
    model_config = ConfigDict(frozen=True)  # Make immutable
    
    def to_prompt_format(self) -> str:
        """Format tool description for use in prompts."""
        server_info = f" (Server: {self.server})" if self.server else ""
        return f"- {self.name}{server_info}: {self.description}"
    
    @classmethod
    def format_list_for_prompt(cls, tools: List['ToolDescription']) -> str:  # type: ignore
        """Format a list of tools for use in prompts."""
        if not tools:
            return "No tools available."
        return "\n".join(tool.to_prompt_format() for tool in tools)


@dataclass(kw_only=True)
class ResearchState:
    messages: Annotated[List[BaseMessage], add_messages] = field(default_factory=list)
    search_query: str = field(default=None)  # Search query
    web_research_results: list = field(default_factory=list)
    sources_gathered: Annotated[list, operator.add] = field(default_factory=list)
    research_loop_count: int = field(default=0)  # Research loop count
    follow_up_query: str = field(default=None)  # Follow-up query
    knowledge_gap: str = field(default=None)  # Knowledge gap
    summary: str = field(default=None)  # Summary of the research
    reasoning: str = field(default=None)  # Reasoning for the search query
    report: dict = field(default=None)  # Final report
    tools_description: List[ToolDescription] = field(default_factory=list)  # Available tools description
    tools_to_use: List[str] = field(default_factory=list)  # Tools to use
    stop_research: bool = field(default=False)  # Flag to stop research if summary is good enough