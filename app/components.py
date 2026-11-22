"""Shared layout components (header + navigation)."""
from __future__ import annotations

import reflex as rx

from app.ui_tokens import (
    BG_CARD,
    BORDER,
    TEAL_HOVER,
    TEAL_SOLID,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

NAV_ITEMS = [
    ("Workspace", "", "workspace"),
    ("History", "history", "history"),
    ("Settings", "settings", "settings"),
]


def nav_item(label: str, route: str, active: bool = False) -> rx.Component:
    """Navigation link with clear active/inactive states."""
    return rx.link(
        label,
        href=f"/{route}",
        style={
            "padding": "6px 12px",
            "borderRadius": "6px",
            "color": "#FFFFFF" if active else TEXT_PRIMARY,
            "textDecoration": "none",
            "fontWeight": "600" if active else "500",
            "fontSize": "0.88rem",
            "background": TEAL_SOLID if active else "transparent",
            "whiteSpace": "nowrap",
            "_hover": {"background": TEAL_HOVER if active else "#DCE7D8"},
        },
    )


def app_header(active: str = "") -> rx.Component:
    """Sticky app header — in normal flow so it never covers page content."""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.text(
                    "Phrasia.",
                    font_size="1.3rem",
                    font_weight="bold",
                    color=TEXT_PRIMARY,
                    line_height="1",
                    white_space="nowrap",
                ),
                rx.text(
                    "Words, Refined.",
                    font_size="0.8rem",
                    color=TEXT_MUTED,
                    line_height="1",
                ),
                align="center",
                spacing="2",
            ),
            rx.spacer(),
            rx.hstack(
                *[
                    nav_item(label, route, active=key == active)
                    for label, route, key in NAV_ITEMS
                ],
                gap="4px",
                align="center",
            ),
            width="100%",
            max_width="1400px",
            margin_x="auto",
            padding="12px 24px",
            align="center",
            wrap="wrap",
            gap="8px",
        ),
        width="100%",
        background=BG_CARD,
        border_bottom=f"1px solid {BORDER}",
        position="sticky",
        top="0",
        z_index="100",
        box_shadow="0 1px 4px rgba(27,94,59,0.08)",
    )
