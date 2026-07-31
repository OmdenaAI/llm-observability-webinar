"""Loads data/corpus/*.md into the configured vector store — both the
plain collection and the contextual collection (see
infrastructure/vector_store/contextualizer.py) needed for Moment 3's
plain-vs-contextual comparison.

Each document is analyzed exactly ONCE via DocumentContextualizer.analyze()
before either collection is built. That analysis produces `status` and
`misattribution_risk` metadata attached to BOTH collections (previously
the contextualizer's output only ever reached the contextual collection —
a gap, since Moments 2 and 3 can both run in plain mode too), plus the
`blurb` used to build the contextual collection's content.

Each document is then chunked (see infrastructure/vector_store/chunker.py)
before embedding. Chunking is a generic, size-based recursive split — it
has no awareness of any particular document's content, and a document
already under the chunk-size threshold (most of this corpus) comes back
as a single chunk, unchanged from pre-chunking behavior. Every chunk
inherits its parent document's `status`/`misattribution_risk`/
`risk_reason` (a document-level judgment, computed once, not re-run per
chunk) plus a `chunk_index` identifying its position within the document.

Run via `make seed`.
"""
import asyncio
from pathlib import Path

from src.config.container import Container
from src.config.settings import get_settings
from src.infrastructure.vector_store.chunker import chunk_text
from src.infrastructure.vector_store.contextualizer import (
    DocumentAnalysis,
    DocumentContextualizer,
)
from utils.logger import get_logger

logger = get_logger()

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


def load_corpus_documents() -> list[dict]:
    """Read every markdown file in the corpus directory into document dicts.

    Returns:
        A list of dicts, each with `content` (the file's text),
        `source` (the filename), and `metadata` (containing the full
        path) — matching the shape VectorStoreInterface.upsert_documents
        expects. `status`/`misattribution_risk` are added later, once
        each document has been analyzed — see analyze_documents().
    """
    documents = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        documents.append(
            {
                "content": path.read_text(encoding="utf-8"),
                "source": path.name,
                "metadata": {"path": str(path)},
            }
        )
    return documents


async def analyze_documents(
    documents: list[dict],
    contextualizer: DocumentContextualizer,
) -> list[tuple[dict, DocumentAnalysis]]:
    """Run the ingestion-time analysis once per document.

    This is the single point where every document — regardless of size,
    source, or how carefully it was authored — gets scanned for currency
    (`status`) and conditional-fact misattribution risk
    (`misattribution_risk`). Runs once per WHOLE document, before
    chunking — this is a document-level judgment ("is this document
    current, does it contain a scoped fact"), not a per-chunk one, so
    every chunk of a given document inherits the same analysis rather
    than each chunk being separately (and redundantly) analyzed.

    Args:
        documents: The plain documents loaded from the corpus.
        contextualizer: Used to analyze each document.

    Returns:
        A list of (document, analysis) pairs, one per input document.
    """
    analyzed = []
    for document in documents:
        analysis = await contextualizer.analyze(document)
        analyzed.append((document, analysis))
    return analyzed


def _chunk_document(
    document: dict,
    analysis: DocumentAnalysis,
    content: str,
) -> list[dict]:
    """Split one document's content into chunk-document dicts.

    Args:
        document: The original whole document (for `source` and base
            `metadata`).
        analysis: The document-level analysis to inherit onto every
            chunk.
        content: The text to chunk — the document's raw content for the
            plain collection, or blurb-prefixed content for the
            contextual collection (see build_contextualized_documents).

    Returns:
        One document dict per chunk, each with the same `source` and
        inherited `status`/`misattribution_risk`/`risk_reason`, plus a
        `chunk_index` distinguishing chunks from the same source.
    """
    chunk_documents = []
    for chunk_index, chunk_content in enumerate(chunk_text(content)):
        chunk_documents.append(
            {
                "content": chunk_content,
                "source": document["source"],
                "metadata": {
                    **document.get("metadata", {}),
                    **analysis.as_metadata(),
                    "chunk_index": chunk_index,
                },
            }
        )
    return chunk_documents


def build_plain_documents(
    analyzed: list[tuple[dict, DocumentAnalysis]],
) -> list[dict]:
    """Chunk each document's raw content and attach its analysis metadata,
    for the plain collection.

    Args:
        analyzed: (document, analysis) pairs from analyze_documents().

    Returns:
        One document dict per chunk (most documents in this corpus stay
        as a single chunk — chunk_text only splits when a document
        exceeds the size threshold), each carrying the parent document's
        `status`/`misattribution_risk`/`risk_reason` plus `chunk_index`.
    """
    plain_documents = []
    for document, analysis in analyzed:
        plain_documents.extend(_chunk_document(document, analysis, document["content"]))
    return plain_documents


def build_contextualized_documents(
    analyzed: list[tuple[dict, DocumentAnalysis]],
    contextualizer: DocumentContextualizer,
) -> list[dict]:
    """Build the contextual collection's chunk-documents from
    already-computed analyses.

    Each document's blurb is prefixed onto its content BEFORE chunking
    (not onto each chunk individually) — the blurb situates the whole
    document once; chunking then splits that blurb-plus-content text the
    same way build_plain_documents splits the raw content, so a chunk
    containing the blurb sentence and a chunk containing only body text
    can end up as separate chunks if the combined text exceeds the size
    threshold, same as any other paragraph/sentence boundary would.

    Args:
        analyzed: (document, analysis) pairs from analyze_documents().
        contextualizer: Used only to format contextualized_content() —
            does not make any further LLM calls here.

    Returns:
        One document dict per chunk, with the same `source` and the
        same `status`/`misattribution_risk`/`risk_reason`/`chunk_index`
        metadata shape as build_plain_documents.
    """
    contextualized = []
    for document, analysis in analyzed:
        contextual_content = contextualizer.contextualized_content(document, analysis)
        contextualized.extend(_chunk_document(document, analysis, contextual_content))
    return contextualized


async def main() -> None:
    """Load the corpus, analyze it once, chunk it, and upsert both plain
    and contextual versions with matching status/risk/chunk metadata."""
    settings = get_settings()
    container = Container()

    documents = load_corpus_documents()
    logger.info(f"Loaded {len(documents)} documents from {CORPUS_DIR}")

    vector_store = container.qdrant_store()  # TODO: respect settings.vector_store_backend

    contextualizer = DocumentContextualizer(
        openai_api_key=settings.openai_api_key,
        model=settings.eval_judge_model,
    )
    analyzed = await analyze_documents(documents, contextualizer)
    for document, analysis in analyzed:
        logger.info(
            f"Analyzed {document['source']}: status={analysis.status!r}, "
            f"misattribution_risk={analysis.misattribution_risk}"
            + (f" ({analysis.risk_reason})" if analysis.misattribution_risk else "")
        )

    plain_documents = build_plain_documents(analyzed)
    for document, analysis in analyzed:
        chunk_count = sum(1 for d in plain_documents if d["source"] == document["source"])
        logger.info(f"Chunked {document['source']} into {chunk_count} chunk(s)")

    plain_count = await vector_store.upsert_documents(plain_documents, contextual=False)
    logger.info(
        f"Ingested {plain_count} plain chunks into "
        f"'{settings.qdrant_collection_name}'"
    )

    contextualized_documents = build_contextualized_documents(analyzed, contextualizer)
    contextual_count = await vector_store.upsert_documents(
        contextualized_documents,
        contextual=True,
    )
    logger.info(
        f"Ingested {contextual_count} contextualized chunks into "
        f"'{settings.qdrant_collection_name}_contextual'"
    )


if __name__ == "__main__":
    asyncio.run(main())