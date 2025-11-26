# Audiobookify

> Convert EPUB files to high-quality M4B audiobooks using Microsoft Edge's cloud-based text-to-speech.

Forked from [epub2tts-edge](https://github.com/aedocw/epub2tts-edge) with enhanced chapter detection, batch processing, and a terminal UI.

## Features

- **Enhanced Chapter Detection** - Parses Table of Contents (EPUB2/EPUB3) and HTML headings
- **Batch Processing** - Convert entire folders of EPUBs at once
- **Terminal UI** - Interactive interface for easy conversion
- **Smart Resume** - Picks up where it left off if interrupted
- **Chapter Markers** - Proper M4B chapter navigation
- **Cover Art** - Automatically embeds cover images
- **Fast** - Parallel sentence processing for quick conversion

> **Note:** EPUB files must be DRM-free

## Quick Start

```bash
# Install
pip install git+https://github.com/loganrooks/audiobookify.git

# Convert a single EPUB
audiobookify mybook.epub              # Export to text
audiobookify mybook.txt               # Convert to audiobook

# Or use the short alias
abfy mybook.epub

# Batch convert a folder
audiobookify /path/to/books --batch

# Launch interactive TUI
audiobookify --tui
```

## Usage

### Single File Conversion

```bash
# Step 1: Export EPUB to text (review/edit chapters)
audiobookify mybook.epub

# Step 2: Convert text to audiobook
audiobookify mybook.txt --cover mybook.png
```

### Batch Processing

```bash
# Process all EPUBs in a folder
audiobookify /path/to/books --batch

# Recursive (include subfolders)
audiobookify /path/to/library --batch --recursive

# Export only (no audio conversion)
audiobookify /path/to/books --batch --export-only

# Custom output directory
audiobookify /path/to/books --batch -o /path/to/audiobooks
```

### Terminal UI

```bash
# Launch TUI
audiobookify /path/to/books --tui

# Or use dedicated command
audiobookify-tui /path/to/books

# Short alias
abfy-tui
```

**Keyboard Shortcuts:**
| Key | Action |
|-----|--------|
| `s` | Start processing |
| `Esc` | Stop |
| `r` | Refresh files |
| `a` | Select all |
| `d` | Deselect all |
| `q` | Quit |

### Chapter Detection Options

```bash
# Detection method
audiobookify mybook.epub --detect toc        # Table of Contents only
audiobookify mybook.epub --detect headings   # HTML headings only
audiobookify mybook.epub --detect combined   # Both (default)
audiobookify mybook.epub --detect auto       # Auto-select best

# Hierarchy display style
audiobookify mybook.epub --hierarchy flat       # Chapter 1
audiobookify mybook.epub --hierarchy numbered   # 1.1 Chapter 1
audiobookify mybook.epub --hierarchy arrow      # Part 1 > Chapter 1
audiobookify mybook.epub --hierarchy breadcrumb # Part 1 / Chapter 1

# Preview chapters without converting
audiobookify mybook.epub --preview

# Limit chapter depth
audiobookify mybook.epub --max-depth 2
```

### All Options

| Option | Description |
|--------|-------------|
| `--speaker VOICE` | TTS voice (default: en-US-AndrewNeural) |
| `--cover IMAGE` | Cover image (jpg/png) |
| `--detect METHOD` | Detection: toc, headings, combined, auto |
| `--hierarchy STYLE` | Display: flat, numbered, arrow, breadcrumb, indented |
| `--max-depth N` | Maximum chapter depth |
| `--preview` | Preview chapters only |
| `--legacy` | Use original detection algorithm |
| `--batch` | Batch processing mode |
| `--recursive` | Scan subfolders |
| `--output-dir DIR` | Output directory |
| `--export-only` | Export to text only |
| `--no-skip` | Don't skip already processed |
| `--tui` | Launch terminal UI |
| `--paragraphpause MS` | Pause between paragraphs (default: 1200) |
| `--sentencepause MS` | Pause between sentences (default: 1200) |

List available voices: `edge-tts --list-voices`

## Installation

**Requirements:** Python 3.11+, FFmpeg, espeak-ng

<details>
<summary><b>Linux</b></summary>

```bash
# Install dependencies
sudo apt install espeak-ng ffmpeg python3-venv

# Clone and install
git clone https://github.com/loganrooks/audiobookify
cd audiobookify
python3 -m venv .venv && source .venv/bin/activate
pip install .
```
</details>

<details>
<summary><b>macOS</b></summary>

```bash
# Install dependencies
brew install espeak pyenv ffmpeg

# Clone and install
git clone https://github.com/loganrooks/audiobookify
cd audiobookify
pyenv install 3.11
pyenv local 3.11
python -m venv .venv && source .venv/bin/activate
pip install .
```
</details>

<details>
<summary><b>Windows</b></summary>

1. Install [Python 3.11](https://www.python.org/downloads/release/python-3117/)
2. Install [espeak-ng](https://github.com/espeak-ng/espeak-ng/releases) (x64 msi)
3. Install [FFmpeg](https://github.com/BtbN/FFmpeg-Builds/releases) and add to PATH

```powershell
git clone https://github.com/loganrooks/audiobookify
cd audiobookify
py -m venv .venv
.venv\scripts\activate
pip install .
```
</details>

<details>
<summary><b>Docker</b></summary>

```bash
docker build . -t audiobookify

# Export EPUB
docker run --rm -v ~/Books:/files audiobookify "/files/mybook.epub"

# Convert to audiobook
docker run --rm -v ~/Books:/files audiobookify "/files/mybook.txt"
```
</details>

## Documentation

- [CLAUDE.md](./CLAUDE.md) - Development context for AI assistants
- [ROADMAP.md](./ROADMAP.md) - Future plans and features
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines

## Credits

**Original Author:** [Christopher Aedo](https://github.com/aedocw) (epub2tts-edge)

**Fork Maintainer:** [loganrooks](https://github.com/loganrooks)

## Contributing

Contributions welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

GPL 3.0
