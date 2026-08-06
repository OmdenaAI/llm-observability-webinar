"""Loads data/corpus/*.md into the configured vector store — both the
plain collection and the contextual collection (see
infrastructure/vector_store/contextualizer.py) needed for Moment 3's
plain-vs-contextual comparison.

Run via `make seed`.
"""
import asyncio
from pathlib import Path

from src.config.container import Container
from src.config.settings import get_settings
from src.infrastructure.vector_store.chunker import chunk_document
from src.infrastructure.vector_store.contextualizer import DocumentContextualizer
from utils.logger import get_logger

logger = get_logger()

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


def load_corpus_documents() -> list[dict]:
    """Read every markdown file in the corpus directory into document dicts.

    Returns:
        A list of dicts, each with `content` (the file's text),
        `source` (the filename), and `metadata` (containing the full
        path) — matching the shape VectorStoreInterface.upsert_documents
        expects.
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


def build_chunk_documents(
    documents: list[dict],
) -> list[dict]:
    """Split each document into paragraph-level chunks.

    Whole-file embedding diluted short, specific facts inside a much
    longer document's overall vector (e.g. a single retention-duration
    sentence competing, as a whole-document vector, against another
    whole document that's topically broader but less specific to a
    given question) — see chunker.py's module docstring. Splitting into
    chunks here means each embedded unit represents one concentrated
    idea instead of an entire document.

    Args:
        documents: The whole documents loaded from the corpus.

    Returns:
        A new, longer list of document dicts — one per chunk, each
        carrying the same `source` as its parent document plus
        `chunk_index`/`chunk_count` in `metadata` for traceability back
        to which part of the source document it came from.
    """
    chunk_documents = []
    for document in documents:
        chunks = chunk_document(document["content"])
        for index, chunk in enumerate(chunks):
            chunk_documents.append(
                {
                    "content": chunk,
                    "source": document["source"],
                    "metadata": {
                        **document.get("metadata", {}),
                        "chunk_index": index,
                        "chunk_count": len(chunks),
                    },
                }
            )
    return chunk_documents


async def build_contextualized_chunk_documents(
    documents: list[dict],
    chunk_documents: list[dict],
    contextualizer: DocumentContextualizer,
) -> list[dict]:
    """Run each chunk through the contextualizer, producing a parallel
    chunk-document list with content prefixed by a situating context
    blurb.

    Each chunk is annotated using its OWN parent document's full text
    for situating context (e.g. "this is the superseded 2023 policy"),
    not the whole corpus — see contextualizer.py's module docstring for
    why annotating at the whole-document level would reintroduce the
    same dilution chunking was meant to fix.

    Args:
        documents: The whole documents loaded from the corpus, keyed by
            `source`, used to look up each chunk's parent document text.
        chunk_documents: The chunk-level documents from
            build_chunk_documents, to be contextualized.
        contextualizer: Used to generate each chunk's context blurb.

    Returns:
        A new list of chunk-document dicts with the same `source`/
        `metadata` but contextualized `content`.
    """
    documents_by_source = {doc["source"]: doc for doc in documents}

    contextualized = []
    for chunk_document_ in chunk_documents:
        parent_document = documents_by_source[chunk_document_["source"]]
        contextual_content = await contextualizer.contextualize_chunk(
            parent_document,
            chunk_document_["content"],
        )
        contextualized.append(
            {
                "content": contextual_content,
                "source": chunk_document_["source"],
                "metadata": chunk_document_.get("metadata", {}),
            }
        )
    return contextualized


async def main() -> None:
    """Load the corpus, chunk it, and upsert both plain and contextual versions."""
    settings = get_settings()
    container = Container()

    documents = load_corpus_documents()
    logger.info(f"Loaded {len(documents)} documents from {CORPUS_DIR}")

    chunk_documents = build_chunk_documents(documents)
    logger.info(
        f"Split into {len(chunk_documents)} chunks across {len(documents)} documents"
    )

    vector_store = container.qdrant_store()  # TODO: respect settings.vector_store_backend

    plain_count = await vector_store.upsert_documents(chunk_documents, contextual=False)
    logger.info(
        f"Ingested {plain_count} plain chunks into "
        f"'{settings.qdrant_collection_name}'"
    )

    contextualizer = DocumentContextualizer(
        openai_api_key=settings.openai_api_key,
        model=settings.eval_judge_model,
    )
    contextualized_chunk_documents = await build_contextualized_chunk_documents(
        documents,
        chunk_documents,
        contextualizer,
    )
    contextual_count = await vector_store.upsert_documents(
        contextualized_chunk_documents,
        contextual=True,
    )
    logger.info(
        f"Ingested {contextual_count} contextualized chunks into "
        f"'{settings.qdrant_collection_name}_contextual'"
    )


if __name__ == "__main__":
    asyncio.run(main())