# Settings Panel Redesign

## Overview

Redesign the TUI into a more organized, tabbed interface with clear separation between configuration (settings) and operations (actions). This includes reorganizing both the settings panel and the bottom tabs.

---

## Current State

### Problems

1. **Mixed Concerns**: Settings and action buttons combined in one scrolling panel
2. **Overwhelming Options**: All settings visible at once, regardless of relevance
3. **No Logical Grouping**: Voice settings mixed with detection settings mixed with output options
4. **Poor Discoverability**: Advanced options hidden among common ones
5. **Redundant Tabs**: Queue and Jobs are conceptually similar
6. **Action Placement**: Buttons like "Preview Chapters" are in settings, not near files

---

## Proposed Design

### High-Level Structure

```
┌─────────────────────────────────────┬─────────────────────────────┐
│                                     │ ⚙️ Settings                 │
│  📁 Files                           │ ┌───────────────────────────┤
│  ┌─────────────────────────────┐    │ │ 🎙️│🎵│📖│⚙️              │
│  │ [path input______] [📂]     │    │ ├───────────────────────────┤
│  │                             │    │ │                           │
│  │ ☑ Book One.epub             │    │ │   [Tab Content]           │
│  │ ☐ Book Two.epub             │    │ │                           │
│  │ ☑ Book Three.epub           │    │ │                           │
│  └─────────────────────────────┘    │ └───────────────────────────┤
│  [All][None][⟳][📋 Preview][📝 Export]│                             │
│                                     │  (Profile selector - future) │
├─────────────────────────────────────┴─────────────────────────────┤
│ 📋 Preview │ ▶️ Current │ 📊 Jobs │ 📜 Log                         │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│                    [Bottom Tab Content]                           │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Settings Panel (4 Emoji Tabs)

### Tab 1: 🎙️ Voice

Primary voice and speech settings.

| Setting | Type | Default | Notes |
|---------|------|---------|-------|
| Voice | Select | en-US-AndrewNeural | Dropdown with all voices |
| Rate | Select | Normal | -50% to +50% |
| Volume | Select | Normal | -50% to +50% |
| Narrator Voice | Input | (empty) | For multi-voice mode |
| [🔊 Preview] | Button | - | Inline voice preview |

### Tab 2: 🎵 Audio

Sound quality and timing settings.

| Setting | Type | Default | Notes |
|---------|------|---------|-------|
| Sentence Pause | Select | 1200ms | Pause after sentences |
| Paragraph Pause | Select | 1200ms | Pause after paragraphs |
| Trim Silence | Toggle | Off | Remove excessive silence |
| ↳ Threshold | Input | -40 dBFS | *Shown when Trim enabled* |
| ↳ Max Duration | Input | 2000ms | *Shown when Trim enabled* |
| Normalize | Toggle | Off | Consistent volume levels |
| ↳ Target | Input | -16 dBFS | *Shown when Normalize enabled* |
| ↳ Method | Select | peak | *Shown when Normalize enabled* |

### Tab 3: 📖 Chapters

Chapter detection and selection settings.

| Setting | Type | Default | Notes |
|---------|------|---------|-------|
| Detection | Select | combined | toc/headings/combined/auto |
| Hierarchy | Select | flat | flat/numbered/indented/arrow/breadcrumb |
| Max Depth | Input | (all) | Limit chapter nesting depth |
| Chapters | Input | (all) | e.g., "1-5", "1,3,7", "5-" |

### Tab 4: ⚙️ Advanced

Power user and batch processing settings.

| Setting | Type | Default | Notes |
|---------|------|---------|-------|
| Pronunciation | Input | (empty) | Path to dictionary file |
| Voice Mapping | Input | (empty) | Path to voice mapping JSON |
| Parallel Workers | Input | 5 | 1-15 concurrent tasks |
| Recursive Scan | Toggle | Off | Scan subdirectories |
| Skip Existing | Toggle | On | Skip already processed |
| Text Only | Toggle | Off | Export text, no audio |
| Retry Count | Input | 3 | TTS retry attempts |
| Retry Delay | Input | 3s | Delay between retries |

---

## FilePanel Updates

Move file-related actions to FilePanel:

```
┌─────────────────────────────────────┐
│ 📁 Files (3)           [📚] [📝]    │  ← Mode buttons (Books/Text)
├─────────────────────────────────────┤
│ [path input_______________] [📂]    │  ← Path + Browse button
├─────────────────────────────────────┤
│ ☑ Book One.epub                     │
│ ☐ Book Two.epub                     │
│ ☑ Book Three.epub                   │
├─────────────────────────────────────┤
│[All][None][⟳] [📋 Preview][📝 Export]│  ← Actions moved here
└─────────────────────────────────────┘
```

**Moved to FilePanel:**
- 📋 Preview Chapters - loads selected file's chapters
- 📝 Export & Edit - exports to text file

---

## Bottom Tabs (4 Tabs)

### Tab 1: 📋 Preview

Chapter editing before conversion.

```
┌─────────────────────────────────────┐
│ Preview: Book One.epub              │
├─────────────────────────────────────┤
│ [▶️ Start All]                      │  ← Start conversion
├─────────────────────────────────────┤
│ ☑ Chapter 1: Introduction     1.2k  │
│ ☑ Chapter 2: The Beginning    3.4k  │
│ ☐ Chapter 3: (Excluded)       0.5k  │
│ ☑ Chapter 4: The Journey      5.1k  │
├─────────────────────────────────────┤
│ [Space] Toggle [M] Merge [X] Delete │
└─────────────────────────────────────┘
```

### Tab 2: ▶️ Current

Detailed progress of active conversion.

```
┌─────────────────────────────────────┐
│ Current Job                         │
├─────────────────────────────────────┤
│ [▶️ Start] [⏸️ Pause] [⏹️ Stop]      │
├─────────────────────────────────────┤
│ 📖 Book One.epub                    │
│                                     │
│ Chapter 3/12: "The Journey"         │
│ ████████████████░░░░░░░░ 67%        │
│                                     │
│ Elapsed: 4:21  |  ETA: ~2:10        │
│                                     │
│ ✓ Ch.1  ✓ Ch.2  ● Ch.3  ○ Ch.4  ... │
│                                     │
│ Processing: "The sun rose slowly..."│
└─────────────────────────────────────┘
```

### Tab 3: 📊 Jobs

Combined queue and job history.

```
┌─────────────────────────────────────┐
│ Jobs                                │
├─────────────────────────────────────┤
│ [▶️ Start] [⏸️ Pause] [⏹️ Stop]      │
├─────────────────────────────────────┤
│ ● Book One.epub       Converting 67%│
│ ○ Book Two.epub       Pending       │
│ ○ Book Three.epub     Pending       │
│ ⏸ Book Four.epub      Paused @ Ch.5 │
│ ✗ Book Five.epub      Failed        │
│ ✓ Book Six.epub       Completed     │
├─────────────────────────────────────┤
│ [↑↓ Move] [R Resume] [X Delete]     │
└─────────────────────────────────────┘
```

**Status Icons:**
- ● In Progress (with percentage)
- ○ Pending
- ⏸ Paused (with chapter info)
- ✗ Failed
- ✓ Completed

### Tab 4: 📜 Log

Debug and verbose output.

```
┌─────────────────────────────────────┐
│ Log                    [Clear]      │
├─────────────────────────────────────┤
│ [12:34:01] Starting Book One.epub   │
│ [12:34:02] Detected 12 chapters     │
│ [12:34:03] Processing Chapter 1...  │
│ [12:34:15] Chapter 1 complete (12s) │
│ [12:34:16] Processing Chapter 2...  │
│ ...                                 │
└─────────────────────────────────────┘
```

---

## Controls Distribution

Transport controls appear in multiple locations for convenience:

| Location | Controls | Context |
|----------|----------|---------|
| 📋 Preview | [▶️ Start All] | Convert previewed chapters |
| ▶️ Current | [▶️][⏸️][⏹️] | Control + detailed view |
| 📊 Jobs | [▶️][⏸️][⏹️] | Control queue processing |

Keyboard shortcuts (global):
- `s` - Start conversion
- `Escape` - Stop conversion
- (Consider: `p` for pause?)

---

## Progressive Disclosure

Show sub-settings only when parent toggle is enabled:

```
OFF state:                      ON state:
┌─────────────────────┐         ┌─────────────────────┐
│ [ ] Normalize Audio │         │ [✓] Normalize Audio │
└─────────────────────┘         │     Target: -16 dBFS│
                                │     Method: [peak ▼]│
                                └─────────────────────┘
```

Settings with progressive disclosure:
- Trim Silence → Threshold, Max Duration
- Normalize → Target, Method

---

## Settings Profiles (Future)

Profile selector above tabs for quick switching:

```
┌─────────────────────────────────────┐
│ Profile: [Default ▼]    [💾 Save]   │
├─────────────────────────────────────┤
│ 🎙️ │ 🎵 │ 📖 │ ⚙️                   │
├─────────────────────────────────────┤
```

**Built-in profiles:**
- Default - Standard settings
- Quick Draft - Faster rate, less processing
- High Quality - Normalize, trim silence, careful pacing
- Accessibility - Slower rate, longer pauses

---

## Implementation Phases

### Phase 1: Structural Changes
- [ ] Create new SettingsPanel with TabbedContent (4 emoji tabs)
- [ ] Move 📋 Preview Chapters button to FilePanel
- [ ] Move 📝 Export & Edit button to FilePanel
- [ ] Move 🔊 Preview Voice to Voice tab (inline)
- [ ] Combine Queue + Jobs into single Jobs tab
- [ ] Add ▶️ Current tab for detailed progress
- [ ] Update tab labels to use emojis

### Phase 2: Settings Organization
- [ ] Implement 🎙️ Voice tab
- [ ] Implement 🎵 Audio tab
- [ ] Implement 📖 Chapters tab
- [ ] Implement ⚙️ Advanced tab
- [ ] Add transport controls to Current and Jobs tabs
- [ ] Add Start All to Preview tab

### Phase 3: Progressive Disclosure
- [ ] Trim Silence sub-settings (threshold, max duration)
- [ ] Normalize sub-settings (target, method)
- [ ] Smooth show/hide animations

### Phase 4: Polish
- [ ] Keyboard shortcuts for tab switching
- [ ] Context-sensitive button enabling/disabling
- [ ] Help text / tooltips for complex settings

### Phase 5: Profiles (Future)
- [ ] SettingsProfile dataclass
- [ ] Built-in profiles
- [ ] Profile selector UI
- [ ] Custom profile save/load

---

## Migration Notes

### Settings Mapping

| Old Location | New Location |
|--------------|--------------|
| Voice Selection | 🎙️ Voice tab |
| Rate/Volume | 🎙️ Voice tab |
| Preview Voice btn | 🎙️ Voice tab (inline) |
| Sentence/Paragraph Pause | 🎵 Audio tab |
| Trim Silence | 🎵 Audio tab |
| Normalize | 🎵 Audio tab |
| Detection/Hierarchy | 📖 Chapters tab |
| Chapter Selection | 📖 Chapters tab |
| Pronunciation/Voice Mapping | ⚙️ Advanced tab |
| Parallel Workers | ⚙️ Advanced tab |
| Recursive/Skip Existing | ⚙️ Advanced tab |
| Preview Chapters btn | FilePanel |
| Export & Edit btn | FilePanel |

### Bottom Tab Changes

| Old | New |
|-----|-----|
| Progress | ▶️ Current (enhanced) |
| Preview | 📋 Preview (unchanged) |
| Queue | *(merged into Jobs)* |
| Jobs | 📊 Jobs (queue + history) |
| Log | 📜 Log (unchanged) |

---

## Benefits

1. **Clearer Organization**: Related settings grouped in tabs
2. **Reduced Cognitive Load**: See only relevant options per tab
3. **Better Discoverability**: Emoji tabs are scannable
4. **Separation of Concerns**: Settings vs file actions vs conversion controls
5. **Fewer Tabs**: 5 → 4 bottom tabs by combining Queue/Jobs
6. **Contextual Actions**: Buttons near the things they operate on
7. **Future Extensibility**: Easy to add profiles, new tabs
