"""Entities related to a user query and its retrieval result.

These are pure data objects — no dependency on any infrastructure library.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RetrievedChunk:
    """A single piece of retrieved context.

    Attributes:
        content: The raw text of the retrieved chunk.
        source: An identifier for where the chunk came from (e.g. a
            filename), used for display and for citation-style debugging.
        score: The retriever's relevance score for this chunk against the
            originating query.
        metadata: Any additional retriever-specific data (e.g. document ID,
            chunk index) that downstream consumers may need.
    """

    content: str
    source: str
    score: float
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Query:
    """A user's question, plus the retrieval mode requested.

    Attributes:
        text: The user's natural-language question.
        use_contextual_retrieval: Whether the retriever should use its
            contextual retrieval strategy instead of plain retrieval.
            Toggled live in Moment 3 of the demo.
    """

    text: str
    use_contextual_retrieval: bool = False


@dataclass(frozen=True)
class RetrievalResult:
    """The set of chunks retrieved for a given query.

    Attributes:
        query: The query that produced this result.
        chunks: The retrieved chunks, ordered by relevance.
        retrieval_mode: Which retrieval strategy was used — "plain" or
            "contextual" — recorded for observability/debugging.
    """

    query: Query
    chunks: list[RetrievedChunk]
    retrieval_mode: str
