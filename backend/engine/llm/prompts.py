"""Prompt templates loaded from editable Markdown files."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

_STRICT = (
    "\n\nThe previous draft changed a protected detail or drifted in length. "
    "Write it again. Keep every number, name, URL, citation, hedge, and negation "
    "exactly, and stay close to the original length."
)
_BURST = (
    "\n\nMake the rhythm deliberately uneven: mix short and medium sentences, "
    "and do not repeat the same opening."
)


@lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8").strip()


def avoid_phrase(tells: Iterable[dict[str, Any]], limit: int = 10) -> str:
    names: list[str] = []
    for tell in tells:
        name = str(tell.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    if not names:
        return "none found in this passage"
    return ", ".join(names[:limit])


def _clip(text: str, limit: int) -> str:
    value = " ".join((text or "").split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def protect_extract(text: str) -> str:
    """Mask protected spans in context-only text before showing it to a provider."""
    from backend.engine import protect

    return protect.extract(text)[0]


def examples_block(examples: Iterable[dict[str, Any]]) -> str:
    rows = []
    for item in examples:
        source = _clip(str(item.get("source_text", "")), 420)
        rewritten = _clip(str(item.get("rewritten_text", "")), 420)
        if not source or not rewritten:
            continue
        rows.append(f"Source: {source}\nRewritten: {rewritten}")
    if not rows:
        return ""
    return "Examples of edits this app has kept:\n\n" + "\n\n".join(rows) + "\n\n"


def build_probe() -> tuple[str, str]:
    return (
        "Reply with the single word OK and nothing else.",
        "Connection test.",
    )


def build_sentence_rewrite(
    text: str,
    *,
    operation: str,
    instruction: str,
    tone: str,
    strength: str,
    avoid: str,
    previous: str = "",
    following: str = "",
    examples: Iterable[dict[str, Any]] = (),
    strict: bool = False,
) -> tuple[str, str]:
    """Build the per-sentence prompt from the editable Markdown files."""
    system = load_prompt("rewrite_sentence_system.md")
    system = system.replace("{operation}", instruction)
    system = system.replace("{strict}", _STRICT if strict else "")
    user = load_prompt("rewrite_sentence_user.md")
    if operation == "merge":
        count_rule = "Return ONE complete sentence that carries both source sentences."
    elif operation == "split":
        count_rule = "Return TWO complete sentences, separated by a space."
    else:
        count_rule = "Return ONE complete sentence."

    context: list[str] = []
    if previous:
        context.append(f"Previous sentence, for context only: {_clip(protect_extract(previous), 400)}")
    if following:
        context.append(f"Next sentence, for context only: {_clip(protect_extract(following), 400)}")
    user = user.replace("{text}", text)
    user = user.replace("{sentence_count_rule}", count_rule)
    user = user.replace("{context_block}", "\n".join(context))
    user = user.replace("{examples_block}", examples_block(examples).strip())
    user = user.replace("{tone}", tone)
    user = user.replace("{strength}", strength)
    user = user.replace("{avoid}", avoid)
    return system, user
