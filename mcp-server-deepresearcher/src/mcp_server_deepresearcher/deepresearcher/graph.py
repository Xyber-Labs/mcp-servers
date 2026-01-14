import asyncio
import concurrent.futures
import json
import logging
import re
from typing import List, Union, Literal
import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool, Tool
from langgraph.graph import END, START, StateGraph

from mcp_server_deepresearcher.deepresearcher.utils import (
    clean_response,
    create_mcp_tasks,
    extract_sources_from_raw_content,
    format_sources,
    deduplicate_sources,
)
from mcp_server_deepresearcher.deepresearcher.prompts import (
    get_current_date,
    query_writer_instructions,
    summarizer_instructions,
    reflection_instructions,
    final_report_instructions,
    web_research_instructions,
)
from mcp_server_deepresearcher.deepresearcher.state import ResearchState, ToolDescription
from mcp_server_deepresearcher.db.database import get_db_instance

logger = logging.getLogger(__name__)


current_date = get_current_date()


# Nodes
class ResearchGraph:
    """Research graph for performing deep research on topics."""
    def __init__(
        self,
        LLM,
        LLM_THINKING,
        tools: List[Union[Tool, StructuredTool]],
        research_topic: str,
        research_loop_max: int,
        tools_description: List[ToolDescription] = None,
    ):
        self.llm = LLM
        self.llm_thinking = LLM_THINKING
        self.tools = tools
        self.research_topic = research_topic
        self.research_loop_max = research_loop_max
        self.tools_description = tools_description or []
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        # Add nodes and edges
        builder = StateGraph(ResearchState, input_schema=ResearchState, output_schema=ResearchState)
        # Add nodes
        builder.add_node("generate_query", self.generate_query)
        builder.add_node("web_research", self.web_research)
        builder.add_node("summarize_sources", self.summarize_sources)
        builder.add_node("reflect_on_summary", self.reflect_on_summary)
        builder.add_node("generate_report", self.generate_report)

        # Add edges
        builder.add_edge(START, "generate_query")
        builder.add_edge("generate_query", "web_research")
        builder.add_edge("web_research", "summarize_sources")
        builder.add_edge("summarize_sources", "reflect_on_summary")
        builder.add_conditional_edges("reflect_on_summary", self.route_research)
        builder.add_edge("generate_report", END)
        graph = builder.compile()
        logger.info("Graph compiled successfully")

        # Script to save the graph as an image file
        # Save the graph visualization as an image file
        # logger.info("Saving graph as image")
        # try:
        #     # Get the directory of the current file
        #     output_dir = os.path.dirname(os.path.abspath(__file__))
        #     output_path = os.path.join(output_dir, "agent_research_graph.png")

        #     # Save the graph visualization as a PNG file
        #     try:
        #         # Use the appropriate method to save the graph
        #         # The get_graph() method accesses the internal graph representation
        #         graph_image = graph.get_graph().draw_mermaid_png()
        #         with open(output_path, "wb") as f:
        #             f.write(graph_image)
        #         logger.info(f"Graph saved to {output_path}")
        #     except Exception as e:
        #         logger.error(f"Error saving graph: {e}")
        # except Exception as e:
        #     logger.error(f"Error saving graph: {e}")

        return graph

    # Generate Query Node
    async def generate_query(self, state: ResearchState, config: RunnableConfig):
        """LangGraph node that generates a search query based on the research topic.
        This node is called to provide agent with the state of the art research.
        It generates the query for the following node to perform web research.
        """

        logger.info("--- Starting Generate Query Node ---")

        # logger.info(f"Tools description: {self.tools_description}")
        # breakpoint()

        # Format the prompt
        formated_prompt = query_writer_instructions.format(
            current_date=current_date, 
            research_topic=self.research_topic,
            tools_description=ToolDescription.format_list_for_prompt(self.tools_description),
        )
        result = await self.llm.ainvoke(formated_prompt)
        cleaned = clean_response(result.content)
        
        # Try JsonOutputParser first, fall back to json.loads if it fails
        try:
            parsed_result = JsonOutputParser().parse(cleaned)
        except Exception as parser_error:
            logger.warning(f"JsonOutputParser failed, falling back to json.loads(): {parser_error}")
            parsed_result = json.loads(cleaned)
        
        result = parsed_result


        # Get the query, reasoning, and tools
        try:
            search_query = result.get("query")
            reasoning = result.get("reasoning") or result.get("rationale")
            tools_to_use = result.get("tools", [])
            
            if not search_query or not reasoning:
                raise ValueError(
                    "LLM response missing 'query' or 'reasoning'/'rationale'"
                )

            # Validate tools_to_use is a list
            if not isinstance(tools_to_use, list):
                logger.warning(f"Tools field is not a list, got {type(tools_to_use)}. Converting to list.")
                tools_to_use = [tools_to_use] if tools_to_use else []

            logger.info(f"Search query: {search_query}")
            logger.info(f"Reasoning: {reasoning}")

            
            state.search_query = search_query
            state.reasoning = reasoning
            state.tools_to_use = tools_to_use
            logger.info(f"Tools to use: {state.tools_to_use}")
            return state

        except Exception as e:
            logger.error(f"Error generating query: {e}, result: {result}")
            state.search_query = None

            return END

    # Web Research Node
    async def web_research(self, state: ResearchState, config: RunnableConfig):
        """
        LangGraph node that performs parallel web research using multiple MCP servers.

        Executes searches, correctly parses and aggregates the results, and formats
        them for further processing.
        """
        logger.info("--- Starting Parallel Web Research Node ---")

        # Filter tools based on tools_to_use from state
        if state.tools_to_use:
            selected_tools = [
                tool for tool in self.tools 
                if tool.name in state.tools_to_use
            ]
            logger.info(f"Selected {len(selected_tools)} tools from {len(state.tools_to_use)} requested: {[t.name for t in selected_tools]}")
        else:
            # If no tools specified, use all available tools
            selected_tools = self.tools
            logger.info(f"No tools specified, using all {len(selected_tools)} available tools")

        # 1. Create and execute tasks in parallel
        tasks, task_names = create_mcp_tasks(selected_tools, state.search_query)
        # return_exceptions=True is crucial for resilience
        parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 2. Process the results in a single, clean loop
        all_raw_content = []
        all_structured_sources = []
        failed_tasks = []

        for i, result in enumerate(parallel_results):
            task_name = task_names[i]

            if isinstance(result, Exception):
                # Extract error details
                error_msg = str(result)
                error_type = type(result).__name__
                
                # Handle specific error types
                if "404" in error_msg or "Not Found" in error_msg:
                    error_detail = "No results found for this search query"
                    logger.warning(f"  - Task '{task_name}' returned 404/Not Found: {error_detail}")
                elif "HTTP error" in error_msg:
                    # Extract HTTP error code if available
                    http_match = re.search(r'HTTP error (\d+)', error_msg)
                    http_code = http_match.group(1) if http_match else "unknown"
                    error_detail = f"HTTP error {http_code}"
                    logger.error(f"  - Task '{task_name}' HTTP error {http_code}: {error_msg}")
                elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    error_detail = "Request timed out"
                    logger.error(f"  - Task '{task_name}' timed out: {error_msg}")
                elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                    error_detail = "Network connection error"
                    logger.error(f"  - Task '{task_name}' connection error: {error_msg}")
                else:
                    error_detail = f"Error ({error_type}): {error_msg[:200]}"
                    logger.error(f"  - Task '{task_name}' failed with {error_type}: {error_msg}")
                
                failed_tasks.append({
                    "task": task_name,
                    "error_type": error_type,
                    "error_message": error_msg,
                    "error_detail": error_detail
                })
                
                # Add informative error note to raw content for LLM context
                all_raw_content.append(
                    f"Note: The search tool '{task_name}' encountered an error: {error_detail}. "
                    f"This may indicate no results were found for the query or a temporary service issue."
                )
                continue

            # This handles both string and tuple `(content, None)` results
            content = result[0] if isinstance(result, tuple) else result

            # Generic processing for all tools - no instrument-specific parsing
            if isinstance(content, (dict, list)):
                try:
                    content_str = json.dumps(content, indent=2, default=str)
                except Exception:
                    content_str = str(content)
            else:
                content_str = str(content)

            if not content_str or not content_str.strip():
                logger.warning(f"  - Task '{task_name}' succeeded but returned empty content.")
                continue

            logger.info(f"  - Task '{task_name}' completed successfully. Adding raw content.")
            all_raw_content.append('Search Results from ' + task_name + ': \n' + '-' * 100 + '\n' + content_str + '\n' + '-' * 100 + '\n')

            # Use generic extractor for sources
            tool_sources = extract_sources_from_raw_content(content, task_name)
            all_structured_sources.extend(tool_sources)
            logger.info(f"  - Extracted {len(tool_sources)} sources from '{task_name}' results.")

        # 3. Aggregate and format the final outputs
        # Separate successful results from error messages
        successful_content = []
        error_messages = []
        
        for content in all_raw_content:
            if content.startswith("Note: The search tool") or "encountered an error" in content:
                error_messages.append(content)
            else:
                successful_content.append(content)
        
        # Log task execution summary
        successful_tasks = len(parallel_results) - len(failed_tasks)
        logger.info(f"Task execution summary: {successful_tasks}/{len(parallel_results)} tasks succeeded")
        if failed_tasks:
            logger.warning(f"Failed tasks ({len(failed_tasks)}): {[t['task'] for t in failed_tasks]}")
            for failed_task in failed_tasks:
                logger.warning(f"  - {failed_task['task']}: {failed_task['error_detail']}")
        
        # Combine content: successful results first, then error messages at the end
        # This helps LLM prioritize actual results over error messages
        if successful_content:
            search_str = "\n\n---\n\n".join(successful_content)
            if error_messages:
                search_str += "\n\n---\n\nNote: Some search tools encountered errors:\n" + "\n".join(error_messages)
        elif error_messages:
            # Only errors, no successful results
            search_str = "\n\n---\n\n".join(error_messages)
        else:
            search_str = ""
        
        # Log web research results size for debugging
        logger.info(f"Web research results size: {len(search_str):,} characters")
        logger.info(f"Number of raw content items: {len(all_raw_content)}")
        logger.info(f"Search query used: {state.search_query}")
        logger.info(f"Research loop count before update: {state.research_loop_count}")

        # Get existing sources from state
        existing_sources = []
        if state.sources_gathered:
            for source_item in state.sources_gathered:
                if isinstance(source_item, dict):
                    existing_sources.append(source_item)
                elif isinstance(source_item, str):
                    # Handle backward compatibility for formatted string sources
                    lines = source_item.split("\n")
                    for line in lines:
                        if not line.strip() or line.strip() == "No valid sources found.":
                            continue
                        match = re.match(r'\d+\.\s*(?:\[([^\]]+)\]\s*)?([^(]+)\s*\(([^)]+)\)', line.strip())
                        if match:
                            source_name, title, url = match.groups()
                            existing_sources.append({
                                "name": source_name.strip() if source_name else "unknown",
                                "title": title.strip(),
                                "url": url.strip()
                            })
        
        # Deduplicate sources from this run and existing sources separately
        unique_new_sources = deduplicate_sources(all_structured_sources)
        unique_existing_sources = deduplicate_sources(existing_sources)

        # Create a set of existing URLs for efficient filtering
        existing_urls = {src.get("url", "N/A").rstrip('/') for src in unique_existing_sources if src.get("url") and src.get("url") != "N/A"}

        # Filter out new sources that are already present in the existing sources
        new_sources_to_add = []
        for src in unique_new_sources:
            url = src.get("url", "N/A")
            # Add if it has a URL that we haven't seen
            if url and url != "N/A":
                if url.rstrip('/') not in existing_urls:
                    new_sources_to_add.append(src)
                    existing_urls.add(url.rstrip('/')) # Ensure no duplicates within the new list
            else:
                # For sources without URLs, add if the title is new among no-URL sources
                existing_titles = {s.get("title", "").strip().lower() for s in unique_existing_sources if not s.get("url") or s.get("url") == "N/A"}
                title = src.get("title", "").strip().lower()
                if title and title not in existing_titles:
                    new_sources_to_add.append(src)

        # Final combined list of unique sources for logging
        final_unique_sources = unique_existing_sources + new_sources_to_add
        
        logger.info(f"Sources this cycle: {len(all_structured_sources)} -> {len(unique_new_sources)} unique. "
                   f"Existing unique sources: {len(unique_existing_sources)}. "
                   f"Added {len(new_sources_to_add)} new unique sources. "
                   f"Total unique sources: {len(final_unique_sources)}.")
        
        # Format sources for logging
        formatted_sources_str = format_sources(final_unique_sources)
        logger.info(f"All unique sources ({len(final_unique_sources)} total): {formatted_sources_str[:500]}...")

        logger.info("--- Web Research Node Finished ---")


        
        if not search_str or not search_str.strip():
            logger.warning("WARNING: No content found in web research results!")
        

        return {
            # Return only new sources that don't exist in state
            # operator.add will accumulate them, but we've already filtered duplicates
            "sources_gathered": new_sources_to_add,
            "research_loop_count": state.research_loop_count + 1,
            "web_research_results": [search_str],
        }

    # Summarize Sources Node
    async def summarize_sources(self, state: ResearchState) -> ResearchState:
        """
        This node is called to summarize the web research results.
        It uses an LLM to create or update a running summary based on the newest web research
        results, integrating them with any existing summary.
        """
        logger.info("--- Starting Summarize Sources Node ---")

        # Extract web research results from state
        web_research_results = state.web_research_results or []
        logger.info(f"Found {len(web_research_results)} web research result(s) in state")
        
        # Log detailed info about web_research_results for debugging
        if web_research_results:
            total_chars = sum(len(str(r)) for r in web_research_results)
            logger.info(f"web_research_results total size: {total_chars:,} characters")
            for idx, result in enumerate(web_research_results):
                result_str = str(result)
                logger.info(f"  Result {idx + 1}: {len(result_str):,} chars")
        else:
            logger.info("web_research_results is empty")
        


        # Existing summary
        existing_summary = state.summary if state.summary is not None else None
        logger.info(f"Existing summary: {existing_summary}")
        
        # Truncate web_research_results to avoid token limit (max ~500k tokens = ~2M chars)
        # Approximate: 1 token ≈ 4 characters, so 500k tokens ≈ 2M characters   
        MAX_CHARS = 2_000_000
        
        # Calculate total character count
        total_chars = sum(len(result.strip()) for result in web_research_results)
        logger.info(f"Total web research results characters: {total_chars:,}")
        
        if total_chars > MAX_CHARS:
            logger.warning(f"Web research results exceed {MAX_CHARS:,} characters. Truncating...")
            truncated_results = []
            current_chars = 0
            for result in web_research_results:
                result_str = str(result)
                result_chars = len(result_str)
                if current_chars + result_chars <= MAX_CHARS:
                    truncated_results.append(result)
                    current_chars += result_chars
                else:
                    # Truncate the last result if needed
                    remaining_chars = MAX_CHARS - current_chars
                    if remaining_chars > 1000:  # Only include if meaningful amount remains
                        truncated_results.append(result_str[:remaining_chars] + "\n\n[TRUNCATED...]")
                    break
            web_research_results = truncated_results
            logger.info(f"Truncated to {sum(len(str(r)) for r in web_research_results):,} characters")

        # Log what's being sent to the LLM for debugging
        if web_research_results:
            logger.info("Content being sent to summarizer LLM:")
            for idx, result in enumerate(web_research_results):
                result_preview = str(result)[:500] + "..." if len(str(result)) > 500 else str(result)
                logger.info(f"  Result {idx + 1} preview: {result_preview}")
        
        formated_prompt = summarizer_instructions.format(
            current_date=current_date,
            web_research_results=web_research_results,
        )

        result = await self.llm_thinking.ainvoke(formated_prompt)
        raw_content = result.content if hasattr(result, 'content') else str(result)
        
        # Handle case where raw_content is a list (extract first string element)
        if isinstance(raw_content, list):
            logger.warning(f"LLM returned a list instead of string in reflect_on_summary, extracting first element")
            if len(raw_content) > 0:
                raw_content = str(raw_content[0])
            else:
                raw_content = ""
        
        # Ensure raw_content is a string
        if not isinstance(raw_content, str):
            raw_content = str(raw_content)
        
        cleaned = clean_response(raw_content)
        
        # Try JsonOutputParser first, fall back to json.loads if it fails
        try:
            parsed_result = JsonOutputParser().parse(cleaned)
        except Exception as parser_error:
            logger.warning(f"JsonOutputParser failed, falling back to json.loads(): {parser_error}")
            parsed_result = json.loads(cleaned)

        running_summary = parsed_result.get("running_summary")

        # Append existing summary with new summary
        if existing_summary and existing_summary.strip() and existing_summary != "None":
            state.summary = existing_summary + '\n\n---\n\n' + '-'*100 + f'\n\nNew search results from web research with tools used {state.tools_to_use}:\n' + '-'*100 + '\n\n' + running_summary
        elif running_summary is not None:
            state.summary = running_summary
        else:
            state.summary = "No summary generated"
        
        logger.info(f"Summary: {state.summary}")
        return state

    # Reflect on Summary Node
    async def reflect_on_summary(self, state: ResearchState) -> ResearchState:
        """
        This node is called to identify knowledge gaps and generate follow-up queries.

        Analyzes the current summary to identify areas for further research and generates
        a new search query to address those gaps. Uses structured output to extract
        the follow-up query in JSON format.
        """
        logger.info("--- Starting Reflect on Summary Node ---")
        formated_prompt = reflection_instructions.format(
            current_date=current_date,
            research_topic=self.research_topic,
            summary=state.summary,
            mcp_tools=state.tools_to_use,
            tools_description=ToolDescription.format_list_for_prompt(self.tools_description)
        )
        result = await self.llm_thinking.ainvoke(formated_prompt)
        raw_content = result.content if hasattr(result, 'content') else str(result)
        
        # Handle case where raw_content is a list (extract first string element)
        if isinstance(raw_content, list):
            logger.warning(f"LLM returned a list instead of string in reflect_on_summary, extracting first element")
            if len(raw_content) > 0:
                raw_content = str(raw_content[0])
            else:
                raw_content = ""
        
        # Ensure raw_content is a string
        if not isinstance(raw_content, str):
            raw_content = str(raw_content)
        
        cleaned = clean_response(raw_content)
        
        # Try JsonOutputParser first, fall back to json.loads if it fails
        try:
            parsed_result = JsonOutputParser().parse(cleaned)
        except Exception as parser_error:
            logger.warning(f"JsonOutputParser failed, falling back to json.loads(): {parser_error}")
            parsed_result = json.loads(cleaned)
        
        result = parsed_result
        state.follow_up_query = result["follow_up_query"]
        state.knowledge_gap = result["knowledge_gap"]
        state.search_query = state.follow_up_query
        state.stop_research = result["stop_research"]
        logger.info(f"Follow-up query: {state.follow_up_query}")
        logger.info(f"Knowledge gap: {state.knowledge_gap}")
        logger.info(f"Search query: {state.search_query}")
        logger.info(f"Stop research: {state.stop_research}")
    
        # Get tools with safe default (consistent with generate_query pattern)
        tools_to_use = result.get("tools", [])
        
        # Validate tools_to_use is a list
        if not isinstance(tools_to_use, list):
            logger.warning(f"Tools field is not a list, got {type(tools_to_use)}. Converting to list.")
            tools_to_use = [tools_to_use] if tools_to_use else []
        
        state.tools_to_use = tools_to_use
        logger.info(f"Tools to use: {state.tools_to_use}")
        return state

    # Finalize Summary Node
    async def generate_report(self, state: ResearchState) -> dict:
        """
        LangGraph node that finalizes the research summary.

        This node cleans and deduplicates the gathered sources, then uses an LLM to
        generate a final, beautifully formatted research report with a title,
        executive summary, and key findings, followed by a clean list of sources.
        """
        logger.info("--- Starting Generate Report Node ---")
        logger.info(f"Summary for article: {state.summary}")

        formated_prompt = final_report_instructions.format(
            current_date=current_date,
            research_topic=self.research_topic,
            summary=state.summary,
        )
        # 2. Use the LLM to generate the structured report as JSON
        result = await self.llm_thinking.ainvoke(formated_prompt)
        raw_content = result.content if hasattr(result, 'content') else str(result)
        
        # Handle case where raw_content is a list (extract first string element)
        if isinstance(raw_content, list):
            logger.warning(f"LLM returned a list instead of string in finalize_summary, extracting first element")
            if len(raw_content) > 0:
                raw_content = str(raw_content[0])
            else:
                raw_content = ""
        
        # Ensure raw_content is a string
        if not isinstance(raw_content, str):
            raw_content = str(raw_content)
        
        cleaned_content = clean_response(raw_content)
        try:
            report_data = JsonOutputParser().parse(cleaned_content)
        except Exception as parser_error:
            logger.warning(f"JsonOutputParser failed, falling back to json.loads(): {parser_error}")
            report_data = json.loads(cleaned_content)

        logger.info(f"Report data: {report_data}")

        try:
            report_content = report_data.get("report_content", "")
            title = report_data.get("title", "")
            key_findings = report_data.get("key_findings", [])
        except Exception as e:
            logger.error(f"Error parsing report data: {e}")
            logger.error(f"Report data: {report_data}")
            
        
        if not report_content or not title or not key_findings:
            logger.error("Report content, title, or key findings are missing")


        # Add formatted sources to the report
        # Deduplicate all accumulated sources before adding to report
        if state.sources_gathered:
            # Parse any formatted strings and ensure all are dicts
            all_sources = []
            for source_item in state.sources_gathered:
                if isinstance(source_item, dict):
                    all_sources.append(source_item)
                elif isinstance(source_item, str):
                    # Parse formatted string (backward compatibility)
                    lines = source_item.split("\n")
                    for line in lines:
                        line = line.strip()
                        if not line or line == "No valid sources found.":
                            continue
                        match = re.match(r'\d+\.\s*(?:\[([^\]]+)\]\s*)?([^(]+)\s*\(([^)]+)\)', line)
                        if match:
                            source_name, title, url = match.groups()
                            all_sources.append({
                                "name": source_name.strip() if source_name else "unknown",
                                "title": title.strip(),
                                "url": url.strip()
                            })
            
            # Deduplicate all accumulated sources
            unique_sources = deduplicate_sources(all_sources)
            formatted_sources = format_sources(unique_sources)
            report_data["sources"] = formatted_sources
            logger.info(f"Added {len(unique_sources)} unique sources to final report (from {len(all_sources)} total accumulated)")

        # Set the report in state so it's returned in the result
        state.report = report_data

        # Save report to database
        try:
            db = get_db_instance()
            report_id = db.save_research_report(
                research_topic=self.research_topic,
                title=title,
                executive_summary=report_content,
                key_findings=key_findings,
                sources=report_data.get("sources"),
                report_data=report_data,
                research_loop_count=state.research_loop_count,
            )
            logger.info(f"Research report saved to database with ID: {report_id}")
        except Exception as db_error:
            logger.error(f"Failed to save research report to database: {db_error}")
            # Don't fail the entire process if DB save fails
            logger.warning("Continuing despite database save failure")

        return state

    async def route_research(
        self, state: ResearchState, config: RunnableConfig
    ) -> Literal["generate_report", "web_research"]:
        """LangGraph routing function that determines the next step in the research flow.

        Controls the research loop by deciding whether to continue gathering information
        or to finalize the summary based on the configured maximum number of research loops.

        Args:
            state: Current graph state containing the research loop count
            config: Configuration for the runnable, including max_web_research_loops setting

        Returns:
            String literal indicating the next node to visit ("web_research" or "generate_report")
        """
        logger.info("--- Starting Route Research Node ---")

        # Check max loops first - hard limit
        if state.research_loop_count >= self.research_loop_max:
            logger.info(
                f"Research loop count: {state.research_loop_count} reached or exceeded max loops: {self.research_loop_max}, returning to generate_report"
            )
            return "generate_report"
        
        # Check if agent decided to stop research
        if state.stop_research:
            logger.info(
                f"Agent decided to stop research (summary is good enough), returning to generate_report"
            )
            return "generate_report"
        
        # Otherwise continue research
        logger.info(
            f"Research loop count: {state.research_loop_count} is less than max loops: {self.research_loop_max}, continuing research"
        )
        return "web_research"


# Alias for backward compatibility
DeepResearcher = ResearchGraph

