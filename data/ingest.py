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

Run via `make seed`.
"""
import asyncio
from pathlib import Path

from src.config.container import Container
from src.config.settings import get_settings
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
    (`misattribution_risk`). Runs once per document; the same
    DocumentAnalysis is reused to build both the plain collection's
    metadata and the contextual collection's content/metadata, so this
    is not a second LLM call per collection.

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


def build_plain_documents(
    analyzed: list[tuple[dict, DocumentAnalysis]],
) -> list[dict]:
    """Attach each document's analysis metadata for the plain collection.

    Args:
        analyzed: (document, analysis) pairs from analyze_documents().

    Returns:
        Document dicts with `status`/`misattribution_risk`/`risk_reason`
        merged into their existing metadata — content is untouched.
    """
    plain_documents = []
    for document, analysis in analyzed:
        plain_documents.append(
            {
                "content": document["content"],
                "source": document["source"],
                "metadata": {
                    **document.get("metadata", {}),
                    **analysis.as_metadata(),
                },
            }
        )
    return plain_documents


def build_contextualized_documents(
    analyzed: list[tuple[dict, DocumentAnalysis]],
    contextualizer: DocumentContextualizer,
) -> list[dict]:
    """Build the contextual collection's documents from already-computed
    analyses — producing a second document list with content prefixed by
    each document's situating blurb.

    Args:
        analyzed: (document, analysis) pairs from analyze_documents().
        contextualizer: Used only to format contextualized_content() —
            does not make any further LLM calls here.

    Returns:
        A new list of document dicts with the same `source` and the
        same `status`/`misattribution_risk`/`risk_reason` metadata as
        the plain collection, but content prefixed with the blurb.
    """
    contextualized = []
    for document, analysis in analyzed:
        contextualized.append(
            {
                "content": contextualizer.contextualized_content(document, analysis),
                "source": document["source"],
                "metadata": {
                    **document.get("metadata", {}),
                    **analysis.as_metadata(),
                },
            }
        )
    return contextualized


async def main() -> None:
    """Load the corpus, analyze it once, and upsert both plain and
    contextual versions with matching status/risk metadata."""
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
    plain_count = await vector_store.upsert_documents(plain_documents, contextual=False)
    logger.info(
        f"Ingested {plain_count} plain documents into "
        f"'{settings.qdrant_collection_name}'"
    )

    contextualized_documents = build_contextualized_documents(analyzed, contextualizer)
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