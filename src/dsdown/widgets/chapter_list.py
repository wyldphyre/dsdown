"""Chapter list widget for displaying unprocessed chapters."""

from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, ListItem, ListView, Static

from dsdown.models.chapter import Chapter


class ChapterItem(ListItem):
    """A single chapter item in the list."""

    def __init__(self, chapter: Chapter) -> None:
        super().__init__()
        self.chapter = chapter

    def compose(self) -> ComposeResult:
        """Compose the chapter item content."""
        from rich.text import Text

        content = Text()

        # Title (bold)
        content.append(self.chapter.title, style="bold")

        # Authors (dim, indented on new line)
        if self.chapter.authors:
            authors_text = f"by {', '.join(self.chapter.authors)}"
            content.append(f"\n  {authors_text}", style="dim")

        # Tags (cyan, indented on new line)
        if self.chapter.tags:
            tags_text = " ".join(f"[{tag}]" for tag in self.chapter.tags)
            content.append(f"\n  {tags_text}", style="cyan")

        yield Static(content)


class DateHeaderItem(ListItem):
    """A date header item for grouping chapters in the list."""

    def __init__(self, release_date: date | None) -> None:
        super().__init__()
        self.disabled = True
        if release_date:
            self._text = release_date.strftime("%B %d, %Y")
        else:
            self._text = "Unknown Date"

    def compose(self) -> ComposeResult:
        yield Static(f"── {self._text} ──", classes="date-header")


class ChapterList(Vertical):
    """Widget displaying the list of unprocessed chapters."""

    class ChapterSelected(Message):
        """Message sent when a chapter is selected."""

        def __init__(self, chapter: Chapter) -> None:
            super().__init__()
            self.chapter = chapter

    class ChapterHighlighted(Message):
        """Message sent when a chapter is highlighted."""

        def __init__(self, chapter: Chapter) -> None:
            super().__init__()
            self.chapter = chapter

    def __init__(self) -> None:
        super().__init__()
        self._chapters: list[Chapter] = []
        self._chapters_by_date: dict[date | None, list[Chapter]] = {}

    def compose(self) -> ComposeResult:
        """Compose the chapter list."""
        yield Label("Unprocessed Chapters (0)", id="chapter-list-header")
        yield ListView(id="chapter-listview")

    def update_chapters(
        self,
        chapters_by_date: dict[date | None, list[Chapter]],
        restore_index: int | None = None,
    ) -> None:
        """Update the displayed chapters.

        Args:
            chapters_by_date: Chapters grouped by release date.
            restore_index: Optional index to restore highlight to after update.
        """
        try:
            self._chapters_by_date = chapters_by_date
            self._chapters = []

            # Flatten for easy access
            for chapters in chapters_by_date.values():
                self._chapters.extend(chapters)

            # Use batch_update to prevent intermediate renders
            with self.app.batch_update():
                # Update header
                try:
                    header = self.query_one("#chapter-list-header", Label)
                    header.update(f"Unprocessed Chapters ({len(self._chapters)})")
                except Exception:
                    pass

                # Update list view
                try:
                    listview = self.query_one("#chapter-listview", ListView)
                    listview.clear()

                    # Sort dates (most recent first, None at end)
                    sorted_dates = sorted(
                        chapters_by_date.keys(),
                        key=lambda d: (d is None, d if d else date.min),
                        reverse=True,
                    )

                    for release_date in sorted_dates:
                        chapters = chapters_by_date[release_date]
                        # Add date header
                        listview.append(DateHeaderItem(release_date))
                        for chapter in chapters:
                            listview.append(ChapterItem(chapter))
                except Exception:
                    pass

            # Restore highlight if requested (outside batch_update)
            if restore_index is not None:
                self._pending_restore_index = restore_index
                self.set_timer(0.2, self._do_restore_highlight)
        except Exception:
            pass

    def _do_restore_highlight(self) -> None:
        """Restore highlight after refresh."""
        try:
            index = getattr(self, "_pending_restore_index", None)
            if index is None:
                return
            listview = self.query_one("#chapter-listview", ListView)
            child_count = len(listview.children)
            if child_count == 0:
                return
            # Clamp to valid range
            valid_index = min(index, child_count - 1)
            # Skip disabled items (date headers) - search forward first
            while valid_index < child_count:
                item = listview.children[valid_index]
                if isinstance(item, ChapterItem):
                    break
                valid_index += 1
            # If we went past the end, search backwards
            if valid_index >= child_count:
                valid_index = min(index, child_count - 1)
                while valid_index >= 0:
                    item = listview.children[valid_index]
                    if isinstance(item, ChapterItem):
                        break
                    valid_index -= 1
            if valid_index >= 0:
                # Focus first to ensure the listview is active
                listview.focus()
                # Set the index to move the highlight
                listview.index = valid_index
        except Exception as e:
            self.app.notify(f"Restore error: {e}", severity="error", timeout=10)
        finally:
            self._pending_restore_index = None

    def get_selected_chapter(self) -> Chapter | None:
        """Get the currently selected chapter."""
        try:
            listview = self.query_one("#chapter-listview", ListView)
            if listview.highlighted_child is not None:
                if isinstance(listview.highlighted_child, ChapterItem):
                    return listview.highlighted_child.chapter
        except Exception:
            pass
        return None

    def get_highlighted_index(self) -> int | None:
        """Get the index of the currently highlighted chapter."""
        try:
            listview = self.query_one("#chapter-listview", ListView)
            return listview.index
        except Exception:
            return None

    def restore_highlight(self, index: int) -> None:
        """Restore the highlight to a specific index after a delay.

        Args:
            index: The index to highlight. Will be clamped to valid range.
        """
        def do_restore() -> None:
            try:
                listview = self.query_one("#chapter-listview", ListView)
                child_count = len(listview.children)
                if child_count == 0:
                    return
                # Clamp to valid range
                valid_index = min(index, child_count - 1)
                # Skip disabled items (date headers) - search forward first
                while valid_index < child_count:
                    item = listview.children[valid_index]
                    if isinstance(item, ChapterItem):
                        break
                    valid_index += 1
                # If we went past the end, search backwards
                if valid_index >= child_count:
                    valid_index = min(index, child_count - 1)
                    while valid_index >= 0:
                        item = listview.children[valid_index]
                        if isinstance(item, ChapterItem):
                            break
                        valid_index -= 1
                if valid_index >= 0:
                    listview.index = valid_index
                    listview.focus()
            except Exception:
                pass

        self.set_timer(0.15, do_restore)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle chapter selection."""
        try:
            if isinstance(event.item, ChapterItem):
                self.post_message(self.ChapterSelected(event.item.chapter))
        except Exception:
            pass

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle chapter highlight."""
        try:
            if event.item is not None and isinstance(event.item, ChapterItem):
                self.post_message(self.ChapterHighlighted(event.item.chapter))
        except Exception:
            pass
