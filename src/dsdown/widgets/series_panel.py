"""Series panel widget for displaying followed and ignored series."""

from __future__ import annotations

from collections.abc import Sequence

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, ListItem, ListView

from dsdown.models.series import Series


class SeriesItem(ListItem):
    """A single series item in the list."""

    def __init__(self, series: Series) -> None:
        super().__init__()
        self.series = series

    def compose(self) -> ComposeResult:
        """Compose the series item."""
        yield Label(f"* {self.series.name}", classes="series-name")


class SeriesPanel(Vertical):
    """Widget displaying followed and ignored series."""

    class SeriesSelected(Message):
        """Message sent when a series is selected."""

        def __init__(self, series: Series) -> None:
            super().__init__()
            self.series = series

    def __init__(self) -> None:
        super().__init__()
        self._followed: list[Series] = []
        self._ignored: list[Series] = []

    def compose(self) -> ComposeResult:
        """Compose the series panel."""
        yield Label("Followed Series (0)", id="followed-header")
        yield ListView(id="followed-listview")
        yield Label("Ignored Series (0)", id="ignored-header")
        yield ListView(id="ignored-listview")

    def update_series(
        self,
        followed: Sequence[Series],
        ignored: Sequence[Series],
        restore_followed_id: int | None = None,
    ) -> None:
        """Update the displayed series.

        Args:
            followed: List of followed series.
            ignored: List of ignored series.
            restore_followed_id: Optional series ID to restore highlight to in followed list.
        """
        try:
            self._followed = list(followed)
            self._ignored = list(ignored)
            restore_index = None

            # Use batch_update to prevent intermediate renders
            with self.app.batch_update():
                # Update followed
                try:
                    followed_header = self.query_one("#followed-header", Label)
                    followed_header.update(f"Followed Series ({len(self._followed)})")

                    followed_list = self.query_one("#followed-listview", ListView)
                    followed_list.clear()
                    for i, series in enumerate(self._followed):
                        followed_list.append(SeriesItem(series))
                        if restore_followed_id and series.id == restore_followed_id:
                            restore_index = i
                except Exception:
                    pass

                # Update ignored
                try:
                    ignored_header = self.query_one("#ignored-header", Label)
                    ignored_header.update(f"Ignored Series ({len(self._ignored)})")

                    ignored_list = self.query_one("#ignored-listview", ListView)
                    ignored_list.clear()
                    for series in self._ignored:
                        ignored_list.append(SeriesItem(series))
                except Exception:
                    pass

            # Restore highlight after batch_update completes
            if restore_index is not None:
                def do_restore() -> None:
                    try:
                        lv = self.query_one("#followed-listview", ListView)
                        lv.index = restore_index
                        lv.focus()
                    except Exception:
                        pass
                self.set_timer(0.1, do_restore)
        except Exception:
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle series selection."""
        try:
            if isinstance(event.item, SeriesItem):
                self.post_message(self.SeriesSelected(event.item.series))
        except Exception:
            pass
