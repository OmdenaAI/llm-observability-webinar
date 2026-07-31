"""Generates structured ingestion-time judgments for documents, extending
Anthropic's "contextual retrieval" technique with two additional signals
this webinar's demo scenarios need.

For each document, ONE LLM call now returns THREE things instead of the
original single free-text blurb:

- `blurb`: the original situating context sentence (still used to build
  the contextual collection's content — unchanged purpose, Moment 3's
  plain-vs-contextual retrieval comparison).
- `status`: "current" | "superseded" | "uncertain" — whether the
  document appears to be the current, authoritative version or has been
  superseded (e.g. by explicit versioning/date language, or by an
  internal note saying so). Feeds Moment 3's stale-context evaluator
  weighting.
- `misattribution_risk`: whether the document states a fact that is
  conditionally scoped (e.g. applies only to backups, only to a
  specific tier/plan, only under certain conditions) in a way that
  could plausibly be misattributed as a general/unscoped answer if a
  reader — human or model — only sees part of the document, or reads
  quickly. Feeds Moment 2's ingestion-time risk flag.

Deliberately still ONE call per document (not three) — same cost as the
original contextualizer, richer output. Runs only at ingestion
(data/ingest.py), never on the live request path.

Crucially, this runs identically on every document regardless of who
uploaded it or how carefully it was authored — there is no reliance on
a human tagging risk correctly, since a user who could reliably spot
this risk themselves wouldn't need the system to catch it for them.
"""
import json

from openai import AsyncOpenAI

from utils.logger import get_logger

logger = get_logger()

ANALYSIS_PROMPT = """You are analyzing a document for a search index and \
risk-scanning it. Given the full document below, produce a JSON object \
with exactly these fields:

- "blurb": a 1-2 sentence context blurb that situates this document for \
retrieval purposes (what it covers, and whether it's current or legacy).
- "status": one of "current", "superseded", or "uncertain" — based on \
explicit signals in the document itself (dates, version markers, notes \
about being legacy/current). Use "uncertain" if there's no clear signal \
either way — do not guess.
- "misattribution_risk": true or false — true if the document states a \
specific fact (a number, duration, limit, etc.) that is conditionally \
scoped (e.g. applies only under certain conditions, only to a specific \
system/tier/category) in a way that could plausibly be misattributed as \
a general, unscoped answer if a reader only sees or retains part of the \
document. false if the document's facts are unscoped, or if scoping is \
stated so prominently it's unlikely to be dropped.
- "risk_reason": if misattribution_risk is true, one sentence naming \
which fact and its scope. Empty string if misattribution_risk is false.

Respond with ONLY the JSON object, no preamble, no markdown fences.

Document (source: {source}):
{content}"""


class DocumentAnalysis:
    """The structured result of analyzing one document at ingestion time.

    Attributes:
        blurb: The situating context blurb (used to build contextual
            collection content — see contextualized_content()).
        status: "current", "superseded", or "uncertain".
        misattribution_risk: Whether this document contains a
            conditionally-scoped fact at risk of being misattributed as
            general/unscoped.
        risk_reason: A one-sentence explanation if misattribution_risk
            is True; empty string otherwise.
    """

    def __init__(
        self,
        blurb: str,
        status: str,
        misattribution_risk: bool,
        risk_reason: str,
    ) -> None:
        self.blurb = blurb
        self.status = status
        self.misattribution_risk = misattribution_risk
        self.risk_reason = risk_reason

    def as_metadata(
        self,
    ) -> dict:
        """Return the fields meant to be attached to document metadata.

        `blurb` is deliberately excluded — it's consumed directly by
        contextualized_content() to build the contextual collection's
        text, not carried as a metadata field on either collection.

        Returns:
            A dict with `status`, `misattribution_risk`, and
            `risk_reason`, ready to merge into a document's metadata
            dict before upsert.
        """
        return {
            "status": self.status,
            "misattribution_risk": self.misattribution_risk,
            "risk_reason": self.risk_reason,
        }


class DocumentContextualizer:
    """Generates a structured ingestion-time analysis per document via an
    LLM call: a retrieval blurb, a currency status, and a
    misattribution-risk flag."""

    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-4o-mini",
    ) -> None:
        """Initialize the contextualizer's OpenAI client.

        Args:
            openai_api_key: API key for the analysis calls.
            model: The model to use — deliberately a cheap/fast model,
                since this runs once per document at ingestion time, not
                on the live path.
        """
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self._model = model

    async def analyze(
        self,
        document: dict,
    ) -> DocumentAnalysis:
        """Run the structured ingestion-time analysis for one document.

        Args:
            document: A document dict with `content` and `source` keys.

        Returns:
            The parsed DocumentAnalysis for this document.
        """
        prompt = ANALYSIS_PROMPT.format(
            source=document.get("source", "unknown"),
            content=document["content"],
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = response.choices[0].message.content
        data = json.loads(raw_text)

        analysis = DocumentAnalysis(
            blurb=data.get("blurb", ""),
            status=data.get("status", "uncertain"),
            misattribution_risk=bool(data.get("misattribution_risk", False)),
            risk_reason=data.get("risk_reason", ""),
        )
        logger.debug(
            f"Analyzed {document.get('source')}: status={analysis.status!r}, "
            f"misattribution_risk={analysis.misattribution_risk}"
        )
        return analysis

    def contextualized_content(
        self,
        document: dict,
        analysis: DocumentAnalysis,
    ) -> str:
        """Build the contextual collection's content from a document and
        its already-computed analysis.

        Args:
            document: A document dict with a `content` key.
            analysis: The analysis previously computed for this document
                (via analyze()) — passed in rather than recomputed, so
                the LLM is only called once per document even though its
                result feeds both the plain and contextual collections.

        Returns:
            The document's content, prefixed with the analysis's blurb.
        """
        return f"{analysis.blurb}\n\n{document['content']}"