"""Contract every vector store implementation must satisfy.

core/ depends only on this interface — never on Qdrant, pgvector, or
Chroma directly. Swapping the backend is a container binding change.
"""
from abc import ABC, abstractmethod

from src.domain.entities.query import Query, RetrievalResult


class VectorStoreInterface(ABC):
    """Abstract contract for retrieving and ingesting document chunks."""

    @abstractmethod
    async def retrieve(
        self,
        query: Query,
        top_k: int = 2,
    ) -> RetrievalResult:
        """Return the top_k most relevant chunks for the given query.

        Implementations are responsible for honoring
        `query.use_contextual_retrieval` — either by routing to a
        different index/strategy internally, or by raising
        NotImplementedError if the backend doesn't support it.

        Args:
            query: The user's question and retrieval-mode preference.
            top_k: The maximum number of chunks to return. Defaults to
                2 rather than a larger number specifically because the
                demo corpus only has 3 documents — a higher top_k meant
                every retrieval, plain or contextual, returned nearly
                the whole corpus regardless of mode, which silently
                erased the plain-vs-contextual distinction Moment 3
                exists to demonstrate (confirmed via a live run showing
                identical 1.0/1.0 scores in both modes).

        Returns:
            The retrieved chunks, wrapped with the originating query and
            the retrieval mode actually used.
        """
        raise NotImplementedError

    @abstractmethod
    async def upsert_documents(
        self,
        documents: list[dict],
    ) -> int:
        """Load or refresh documents into the store.

        Used by the seed/ingest script, not by the live request path.

        Args:
            documents: A list of document dicts, each expected to
                contain at least `content` and `source` keys.

        Returns:
            The number of documents successfully ingested.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(
        self,
    ) -> bool:
        """Return True if the underlying store is reachable and healthy."""
        raise NotImplementedError
