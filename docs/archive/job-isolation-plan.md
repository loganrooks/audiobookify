# Job Isolation Overhaul Plan

## Problem Statement

When processing a new book, the system incorrectly reuses audio files from previous jobs, resulting in audiobooks with wrong content. This happens because:

1. **`read_book()` blindly trusts existing files** - If `partN.flac` exists, it's used without verification (line 390-392 in audio_generator.py)
2. **`process_text_files()` bypasses job isolation** - Uses text file's directory directly (line 3393 in tui.py)
3. **No `output_dir` passed to `read_book()`** - Relies on `os.chdir()` which is error-prone
4. **Multiple code paths with inconsistent isolation** - EPUB processing uses jobs, TXT processing doesn't

---

## Root Cause Analysis

### The Offending Code

**audio_generator.py lines 390-392:**
```python
if os.path.isfile(partname):
    logger.info("%s exists, skipping to next chapter", partname)
    segments.append(partname)  # BUG: Blindly trusts existing file!
```

**Similar issue at lines 442-443:**
```python
ptemp = str(out_path / f"pgraphs{pindex}.flac")
if os.path.isfile(ptemp):
    logger.debug("%s exists, skipping to next paragraph", ptemp)
```

### Code Paths That Call `read_book()`

| Location | Passes `output_dir`? | Uses Job Isolation? | Problem |
|----------|---------------------|---------------------|---------|
| batch_processor.py:612 | NO | Yes (via os.chdir) | Relies on chdir |
| tui.py:3447 (process_text_files) | NO | NO | Completely unprotected! |
| epub2tts_edge.py:1088 | YES | Yes | OK |

---

## Solution Design

### Principle: Explicit Paths, No Trust

1. **Always pass `output_dir` explicitly** - Never rely on current working directory
2. **Never reuse intermediate files** - Delete existing part files before generating
3. **All processing paths use job isolation** - TXT files get jobs too
4. **Remove `os.chdir()` usage** - Pass absolute paths everywhere

---

## Implementation Phases

### Phase 1: Fix `read_book()` to Never Blindly Reuse Files

**File: `epub2tts_edge/audio_generator.py`**

Changes:
1. Add parameter `force_regenerate: bool = True` (default True for safety)
2. When `force_regenerate=True`, delete existing part files before generating
3. When `force_regenerate=False` (for explicit resume), verify files belong to current job

```python
def read_book(
    ...
    output_dir: str | None = None,
    force_regenerate: bool = True,  # NEW: Always regenerate by default
    job_id: str | None = None,  # NEW: For verification when resuming
) -> list[str]:
    ...
    # Set up output directory
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    else:
        out_path = Path(".")

    for i, chapter in enumerate(book_contents, start=1):
        partname = str(out_path / f"part{i}.flac")

        # CHANGED: Only skip if explicitly resuming and file is valid
        if not force_regenerate and os.path.isfile(partname):
            logger.info("%s exists, using existing file", partname)
            segments.append(partname)
        else:
            # Delete existing file if present (ensures clean state)
            if os.path.isfile(partname):
                os.remove(partname)
            # Generate new audio...
```

### Phase 2: Fix All Callers to Pass `output_dir` Explicitly

**File: `epub2tts_edge/batch_processor.py`** (line 612)

Before:
```python
files = read_book(
    book_contents,
    self.config.speaker,
    ...
)
```

After:
```python
files = read_book(
    book_contents,
    self.config.speaker,
    ...
    output_dir=working_dir,  # Pass explicitly
    force_regenerate=not task.is_resume,  # Only skip for explicit resume
)
```

**File: `epub2tts_edge/tui.py`** (line 3447 in process_text_files)

Before:
```python
audio_files = read_book(
    book_contents,
    config["speaker"],
    ...
)
```

After:
```python
audio_files = read_book(
    book_contents,
    config["speaker"],
    ...
    output_dir=str(job_output_dir),  # Use job directory
    force_regenerate=True,  # Always regenerate for new jobs
)
```

### Phase 3: Add Job Isolation to `process_text_files()`

**File: `epub2tts_edge/tui.py`**

The `process_text_files()` method must create jobs just like `process_files()` does:

```python
@work(exclusive=True, thread=True)
def process_text_files(self, files: list[Path]) -> None:
    """Process text files in background thread."""
    from .job_manager import JobManager, JobStatus

    settings_panel = self.query_one(SettingsPanel)
    config = settings_panel.get_config()

    # Create job manager for isolation
    job_manager = JobManager()

    for txt_path in files:
        # Create isolated job for this text file
        job = job_manager.create_job(
            str(txt_path),
            speaker=config["speaker"],
        )
        working_dir = Path(job.job_dir)

        # Copy text file to job directory
        import shutil
        job_txt_path = working_dir / txt_path.name
        shutil.copy(txt_path, job_txt_path)

        # Generate audio in isolated directory
        audio_files = read_book(
            book_contents,
            config["speaker"],
            ...
            output_dir=str(working_dir),
            force_regenerate=True,
        )

        # Create M4B in job directory, then move to output
        ...
```

### Phase 4: Remove `os.chdir()` Usage

**File: `epub2tts_edge/batch_processor.py`**

Remove the `os.chdir(working_dir)` block and pass absolute paths:

Before:
```python
original_dir = os.getcwd()
os.chdir(working_dir)
try:
    ...
finally:
    os.chdir(original_dir)
```

After:
```python
# No chdir needed - pass explicit paths
files = read_book(
    ...
    output_dir=working_dir,
)
generate_metadata(files, ..., output_dir=working_dir)
make_m4b(files, ..., output_dir=working_dir)
```

**File: `epub2tts_edge/tui.py`** (process_text_files)

Same pattern - remove `os.chdir()`, pass explicit paths.

### Phase 5: Add Job Cleanup

**File: `epub2tts_edge/audio_generator.py`**

Add function to clean intermediate files:

```python
def clean_intermediate_files(output_dir: str | Path) -> None:
    """Remove intermediate audio files from directory."""
    out_path = Path(output_dir)
    patterns = ["part*.flac", "pgraphs*.flac", "sntnc*.mp3"]
    for pattern in patterns:
        for f in out_path.glob(pattern):
            f.unlink()
```

Call this at the START of `read_book()` when `force_regenerate=True`:

```python
def read_book(..., force_regenerate=True):
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        if force_regenerate:
            clean_intermediate_files(out_path)
    ...
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `epub2tts_edge/audio_generator.py` | Add `force_regenerate`, `clean_intermediate_files()`, pass output_dir |
| `epub2tts_edge/batch_processor.py` | Pass `output_dir` to read_book, remove os.chdir |
| `epub2tts_edge/tui.py` | Add job isolation to process_text_files, pass output_dir |
| `epub2tts_edge/epub2tts_edge.py` | Verify already passes output_dir correctly |

---

## Testing Strategy

1. **Unit tests for `clean_intermediate_files()`**
2. **Unit tests for `read_book()` with `force_regenerate`**
3. **Integration test: Process book A, then book B in same directory**
   - Verify book B doesn't use book A's audio
4. **Integration test: Process TXT files**
   - Verify job isolation is used
5. **Resume test: Cancel mid-processing, resume**
   - Verify correct chapters are reused

---

## Rollout Plan

1. **Phase 1**: Fix `read_book()` - highest impact, simplest change
2. **Phase 2**: Fix callers - ensures isolation is used
3. **Phase 3**: Fix `process_text_files()` - completes coverage
4. **Phase 4**: Remove `os.chdir()` - cleanup, reduces complexity
5. **Phase 5**: Add cleanup functions - belt and suspenders

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing resume functionality | Add `force_regenerate=False` option for explicit resume |
| Performance impact of always regenerating | Only affects edge case of corrupt state; normal flow unaffected |
| Tests failing | Update tests to account for new behavior |

---

## Success Criteria

1. Processing book B after book A NEVER uses book A's audio
2. All intermediate files go to job-isolated directories
3. No code path relies on `os.chdir()` or current working directory
4. Explicit resume works correctly (reuses valid intermediate files)
5. All existing tests pass
6. New tests cover the fixed scenarios
