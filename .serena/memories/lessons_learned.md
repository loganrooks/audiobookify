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

---
Last updated: 2025-12-05
