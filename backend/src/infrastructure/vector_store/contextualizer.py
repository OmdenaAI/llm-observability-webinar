"""Generates short context annotations for documents, per Anthropic's
"contextual retrieval" technique — used only during ingestion
(data/ingest.py), never on the live request path.

For each document, an LLM call produces a 1-2 sentence blurb situating
that document (e.g. noting whether it's current or superseded, what
topic it covers) which is prepended to the document's content before
it's embedded and stored in the "_contextual" collection. This is what
gives Moment 3 a real, visible faithfulness difference between plain
and contextual retrieval — the contextual version explicitly states
things like "this is the current 2026 policy, superseding the 2023
version," which a plain embedding of the raw document text wouldn't
surface as clearly.
"""
from openai import AsyncOpenAI

from utils.logger import get_logger

logger = get_logger()

CONTEXTUALIZATION_PROMPT = """You are preparing a document for a search \
index. Given the full document below, write a 1-2 sentence context \
blurb that situates this document for retrieval purposes — note what \
it covers, and critically, whether it appears current or superseded/\
outdated relative to its content (e.g. dates, version markers, explicit \
notes about being legacy or current). Respond with ONLY the blurb \
text, no preamble.

Document (source: {source}):
{content}"""


class DocumentContextualizer:
    """Generates a short situating context blurb per document via an LLM call."""

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
                per document at ingestion time, not on the live path.
        """
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self._model = model

    async def contextualize(
        self,
        document: dict,
    ) -> str:
        """Generate a context blurb to prepend to a document's content.

        Args:
            document: A document dict with `content` and `source` keys.

        Returns:
            The document's content, prefixed with the generated context
            blurb.
        """
        prompt = CONTEXTUALIZATION_PROMPT.format(
            source=document.get("source", "unknown"),
            content=document["content"],
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        blurb = response.choices[0].message.content.strip()
        logger.debug(f"Contextualized {document.get('source')}: {blurb!r}")
        return f"{blurb}\n\n{document['content']}"
