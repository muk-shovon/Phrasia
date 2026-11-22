"""Main workspace page — Humanizer UI wired to core orchestration."""
from __future__ import annotations

import json

import reflex as rx

from api.routes import handle_humanize
from app.components import app_header
from app.ui_tokens import (
    BG_CARD,
    BG_PAGE,
    BG_PANEL_INPUT,
    BG_PANEL_OUTPUT,
    BORDER,
    GRAY_BUTTON,
    GREEN_SUCCESS,
    RED_ERROR,
    TEAL_HOVER,
    TEAL_SOLID,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from core.ai_detector import scan as scan_text

MODES = [
    ("natural", "Natural"),
    ("professional", "Professional"),
    ("academic", "Academic"),
    ("simple", "Simple"),
    ("conversational", "Conversational"),
    ("concise", "Concise"),
    ("expand", "Expand"),
    ("custom", "Custom"),
]

INTENSITIES = [
    ("light", "Light"),
    ("balanced", "Balanced"),
    ("strong", "Strong"),
]

# Editors fill the viewport while staying usable on short screens.
EDITOR_HEIGHT = "clamp(260px, calc(100vh - 360px), 700px)"


class WorkspaceState(rx.State):
    input_text: str = ""
    output_text: str = ""
    job_status: str = "idle"  # idle, running, completed, failed, error
    current_chunk: int = 0
    total_chunks: int = 0
    completed_chunks: int = 0
    error_message: str = ""
    provider_used: str = ""
    mode_selected: str = "natural"
    intensity_selected: str = "balanced"
    preserve_meaning: bool = True
    preserve_facts: bool = True
    preserve_citations: bool = True
    deep_humanize: bool = True
    custom_instruction: str = ""
    word_count: int = 0
    char_count: int = 0
    is_processing: bool = False
    copied: bool = False
    input_score: int = 0
    input_verdict: str = ""
    input_sentences: list[dict] = []
    output_score: int = 0
    output_verdict: str = ""
    output_sentences: list[dict] = []
    show_deep_scan: bool = False
    strength: int = 60
    formal: bool = False

    def on_input_change(self, value: str) -> None:
        self.input_text = value
        self.word_count = len(value.split()) if value.strip() else 0
        self.char_count = len(value)
        self.copied = False

    def set_mode(self, mode: str) -> None:
        self.mode_selected = mode

    def set_intensity(self, intensity: str) -> None:
        self.intensity_selected = intensity

    def set_custom_instruction(self, val: str) -> None:
        self.custom_instruction = val

    def toggle_preserve_meaning(self, val: bool) -> None:
        self.preserve_meaning = val

    def toggle_preserve_facts(self, val: bool) -> None:
        self.preserve_facts = val

    def toggle_preserve_citations(self, val: bool) -> None:
        self.preserve_citations = val

    def set_deep_humanize(self, val: bool) -> None:
        self.deep_humanize = val

    def scan_input(self) -> None:
        if not self.input_text.strip():
            return
        result = scan_text(self.input_text)
        self.input_score = round(result.normal_score * 100)
        self.input_verdict = result.verdict
        self.input_sentences = [s.as_dict() for s in result.sentences]

    def scan_output(self) -> None:
        if not self.output_text.strip():
            return
        result = scan_text(self.output_text)
        self.output_score = round(result.normal_score * 100)
        self.output_verdict = result.verdict
        self.output_sentences = [s.as_dict() for s in result.sentences]

    def toggle_deep_scan(self) -> None:
        self.show_deep_scan = not self.show_deep_scan

    def set_strength(self, value: list) -> None:
        self.strength = int(value[0])

    def set_formal(self, value: bool) -> None:
        self.formal = value

    def copy_output(self):
        if not self.output_text:
            return
        self.copied = True
        return rx.set_clipboard(self.output_text)

    async def humanize(self) -> None:
        if not self.input_text.strip():
            self.error_message = "Please enter or paste some text first."
            self.job_status = "error"
            return

        self.job_status = "running"
        self.error_message = ""
        self.is_processing = True
        self.output_text = ""
        self.copied = False

        payload = {
            "input_text": self.input_text,
            "mode": self.mode_selected,
            "intensity": self.intensity_selected,
            "preserve_meaning": self.preserve_meaning,
            "preserve_facts": self.preserve_facts,
            "preserve_citations": self.preserve_citations,
            "deep_humanize": self.deep_humanize,
            "custom_instruction": self.custom_instruction or None,
            "strength": self.strength / 100.0,
            "formal": self.formal,
        }

        try:
            res = await handle_humanize(payload)
            body = (
                json.loads(res["body"])
                if isinstance(res.get("body"), str)
                else res.get("body", {})
            )

            if res.get("status_code") == 200 and body.get("status") in ("completed", "running"):
                self.output_text = body.get("output", "")
                self.job_status = "completed"
                self.provider_used = body.get("provider_used", "")
                self.completed_chunks = body.get("completed_chunks", 1)
                self.total_chunks = body.get("total_chunks", 1)
                self.scan_output()
            else:
                self.error_message = (
                    body.get("error_message")
                    or body.get("error")
                    or "Humanization failed. Check server/provider configuration."
                )
                self.job_status = "failed"
                self.output_text = body.get("output", "")
        except Exception as exc:
            self.error_message = f"Request error: {str(exc)}"
            self.job_status = "failed"
        finally:
            self.is_processing = False


# Module-level shorthand so UI helpers can reference event handlers.
state = WorkspaceState


def mode_chip(mode_val: str, label: str, selected) -> rx.Component:
    """Individual tone/mode selection button."""
    return rx.button(
        label,
        type="button",
        size="1",
        variant=rx.cond(selected, "solid", "outline"),
        color_scheme="gray",
        on_click=state.set_mode(mode_val),
        style={
            "borderColor": rx.cond(selected, TEAL_SOLID, BORDER),
            "color": rx.cond(selected, "#FFFFFF", TEXT_PRIMARY),
            "background": rx.cond(selected, TEAL_SOLID, BG_CARD),
            "fontWeight": rx.cond(selected, "600", "500"),
            "minWidth": "96px",
            "justifyContent": "flex-start",
            "textAlign": "left",
            "height": "34px",
            "fontSize": "0.82rem",
            "whiteSpace": "nowrap",
        },
    )


def intensity_chip(val: str, label: str, selected) -> rx.Component:
    """Individual intensity selection button."""
    return rx.button(
        label,
        type="button",
        size="1",
        variant=rx.cond(selected, "solid", "outline"),
        color_scheme="gray",
        on_click=state.set_intensity(val),
        style={
            "borderColor": rx.cond(selected, TEXT_SECONDARY, GRAY_BUTTON),
            "color": rx.cond(selected, "#FFFFFF", TEXT_PRIMARY),
            "background": rx.cond(selected, TEXT_SECONDARY, BG_CARD),
            "fontWeight": rx.cond(selected, "600", "500"),
            "minWidth": "80px",
            "justifyContent": "center",
            "height": "34px",
            "fontSize": "0.8rem",
            "whiteSpace": "nowrap",
        },
    )


def status_label(status) -> rx.Var:
    """Human-readable job status label."""
    return rx.cond(
        status == "idle", "Idle",
        rx.cond(
            status == "running", "Running",
            rx.cond(
                status == "completed", "Done",
                rx.cond(
                    status == "failed", "Failed",
                    rx.cond(status == "error", "Error", status),
                ),
            ),
        ),
    )


def status_color_scheme(status) -> rx.Var:
    """Radix color scheme for the status badge (computed from the Var)."""
    return rx.cond(
        status == "completed", "green",
        rx.cond(
            status == "failed", "red",
            rx.cond(status == "error", "red", rx.cond(status == "running", "teal", "gray")),
        ),
    )


def options_bar() -> rx.Component:
    """Tone + intensity controls, in normal flow below the header."""
    return rx.box(
        rx.grid(
            rx.vstack(
                rx.text(
                    "Tone",
                    font_size="0.72rem",
                    font_weight="700",
                    color=TEXT_MUTED,
                    letter_spacing="0.8px",
                    text_transform="uppercase",
                ),
                rx.flex(
                    *[mode_chip(mv, lb, state.mode_selected == mv) for mv, lb in MODES],
                    wrap="wrap",
                    gap="6px",
                ),
                align="start",
                spacing="2",
                width="100%",
            ),
            rx.vstack(
                rx.text(
                    "Intensity",
                    font_size="0.72rem",
                    font_weight="700",
                    color=TEXT_MUTED,
                    letter_spacing="0.8px",
                    text_transform="uppercase",
                ),
                rx.flex(
                    *[
                        intensity_chip(iv, lb, state.intensity_selected == iv)
                        for iv, lb in INTENSITIES
                    ],
                    wrap="wrap",
                    gap="6px",
                ),
                align="start",
                spacing="2",
                width="100%",
            ),
            columns=rx.breakpoints(initial="1", md="2"),
            gap="24px",
            width="100%",
            max_width="1400px",
            margin_x="auto",
            padding="14px 24px 6px",
            align_items="start",
        ),
        rx.hstack(
            rx.switch(
                checked=state.deep_humanize,
                on_change=state.set_deep_humanize,
                color_scheme="teal",
                size="1",
            ),
            rx.text(
                "Deep human pass — a second rewrite that reduces machine-like phrasing "
                "(uses about 2x requests).",
                font_size="0.78rem",
                color=TEXT_MUTED,
            ),
            align="center",
            gap="8px",
            width="100%",
            max_width="1400px",
            margin_x="auto",
            padding="4px 24px 12px",
        ),
        rx.hstack(
            rx.text(
                "Extra instruction",
                font_size="0.72rem",
                font_weight="700",
                color=TEXT_MUTED,
                letter_spacing="0.6px",
                text_transform="uppercase",
                white_space="nowrap",
            ),
            rx.input(
                placeholder="e.g. Use short sentences and a conversational tone",
                value=state.custom_instruction,
                on_change=state.set_custom_instruction,
                debounce_timeout=150,
                force_notify_on_blur=True,
                size="2",
                width="100%",
                max_width="560px",
            ),
            align="center",
            gap="10px",
            width="100%",
            max_width="1400px",
            margin_x="auto",
            padding="4px 24px 14px",
        ),
        width="100%",
        background=BG_CARD,
        border_bottom=f"1px solid {BORDER}",
    )


def panel_shell(
    *,
    title: str,
    header_right: rx.Component,
    textarea: rx.Component,
    footer: rx.Component,
    background: str,
) -> rx.Component:
    """Shared panel frame: header / editor / action bar."""
    return rx.box(
        rx.flex(
            rx.text(
                title,
                font_size="0.9rem",
                font_weight="700",
                color=TEXT_PRIMARY,
            ),
            rx.spacer(),
            header_right,
            align="center",
            justify="between",
            width="100%",
            min_height="48px",
            padding="10px 16px",
            border_bottom=f"1px solid {BORDER}",
            background=background,
            border_radius="12px 12px 0 0",
            gap="8px",
        ),
        textarea,
        footer,
        background=background,
        border_radius="12px",
        border=f"1px solid {BORDER}",
        box_shadow="0 2px 12px rgba(27,94,59,0.07)",
        overflow="hidden",
        min_width="0",
        display="flex",
        flex_direction="column",
    )


def workspace_page() -> rx.Component:
    input_panel = panel_shell(
        title="Original Text",
        header_right=rx.hstack(
            rx.badge(
                f"{state.word_count} words",
                variant="soft",
                color_scheme="gray",
                size="1",
            ),
            rx.badge(
                f"{state.char_count} chars",
                variant="soft",
                color_scheme="gray",
                size="1",
            ),
            rx.cond(
                state.input_verdict != "",
                rx.badge(
                    f"AI check: {state.input_score}% · {state.input_verdict}",
                    variant="soft",
                    color_scheme=rx.cond(
                        state.input_verdict == "Looks Human", "green", "red"
                    ),
                    size="1",
                ),
                rx.fragment(),
            ),
            gap="6px",
            align="center",
        ),
        textarea=rx.text_area(
            placeholder="Paste or type your text here…",
            value=state.input_text,
            on_change=state.on_input_change,
            debounce_timeout=100,
            force_notify_on_blur=True,
            size="3",
            width="100%",
            height=EDITOR_HEIGHT,
            resize="none",
            border="none",
            outline="none",
            # DebounceInput wraps the Radix textarea, so padding must target the
            # inner <textarea> to match the output editor exactly.
            padding="0",
            style={"textarea": {"padding": "14px 16px"}},
            font_size="0.95rem",
            line_height="1.7",
            color=TEXT_PRIMARY,
            background=BG_PANEL_INPUT,
            font_family="Inter, ui-sans-serif, system-ui, sans-serif",
            _placeholder={"color": TEXT_MUTED, "opacity": "1"},
        ),
        footer=rx.box(
            rx.vstack(
                rx.hstack(
                    rx.button(
                        "Scan for AI",
                        type="button",
                        on_click=state.scan_input,
                        color_scheme="gray",
                        variant="outline",
                        style={"height": "44px", "padding_x": "16px", "fontWeight": "600"},
                    ),
                    rx.button(
                        "✦  Humanize Text",
                        type="button",
                        color_scheme="teal",
                        loading=state.is_processing,
                        disabled=state.is_processing,
                        on_click=state.humanize,
                        width="100%",
                        style={
                            "height": "44px",
                            "fontWeight": "700",
                            "fontSize": "0.95rem",
                            "letterSpacing": "0.3px",
                            "borderRadius": "8px",
                            "background": TEAL_SOLID,
                            "color": "#FFFFFF",
                            "_hover": {"background": TEAL_HOVER},
                        },
                    ),
                    gap="8px",
                    width="100%",
                ),
                rx.hstack(
                    rx.text(
                        "Strength",
                        font_size="0.74rem",
                        color=TEXT_MUTED,
                        white_space="nowrap",
                    ),
                    rx.slider(
                        value=[state.strength],
                        on_change=state.set_strength,
                        min=0,
                        max=100,
                        step=1,
                        color_scheme="teal",
                        width="130px",
                    ),
                    rx.text(f"{state.strength}%", font_size="0.74rem", color=TEXT_PRIMARY),
                    rx.spacer(),
                    rx.checkbox(
                        checked=state.formal,
                        on_change=state.set_formal,
                        color_scheme="teal",
                        size="1",
                    ),
                    rx.text(
                        "Formal tone",
                        font_size="0.74rem",
                        color=TEXT_MUTED,
                        white_space="nowrap",
                    ),
                    align="center",
                    gap="8px",
                    width="100%",
                ),
                spacing="2",
                width="100%",
            ),
            padding="12px 16px",
            width="100%",
        ),
        background=BG_PANEL_INPUT,
    )

    output_panel = panel_shell(
        title="Rewritten Text",
        header_right=rx.hstack(
            rx.badge(
                status_label(state.job_status),
                variant="soft",
                color_scheme=status_color_scheme(state.job_status),
                size="1",
            ),
            rx.cond(
                state.provider_used != "",
                rx.badge(
                    f"via {state.provider_used}",
                    variant="soft",
                    color_scheme="gray",
                    size="1",
                    text_transform="lowercase",
                ),
                rx.fragment(),
            ),
            gap="6px",
            align="center",
        ),
        textarea=rx.text_area(
            value=state.output_text,
            placeholder="Your humanized text will appear here…",
            read_only=True,
            size="3",
            width="100%",
            height=EDITOR_HEIGHT,
            resize="none",
            border="none",
            outline="none",
            padding="14px 16px",
            # Radix dims read-only textareas to gray-a11; keep generated text
            # fully legible instead.
            style={
                "textarea": {
                    "color": TEXT_PRIMARY,
                    "-webkit-text-fill-color": TEXT_PRIMARY,
                    "opacity": "1",
                }
            },
            font_size="0.95rem",
            line_height="1.7",
            color=TEXT_PRIMARY,
            background=BG_PANEL_OUTPUT,
            font_family="Inter, ui-sans-serif, system-ui, sans-serif",
            _placeholder={"color": TEXT_MUTED, "opacity": "1"},
        ),
        footer=rx.box(
            rx.hstack(
                rx.button(
                    rx.cond(state.copied, "Copied ✓", "Copy"),
                    type="button",
                    on_click=state.copy_output,
                    color_scheme="gray",
                    variant="soft",
                    disabled=state.output_text == "",
                    style={
                        "height": "44px",
                        "padding_x": "18px",
                        "fontWeight": "600",
                        "fontSize": "0.85rem",
                        "borderRadius": "8px",
                        "minWidth": "96px",
                    },
                ),
                rx.spacer(),
                rx.cond(
                    state.output_verdict != "",
                    rx.hstack(
                        rx.text(
                            f"{state.output_score}%",
                            font_size="0.9rem",
                            font_weight="700",
                            color=rx.cond(
                                state.output_verdict == "Looks Human",
                                GREEN_SUCCESS,
                                RED_ERROR,
                            ),
                        ),
                        rx.text(
                            state.output_verdict,
                            font_size="0.75rem",
                            color=TEXT_MUTED,
                        ),
                        rx.button(
                            "Deep Scan",
                            type="button",
                            size="1",
                            variant="ghost",
                            on_click=state.toggle_deep_scan,
                            style={"height": "28px", "fontSize": "0.72rem"},
                        ),
                        gap="6px",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    state.copied,
                    rx.text(
                        "Copied to clipboard",
                        font_size="0.75rem",
                        color=GREEN_SUCCESS,
                        font_weight="600",
                    ),
                    rx.fragment(),
                ),
                width="100%",
                align="center",
                gap="8px",
            ),
            padding="12px 16px",
            width="100%",
        ),
        background=BG_PANEL_OUTPUT,
    )

    return rx.box(
        app_header("workspace"),
        options_bar(),
        rx.box(
            rx.grid(
                input_panel,
                output_panel,
                columns=rx.breakpoints(initial="1", md="2"),
                gap="16px",
                width="100%",
                max_width="1400px",
                margin_x="auto",
                padding="20px 24px",
                align_items="stretch",
            ),
            width="100%",
        ),
        rx.cond(
            state.show_deep_scan,
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            "Deep Scan — sentence by sentence",
                            font_size="0.95rem",
                            font_weight="700",
                            color=TEXT_PRIMARY,
                        ),
                        rx.spacer(),
                        rx.cond(
                            state.input_verdict != "",
                            rx.text(
                                f"Original: {state.input_score}% · {state.input_verdict}",
                                font_size="0.78rem",
                                color=TEXT_MUTED,
                            ),
                            rx.fragment(),
                        ),
                        width="100%",
                    ),
                    rx.foreach(
                        state.output_sentences,
                        lambda s: rx.hstack(
                            rx.badge(
                                f"{s['score_pct']}%",
                                color_scheme=rx.cond(s["looks_human"], "green", "red"),
                                variant="soft",
                                size="1",
                            ),
                            rx.text(
                                s["sentence"],
                                font_size="0.85rem",
                                color=TEXT_PRIMARY,
                                line_height="1.5",
                            ),
                            width="100%",
                            align="start",
                            gap="10px",
                            padding="8px 10px",
                            border_radius="8px",
                            background=rx.cond(
                                s["looks_human"], "#F0F7F0", "#FDF2F2"
                            ),
                        ),
                    ),
                    width="100%",
                    align="start",
                    spacing="2",
                ),
                width="100%",
                max_width="1400px",
                margin_x="auto",
                padding="16px 24px",
                background=BG_CARD,
                border=f"1px solid {BORDER}",
                border_radius="12px",
            ),
            rx.fragment(),
        ),
        rx.cond(
            state.error_message != "",
            rx.box(
                rx.flex(
                    rx.text("⚠", font_size="1rem", color=RED_ERROR),
                    rx.text(
                        state.error_message,
                        font_size="0.85rem",
                        color=RED_ERROR,
                        font_weight="500",
                    ),
                    align="center",
                    gap="8px",
                    width="100%",
                    padding="12px 16px",
                    border_radius="8px",
                    background="#FEF2F2",
                    border="1px solid #FECACA",
                ),
                width="100%",
                max_width="1400px",
                margin_x="auto",
                padding="0px 24px",
            ),
            rx.fragment(),
        ),
        rx.box(height="24px"),
        width="100%",
        min_height="100vh",
        background=BG_PAGE,
        font_family="Inter, ui-sans-serif, system-ui, sans-serif",
    )


def home_page() -> rx.Component:
    return workspace_page()
