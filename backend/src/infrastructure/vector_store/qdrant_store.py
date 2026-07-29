"""Qdrant implementation of the vector store contract.

Uses OpenAI's embedding API (text-embedding-3-small by default) for
both ingestion and query embedding. Qdrant itself needs no auth for
local Docker use; the only credential required here is OPENAI_API_KEY.

Manages TWO collections to support Moment 3's plain-vs-contextual
retrieval comparison: `{collection_name}` (plain document content) and
`{collection_name}_contextual` (content prefixed with a short
LLM-generated context blurb — see contextualizer.py). Both must be
populated via data/ingest.py before Moment 3 will show a real
faithfulness delta; if the contextual collection is empty,
`_do_retrieve` falls back to the plain collection with a warning log
rather than erroring, so a missed ingestion step degrades gracefully
instead of crashing the demo mid-question.
"""
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qdrant_models
from openai import AsyncOpenAI

from src.domain.entities.query import Query, RetrievalResult, RetrievedChunk
from src.infrastructure.vector_store.base import BaseVectorStore
from utils.logger import get_logger

logger = get_logger()

# text-embedding-3-small produces 1536-dimensional vectors. If
# openai_embedding_model is changed to a different OpenAI embedding model,
# this must be updated to match (e.g. text-embedding-3-large is 3072).
EMBEDDING_DIMENSIONS = 1536


class QdrantVectorStore(BaseVectorStore):
    """Vector store backed by Qdrant, embedded via OpenAI, with plain +
    contextual collections."""

    def __init__(
        self,
        url: str,
        collection_name: str = "demo_corpus",
        openai_api_key: str = "",
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        """Initialize the store's Qdrant and OpenAI embedding clients.

        Args:
            url: The base URL of the Qdrant instance.
            collection_name: The name of the plain-content collection.
                The contextual collection is derived as
                f"{collection_name}_contextual".
            openai_api_key: API key used for the embedding calls.
            embedding_model: The OpenAI embedding model to use for both
                ingestion and query embedding — must match on both
                sides, since a query embedded with a different model
                than the corpus would produce meaningless similarity
                scores.
        """
        self._collection_name = collection_name
        self._contextual_collection_name = f"{collection_name}_contextual"
        self._embedding_model = embedding_model
        self._client = AsyncQdrantClient(url=url)
        self._embedding_client = AsyncOpenAI(api_key=openai_api_key)

    async def _embed(
        self,
        text: str,
    ) -> list[float]:
        """Embed a single piece of text via the OpenAI embeddings API.

        Args:
            text: The text to embed.

        Returns:
            The embedding vector.
        """
        response = await self._embedding_client.embeddings.create(
            model=self._embedding_model,
            input=text,
        )
        return response.data[0].embedding

    async def _ensure_collection(
        self,
        collection_name: str,
    ) -> None:
        """Create the given collection if it doesn't already exist.

        Args:
            collection_name: The collection to check/create.
        """
        exists = await self._client.collection_exists(collection_name)
        if not exists:
            logger.info(f"Creating Qdrant collection '{collection_name}'")
            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=EMBEDDING_DIMENSIONS,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )

    async def _do_retrieve(
        self,
        query: Query,
        top_k: int,
    ) -> RetrievalResult:
        """Embed the query and search the appropriate Qdrant collection.

        Searches `_contextual_collection_name` when
        `query.use_contextual_retrieval` is set, falling back to the
        plain collection (with a warning) if the contextual collection
        doesn't exist yet — e.g. because `make seed` hasn't been run
        with contextualization enabled.

        Args:
            query: The user's question and retrieval-mode preference.
            top_k: The maximum number of chunks to return.

        Returns:
            The retrieved chunks, mapped from Qdrant search hits.
        """
        target_collection = self._collection_name
        retrieval_mode = "plain"

        if query.use_contextual_retrieval:
            contextual_exists = await self._client.collection_exists(
                self._contextual_collection_name,
            )
            if contextual_exists:
                target_collection = self._contextual_collection_name
                retrieval_mode = "contextual"
            else:
                logger.warning(
                    f"Contextual collection '{self._contextual_collection_name}' "
                    "does not exist — falling back to plain retrieval. "
                    "Run `make seed` to populate it."
                )

        vector = await self._embed(query.text)

        # NOTE: .search() was removed from AsyncQdrantClient in current
        # qdrant-client versions (confirmed via a live run against
        # qdrant-client 1.18.0 — .search() raised AttributeError).
        # .query_points() is the current replacement; unlike .search(),
        # it returns a QueryResponse wrapping the hits in `.points`,
        # not the list of hits directly.
        response = await self._client.query_points(
            collection_name=target_collection,
            query=vector,
            limit=top_k,
        )
        hits = response.points

        chunks = [
            RetrievedChunk(
                content=hit.payload.get("content", ""),
                source=hit.payload.get("source", "unknown"),
                score=hit.score,
                metadata=hit.payload.get("metadata", {}),
            )
            for hit in hits
        ]

        return RetrievalResult(
            query=query,
            chunks=chunks,
            retrieval_mode=retrieval_mode,
        )

    async def upsert_documents(
        self,
        documents: list[dict],
        contextual: bool = False,
    ) -> int:
        """Embed and upsert documents into the plain or contextual collection.

        Overrides BaseVectorStore.upsert_documents to add the
        `contextual` flag — VectorStoreInterface's base contract only
        declares `documents`, but this is an additive, optional
        parameter (defaults preserve the base signature's behavior), so
        it doesn't break substitutability for callers that only know
        about the interface.

        Args:
            documents: Document dicts, each expected to have `content`,
                `source`, and optionally `metadata` keys. When
                `contextual` is True, callers are expected to have
                already run each document's content through
                DocumentContextualizer.
            contextual: Whether to upsert into the contextual
                collection rather than the plain one.

        Returns:
            The number of documents ingested.
        """
        target_collection = (
            self._contextual_collection_name if contextual else self._collection_name
        )
        logger.info(
            f"Upserting {len(documents)} documents into "
            f"'{target_collection}' (contextual={contextual})"
        )
        return await self._do_upsert(documents, target_collection)

    async def _do_upsert(
        self,
        documents: list[dict],
        collection_name: str | None = None,
    ) -> int:
        """Embed and upsert documents into the given Qdrant collection.

        Args:
            documents: Document dicts, each expected to have `content`,
                `source`, and optionally `metadata` keys.
            collection_name: Which collection to upsert into; defaults
                to the plain collection if not given (matching
                BaseVectorStore's simpler single-collection contract).

        Returns:
            The number of documents ingested.
        """
        collection_name = collection_name or self._collection_name
        await self._ensure_collection(collection_name)

        points = []
        for index, document in enumerate(documents):
            # NOTE: point IDs are sequential indices, not content hashes.
            # This is fine for our use case since data/ingest.py always
            # upserts the full corpus in one pass per collection
            # (re-running it overwrites the same IDs cleanly), but would
            # need a stable ID scheme (e.g. a hash of `source`) if
            # documents were ever ingested incrementally or out of a
            # fixed order.
            vector = await self._embed(document["content"])
            points.append(
                qdrant_models.PointStruct(
                    id=index,
                    vector=vector,
                    payload={
                        "content": document["content"],
                        "source": document.get("source", "unknown"),
                        "metadata": document.get("metadata", {}),
                    },
                )
            )

        await self._client.upsert(
            collection_name=collection_name,
            points=points,
        )
        return len(points)

    async def health_check(
        self,
    ) -> bool:
        """Return True if Qdrant is reachable."""
        try:
            await self._client.get_collections()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Qdrant health check failed: {exc}")
            return False
