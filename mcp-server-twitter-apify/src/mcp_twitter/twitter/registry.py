from __future__ import annotations

from typing import Sequence

from mcp_twitter.twitter.models import QueryDefinition, QueryType


class QueryRegistry:
    """Holds predefined queries and provides convenient lookups."""

    def __init__(self, queries_by_type: dict[QueryType, Sequence[QueryDefinition]]):
        self._by_type: dict[QueryType, list[QueryDefinition]] = {
            k: list(v) for k, v in queries_by_type.items()
        }
        self._by_id: dict[str, QueryDefinition] = {}
        for q_type, qs in self._by_type.items():
            for q in qs:
                if q.type != q_type:
                    q.type = q_type
                self._by_id[q.id] = q

    def types(self) -> list[QueryType]:
        return list(self._by_type.keys())

    def list_queries(self, query_type: QueryType | None = None) -> list[QueryDefinition]:
        if query_type:
            return list(self._by_type.get(query_type, []))
        out: list[QueryDefinition] = []
        for qs in self._by_type.values():
            out.extend(qs)
        return out

    def get(self, query_id: str) -> QueryDefinition | None:
        return self._by_id.get(query_id)

    def by_type(self, query_type: QueryType) -> list[QueryDefinition]:
        return list(self._by_type.get(query_type, []))


