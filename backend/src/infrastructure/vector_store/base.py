"""Abstract base for vector store implementations.

Every concrete store (Qdrant, pgvector, Chroma) subclasses this rather
than implementing VectorStoreInterface directly, so shared/common
behavior (e.g. logging, common health-check shape) lives in one place.
"""
from abc import abstractmethod

from src.domain.entities.query import Query, RetrievalResult
from src.domain.interfaces.vector_store import VectorStoreInterface
from utils.logger import get_logger

logger = get_logger()


class BaseVectorStore(VectorStoreInterface):
    """Shared logging/error wrapping around concrete vector store calls.

    Concrete stores must implement `_do_retrieve`, `_do_upsert`, and
    `health_check`.
    """

    async def retrieve(
        self,
        query: Query,
        top_k: int = 2,
    ) -> RetrievalResult:
        """Log and delegate to the concrete store's retrieval logic.

        Args:
            query: The user's question and retrieval-mode preference.
            top_k: The maximum number of chunks to return.

        Returns:
            The retrieved chunks.
        """
        logger.debug(f"Retrieving top_k={top_k} for query: {query.text!r}")
        return await self._do_retrieve(query, top_k)

    async def upsert_documents(
        self,
        documents: list[dict],
    ) -> int:
        """Log and delegate to the concrete store's upsert logic.

        Args:
            documents: The documents to ingest.

        Returns:
            The number of documents ingested.
        """
        logger.info(f"Upserting {len(documents)} documents")
        return await self._do_upsert(documents)

    @abstractmethod
    async def _do_retrieve(
        self,
        query: Query,
        top_k: int,
    ) -> RetrievalResult:
        """Perform the actual retrieval against the concrete backend.

        Args:
            query: The user's question and retrieval-mode preference.
            top_k: The maximum number of chunks to return.
        """
        raise NotImplementedError

    @abstractmethod
    async def _do_upsert(
        self,
        documents: list[dict],
    ) -> int:
        """Perform the actual document ingestion against the concrete backend.

        Args:
            documents: The documents to ingest.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(
        self,
    ) -> bool:
        """Return True if the underlying store is reachable and healthy."""
        raise NotImplementedError
