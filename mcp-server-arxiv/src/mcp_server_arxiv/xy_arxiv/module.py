from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache

import arxiv
import fitz

from mcp_server_arxiv.xy_arxiv.config import ArxivConfig, get_arxiv_config
from mcp_server_arxiv.xy_arxiv.errors import ArxivApiError, ArxivServiceError
from mcp_server_arxiv.xy_arxiv.models import ArxivSearchResult

logger = logging.getLogger(__name__)

_THREAD_POOL_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor()
_PROCESS_POOL_EXECUTOR: ProcessPoolExecutor = ProcessPoolExecutor()


@dataclass(frozen=True)
class _PaperContext:
    paper: arxiv.Result
    arxiv_id: str
    pdf_url: str | None


def _parse_pdf_sync(temp_pdf_path: str) -> str:
    doc = fitz.open(temp_pdf_path)
    try:
        extracted_pages = [page.get_text("text", sort=True) for page in doc]
    finally:
        doc.close()
    return "\n".join(extracted_pages).strip()


@lru_cache(maxsize=1)
def get_arxiv_service() -> _ArxivService:
    config = get_arxiv_config()
    return _ArxivService(config)


class _ArxivService:
    def __init__(self, config: ArxivConfig):
        self.config = config
        self.client = arxiv.Client()
        logger.info("_ArxivService initialized.")

    async def search(
        self,
        *,
        query: str | None = None,
        arxiv_id: str | None = None,
        max_results: int | None = None,
        max_text_length: int | None = None,
    ) -> list[ArxivSearchResult]:
        try:
            normalized_query, normalized_id = self._validate_inputs(query, arxiv_id)
            effective_max_results = self._resolve_max_results(max_results)
            effective_max_text_length = self._resolve_max_text_length(max_text_length)
            search_params, expected_id = self._build_search(
                normalized_query,
                normalized_id,
                effective_max_results,
            )
            papers_metadata = await self._fetch_papers_metadata(
                search_params, expected_id=expected_id
            )
            if not papers_metadata:
                logger.info("No papers found on ArXiv for query '%s'", normalized_query)
                return []

            with tempfile.TemporaryDirectory(prefix="arxiv_pdf_") as temp_dir:
                if expected_id:
                    single_result = await self._process_single_paper(
                        papers_metadata[0],
                        temp_dir,
                        effective_max_text_length,
                    )
                    return [single_result]
                return await self._process_multiple_papers(
                    papers_metadata,
                    temp_dir,
                    effective_max_text_length,
                )
        except (ValueError, ArxivApiError):
            raise
        except Exception as exc:
            logger.error("Error during ArXiv operation: %s", exc, exc_info=True)
            raise ArxivServiceError(
                f"An unexpected error occurred during the ArXiv operation: {exc}"
            ) from exc

    def _validate_inputs(
        self, query: str | None, arxiv_id: str | None
    ) -> tuple[str | None, str | None]:
        # Normalize inputs first
        normalized_query = query.strip() if isinstance(query, str) and query else None
        normalized_id = arxiv_id.strip() if isinstance(arxiv_id, str) and arxiv_id else None

        # Check for empty strings
        if isinstance(query, str) and not normalized_query:
            raise ValueError("Query cannot be empty")
        if isinstance(arxiv_id, str) and not normalized_id:
            raise ValueError("arxiv_id cannot be empty")

        # Check for conflicts and missing inputs
        if normalized_query and normalized_id:
            raise ValueError("Cannot provide both 'query' and 'arxiv_id'")
        if not normalized_query and not normalized_id:
            raise ValueError("Either 'query' or 'arxiv_id' must be provided")

        return normalized_query, normalized_id

    def _resolve_max_results(self, override: int | None) -> int:
        effective = override if override is not None else self.config.max_results
        if effective is None or effective < 1:
            raise ValueError("max_results must be greater than 0")
        return effective

    def _resolve_max_text_length(self, override: int | None) -> int | None:
        if override is None:
            return self.config.max_text_length
        if override < 100:
            raise ValueError("max_text_length must be at least 100 characters")
        return override

    def _build_search(
        self,
        query: str | None,
        arxiv_id: str | None,
        max_results: int,
    ) -> tuple[arxiv.Search, str | None]:
        if arxiv_id:
            logger.info("Fetching ArXiv paper by ID: %s", arxiv_id)
            return arxiv.Search(id_list=[arxiv_id], max_results=1), arxiv_id

        assert query is not None
        logger.info("Performing ArXiv search for query: '%s...'", query[:100])
        return (
            arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            ),
            None,
        )

    async def _fetch_papers_metadata(
        self,
        search_params: arxiv.Search,
        *,
        expected_id: str | None = None,
    ) -> list[arxiv.Result]:
        loop = asyncio.get_running_loop()
        try:
            results_iterator = self.client.results(search_params)
            papers_list: list[arxiv.Result] = await loop.run_in_executor(
                _THREAD_POOL_EXECUTOR, list, results_iterator
            )
            if expected_id and not papers_list:
                raise ArxivApiError(f"Paper with ID {expected_id} not found on ArXiv")
            return papers_list
        except ArxivApiError:
            raise
        except Exception as exc:
            logger.error("Error fetching papers from ArXiv: %s", exc, exc_info=True)
            raise ArxivApiError(f"Failed to retrieve papers from ArXiv: {exc}") from exc

    async def _process_single_paper(
        self,
        paper_obj: arxiv.Result,
        temp_dir: str,
        max_text_length: int | None,
    ) -> ArxivSearchResult:
        if not isinstance(paper_obj, arxiv.Result):
            raise ArxivApiError(f"Unexpected result type from ArXiv: {type(paper_obj)}")
        context = self._build_context(paper_obj)
        return await self._process_context(context, temp_dir, max_text_length)

    async def _process_multiple_papers(
        self,
        papers_metadata: list[arxiv.Result],
        temp_dir: str,
        max_text_length: int | None,
    ) -> list[ArxivSearchResult]:
        contexts: list[_PaperContext] = []
        tasks: list[asyncio.Task[ArxivSearchResult]] = []

        for paper_obj in papers_metadata:
            if not isinstance(paper_obj, arxiv.Result):
                logger.warning(
                    "Skipping non-Result item from ArXiv: %s",
                    type(paper_obj),
                )
                continue
            context = self._build_context(paper_obj)
            contexts.append(context)
            tasks.append(
                asyncio.create_task(
                    self._process_context(context, temp_dir, max_text_length),
                    name=f"pdf_process_{context.arxiv_id}",
                )
            )

        if not tasks:
            return []

        processed = await asyncio.gather(*tasks, return_exceptions=True)
        final_results: list[ArxivSearchResult] = []

        for context, result in zip(contexts, processed, strict=False):
            if isinstance(result, ArxivSearchResult):
                final_results.append(result)
            else:
                logger.error(
                    "Task for paper %s failed: %s",
                    context.arxiv_id,
                    result,
                    exc_info=isinstance(result, Exception),
                )
                final_results.append(self._build_error_result(context.paper, result))

        logger.info("ArXiv search successful, processed %d papers", len(final_results))
        return final_results

    def _build_context(self, paper_obj: arxiv.Result) -> _PaperContext:
        return _PaperContext(
            paper=paper_obj,
            arxiv_id=paper_obj.get_short_id(),
            pdf_url=paper_obj.pdf_url,
        )

    async def _process_context(
        self,
        context: _PaperContext,
        temp_dir: str,
        max_text_length: int | None,
    ) -> ArxivSearchResult:
        pdf_path: str | None = None
        try:
            pdf_path = await self._download_pdf(context, temp_dir)
            full_text = await self._parse_pdf(pdf_path)
            normalized_text = self._normalize_full_text(full_text, max_text_length)
            return self._build_result(context, normalized_text, None)
        except FileNotFoundError:
            message = "[Download failed or file not found after download attempt]"
            logger.error("Error for %s: %s", context.arxiv_id, message)
            return self._build_result(context, None, message)
        except fitz.fitz.FitzError as exc:
            message = f"[Failed to parse PDF: {exc}]"
            logger.error("Error for %s: %s", context.arxiv_id, message)
            return self._build_result(context, None, message)
        except Exception as exc:
            message = (
                f"[Unexpected error processing PDF {context.arxiv_id}: "
                f"{type(exc).__name__} - {exc}]"
            )
            logger.error("Error for %s: %s", context.arxiv_id, message, exc_info=True)
            return self._build_result(context, None, message)
        finally:
            self._cleanup_temp_file(pdf_path)

    async def _download_pdf(self, context: _PaperContext, temp_dir: str) -> str:
        safe_filename = f"{context.arxiv_id.replace('/', '_')}.pdf"
        temp_pdf_path = os.path.join(temp_dir, safe_filename)
        logger.info("Downloading PDF for %s to %s", context.arxiv_id, temp_pdf_path)

        loop = asyncio.get_running_loop()

        def _download() -> None:
            context.paper.download_pdf(dirpath=temp_dir, filename=safe_filename)

        await loop.run_in_executor(_THREAD_POOL_EXECUTOR, _download)
        logger.info("Download successful for %s", context.arxiv_id)
        return temp_pdf_path

    async def _parse_pdf(self, temp_pdf_path: str) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _PROCESS_POOL_EXECUTOR,
            _parse_pdf_sync,
            temp_pdf_path,
        )

    def _cleanup_temp_file(self, temp_pdf_path: str | None) -> None:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                logger.debug("Deleted temporary PDF: %s", temp_pdf_path)
            except Exception as exc:
                logger.warning(
                    "Failed to delete temporary PDF %s: %s",
                    temp_pdf_path,
                    exc,
                )

    def _normalize_full_text(self, text: str, max_length: int | None) -> str:
        cleaned = text.strip()
        if not cleaned:
            return "[Could not extract text content from PDF]"
        if max_length is not None and len(cleaned) > max_length:
            return f"{cleaned[:max_length]}... (truncated to {max_length} chars)"
        return cleaned

    def _build_result(
        self,
        context: _PaperContext,
        full_text: str | None,
        processing_error: str | None,
    ) -> ArxivSearchResult:
        paper = context.paper
        published_value = (
            paper.published.strftime("%Y-%m-%d") if paper.published else "N/A"
        )
        authors = [author.name for author in paper.authors]

        return ArxivSearchResult(
            title=paper.title,
            authors=authors,
            published_date=published_value,
            summary=paper.summary,
            arxiv_id=context.arxiv_id,
            pdf_url=context.pdf_url,
            full_text=full_text,
            processing_error=processing_error,
        )

    def _build_error_result(
        self,
        paper_obj: arxiv.Result,
        error: Exception | BaseException,
    ) -> ArxivSearchResult:
        message = f"Failed during PDF processing: {type(error).__name__} - {error}"
        return ArxivSearchResult(
            title=paper_obj.title,
            authors=[author.name for author in paper_obj.authors],
            published_date=(
                paper_obj.published.strftime("%Y-%m-%d")
                if paper_obj.published
                else "N/A"
            ),
            summary=paper_obj.summary,
            arxiv_id=paper_obj.get_short_id(),
            pdf_url=paper_obj.pdf_url,
            processing_error=message,
        )

