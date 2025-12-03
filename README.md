# Audiobookify

> Convert EPUB and MOBI/AZW files to high-quality M4B audiobooks using Microsoft Edge's cloud-based text-to-speech.

Forked from [epub2tts-edge](https://github.com/aedocw/epub2tts-edge) with enhanced chapter detection, batch processing, and a terminal UI.

## Features

- **Multi-Format Support** - EPUB, MOBI, AZW, and AZW3 files
- **Enhanced Chapter Detection** - Parses Table of Contents (EPUB2/EPUB3) and HTML headings
- **Batch Processing** - Convert entire folders of ebooks at once
- **Terminal UI** - Interactive interface for easy conversion
- **Smart Resume** - Picks up where it left off if interrupted
- **Chapter Markers** - Proper M4B chapter navigation
- **Cover Art** - Automatically embeds cover images
- **Fast** - Parallel sentence processing for quick conversion

### New in v2.3.0
- **MOBI/AZW Support** - Parse Kindle format ebooks (MOBI, AZW, AZW3)
- **Docker Support** - Containerized deployment with docker-compose
- **Calibre Plugin** - Convert books directly from Calibre library

### New in v2.2.0
- **Audio Normalization** - Consistent volume across chapters (`--normalize`)
- **Silence Trimming** - Remove excessive pauses (`--trim-silence`)
- **Custom Pronunciation** - Dictionary for proper nouns (`--pronunciation`)
- **Multiple Voices** - Different voices for characters (`--voice-mapping`)

### New in v2.1.0
- **Voice Preview** - Listen to voices before converting (`--preview-voice`)
- **Speed/Volume Control** - Adjust speech rate and volume (`--rate`, `--volume`)
- **Chapter Selection** - Convert only specific chapters (`--chapters "1-5"`)
- **Pause/Resume** - Continue interrupted conversions (`--resume`)

> **Note:** EPUB and MOBI/AZW files must be DRM-free

## Quick Start

```bash
# Install (use pipx for isolated environment)
pipx install audiobookify
# Or: pip install audiobookify

# Convert a single EPUB
audiobookify mybook.epub              # Export to text
audiobookify mybook.txt               # Convert to audiobook

# Convert a MOBI/AZW file
audiobookify mybook.mobi              # Export to text
audiobookify mybook.azw3              # Export to text

# Or use the short alias
abfy mybook.epub

# Batch convert a folder
audiobookify /path/to/books --batch

# Launch interactive TUI
audiobookify --tui
```

### Docker

```bash
# Build the image
docker build -t audiobookify .

# Export EPUB to text
docker run -v $(pwd)/books:/books audiobookify /books/mybook.epub

# Convert to audiobook
docker run -v $(pwd)/books:/books audiobookify /books/mybook.txt

# Batch processing
docker run -v $(pwd)/books:/books audiobookify /books --batch

# Using docker-compose
docker-compose build
docker-compose run audiobookify /books/mybook.epub
```

### Calibre Plugin

Convert books directly from your Calibre library:

```bash
# Build the plugin
cd calibre_plugin
./build_plugin.sh

# Install in Calibre:
# 1. Preferences → Plugins → Load plugin from file
# 2. Select audiobookify-calibre.zip
# 3. Restart Calibre
```

See [calibre_plugin/README.md](calibre_plugin/README.md) for detailed instructions.

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
| `p` | Preview voice |
| `q` | Quit |

### Voice Preview & Adjustment (v2.1.0)

```bash
# List available voices
audiobookify --list-voices

# Preview a voice before converting
audiobookify --preview-voice                           # Preview default voice
audiobookify --preview-voice --speaker en-US-JennyNeural  # Preview specific voice

# Adjust speech rate
audiobookify mybook.txt --rate "+20%"   # 20% faster
audiobookify mybook.txt --rate "-10%"   # 10% slower

# Adjust volume
audiobookify mybook.txt --volume "+50%"  # Louder
audiobookify mybook.txt --volume "-25%"  # Quieter

# Combine adjustments
audiobookify mybook.txt --rate "+20%" --volume "-10%"
```

### Chapter Selection (v2.1.0)

```bash
# Convert specific chapters only
audiobookify mybook.txt --chapters "1-5"       # Chapters 1 through 5
audiobookify mybook.txt --chapters "1,3,7"     # Chapters 1, 3, and 7
audiobookify mybook.txt --chapters "5-"        # Chapter 5 to end
audiobookify mybook.txt --chapters "1,3,5-7"   # Mix of single and ranges
```

### Pause/Resume (v2.1.0)

```bash
# Resume an interrupted conversion
audiobookify mybook.txt --resume

# Start fresh (ignore saved progress)
audiobookify mybook.txt --no-resume
```

Conversions automatically save progress and can be resumed after Ctrl+C interruption.

### Audio Normalization (v2.2.0)

```bash
# Normalize volume across chapters
audiobookify mybook.txt --normalize

# Custom target loudness (default: -16 dBFS)
audiobookify mybook.txt --normalize --normalize-target -14.0

# Use RMS method instead of peak
audiobookify mybook.txt --normalize --normalize-method rms
```

### Silence Trimming (v2.2.0)

```bash
# Trim excessive silence
audiobookify mybook.txt --trim-silence

# Custom silence threshold (default: -40 dBFS)
audiobookify mybook.txt --trim-silence --silence-thresh -50

# Maximum silence duration (default: 2000ms)
audiobookify mybook.txt --trim-silence --max-silence 1500
```

### Custom Pronunciation (v2.2.0)

Create a pronunciation dictionary file:

**JSON format (`pronunciation.json`):**
```json
{
  "Hermione": "Her-my-oh-nee",
  "Voldemort": "Vol-de-mor",
  "Nguyen": "Win"
}
```

**Text format (`pronunciation.txt`):**
```
# Comments start with #
Hermione = Her-my-oh-nee
Voldemort = Vol-de-mor
```

```bash
# Use pronunciation dictionary
audiobookify mybook.txt --pronunciation pronunciation.json

# Case-sensitive matching
audiobookify mybook.txt --pronunciation pronunciation.txt --pronunciation-case-sensitive
```

### Multiple Voices (v2.2.0)

Create a voice mapping file (`voices.json`):
```json
{
  "default_voice": "en-US-AndrewNeural",
  "narrator_voice": "en-US-GuyNeural",
  "character_voices": {
    "Harry": "en-GB-RyanNeural",
    "Hermione": "en-GB-SoniaNeural",
    "Dumbledore": "en-GB-ThomasNeural"
  }
}
```

```bash
# Use voice mapping for multi-voice narration
audiobookify mybook.txt --voice-mapping voices.json

# Just set a different narrator voice (non-dialogue)
audiobookify mybook.txt --narrator-voice en-US-GuyNeural
```

The multi-voice processor automatically detects dialogue (quoted text) and attributes speakers.

> **Tip:** See the `examples/` folder for sample pronunciation and voice mapping files you can use as templates.

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
| **v2.1.0 Options** | |
| `--list-voices` | List available voices |
| `--preview-voice` | Preview the selected voice |
| `--rate RATE` | Speech rate (e.g., "+20%", "-10%") |
| `--volume VOL` | Volume adjustment (e.g., "+50%", "-25%") |
| `--chapters RANGE` | Select chapters (e.g., "1-5", "1,3,7") |
| `--resume` | Resume interrupted conversion |
| `--no-resume` | Start fresh, ignore saved progress |
| **v2.2.0 Options** | |
| `--normalize` | Normalize audio volume across chapters |
| `--normalize-target DBFS` | Target loudness (default: -16.0 dBFS) |
| `--normalize-method METHOD` | Normalization method: peak or rms |
| `--trim-silence` | Trim excessive silence from audio |
| `--silence-thresh DBFS` | Silence threshold (default: -40 dBFS) |
| `--max-silence MS` | Max silence duration before trimming (default: 2000) |
| `--pronunciation FILE` | Path to pronunciation dictionary |
| `--pronunciation-case-sensitive` | Case-sensitive pronunciation matching |
| `--voice-mapping FILE` | Path to voice mapping JSON file |
| `--narrator-voice VOICE` | Voice for narration (non-dialogue) |

List available voices: `audiobookify --list-voices` or `edge-tts --list-voices`

## Installation

**Requirements:** Python 3.11+, FFmpeg, espeak-ng

### Quick Install (PyPI)

```bash
# Recommended: use pipx for isolated CLI installation
pipx install audiobookify

# Or with pip in a virtual environment
pip install audiobookify
```

### Platform-Specific Setup

<details>
<summary><b>Linux</b></summary>

```bash
# Install system dependencies
sudo apt install espeak-ng ffmpeg python3-venv pipx

# Option 1: pipx (recommended for CLI tools)
pipx install audiobookify

# Option 2: Virtual environment
git clone https://github.com/loganrooks/audiobookify
cd audiobookify
python3 -m venv .venv
source .venv/bin/activate
pip install ".[tui]"
```
</details>

<details>
<summary><b>macOS</b></summary>

```bash
# Install system dependencies
brew install espeak ffmpeg pipx

# Option 1: pipx (recommended for CLI tools)
pipx install audiobookify

# Option 2: Virtual environment
git clone https://github.com/loganrooks/audiobookify
cd audiobookify
python3 -m venv .venv
source .venv/bin/activate
pip install ".[tui]"
```
</details>

<details>
<summary><b>Windows</b></summary>

1. Install [Python 3.11+](https://www.python.org/downloads/)
2. Install [espeak-ng](https://github.com/espeak-ng/espeak-ng/releases) (x64 msi)
3. Install [FFmpeg](https://github.com/BtbN/FFmpeg-Builds/releases) and add to PATH

```powershell
# Option 1: pipx (recommended)
pip install pipx
pipx install audiobookify

# Option 2: Virtual environment
git clone https://github.com/loganrooks/audiobookify
cd audiobookify
py -m venv .venv
.venv\Scripts\activate
pip install ".[tui]"
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

### Development Install

```bash
git clone https://github.com/loganrooks/audiobookify
cd audiobookify
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"  # Editable install with all dependencies
```

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
