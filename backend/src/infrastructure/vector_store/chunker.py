"""A generic, recursive text chunker: paragraph boundaries first, falling
back to sentence boundaries for any paragraph still too large, falling
back to a hard word-count cut as a last resort for any sentence still
too large.

This is deliberately document-agnostic — it has no awareness of which
file it's splitting or what any sentence says. The same function
produces one chunk for a short document (nothing to split) and several
chunks for a longer one, purely as a function of size relative to
`max_chunk_words`, the same way any real recursive/token-aware splitter
behaves.

Word count is used as an approximation of token count (roughly
words * 1.3 for English prose) rather than a real tokenizer, to avoid
adding a tokenizer dependency for what only needs to be an approximate
size threshold at ingestion time — not exact, just consistent.
"""
import re

# ~300 tokens (~230 words) is a common middle-of-the-road chunk size in
# production RAG systems — small enough to keep unrelated facts from
# being crammed into one chunk, large enough that short documents (a
# FAQ entry, a one-paragraph notice) naturally stay whole. This is a
# fixed, general-purpose default — not tuned to any specific document
# in this corpus.
DEFAULT_MAX_CHUNK_WORDS = 230

_HEADING_PATTERN = re.compile(r"^#{1,6}\s")


def _split_into_paragraphs(
    text: str,
) -> list[str]:
    """Split text on blank-line boundaries, then merge any markdown
    heading line into the paragraph that follows it.

    Without this merge, a heading line (e.g. "## Production Systems")
    that's separated from its body text by a blank line — the normal
    way markdown is written — would become its own paragraph, and
    therefore its own chunk: a near-empty, low-information embedding
    with no content. Real recursive/markdown-aware splitters treat a
    heading as belonging with what follows it, not as a chunk boundary
    in its own right; this mirrors that, generically, for any document
    with markdown headings — not specific to any one file.

    Args:
        text: The full document text.

    Returns:
        Non-empty paragraphs, whitespace-trimmed, with any heading-only
        paragraph merged into the next one.
    """
    raw_paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    merged: list[str] = []
    pending_heading: str | None = None
    for paragraph in raw_paragraphs:
        if _HEADING_PATTERN.match(paragraph) and "\n" not in paragraph:
            # A heading line on its own (no body text within the same
            # paragraph) — hold it and attach it to whatever comes next.
            pending_heading = paragraph
            continue
        if pending_heading is not None:
            merged.append(f"{pending_heading}\n\n{paragraph}")
            pending_heading = None
        else:
            merged.append(paragraph)

    # A trailing heading with nothing after it (rare, but possible at
    # the very end of a document) — keep it rather than silently drop it.
    if pending_heading is not None:
        merged.append(pending_heading)

    return merged


def _split_into_sentences(
    text: str,
) -> list[str]:
    """Split text on sentence-ending punctuation followed by whitespace.

    A simple regex split, not a full sentence-boundary NLP model — this
    is intentionally the same order of sophistication as the paragraph
    split above; both are structural heuristics, not semantic ones.

    Args:
        text: A single paragraph's text.

    Returns:
        Non-empty sentences, whitespace-trimmed.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def _word_count(
    text: str,
) -> int:
    """Return an approximate word count for a piece of text."""
    return len(text.split())


def chunk_text(
    text: str,
    max_chunk_words: int = DEFAULT_MAX_CHUNK_WORDS,
) -> list[str]:
    """Recursively split text into chunks under max_chunk_words.

    Order of attempts, per piece of text:
    1. If it's already under max_chunk_words, keep it whole.
    2. Otherwise, split on paragraph boundaries and recurse into each
       paragraph.
    3. If a single paragraph is still too large, split it on sentence
       boundaries.
    4. If a single sentence is somehow still too large, hard-cut it at
       max_chunk_words as a last resort — no cleverness, just a size
       cap, since this case should be rare in practice.

    Args:
        text: The full document text to chunk.
        max_chunk_words: The approximate word-count ceiling per chunk.

    Returns:
        An ordered list of chunk strings. A document entirely under
        max_chunk_words returns as a single-element list — chunking
        that doesn't need to happen, doesn't happen.
    """
    if _word_count(text) <= max_chunk_words:
        return [text]

    chunks: list[str] = []
    for paragraph in _split_into_paragraphs(text):
        if _word_count(paragraph) <= max_chunk_words:
            chunks.append(paragraph)
            continue

        # Paragraph itself exceeds the cap — fall back to sentences.
        for sentence in _split_into_sentences(paragraph):
            if _word_count(sentence) <= max_chunk_words:
                chunks.append(sentence)
                continue

            # A single sentence exceeds the cap — hard cut as a last
            # resort. Rare in practice; no attempt to find a "nice"
            # boundary here, since there isn't a structural one left.
            words = sentence.split()
            for i in range(0, len(words), max_chunk_words):
                chunks.append(" ".join(words[i : i + max_chunk_words]))

    return chunks