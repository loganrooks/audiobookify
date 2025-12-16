# Lessons Learned - Common Mistakes & Patterns

## Purpose
Track recurring mistakes to improve future behavior. Review at session start.

## Git Workflow Mistakes

### 1. Forgetting to Push After Commit
**Pattern**: Complete commit successfully, then forget to run `git push`
**Impact**: User has to remind, work not shared, potential sync issues
**Fix**: ALWAYS run `git push` immediately after successful commit
**Checklist**: commit → verify success → push → verify push success

### 2. Not Running Format Check Before Commit
**Pattern**: Run `ruff check` but not `ruff format --check`
**Impact**: Pre-commit hook fails, have to re-commit
**Fix**: Run `ruff format .` before staging, or run after lint fix

## TUI Development Patterns

### 1. Textual Event Model
**Learning**: Key events (on_key) and mouse events (Click) are separate streams
**Pattern**: Don't use on_key to track modifier state for mouse clicks
**Fix**: Use Click event's built-in `event.shift`, `event.ctrl`, etc.

### 2. Textual Message Bubbling Issues
**Learning**: Nested Message classes (e.g., `Widget.MessageName`) may not bubble correctly
**Pattern**: Message handler auto-discovery can fail for nested classes
**Fix**: Use direct method calls via `self.ancestors` instead of message bubbling
**Example**:
```python
# Instead of: self.post_message(self.Clicked(...))
# Use direct call:
for ancestor in self.ancestors:
    if isinstance(ancestor, ParentPanel):
        ancestor._handle_click(self, event.shift)
        break
```

### 3. Custom Messages - Use With Caution
**Pattern**: Child widgets posting messages to parent panels
**Caveat**: May not work reliably - prefer direct method calls for critical functionality

### 4. ListView Click Handling
**Learning**: `ListItem.on_click` doesn't reliably fire because `ListView` handles clicks at a higher level
**Pattern**: When you need to capture clicks on ListView items with modifiers (shift, ctrl):
- Use `@on(Click, "#list-view-id")` decorator at the parent container level
- Let the click bubble up (don't call `event.stop()` in ListItem)
- Access `ListView.highlighted_child` which is already updated by the time your handler fires
**Example**:
```python
@on(Click, "#chapter-tree")
def _on_tree_click(self, event: Click) -> None:
    chapter_tree = self.query_one("#chapter-tree", ListView)
    highlighted = chapter_tree.highlighted_child  # Already updated
    if event.shift:
        # Handle shift-click range selection
        pass
    else:
        # Handle regular click
        highlighted.toggle_selection()
```

## Code Quality

### 1. Always Format Before Commit
**Command sequence**:
```bash
ruff check . --fix
ruff format .
git add -A
git commit -m "message"
git push
```

## Session Workflow

### Start of Session
1. Check git status and branch
2. Read relevant memories (lessons_learned, session context)
3. Understand current state before making changes

### End of Task
1. Run tests
2. Run lint/format
3. Commit with descriptive message
4. **PUSH to remote**
5. Verify push succeeded

### 5. Terminal Modifier Key Limitations
**Learning**: Terminals have significant limitations with modifier keys:
- Shift+Click is intercepted by many terminals for text selection
- Shift+Space is not reliably detected (space has no shifted variant)
- Shift+Arrow may work but varies by terminal

**Pattern**: Modifier+key combinations are unreliable in terminal apps
**Fix**: Use distinct keys instead of modifiers for important actions
**Example**: Instead of Shift+Space for range select, use Enter key
- Space = toggle selection (sets anchor)
- Enter = select range from anchor to current
- This is more reliable across all terminals

---
## Testing Infrastructure Patterns

### 1. Mock TTS for Fast Testing
**Pattern**: Tests that call TTS are slow and require network
**Fix**: Use `enable_test_mode()` / `disable_test_mode()` from audio_generator
**Example**:
```python
try:
    enable_test_mode()  # Uses MockTTSEngine
    # ... test code ...
finally:
    disable_test_mode()
```

### 2. MockTTSEngine.generate_sync() and asyncio
**Learning**: `generate_sync()` is called from ThreadPoolExecutor threads
**Pattern**: Cannot use `asyncio.get_event_loop().run_until_complete()` in thread
**Fix**: Implement sync version without asyncio - direct implementation

### 3. Cross-Platform Path Comparison
**Learning**: Path strings differ across platforms:
- macOS: `/var/` is symlink to `/private/var/`
- Windows: Uses 8.3 short names like `RUNNER~1` vs `runneradmin`
**Fix**: Use `Path(path).resolve()` before comparing paths in tests

### 4. API Naming Conventions
**Learning**: Always verify actual API before writing tests
- `FilterConfig` uses `remove_front_matter`, not `filter_front_matter`
- `EventBus` uses `on()` method, not `subscribe()`
- `get_flat_chapters()` returns dicts, not ChapterNode objects

---
## Profile Management Patterns

### 1. Singleton with Reset for Testing
**Pattern**: Use `get_instance()` + `reset_instance()` for singletons that need testing
**Example**: ProfileManager has both methods - reset clears cache for test isolation

### 2. Dirty State Tracking
**Pattern**: Track `_loaded_*_snapshot` dict, compare with `_get_*_settings()` current
**Fix**: Use dict comparison, not object identity

### 3. Dynamic Select Options
**Pattern**: Use method `_get_*_options()` instead of class variable for dynamic data
**Fix**: Textual's `Select.set_options()` refreshes dropdown at runtime

---
Last updated: 2025-12-16
