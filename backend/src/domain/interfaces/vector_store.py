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
    async def retrieve_by_marker(
        self,
        source: str,
        content_contains: str | None = None,
        contextual: bool = False,
    ) -> RetrievalResult:
        """Return chunk(s) from a known source document, bypassing vector
        similarity entirely.

        Used only by scripted demo sub-cases (Moment 2's quality-trap
        question, Moment 3's dedicated stale-context question) where the
        whole point is to reliably exercise a known document's
        downstream behavior (generation + judging) — not to test
        whether retrieval organically finds it. Everything downstream of
        retrieval (generation, judging) still runs for real; only which
        chunk(s) get selected is pinned. Never used for Moment 3's
        plain-vs-contextual comparison, where retrieval's own ranking
        behavior is the thing being demonstrated.

        Args:
            source: The exact `source` filename to look within (e.g.
                "backup_disaster_recovery_policy.md").
            content_contains: A substring that appears in exactly one
                chunk of that document — used to pin to one specific
                chunk when only part of a multi-chunk document matters
                (e.g. Moment 2's trap). If None, returns every chunk
                belonging to that source document instead — used when
                a question needs multiple facts from the same document
                together (e.g. Moment 3's two-part stale-context
                question, which needs both the stale support-response
                chunk and the stale refund chunk).
            contextual: Whether to look in the contextual collection
                instead of the plain one.

        Returns:
            A RetrievalResult with retrieval_mode="pinned", containing
            the matching chunk(s) (or zero chunks if no match is found —
            callers should treat an empty result as a misconfigured
            marker/source pair to fix, not a normal empty-retrieval
            case).
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