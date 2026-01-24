"""Chapter list widget for displaying unprocessed chapters."""

from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
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
        # Title
        yield Label(self.chapter.title, classes="chapter-title")

        # Authors
        if self.chapter.authors:
            authors_text = f"by {', '.join(self.chapter.authors)}"
            yield Label(authors_text, classes="chapter-authors")

        # Tags
        if self.chapter.tags:
            tags_text = " ".join(f"[{tag}]" for tag in self.chapter.tags)
            yield Label(tags_text, classes="chapter-tags")


class DateHeader(Static):
    """A date header for grouping chapters."""

    def __init__(self, release_date: date | None) -> None:
        if release_date:
            text = release_date.strftime("%B %d, %Y")
        else:
            text = "Unknown Date"
        super().__init__(f"=== {text} ===", classes="date-header")


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

    def update_chapters(self, chapters_by_date: dict[date | None, list[Chapter]]) -> None:
        """Update the displayed chapters.

        Args:
            chapters_by_date: Chapters grouped by release date.
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
                        for chapter in chapters:
                            listview.append(ChapterItem(chapter))
                except Exception:
                    pass
        except Exception:
            pass

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
