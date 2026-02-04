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

        # Status indicator and formatting
        if status == DownloadStatus.DOWNLOADING.value:
            indicator = "▶"
            status_label = f"[{status}]"
            text = f"{indicator} {chapter.title} {status_label}"
        elif status == DownloadStatus.PENDING.value:
            indicator = "○"
            text = f"{indicator} {chapter.title}"
        elif status == DownloadStatus.COMPLETED.value:
            indicator = "✓"
            text = f"{indicator} {chapter.title} [{status}]"
        elif status == DownloadStatus.FAILED.value:
            indicator = "✗"
            text = f"[bold red]{indicator} {chapter.title} [FAILED][/bold red]"
        else:
            indicator = "?"
            text = f"{indicator} {chapter.title} [{status}]"

        yield Label(text, classes="queue-item-title")


class DownloadQueueWidget(Vertical):
    """Widget displaying the download queue."""

    def __init__(self) -> None:
        super().__init__()
        self._queue: list[DownloadQueueModel] = []
        self._downloading_title: str = ""

    def compose(self) -> ComposeResult:
        """Compose the download queue widget."""
        yield Label("Download Queue (0)", id="queue-header")
        yield ListView(id="queue-listview")
        yield Static("", id="download-progress")
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

    def set_download_progress(
        self, title: str, downloaded: int, total: int
    ) -> None:
        """Update the download progress display.

        Args:
            title: Title of the chapter being downloaded.
            downloaded: Bytes downloaded so far.
            total: Total bytes to download.
        """
        try:
            self._downloading_title = title
            progress_static = self.query_one("#download-progress", Static)

            if total > 0:
                percent = (downloaded / total) * 100
                # Create a simple text progress bar
                bar_width = 20
                filled = int(bar_width * downloaded / total)
                bar = "█" * filled + "░" * (bar_width - filled)
                size_mb = downloaded / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                progress_static.update(
                    f"▶ {title[:30]}{'...' if len(title) > 30 else ''}\n"
                    f"  [{bar}] {percent:.0f}% ({size_mb:.1f}/{total_mb:.1f} MB)"
                )
            else:
                progress_static.update(f"▶ Downloading: {title}")
        except Exception:
            pass

    def clear_download_progress(self) -> None:
        """Clear the download progress display."""
        try:
            self._downloading_title = ""
            progress_static = self.query_one("#download-progress", Static)
            progress_static.update("")
        except Exception:
            pass
