from __future__ import annotations

from typing import Any, Iterator


class FakeApifyDataset:
    def __init__(self, items: list[dict[str, Any]]):
        self._items = items

    def iterate_items(self) -> Iterator[dict[str, Any]]:
        yield from self._items


class FakeApifyActor:
    def __init__(self, dataset_id: str, record_calls: list[dict[str, Any]]):
        self._dataset_id = dataset_id
        self._record_calls = record_calls

    def call(self, run_input: dict[str, Any]) -> dict[str, Any]:
        self._record_calls.append(run_input)
        return {"defaultDatasetId": self._dataset_id}


class FakeApifyClient:
    def __init__(self, dataset_id: str, items: list[dict[str, Any]]):
        self._dataset_id = dataset_id
        self._items = items
        self.calls: list[dict[str, Any]] = []
        self.actor_ids: list[str] = []

    def actor(self, actor_id: str) -> FakeApifyActor:
        self.actor_ids.append(actor_id)
        return FakeApifyActor(self._dataset_id, self.calls)

    def dataset(self, dataset_id: str) -> FakeApifyDataset:
        assert dataset_id == self._dataset_id
        return FakeApifyDataset(self._items)


