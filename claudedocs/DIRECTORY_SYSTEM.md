# Centralized Directory System Design

## Overview

This document outlines the design for a centralized directory management system for Audiobookify. The goal is to provide a consistent, configurable location for all application data, job metadata, intermediate files, and output.

## Current State

**Problems:**
1. **Scattered temp files** - `tempfile.mkdtemp()` creates files in system temp (random locations)
2. **Hardcoded paths** - `~/.audiobookify/jobs/` hardcoded in JobManager
3. **No output configuration** - Final M4B goes to source directory or job folder
4. **No platform awareness** - Same path logic on all platforms
5. **No user configuration** - Can't specify custom locations

**Current temp file locations:**
- `audio_generator.py`: System temp for silence/normalization processing
- `voice_preview.py`: System temp for preview audio
- `job_manager.py`: `~/.audiobookify/jobs/{job_id}/`

## Proposed Design

### Directory Structure (Simplified)

```
~/.audiobookify/                    # Base directory (configurable)
├── config.json                     # Application configuration
├── jobs/                           # Job storage
│   └── {slug}/                     # e.g., derrida_writing-and-difference_a1b2c3
│       ├── job.json                # Job metadata (status, progress, settings)
│       ├── source.txt              # Exported text (intermediate)
│       ├── audio/                  # ALL intermediate audio files
│       │   ├── chapter_001.flac
│       │   ├── chapter_002.flac
│       │   └── ...
│       └── {Author} - {Title}.m4b  # Final output (in job folder by default)
├── cache/                          # Voice previews, etc.
│   └── voice_previews/
└── logs/                           # Application logs (optional)
```

### Job Folder Naming (Slug Template)

Job folders use a human-readable slug format for easy navigation:

**Default template:** `{author_lastname}_{title_slug}_{short_id}`

**Examples:**
- `derrida_writing-and-difference_a1b2c3`
- `dostoevsky_brothers-karamazov_f4e5d6`
- `unknown_my-book_789abc` (when author is missing)

**Slug generation rules:**
1. `author_lastname`: First author's last name, lowercase, alphanumeric only
2. `title_slug`: Book title, lowercase, spaces→hyphens, max 30 chars
3. `short_id`: 6-char unique identifier (timestamp hash)

**Configurable templates:**
```json
{
  "job_slug_template": "{author_lastname}_{title_slug}_{short_id}",
  // Alternatives:
  // "{title_slug}_{short_id}"
  // "{author_lastname}_{short_id}"
  // "{year}_{author_lastname}_{title_slug}"
}
```

### Platform-Specific Defaults

| Platform | Default Base Directory |
|----------|----------------------|
| Linux    | `~/.audiobookify/` |
| macOS    | `~/Library/Application Support/Audiobookify/` |
| Windows  | `%APPDATA%\Audiobookify\` |

### Configuration Priority (highest to lowest)

1. **CLI argument**: `--base-dir /custom/path`
2. **Environment variable**: `AUDIOBOOKIFY_HOME=/custom/path`
3. **Config file**: `config.json` in default location
4. **Platform default**: As shown above

## Implementation

### 1. Slug Generator

```python
# epub2tts_edge/config.py

import re
import hashlib
import time


def extract_author_lastname(author: str | None) -> str:
    """Extract last name from author string.

    Examples:
        "Jacques Derrida" → "derrida"
        "Fyodor Dostoevsky" → "dostoevsky"
        "J.R.R. Tolkien" → "tolkien"
        "Author Name, Second Author" → "name" (first author only)
        None → "unknown"
    """
    if not author:
        return "unknown"

    # Take first author if multiple (comma or "and" separated)
    first_author = re.split(r",|(?:\s+and\s+)", author)[0].strip()

    # Split into parts, take the last word as lastname
    parts = first_author.split()
    if not parts:
        return "unknown"

    lastname = parts[-1]
    # Remove non-alphanumeric, lowercase
    return re.sub(r"[^a-z0-9]", "", lastname.lower()) or "unknown"


def slugify_title(title: str | None, max_length: int = 30) -> str:
    """Convert title to URL-friendly slug.

    Examples:
        "Writing and Difference" → "writing-and-difference"
        "The Brothers Karamazov" → "the-brothers-karamazov"
        "A Very Long Title That Goes On And On" → "a-very-long-title-that-goes" (truncated)
    """
    if not title:
        return "untitled"

    # Lowercase, replace spaces/underscores with hyphens
    slug = title.lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    # Remove non-alphanumeric except hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Trim hyphens from ends
    slug = slug.strip("-")

    # Truncate at word boundary if too long
    if len(slug) > max_length:
        slug = slug[:max_length].rsplit("-", 1)[0]

    return slug or "untitled"


def generate_short_id() -> str:
    """Generate 6-character unique identifier."""
    hash_input = f"{time.time()}"
    return hashlib.md5(hash_input.encode()).hexdigest()[:6]


def generate_job_slug(
    title: str | None,
    author: str | None,
    template: str = "{author_lastname}_{title_slug}_{short_id}",
) -> str:
    """Generate job folder slug from metadata.

    Args:
        title: Book title
        author: Author name(s)
        template: Slug template with placeholders

    Returns:
        Slug string like "derrida_writing-and-difference_a1b2c3"
    """
    return template.format(
        author_lastname=extract_author_lastname(author),
        title_slug=slugify_title(title),
        short_id=generate_short_id(),
    )
```

### 2. AppConfig Class

```python
# epub2tts_edge/config.py

import os
import json
import platform
from pathlib import Path
from dataclasses import dataclass


@dataclass
class AppConfig:
    """Centralized application configuration."""

    # Directory paths
    base_dir: Path
    jobs_dir: Path
    cache_dir: Path
    output_dir: Path | None = None  # None = use job directory

    # Slug template for job folders
    job_slug_template: str = "{author_lastname}_{title_slug}_{short_id}"

    # Processing defaults
    default_voice: str = "en-US-AndrewNeural"
    cleanup_audio_on_success: bool = True  # Delete audio/ folder after M4B created
    cleanup_jobs_after_days: int = 30

    @classmethod
    def get_platform_default_base(cls) -> Path:
        """Get platform-specific default base directory."""
        system = platform.system()

        if system == "Windows":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
            return Path(base) / "Audiobookify"
        elif system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "Audiobookify"
        else:  # Linux and others
            return Path.home() / ".audiobookify"

    @classmethod
    def load(cls, base_dir: str | Path | None = None) -> "AppConfig":
        """Load configuration with priority resolution."""
        # Priority 1: Explicit argument
        if base_dir:
            base = Path(base_dir)
        # Priority 2: Environment variable
        elif env_home := os.environ.get("AUDIOBOOKIFY_HOME"):
            base = Path(env_home)
        # Priority 3: Platform default
        else:
            base = cls.get_platform_default_base()

        # Ensure base exists
        base.mkdir(parents=True, exist_ok=True)

        # Check for config file
        config_file = base / "config.json"
        file_config = {}
        if config_file.exists():
            with open(config_file) as f:
                file_config = json.load(f)

        # Build config
        return cls(
            base_dir=base,
            jobs_dir=Path(file_config.get("jobs_dir", base / "jobs")),
            cache_dir=Path(file_config.get("cache_dir", base / "cache")),
            output_dir=Path(file_config["output_dir"]) if file_config.get("output_dir") else None,
            job_slug_template=file_config.get(
                "job_slug_template", "{author_lastname}_{title_slug}_{short_id}"
            ),
            default_voice=file_config.get("default_voice", "en-US-AndrewNeural"),
            cleanup_audio_on_success=file_config.get("cleanup_audio_on_success", True),
            cleanup_jobs_after_days=file_config.get("cleanup_jobs_after_days", 30),
        )

    def save(self) -> None:
        """Save configuration to disk."""
        config_file = self.base_dir / "config.json"
        config_dict = {
            "jobs_dir": str(self.jobs_dir),
            "cache_dir": str(self.cache_dir),
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "job_slug_template": self.job_slug_template,
            "default_voice": self.default_voice,
            "cleanup_audio_on_success": self.cleanup_audio_on_success,
            "cleanup_jobs_after_days": self.cleanup_jobs_after_days,
        }
        with open(config_file, "w") as f:
            json.dump(config_dict, f, indent=2)

    def ensure_dirs(self) -> None:
        """Ensure all directories exist."""
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_job_dir(self, slug: str) -> Path:
        """Get directory for a specific job."""
        return self.jobs_dir / slug

    def get_job_audio_dir(self, slug: str) -> Path:
        """Get audio directory for a job (intermediate files)."""
        return self.jobs_dir / slug / "audio"

    def get_output_path(self, slug: str, filename: str) -> Path:
        """Get output path for final M4B file."""
        if self.output_dir:
            return self.output_dir / filename
        return self.jobs_dir / slug / filename


# Singleton for global access
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AppConfig.load()
        _config.ensure_dirs()
    return _config


def init_config(base_dir: str | Path | None = None) -> AppConfig:
    """Initialize configuration with optional custom base directory."""
    global _config
    _config = AppConfig.load(base_dir)
    _config.ensure_dirs()
    return _config
```

### 3. Updated JobManager

```python
# Changes to job_manager.py

from epub2tts_edge.config import get_config, generate_job_slug

class JobManager:
    def __init__(self, jobs_dir: str | None = None):
        config = get_config()
        self.jobs_dir = Path(jobs_dir) if jobs_dir else config.jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def create_job(
        self,
        source_file: str,
        title: str | None = None,
        author: str | None = None,
        speaker: str = "en-US-AndrewNeural",
        ...
    ) -> Job:
        config = get_config()

        # Generate human-readable slug for job folder
        slug = generate_job_slug(
            title=title,
            author=author,
            template=config.job_slug_template,
        )
        job_dir = config.get_job_dir(slug)
        audio_dir = config.get_job_audio_dir(slug)

        # Create directories
        job_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)

        job = Job(
            job_id=slug,  # slug IS the job_id now
            source_file=source_file,
            job_dir=str(job_dir),
            audio_dir=str(audio_dir),
            title=title,
            author=author,
            speaker=speaker,
            ...
        )
        self._save_job(job)
        return job
```

### 4. Updated audio_generator.py

```python
# Changes to audio_generator.py

import shutil
from epub2tts_edge.config import get_config

def read_book(
    ...,
    audio_dir: str | None = None,  # NEW: job's audio directory
):
    config = get_config()

    # All intermediate files go in the job's audio directory
    # No separate temp directories needed!

    # Generate chapter audio to audio_dir/chapter_001.flac, etc.
    for i, chapter in enumerate(chapters):
        output_file = Path(audio_dir) / f"chapter_{i:03d}.flac"
        generate_chapter_audio(chapter, output_file, ...)

    # Silence trimming and normalization work IN-PLACE
    # or use audio_dir for any intermediates
    if trim_silence:
        trim_silence_in_files(audio_dir)  # Modifies files in place
    if normalize:
        normalize_files_in_place(audio_dir)

    # Combine into final M4B
    output_path = config.get_output_path(job_id, f"{author} - {title}.m4b")
    combine_to_m4b(audio_dir, output_path)

    # Cleanup audio folder on success
    if config.cleanup_audio_on_success:
        shutil.rmtree(audio_dir, ignore_errors=True)

    return output_path
```

### 4. CLI Arguments

```python
# In epub2tts_edge.py main()

parser.add_argument(
    "--base-dir",
    help="Base directory for Audiobookify data (default: platform-specific)",
)
parser.add_argument(
    "--output-dir", "-o",
    help="Output directory for final audiobook (default: job directory)",
)

# Initialize config early
if args.base_dir:
    init_config(args.base_dir)
config = get_config()
if args.output_dir:
    config.output_dir = Path(args.output_dir)
```

### 5. TUI Integration

```python
# In tui.py SettingsPanel

class SettingsPanel(Vertical):
    def compose(self):
        ...
        # Add directory settings section
        yield Label("Output Directory:")
        yield Input(
            placeholder=str(get_config().output_dir or "Job directory"),
            id="output-dir-input",
        )
        yield Button("Browse...", id="browse-output-dir")
```

## Migration Path

1. **v2.4.x**: Introduce AppConfig with backward compatibility
   - Default to existing `~/.audiobookify/jobs/` on Linux
   - Existing jobs continue to work

2. **v2.5.0**: Full integration
   - All temp files use centralized temp directory
   - Output directory configurable
   - Platform-specific defaults

3. **v3.0.0**: Cleanup
   - Remove deprecated hardcoded paths
   - Add migration utility for old job directories

## Benefits

1. **User control** - Configure where data is stored
2. **Platform appropriate** - Follows OS conventions
3. **Predictable cleanup** - All temp files in one place
4. **Portable** - Set `AUDIOBOOKIFY_HOME` for different locations
5. **Organization** - Clear structure for jobs, temp, cache

## Configuration Examples

### Default (Linux)
```json
// ~/.audiobookify/config.json
{
  "jobs_dir": "~/.audiobookify/jobs",
  "temp_dir": "~/.audiobookify/temp",
  "cache_dir": "~/.audiobookify/cache",
  "output_dir": null,
  "cleanup_temp_on_success": true
}
```

### Custom Output Directory
```json
{
  "output_dir": "/mnt/audiobooks/converted",
  "cleanup_temp_on_success": true
}
```

### CLI Override
```bash
# Use custom base directory
audiobookify --base-dir /data/audiobookify book.epub

# Just override output
audiobookify -o /mnt/audiobooks book.epub
```

## Testing

1. Test platform detection on Linux, macOS, Windows
2. Test priority resolution (CLI > env > config > default)
3. Test directory creation and permissions
4. Test temp file cleanup
5. Test migration from existing jobs
