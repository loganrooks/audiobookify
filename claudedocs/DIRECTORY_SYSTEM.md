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

### Directory Structure

```
~/.audiobookify/                    # Base directory (configurable)
├── config.json                     # Application configuration
├── jobs/                           # Job storage
│   └── {job_id}/
│       ├── job.json                # Job metadata (status, progress, settings)
│       ├── source.txt              # Exported text (intermediate)
│       ├── chapters/               # Chapter audio files
│       │   ├── chapter_001.flac
│       │   ├── chapter_002.flac
│       │   └── ...
│       └── output/                 # Final output (default location)
│           └── {Author} - {Title}.m4b
├── temp/                           # Temporary processing files
│   ├── silence_processing/
│   └── normalization/
├── cache/                          # Voice previews, etc.
│   └── voice_previews/
└── logs/                           # Application logs (optional)
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

### 1. AppConfig Class

```python
# epub2tts_edge/config.py

import os
import json
import platform
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class AppConfig:
    """Centralized application configuration."""

    # Directory paths
    base_dir: Path
    jobs_dir: Path
    temp_dir: Path
    cache_dir: Path
    output_dir: Path | None = None  # None = use job directory

    # Processing defaults
    default_voice: str = "en-US-AndrewNeural"
    cleanup_temp_on_success: bool = True
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
            temp_dir=Path(file_config.get("temp_dir", base / "temp")),
            cache_dir=Path(file_config.get("cache_dir", base / "cache")),
            output_dir=Path(file_config["output_dir"]) if file_config.get("output_dir") else None,
            default_voice=file_config.get("default_voice", "en-US-AndrewNeural"),
            cleanup_temp_on_success=file_config.get("cleanup_temp_on_success", True),
            cleanup_jobs_after_days=file_config.get("cleanup_jobs_after_days", 30),
        )

    def save(self) -> None:
        """Save configuration to disk."""
        config_file = self.base_dir / "config.json"
        config_dict = {
            "jobs_dir": str(self.jobs_dir),
            "temp_dir": str(self.temp_dir),
            "cache_dir": str(self.cache_dir),
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "default_voice": self.default_voice,
            "cleanup_temp_on_success": self.cleanup_temp_on_success,
            "cleanup_jobs_after_days": self.cleanup_jobs_after_days,
        }
        with open(config_file, "w") as f:
            json.dump(config_dict, f, indent=2)

    def ensure_dirs(self) -> None:
        """Ensure all directories exist."""
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_job_dir(self, job_id: str) -> Path:
        """Get directory for a specific job."""
        return self.jobs_dir / job_id

    def get_job_chapters_dir(self, job_id: str) -> Path:
        """Get chapters directory for a job."""
        return self.jobs_dir / job_id / "chapters"

    def get_job_output_dir(self, job_id: str) -> Path:
        """Get output directory for a job."""
        if self.output_dir:
            return self.output_dir
        return self.jobs_dir / job_id / "output"

    def create_temp_dir(self, prefix: str = "processing") -> Path:
        """Create a temporary directory under the app's temp dir."""
        import tempfile
        return Path(tempfile.mkdtemp(prefix=f"audiobookify_{prefix}_", dir=self.temp_dir))


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

### 2. Updated JobManager

```python
# Changes to job_manager.py

from epub2tts_edge.config import get_config

class JobManager:
    def __init__(self, jobs_dir: str | None = None):
        config = get_config()
        self.jobs_dir = Path(jobs_dir) if jobs_dir else config.jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def create_job(self, source_file: str, ...) -> Job:
        job_id = self._generate_job_id(source_file)
        job_dir = self.jobs_dir / job_id

        # Create subdirectories
        (job_dir / "chapters").mkdir(parents=True, exist_ok=True)
        (job_dir / "output").mkdir(parents=True, exist_ok=True)

        job = Job(
            job_id=job_id,
            source_file=source_file,
            job_dir=str(job_dir),
            chapters_dir=str(job_dir / "chapters"),
            output_dir=str(get_config().get_job_output_dir(job_id)),
            ...
        )
        ...
```

### 3. Updated audio_generator.py

```python
# Changes to audio_generator.py

from epub2tts_edge.config import get_config

def read_book(...):
    config = get_config()

    # Use centralized temp directory
    silence_temp_dir = config.create_temp_dir("silence")
    norm_temp_dir = config.create_temp_dir("norm")

    try:
        # Processing...
    finally:
        # Cleanup based on config
        if config.cleanup_temp_on_success:
            shutil.rmtree(silence_temp_dir, ignore_errors=True)
            shutil.rmtree(norm_temp_dir, ignore_errors=True)
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
