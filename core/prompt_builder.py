"""Versioned prompt templates for the Humanizer pipeline."""
from __future__ import annotations

PROMPT_VERSION = "2"


# Phrases that make text read like a generic model completion. Included in the
# prompt so the model actively avoids them, and in the post-processor as a
# deterministic safety net.
AI_TELL_PHRASES = (
    "it is important to note that",
    "it's important to note that",
    "it is worth noting that",
    "it's worth noting that",
    "in conclusion",
    "furthermore",
    "moreover",
    "additionally",
    "overall",
    "in summary",
    "that being said",
)

AI_TELL_WORDS = (
    "delve",
    "tapestry",
    "testament",
    "realm",
    "landscape",
    "crucial",
    "pivotal",
    "vital",
    "robust",
    "seamless",
    "foster",
    "leverage",
    "utilize",
    "navigate",
    "underscore",
    "comprehensive",
    "multifaceted",
    "ever-evolving",
)


_HUMAN_SIGNATURE_RULES = [
    "HUMAN WRITING STYLE — this is the most important stylistic requirement:",
    "- Write like a real person who has thought about the topic, not like a "
    "model completing a template.",
    "- Vary sentence length sharply. Mix very short sentences (3-8 words) with "
    "longer ones. Never let a paragraph consist of sentences of equal length.",
    "- Use natural contractions (it's, don't, can't, we've, that's) unless the chosen mode "
    "explicitly forbids them.",
    "- Break perfect parallel structure. Do not make every bullet or sentence start the same way.",
    "- Prefer concrete, everyday words over abstract buzzwords. Say 'use' instead of 'utilize', "
    "'help' instead of 'facilitate'.",
    "- Avoid stock transitions and filler: " + ", ".join(f"'{p}'" for p in AI_TELL_PHRASES) + ".",
    "- Avoid AI-cliché vocabulary: " + ", ".join(f"'{w}'" for w in AI_TELL_WORDS) + ".",
    "- Do not add a tidy summary paragraph at the end unless the original had one.",
    "- Keep a little natural roughness — an occasional short fragment, a parenthetical, or an "
    "aside is welcome. Do not polish away the author's voice.",
    "- Do NOT claim the output has passed, or will evade, any AI detector.",
]


def build_humanizer_prompt(
    *,
    mode: str,
    intensity: str,
    preserve_meaning: bool,
    preserve_facts: bool,
    preserve_citations: bool,
    preserve_formatting: bool,
    preserve_quotes: bool,
    custom_instruction: str | None,
    language_hint: str | None,
) -> tuple[str, str]:
    """Builds ``(system_instruction, user_instruction)`` for a generation request."""
    system_lines = [
        f"You are Phrasia's Humanizer engine (prompt version {PROMPT_VERSION}).",
        "Rewrite the supplied text so it reads as naturally written by a real person, "
        "while preserving its meaning and facts.",
        "Aim for natural flow and clarity, but never at the cost of sounding machine-written.",
        "",
        "MANDATORY RULES:",
        "- Preserve the original meaning and factual claims exactly.",
        "- Do NOT invent facts, citations, links, statistics, or source material.",
        "- Do NOT add personal anecdotes or speculative content.",
    ]
    if preserve_facts:
        system_lines.append(
            "- Preserve all names, dates, amounts, numeric values, proper nouns, and identifiers."
        )
    if preserve_citations:
        system_lines.append(
            "- Preserve citation markers, reference strings, bracketed numbers, and "
            "quotation marks exactly."
        )
    if preserve_quotes:
        system_lines.append(
            "- Do not rewrite text inside explicit block-quoted passages unless instructed."
        )
    if preserve_formatting:
        system_lines.append(
            "- Preserve headings, paragraph breaks, lists, and structural markers where possible."
        )
    system_lines += ["", *_HUMAN_SIGNATURE_RULES]
    system_lines += [
        "",
        "RETURN FORMAT: Output ONLY the rewritten text. No commentary, no preamble, "
        "no notes about your changes.",
    ]
    if language_hint:
        system_lines.append(
            f"The input language is likely: {language_hint}. Keep the output in the same "
            "language unless explicitly translated."
        )

    intensity_note = ""
    if intensity == "light":
        intensity_note = (
            "Make modest changes. Keep the original phrasing where it already sounds "
            "natural, but smooth stiff or formulaic sentences."
        )
    elif intensity == "balanced":
        intensity_note = (
            "Rewrite noticeably: change word choices and sentence rhythm so the prose "
            "sounds like a person wrote it, while keeping every claim intact."
        )
    elif intensity == "strong":
        intensity_note = (
            "Rewrite aggressively for a distinctly human voice. Restructure freely, vary "
            "sentence length widely, and remove every trace of formulaic model prose. "
            "Meaning and facts must still be identical."
        )

    user_lines = [
        f"Mode: {mode}",
        f"Intensity: {intensity}",
        intensity_note,
        *_mode_instructions(mode),
    ]
    if custom_instruction:
        user_lines.append(f"\nAdditional instruction from author: {custom_instruction}")
    user_lines.append("\nRewrite the following text:")
    return "\n".join(system_lines), "\n".join(user_lines)


def build_dehumanize_prompt(*, language_hint: str | None = None) -> tuple[str, str]:
    """Second-pass prompt: strip remaining model-like patterns from a draft."""
    system = "\n".join(
        [
            f"You are Phrasia's humanization editor (prompt version {PROMPT_VERSION}).",
            "You receive a draft that is correct but still reads as machine-written.",
            "Rewrite it so a human reader would believe a person wrote it.",
            "",
            "RULES:",
            "- Keep every fact, number, name, citation, and claim exactly as written.",
            "- Do not add new information, examples, opinions, or anecdotes.",
            *_HUMAN_SIGNATURE_RULES,
            "- Instead of a tidy conclusion, end the way a person naturally would — "
            "sometimes that means stopping on the last concrete point.",
            "- Return ONLY the rewritten text. No commentary.",
        ]
    )
    if language_hint:
        system += f"\nKeep the same language: {language_hint}."
    user = (
        "Rewrite the draft below to remove any remaining AI-like patterns. "
        "Keep it roughly the same length.\n\nDraft:\n"
    )
    return system, user


def _mode_instructions(mode: str) -> list[str]:
    modes = {
        "natural": [
            "Goal: writing that feels like a careful human writer, warm but not gushing.",
            "Break up evenly sized sentences. Use everyday words. Allow a short fragment "
            "here and there.",
        ],
        "professional": [
            "Goal: polished professional writing that still sounds like a person, not a "
            "corporate template.",
            "Use plain business language. Avoid buzzwords and stacked abstractions. "
            "Contractions are fine.",
        ],
        "academic": [
            "Goal: precise scholarly prose that avoids mechanical, textbook uniformity.",
            "Keep terminology and formal tone, but vary sentence rhythm and drop filler "
            "transitions. Avoid the stock academic openers.",
        ],
        "simple": [
            "Goal: plain, clear language a reader can grasp immediately.",
            "Use short words and short sentences. Mix in a longer sentence occasionally "
            "so it does not sound like a children's primer.",
        ],
        "conversational": [
            "Goal: write the way a knowledgeable friend explains something over coffee.",
            "Use contractions, direct address where suitable, and natural asides. "
            "Avoid neat transitions entirely.",
        ],
        "concise": [
            "Goal: same information, fewer words, human rhythm.",
            "Cut filler and stock transitions. Keep a mix of short and medium sentences.",
        ],
        "expand": [
            "Goal: fuller explanation that still sounds like a real author.",
            "Add useful connective tissue and concrete detail, but never invent facts. "
            "Vary sentence lengths as a person would.",
        ],
        "custom": [],
    }
    return modes.get(mode, modes["natural"])
