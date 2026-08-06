"""Generates short context annotations for document chunks, per
Anthropic's "contextual retrieval" technique — used only during
ingestion (data/ingest.py), never on the live request path.

For each chunk of a document, an LLM call is given the FULL document
plus that one chunk, and produces a 1-2 sentence blurb situating that
specific chunk (e.g. noting whether the document it's from is current
or superseded, what topic the chunk covers) which is prepended to the
chunk's own content before it's embedded and stored in the
"_contextual" collection. This is what gives Moment 3 a real, visible
faithfulness difference between plain and contextual retrieval — the
contextual version explicitly states things like "this chunk is from
the 2023 policy, superseded by the 2026 version," which a plain
embedding of the raw chunk text wouldn't surface as clearly.

Chunk-level (not whole-document) annotation matters here specifically
because chunking (see chunker.py) was introduced to stop a short,
specific fact from being diluted by the rest of its document's
unrelated content in a single whole-document vector — annotating the
whole document again per chunk would just reintroduce that dilution
one level up.
"""
from openai import AsyncOpenAI

from utils.logger import get_logger

logger = get_logger()

CONTEXTUALIZATION_PROMPT = """You are preparing a document chunk for a \
search index. Below is the full document for context, followed by one \
specific chunk from that document. Write a 1-2 sentence context blurb \
for THIS CHUNK specifically — situating it within the document (what \
the document as a whole covers, and critically, whether the document \
appears current or superseded/outdated relative to its content, e.g. \
dates, version markers, explicit notes about being legacy or current) \
plus what this particular chunk covers. Respond with ONLY the blurb \
text, no preamble.

Full document (source: {source}):
{full_content}

Chunk to annotate:
{chunk}"""


class DocumentContextualizer:
    """Generates a short situating context blurb per chunk via an LLM call."""

    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-4o-mini",
    ) -> None:
        """Initialize the contextualizer's OpenAI client.

        Args:
            openai_api_key: API key for the contextualization calls.
            model: The model to use for generating context blurbs —
                deliberately a cheap/fast model, since this runs once
                per chunk at ingestion time, not on the live path.
        """
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self._model = model

    async def contextualize_chunk(
        self,
        document: dict,
        chunk: str,
    ) -> str:
        """Generate a context blurb to prepend to one chunk of a document.

        Args:
            document: The full document dict (`content` and `source`
                keys) this chunk was taken from — used to give the
                judge model enough context to situate the chunk (e.g.
                current vs. superseded) even though only the chunk
                itself gets embedded.
            chunk: The specific chunk of `document["content"]` to
                annotate.

        Returns:
            The chunk's content, prefixed with the generated context
            blurb.
        """
        prompt = CONTEXTUALIZATION_PROMPT.format(
            source=document.get("source", "unknown"),
            full_content=document["content"],
            chunk=chunk,
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        blurb = response.choices[0].message.content.strip()
        logger.debug(
            f"Contextualized a chunk of {document.get('source')}: {blurb!r}"
        )
        return f"{blurb}\n\n{chunk}"