import logging

from fastapi import APIRouter, Request
from fastmcp.exceptions import ToolError

from qdrant_client.models import CollectionInfo, ScoredPoint

from mcp_server_qdrant.qdrant import Entry, QdrantConnector
from mcp_server_qdrant.schemas import (
    QdrantStoreRequest,
    QdrantFindRequest,
    QdrantGetCollectionInfoRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/store",
    tags=["Qdrant"],
    operation_id="qdrant_store",
)
async def qdrant_store(
    request_body: QdrantStoreRequest,
    request: Request,
) -> str:
    """
    Keep the memory for later use, when you are asked to remember something.
    The collection will be created automatically with configured settings if it doesn't exist.
    """
    qdrant_connector: QdrantConnector = request.app.state.qdrant_connector

    try:
        # Execute core logic using the validated request data
        entry = Entry(
            content=request_body.information, metadata=request_body.metadata
        )
        await qdrant_connector.store(
            entry, collection_name=request_body.collection_name
        )

        logger.info(
            f"Successfully stored information in collection {request_body.collection_name}"
        )
        return f"Remembered: {request_body.information} in collection {request_body.collection_name}"

    except Exception as e:
        logger.error(f"Error storing information: {e}", exc_info=True)
        raise ToolError(f"Error storing information: {e}") from e


@router.post(
    "/find",
    tags=["Qdrant"],
    operation_id="qdrant_find",
)
async def qdrant_find(
    request_body: QdrantFindRequest,
    request: Request,
) -> list[ScoredPoint] | str:
    """
    Look up memories in Qdrant. Use this tool when you need to find memories by their content.
    You can optionally filter by metadata fields (e.g., {"metadata.user_id": "alice", "metadata.category": "work"}).
    Filtering by tenant fields (if configured) will be much faster than filtering by other fields.
    """
    qdrant_connector: QdrantConnector = request.app.state.qdrant_connector

    try:
        # Execute core logic using the validated request data
        search_results = await qdrant_connector.search(
            request_body.query,
            collection_name=request_body.collection_name,
            limit=request_body.search_limit,
            filters=request_body.filters,
        )

        # Format response
        if not search_results:
            message = f"No information found for the query '{request_body.query}'"
            logger.info(message)
            return message

        logger.info(
            f"Successfully searched Qdrant with {len(search_results.points)} results"
        )
        return search_results.points

    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}", exc_info=True)
        raise ToolError(f"Error searching Qdrant: {e}") from e


@router.post(
    "/get_collection_info",
    tags=["Qdrant"],
    operation_id="qdrant_get_collection_info",
)
async def qdrant_get_collection_info(
    request_body: QdrantGetCollectionInfoRequest,
    request: Request,
) -> CollectionInfo | dict[str, str]:
    """
    Retrieves detailed configuration and schema information for a specific Qdrant collection.
    Use this to understand how a collection is set up, what fields are indexed,
    if it's configured for multi-tenancy, and its vector parameters.
    """
    qdrant_connector: QdrantConnector = request.app.state.qdrant_connector

    try:
        collection_details = await qdrant_connector.get_collection_details(
            request_body.collection_name
        )
        logger.info(
            f"Successfully retrieved details for collection {request_body.collection_name}"
        )
        return collection_details

    except Exception as e:
        collection_name = request_body.collection_name

        logger.error(
            f"Error getting info for collection '{collection_name}': {e}", exc_info=True
        )
        # Return a structured error dict for the LLM rather than raising ToolError
        return {
            "error": f"Failed to get information for collection '{collection_name}': {str(e)}"
        }


@router.post(
    "/get_collections",
    tags=["Qdrant"],
    operation_id="qdrant_get_collections",
)
async def qdrant_get_collections(
    request: Request,
) -> list[str]:
    """
    Retrieves the names of all collections in the Qdrant database.
    Use this to discover what collections are available before storing or searching data.
    """
    qdrant_connector: QdrantConnector = request.app.state.qdrant_connector

    try:
        collection_names = await qdrant_connector.get_collection_names()
        logger.info(f"Successfully retrieved {len(collection_names)} collection names")
        return collection_names

    except Exception as e:
        logger.error(f"Error getting collection names: {e}", exc_info=True)
        raise ToolError(f"Error getting collection names: {e}") from e
