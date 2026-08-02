"""Sentence-level chunking for corpus documents.

Whole-file embedding was the original ingestion strategy (see
data/ingest.py's git history) — one vector per file. That diluted
short, specific facts (e.g. a single retention-duration sentence)
inside a much longer document's overall vector, making retrieval favor
topically-broad documents over ones containing the specific fact a
question is actually asking about. Paragraph-level chunking was tried
next and reduced but didn't eliminate that dilution — a paragraph can
still mix the one specific fact with a couple of sentences of
surrounding scope-setting text. This module chunks at the sentence
level instead, so a chunk's embedding represents one concrete claim
rather than a paragraph's worth of them.
"""
import re

# Splits after sentence-ending punctuation, only when followed by
# whitespace and a capital letter or digit — avoids splitting on
# abbreviations/decimals mid-sentence in the (unlikely, for this
# corpus) case they appear. Good enough for plain-prose policy docs;
# not a general-purpose sentence tokenizer.
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _split_into_sentences(
    paragraph: str,
) -> list[str]:
    """Split one paragraph into sentence-level fragments.

    Args:
        paragraph: A single paragraph's text (no blank lines within it).

    Returns:
        A list of sentence strings, in order.
    """
    return [s.strip() for s in _SENTENCE_BOUNDARY_RE.split(paragraph) if s.strip()]


def chunk_document(
    content: str,
    min_chunk_chars: int = 60,
) -> list[str]:
    """Split a document's content into sentence-level chunks.

    First splits on blank lines (paragraphs), then splits each
    paragraph into individual sentences. Short fragments (e.g. a
    `# Title` line, a lone `Last updated: ...` line, or a short
    sentence) are merged into the following fragment rather than left
    as their own chunk — a fragment alone as a standalone embedded
    chunk carries too little signal and just adds retrieval noise.

    Args:
        content: The full document text.
        min_chunk_chars: Fragments shorter than this are merged forward
            into the next fragment rather than kept standalone. Lower
            than the paragraph-chunking default this replaced, since
            individual sentences are naturally shorter units than
            paragraphs.

    Returns:
        A list of chunk strings, in document order. Always returns at
        least one chunk (the whole content) if the document has no
        usable sentence/paragraph breaks at all.
    """
    raw_paragraphs = [p.strip() for p in content.split("\n\n")]
    raw_paragraphs = [p for p in raw_paragraphs if p]

    raw_fragments: list[str] = []
    for paragraph in raw_paragraphs:
        raw_fragments.extend(_split_into_sentences(paragraph))

    if not raw_fragments:
        return [content.strip()] if content.strip() else []

    chunks: list[str] = []
    pending = ""
    for fragment in raw_fragments:
        combined = f"{pending} {fragment}" if pending else fragment
        if len(combined) < min_chunk_chars:
            # Too short to stand alone (e.g. just a heading, or a
            # short sentence) — hold it and merge into the next
            # fragment instead.
            pending = combined
        else:
            chunks.append(combined)
            pending = ""

    if pending:
        # Trailing short fragment with nothing left to merge forward
        # into — attach it to the last real chunk rather than drop it
        # or ship it as its own near-empty chunk.
        if chunks:
            chunks[-1] = f"{chunks[-1]} {pending}"
        else:
            chunks.append(pending)

    return chunks