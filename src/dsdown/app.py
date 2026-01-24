"""Main Textual application for dsdown."""

from __future__ import annotations

from textual.app import App

from dsdown.screens.main_screen import MainScreen


class DsdownApp(App):
    """Dynasty Scans download manager TUI application."""

    TITLE = "dsdown - Dynasty Scans Manager"

    CSS = """
    Screen {
        background: $background;
    }
    """

    def on_mount(self) -> None:
        """Set up the application on mount."""
        self.push_screen(MainScreen())
