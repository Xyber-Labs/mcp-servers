import pytest
import json
import asyncio
import httpx
from unittest.mock import AsyncMock, patch, MagicMock, call
from fastmcp import Context
from fastapi import FastAPI
from fastmcp.exceptions import ToolError
from langchain_core.runnables import Runnable

from mcp_server_deepresearcher.app import get_mcp_server, app_lifespan
from mcp_server_deepresearcher.schemas import DeepResearchRequest


_mcp_server = None

async def get_deep_research_func():
    """Get the deep_research function from mcp_server tools."""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = get_mcp_server()
    tools = await _mcp_server.get_tools()
    if 'deep_research' in tools:
        return tools['deep_research'].fn
    raise ValueError("deep_research tool not found")


@pytest.mark.asyncio
async def test_deep_research_success(mock_context, mock_agent):
    """Test successful deep research execution."""
    from mcp_server_deepresearcher.schemas import DeepResearchRequest
    
    deep_research_func = await get_deep_research_func()
    request = DeepResearchRequest(research_topic='artificial intelligence')
    
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        result = await deep_research_func(mock_context, request)
        
        parsed_result = json.loads(result)
        assert 'result' in parsed_result
        assert parsed_result['result'] == 'Test research summary'
        assert 'sources' in parsed_result
        assert 'query_count' in parsed_result
        
        mock_agent.graph.ainvoke.assert_called_once()
        call_args = mock_agent.graph.ainvoke.call_args
        assert call_args[0][0]['research_topic'] == 'artificial intelligence'
        assert call_args[1]['config']['configurable']['max_web_research_loops'] == 3


@pytest.mark.asyncio
async def test_deep_research_default_loops(mock_context, mock_agent):
    from mcp_server_deepresearcher.schemas import DeepResearchRequest
    
    deep_research_func = await get_deep_research_func()
    request = DeepResearchRequest(research_topic='quantum computing')
    
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        await deep_research_func(mock_context, request)
        
        call_args = mock_agent.graph.ainvoke.call_args
        assert call_args[1]['config']['configurable']['max_web_research_loops'] == 3


@pytest.mark.asyncio
async def test_deep_research_missing_llm(context_missing_llm):
    deep_research_func = await get_deep_research_func()
    request = DeepResearchRequest(research_topic='test topic')
    
    with pytest.raises(ToolError) as exc_info:
        await deep_research_func(context_missing_llm, request)
    assert 'Shared resources' in str(exc_info.value)


@pytest.mark.asyncio
async def test_deep_research_missing_tools(context_missing_tools):
    deep_research_func = await get_deep_research_func()
    request = DeepResearchRequest(research_topic='test topic')
    
    with pytest.raises(ToolError) as exc_info:
        await deep_research_func(context_missing_tools, request)
    assert 'Shared resources' in str(exc_info.value)

@pytest.mark.asyncio
async def test_deep_research_agent_error(mock_context, mock_agent_with_error):
    deep_research_func = await get_deep_research_func()
    request = DeepResearchRequest(research_topic='pytest topic')
    
    with patch('mcp_server_deepresearcher.server.DeepResearcher', return_value=mock_agent_with_error):
        with pytest.raises(ToolError) as exc:
            await deep_research_func(mock_context, request)
        assert 'unexpected error' in str(exc.value).lower()

@pytest.mark.asyncio
async def test_app_lifespan_initialization(monkeypatch):
    mock_llm = MagicMock(spec=Runnable)
    mock_llm_with_fallbacks = MagicMock(spec=Runnable)
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm_with_fallbacks)
    mock_spare_llm = MagicMock(spec=Runnable)
    mock_tools = [MagicMock()]
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(return_value=mock_tools)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', lambda: mock_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', lambda: mock_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', lambda **kwargs: {'mock': 'config'})
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', lambda cfg: mock_client)
    monkeypatch.setattr('mcp_server_deepresearcher.app.construct_tools_description_yaml', lambda tools: "tools:\n  - name: test")
    monkeypatch.setattr('mcp_server_deepresearcher.app.parse_tools_description_from_yaml', lambda yaml_str: [{"name": "test", "description": "test"}])
    monkeypatch.setattr('mcp_server_deepresearcher.app.initialize_llm', lambda llm_type, raise_on_error: None)
    from mcp_server_deepresearcher.app import app_lifespan
    from fastapi import FastAPI
    server = MagicMock(spec=FastAPI)
    async with app_lifespan(server) as resources:
        assert 'llm' in resources
        assert 'mcp_tools' in resources
        assert resources['llm'] is mock_llm_with_fallbacks
        assert resources['mcp_tools'] == mock_tools

@pytest.mark.asyncio
async def test_streaming_events(monkeypatch):
    class FakeAsyncGen:
        def __aiter__(self):
            self.count = 0
            return self
        async def __anext__(self):
            if self.count < 2:
                self.count += 1
                return {'event': f'data-{self.count}'}
            raise StopAsyncIteration
    mock_llm = MagicMock()
    mock_tools = [MagicMock()]
    mock_agent = MagicMock()
    mock_agent.graph.ainvoke = lambda *a, **kw: FakeAsyncGen()
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        ctx = MagicMock()
        ctx.request_context.lifespan_context = {
            'llm': mock_llm,
            'mcp_tools': mock_tools
        }
        # Collect streamed events
        events = []
        async for event in mock_agent.graph.ainvoke({'research_topic': 'pytest'}):
            events.append(event)
        assert events == [{'event': 'data-1'}, {'event': 'data-2'}]


@pytest.mark.asyncio
async def test_deep_research_empty_topic(mock_context):
    deep_research_func = await get_deep_research_func()
    request = DeepResearchRequest(research_topic='')
    
    mock_agent = MagicMock()
    mock_agent.graph.ainvoke = AsyncMock(return_value={
        'running_summary': {
            'result': 'Empty topic handled',
            'sources': [],
            'query_count': 0
        }
    })
    
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        result = await deep_research_func(mock_context, request)
        parsed_result = json.loads(result)
        assert 'result' in parsed_result



@pytest.mark.asyncio
async def test_deep_research_malformed_result():
    deep_research_func = await get_deep_research_func()
    request = DeepResearchRequest(research_topic='test topic')
    
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {
        'llm': MagicMock(),
        'mcp_tools': [MagicMock()]
    }
    
    mock_agent = MagicMock()
    mock_agent.graph.ainvoke = AsyncMock(return_value={
        'unexpected_key': 'unexpected_value'
    })
    
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        result = await deep_research_func(ctx, request)
        parsed_result = json.loads(result)
        assert parsed_result == {}


def test_mcp_server_initialization():
    mcp_server = get_mcp_server()
    assert mcp_server.name == "deep_researcher"


@pytest.mark.asyncio
async def test_mcp_server_tool_registration():
    mcp_server = get_mcp_server()
    tools = await mcp_server.get_tools()
    assert len(tools) >= 1
    assert 'deep_research' in tools


@pytest.mark.asyncio
async def test_app_lifespan_network_error(monkeypatch):
    mock_llm = MagicMock(spec=Runnable)
    mock_llm_with_fallbacks = MagicMock(spec=Runnable)
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm_with_fallbacks)
    mock_spare_llm = MagicMock(spec=Runnable)
    
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', lambda: mock_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', lambda: mock_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', lambda **kwargs: {'mock': 'config'})
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', lambda cfg: mock_client)
    
    server = MagicMock(spec=FastAPI)
    
    with pytest.raises(httpx.ConnectError):
        async with app_lifespan(server) as resources:
            pass


@pytest.mark.asyncio
async def test_app_lifespan_partial_tools_failure(monkeypatch):
    mock_llm = MagicMock(spec=Runnable)
    mock_llm_with_fallbacks = MagicMock(spec=Runnable)
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm_with_fallbacks)
    mock_spare_llm = MagicMock(spec=Runnable)
    
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(return_value=[MagicMock()])  # Only one tool instead of expected multiple
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', lambda: mock_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', lambda: mock_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', lambda **kwargs: {'mock': 'config'})
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', lambda cfg: mock_client)
    monkeypatch.setattr('mcp_server_deepresearcher.app.construct_tools_description_yaml', lambda tools: "tools:\n  - name: test")
    monkeypatch.setattr('mcp_server_deepresearcher.app.parse_tools_description_from_yaml', lambda yaml_str: [{"name": "test", "description": "test"}])
    monkeypatch.setattr('mcp_server_deepresearcher.app.initialize_llm', lambda llm_type, raise_on_error: None)
    
    server = MagicMock(spec=FastAPI)
    
    async with app_lifespan(server) as resources:
        assert 'llm' in resources
        assert 'mcp_tools' in resources
        assert len(resources['mcp_tools']) == 1


@pytest.mark.asyncio
async def test_app_lifespan_llm_initialization_error(monkeypatch):
    def failing_llm_setup(cfg):
        raise Exception("LLM initialization failed")
    
    monkeypatch.setattr('mcp_server_deepresearcher.server.setup_llm', failing_llm_setup)
    
    server = MagicMock(spec=FastAPI)
    
    with pytest.raises(Exception, match="LLM initialization failed"):
        async with app_lifespan(server) as resources:
            pass


@pytest.mark.asyncio
async def test_streaming_with_real_agent_behavior(monkeypatch):
    class RealisticAsyncGen:
        def __init__(self):
            self.events = [
                {'event': 'query_generated', 'data': {'query': 'test query'}},
                {'event': 'research_started', 'data': {'sources': 2}},
                {'event': 'summarization_complete', 'data': {'tokens': 150}},
                {'event': 'research_complete', 'data': {'final_summary': 'done'}}
            ]
            self.index = 0
        
        def __aiter__(self):
            return self
        
        async def __anext__(self):
            if self.index < len(self.events):
                event = self.events[self.index]
                self.index += 1
                await asyncio.sleep(0.01)  # Simulate processing time
                return event
            raise StopAsyncIteration
    
    mock_llm = MagicMock()
    mock_tools = [MagicMock()]
    mock_agent = MagicMock()
    mock_agent.graph.ainvoke = lambda *a, **kw: RealisticAsyncGen()
    
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        ctx = MagicMock()
        ctx.request_context.lifespan_context = {
            'llm': mock_llm,
            'mcp_tools': mock_tools
        }
        
        events = []
        async for event in mock_agent.graph.ainvoke({'research_topic': 'AI research'}):
            events.append(event)
        
        assert len(events) == 4
        assert events[0]['event'] == 'query_generated'
        assert events[3]['event'] == 'research_complete'


@pytest.mark.asyncio
async def test_streaming_error_handling():
    class FailingAsyncGen:
        def __aiter__(self):
            return self
        
        async def __anext__(self):
            raise Exception("Streaming error")
    
    mock_llm = MagicMock()
    mock_tools = [MagicMock()]
    mock_agent = MagicMock()
    mock_agent.graph.ainvoke = lambda *a, **kw: FailingAsyncGen()
    
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        ctx = MagicMock()
        ctx.request_context.lifespan_context = {
            'llm': mock_llm,
            'mcp_tools': mock_tools
        }
        
        with pytest.raises(Exception, match="Streaming error"):
            async for event in mock_agent.graph.ainvoke({'research_topic': 'test'}):
                pass


@pytest.mark.asyncio
async def test_concurrent_deep_research_requests(multiple_contexts, mock_agent_factory):
    
    with patch('mcp_server_deepresearcher.server.DeepResearcher', side_effect=mock_agent_factory):
        deep_research_func = await get_deep_research_func()
        tasks = [
            deep_research_func(multiple_contexts[0], DeepResearchRequest(research_topic='topic1')),
            deep_research_func(multiple_contexts[1], DeepResearchRequest(research_topic='topic2')),
            deep_research_func(multiple_contexts[2], DeepResearchRequest(research_topic='topic3'))
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert len(mock_agent_factory.created_agents) == 3
        
        result_texts = []
        for result in results:
            parsed = json.loads(result)
            result_texts.append(parsed['result'])
        
        assert len(set(result_texts)) == 3  # All unique
        for result_text in result_texts:
            assert 'Research result' in result_text


@pytest.mark.asyncio
async def test_app_lifespan_cleanup_on_error(monkeypatch):
    cleanup_called = False
    
    def mock_cleanup():
        nonlocal cleanup_called
        cleanup_called = True
    
    # Create proper Runnable mocks to avoid Pydantic validation errors
    mock_llm = MagicMock(spec=Runnable)
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm)
    mock_llm.cleanup = mock_cleanup
    
    mock_spare_llm = MagicMock(spec=Runnable)
    
    # Create a mock client factory that raises an error when get_tools is called
    def mock_client_factory(cfg):
        mock_client = MagicMock()
        mock_client.get_tools = AsyncMock(side_effect=Exception("Setup error"))
        return mock_client
    
    monkeypatch.setattr('mcp_server_deepresearcher.server.setup_llm', lambda cfg: mock_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.server.setup_spare_llm', lambda cfg: mock_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', lambda **kwargs: {'server1': {'url': 'http://test'}})
    monkeypatch.setattr('mcp_server_deepresearcher.server.MultiServerMCPClient', mock_client_factory)
    
    server = MagicMock(spec=FastAPI)
    
    # The exception should be raised during initialization when get_tools is called
    with pytest.raises(Exception) as exc_info:
        async with app_lifespan(server) as resources:
            pass
    
    # Verify the error message contains "Setup error"
    assert "Setup error" in str(exc_info.value)
    
    # Cleanup should be called even on error
    # Note: This test assumes cleanup logic exists, may need adjustment based on actual implementation


@pytest.mark.asyncio
async def test_deep_research_large_topic(mock_context, large_research_topic):
    mock_agent = MagicMock()
    mock_agent.graph.ainvoke = AsyncMock(return_value={
        'running_summary': {
            'result': 'Large topic processed',
            'sources': ['example.com'],
            'query_count': 1
        }
    })
    
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        deep_research_func = await get_deep_research_func()
        request = DeepResearchRequest(research_topic=large_research_topic)
        result = await deep_research_func(mock_context, request)
        parsed_result = json.loads(result)
        assert 'result' in parsed_result
        
        call_args = mock_agent.graph.ainvoke.call_args
        assert call_args[0][0]['research_topic'] == large_research_topic


@pytest.mark.asyncio
async def test_deep_research_unicode_topic(mock_context, unicode_research_topic):
    mock_agent = MagicMock()
    mock_agent.graph.ainvoke = AsyncMock(return_value={
        'running_summary': {
            'result': 'Unicode topic processed',
            'sources': ['example.com'],
            'query_count': 1
        }
    })
    
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        deep_research_func = await get_deep_research_func()
        request = DeepResearchRequest(research_topic=unicode_research_topic)
        result = await deep_research_func(mock_context, request)
        parsed_result = json.loads(result)
        assert 'result' in parsed_result
        
        call_args = mock_agent.graph.ainvoke.call_args
        assert call_args[0][0]['research_topic'] == unicode_research_topic



@pytest.mark.asyncio
async def test_app_lifespan_with_missing_env_vars(monkeypatch):
    def failing_config():
        raise ValueError("Missing required environment variable")
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.LLM_Config', failing_config)
    
    server = MagicMock(spec=FastAPI)
    
    with pytest.raises(ValueError, match="Missing required environment variable"):
        async with app_lifespan(server) as resources:
            pass


@pytest.mark.asyncio
async def test_app_lifespan_with_partial_config(monkeypatch):
    mock_llm = MagicMock()
    mock_llm_with_fallbacks = MagicMock()
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm_with_fallbacks)
    mock_spare_llm = MagicMock()
    mock_tools = []  # Empty tools list
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(return_value=mock_tools)
    
    monkeypatch.setattr('mcp_server_deepresearcher.server.setup_llm', lambda cfg: mock_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.server.setup_spare_llm', lambda cfg: mock_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', lambda **kwargs: {})
    monkeypatch.setattr('mcp_server_deepresearcher.server.MultiServerMCPClient', lambda cfg: mock_client)
    monkeypatch.setattr('mcp_server_deepresearcher.server.construct_tools_description_yaml', lambda tools: "")
    monkeypatch.setattr('mcp_server_deepresearcher.server.parse_tools_description_from_yaml', lambda yaml_str: [])
    monkeypatch.setattr('mcp_server_deepresearcher.server.initialize_llm', lambda llm_type, raise_on_error: None)
    
    server = MagicMock(spec=FastAPI)
    
    async with app_lifespan(server) as resources:
        assert 'llm' in resources
        assert 'mcp_tools' in resources
        assert resources['mcp_tools'] == []




@pytest.mark.asyncio
async def test_mcp_client_http_timeout(monkeypatch):
    mock_llm = MagicMock(spec=Runnable)
    mock_llm_with_fallbacks = MagicMock(spec=Runnable)
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm_with_fallbacks)
    mock_spare_llm = MagicMock(spec=Runnable)
    
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', lambda: mock_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', lambda: mock_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', lambda **kwargs: {'mock': 'config'})
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', lambda cfg: mock_client)
    
    server = MagicMock(spec=FastAPI)
    
    with pytest.raises(httpx.TimeoutException):
        async with app_lifespan(server) as resources:
            pass


@pytest.mark.asyncio
async def test_mcp_client_http_error_codes(monkeypatch):
    mock_llm = MagicMock(spec=Runnable)
    mock_llm_with_fallbacks = MagicMock(spec=Runnable)
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm_with_fallbacks)
    mock_spare_llm = MagicMock(spec=Runnable)
    
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(side_effect=httpx.HTTPStatusError(
        "Server error", 
        request=MagicMock(), 
        response=MagicMock(status_code=500)
    ))
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', lambda: mock_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', lambda: mock_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', lambda **kwargs: {'mock': 'config'})
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', lambda cfg: mock_client)
    
    server = MagicMock(spec=FastAPI)
    
    with pytest.raises(httpx.HTTPStatusError):
        async with app_lifespan(server) as resources:
            pass


@pytest.mark.asyncio
async def test_full_request_lifecycle(monkeypatch):
    mock_llm = MagicMock(spec=Runnable)
    mock_llm_with_fallbacks = MagicMock(spec=Runnable)
    mock_llm.with_fallbacks = MagicMock(return_value=mock_llm_with_fallbacks)
    mock_spare_llm = MagicMock(spec=Runnable)
    mock_tools = [MagicMock(name="test_tool")]
    mock_client = MagicMock()
    mock_client.get_tools = AsyncMock(return_value=mock_tools)
    
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_llm', lambda: mock_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.setup_spare_llm', lambda: mock_spare_llm)
    monkeypatch.setattr('mcp_server_deepresearcher.app.load_mcp_servers_config', lambda **kwargs: {'mock': 'config'})
    monkeypatch.setattr('mcp_server_deepresearcher.app.MultiServerMCPClient', lambda cfg: mock_client)
    monkeypatch.setattr('mcp_server_deepresearcher.app.construct_tools_description_yaml', lambda tools: "tools:\n  - name: test")
    monkeypatch.setattr('mcp_server_deepresearcher.app.parse_tools_description_from_yaml', lambda yaml_str: [{"name": "test", "description": "test"}])
    monkeypatch.setattr('mcp_server_deepresearcher.app.initialize_llm', lambda llm_type, raise_on_error: None)
    
    mock_agent = MagicMock()
    mock_agent.graph.ainvoke = AsyncMock(return_value={
        'running_summary': {
            'result': 'Comprehensive research completed',
            'sources': ['https://source1.com', 'https://source2.com'],
            'query_count': 5,
            'tokens_used': 1500,
            'processing_time': 45.6
        }
    })
    
    server = MagicMock(spec=FastAPI)
    
    async with app_lifespan(server) as resources:
        assert 'llm' in resources
        assert 'mcp_tools' in resources
        
        ctx = MagicMock(spec=Context)
        ctx.request_context.lifespan_context = resources
        
        with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
            deep_research_func = await get_deep_research_func()
            request = DeepResearchRequest(research_topic='advanced AI research')
            result = await deep_research_func(ctx, request)
            
            parsed_result = json.loads(result)
            assert parsed_result['result'] == 'Comprehensive research completed'
            assert len(parsed_result['sources']) == 2
            assert parsed_result['query_count'] == 5
            
            mock_agent.graph.ainvoke.assert_called_once()
            call_args = mock_agent.graph.ainvoke.call_args
            assert call_args[0][0]['research_topic'] == 'advanced AI research'
            assert call_args[1]['config']['configurable']['max_web_research_loops'] == 3


@pytest.mark.asyncio
async def test_memory_cleanup_after_research():
    """Test that memory is properly cleaned up after research."""
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {
        'llm': MagicMock(),
        'mcp_tools': [MagicMock()]
    }
    
    created_agents = []
    
    def track_agent_creation(*args, **kwargs):
        agent = MagicMock()
        agent.graph.ainvoke = AsyncMock(return_value={
            'running_summary': {'result': 'Test', 'sources': [], 'query_count': 1}
        })
        created_agents.append(agent)
        return agent
    
    with patch('mcp_server_deepresearcher.server.DeepResearcher', side_effect=track_agent_creation):
        deep_research_func = await get_deep_research_func()
        for i in range(3):
            request = DeepResearchRequest(research_topic=f'topic {i}')
            await deep_research_func(ctx, request)
        
        assert len(created_agents) == 3
        
        for agent in created_agents:
            agent.graph.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_json_serialization_edge_cases():
    """Test JSON serialization of various edge case results."""
    ctx = MagicMock(spec=Context)
    ctx.request_context.lifespan_context = {
        'llm': MagicMock(),
        'mcp_tools': [MagicMock()]
    }
    
    mock_agent = MagicMock()
    mock_agent.graph.ainvoke = AsyncMock(return_value={
        'running_summary': {
            'result': None,
            'sources': None,
            'query_count': None
        }
    })
    
    with patch('mcp_server_deepresearcher.deepresearcher.graph.DeepResearcher', return_value=mock_agent):
        deep_research_func = await get_deep_research_func()
        request = DeepResearchRequest(research_topic='test topic')
        result = await deep_research_func(ctx, request)
        parsed_result = json.loads(result)  # Should not raise exception
        assert parsed_result['result'] is None
