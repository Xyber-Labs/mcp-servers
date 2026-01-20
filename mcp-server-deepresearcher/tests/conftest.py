import pytest
import asyncio
import httpx
from unittest.mock import MagicMock, AsyncMock
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError
from langchain_core.runnables import Runnable

from mcp_server_deepresearcher.schemas import DeepResearchRequest


@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=Runnable)
    llm.with_fallbacks = MagicMock(return_value=llm)
    return llm


@pytest.fixture
def mock_spare_llm():
    spare_llm = MagicMock(spec=Runnable)
    return spare_llm


@pytest.fixture
def mock_mcp_tools():
    tool1 = MagicMock()
    tool1.name = "tavily_search"
    tool2 = MagicMock()
    tool2.name = "arxiv_search"
    tool3 = MagicMock()
    tool3.name = "apify_scrape"
    return [tool1, tool2, tool3]


@pytest.fixture
def mock_mcp_client(mock_mcp_tools):
    client = MagicMock()
    client.get_tools = AsyncMock(return_value=mock_mcp_tools)
    return client


@pytest.fixture
def mock_context(mock_llm, mock_mcp_tools):
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {
        'llm': mock_llm,
        'mcp_tools': mock_mcp_tools
    }
    return ctx


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.graph.ainvoke = AsyncMock(return_value={
        'running_summary': {
            'result': 'Test research summary',
            'sources': ['https://example.com'],
            'query_count': 2
        }
    })
    return agent


@pytest.fixture
def mock_fastmcp_server():
    return MagicMock(spec=FastMCP)


@pytest.fixture
def mock_configs():
    llm_config = MagicMock()
    llm_config.TOGETHER_API_KEY = "test-together-key"
    llm_config.GOOGLE_API_KEY = "test-google-key"
    llm_config.MISTRAL_API_KEY = "test-mistral-key"
    
    search_config = MagicMock()
    search_config.APIFY_TOKEN = "test-apify-token"
    search_config.MCP_TAVILY_URL = "http://localhost:3001"
    search_config.MCP_ARXIV_URL = "http://localhost:3002"
    
    return llm_config, search_config


#Additional useful fixtures

@pytest.fixture
def empty_context():
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {}
    return ctx


@pytest.fixture
def context_missing_llm(mock_mcp_tools):
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {
        'llm': None,
        'mcp_tools': mock_mcp_tools
    }
    return ctx


@pytest.fixture
def context_missing_tools(mock_llm):
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {
        'llm': mock_llm,
        'mcp_tools': None
    }
    return ctx


@pytest.fixture
def mock_agent_with_error():
    agent = MagicMock()
    agent.graph.ainvoke = AsyncMock(side_effect=Exception('Agent error'))
    return agent


@pytest.fixture
def mock_http_client():
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    return client


@pytest.fixture
def mock_network_timeout():
    return httpx.TimeoutException("Request timeout")


@pytest.fixture
def mock_network_error():
    return httpx.ConnectError("Connection failed")


@pytest.fixture
def mock_http_500_error():
    return httpx.HTTPStatusError(
        "Server error", 
        request=MagicMock(), 
        response=MagicMock(status_code=500)
    )


@pytest.fixture
def sample_research_topics():
    return [
        'artificial intelligence',
        'quantum computing',
        'machine learning',
        'deep learning',
        'neural networks'
    ]


@pytest.fixture
def large_research_topic():
    return "A" * 10000


@pytest.fixture
def unicode_research_topic():
    return "Исследование ИИ в 中国 🤖"


@pytest.fixture
def malformed_agent_result():
    agent = MagicMock()
    agent.graph.ainvoke = AsyncMock(return_value={
        'unexpected_key': 'unexpected_value'
    })
    return agent


@pytest.fixture
def agent_with_null_results():
    agent = MagicMock()
    agent.graph.ainvoke = AsyncMock(return_value={
        'running_summary': {
            'result': None,
            'sources': None,
            'query_count': None
        }
    })
    return agent


#Helper fixtures for concurrent testing

@pytest.fixture
def multiple_contexts(mock_llm, mock_mcp_tools):
    contexts = []
    for i in range(3):
        ctx = MagicMock(spec=Context)
        ctx.request_context.lifespan_context = {
            'llm': mock_llm,
            'mcp_tools': mock_mcp_tools
        }
        contexts.append(ctx)
    return contexts


@pytest.fixture
def mock_agent_factory():
    created_agents = []
    
    def create_agent(*args, **kwargs):
        agent = MagicMock()
        call_id = len(created_agents) + 1
        
        async def mock_ainvoke(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing time
            return {
                'running_summary': {
                    'result': f'Research result {call_id}',
                    'sources': [f'source{call_id}.com'],
                    'query_count': call_id
                }
            }
        
        agent.graph.ainvoke = mock_ainvoke
        created_agents.append(agent)
        return agent
    
    create_agent.created_agents = created_agents
    return create_agent


# Additional fixtures for new test structure

@pytest.fixture
def mock_app_state():
    """Create mock app state with research resources."""
    state = MagicMock()
    state.llm = MagicMock()
    state.llm_thinking = MagicMock()
    state.mcp_tools = [MagicMock(name="tool1"), MagicMock(name="tool2")]
    state.tools_description = []
    return state


@pytest.fixture
def mock_fastapi_app(mock_app_state):
    """Create a mock FastAPI app with state."""
    app = MagicMock()
    app.state = mock_app_state
    return app


@pytest.fixture
def mock_research_request():
    """Create a mock research request."""
    return DeepResearchRequest(
        research_topic="test topic"
    )
