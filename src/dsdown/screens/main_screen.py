"""Main screen for the dsdown application."""

from __future__ import annotations

import webbrowser
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, ListView, Static

from dsdown.config import DYNASTY_BASE_URL
from dsdown.models.chapter import Chapter
from dsdown.models.database import get_session, init_db
from dsdown.screens.confirm_dialog import ConfirmDialog
from dsdown.screens.follow_dialog import FollowDialog, FollowDialogResult
from dsdown.services.chapter_service import ChapterService
from dsdown.services.download_service import DownloadService
from dsdown.services.series_service import SeriesService
from dsdown.widgets.chapter_list import ChapterList
from dsdown.widgets.download_queue import DownloadQueueWidget
from dsdown.widgets.series_panel import SeriesPanel
from dsdown.widgets.status_bar import StatusBar


class MainScreen(Screen):
    """Main application screen."""

    BINDINGS = [
        ("f", "fetch", "Fetch"),
        ("i", "ignore", "Ignore"),
        ("w", "follow", "Follow"),
        ("u", "unfollow", "Unfollow"),
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
        border: solid $primary;
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

    ChapterList {
        height: 100%;
        min-height: 5;
    }

    #chapter-list-header {
        text-style: bold;
        padding: 0 1;
        background: $accent;
        height: 1;
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
        height: auto;
        max-height: 40%;
        min-height: 4;
        border-bottom: solid $secondary;
    }

    #queue-header {
        text-style: bold;
        padding: 0 1;
        background: $accent;
        height: 1;
    }

    #queue-listview {
        height: auto;
        max-height: 10;
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

    SeriesPanel {
        height: 1fr;
        min-height: 5;
    }

    #followed-header, #ignored-header {
        text-style: bold;
        padding: 0 1;
        background: $accent;
        height: 1;
    }

    #followed-listview, #ignored-listview {
        height: auto;
        max-height: 10;
        min-height: 1;
    }

    .series-name {
        padding-left: 1;
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
            try:
                series_panel = self.query_one(SeriesPanel)
                return series_panel.get_highlighted_followed_series() is not None
            except Exception:
                return False
        return True

    def compose(self) -> ComposeResult:
        """Compose the main screen."""
        yield Header()

        with Container(id="left-panel"):
            yield ChapterList()

        with Vertical(id="right-panel"):
            yield DownloadQueueWidget()
            yield SeriesPanel()

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

        # Load initial data
        self._refresh_all()

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
        except Exception as e:
            self._set_status(f"Refresh error: {e}")

    def _refresh_chapters(self, restore_index: int | None = None) -> None:
        """Refresh the chapter list.

        Args:
            restore_index: Optional index to restore highlight to after update.
        """
        try:
            chapters_by_date = self._chapter_service.get_chapters_by_date()
            try:
                chapter_list = self.query_one(ChapterList)
                chapter_list.update_chapters(chapters_by_date, restore_index)
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
        """Refresh the series panel.

        Args:
            restore_followed_id: Optional series ID to restore highlight to.
        """
        try:
            followed = self._series_service.get_followed_series()
            ignored = self._series_service.get_ignored_series()

            series_panel = self.query_one(SeriesPanel)
            series_panel.update_series(followed, ignored, restore_followed_id)
        except Exception:
            pass  # Silently ignore refresh errors

    def _set_status(self, message: str) -> None:
        """Set the status bar message."""
        status_bar = self.query_one(StatusBar)
        status_bar.set_message(message)

    def on_chapter_list_chapter_highlighted(self, event: ChapterList.ChapterHighlighted) -> None:
        """Handle chapter highlight."""
        self._selected_chapter = event.chapter

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle list view highlight changes to refresh conditional bindings."""
        self.refresh_bindings()

    def on_descendant_focus(self, event) -> None:
        """Handle focus changes to refresh conditional bindings."""
        self.refresh_bindings()

    def on_chapter_list_chapter_selected(self, event: ChapterList.ChapterSelected) -> None:
        """Handle chapter selection (Enter key)."""
        self._selected_chapter = event.chapter
        # Open the chapter in browser on selection
        self._open_chapter(event.chapter)

    def on_series_panel_series_selected(self, event: SeriesPanel.SeriesSelected) -> None:
        """Handle series selection.

        - For followed series: edit download path settings
        - For ignored series: unignore the series
        """
        series = event.series
        series_id = series.id
        series_name = series.name

        if series.is_ignored:
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

        if not series.is_followed:
            return  # Series has no status, nothing to do

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

            def handle_follow_result(result: FollowDialogResult | None) -> None:
                """Handle the result from the follow dialog."""
                try:
                    if result is None:
                        self._set_status("Follow cancelled")
                        return

                    # Re-fetch the series from the database to ensure it's attached to the session
                    series = self._series_service.get_series_by_id(series_id)
                    if not series:
                        self._set_status("Series not found")
                        return

                    # Follow the series
                    self._series_service.follow_series(
                        series,
                        result.path,
                        result.include_series_in_filename,
                    )

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

            # Show dialog with callback
            self.app.push_screen(FollowDialog(series_name), handle_follow_result)
        except Exception as e:
            self._set_status(f"Error: {e}")

    def action_unfollow(self) -> None:
        """Unfollow the currently highlighted followed series."""
        try:
            series_panel = self.query_one(SeriesPanel)
            series = series_panel.get_highlighted_followed_series()
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
            "F=Fetch I=Ignore W=Follow O=Open P=Process Q=Queue S=Start U=Unfollow(followed)"
        )

    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
