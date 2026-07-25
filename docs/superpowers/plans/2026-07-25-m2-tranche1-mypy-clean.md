# M2 Tranche 1 — Type Baseline Clean + Flagged Defects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear all 53 mypy errors (fixing the real defects they point at, with tests), flip mypy to blocking in CI, ship `py.typed`, and drop the vestigial setuptools runtime dependency.

**Architecture:** No structural changes. Behavior-bug fixes (pipeline pronunciation/voice-mapping loading, `PipelineResult` on early failure, TUI preview-state attribute) are TDD'd; the remaining errors are mechanical annotation/API corrections verified by mypy itself plus the full suite staying green. CI's mypy step loses `continue-on-error` only after the count is 0.

**Tech Stack:** Python 3.11+ (venv at `.venv/`, Python 3.13), mypy, pytest, Textual (TUI tests via `app.run_test()`), edge-tts.

## Global Constraints

- Interpreter: **`.venv/bin/python`** (the pyenv global lacks project deps). All commands below assume repo root.
- Test runs: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/ -q` — baseline **570 passed, 5 skipped** (measured 2026-07-25). New tests may raise the passed count; nothing may fail.
- mypy baseline: **53 errors in 15 files** (`.venv/bin/python -m mypy epub2tts_edge`). Each task states which errors it retires; re-run mypy after each task and confirm the expected drop. Target after Task 10: **0 errors**.
- Format/lint before every commit: `.venv/bin/python -m ruff format epub2tts_edge tests setup.py && .venv/bin/python -m ruff check .` (format is scoped to Python sources on purpose — ruff ≥0.16 reformats Markdown code fences).
- Commit AND push together: `git add -A && git commit -m "..." && git push` (project rule: a commit is not complete until pushed).
- No behavior changes in the mechanical tasks. Where a fix could change behavior, it is called out and tested.
- `# type: ignore` is a last resort; every use needs the specific error code and a comment saying why. The tasks below need none.

---

### Task 1: Drop the vestigial setuptools runtime dependency

**Files:**
- Modify: `pyproject.toml` (line 59, inside `[project] dependencies`)
- Modify: `requirements.txt` (line 21)

**Interfaces:**
- Consumes: nothing. Produces: nothing later tasks rely on.
- Warrant: `grep -rn "pkg_resources\|import setuptools" epub2tts_edge/` returns nothing (verified 2026-07-25); the only setuptools uses are the build backend (`[build-system]`, `setup.py`), which are unaffected.

- [ ] **Step 1: Remove the dependency lines**

In `pyproject.toml`, delete the line `    "setuptools>=61.0",` from the `[project] dependencies` list (do NOT touch `[build-system] requires` or `[tool.setuptools.*]`). In `requirements.txt`, delete the line `setuptools>=61.0`.

- [ ] **Step 2: Verify the sync check and suite pass**

Run: `.venv/bin/python scripts/check_requirements_sync.py && SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/ -q`
Expected: sync check OK; 570 passed, 5 skipped.

- [ ] **Step 3: Verify the wheel still builds and installs clean**

Run: `.venv/bin/python -m build --wheel --outdir /tmp/t1dist && python3 -m venv /tmp/t1venv && /tmp/t1venv/bin/pip install -q /tmp/t1dist/*.whl && /tmp/t1venv/bin/audiobookify --version`
Expected: prints `audiobookify 2.6.0` (or current version). Clean up: `rm -rf /tmp/t1dist /tmp/t1venv`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml requirements.txt && git commit -m "Drop vestigial setuptools runtime dependency (M2)" && git push
```

---

### Task 2: Fix pipeline pronunciation loading (live crash bug) — TDD

`core/pipeline.py:303` passes a file **path** (`str`) to `PronunciationProcessor`, whose `__init__(config: PronunciationConfig | None)` stores it and immediately calls `self.config.case_sensitive` → `AttributeError` the first time a pipeline runs with `pronunciation_dict` set. The real API is `PronunciationProcessor().load_dictionary(file_path)` (`epub2tts_edge/pronunciation.py:117`).

**Files:**
- Modify: `epub2tts_edge/core/pipeline.py:299-303` (inside `generate_audio`)
- Test: `tests/test_pipeline.py` (append a new test class)

**Interfaces:**
- Consumes: `PronunciationProcessor` from `epub2tts_edge/pronunciation.py` — `__init__(config: PronunciationConfig | None = None)`, `load_dictionary(file_path: str) -> None`, attribute `config.dictionary: dict[str, str]`.
- Produces: `ConversionPipeline._load_pronunciation_processor() -> PronunciationProcessor | None` — Task 3 mirrors this shape for voice mapping.
- Retires mypy error: `core/pipeline.py:303 [arg-type]`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_pipeline.py`; mirror its existing imports/fixtures — it already imports `ConversionPipeline` and `PipelineConfig`)

```python
class TestPronunciationLoading:
    """Pipeline must load a pronunciation dictionary from the configured path."""

    def test_load_pronunciation_processor_reads_the_file(self, tmp_path):
        pron_file = tmp_path / "pron.json"
        pron_file.write_text('{"Hermione": "her-MY-oh-nee"}', encoding="utf-8")

        config = PipelineConfig(pronunciation_dict=str(pron_file))
        pipeline = ConversionPipeline(config=config, base_dir=tmp_path)

        processor = pipeline._load_pronunciation_processor()

        assert processor is not None
        assert processor.config.dictionary == {"Hermione": "her-MY-oh-nee"}
        assert processor.process("Hermione waved.") == "her-MY-oh-nee waved."

    def test_load_pronunciation_processor_none_when_unconfigured(self, tmp_path):
        pipeline = ConversionPipeline(config=PipelineConfig(), base_dir=tmp_path)
        assert pipeline._load_pronunciation_processor() is None
```

Note: check `ConversionPipeline.__init__`'s actual signature in `core/pipeline.py` before writing — if it takes different kwargs (e.g. no `base_dir`), construct it the way the existing tests in `tests/test_pipeline.py` do. Reuse their fixture if one builds a pipeline.

- [ ] **Step 2: Run to verify failure**

Run: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_pipeline.py -k Pronunciation -v`
Expected: FAIL — `AttributeError: 'ConversionPipeline' object has no attribute '_load_pronunciation_processor'`.

- [ ] **Step 3: Implement**

In `core/pipeline.py`, add a method on `ConversionPipeline` (near `generate_audio`):

```python
def _load_pronunciation_processor(self) -> "PronunciationProcessor | None":
    """Build a pronunciation processor from the configured dictionary file.

    The config stores a file PATH; PronunciationProcessor wants a config
    object. Passing the path straight through (the old code) crashed on
    first use.
    """
    if not self.config.pronunciation_dict:
        return None
    from ..pronunciation import PronunciationProcessor

    processor = PronunciationProcessor()
    processor.load_dictionary(self.config.pronunciation_dict)
    return processor
```

Then replace the inline block at lines 298-303 with:

```python
        # Load pronunciation processor if configured
        pronunciation_processor = self._load_pronunciation_processor()
```

Use a `TYPE_CHECKING` import for the return annotation if `PronunciationProcessor` isn't imported at module top (keep the lazy runtime import — that's the existing style here).

- [ ] **Step 4: Run tests + mypy**

Run: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_pipeline.py -q && .venv/bin/python -m mypy epub2tts_edge | tail -1`
Expected: tests pass; mypy count drops 53 → 52.

- [ ] **Step 5: Commit**

```bash
git add epub2tts_edge/core/pipeline.py tests/test_pipeline.py && git commit -m "Fix pipeline pronunciation loading: path was passed where a config belongs" && git push
```

---

### Task 3: Fix pipeline voice-mapping loading (live crash bug) — TDD

`core/pipeline.py:310` calls `VoiceMapping.from_json(path)` — no such method exists (`VoiceMapping` is a plain dataclass; the JSON loader is `MultiVoiceProcessor.load_mapping(file_path)`, `epub2tts_edge/multi_voice.py:261`). Any pipeline run with `voice_mapping` set crashes with `AttributeError`. Also note: line 311-312 sets `mapping.default_voice = narrator_voice` — but the field for narration is `narrator_voice`, and `load_mapping` may already set voices from the file; preserve the *intent* (narrator override) using the correct field.

**Files:**
- Modify: `epub2tts_edge/core/pipeline.py:305-313`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `MultiVoiceProcessor(mapping: VoiceMapping | None = None)` with `load_mapping(file_path: str) -> None`; `VoiceMapping` dataclass fields `default_voice: str`, `narrator_voice: str | None`, `character_voices: dict[str, str]` (`multi_voice.py:13-24`). Verify `MultiVoiceProcessor.__init__`'s exact signature in the file before implementing.
- Produces: `ConversionPipeline._load_multi_voice_processor() -> MultiVoiceProcessor | None`.
- Retires mypy error: `core/pipeline.py:310 [attr-defined]`.

- [ ] **Step 1: Write the failing tests** (append to the class from Task 2 or a sibling class)

```python
class TestVoiceMappingLoading:
    """Pipeline must load a voice mapping from the configured JSON path."""

    def test_load_multi_voice_processor_reads_the_file(self, tmp_path):
        mapping_file = tmp_path / "voices.json"
        mapping_file.write_text(
            '{"default_voice": "en-US-AndrewNeural",'
            ' "character_voices": {"Alice": "en-US-AriaNeural"}}',
            encoding="utf-8",
        )

        config = PipelineConfig(voice_mapping=str(mapping_file))
        pipeline = ConversionPipeline(config=config, base_dir=tmp_path)

        processor = pipeline._load_multi_voice_processor()

        assert processor is not None
        assert processor.mapping.character_voices == {"Alice": "en-US-AriaNeural"}

    def test_narrator_voice_overrides_mapping(self, tmp_path):
        mapping_file = tmp_path / "voices.json"
        mapping_file.write_text('{"default_voice": "en-US-AndrewNeural"}', encoding="utf-8")

        config = PipelineConfig(
            voice_mapping=str(mapping_file),
            narrator_voice="en-GB-SoniaNeural",
        )
        pipeline = ConversionPipeline(config=config, base_dir=tmp_path)

        processor = pipeline._load_multi_voice_processor()

        assert processor is not None
        assert processor.mapping.narrator_voice == "en-GB-SoniaNeural"

    def test_load_multi_voice_processor_none_when_unconfigured(self, tmp_path):
        pipeline = ConversionPipeline(config=PipelineConfig(), base_dir=tmp_path)
        assert pipeline._load_multi_voice_processor() is None
```

First read `multi_voice.py`'s `load_mapping` body to confirm the JSON schema keys (`default_voice`, `character_voices`, …) and adjust the fixture JSON to match what it actually parses. If the loader errors on unknown/missing keys, use the minimal valid document it accepts.

- [ ] **Step 2: Run to verify failure**

Run: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_pipeline.py -k VoiceMapping -v`
Expected: FAIL — no attribute `_load_multi_voice_processor`.

- [ ] **Step 3: Implement**

```python
def _load_multi_voice_processor(self) -> "MultiVoiceProcessor | None":
    """Build a multi-voice processor from the configured mapping file.

    The old code called VoiceMapping.from_json(), which never existed;
    the JSON loader lives on MultiVoiceProcessor.
    """
    if not self.config.voice_mapping:
        return None
    from ..multi_voice import MultiVoiceProcessor

    processor = MultiVoiceProcessor()
    processor.load_mapping(self.config.voice_mapping)
    if self.config.narrator_voice:
        processor.mapping.narrator_voice = self.config.narrator_voice
    return processor
```

Replace the inline block at lines 305-313 with:

```python
        # Load multi-voice processor if configured
        multi_voice_processor = self._load_multi_voice_processor()
```

- [ ] **Step 4: Run tests + mypy**

Run: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_pipeline.py -q && .venv/bin/python -m mypy epub2tts_edge | tail -1`
Expected: pass; mypy 52 → 51.

- [ ] **Step 5: Commit**

```bash
git add epub2tts_edge/core/pipeline.py tests/test_pipeline.py && git commit -m "Fix pipeline voice-mapping loading: VoiceMapping.from_json never existed" && git push
```

---

### Task 4: `PipelineResult.job` is `Job | None` on early failure — TDD

`core/pipeline.py:546`: when `create_job` itself raises, the except-handler builds `PipelineResult(job=None)` — but the dataclass declares `job: Job` (`pipeline.py:84`). Runtime "works" (dataclasses don't enforce), so every consumer of `result.job` is typed wrong. Honest fix: declare `job: Job | None` and let mypy re-check consumers.

**Files:**
- Modify: `epub2tts_edge/core/pipeline.py:84`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `PipelineResult.job: Job | None`. Any consumer that mypy then flags (in `epub2tts_edge/`, not tests) must gate on `result.job is not None` — fix those in this task too, so the task retires errors without minting new ones.
- Retires mypy error: `core/pipeline.py:546 [arg-type]`.

- [ ] **Step 1: Write the failing-by-intent test** (documents the early-failure contract)

```python
class TestEarlyFailureResult:
    """run() on a nonexistent source must fail gracefully, job=None."""

    def test_run_with_missing_source_returns_failure_with_no_job(self, tmp_path):
        pipeline = ConversionPipeline(config=PipelineConfig(), base_dir=tmp_path)
        result = pipeline.run(tmp_path / "does-not-exist.epub")

        assert result.success is False
        assert result.error
        assert result.job is None
```

- [ ] **Step 2: Run it**

Run: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_pipeline.py -k EarlyFailure -v`
Expected: PASS at runtime already (this is a contract-pinning test — the defect is in the type). If it FAILS because `create_job` succeeds on missing files and failure happens later with a real `job`, adjust the assertion to match observed behavior (`result.job` may be non-None then) and note it — the dataclass annotation fix below still stands because line 546 can receive `None`.

- [ ] **Step 3: Fix the annotation**

In `core/pipeline.py:84` change `job: Job` → `job: Job | None`, with comment: `# None when the pipeline fails before a job is created`

- [ ] **Step 4: mypy the fallout, fix in-package consumers**

Run: `.venv/bin/python -m mypy epub2tts_edge`
Expected: `core/pipeline.py:546` gone (51 → 50 net). If new `[union-attr]` errors appear at `result.job.<attr>` sites in `epub2tts_edge/`, add `is not None` guards there in this task.

- [ ] **Step 5: Full suite + commit**

Run: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/ -q`

```bash
git add epub2tts_edge/core/pipeline.py tests/test_pipeline.py && git commit -m "Declare PipelineResult.job Optional: early failures return job=None" && git push
```

---

### Task 5: TUI preview job guard reads a nonexistent attribute — TDD

`tui/app.py:670` reads `preview_state.epub_path`; `ChapterPreviewState` has **`source_file`** (`tui/models/preview_state.py:32`). At runtime the guard raises `AttributeError` inside `_start_preview_job` whenever a PREVIEW job is started with a loaded preview state.

**Files:**
- Modify: `epub2tts_edge/tui/app.py:668-671`
- Test: `tests/test_tui_workflows.py`

**Interfaces:**
- Consumes: `ChapterPreviewState(source_file: Path, detection_method: str, ...)`; test helpers `make_preview_chapter()` / `load_preview_chapters()` already defined at the top of `tests/test_tui_workflows.py`; app test pattern `async with AudiobookifyApp(initial_path=...).run_test():`.
- Retires mypy error: `tui/app.py:670 [attr-defined]`.

- [ ] **Step 1: Write the failing test** (append to `tests/test_tui_workflows.py`; reuse its `temp_dir` fixture and existing imports — check how `_start_preview_job` obtains its `job` argument by reading `tui/app.py:663-690` first, and construct the minimal `Job` the same way existing job-flow tests in the file do; if no test constructs a `Job`, use `epub2tts_edge.job_manager` the way `app.py` does)

```python
class TestPreviewJobGuard:
    """_start_preview_job must compare against the preview state's real attribute."""

    @pytest.mark.asyncio
    async def test_mismatched_preview_state_warns_instead_of_crashing(self, temp_dir):
        app = AudiobookifyApp(initial_path=str(temp_dir))

        async with app.run_test() as _:
            preview = app.query_one(PreviewPanel)
            load_preview_chapters(
                preview, [make_preview_chapter("Chapter 1", "Some content")]
            )
            # Preview state points at file A...
            preview.preview_state.source_file = Path(temp_dir) / "a.epub"

            # ...while the job points at file B: the guard must take the
            # "please preview first" branch, not raise AttributeError.
            job = SimpleNamespace(source_file=str(Path(temp_dir) / "b.epub"))
            app._start_preview_job(job)  # AttributeError before the fix
```

(`from types import SimpleNamespace`, `from pathlib import Path` — add to the test file's imports if absent. A `SimpleNamespace` is enough iff `_start_preview_job` only touches `job.source_file` before the guard returns — verify by reading the method; otherwise build a real `Job`.)

- [ ] **Step 2: Run to verify it fails for the right reason**

Run: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_tui_workflows.py -k PreviewJobGuard -v`
Expected: FAIL with `AttributeError: 'ChapterPreviewState' object has no attribute 'epub_path'`.

- [ ] **Step 3: Fix**

In `tui/app.py:670` change `preview_panel.preview_state.epub_path` → `preview_panel.preview_state.source_file`.

- [ ] **Step 4: Run test + mypy**

Run: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_tui_workflows.py -q && .venv/bin/python -m mypy epub2tts_edge | tail -1`
Expected: pass; mypy 50 → 49.

- [ ] **Step 5: Commit**

```bash
git add epub2tts_edge/tui/app.py tests/test_tui_workflows.py && git commit -m "Fix preview-job guard: ChapterPreviewState has source_file, not epub_path" && git push
```

---

### Task 6: `epub2tts_edge.py` behavior-adjacent fixes (returns + bs4 API)

Four errors where the fix touches behavior contracts; still safe, but each verified.

**Files:**
- Modify: `epub2tts_edge/epub2tts_edge.py` lines 99, 117-150, 219+, and the end of `export_legacy` (~line 286)

**Interfaces:**
- Produces: `get_epub_cover(epub_path: str) -> IO[bytes] | None`; `export_legacy(...) -> str` that actually returns the outfile path.
- Retires 5 mypy errors: `epub2tts_edge.py:99` (×2, `[call-arg]`), `:117 [return]`, `:150 [return-value]`, `:219 [return]`.

- [ ] **Step 1: `findAll` → `find_all`** (line 99)

```python
    for a in soup.find_all("a", href=True):
```

(`findAll` is the removed-in-bs4-stubs camelCase alias; identical behavior.)

- [ ] **Step 2: `get_epub_cover` — explicit None + accurate IO type** (lines 117, 150)

Change the signature to `def get_epub_cover(epub_path: str) -> IO[bytes] | None:` (add `IO` to the `typing` import; drop `BinaryIO` from the signature — keep the import only if used elsewhere: check with grep). Add an explicit `return None` after the `except FileNotFoundError` handler's log line so the fall-through is intentional, not implied.

- [ ] **Step 3: `export_legacy` returns its outfile** (line 219's `-> str`)

At the end of `export_legacy` (after the `with open(outfile, ...)` block closes, currently ~line 286), add:

```python
    return outfile
```

The only caller (`epub2tts_edge.py:995`) discards the return value, so this cannot change behavior — it makes the function honor its declared type the same way `export()` does (`return outfile`, line 216).

- [ ] **Step 4: Run mypy + suite**

Run: `.venv/bin/python -m mypy epub2tts_edge | tail -1 && SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/ -q`
Expected: mypy 49 → 44; suite green.

- [ ] **Step 5: Commit**

```bash
git add epub2tts_edge/epub2tts_edge.py && git commit -m "Fix return contracts and bs4 API use in the CLI module (mypy)" && git push
```

---

### Task 7: Mechanical annotations — `logger.py`, `mobi_parser.py`, `chapter_detector.py`

Retires 15 errors: `logger.py:75`; `mobi_parser.py:195,251,252`; `chapter_detector.py:78,82,195,199,208,347,496,1041,1246,1280,1326` (11 sites).

**Files:**
- Modify: `epub2tts_edge/logger.py`, `epub2tts_edge/mobi_parser.py`, `epub2tts_edge/chapter_detector.py`

- [ ] **Step 1: `logger.py:75`** — the dict is untyped so indexing returns Any. Annotate the module-level cache: find `_loggers` and declare it `_loggers: dict[str, logging.Logger] = {}`.

- [ ] **Step 2: `mobi_parser.py:195`** — `self._raw_html` is inferred `None` from `__init__`. In `__init__`, annotate: `self._raw_html: str | None = None`.

- [ ] **Step 3: `mobi_parser.py:251-252`** — the `with open(html_file, ...) as f` reuses `f`, which an enclosing loop bound to a `str` (`for f in files:` in `_read_extracted_html`'s directory walk). Rename the file-handle: `with open(html_file, encoding="utf-8", errors="ignore") as html_fh:` / `content_parts.append(html_fh.read())`.

- [ ] **Step 4: `chapter_detector.py` fixes**

  - `:78` → `path: list[ChapterNode] = []`
  - `:79-82` → `node: ChapterNode | None = self` (the walk assigns `node.parent`, which is Optional)
  - `:195,199,208` — `debug_info` is `dict[str, object]`; mypy can't see the list values. Give it a type: `debug_info: dict[str, Any] = {...}` (import `Any` if absent — the file already imports from `typing`).
  - `:347` — `href = a.get("href", "")` returns `str | AttributeValueList | None` under bs4 stubs. Coerce: `file_href, anchor = self._split_href(str(href))` (the default `""` already guards None; `str()` flattens AttributeValueList to a usable href string only if it IS a str — bs4 returns str for `href` in practice; the cast documents it).
  - `:496` — same bs4 issue with `tag.get("id")`. Where `element_id` is built (line 489): `element_id = tag.get("id")` → append `(level, title, str(element_id) if element_id is not None else None)` or coerce at the append site so the tuple matches `list[tuple[int, str, str | None]]`.
  - `:1041` → `paragraphs: list[str] = []` (confirm the element type by looking at what's appended a few lines below; if it appends soup elements or dicts, annotate to match reality, not to `str`).
  - `:1246,1280,1326` — `self._chapter_tree: ChapterNode | None`. After `if not self._chapter_tree: self.detect()`, mypy can't see `detect()` populates it. Add a narrowing assert in each of the three methods after the detect call: `assert self._chapter_tree is not None  # detect() always builds the tree`.

- [ ] **Step 5: Run mypy + targeted tests**

Run: `.venv/bin/python -m mypy epub2tts_edge | tail -1 && SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_chapter_detector.py tests/test_mobi_parser.py -q`
Expected: mypy 44 → 29; tests green.

- [ ] **Step 6: Full suite + commit**

```bash
SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/ -q
git add epub2tts_edge/logger.py epub2tts_edge/mobi_parser.py epub2tts_edge/chapter_detector.py && git commit -m "Clear mypy errors in logger, mobi_parser, chapter_detector (mechanical)" && git push
```

---

### Task 8: Mechanical annotations — `audio_generator.py`, `voice_preview.py`

Retires 12 errors: `audio_generator.py:264` (×3), `:299` (×3), `:450`, `:731`, `:732` (9 total); `voice_preview.py:615` (×3).

**Files:**
- Modify: `epub2tts_edge/audio_generator.py`, `epub2tts_edge/voice_preview.py`

- [ ] **Step 1: The `Communicate(**kwargs)` pattern** (audio_generator 264, 299; voice_preview 615)

All three sites build `kwargs = {}` then unpack into `edge_tts.Communicate`. mypy maps `dict[str, str]` values onto every optional param. Fix by typing the dict as Any-valued at each site:

```python
            kwargs: dict[str, Any] = {}
```

(`Any` is already imported in `audio_generator.py` — verify; add `from typing import Any` to `voice_preview.py` if missing.) Do NOT restructure into explicit keyword arguments — `Communicate`'s defaults for rate/volume are private to edge-tts, and passing `None` explicitly changes behavior.

- [ ] **Step 2: `audio_generator.py:450`** → `segments: list[str] = []` (the function's docstring says it returns FLAC filenames; the appends at ~614 append `partname` strings — confirm).

- [ ] **Step 3: `audio_generator.py:731-732`** — in `make_m4b`'s cleanup, `for f in files:` reuses `f`, bound earlier by `with open(filelist, "w", ...) as f:` (line 687). Rename the cleanup loop variable:

```python
    for segment_file in files:
        os.remove(segment_file)
```

- [ ] **Step 4: Run mypy + targeted tests**

Run: `.venv/bin/python -m mypy epub2tts_edge | tail -1 && SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_test_mode.py tests/test_voice_preview.py tests/test_tts_params.py -q`
Expected: mypy 29 → 17; tests green.

- [ ] **Step 5: Commit**

```bash
git add epub2tts_edge/audio_generator.py epub2tts_edge/voice_preview.py && git commit -m "Clear mypy errors in audio_generator and voice_preview (mechanical)" && git push
```

---

### Task 9: Mechanical annotations — TUI modules

Retires 13 errors: `help_screen.py:102`; `directory_browser.py:15`; `file_panel.py:351`; `preview_panel.py:818,836,872`; `settings_panel.py:136,347`; `event_adapter.py:64,124`; `queue_panel.py:60,62,64`.

**Files:**
- Modify: the seven files above under `epub2tts_edge/tui/`

- [ ] **Step 1: `help_screen.py:102`** — the override drops the supertype's parameter. Match it:

```python
    def action_dismiss(self, result: None = None) -> None:
        """Close the help screen."""
        self.dismiss()
```

Check the exact supertype signature mypy printed (`action_dismiss(self, result: Any | None = ...) -> Coroutine[...]`); Textual's `Screen.action_dismiss` is async in this version, so the clean override is `async def action_dismiss(self, result: None = None) -> None: self.dismiss()`. Verify the help screen still closes: `SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_tui_workflows.py -q` plus mypy accepting the override.

- [ ] **Step 2: `directory_browser.py:15`** — parameter type must be the supertype's `Iterable[Path]`:

```python
from collections.abc import Iterable

    def filter_paths(self, paths: Iterable[Path]) -> list[Path]:
```

- [ ] **Step 3: `file_panel.py:351`** → `all_files: list[Path] = []` (it extends with `Path.glob` results).

- [ ] **Step 4: `preview_panel.py:818,836,872`** — dynamic attribute on `Input`. Define a tiny subclass near the top of the file (after imports):

```python
class TitleEditInput(Input):
    """Input that remembers which chapter list item it is editing."""

    chapter_item: Any = None
```

Replace the `Input(...)` construction at ~813 with `TitleEditInput(...)`, and the two `self.query_one("#title-edit-input", Input)` lookups (at ~871 and wherever the submit handler queries it) with `TitleEditInput`. For `:836` (`self.preview_state.modified` where `preview_state: ChapterPreviewState | None`), add a guard right before: `if self.preview_state is not None: self.preview_state.modified = True` (or an early-return guard at the top of the method if `preview_state` being None there is impossible — read the method and pick the honest one).

- [ ] **Step 5: `settings_panel.py:136`** — the comprehension calls `get_profile(name)` twice and mypy sees the second call as Optional. Rewrite the class attribute:

```python
    PROFILE_OPTIONS = [("custom", "Custom")] + [
        (name, profile.name if (profile := get_profile(name)) else name)
        for name in get_profile_names()
    ]
```

- [ ] **Step 6: `settings_panel.py:347`** — `event.value` is `SelectType | NoSelection`. Guard:

```python
        if event.select.id == "profile-select":
            profile_name = event.value
            if isinstance(profile_name, str) and profile_name != "custom":
                self._apply_profile(profile_name)
```

- [ ] **Step 7: `event_adapter.py:64,124`** — `list[callable]` uses the builtin as a type. Fix:

```python
from collections.abc import Callable

        self._unsubscribers: list[Callable[[], None]] = []
```

(Confirm the unsubscriber signature: `event_bus.on(...)` returns a zero-arg callable — check `core/events.py`; adjust the `Callable[...]` params to its real return type.)

- [ ] **Step 8: `queue_panel.py:60,62,64`** — `update_cell_at` wants a `Coordinate`:

```python
from textual.coordinate import Coordinate

            table.update_cell_at(Coordinate(row_key, 0), status_icon)
            table.update_cell_at(
                Coordinate(row_key, 2), str(task.chapter_count) if task.chapter_count else "-"
            )
            table.update_cell_at(Coordinate(row_key, 3), self._format_duration(task.duration))
```

- [ ] **Step 9: Run mypy + TUI tests, then full suite**

Run: `.venv/bin/python -m mypy epub2tts_edge | tail -1 && SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/test_tui_workflows.py -q && SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/ -q`
Expected: mypy 17 → 4; all green.

- [ ] **Step 10: Commit**

```bash
git add epub2tts_edge/tui/ && git commit -m "Clear mypy errors across TUI modules (mechanical)" && git push
```

---

### Task 10: Final four — `epub2tts_edge.py:278,434,440` and `core/pipeline.py:579`

Both files build chapter dicts as `{"title": ..., "paragraphs": [...]}` and mypy infers `object`/`Sequence` values. Give the structure a name once and reuse it.

**Files:**
- Modify: `epub2tts_edge/epub2tts_edge.py`, `epub2tts_edge/core/pipeline.py`

- [ ] **Step 1: Annotate the chapter dicts in `epub2tts_edge.py`**

At `:434` the enclosing function builds `current_chapter = {"title": ..., "paragraphs": []}`. Annotate at creation: `current_chapter: dict[str, Any] = {...}` and `book_contents: list[dict[str, Any]] = []`, and `chapter_titles: list[str] = []` where declared (this also clears `:440`'s tuple mismatch). At `:278` (in `export_legacy`) the loop iterates `chapter["paragraphs"]` on the same shape — annotate `book_contents: list[dict[str, Any]] = []` at the top of `export_legacy` too. Import `Any` if the module doesn't already.

- [ ] **Step 2: `core/pipeline.py:579`** — same pattern in `_parse_text_file`: `current_chapter` is inferred with `Sequence[str]` values. Annotate: `current_chapter: dict[str, Any] | None = None` and `chapters: list[dict[str, Any]] = []` (matches the declared return `list[dict]`).

- [ ] **Step 3: Zero check**

Run: `.venv/bin/python -m mypy epub2tts_edge`
Expected: **`Success: no issues found in 43 source files`**. If stragglers remain, fix them in this task — the next task flips CI to blocking and must start from 0.

- [ ] **Step 4: Full suite + commit**

```bash
SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/ -q
git add epub2tts_edge/epub2tts_edge.py epub2tts_edge/core/pipeline.py && git commit -m "Annotate chapter-dict structures; mypy baseline reaches zero" && git push
```

---

### Task 11: Flip mypy to blocking, ship `py.typed`, propagate docs

Only after Task 10's zero. `pyproject.toml:104-105` already declares `py.typed` in package-data — the file itself was never created, so wheels ship without it (that's why creating it was deferred until the baseline was clean).

**Files:**
- Create: `epub2tts_edge/py.typed` (empty file)
- Modify: `.github/workflows/ci.yml:124-129` (mypy step)
- Modify: `CHANGELOG.md`, `docs/uplift-plan.md`, `ROADMAP.md` (propagation)

- [ ] **Step 1: Create the marker**

Run: `touch epub2tts_edge/py.typed`

- [ ] **Step 2: Verify it ships in the wheel**

Run: `.venv/bin/python -m build --wheel --outdir /tmp/t11dist && unzip -l /tmp/t11dist/*.whl | grep py.typed && rm -rf /tmp/t11dist`
Expected: `epub2tts_edge/py.typed` listed.

- [ ] **Step 3: Make CI mypy blocking**

In `.github/workflows/ci.yml`, replace the mypy step (and its stale comment):

```yaml
      # Blocking since the M2 tranche-1 cleanup took the baseline to zero
      # (2026-07). If this fails, fix the types -- do not re-add
      # continue-on-error.
      - name: Run mypy
        run: mypy epub2tts_edge
```

- [ ] **Step 4: Propagate**

- `CHANGELOG.md`: under `## [Unreleased]` (create the section if absent, with a compare link following the existing pattern), add entries for: pipeline pronunciation/voice-mapping crash fixes, preview-job guard fix, `PipelineResult.job` Optional, mypy now blocking + `py.typed` shipped, setuptools runtime dep dropped.
- `docs/uplift-plan.md` M2 section: tick the completed checkboxes (mypy items at lines ~143-146, setuptools at ~135, and the three product-defect lines ~150-152), and correct the stale line references in those product-defect items to the real sites (546 / 278 / 670) with a note that the plan's originals had drifted.
- `ROADMAP.md`: if it mentions the mypy backlog (CI comment says "Tracked in ROADMAP.md"), update that line to reflect blocking-and-green. Grep: `grep -n mypy ROADMAP.md`.

- [ ] **Step 5: Full local gate, commit, watch CI**

```bash
SKIP_TTS_TESTS=1 .venv/bin/python -m pytest tests/ -q
.venv/bin/python -m ruff format epub2tts_edge tests setup.py && .venv/bin/python -m ruff check .
.venv/bin/python -m mypy epub2tts_edge
git add -A && git commit -m "Make mypy blocking and ship py.typed (M2 tranche 1 complete)" && git push
gh run watch $(gh run list --branch main --limit 1 --json databaseId -q '.[0].databaseId') --exit-status
```

Expected: CI fully green with mypy now a required-to-pass step.

---

## Running mypy ledger (expected after each task)

| After task | Expected `mypy` errors |
|---|---|
| baseline | 53 |
| 2 | 52 |
| 3 | 51 |
| 4 | 50 (plus any consumer fallout, fixed within the task) |
| 5 | 49 |
| 6 | 44 |
| 7 | 29 |
| 8 | 17 |
| 9 | 4 |
| 10 | **0** |

The per-task numbers are the plan's arithmetic over the measured error list; the authoritative check is always `.venv/bin/python -m mypy epub2tts_edge | tail -1`. If a task's actual drop differs, investigate before moving on — a smaller drop means a site was missed; a larger one means a fix cascaded (fine, note it).
