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

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/ -v
```

## Project Structure

```
audiobookify/
├── epub2tts_edge/          # Main package
│   ├── __init__.py         # Package exports
│   ├── epub2tts_edge.py    # CLI and audio generation
│   ├── chapter_detector.py # Chapter detection logic
│   ├── batch_processor.py  # Batch processing
│   └── tui.py             # Terminal UI
├── tests/                  # Test files
├── CLAUDE.md              # Development context for AI
├── ROADMAP.md             # Future plans
├── CONTRIBUTING.md        # This file
└── README.md              # User documentation
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
# All tests (uses mock TTS automatically - no network calls)
python -m pytest tests/ -v

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

## Areas for Contribution

### High Priority
- [ ] Bug fixes
- [x] Test coverage improvements (558 tests, good coverage)
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
- Check [CLAUDE.md](./CLAUDE.md) for technical context
- See [ROADMAP.md](./ROADMAP.md) for project direction

## License

By contributing, you agree that your contributions will be licensed under the GPL 3.0 License.
