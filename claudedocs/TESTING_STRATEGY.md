# Testing Strategy

## Overview

This document defines testing approaches to catch bugs early and prevent regressions, reducing manual E2E testing burden.

## Current State (Updated December 2024)

### Existing Tests (558 tests)

| Module | Tests | Coverage |
|--------|-------|----------|
| audio_normalization | 17 | Good |
| batch_processor | 19 | Good |
| chapter_detector | 17 | Good |
| chapter_selector | 24 | Good |
| content_filter | 40 | Good |
| e2e_workflow | 14 | Good |
| event_bus | 34 | Good |
| integration | 19 | Basic |
| job_manager | 32 | Good |
| mobi_parser | 30 | Good |
| multi_voice | 28 | Good |
| output_naming | 34 | Good |
| pause_resume | 14 | Good |
| pipeline | 29 | Good (60%) |
| preview_export | 9 | Basic |
| profiles | 27 | Good |
| pronunciation | 23 | Good |
| silence_detection | 18 | Good |
| test_mode | 13 | Good |
| tts_params | 10 | Good |
| tui_workflows | 55 | Good |
| voice_preview | 18 | Good |

### TUI Testing Infrastructure ✅

Now available:
- Panel instantiation and mounting tests
- Preview loading and chapter editing tests
- Job selection and batch operations tests
- Lazy import verification tests
- Mock TTS integration tests
- Processing initiation workflow tests
- Error handling tests (file errors, invalid formats, TTS failures)
- Full E2E workflow tests with mock TTS (EPUB → text → audio → M4B)
- Core pipeline tests (29 tests covering ConversionPipeline, PipelineConfig, PipelineResult)

### Remaining Gaps

All major testing gaps have been addressed. Future enhancements:
- Snapshot testing for regression detection
- Test documentation improvements

---

## Testing Pyramid

```
                    ┌─────────┐
                   /  Manual   \      ← Reduced with automation
                  /    E2E      \
                 ├───────────────┤
                /   Integration   \   ← TUI workflows + pipeline (84 tests)
               /      Tests        \
              ├─────────────────────┤
             /      Unit Tests       \  ← Strong coverage
            /   (558 existing tests)  \
           └───────────────────────────┘
```

---

## New Test Categories

### 1. TUI Integration Tests

Using Textual's testing framework:

```python
# tests/test_tui_workflows.py

import pytest
from textual.testing import AppTest
from epub2tts_edge.tui import AudiobookifyApp

@pytest.fixture
def sample_epub(tmp_path):
    """Create a minimal test EPUB."""
    epub_path = tmp_path / "test_book.epub"
    create_test_epub(epub_path, chapters=[
        ("Chapter 1", "First chapter content."),
        ("Chapter 2", "Second chapter content."),
        ("Notes", "End notes."),
    ])
    return epub_path

class TestPreviewWorkflow:
    """Test the preview → edit → process workflow."""

    @pytest.mark.asyncio
    async def test_preview_loads_chapters(self, sample_epub):
        """Preview should load and display chapters."""
        async with AppTest.run(AudiobookifyApp) as pilot:
            app = pilot.app

            # Navigate to sample epub directory
            app.query_one(FilePanel).current_path = sample_epub.parent

            # Wait for file list to populate
            await pilot.pause()

            # Select the epub
            file_list = app.query_one("#file-list", ListView)
            # ... select file

            # Click preview
            await pilot.click("#preview-chapters-btn")
            await pilot.pause()

            # Verify chapters loaded
            preview = app.query_one(PreviewPanel)
            assert preview.has_chapters()
            assert len(preview.preview_state.chapters) == 3

    @pytest.mark.asyncio
    async def test_delete_chapter_removes_from_list(self, sample_epub):
        """Deleting a chapter should remove it from preview."""
        async with AppTest.run(AudiobookifyApp) as pilot:
            # ... setup
            preview = pilot.app.query_one(PreviewPanel)
            initial_count = len(preview.preview_state.chapters)

            # Select and delete "Notes" chapter
            # ...

            assert len(preview.preview_state.chapters) == initial_count - 1

    @pytest.mark.asyncio
    async def test_merge_combines_chapters(self, sample_epub):
        """Merging chapters should combine content."""
        # ...

    @pytest.mark.asyncio
    async def test_undo_restores_state(self, sample_epub):
        """Undo should restore previous chapter state."""
        # ...

    @pytest.mark.asyncio
    async def test_start_all_processes_remaining(self, sample_epub):
        """Start All should process all chapters in list."""
        # ...
```

### 2. Test Fixtures

```python
# tests/fixtures/epub_factory.py

from ebooklib import epub

def create_test_epub(
    path: Path,
    title: str = "Test Book",
    author: str = "Test Author",
    chapters: list[tuple[str, str]] = None,
) -> Path:
    """Create a minimal EPUB for testing."""
    book = epub.EpubBook()
    book.set_title(title)
    book.add_author(author)

    chapters = chapters or [("Chapter 1", "Test content.")]

    for i, (ch_title, ch_content) in enumerate(chapters):
        ch = epub.EpubHtml(title=ch_title, file_name=f'ch{i}.xhtml')
        ch.content = f'<h1>{ch_title}</h1><p>{ch_content}</p>'
        book.add_item(ch)
        book.spine.append(ch)

    # Add TOC
    book.toc = [epub.Link(f'ch{i}.xhtml', ch_title, f'ch{i}')
                for i, (ch_title, _) in enumerate(chapters)]

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(str(path), book)
    return path

# Predefined fixtures
FIXTURES = {
    "simple_book": {
        "chapters": [
            ("Chapter 1", "First chapter."),
            ("Chapter 2", "Second chapter."),
        ]
    },
    "book_with_front_matter": {
        "chapters": [
            ("Title Page", "Book Title"),
            ("Copyright", "Copyright notice."),
            ("Dedication", "For someone."),
            ("Chapter 1", "Real content."),
            ("Chapter 2", "More content."),
            ("Notes", "End notes."),
            ("Index", "A, B, C"),
        ]
    },
    "nested_chapters": {
        "chapters": [
            ("Part I", ""),
            ("Chapter 1", "Content."),
            ("Chapter 2", "Content."),
            ("Part II", ""),
            ("Chapter 3", "Content."),
        ]
    },
}
```

### 3. Mock TTS for Fast Tests

```python
# tests/mocks/tts_mock.py

class MockTTSEngine:
    """Mock TTS that generates silence instead of speech."""

    def __init__(self, speed_factor: float = 100.0):
        """
        Args:
            speed_factor: How much faster than real TTS.
                         100.0 = instant, 1.0 = real-time
        """
        self.speed_factor = speed_factor
        self.calls = []  # Track calls for assertions

    async def generate(self, text: str, voice: str, **kwargs) -> bytes:
        """Generate silent audio of appropriate duration."""
        self.calls.append({"text": text, "voice": voice, **kwargs})

        # Calculate duration based on text length
        # Assume ~150 words/minute speaking rate
        words = len(text.split())
        duration_seconds = (words / 150) * 60 / self.speed_factor

        # Generate silent audio
        return generate_silence(duration_seconds)

# Usage in tests:
@pytest.fixture
def mock_tts(monkeypatch):
    mock = MockTTSEngine(speed_factor=1000)  # 1000x faster
    monkeypatch.setattr("epub2tts_edge.audio_generator.run_edgespeak", mock.generate)
    return mock

def test_processing_with_mock(mock_tts, sample_epub):
    result = process_book(sample_epub)
    assert result.success
    assert len(mock_tts.calls) > 0  # TTS was called
```

### 4. Snapshot Testing

```python
# tests/test_export_snapshots.py

def test_export_produces_expected_output(sample_epub, snapshot):
    """Exported text should match expected format."""
    preview_state = load_preview(sample_epub)

    # Simulate some edits
    preview_state.chapters = preview_state.chapters[1:-1]  # Remove first/last

    output = preview_state.export_to_text(Path("output.txt"))

    # Compare against saved snapshot
    assert output.read_text() == snapshot
```

---

## Test Mode for Development

### --test-mode Flag

```python
# In CLI and TUI

@click.option('--test-mode', is_flag=True, help='Use mock TTS for testing')
def main(test_mode: bool, ...):
    if test_mode:
        # Use mock TTS engine
        configure_mock_tts()
        # Disable network checks
        # Speed up animations
```

### Benefits

1. **Fast iteration** - Process book in seconds instead of minutes
2. **No API costs** - No Edge TTS calls
3. **Offline development** - No internet required
4. **Reproducible** - Same output every time

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install pytest-asyncio textual[dev]

      - name: Run unit tests
        run: pytest tests/ -v --ignore=tests/test_tui_workflows.py

      - name: Run TUI tests
        run: pytest tests/test_tui_workflows.py -v

      - name: Run integration tests
        run: pytest tests/test_integration.py -v --test-mode
```

---

## Testing Guidelines for Claude Code

### Before Making Changes

1. **Run existing tests**: `pytest tests/ -x -q`
2. **Check coverage for affected modules**: `pytest --cov=epub2tts_edge.MODULE`

### After Making Changes

1. **Run full test suite**: `pytest tests/ -v`
2. **Run linting**: `ruff check . && ruff format --check .`
3. **Test affected workflow manually** (if no TUI test exists)

### When Adding Features

1. **Write unit tests first** (TDD when possible)
2. **Add integration test** for new workflows
3. **Update test fixtures** if new EPUB structures needed
4. **Document manual testing steps** if automation not possible

### Common Pitfalls

| Issue | Prevention |
|-------|------------|
| Async test failures | Use `@pytest.mark.asyncio` |
| Import errors after refactor | Run tests after each file move |
| Flaky TUI tests | Use `await pilot.pause()` appropriately |
| Mock not applied | Verify monkeypatch path is correct |

---

## Implementation Checklist

### Phase 1: Foundation ✅
- [x] Create tests/fixtures/ directory
- [x] Implement create_test_epub() helper
- [x] Create predefined EPUB fixtures (8 fixture types)
- [x] Implement MockTTSEngine (with async/sync, call tracking, failure simulation)
- [x] Add --test-mode flag to CLI (13 tests)

### Phase 2: TUI Tests ✅
- [x] Set up pytest-asyncio for TUI tests
- [x] Create tests/test_tui_workflows.py (55 tests)
- [x] Test preview loading
- [x] Test chapter editing (delete, merge, undo)
- [x] Test job selection and batch operations
- [x] Test lazy import verification
- [x] Test processing initiation (with mock TTS) - 4 tests
- [x] Test error handling (file errors, invalid formats, TTS failures) - 15 tests

### Phase 3: CI Integration (Mostly Done)
- [x] Update GitHub Actions workflow (multi-platform, lint, tests)
- [x] Add test coverage reporting (Codecov + HTML artifacts)
- [ ] Add snapshot testing
- [ ] Create test documentation

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Unit test coverage | >80% |
| TUI workflow coverage | Key workflows tested |
| CI pass rate | >95% |
| Time to run tests | <2 minutes |
| Manual testing needed | Only for visual/UX issues |
