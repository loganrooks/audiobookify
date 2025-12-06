"""Centralized application configuration for Audiobookify.

This module provides:
- AppConfig: Centralized configuration management
- Slug generation for human-readable job folder names
- Platform-specific default directories
- Configuration priority: CLI > Environment > Config file > Default
"""

import hashlib
import json
import os
import platform
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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
        """Load configuration with priority resolution.

        Priority (highest to lowest):
        1. Explicit argument (base_dir parameter)
        2. Environment variable (AUDIOBOOKIFY_HOME)
        3. Platform default
        """
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
        file_config: dict[str, Any] = {}
        if config_file.exists():
            try:
                with open(config_file) as f:
                    file_config = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass  # Use defaults if config is invalid

        # Build config with file overrides
        jobs_dir = Path(file_config.get("jobs_dir", base / "jobs"))
        cache_dir = Path(file_config.get("cache_dir", base / "cache"))
        output_dir = Path(file_config["output_dir"]) if file_config.get("output_dir") else None

        return cls(
            base_dir=base,
            jobs_dir=jobs_dir,
            cache_dir=cache_dir,
            output_dir=output_dir,
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


def reset_config() -> None:
    """Reset the global configuration (mainly for testing)."""
    global _config
    _config = None
