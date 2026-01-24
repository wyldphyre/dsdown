"""Download queue widget."""

from __future__ import annotations

from collections.abc import Sequence

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ListItem, ListView, Static

from dsdown.models.download import DownloadQueue as DownloadQueueModel
from dsdown.models.download import DownloadStatus


class QueueItem(ListItem):
    """A single item in the download queue."""

    def __init__(self, entry: DownloadQueueModel) -> None:
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        """Compose the queue item."""
        chapter = self.entry.chapter
        status = self.entry.status

        # Status indicator
        if status == DownloadStatus.DOWNLOADING.value:
            indicator = ">"
        elif status == DownloadStatus.PENDING.value:
            indicator = " "
        elif status == DownloadStatus.COMPLETED.value:
            indicator = "+"
        else:
            indicator = "!"

        status_label = f"[{status}]" if status != DownloadStatus.PENDING.value else ""

        yield Label(f"{indicator} {chapter.title} {status_label}", classes="queue-item-title")


class DownloadQueueWidget(Vertical):
    """Widget displaying the download queue."""

    def __init__(self) -> None:
        super().__init__()
        self._queue: list[DownloadQueueModel] = []

    def compose(self) -> ComposeResult:
        """Compose the download queue widget."""
        yield Label("Download Queue (0)", id="queue-header")
        yield ListView(id="queue-listview")
        yield Static("", id="queue-status")

    def update_queue(
        self,
        queue: Sequence[DownloadQueueModel],
        available_slots: int,
        next_slot_time: str | None = None,
    ) -> None:
        """Update the displayed queue.

        Args:
            queue: The download queue entries.
            available_slots: Number of available download slots.
            next_slot_time: When the next slot becomes available (formatted string).
        """
        try:
            self._queue = list(queue)

            # Use batch_update to prevent intermediate renders
            with self.app.batch_update():
                # Update header
                try:
                    header = self.query_one("#queue-header", Label)
                    header.update(f"Download Queue ({len(self._queue)})")
                except Exception:
                    pass

                # Update list view
                try:
                    listview = self.query_one("#queue-listview", ListView)
                    listview.clear()

                    for entry in self._queue:
                        listview.append(QueueItem(entry))
                except Exception:
                    pass

                # Update status
                try:
                    status = self.query_one("#queue-status", Static)
                    if next_slot_time:
                        status.update(f"Slots: {available_slots}/8 (next at {next_slot_time})")
                    else:
                        status.update(f"Slots: {available_slots}/8 available")
                except Exception:
                    pass
        except Exception:
            pass

    def get_queue_count(self) -> int:
        """Get the number of items in the queue."""
        return len(self._queue)
