"""Dialog for following a series and setting download path."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Static


@dataclass
class FollowDialogResult:
    """Result from the follow dialog."""

    path: Path
    include_series_in_filename: bool


class FollowDialog(ModalScreen[Optional[FollowDialogResult]]):
    """Modal dialog for setting a download path when following a series."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    FollowDialog {
        align: center middle;
    }

    FollowDialog > Vertical {
        width: 60;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    FollowDialog #title {
        text-align: center;
        width: 100%;
        text-style: bold;
    }

    FollowDialog #series-name {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    FollowDialog Input {
        width: 100%;
        margin-bottom: 1;
    }

    FollowDialog #checkbox-row {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    FollowDialog #buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    FollowDialog Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        series_name: str,
        existing_path: Path | None = None,
        include_series_in_filename: bool = True,
    ) -> None:
        super().__init__()
        self.series_name = series_name
        self._existing_path = existing_path
        self._include_series_in_filename = include_series_in_filename
        self._is_edit_mode = existing_path is not None
        if existing_path:
            self._default_path = existing_path
        else:
            self._default_path = Path.home() / "Downloads" / "dsdown" / self._sanitize_name(series_name)

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a series name for use as a directory name."""
        # Remove or replace characters that are problematic in filenames
        invalid_chars = '<>:"/\\|?*'
        result = name
        for char in invalid_chars:
            result = result.replace(char, "_")
        return result.strip()

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        title = "Edit Download Path" if self._is_edit_mode else "Follow Series"
        button_text = "Save" if self._is_edit_mode else "Follow"

        with Vertical():
            yield Label(title, id="title")
            yield Label(self.series_name, id="series-name")
            yield Static("Download path:")
            yield Input(
                value=str(self._default_path),
                placeholder="Enter download path...",
                id="path-input",
            )
            with Horizontal(id="checkbox-row"):
                yield Checkbox(
                    "Include series name in filename",
                    value=self._include_series_in_filename,
                    id="include-series-checkbox",
                )
            with Vertical(id="buttons"):
                yield Button(button_text, variant="primary", id="follow-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def _clean_path(self, value: str) -> Path:
        """Clean a path string by removing surrounding quotes."""
        cleaned = value.strip()
        # Remove surrounding single or double quotes
        if (cleaned.startswith("'") and cleaned.endswith("'")) or \
           (cleaned.startswith('"') and cleaned.endswith('"')):
            cleaned = cleaned[1:-1]
        return Path(cleaned)

    def _get_result(self) -> FollowDialogResult:
        """Get the current dialog result."""
        path_input = self.query_one("#path-input", Input)
        checkbox = self.query_one("#include-series-checkbox", Checkbox)
        return FollowDialogResult(
            path=self._clean_path(path_input.value),
            include_series_in_filename=checkbox.value,
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "follow-btn":
            self.dismiss(self._get_result())
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in input."""
        self.dismiss(self._get_result())

    def action_cancel(self) -> None:
        """Cancel the dialog."""
        self.dismiss(None)
