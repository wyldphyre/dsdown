# dsdown

A TUI application for managing and downloading manga chapters from dynasty-scans.com.

## Project Structure

```
src/dsdown/
├── app.py              # Main Textual application
├── config.py           # Configuration management (~/.config/dsdown/)
├── models/             # SQLAlchemy models
│   ├── chapter.py      # Chapter model (title, url, tags, authors, release_date)
│   ├── series.py       # Series model (followed/ignored status, download path)
│   ├── download.py     # Download queue and history models
│   └── database.py     # Database initialization
├── screens/            # Textual screens
│   ├── main_screen.py  # Main application screen with keybindings
│   ├── follow_dialog.py    # Dialog for following a series
│   └── confirm_dialog.py   # Generic confirmation dialog
├── widgets/            # Textual widgets
│   ├── chapter_list.py     # Unprocessed chapters list (grouped by date)
│   ├── download_queue.py   # Download queue display
│   └── status_bar.py       # Status bar with keybindings
├── services/           # Business logic
│   ├── chapter_service.py  # Chapter fetching and management
│   ├── series_service.py   # Series follow/ignore/unfollow
│   ├── download_service.py # Download queue processing
│   └── comicinfo.py        # ComicInfo.xml metadata generation
└── scraper/            # Web scraping
    ├── client.py       # HTTP client for dynasty-scans.com
    ├── parser.py       # Releases page parser
    └── chapter_parser.py   # Individual chapter page parser
```

## Key Concepts

- **Chapters**: Individual releases from dynasty-scans.com with title, URL, tags, authors, volume, and release date
- **Series**: A collection of chapters that can be followed (auto-download) or ignored (auto-skip), with optional description and cover image
- **Download Queue**: Rate-limited queue (8 downloads per 24 hours)
- **ComicInfo.xml**: CBZ metadata following the v2.1 spec
- **Tabbed UI**: Main screen uses TabbedContent with Unprocessed/Followed/Ignored tabs

## Keybindings (Main Screen)

- `f` - Fetch new chapters from releases page
- `w` - Follow series of selected chapter (auto-queue future chapters)
- `i` - Ignore series of selected chapter (auto-skip future chapters)
- `u` - Unfollow a followed series (when focused on followed list)
- `r` - Refresh metadata (description/cover) for selected followed series
- `p` - Mark chapter as processed (skip without downloading)
- `q` - Queue chapter for download
- `s` - Start processing download queue
- `o` - Open chapter URL in browser
- `Enter` - On followed series: edit settings; On ignored series: unignore it
- `?` - Help
- `Escape` - Quit

## Database

SQLite database stored at `~/.config/dsdown/dsdown.db` with tables:
- `chapters` - All fetched chapters
- `series` - Series with follow/ignore status and download settings
- `download_queue` - Pending downloads
- `download_history` - Rate limiting tracker

## Dependencies

- **textual** - TUI framework
- **httpx** - Async HTTP client
- **beautifulsoup4/lxml** - HTML parsing
- **sqlalchemy** - ORM

## Running

```bash
pip install -e .
dsdown
```

## Development Notes

- Use `ruff` for linting (configured in pyproject.toml)
- Async operations for network requests
- Textual's `batch_update()` for efficient UI updates
- Downloads save as CBZ with ComicInfo.xml metadata
