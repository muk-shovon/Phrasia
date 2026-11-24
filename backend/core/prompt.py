"""Humanizer prompt construction. Single source of truth for tones/strengths."""
from __future__ import annotations

from dataclasses import dataclass

from backend.core.ai_patterns import strong_patterns

MODES: dict[str, dict[str, str]] = {
    "casual": {"label": "Casual", "guidance": "Friendly peer voice, everyday words, natural contractions."},
    "professional": {"label": "Professional", "guidance": "Clear, direct, polite, no corporate buzzwords."},
    "academic": {"label": "Academic", "guidance": "Objective, active and readable, few or no contractions, no bloated filler."},
    "marketing": {"label": "Marketing", "guidance": "Punchy and persuasive, but use ONLY benefits stated in the source."},
    "storytelling": {"label": "Storytelling", "guidance": "Natural narrative flow, concrete detail ONLY from the source, no invented scenes or facts."},
    "balanced": {"label": "Balanced", "guidance": "Keep the author's style, but make the prose cleaner and more direct."},
    "natural": {"label": "Natural", "guidance": "Use plain, natural wording and an easy rhythm."},
    "concise": {"label": "Concise", "guidance": "Tighten the text and remove filler while keeping every fact."},
    "persuasive": {"label": "Persuasive", "guidance": "Lead with the point and keep evidence intact without exaggeration."},
    "narrative": {"label": "Narrative", "guidance": "Favor clear flow and concrete detail; vary sentence length."},
}

INTENSITIES: dict[str, dict[str, str]] = {
    "light": {"label": "Light", "guidance": "Fix AI cliches, robotic transitions and passive voice; keep most sentence structure."},
    "medium": {"label": "Medium", "guidance": "Restructure most sentences, varied rhythm, everyday vocabulary, same order of ideas."},
    "heavy": {"label": "Heavy", "guidance": "Rebuild every sentence's structure. Keep paragraph count and order of ideas."},
    "strong": {"label": "Strong", "guidance": "Rebuild every sentence's structure. Keep paragraph count and order of ideas."},
}

FORMULAIC_BAN = (
    "Furthermore, Moreover, Additionally, In conclusion, It is important to note, "
    "delve into, tapestry, landscape, realm, testament to"
)

WORST_OFFENDERS = "delve, tapestry, crucial, pivotal, leverage, furthermore, moreover, in conclusion"


@dataclass(frozen=True)
class HumanizeOptions:
    preserve_formatting: bool = True
    keep_quotes: bool = True
    deep_humanize: bool = False
    remove_em_dashes: bool = False
    clean_invisible: bool = True


def normalise_mode(mode: str | None) -> str:
    value = (mode or "").strip().lower()
    return value if value in MODES else "casual"


def normalise_intensity(intensity: str | None) -> str:
    value = (intensity or "").strip().lower()
    if value == "strong":
        value = "heavy"
    return value if value in INTENSITIES else "medium"


def build_system_prompt(mode: str, intensity: str, options: HumanizeOptions) -> str:
    """Build a short system instruction sent to providers."""
    mode_key = normalise_mode(mode)
    intensity_key = normalise_intensity(intensity)

    formatting_rule = (
        "Preserve the paragraph and line structure; keep headings, lists and paragraph breaks exactly."
        if options.preserve_formatting
        else "Paragraph breaks may be adjusted slightly."
    )
    quote_rule = (
        "Keep text in quotation marks, code, URLs, emails, and citations character-for-character."
        if options.keep_quotes
        else "Keep URLs, emails, code, and citations character-for-character."
    )

    tone_line = f"Tone ({mode_key}): {MODES[mode_key]['guidance']}"
    strength_line = f"Strength ({intensity_key}): {INTENSITIES[intensity_key]['guidance']}"
    contraction_rule = (
        "Contractions are natural; fragments, one rhetorical question or one short (parenthetical) remark allowed only in casual/storytelling, max one per paragraph."
        if mode_key in {"casual", "storytelling"}
        else "Use contractions only where the tone allows; no fragments, rhetorical questions, or parenthetical asides unless the source has them."
    )

    return "\n".join(
        [
            "You are a human editor. Rewrite the text so it reads like a person wrote it.",
            "Input sentences are tagged [S1], [S2]... Return the same tags in order. Merge [S1+S2] or split as [S4] lines when needed.",
            tone_line,
            strength_line,
            "",
            "Style:",
            "- Plain words, active voice. Start each paragraph with its main point.",
            "- Vary sentence length (some 3-7 words, some 16-25); never three similar-length sentences in a row.",
            f"- {contraction_rule}",
            "",
            "HARD constraints:",
            "- Keep every fact, number, name, URL, citation unchanged.",
            "- Keep hedges and modal strength exactly (may/might/can/should/must, always/usually/often, not/no). Add no new claims.",
            "- Keep the source's lists as they are (do not create new groups of three, do not split an existing three-item list).",
            f"- {formatting_rule}",
            f"- {quote_rule}",
            '- Do not add moreover/furthermore/additionally/ultimately or Oxford commas not in the source.',
            f"- Avoid AI words, especially: {WORST_OFFENDERS}.",
            "- Output only the tagged sentences, no preamble, no notes.",
        ]
    ).strip()


def meta_payload() -> dict[str, list[dict[str, str]]]:
    return {
        "modes": [{"id": k, "label": v["label"]} for k, v in MODES.items()],
        "intensities": [
            {"id": k, "label": v["label"]} for k, v in INTENSITIES.items() if k != "strong"
        ],
    }
