# Session Handoff - v2.6.0 TUI Enhancements

## Session Date: 2025-12-16

## Branch
`feature/v2.6.0-tui-enhancements`

## Summary
Started implementation of v2.6.0 features focusing on profile management. Feature 1 (Profile Management) is ~85% complete. Features 2-4 are planned but not started.

## Completed Work

### Feature 1: Profile Management (85% Complete)

#### 1. AppConfig Changes (`epub2tts_edge/config.py`)
- ✅ Added `profiles_dir: Path` field to AppConfig dataclass
- ✅ Updated `load()` to read profiles_dir from config.json
- ✅ Updated `save()` to persist profiles_dir
- ✅ Updated `ensure_dirs()` to create profiles directory

#### 2. ProfileManager Class (`epub2tts_edge/core/profiles.py`)
- ✅ Created `ProfileManager` class (lines 152-514)
  - Singleton pattern with `get_instance()` / `reset_instance()`
  - `_name_to_key()` - converts "My Profile" → "my_profile"
  - `_load_user_profiles()` - loads JSON from profiles_dir
  - `get_profile()`, `list_profiles()`, `get_profile_names()`
  - `get_builtin_names()`, `get_user_profile_names()`
  - `is_builtin()`, `is_user_profile()`
  - `save_profile(profile, overwrite=False)` - saves to JSON
  - `delete_profile(name)` - removes profile
  - `rename_profile(old, new)` - renames profile
  - `export_profile()`, `import_profile()` - for sharing
  - `refresh()` - reloads from disk

- ✅ Updated module functions to delegate to ProfileManager:
  - `get_profile()`, `list_profiles()`, `get_profile_names()`
  - Added `get_builtin_profile_names()`

#### 3. SettingsPanel Updates (`epub2tts_edge/tui/panels/settings_panel.py`)
- ✅ Added imports for `ProcessingProfile`, `ProfileManager`, `Static`, `reactive`
- ✅ Added CSS for `.profile-actions` buttons and `#dirty-indicator`
- ✅ Removed static `PROFILE_OPTIONS` class variable
- ✅ Added `is_dirty: reactive[bool]` state tracking
- ✅ Added `__init__` with `_loaded_profile_key` and `_loaded_profile_snapshot`
- ✅ Added `_get_profile_options()` - dynamically builds profile dropdown
- ✅ Added profile action buttons: Save As, Overwrite, Delete + dirty indicator
- ✅ Updated `on_mount()` to initialize dirty state
- ✅ Updated `on_switch_changed()` to check dirty state
- ✅ Updated `on_select_changed()` to handle profile selection and dirty check
- ✅ Updated `_apply_profile()` to track loaded profile state
- ✅ Added `_get_profile_settings()` - extracts profile-relevant settings
- ✅ Added `_check_dirty()` - compares current vs snapshot
- ✅ Added `_update_dirty_indicator()` - shows/hides indicator
- ✅ Added `_update_profile_buttons()` - enables/disables buttons
- ✅ Added `_refresh_profile_dropdown()` - updates options after save/delete
- ✅ Added `on_button_pressed()` - routes to save/overwrite/delete handlers
- ✅ Added `_on_save_profile()` - opens ProfileNameDialog
- ✅ Added `_do_save_profile(name)` - callback from dialog
- ✅ Added `_on_overwrite_profile()` - saves changes to existing profile
- ✅ Added `_on_delete_profile()` - removes user profile

#### 4. ProfileNameDialog (NEEDS CREATION)
- ❌ File not yet created: `epub2tts_edge/tui/screens/profile_dialog.py`
- SettingsPanel imports it but file doesn't exist yet

## Remaining Work for Feature 1

### Immediate Next Step
Create `epub2tts_edge/tui/screens/profile_dialog.py` - a ModalScreen that:
- Shows input field for profile name
- Returns string or None on dismiss
- Validates name length and emptiness

### Then: Unit Tests
- Create `tests/test_profile_manager.py` with tests for ProfileManager

## Features 2-4 (Not Started)

### Feature 2: Multi-File Preview Tabs
- Browser-style tabs with state per file
- New files: `multi_preview_state.py`, `multi_preview_panel.py`

### Feature 3: Parallel Job Processing
- JobQueue class with ThreadPoolExecutor(max_workers=3)
- New files: `job_queue.py`, `multi_job_progress_panel.py`

### Feature 4: Progress Estimation
- Word-count based progress
- Add total_words/completed_words to Job

## Key Files Modified
- `epub2tts_edge/config.py` - profiles_dir field
- `epub2tts_edge/core/profiles.py` - ProfileManager class (~360 lines added)
- `epub2tts_edge/tui/panels/settings_panel.py` - Profile UI (~250 lines added)

## Test Status
- 558 tests passed before this session
- Tests will fail now due to missing profile_dialog.py import

## Plan File Location
`/home/rookslog/.claude/plans/elegant-shimmying-sky.md`

## Git Status
- Branch: `feature/v2.6.0-tui-enhancements`
- Uncommitted changes in config.py, profiles.py, settings_panel.py
- Need to create profile_dialog.py before tests will pass
