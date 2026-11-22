"""History page — document and job list."""
from __future__ import annotations

import reflex as rx


class HistoryState(rx.State):
    documents: list[dict] = []
    search_query: str = ""

    def load_documents(self) -> None:
        """Load from Supabase in production; return sample for local dev."""
        self.documents = [
            {
                "id": "1",
                "title": "Sample Document",
                "date": "2026-11-19",
                "status": "completed",
                "provider": "gemini",
                "word_count": 342,
            }
        ]

    def set_search_query(self, query: str) -> None:
        self.search_query = query

    @rx.var
    def filtered_documents(self) -> list[dict]:
        q = self.search_query.lower().strip()
        if not q:
            return self.documents
        return [d for d in self.documents if q in d["title"].lower()]


def history_page() -> rx.Component:
    state = HistoryState

    return rx.container(
        rx.flex(
            rx.text("Phrasia.", font_size="1.4rem", weight="bold", color="#174D3B"),
            rx.spacer(),
            rx.link("Log out", href="/", style={"color": "#174D3B"}),
            padding_x="24px",
            padding_y="16px",
            border_bottom="1px solid #EEF1EC",
            bg="white",
        ),
        rx.vstack(
            rx.text("Document History", font_size="1.5rem", weight="bold", color="#18221F"),
            rx.input(
                placeholder="Search documents…",
                value=state.search_query,
                on_change=state.set_search_query,
                size="3",
                width="400px",
                margin_y="16px",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Title"),
                        rx.table.column_header_cell("Date"),
                        rx.table.column_header_cell("Status"),
                        rx.table.column_header_cell("Provider"),
                        rx.table.column_header_cell("Words"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        state.filtered_documents,
                        lambda doc: rx.table.row(
                            rx.table.cell(doc["title"]),
                            rx.table.cell(doc["date"]),
                            rx.table.cell(
                                rx.badge(
                                    doc["status"],
                                    color_scheme=rx.cond(doc["status"] == "completed", "green", "gray"),
                                    size="1",
                                )
                            ),
                            rx.table.cell(doc["provider"]),
                            rx.table.cell(str(doc["word_count"])),
                        ),
                    ),
                ),
                width="100%",
                margin_top="16px",
            ),
            align="start",
            padding="24px",
            width="100%",
            max_width="1200px",
        ),
        margin_top="64px",
    )