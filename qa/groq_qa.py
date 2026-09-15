"""Real task-accuracy Q&A: given a textual representation of an artifact
(the flattened baseline, or the structured common-schema JSON) and a
natural-language question, calls a real Groq-hosted LLM and returns its
free-text answer.

This is the module `docs/eval-methodology.md` describes as not existing
yet — "task accuracy" (does a model actually answer correctly), as opposed
to `eval/run_eval.py`'s "fact-recoverability" (is the fact present at all,
checked with no model involved). It is deliberately small and
single-purpose: it does not know about `qa_dataset.json`'s shape, scoring,
or adapters. Two callers share it without duplicating the Groq-calling
logic:

- `eval/run_real_eval.py` — calls `ask()` twice per question (once with the
  baseline flattened text, once with the structured JSON) and scores each
  answer against `qa_dataset.json`'s `expect_substring`, producing the real
  baseline-vs-structured task-accuracy numbers this project has not had
  until now.
- `webapp/main.py`'s `POST /api/ask` — calls `ask()` once, with the
  structured JSON of whatever artifact the user just analyzed in the
  browser, so a person can ask an ad-hoc question interactively.

Why the structured representation handed to the model is `to_structured()`
(the region list), not `to_text()`'s flattened join or `to_json()`'s full
schema: `to_text()` is itself just another flattening (regions joined by
newlines with structure discarded) and wouldn't test anything different
from the CSV baseline. `to_json()` adds `source`/`checks` metadata that
carries no signal for answering a factual question. `to_structured()` is
the actual claim CLAUDE.md's problem statement makes worth testing: each
region typed, confidence-scored, and carrying its `relationships`
(formula-ref, cross-sheet-ref, connects-to, ...) — the exact information a
flat text dump throws away. Handing the model *that* is the real test of
whether preserving structure helps a model answer correctly, which is a
strictly stronger and different claim than "the fact is present somewhere
in this blob" (what `run_eval.py` already measures).

Handling a missing or invalid `GROQ_API_KEY` mirrors
`adapters/common/ocr.py`'s `tesseract_status()` pattern: report clearly,
never crash, never silently fabricate an answer.
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent

# Loads repo-root .env into os.environ if present; a no-op (not an error) if
# it doesn't exist, and never overrides a variable already set in the real
# environment (e.g. exported in the shell, or set by CI).
load_dotenv(ROOT / ".env")

# Picked from https://console.groq.com/docs/models (checked 2026-09-04):
# openai/gpt-oss-120b is Groq's flagship general-purpose production text
# model at the time this was written. Groq's model lineup changes over
# time, so this is overridable via GROQ_MODEL rather than hardcoded as the
# only option.
DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = (
    "You answer questions using only the supplied NexDoc evidence.\n"
    "Do not invent facts.\n"
    "If evidence is insufficient, say so.\n"
    "Cite the source artifact when possible."
)

MAX_CONTEXT_CHARS = 14000
MAX_CONTEXT_NODES = 20

def _extract_keywords(text: str) -> list[str]:
    words = text.lower().split()
    stop_words = {"what", "which", "where", "when", "does", "this", "that", "the", "and", "for", "with", "is", "are"}
    return [w.strip('.,?!;') for w in words if len(w) > 3 and w not in stop_words]

def retrieve_context(question: str, context: str, max_chars: int = MAX_CONTEXT_CHARS) -> tuple[str, str, int, int]:
    """Limits the context by retrieving only relevant chunks or graph nodes.
    Returns (retrieved_json, context_type, num_nodes, num_rels)
    """
    try:
        data = json.loads(context)
        regions = data if isinstance(data, list) else data.get("regions", [])
        if not regions and isinstance(data, dict) and "nodes" in data:
            regions = data["nodes"]
            
        if not regions:
            return context[:max_chars], "graph", 0, 0
            
        keywords = _extract_keywords(question)
        
        scored_nodes = []
        node_map = {}
        for r in regions:
            r_id = r.get("id", "")
            node_map[r_id] = r
            search_text = (r.get("text") or "") + " " + (r.get("label") or "") + " " + (r.get("type") or "")
            search_text = search_text.lower()
            
            score = sum(1 for k in keywords if k in search_text)
            if r_id and r_id.lower() in question.lower():
                score += 5
            scored_nodes.append((score, r))
            
        scored_nodes.sort(key=lambda x: x[0], reverse=True)
        
        selected_nodes = {}
        num_rels = 0
        top_candidates = [n for s, n in scored_nodes if s > 0][:5]
        if not top_candidates and scored_nodes:
            top_candidates = [scored_nodes[0][1]]
            
        for node in top_candidates:
            nid = node.get("id")
            if nid and nid not in selected_nodes:
                selected_nodes[nid] = node
                
                # Multi-hop preservation: Follow relationships greedily for context
                rels = node.get("relationships", [])
                for rel in rels:
                    target_id = rel.get("target")
                    if target_id and target_id in node_map and target_id not in selected_nodes:
                        selected_nodes[target_id] = node_map[target_id]
                        num_rels += 1
                        # Continue hopping one more level for deep multi-hop
                        sub_rels = node_map[target_id].get("relationships", [])
                        for s_rel in sub_rels:
                            sub_target_id = s_rel.get("target")
                            if sub_target_id and sub_target_id in node_map and sub_target_id not in selected_nodes:
                                selected_nodes[sub_target_id] = node_map[sub_target_id]
                                num_rels += 1
                                if len(selected_nodes) >= MAX_CONTEXT_NODES:
                                    break
                    if len(selected_nodes) >= MAX_CONTEXT_NODES:
                        break
            if len(selected_nodes) >= MAX_CONTEXT_NODES:
                break
                
        retrieved_json = json.dumps(list(selected_nodes.values()), indent=2)
        if len(retrieved_json) > max_chars:
            retrieved_json = retrieved_json[:max_chars] + "\n...[TRUNCATED]"
            
        return retrieved_json, "graph", len(selected_nodes), num_rels

    except json.JSONDecodeError:
        chunks = context.split('\n\n')
        keywords = _extract_keywords(question)
        scored_chunks = []
        for chunk in chunks:
            score = sum(1 for k in keywords if k in chunk.lower())
            scored_chunks.append((score, chunk))
            
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        result = []
        current_len = 0
        for score, chunk in scored_chunks:
            if current_len + len(chunk) > max_chars:
                break
            result.append(chunk)
            current_len += len(chunk)
            
        return "\n...\n".join(result), "text", len(result), 0


class GroqQAError(RuntimeError):
    """Base class for a handled failure in the Groq Q&A path — raised
    instead of letting the Groq SDK's own exception (or a KeyError on a
    missing env var) propagate as a raw crash."""


class GroqNotConfiguredError(GroqQAError):
    """Raised when GROQ_API_KEY is missing/empty, or Groq itself rejects it
    as invalid/expired. Callers (eval script, /api/ask) catch this and show
    its message directly instead of a stack trace or a fabricated answer."""


def api_key_status() -> tuple[bool, str]:
    """Returns (available, detail) with no network call — mirrors
    `adapters/common/ocr.py`'s `tesseract_status()` shape so callers can
    check availability up front (e.g. to decide whether to even show the
    "Ask a question" box) the same way the document/diagram adapters check
    for Tesseract before attempting OCR.
    """
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        return False, (
            "GROQ_API_KEY is not set. Copy .env.example to .env at the repo "
            "root and fill in a real Groq API key (https://console.groq.com/keys) "
            "to enable Groq-backed Q&A."
        )
    return True, "GROQ_API_KEY is set."


def _client() -> Any:
    from groq import Groq  # imported lazily so importing this module never requires network/creds

    available, detail = api_key_status()
    if not available:
        raise GroqNotConfiguredError(detail)
    return Groq(api_key=os.environ["GROQ_API_KEY"])


def ask(question: str, context: str, *, model: str | None = None, client: Any | None = None) -> str:
    """Sends `context` (some textual representation of an artifact) plus
    `question` to a Groq chat-completion model and returns its free-text
    answer.

    `client` exists so tests can inject a fake Groq client — anything
    exposing `.chat.completions.create(...)` matching the real SDK's
    response shape (`response.choices[0].message.content`) — and verify the
    prompt-building and response-parsing logic without a network call or a
    real API key. Production callers never pass it; a real `Groq()` client
    is built from `GROQ_API_KEY` when omitted.

    Raises `GroqNotConfiguredError` if no key is configured, or if Groq
    itself reports the key is invalid/unauthorized. Raises the more general
    `GroqQAError` for any other Groq API failure (network, rate limit,
    model error). Either way: a clear, honest message, never a raw
    traceback and never a silently wrong/fabricated answer.
    """
    if client is None:
        client = _client()

    bounded_context, ctx_type, num_nodes, num_rels = retrieve_context(question, context)
    
    sys_prompt_len = len(SYSTEM_PROMPT)
    est_ctx_tokens = len(bounded_context) // 4
    est_total_tokens = (sys_prompt_len + len(question) + len(bounded_context)) // 4
    
    logger.info(f"Question: {question}")
    logger.info(f"Context type: {ctx_type}")
    if ctx_type == "graph":
        logger.info(f"Retrieved nodes: {num_nodes}")
        logger.info(f"Retrieved relationships: {num_rels}")
    else:
        logger.info(f"Retrieved chunks: {num_nodes}")
    logger.info(f"Estimated context tokens: {est_ctx_tokens}")
    logger.info(f"Estimated total prompt tokens: {est_total_tokens}")
    logger.info(f"Groq model: {model or DEFAULT_MODEL}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"EVIDENCE:\n\n{bounded_context}\n\nQUESTION:\n{question}",
        },
    ]

    try:
        response = client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            messages=messages,
            temperature=0,
        )
    except Exception as exc:
        try:
            from groq import AuthenticationError, APIStatusError
        except ImportError:  # pragma: no cover
            AuthenticationError = ()  # type: ignore[assignment]
            APIStatusError = () # type: ignore[assignment]
            
        if isinstance(exc, AuthenticationError):
            raise GroqNotConfiguredError(
                f"Groq rejected the configured GROQ_API_KEY as invalid: {exc}"
            ) from exc
            
        # 413 Handling: Retry ONCE with a substantially smaller context
        if isinstance(exc, APIStatusError) and exc.status_code == 413:
            logger.warning("Caught 413. Retrying ONCE with reduced context budget...")
            smaller_chars = MAX_CONTEXT_CHARS // 2
            smaller_context, _, _, _ = retrieve_context(question, context, max_chars=smaller_chars)
            messages[1]["content"] = f"EVIDENCE:\n\n{smaller_context}\n\nQUESTION:\n{question}"
            try:
                response = client.chat.completions.create(
                    model=model or DEFAULT_MODEL,
                    messages=messages,
                    temperature=0,
                )
            except Exception as exc2:
                raise GroqQAError("Retrieved context was too large. Please ask a more specific question.") from exc2
        else:
            raise GroqQAError(f"Groq API call failed: {type(exc).__name__}: {exc}") from exc

    answer = response.choices[0].message.content
    return (answer or "").strip()
