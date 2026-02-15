# dsdown

A terminal user interface (TUI) for managing and downloading manga chapters from dynasty-scans.com.

## Features

- **Tabbed interface** with Unprocessed, Followed, and Ignored tabs
- **Fetch new chapters** from the releases page
- **Follow series** to automatically queue new chapters for download
- **Ignore series** to automatically skip unwanted content
- **Download queue** with rate limiting (8 downloads per 24 hours)
- **ComicInfo.xml metadata** automatically added to downloaded CBZ files
- **Volume detection** from series pages for proper file naming
- **Archive conversion** - automatically converts RAR/7z to CBZ
- **Configurable filenames** - optionally exclude series name from downloads
- **Keyboard-driven interface** for efficient workflow

## Installation

```bash
pip install -e .
```

## Usage

```bash
dsdown
```

### Keybindings

| Key | Action |
|-----|--------|
| `f` | Fetch new chapters from releases page |
| `w` | Follow series of selected chapter |
| `i` | Ignore series of selected chapter |
| `u` | Unfollow a followed series |
| `p` | Mark chapter as processed (skip) |
| `q` | Queue chapter for download |
| `s` | Start processing download queue |
| `o` | Open chapter in browser |
| `Enter` | Edit followed series / Unignore ignored series |
| `?` | Help |
| `Escape` | Quit |

## Configuration

Configuration and data are stored in `~/.config/dsdown/`:
- `config.json` - Application settings
- `dsdown.db` - SQLite database

## Downloaded Files

- Files are saved as CBZ archives
- ComicInfo.xml metadata is automatically embedded with:
  - Series name
  - Volume number
  - Chapter number
  - Title/subtitle
  - Authors
  - Tags
  - Release date
  - Page count
  - Manga reading direction

## Development

```bash
pip install -e ".[dev]"
ruff check src/
```

### Running Tests

```bash
# Run all offline tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_releases_parser.py

# Run live smoke tests against the real website (to check if scraping is broken)
pytest -m live
```

## License

MIT
