"""Humanizer prompt construction. Single source of truth for modes/intensity."""
from __future__ import annotations

from dataclasses import dataclass

from backend.core.ai_patterns import strong_patterns

MODES: dict[str, dict[str, str]] = {
    "balanced": {"label": "Balanced", "guidance": "Keep the author's style, but make the prose cleaner and more direct."},
    "natural": {"label": "Natural", "guidance": "Use plain, natural wording and an easy rhythm."},
    "concise": {"label": "Concise", "guidance": "Tighten the text and remove filler while keeping every fact."},
    "professional": {"label": "Professional", "guidance": "Use clear, specific workplace prose without jargon."},
    "academic": {"label": "Academic", "guidance": "Use precise scholarly prose; keep citations and terminology exact."},
    "casual": {"label": "Casual", "guidance": "Use an easy, conversational register without getting sloppy."},
    "persuasive": {"label": "Persuasive", "guidance": "Lead with the point and keep evidence intact without exaggeration."},
    "narrative": {"label": "Narrative", "guidance": "Favor clear flow and concrete detail; vary sentence length."},
}

INTENSITIES: dict[str, dict[str, str]] = {
    "light": {"label": "Light", "guidance": "Make small edits only where the text is awkward or padded."},
    "medium": {"label": "Medium", "guidance": "Rewrite sentence by sentence where helpful, but keep structure and order."},
    "strong": {"label": "Strong", "guidance": "Rewrite freely for clarity and flow, but never change facts or meaning."},
}

# Kept for backward compatibility with older imports/tests.
FORMULAIC_BAN = (
    "Furthermore, Moreover, Additionally, In conclusion, It is important to note, "
    "delve into, tapestry, landscape, realm, testament to"
)


@dataclass(frozen=True)
class HumanizeOptions:
    preserve_formatting: bool = True
    keep_quotes: bool = True
    deep_humanize: bool = False
    remove_em_dashes: bool = False
    clean_invisible: bool = True


def normalise_mode(mode: str | None) -> str:
    value = (mode or "").strip().lower()
    return value if value in MODES else "balanced"


def normalise_intensity(intensity: str | None) -> str:
    value = (intensity or "").strip().lower()
    return value if value in INTENSITIES else "medium"


def build_system_prompt(mode: str, intensity: str, options: HumanizeOptions) -> str:
    """Build a short system instruction sent to providers."""
    mode_key = normalise_mode(mode)
    intensity_key = normalise_intensity(intensity)

    formatting_rule = (
        "Preserve the paragraph and line structure."
        if options.preserve_formatting
        else "Paragraph breaks may be adjusted slightly."
    )
    quote_rule = (
        "Keep text in quotation marks, code, URLs, emails, and citations character-for-character."
        if options.keep_quotes
        else "Keep URLs, emails, code, and citations character-for-character."
    )

    pattern_lines = []
    for p in strong_patterns(10):
        name = str(p.get("name", "")).strip()
        hint = str(p.get("hint", "")).strip()
        if name and hint:
            pattern_lines.append(f"- {name}: {hint}")

    return "\n".join(
        [
            "You are a careful editor. Rewrite the user's text so it reads naturally.",
            "",
            "Rules:",
            "- Keep every fact, number, name, URL, and citation unchanged.",
            "- Do not add new claims, examples, or opinions.",
            "- Keep hedges and modal strength exactly (may/might/can/should must not become is/must). Do not swap adjectives or nouns for different meanings (good != clear).",
            '- Do not add Oxford commas or words like "ultimately", "moreover", "furthermore" unless the original has them.',
            "- Vary sentence structure for real: merge two short sentences or split one long one at least once per paragraph, and keep the order of ideas.",
            "- Avoid forced triads: if the original lists three items, keep them, but do not create new lists of three.",
            "- State points directly; vary sentence length.",
            "- Do not add emojis, bold, or decorative formatting.",
            f"- {formatting_rule}",
            f"- {quote_rule}",
            f"- Intensity: {INTENSITIES[intensity_key]['guidance']}",
            f"- Style: {MODES[mode_key]['guidance']}",
            "- Return only the rewritten text in the same language.",
            "",
            "Avoid common AI-writing patterns:",
            *pattern_lines,
        ]
    ).strip()


def meta_payload() -> dict[str, list[dict[str, str]]]:
    return {
        "modes": [{"id": k, "label": v["label"]} for k, v in MODES.items()],
        "intensities": [{"id": k, "label": v["label"]} for k, v in INTENSITIES.items()],
    }
