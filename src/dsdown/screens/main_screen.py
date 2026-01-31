"""Main screen for the dsdown application."""

from __future__ import annotations

import webbrowser
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static, TabbedContent, TabPane

from dsdown.config import DYNASTY_BASE_URL
from dsdown.models.chapter import Chapter
from dsdown.models.database import get_session, init_db
from dsdown.models.series import Series
from dsdown.scraper.client import download_image, fetch_series_page
from dsdown.scraper.series_parser import SeriesPageParser
from dsdown.screens.confirm_dialog import ConfirmDialog
from dsdown.screens.follow_dialog import FollowDialog, FollowDialogResult
from dsdown.services.chapter_service import ChapterService
from dsdown.services.download_service import DownloadService
from dsdown.services.series_service import SeriesService
from dsdown.widgets.chapter_list import ChapterList
from dsdown.widgets.download_queue import DownloadQueueWidget
from dsdown.widgets.status_bar import StatusBar


def _write_series_metadata_files(
    folder: Path,
    cover_image: bytes | None,
    description: str | None,
    tags: list[str] | None,
) -> None:
    """Write series metadata files to the series folder.

    Args:
        folder: The series download folder.
        cover_image: Cover image data (written as cover.jpg).
        description: Series description (written as description.txt).
        tags: List of tags (written as tags.txt).
    """
    folder.mkdir(parents=True, exist_ok=True)

    if cover_image:
        cover_path = folder / "cover.jpg"
        cover_path.write_bytes(cover_image)

    if description:
        desc_path = folder / "description.txt"
        desc_path.write_text(description, encoding="utf-8")

    if tags:
        tags_path = folder / "tags.txt"
        tags_path.write_text("\n".join(tags), encoding="utf-8")


class SeriesListItem(ListItem):
    """A series item for the followed/ignored lists."""

    def __init__(self, series: Series) -> None:
        super().__init__()
        self.series = series

    def compose(self) -> ComposeResult:
        yield Label(f"• {self.series.name}", classes="series-name")


class MainScreen(Screen):
    """Main application screen."""

    BINDINGS = [
        ("f", "fetch", "Fetch"),
        ("i", "ignore", "Ignore"),
        ("w", "follow", "Follow"),
        ("u", "unfollow", "Unfollow"),
        ("r", "refresh_metadata", "Refresh"),
        ("o", "open", "Open"),
        ("p", "process", "Process"),
        ("q", "queue", "Queue"),
        ("s", "start_queue", "Start Queue"),
        ("?", "help", "Help"),
        ("escape", "quit", "Quit"),
    ]

    CSS = """
    MainScreen {
        layout: grid;
        grid-size: 2 2;
        grid-columns: 2fr 1fr;
        grid-rows: 1fr 3;
    }

    #left-panel {
        row-span: 1;
        height: 100%;
        min-height: 10;
    }

    #right-panel {
        row-span: 1;
        border: solid $secondary;
        height: 100%;
        min-height: 10;
    }

    #status-panel {
        column-span: 2;
        height: 3;
        border-top: solid $primary;
        padding: 0 1;
    }

    TabbedContent {
        height: 100%;
    }

    ContentSwitcher {
        height: 1fr;
    }

    TabPane {
        height: 100%;
        padding: 0;
    }

    TabPane > ListView {
        height: 100%;
    }

    ChapterList {
        height: 100%;
        min-height: 5;
    }

    #chapter-listview {
        height: 1fr;
        min-height: 3;
    }

    ChapterItem {
        height: auto;
    }

    ChapterItem > Static {
        width: 100%;
    }

    DateHeaderItem {
        height: auto;
        background: $surface;
    }

    .chapter-title {
        text-style: bold;
    }

    .chapter-authors {
        color: $text-muted;
        padding-left: 2;
    }

    .chapter-tags {
        color: $success;
        padding-left: 2;
    }

    .date-header {
        text-align: center;
        text-style: bold;
    }

    DownloadQueueWidget {
        height: 100%;
    }

    #queue-header {
        text-style: bold;
        padding: 0 1;
        background: $accent;
        height: 1;
    }

    #queue-listview {
        height: 1fr;
        min-height: 1;
    }

    #download-progress {
        padding: 0 1;
        color: $success;
        height: auto;
    }

    #queue-status {
        padding: 0 1;
        color: $text-muted;
        height: 1;
    }

    #followed-listview {
        height: 1fr;
        min-height: 3;
    }

    #ignored-listview {
        height: 1fr;
        min-height: 3;
    }

    .series-name {
        padding-left: 1;
    }

    #series-detail-panel {
        height: auto;
        max-height: 12;
        border-top: solid $primary;
        padding: 1;
        color: $text-muted;
        display: none;
    }

    #series-detail-panel.has-content {
        display: block;
    }

    StatusBar {
        height: 1;
        padding: 0 1;
    }

    #keybindings {
        width: 1fr;
    }

    #status-message {
        width: auto;
        color: $warning;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._session = None
        self._chapter_service = None
        self._series_service = None
        self._download_service = None
        self._selected_chapter: Chapter | None = None

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Check if an action should be shown/enabled."""
        if action == "unfollow":
            # Only show unfollow when followed series list has focus
            return self._get_highlighted_followed_series() is not None
        return True

    def compose(self) -> ComposeResult:
        """Compose the main screen."""
        yield Header()

        with Container(id="left-panel"):
            with TabbedContent():
                with TabPane("Unprocessed", id="unprocessed-tab"):
                    yield ChapterList()
                with TabPane("Followed", id="followed-tab"):
                    yield ListView(id="followed-listview")
                    yield Static("", id="series-detail-panel")
                with TabPane("Ignored", id="ignored-tab"):
                    yield ListView(id="ignored-listview")

        with Vertical(id="right-panel"):
            yield DownloadQueueWidget()

        with Container(id="status-panel"):
            yield StatusBar()

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen on mount."""
        # Initialize database
        init_db()
        self._session = get_session()
        self._chapter_service = ChapterService(self._session)
        self._series_service = SeriesService(self._session)
        self._download_service = DownloadService(self._session)

        # Load initial data with a small delay to ensure widgets are ready
        self.set_timer(0.1, self._refresh_all)

    def _refresh_all(self) -> None:
        """Refresh all widgets with current data."""
        # Use call_later to defer refresh to next frame to avoid render issues
        self.call_later(self._do_refresh_all)

    def _do_refresh_all(self) -> None:
        """Actually perform the refresh."""
        try:
            # Use batch_update to prevent intermediate renders during refresh
            with self.app.batch_update():
                self._refresh_chapters()
                self._refresh_queue()
                self._refresh_series()
            # Force tab bar to refresh after batch_update completes
            self._refresh_tab_labels()
        except Exception as e:
            self._set_status(f"Refresh error: {e}")

    def _refresh_chapters(self, restore_index: int | None = None) -> None:
        """Refresh the chapter list.

        Args:
            restore_index: Optional index to restore highlight to after update.
        """
        try:
            chapters_by_date = self._chapter_service.get_chapters_by_date()
            total_count = sum(len(chapters) for chapters in chapters_by_date.values())
            try:
                chapter_list = self.query_one(ChapterList)
                chapter_list.update_chapters(chapters_by_date, restore_index)

                # Update the tab label with count
                self._update_tab_label("unprocessed-tab", f"Unprocessed ({total_count})")
            except Exception:
                pass
        except Exception:
            pass  # Silently ignore refresh errors

    def _refresh_queue(self) -> None:
        """Refresh the download queue."""
        try:
            queue = self._download_service.get_queue()
            available = self._download_service.get_available_slots()
            next_time = self._download_service.get_next_slot_time()
            next_time_str = next_time.strftime("%H:%M") if next_time else None

            queue_widget = self.query_one(DownloadQueueWidget)
            queue_widget.update_queue(queue, available, next_time_str)
        except Exception:
            pass  # Silently ignore refresh errors

    def _refresh_series(self, restore_followed_id: int | None = None) -> None:
        """Refresh the followed and ignored series lists.

        Args:
            restore_followed_id: Optional series ID to restore highlight to.
        """
        try:
            followed = self._series_service.get_followed_series()
            ignored = self._series_service.get_ignored_series()
            restore_index = None

            # Update followed list
            try:
                followed_list = self.query_one("#followed-listview", ListView)
                followed_list.clear()
                for i, series in enumerate(followed):
                    followed_list.append(SeriesListItem(series))
                    if restore_followed_id and series.id == restore_followed_id:
                        restore_index = i

                # Update the tab label with count
                self._update_tab_label("followed-tab", f"Followed ({len(followed)})")

                # Restore selection or select first item
                if restore_index is not None:
                    followed_list.index = restore_index
                elif followed:
                    followed_list.index = 0

                # Defer detail panel update to allow ListView to settle
                self.call_later(self._update_series_detail_panel)
            except Exception:
                pass

            # Update ignored list
            try:
                ignored_list = self.query_one("#ignored-listview", ListView)
                ignored_list.clear()
                for series in ignored:
                    ignored_list.append(SeriesListItem(series))

                # Update the tab label with count
                self._update_tab_label("ignored-tab", f"Ignored ({len(ignored)})")
            except Exception:
                pass

            # Restore highlight after update
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
            pass  # Silently ignore refresh errors

    def _set_status(self, message: str) -> None:
        """Set the status bar message."""
        status_bar = self.query_one(StatusBar)
        status_bar.set_message(message)

    def _update_tab_label(self, pane_id: str, label: str) -> None:
        """Update a tab's label by pane ID.

        Args:
            pane_id: The ID of the TabPane (e.g., "followed-tab").
            label: The new label text.
        """
        try:
            tabbed = self.query_one(TabbedContent)
            tab = tabbed.get_tab(pane_id)
            tab.label = label
        except Exception:
            pass

    def _refresh_tab_labels(self) -> None:
        """Force refresh of the tab bar to show updated labels."""
        try:
            tabbed = self.query_one(TabbedContent)
            # Refresh the Tabs container (the tab bar)
            tabs = tabbed.query_one("Tabs")
            tabs.refresh()
        except Exception:
            pass

    def _get_highlighted_followed_series(self) -> Series | None:
        """Get the currently highlighted series in the followed list.

        Returns:
            The highlighted Series, or None if nothing is highlighted or
            the followed list doesn't have focus.
        """
        try:
            followed_list = self.query_one("#followed-listview", ListView)
            if not followed_list.has_focus:
                return None
            if followed_list.index is None:
                return None
            item = followed_list.highlighted_child
            if isinstance(item, SeriesListItem):
                return item.series
        except Exception:
            pass
        return None

    def _get_highlighted_ignored_series(self) -> Series | None:
        """Get the currently highlighted series in the ignored list.

        Returns:
            The highlighted Series, or None if nothing is highlighted or
            the ignored list doesn't have focus.
        """
        try:
            ignored_list = self.query_one("#ignored-listview", ListView)
            if not ignored_list.has_focus:
                return None
            if ignored_list.index is None:
                return None
            item = ignored_list.highlighted_child
            if isinstance(item, SeriesListItem):
                return item.series
        except Exception:
            pass
        return None

    def _update_series_detail_panel(self) -> None:
        """Update the series detail panel with the currently selected followed series."""
        try:
            panel = self.query_one("#series-detail-panel", Static)

            # Get currently highlighted series (without focus check)
            followed_list = self.query_one("#followed-listview", ListView)
            series = None
            if followed_list.index is not None:
                item = followed_list.highlighted_child
                if isinstance(item, SeriesListItem):
                    series = item.series

            if series and (series.description or series.tags):
                # Build content with description first, then tags in a different color
                parts = []
                if series.description:
                    parts.append(series.description)
                if series.tags:
                    tags_str = ", ".join(series.tags)
                    parts.append(f"[bold cyan]Tags:[/bold cyan] [cyan]{tags_str}[/cyan]")
                panel.update("\n".join(parts))
                panel.add_class("has-content")
            else:
                panel.update("")
                panel.remove_class("has-content")
        except Exception:
            pass

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle list view highlight changes."""
        if event.list_view.id == "followed-listview":
            self._update_series_detail_panel()
        self.refresh_bindings()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Handle tab changes."""
        if event.pane.id == "followed-tab":
            self._update_series_detail_panel()

    def on_chapter_list_chapter_highlighted(self, event: ChapterList.ChapterHighlighted) -> None:
        """Handle chapter highlight."""
        self._selected_chapter = event.chapter

    def on_descendant_focus(self, event) -> None:
        """Handle focus changes to refresh conditional bindings."""
        self.refresh_bindings()

    def on_chapter_list_chapter_selected(self, event: ChapterList.ChapterSelected) -> None:
        """Handle chapter selection (Enter key)."""
        self._selected_chapter = event.chapter
        # Open the chapter in browser on selection
        self._open_chapter(event.chapter)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection in list views (followed/ignored series)."""
        if not isinstance(event.item, SeriesListItem):
            return

        series = event.item.series
        series_id = series.id
        series_name = series.name

        # Check which list this is from
        if event.list_view.id == "ignored-listview":
            # Confirm before unignoring
            def handle_unignore_confirm(confirmed: bool) -> None:
                if not confirmed:
                    self._set_status("Unignore cancelled")
                    return
                try:
                    fresh_series = self._series_service.get_series_by_id(series_id)
                    if fresh_series:
                        self._series_service.unfollow_series(fresh_series)
                        self._set_status(f"Unignored: {series_name}")
                        self._refresh_all()
                except Exception as e:
                    self._set_status(f"Error: {e}")

            self.app.push_screen(
                ConfirmDialog("Unignore Series", f"Stop ignoring '{series_name}'?"),
                handle_unignore_confirm,
            )
            return

        if event.list_view.id == "followed-listview":
            # Edit followed series settings
            existing_path = Path(series.download_path) if series.download_path else None
            include_series = series.include_series_in_filename

            def handle_edit_result(result: FollowDialogResult | None) -> None:
                """Handle the result from the edit dialog."""
                try:
                    if result is None:
                        self._set_status("Edit cancelled")
                        # Still restore selection on cancel
                        self._refresh_series(series_id)
                        return

                    # Re-fetch the series from the database
                    fresh_series = self._series_service.get_series_by_id(series_id)
                    if not fresh_series:
                        self._set_status("Series not found")
                        return

                    # Update the settings
                    fresh_series.download_path = str(result.path)
                    fresh_series.include_series_in_filename = result.include_series_in_filename
                    self._series_service.session.commit()

                    self._set_status(f"Updated settings for: {series_name}")
                    self._refresh_series(series_id)
                except Exception as e:
                    self._set_status(f"Error: {e}")

            # Show dialog with existing settings
            self.app.push_screen(
                FollowDialog(series_name, existing_path, include_series),
                handle_edit_result,
            )

    def _get_selected_chapter(self) -> Chapter | None:
        """Get the currently selected chapter, refreshed from the database."""
        try:
            chapter_list = self.query_one(ChapterList)
            chapter = chapter_list.get_selected_chapter()
            if chapter is None:
                return None
            # Re-query from database to get a fresh, session-attached object
            # This prevents DetachedInstanceError when accessing relationships
            return self._chapter_service.get_chapter_by_id(chapter.id)
        except Exception:
            return None

    async def action_fetch(self) -> None:
        """Fetch new chapters from the website."""
        self._set_status("Fetching new chapters...")

        def progress(msg: str, current: int, total: int | None) -> None:
            self._set_status(msg)

        try:
            result = await self._chapter_service.fetch_new_chapters(progress)
            # Build summary message
            parts = [f"Found {result.total}"]
            if result.queued:
                parts.append(f"queued {result.queued}")
            if result.ignored:
                parts.append(f"ignored {result.ignored}")
            if result.new:
                parts.append(f"new {result.new}")
            self._set_status(", ".join(parts))
            self._refresh_all()
        except Exception as e:
            self._set_status(f"Error fetching chapters: {e}")

    def action_ignore(self) -> None:
        """Ignore the series of the selected chapter."""
        try:
            chapter_list = self.query_one(ChapterList)
            current_index = chapter_list.get_highlighted_index()

            chapter = self._get_selected_chapter()
            if not chapter:
                self._set_status("No chapter selected")
                return

            if not chapter.series:
                self._set_status("Chapter has no series")
                return

            series_name = chapter.series.name
            series_id = chapter.series_id

            # Re-fetch the series from the database to ensure it's attached to the session
            series = self._series_service.get_series_by_id(series_id)
            if not series:
                self._set_status("Series not found")
                return

            self._series_service.ignore_series(series)

            # Mark all unprocessed chapters of this series as processed
            for ch in self._chapter_service.get_unprocessed_chapters():
                if ch.series_id == series_id:
                    self._chapter_service.mark_processed(ch)

            self._set_status(f"Ignored series: {series_name}")

            # Refresh with restored selection
            self._refresh_chapters(current_index)
            self._refresh_queue()
            self._refresh_series()
        except Exception as e:
            self._set_status(f"Error: {e}")

    def action_follow(self) -> None:
        """Follow the series of the selected chapter."""
        try:
            chapter_list = self.query_one(ChapterList)
            current_index = chapter_list.get_highlighted_index()

            chapter = self._get_selected_chapter()
            if not chapter:
                self._set_status("No chapter selected")
                return

            if not chapter.series:
                self._set_status("Chapter has no series")
                return

            series_name = chapter.series.name
            series_id = chapter.series_id
            series_url = chapter.series.url

            async def do_follow(result: FollowDialogResult) -> None:
                """Perform the follow operation with metadata fetch."""
                try:
                    # Re-fetch the series from the database
                    series = self._series_service.get_series_by_id(series_id)
                    if not series:
                        self._set_status("Series not found")
                        return

                    # Fetch series page for metadata
                    description = None
                    cover_image = None
                    tags = None
                    try:
                        self._set_status(f"Fetching metadata for {series_name}...")
                        html = await fetch_series_page(series_url)
                        parser = SeriesPageParser(html)
                        description = parser.get_description()
                        tags = parser.get_tags()
                        cover_image_url = parser.get_cover_image_url()
                        # Download the cover image if available
                        if cover_image_url:
                            try:
                                cover_image = await download_image(cover_image_url)
                            except Exception:
                                pass  # Continue without cover if download fails
                    except Exception:
                        pass  # Continue without metadata if fetch fails

                    # Follow the series with metadata
                    self._series_service.follow_series(
                        series,
                        result.path,
                        result.include_series_in_filename,
                        description,
                        cover_image,
                        tags,
                    )

                    # Write metadata files to series folder
                    _write_series_metadata_files(result.path, cover_image, description, tags)

                    # Queue all unprocessed chapters of this series
                    for ch in self._chapter_service.get_unprocessed_chapters():
                        if ch.series_id == series_id:
                            self._download_service.add_to_queue(ch)
                            self._chapter_service.mark_processed(ch)

                    self._set_status(f"Following series: {series_name}")

                    # Refresh with restored selection
                    self._refresh_chapters(current_index)
                    self._refresh_queue()
                    self._refresh_series()
                except Exception as e:
                    self._set_status(f"Error: {e}")

            def handle_follow_result(result: FollowDialogResult | None) -> None:
                """Handle the result from the follow dialog."""
                if result is None:
                    self._set_status("Follow cancelled")
                    return
                # Run the async follow operation
                self.app.call_later(lambda: self.run_worker(do_follow(result)))

            # Show dialog with callback
            self.app.push_screen(FollowDialog(series_name), handle_follow_result)
        except Exception as e:
            self._set_status(f"Error: {e}")

    def action_unfollow(self) -> None:
        """Unfollow the currently highlighted followed series."""
        try:
            series = self._get_highlighted_followed_series()
            if not series:
                self._set_status("No followed series selected")
                return

            series_id = series.id
            series_name = series.name

            def handle_unfollow_confirm(confirmed: bool) -> None:
                if not confirmed:
                    self._set_status("Unfollow cancelled")
                    return
                try:
                    fresh_series = self._series_service.get_series_by_id(series_id)
                    if fresh_series:
                        self._series_service.unfollow_series(fresh_series)
                        self._set_status(f"Unfollowed: {series_name}")
                        self._refresh_all()
                except Exception as e:
                    self._set_status(f"Error: {e}")

            self.app.push_screen(
                ConfirmDialog("Unfollow Series", f"Stop following '{series_name}'?"),
                handle_unfollow_confirm,
            )
        except Exception as e:
            self._set_status(f"Error: {e}")

    async def action_refresh_metadata(self) -> None:
        """Refresh metadata for the selected followed series."""
        try:
            series = self._get_highlighted_followed_series()
            if not series:
                self._set_status("No followed series selected")
                return

            series_id = series.id
            series_name = series.name
            series_url = series.url

            self._set_status(f"Fetching metadata for {series_name}...")

            try:
                html = await fetch_series_page(series_url)
                parser = SeriesPageParser(html)
                description = parser.get_description()
                tags = parser.get_tags()
                cover_image_url = parser.get_cover_image_url()

                # Download the cover image if available
                cover_image = None
                if cover_image_url:
                    try:
                        cover_image = await download_image(cover_image_url)
                    except Exception:
                        pass  # Continue without cover if download fails

                # Re-fetch series to ensure it's attached to the session
                fresh_series = self._series_service.get_series_by_id(series_id)
                if not fresh_series:
                    self._set_status("Series not found")
                    return

                # Update metadata
                self._series_service.update_series_metadata(
                    fresh_series, description, cover_image, tags
                )

                # Write metadata files to series folder
                if fresh_series.download_path:
                    _write_series_metadata_files(
                        Path(fresh_series.download_path), cover_image, description, tags
                    )

                # Update the series object in the current list item so panel shows new data
                followed_list = self.query_one("#followed-listview", ListView)
                if followed_list.highlighted_child:
                    item = followed_list.highlighted_child
                    if isinstance(item, SeriesListItem):
                        item.series = fresh_series

                # Refresh the detail panel with updated data
                self._update_series_detail_panel()

                self._set_status(f"Updated metadata for: {series_name}")
            except Exception as e:
                self._set_status(f"Error fetching metadata: {e}")
        except Exception as e:
            self._set_status(f"Error: {e}")

    def _open_chapter(self, chapter: Chapter) -> None:
        """Open a chapter in the browser."""
        url = f"{DYNASTY_BASE_URL}{chapter.url}"
        webbrowser.open(url)
        self._set_status(f"Opened: {chapter.title}")

    def action_open(self) -> None:
        """Open the selected chapter in the browser."""
        try:
            chapter = self._get_selected_chapter()
            if not chapter:
                self._set_status("No chapter selected")
                return

            self._open_chapter(chapter)
        except Exception as e:
            self._set_status(f"Error: {e}")

    def action_process(self) -> None:
        """Mark the selected chapter as processed."""
        try:
            chapter_list = self.query_one(ChapterList)
            current_index = chapter_list.get_highlighted_index()

            chapter = self._get_selected_chapter()
            if not chapter:
                self._set_status("No chapter selected")
                return

            title = chapter.title
            self._chapter_service.mark_processed(chapter)
            self._set_status(f"Processed: {title}")

            # Refresh with restored selection
            self._refresh_chapters(current_index)
            self._refresh_queue()
            self._refresh_series()
        except Exception as e:
            self._set_status(f"Error: {e}")

    def action_queue(self) -> None:
        """Add the selected chapter to the download queue."""
        try:
            chapter_list = self.query_one(ChapterList)
            current_index = chapter_list.get_highlighted_index()

            chapter = self._get_selected_chapter()
            if not chapter:
                self._set_status("No chapter selected")
                return

            title = chapter.title
            self._download_service.add_to_queue(chapter)
            self._chapter_service.mark_processed(chapter)
            self._set_status(f"Queued: {title}")

            # Refresh with restored selection
            self._refresh_chapters(current_index)
            self._refresh_queue()
            self._refresh_series()
        except Exception as e:
            self._set_status(f"Error: {e}")

    async def action_start_queue(self) -> None:
        """Start processing the download queue."""
        self._set_status("Starting download queue...")

        def progress(msg: str, current: int, total: int) -> None:
            self._set_status(f"[{current}/{total}] {msg}")
            self._refresh_queue()

        def download_progress(title: str, downloaded: int, total: int) -> None:
            try:
                queue_widget = self.query_one(DownloadQueueWidget)
                queue_widget.set_download_progress(title, downloaded, total)
                self.refresh()
            except Exception:
                pass

        try:
            downloaded = await self._download_service.process_queue(
                progress, download_progress
            )
            # Clear progress display
            try:
                queue_widget = self.query_one(DownloadQueueWidget)
                queue_widget.clear_download_progress()
            except Exception:
                pass
            self._set_status(f"Downloaded {len(downloaded)} chapter(s)")
            self._refresh_all()
        except Exception as e:
            self._set_status(f"Error processing queue: {e}")

    def action_help(self) -> None:
        """Show help information."""
        self._set_status(
            "F=Fetch I=Ignore W=Follow R=Refresh O=Open P=Process Q=Queue S=Start U=Unfollow"
        )

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
