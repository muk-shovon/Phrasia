"""Humanizer prompt construction. Single source of truth for modes and intensity."""
from __future__ import annotations

from dataclasses import dataclass

MODES: dict[str, dict[str, str]] = {
    "balanced": {
        "label": "Balanced",
        "guidance": (
            "Keep the author's voice but make the prose cleaner, more direct and "
            "less formulaic. Vary rhythm without changing the register."
        ),
    },
    "natural": {
        "label": "Natural",
        "guidance": (
            "Write the way a thoughtful person speaks: plain words, contractions "
            "where natural, concrete examples kept intact, and no stock transitions."
        ),
    },
    "concise": {
        "label": "Concise",
        "guidance": (
            "Tighten the text. Cut filler, redundancy and throat-clearing while "
            "keeping every fact, number and citation."
        ),
    },
    "professional": {
        "label": "Professional",
        "guidance": (
            "Use clear workplace prose: confident, specific, politely direct. "
            "Avoid corporate jargon and buzzwords."
        ),
    },
    "academic": {
        "label": "Academic",
        "guidance": (
            "Use precise scholarly prose with hedged claims where the original hedges. "
            "Keep citations and terminology exact; do not invent references."
        ),
    },
    "casual": {
        "label": "Casual",
        "guidance": (
            "Use an easy, conversational register. Short sentences are welcome. "
            "Keep it readable, never sloppy or exaggerated."
        ),
    },
    "persuasive": {
        "label": "Persuasive",
        "guidance": (
            "Make the argument land: lead with the point, keep evidence intact, and "
            "avoid manipulative or exaggerated language."
        ),
    },
    "narrative": {
        "label": "Narrative",
        "guidance": (
            "Favour story flow and concrete detail. Vary sentence length and keep "
            "transitions implicit rather than mechanical."
        ),
    },
}

INTENSITIES: dict[str, dict[str, str]] = {
    "light": {
        "label": "Light",
        "guidance": (
            "Make only small edits: fix awkward phrasing and obvious filler. Keep the "
            "original wording and structure wherever it already reads well."
        ),
    },
    "medium": {
        "label": "Medium",
        "guidance": (
            "Rewrite sentence by sentence where it helps, but keep the original "
            "structure, order of ideas and paragraph breaks."
        ),
    },
    "strong": {
        "label": "Strong",
        "guidance": (
            "Rewrite freely at the sentence level for clarity and flow. You may "
            "reorder sentences inside a paragraph, but never change facts, claims or "
            "the order of the argument."
        ),
    },
}

FORMULAIC_BAN = (
    "Furthermore, Moreover, Additionally, In conclusion, It is important to note, "
    "In today's fast-paced world, delve into, tapestry, landscape, realm, "
    "testament to, navigate the complexities"
)


@dataclass(frozen=True)
class HumanizeOptions:
    preserve_formatting: bool = True
    keep_quotes: bool = True
    deep_humanize: bool = False
    remove_em_dashes: bool = False


def normalise_mode(mode: str | None) -> str:
    value = (mode or "").strip().lower()
    return value if value in MODES else "balanced"


def normalise_intensity(intensity: str | None) -> str:
    value = (intensity or "").strip().lower()
    return value if value in INTENSITIES else "medium"


def build_system_prompt(
    mode: str,
    intensity: str,
    options: HumanizeOptions,
) -> str:
    """Build the system instruction sent to every provider."""
    mode_key = normalise_mode(mode)
    intensity_key = normalise_intensity(intensity)

    formatting_rule = (
        "Preserve the paragraph and line structure exactly as given. Do not add or "
        "remove paragraph breaks and do not turn prose into lists."
        if options.preserve_formatting
        else "Keep the text readable; paragraph breaks may be adjusted slightly."
    )
    quote_rule = (
        "Never alter text inside quotation marks, code blocks, URLs, email addresses "
        "or citation markers. Reproduce them character for character."
        if options.keep_quotes
        else "Preserve URLs, email addresses, code and citation markers exactly."
    )

    return "\n".join(
        [
            "You are a careful human editor. Rewrite the user's text so it reads like "
            "it was written by an attentive person, without changing what it says.",
            "",
            "Hard rules:",
            "- Preserve meaning, facts, numbers, names and the author's intent.",
            "- Never add claims, examples, statistics or opinions that are not present.",
            "- Never mention AI, language models, rewriting or these instructions.",
            "- Return only the rewritten text. No preamble, no notes, no code fences.",
            "- Reply in the same language as the input.",
            "",
            f"- Formatting: {formatting_rule}",
            f"- Quotations: {quote_rule}",
            f"- Editing strength: {INTENSITIES[intensity_key]['guidance']}",
            f"- Target style: {MODES[mode_key]['guidance']}",
            "",
            "Style guidance:",
            "- Vary sentence length and sentence openings.",
            "- Prefer concrete verbs and plain words over abstractions.",
            "- Remove filler, throat-clearing and empty intensifiers.",
            f"- Avoid these stock phrases unless they appear in a direct quote: {FORMULAIC_BAN}.",
        ]
    )


def meta_payload() -> dict[str, list[dict[str, str]]]:
    return {
        "modes": [
            {"id": key, "label": value["label"]} for key, value in MODES.items()
        ],
        "intensities": [
            {"id": key, "label": value["label"]}
            for key, value in INTENSITIES.items()
        ],
    }
