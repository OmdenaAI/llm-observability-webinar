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


async def build_contextualized_documents(
    documents: list[dict],
    contextualizer: DocumentContextualizer,
) -> list[dict]:
    """Run each document through the contextualizer, producing a second
    document list with content prefixed by a situating context blurb.

    Args:
        documents: The plain documents loaded from the corpus.
        contextualizer: Used to generate each document's context blurb.

    Returns:
        A new list of document dicts with the same `source`/`metadata`
        but contextualized `content`.
    """
    contextualized = []
    for document in documents:
        contextual_content = await contextualizer.contextualize(document)
        contextualized.append(
            {
                "content": contextual_content,
                "source": document["source"],
                "metadata": document.get("metadata", {}),
            }
        )
    return contextualized


async def main() -> None:
    """Load the corpus and upsert both plain and contextual versions."""
    settings = get_settings()
    container = Container()

    documents = load_corpus_documents()
    logger.info(f"Loaded {len(documents)} documents from {CORPUS_DIR}")

    vector_store = container.qdrant_store()  # TODO: respect settings.vector_store_backend

    plain_count = await vector_store.upsert_documents(documents, contextual=False)
    logger.info(
        f"Ingested {plain_count} plain documents into "
        f"'{settings.qdrant_collection_name}'"
    )

    contextualizer = DocumentContextualizer(
        openai_api_key=settings.openai_api_key,
        model=settings.eval_judge_model,
    )
    contextualized_documents = await build_contextualized_documents(
        documents,
        contextualizer,
    )
    contextual_count = await vector_store.upsert_documents(
        contextualized_documents,
        contextual=True,
    )
    logger.info(
        f"Ingested {contextual_count} contextualized documents into "
        f"'{settings.qdrant_collection_name}_contextual'"
    )


if __name__ == "__main__":
    asyncio.run(main())
