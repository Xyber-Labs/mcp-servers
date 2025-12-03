from __future__ import annotations

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.payment_agnostic
async def test_hybrid_search_by_id_via_rest(rest_client) -> None:
    config, client = rest_client
    payload = {"arxiv_id": "1706.03762"}
    response = await client.post("/hybrid/search", json=payload)
    # This endpoint should require payment (402) or succeed if payment is configured
    if response.status_code == 402:
        body = response.json()
        assert "accepts" in body and body["accepts"]
        assert body.get("error")
    elif response.status_code == 200:
        result = response.json()
        # When searching by ID, returns a list with a single item
        assert isinstance(result, list)
        assert len(result) == 1
        paper = result[0]
        # Arxiv returns versioned IDs (e.g., "1706.03762v7"), so check it starts with the base ID
        assert paper["arxiv_id"].startswith("1706.03762")
        assert "title" in paper
        assert "authors" in paper
    else:
        # Might be 404 if paper not found, or 503 if service error
        assert response.status_code in [404, 503]

