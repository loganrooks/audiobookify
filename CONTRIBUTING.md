# Contributing to Audiobookify

Thank you for your interest in contributing to Audiobookify!

## Getting Started

### Prerequisites
- Python 3.11+
- FFmpeg installed
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/loganrooks/audiobookify.git
cd audiobookify

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install the package plus dev/test tooling
pip install -e ".[dev]"

# Install the pre-commit hooks (ruff, bandit, secret detection)
pre-commit install

# Run tests
python -m pytest tests/
```

### System dependencies

| Tool | Required for | Install |
|------|--------------|---------|
| FFmpeg | All audio processing | `apt install ffmpeg` / `brew install ffmpeg` / `choco install ffmpeg` |
| espeak-ng | Some pydub operations | `apt install espeak-ng` / `brew install espeak` |

Tests that need FFmpeg skip automatically if it isn't on your PATH, so you can
work on chapter detection, parsing, and TUI code without installing it.

## Project Structure

```
audiobookify/
├── epub2tts_edge/          # Main package
│   ├── epub2tts_edge.py    # CLI entry point and argument parsing
│   ├── audio_generator.py  # TTS calls, audio assembly, M4B creation
│   ├── chapter_detector.py # TOC/heading chapter detection
│   ├── batch_processor.py  # Multi-book batch processing
│   ├── job_manager.py      # Job tracking and per-job directory isolation
│   ├── core/               # Shared pipeline: ConversionPipeline, EventBus,
│   │                       #   profiles, output naming
│   ├── testing/            # MockTTSEngine backing --test-mode (shipped in the
│   │                       #   wheel, so it works for installed users)
│   └── tui/                # Terminal UI: app, panels/, models/, handlers/
├── tests/                  # Test suite
├── scripts/                # Repo maintenance checks
├── docs/                   # Architecture and design docs (archive/ = historical)
└── .github/workflows/      # ci.yml, release.yml, tts-canary.yml
```

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/loganrooks/audiobookify/issues)
2. Create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - EPUB file (if possible) or description
   - Python version, OS

### Suggesting Features

1. Check [ROADMAP.md](./ROADMAP.md) for planned features
2. Open a feature request issue
3. Describe the use case and proposed solution

### Submitting Code

1. Fork the repository
2. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```
3. Make your changes
4. Add/update tests
5. Run tests:
   ```bash
   python -m pytest tests/ -v
   ```
6. Commit with clear message:
   ```bash
   git commit -m "Add feature: description"
   ```
7. Push and create Pull Request

## Code Style

### Python
- Follow PEP 8
- Use type hints where practical
- Docstrings for public functions
- Max line length: 100 characters

### Example
```python
def process_chapter(
    content: str,
    title: Optional[str] = None,
    level: int = 1
) -> ChapterNode:
    """
    Process chapter content and create a ChapterNode.

    Args:
        content: Raw HTML content
        title: Optional chapter title override
        level: Heading level (1-6)

    Returns:
        ChapterNode with extracted content
    """
    # Implementation
```

### Commits
- Use clear, descriptive messages
- Start with verb: Add, Fix, Update, Remove, Refactor
- Reference issues: `Fix #123: description`

## Testing

### Running Tests
```bash
# All tests (mock TTS, no network calls)
python -m pytest tests/

# Specific file
python -m pytest tests/test_chapter_detector.py -v

# With coverage
python -m pytest tests/ --cov=epub2tts_edge --cov-report=html

# Quick sanity check
python -m pytest tests/ -x -q  # Stop on first failure
```

### Test Infrastructure
- **Mock TTS**: Tests use `MockTTSEngine` for fast, offline testing
- **Test Mode**: Enable via `enable_test_mode()` for development
- **Fixtures**: Sample EPUBs in `tests/fixtures/`

### Writing Tests
- Place in `tests/` directory
- Name files `test_*.py`
- Use descriptive test names
- Test edge cases
- Use `sample_epub` fixture for EPUB tests

```python
class TestChapterDetector:
    def test_detect_toc_with_nested_chapters(self, sample_epub):
        """Test that nested TOC entries are properly parsed."""
        detector = ChapterDetector(sample_epub)
        # Test implementation
```

### Test Mode for TTS Tests
```python
from epub2tts_edge.audio_generator import enable_test_mode, disable_test_mode

def test_audio_generation(self, sample_epub, temp_dir):
    try:
        enable_test_mode()  # Uses mock TTS
        # ... test code ...
    finally:
        disable_test_mode()
```

## Release Process

Releases are tag-driven and fully automated. Maintainers only need to do this:

```bash
# 1. Bump the version in pyproject.toml
# 2. Move the [Unreleased] entries into a new "## [X.Y.Z] - YYYY-MM-DD" section
# 3. Commit, then tag and push
git commit -am "Release vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

`.github/workflows/release.yml` then:

1. Verifies the tag matches `pyproject.toml` and that CHANGELOG has a matching section
2. Builds the sdist + wheel and smoke-tests the wheel in a clean venv
3. Publishes to PyPI via Trusted Publishing (no API token is stored)
4. Pushes multi-arch images to `ghcr.io/loganrooks/audiobookify`
5. Creates a GitHub Release with notes extracted from CHANGELOG

**One-time setup required before the first automated release:**

- Configure [PyPI Trusted Publishing](https://pypi.org/manage/project/audiobookify/settings/publishing/)
  with owner `loganrooks`, repo `audiobookify`, workflow `release.yml`, environment `pypi`
- Create a `pypi` environment in the repository settings (ideally with required reviewers)

## Areas for Contribution

See the [uplift plan](./docs/uplift-plan.md) for the sequenced engineering
priorities, and the [project review](./docs/project-review-2026-07.md) for the
findings behind them.

### High Priority
- [ ] **Test coverage on the critical path.** 558 tests, but 45% overall coverage
      and the biggest modules are the least covered: CLI 14%, `tui/app.py` 9%,
      `audio_generator.py` 22%. Tests here are the most valuable contribution
      available right now.
- [ ] **Clearing the mypy baseline** (53 errors across 15 files) so the type check
      can become blocking
- [ ] Bug fixes
- [ ] Documentation

### Medium Priority
- [ ] New TTS engine support
- [ ] Additional input formats
- [ ] Performance optimizations

### Lower Priority
- [ ] UI improvements
- [ ] New output formats
- [ ] Snapshot testing for regression detection

## Questions?

- Open an issue for questions
- Check [docs/architecture.md](./docs/architecture.md) for technical context
- See [ROADMAP.md](./ROADMAP.md) for project direction

## License

By contributing, you agree that your contributions will be licensed under the GPL 3.0 License.
