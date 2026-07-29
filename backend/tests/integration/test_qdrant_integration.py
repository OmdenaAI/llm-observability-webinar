"""Integration test — requires a real Qdrant instance (make run first).

TODO: implement once QdrantVectorStore._do_retrieve/_do_upsert are wired.
Marked skip for now so `make test-integration` doesn't fail on the stub.
"""
import pytest

pytestmark = pytest.mark.skip(reason="QdrantVectorStore implementation pending")


async def test_qdrant_upsert_and_retrieve_roundtrip():
    pass
