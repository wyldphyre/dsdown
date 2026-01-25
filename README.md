# dsdown

A terminal user interface (TUI) for managing and downloading manga chapters from dynasty-scans.com.

## Features

- **Fetch new chapters** from the releases page
- **Follow series** to automatically queue new chapters for download
- **Ignore series** to automatically skip unwanted content
- **Download queue** with rate limiting (8 downloads per 24 hours)
- **ComicInfo.xml metadata** automatically added to downloaded CBZ files
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
  - Chapter number
  - Title
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

## License

MIT
