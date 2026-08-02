"""Wraps a VectorStoreInterface with cross-cutting concerns (retries,
timeouts) that shouldn't live in either the domain interface or the
concrete store implementation.

Note: tracing spans for retrieval are currently created in
RAGOrchestrator itself, not here, to keep a single span per logical step
and avoid nested/duplicate spans. This service is the place to add
retry/backoff logic if the demo's vector store proves flaky, without
touching RAGOrchestrator or the concrete store.
"""
from src.domain.entities.query import Query, RetrievalResult
from src.domain.interfaces.vector_store import VectorStoreInterface


class RetrievalService(VectorStoreInterface):
    """Retry-wrapping decorator around a concrete VectorStoreInterface."""

    def __init__(
        self,
        vector_store: VectorStoreInterface,
        max_retries: int = 2,
    ) -> None:
        """Initialize the service.

        Args:
            vector_store: The underlying vector store to delegate to.
            max_retries: How many additional attempts to make on
                retrieval failure before giving up.
        """
        self._vector_store = vector_store
        self._max_retries = max_retries

    async def retrieve(
        self,
        query: Query,
        top_k: int = 2,
    ) -> RetrievalResult:
        """Retrieve chunks, retrying on failure up to max_retries times.

        Args:
            query: The user's question and retrieval-mode preference.
            top_k: The maximum number of chunks to return.

        Raises:
            Exception: The last error encountered, if all attempts fail.
        """
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._vector_store.retrieve(query, top_k)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        raise last_error  # type: ignore[misc]

    async def retrieve_by_marker(
        self,
        source: str,
        content_contains: str,
        contextual: bool = False,
    ) -> RetrievalResult:
        """Retrieve a pinned chunk, retrying on failure up to max_retries times.

        Args:
            source: The exact source filename to look within.
            content_contains: A substring identifying the specific chunk.
            contextual: Whether to look in the contextual collection.

        Raises:
            Exception: The last error encountered, if all attempts fail.
        """
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._vector_store.retrieve_by_marker(
                    source, content_contains, contextual
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        raise last_error  # type: ignore[misc]

    async def upsert_documents(
        self,
        documents: list[dict],
    ) -> int:
        """Delegate document ingestion to the underlying store.

        Args:
            documents: The documents to ingest.
        """
        return await self._vector_store.upsert_documents(documents)

    async def health_check(
        self,
    ) -> bool:
        """Delegate the health check to the underlying store."""
        return await self._vector_store.health_check()