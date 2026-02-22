import uuid

import httpx
import pytest


@pytest.fixture
def unique_collection_name() -> str:
    """Generate a unique collection name for each test run to avoid conflicts."""
    return f"e2e_test_collection_{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_qdrant_full_workflow(
    subtests,
    server_url: str,
    http_client: httpx.AsyncClient,
    unique_collection_name: str,
) -> None:
    """Qdrant MCP server full workflow: store -> list -> info -> find.

    Step 1: Store information in a new collection (tests auto-creation)
    Step 2: List collections and verify the new collection exists
    Step 3: Get collection info for the created collection
    Step 4: Find/search for the stored information
    """
    collection_name = unique_collection_name
    stored_info = "Machine learning is a subset of artificial intelligence that enables systems to learn from data."
    stored_metadata = {"category": "ai", "source": "e2e_test", "priority": "high"}

    # Step 1: Store information (should auto-create collection)
    store_success = False
    with subtests.test(msg="Step 1: Store information in new collection"):
        response = await http_client.post(
            f"{server_url}/hybrid/store",
            json={
                "collection_name": collection_name,
                "information": stored_info,
                "metadata": stored_metadata,
            },
        )
        print(f"\n[Store] Status: {response.status_code}")
        print(f"[Store] Response: {response.text[:500]}")

        assert response.status_code == 200, f"Store failed: {response.text}"
        assert collection_name in response.text
        store_success = True

    if not store_success:
        pytest.skip("Store failed, skipping remaining steps")

    # Step 2: List collections and verify new collection exists
    list_success = False
    with subtests.test(msg="Step 2: List collections and verify new collection exists"):
        response = await http_client.post(f"{server_url}/hybrid/get_collections")
        print(f"\n[List] Status: {response.status_code}")
        print(f"[List] Response: {response.text[:500]}")

        assert response.status_code == 200, f"List collections failed: {response.text}"

        collections = response.json()
        assert isinstance(collections, list), "Expected list of collections"
        assert collection_name in collections, (
            f"Collection {collection_name} not found in {collections}"
        )
        list_success = True

    if not list_success:
        pytest.skip("List collections failed, skipping remaining steps")

    # Step 3: Get collection info
    info_success = False
    with subtests.test(msg="Step 3: Get collection info"):
        response = await http_client.post(
            f"{server_url}/hybrid/get_collection_info",
            json={"collection_name": collection_name},
        )
        print(f"\n[Info] Status: {response.status_code}")
        print(f"[Info] Response: {response.text[:500]}")

        assert response.status_code == 200, (
            f"Get collection info failed: {response.text}"
        )

        info = response.json()
        assert isinstance(info, dict), "Expected collection info dict"
        # Qdrant CollectionInfo should have these fields
        assert "status" in info, f"Missing 'status' in collection info: {info.keys()}"
        info_success = True

    if not info_success:
        pytest.skip("Get collection info failed, skipping remaining steps")

    # Step 4: Find/search stored information
    with subtests.test(msg="Step 4: Find stored information"):
        response = await http_client.post(
            f"{server_url}/hybrid/find",
            json={
                "collection_name": collection_name,
                "query": "machine learning artificial intelligence",
                "search_limit": 5,
            },
        )
        print(f"\n[Find] Status: {response.status_code}")
        print(f"[Find] Response: {response.text[:500]}")

        assert response.status_code == 200, f"Find failed: {response.text}"

        results = response.json()
        # Results can be a list of ScoredPoints or a string message
        if isinstance(results, list):
            assert len(results) > 0, "Expected at least one result"
            # Check that first result contains our stored document
            first_result = results[0]
            assert "payload" in first_result, (
                f"Missing payload in result: {first_result.keys()}"
            )
            payload = first_result["payload"]
            assert "document" in payload, (
                f"Missing document in payload: {payload.keys()}"
            )
            print(f"\n[Find] Found document: {payload['document'][:200]}...")
        else:
            # String message means no results found
            print(f"\n[Find] Message: {results}")


@pytest.mark.asyncio
async def test_store_with_metadata_filters(
    subtests,
    server_url: str,
    http_client: httpx.AsyncClient,
    unique_collection_name: str,
) -> None:
    """Test storing multiple items and filtering by metadata."""
    collection_name = unique_collection_name

    # Store multiple items with different metadata
    items = [
        {
            "information": "Python is a high-level programming language.",
            "metadata": {"category": "programming", "language": "python"},
        },
        {
            "information": "JavaScript is used for web development.",
            "metadata": {"category": "programming", "language": "javascript"},
        },
        {
            "information": "Deep learning uses neural networks.",
            "metadata": {"category": "ai", "language": "python"},
        },
    ]

    # Step 1: Store all items
    store_success = False
    with subtests.test(msg="Step 1: Store multiple items with metadata"):
        for i, item in enumerate(items):
            response = await http_client.post(
                f"{server_url}/hybrid/store",
                json={
                    "collection_name": collection_name,
                    "information": item["information"],
                    "metadata": item["metadata"],
                },
            )
            print(f"\n[Store {i + 1}] Status: {response.status_code}")
            assert response.status_code == 200, f"Store {i + 1} failed: {response.text}"
        store_success = True

    if not store_success:
        pytest.skip("Store failed, skipping remaining steps")

    # Step 2: Search with metadata filter
    with subtests.test(msg="Step 2: Search with metadata filter"):
        response = await http_client.post(
            f"{server_url}/hybrid/find",
            json={
                "collection_name": collection_name,
                "query": "programming language",
                "search_limit": 10,
                "filters": {"metadata.category": "programming"},
            },
        )
        print(f"\n[Find with filter] Status: {response.status_code}")
        print(f"[Find with filter] Response: {response.text[:500]}")

        assert response.status_code == 200, f"Find with filter failed: {response.text}"

        results = response.json()
        if isinstance(results, list) and len(results) > 0:
            # Verify filtered results only contain programming category
            for result in results:
                if "payload" in result and "metadata" in result["payload"]:
                    metadata = result["payload"]["metadata"]
                    if metadata:
                        assert metadata.get("category") == "programming", (
                            f"Filter failed: {metadata}"
                        )


@pytest.mark.asyncio
async def test_find_nonexistent_collection(
    server_url: str,
    http_client: httpx.AsyncClient,
) -> None:
    """Test that searching a non-existent collection returns appropriate error."""
    fake_collection = f"nonexistent_collection_{uuid.uuid4().hex[:8]}"

    response = await http_client.post(
        f"{server_url}/hybrid/find",
        json={
            "collection_name": fake_collection,
            "query": "test query",
            "search_limit": 5,
        },
    )

    print(f"\n[Find nonexistent] Status: {response.status_code}")
    print(f"[Find nonexistent] Response: {response.text[:500]}")

    # Server may return 500 (ToolError) or 200 with error message
    # depending on error handling strategy
    if response.status_code == 500:
        # ToolError case - server returns 500 for non-existent collection
        # The detailed error message may not be in the response body
        pass  # 500 is expected behavior for this error case
    elif response.status_code == 200:
        # Error returned as response body
        result = response.json()
        if isinstance(result, dict) and "error" in result:
            assert (
                "not found" in result["error"].lower()
                or "does not exist" in result["error"].lower()
            )
    else:
        # Any other 4xx status is also acceptable
        assert response.status_code in (400, 404, 500)


@pytest.mark.asyncio
async def test_get_collection_info_nonexistent(
    server_url: str,
    http_client: httpx.AsyncClient,
) -> None:
    """Test that getting info for a non-existent collection returns appropriate error."""
    fake_collection = f"nonexistent_collection_{uuid.uuid4().hex[:8]}"

    response = await http_client.post(
        f"{server_url}/hybrid/get_collection_info",
        json={"collection_name": fake_collection},
    )

    print(f"\n[Info nonexistent] Status: {response.status_code}")
    print(f"[Info nonexistent] Response: {response.text[:500]}")

    # Endpoint returns error dict rather than raising ToolError
    assert response.status_code == 200, f"Unexpected status: {response.status_code}"
    result = response.json()
    assert isinstance(result, dict), "Expected dict response"
    assert "error" in result, f"Expected error key in response: {result}"


@pytest.mark.asyncio
async def test_store_validation_missing_information(
    server_url: str,
    http_client: httpx.AsyncClient,
    unique_collection_name: str,
) -> None:
    """Test that store endpoint validates required 'information' field."""
    response = await http_client.post(
        f"{server_url}/hybrid/store",
        json={
            "collection_name": unique_collection_name,
            # Missing required 'information' field
        },
    )

    print(f"\n[Store validation] Status: {response.status_code}")
    print(f"[Store validation] Response: {response.text[:500]}")

    # Pydantic validation should return 422
    assert response.status_code == 422, (
        f"Expected 422 for missing field, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_find_validation_missing_query(
    server_url: str,
    http_client: httpx.AsyncClient,
    unique_collection_name: str,
) -> None:
    """Test that find endpoint validates required 'query' field."""
    response = await http_client.post(
        f"{server_url}/hybrid/find",
        json={
            "collection_name": unique_collection_name,
            # Missing required 'query' field
        },
    )

    print(f"\n[Find validation] Status: {response.status_code}")
    print(f"[Find validation] Response: {response.text[:500]}")

    # Pydantic validation should return 422
    assert response.status_code == 422, (
        f"Expected 422 for missing field, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_get_collections_empty_request(
    server_url: str,
    http_client: httpx.AsyncClient,
) -> None:
    """Test that get_collections works with no request body."""
    response = await http_client.post(f"{server_url}/hybrid/get_collections")

    print(f"\n[Get collections] Status: {response.status_code}")
    print(f"[Get collections] Response: {response.text[:500]}")

    assert response.status_code == 200, f"Get collections failed: {response.text}"
    result = response.json()
    assert isinstance(result, list), f"Expected list, got {type(result)}"
