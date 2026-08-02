"""Paragraph-level chunking for corpus documents.

Whole-file embedding was the original ingestion strategy (see
data/ingest.py's git history) — one vector per file. That turned out to
dilute short, specific facts (e.g. a single retention-duration sentence)
inside a much longer document's overall vector, making retrieval favor
topically-broad documents over ones containing the specific fact a
question is actually asking about. This module splits each document
into paragraph-sized chunks instead, so a chunk's embedding represents
one concentrated idea rather than an entire document.
"""


def chunk_document(
    content: str,
    min_chunk_chars: int = 100,
) -> list[str]:
    """Split a document's content into paragraph-level chunks.

    Splits on blank lines (double newlines). Short leading fragments
    (e.g. a `# Title` line or a lone `Last updated: ...` line) are
    merged into the following chunk rather than left as their own
    chunk — a heading alone as a standalone embedded chunk carries
    almost no retrievable signal and would just add retrieval noise.

    Args:
        content: The full document text.
        min_chunk_chars: Paragraphs shorter than this are merged
            forward into the next paragraph rather than kept standalone.

    Returns:
        A list of chunk strings, in document order. Always returns at
        least one chunk (the whole content) if the document has no
        blank-line breaks at all.
    """
    raw_paragraphs = [p.strip() for p in content.split("\n\n")]
    raw_paragraphs = [p for p in raw_paragraphs if p]

    if not raw_paragraphs:
        return [content.strip()] if content.strip() else []

    chunks: list[str] = []
    pending = ""
    for paragraph in raw_paragraphs:
        combined = f"{pending}\n\n{paragraph}" if pending else paragraph
        if len(combined) < min_chunk_chars:
            # Too short to stand alone (e.g. just a heading) — hold it
            # and merge into the next paragraph instead.
            pending = combined
        else:
            chunks.append(combined)
            pending = ""

    if pending:
        # Trailing short fragment with nothing left to merge forward
        # into — attach it to the last real chunk rather than drop it
        # or ship it as its own near-empty chunk.
        if chunks:
            chunks[-1] = f"{chunks[-1]}\n\n{pending}"
        else:
            chunks.append(pending)

    return chunks