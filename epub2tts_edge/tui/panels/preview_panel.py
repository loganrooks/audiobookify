"""Preview panel for interactive chapter preview and editing."""

from copy import deepcopy
from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Click
from textual.message import Message
from textual.widgets import Button, Input, Label, ListItem, ListView, Static, Tab, Tabs

from ..models import ChapterPreviewState, MultiPreviewState, PreviewChapter


class ChapterPreviewItem(ListItem):
    """Interactive chapter item with selection for batch operations."""

    class Clicked(Message):
        """Message sent when chapter item is clicked with modifier info."""

        def __init__(self, item: "ChapterPreviewItem", shift: bool) -> None:
            super().__init__()
            self.item = item
            self.shift = shift

    def __init__(self, chapter: PreviewChapter, index: int) -> None:
        super().__init__()
        self.chapter = chapter
        self.index = index
        self.is_selected = False  # For batch operations (merge/delete)

    def compose(self) -> ComposeResult:
        yield Label(self._build_label())

    def _build_label(self) -> str:
        """Build the display label for this chapter."""
        # Checkbox for batch selection (editing only, not export)
        checkbox = "☑" if self.is_selected else "☐"

        indent = "  " * max(0, self.chapter.level - 1)

        # Truncate title if needed
        title = self.chapter.title
        if len(title) > 50:
            title = title[:47] + "..."

        # Stats
        stats = f"({self.chapter.word_count:,}w)"

        return f"{checkbox} {indent}{title} {stats}"

    def on_click(self, event: Click) -> None:
        """Handle click - pass shift state to parent PreviewPanel.

        Note: We don't stop the event so ListView can update highlighting first.
        The actual selection logic is handled by PreviewPanel._on_chapter_tree_click.
        """
        # Don't call event.stop() - let click bubble to PreviewPanel
        pass

    def toggle_selection(self) -> None:
        """Toggle selection for batch operations."""
        self.is_selected = not self.is_selected
        self.refresh_display()
        # Update CSS class for visual feedback
        if self.is_selected:
            self.add_class("selected")
        else:
            self.remove_class("selected")

    def set_selected(self, selected: bool) -> None:
        """Set selection state directly (for range selection)."""
        if self.is_selected != selected:
            self.is_selected = selected
            self.refresh_display()
            if self.is_selected:
                self.add_class("selected")
            else:
                self.remove_class("selected")

    def refresh_display(self) -> None:
        """Refresh the display."""
        self.query_one(Label).update(self._build_label())


class PreviewPanel(Vertical):
    """Panel for interactive chapter preview and editing."""

    DEFAULT_CSS = """
    PreviewPanel {
        height: 100%;
    }

    PreviewPanel > #preview-header {
        height: auto;
        padding: 0 1;
        background: $surface-darken-1;
    }

    PreviewPanel > #preview-tabs {
        height: auto;
        dock: top;
        background: $surface-darken-2;
        display: none;
    }

    PreviewPanel > #preview-tabs.visible {
        display: block;
    }

    PreviewPanel > #preview-tabs Tab {
        min-width: 10;
        padding: 0 1;
    }

    PreviewPanel > #preview-tabs Tab.-active {
        background: $primary;
    }

    PreviewPanel > #preview-header > Label {
        margin-right: 1;
    }

    PreviewPanel > #preview-header > #book-title {
        width: 1fr;
    }

    PreviewPanel > #preview-header > #chapter-stats {
        color: $text-muted;
    }

    PreviewPanel > #chapter-tree {
        height: 1fr;
        border: solid $primary-darken-2;
        margin: 0;
    }

    PreviewPanel > #content-preview {
        height: auto;
        max-height: 8;
        background: $surface-darken-2;
        padding: 0 1;
        margin: 0;
        display: none;
    }

    PreviewPanel > #content-preview.visible {
        display: block;
    }

    PreviewPanel > #preview-actions {
        height: auto;
        padding: 0;
        margin-top: 0;
    }

    PreviewPanel > #preview-actions > Button {
        min-width: 6;
        height: auto;
        padding: 0;
        margin: 0 1 0 0;
    }

    PreviewPanel > #preview-actions > Button.approve {
        background: $success-darken-1;
    }

    PreviewPanel > #no-preview {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    PreviewPanel > #preview-instructions {
        height: auto;
        padding: 0 1;
        color: $text-muted;
        text-style: italic;
        display: none;
    }

    PreviewPanel > #preview-instructions.visible {
        display: block;
    }

    ChapterPreviewItem {
        height: auto;
        padding: 0 1;
    }

    ChapterPreviewItem.selected {
        background: $primary-darken-2;
    }

    ChapterPreviewItem.selected Label {
        color: $text;
        text-style: bold;
    }
    """

    MAX_UNDO_STACK = 20  # Limit undo history to prevent memory issues

    class ApproveAndStart(Message):
        """Message sent when user clicks Approve & Start."""

        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.preview_state: ChapterPreviewState | None = None
        self._undo_stack: list[list[PreviewChapter]] = []  # Stack of chapter snapshots
        self._last_selected_index: int | None = None  # Anchor for range selection
        self._toggle_mode: bool = False  # Toggle mode (V key)
        # Multi-file preview support
        self._multi_state = MultiPreviewState()
        self._undo_stacks: dict[Path, list[list[PreviewChapter]]] = {}  # Per-file undo

    def compose(self) -> ComposeResult:
        # Header with book info
        with Horizontal(id="preview-header"):
            yield Label("📖", id="book-icon")
            yield Label("Select a file and click 'Preview Chapters'", id="book-title")
            yield Label("", id="chapter-stats")

        # Tab bar for multiple files (hidden when empty)
        yield Tabs(id="preview-tabs")

        # Placeholder when no preview
        yield Static(
            "Select a file and press 'Preview Chapters' to see chapter breakdown",
            id="no-preview",
        )

        # Instruction label for editing - CLEAR that Start processes ALL
        yield Label(
            "📝 V=toggle mode, Space=select, M=merge, X=delete, U=undo",
            id="preview-instructions",
        )

        # Chapter tree (hidden initially)
        yield ListView(id="chapter-tree")

        # Content preview pane (expandable)
        yield Static("", id="content-preview")

        # Action buttons
        with Horizontal(id="preview-actions"):
            yield Button("Select All", id="preview-select-all")
            yield Button("Select None", id="preview-select-none")
            yield Button("✏️ Edit", id="preview-edit", disabled=True)
            yield Button("🔗 Merge", id="preview-merge", disabled=True)
            yield Button("🗑️ Delete", id="preview-delete", disabled=True)
            yield Button("↩️ Undo", id="preview-undo", disabled=True)
            yield Button("▶️ Start All", id="preview-approve", classes="approve", disabled=True)

    def on_mount(self) -> None:
        """Hide the chapter tree initially."""
        self.query_one("#chapter-tree").display = False

    def load_chapters(
        self,
        source_file: Path,
        chapters: list[PreviewChapter],
        detection_method: str,
        book_title: str = "",
        book_author: str = "",
    ) -> None:
        """Load chapters into the preview panel.

        Adds or updates a tab for the file and displays its chapters.
        """
        # Save current undo stack before switching
        if self._multi_state.active_file and self._undo_stack:
            self._undo_stacks[self._multi_state.active_file] = self._undo_stack.copy()

        # Add to multi-state
        added = self._multi_state.add_preview(
            source_file=source_file,
            chapters=chapters,
            detection_method=detection_method,
            book_title=book_title,
            book_author=book_author,
        )

        if not added:
            # At max tabs - notify user
            self.notify("Maximum tabs open. Close a tab first.", severity="warning")
            return

        # Get the active state
        self.preview_state = self._multi_state.active_state

        # Restore or create undo stack for this file
        self._undo_stack = self._undo_stacks.get(source_file, [])

        # Update tabs
        self._update_tabs()

        # Update header
        book_name = source_file.stem
        if len(book_name) > 40:
            book_name = book_name[:37] + "..."
        self.query_one("#book-title", Label).update(book_name)

        # Update stats
        total_chapters = len(chapters)
        total_words = sum(c.word_count for c in chapters)
        self.query_one("#chapter-stats", Label).update(f"{total_chapters} ch, {total_words:,}w")

        # Hide placeholder, show tree and instructions
        self.query_one("#no-preview").display = False
        self.query_one("#preview-instructions").add_class("visible")
        chapter_tree = self.query_one("#chapter-tree", ListView)
        chapter_tree.display = True

        # Populate chapter list
        chapter_tree.clear()
        for i, chapter in enumerate(chapters):
            chapter_tree.append(ChapterPreviewItem(chapter, i))

        # Enable approve button, update other buttons
        self.query_one("#preview-approve", Button).disabled = False
        self._update_action_buttons()

    def clear_preview(self) -> None:
        """Clear the current preview (all tabs)."""
        self.preview_state = None
        self._undo_stack.clear()
        self._multi_state.close_all()
        self._undo_stacks.clear()

        # Hide tabs
        tabs = self.query_one("#preview-tabs", Tabs)
        tabs.clear()
        tabs.remove_class("visible")

        self.query_one("#book-title", Label).update("Select a file and click 'Preview Chapters'")
        self.query_one("#chapter-stats", Label).update("")
        self.query_one("#no-preview").display = True
        self.query_one("#preview-instructions").remove_class("visible")
        self.query_one("#chapter-tree").display = False
        self.query_one("#chapter-tree", ListView).clear()
        self.query_one("#content-preview").display = False
        self.query_one("#preview-approve", Button).disabled = True
        self.query_one("#preview-undo", Button).disabled = True
        self.query_one("#preview-merge", Button).disabled = True
        self.query_one("#preview-delete", Button).disabled = True
        self.query_one("#preview-edit", Button).disabled = True

    def _update_tabs(self) -> None:
        """Update the tabs widget to reflect current state."""
        tabs = self.query_one("#preview-tabs", Tabs)

        # Get current open files
        open_files = self._multi_state.get_open_files()

        if len(open_files) <= 1:
            # Hide tabs when only 0-1 files
            tabs.clear()
            tabs.remove_class("visible")
            return

        # Show tabs
        tabs.add_class("visible")

        # Build new tab set
        existing_ids = {tab.id for tab in tabs.query(Tab)}
        active_file = self._multi_state.active_file

        for file_path in open_files:
            tab_id = self._path_to_tab_id(file_path)
            label = self._multi_state.get_tab_label(file_path)

            # Add indicator for modified state
            if self._multi_state.is_modified(file_path):
                label = f"* {label}"

            if tab_id not in existing_ids:
                # Add new tab
                tabs.add_tab(Tab(label, id=tab_id))
            else:
                # Update existing tab label
                for tab in tabs.query(Tab):
                    if tab.id == tab_id:
                        tab.label = label
                        break

        # Remove tabs for closed files
        current_tab_ids = {self._path_to_tab_id(f) for f in open_files}
        for tab in tabs.query(Tab):
            if tab.id not in current_tab_ids:
                tab.remove()

        # Activate the correct tab
        if active_file:
            tabs.active = self._path_to_tab_id(active_file)

    def _path_to_tab_id(self, file_path: Path) -> str:
        """Convert a file path to a tab ID."""
        # Use hash of path for unique ID
        return f"tab-{hash(str(file_path)) % 10000000:07d}"

    def _tab_id_to_path(self, tab_id: str) -> Path | None:
        """Convert a tab ID back to file path."""
        for file_path in self._multi_state.get_open_files():
            if self._path_to_tab_id(file_path) == tab_id:
                return file_path
        return None

    def _switch_to_file(self, file_path: Path) -> None:
        """Switch display to a different file's preview."""
        if not self._multi_state.has_file(file_path):
            return

        # Save current undo stack
        if self._multi_state.active_file:
            self._undo_stacks[self._multi_state.active_file] = self._undo_stack.copy()

        # Switch in multi-state
        self._multi_state.switch_to(file_path)
        self.preview_state = self._multi_state.active_state

        # Restore undo stack for this file
        self._undo_stack = self._undo_stacks.get(file_path, [])

        if not self.preview_state:
            return

        # Update header
        book_name = file_path.stem
        if len(book_name) > 40:
            book_name = book_name[:37] + "..."
        self.query_one("#book-title", Label).update(book_name)

        # Update stats
        chapters = self.preview_state.chapters
        total_chapters = len(chapters)
        total_words = sum(c.word_count for c in chapters)
        self.query_one("#chapter-stats", Label).update(f"{total_chapters} ch, {total_words:,}w")

        # Rebuild chapter tree
        chapter_tree = self.query_one("#chapter-tree", ListView)
        chapter_tree.clear()
        for i, chapter in enumerate(chapters):
            chapter_tree.append(ChapterPreviewItem(chapter, i))

        # Reset selection anchor
        self._last_selected_index = None

        # Update buttons
        self._update_action_buttons()

    def close_tab(self, file_path: Path | None = None) -> None:
        """Close a preview tab.

        Args:
            file_path: Path to close, or None to close active tab
        """
        if file_path is None:
            file_path = self._multi_state.active_file

        if file_path is None:
            return

        # Remove undo stack for this file
        self._undo_stacks.pop(file_path, None)

        # Close in multi-state
        new_active = self._multi_state.close_tab(file_path)

        if new_active is None:
            # No more tabs - clear everything
            self.clear_preview()
        else:
            # Switch to new active file
            self._switch_to_file(new_active)
            self._update_tabs()

    @on(Tabs.TabActivated, "#preview-tabs")
    def _on_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab switch."""
        if event.tab is None:
            return

        file_path = self._tab_id_to_path(event.tab.id)
        if file_path and file_path != self._multi_state.active_file:
            self._switch_to_file(file_path)

    @property
    def open_file_count(self) -> int:
        """Get the number of open file previews."""
        return self._multi_state.file_count

    @property
    def open_files(self) -> list[Path]:
        """Get list of open file paths."""
        return self._multi_state.get_open_files()

    def has_chapters(self) -> bool:
        """Check if there are chapters loaded."""
        return self.preview_state is not None and len(self.preview_state.chapters) > 0

    def get_included_chapters(self) -> list[PreviewChapter]:
        """Get chapters that are included."""
        if not self.preview_state:
            return []
        return self.preview_state.get_included_chapters()

    def select_all(self) -> None:
        """Select all chapters for batch operations."""
        if not self.preview_state:
            return
        for item in self.query(ChapterPreviewItem):
            if not item.is_selected:
                item.is_selected = True
                item.add_class("selected")
                item.refresh_display()
        self._update_stats()
        self._update_action_buttons()

    def select_none(self) -> None:
        """Deselect all chapters."""
        if not self.preview_state:
            return
        self._clear_all_selections()
        self._update_stats()
        self._update_action_buttons()

    def toggle_content_preview(self) -> None:
        """Toggle the content preview pane."""
        content_preview = self.query_one("#content-preview", Static)
        chapter_tree = self.query_one("#chapter-tree", ListView)

        if content_preview.display:
            content_preview.display = False
            content_preview.remove_class("visible")
        else:
            # Get selected chapter
            if chapter_tree.highlighted_child:
                item = chapter_tree.highlighted_child
                if isinstance(item, ChapterPreviewItem):
                    preview_text = item.chapter.content_preview or "(No content preview available)"
                    content_preview.update(f"Preview: {preview_text}")
                    content_preview.display = True
                    content_preview.add_class("visible")

    def _update_stats(self) -> None:
        """Update the stats display."""
        if not self.preview_state:
            return
        total_chapters = len(self.preview_state.chapters)
        total_words = sum(c.word_count for c in self.preview_state.chapters)
        selected_count = len(self._get_selected_items())

        # Show total chapters (what will be processed) and edit selection
        if selected_count > 0:
            self.query_one("#chapter-stats", Label).update(
                f"{total_chapters} chapters, {total_words:,}w | {selected_count} selected for edit"
            )
        else:
            self.query_one("#chapter-stats", Label).update(
                f"{total_chapters} chapters, {total_words:,}w"
            )

    def _enter_toggle_mode(self) -> None:
        """Enter visual toggle mode."""
        self._toggle_mode = True
        # Toggle the currently highlighted item to start
        highlighted = self._get_highlighted_item()
        if highlighted:
            highlighted.toggle_selection()
            self._update_stats()
            self._update_action_buttons()
        # Update instructions to show visual mode
        self._update_toggle_mode_instructions()

    def _exit_toggle_mode(self) -> None:
        """Exit visual toggle mode."""
        self._toggle_mode = False
        # Update instructions back to normal
        self._update_toggle_mode_instructions()

    def _update_toggle_mode_instructions(self) -> None:
        """Update instructions based on visual mode state."""
        instructions = self.query_one("#preview-instructions", Label)
        if self._toggle_mode:
            instructions.update("🔵 TOGGLE MODE: ↑↓=toggle items, V/Esc=exit | M=merge, X=delete")
        else:
            instructions.update("📝 V=toggle mode, Space=select, M=merge, X=delete, U=undo")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "preview-select-all":
            self.select_all()
        elif event.button.id == "preview-select-none":
            self.select_none()
        elif event.button.id == "preview-edit":
            self.edit_highlighted_title()
        elif event.button.id == "preview-merge":
            self.batch_merge()
        elif event.button.id == "preview-delete":
            self.batch_delete()
        elif event.button.id == "preview-undo":
            self.undo()
        elif event.button.id == "preview-approve":
            # Bubble up to app
            self.post_message(self.ApproveAndStart())

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle ListView selection - only for keyboard navigation (Enter key).

        Note: Click-based selection is handled by on_chapter_preview_item_clicked
        to properly detect shift modifier for range selection.
        """
        # ListView.Selected is triggered by Enter key on highlighted item
        # We still want Enter to toggle selection
        if isinstance(event.item, ChapterPreviewItem):
            event.item.toggle_selection()
            self._last_selected_index = event.item.index
            self._update_stats()
            self._update_action_buttons()

    def _handle_item_click(self, item: ChapterPreviewItem, shift: bool) -> None:
        """Handle chapter item click with shift detection for range selection.

        Called directly from ChapterPreviewItem.on_click to avoid message bubbling issues.

        Args:
            item: The clicked chapter item
            shift: True if shift key was held during click
        """
        clicked_index = item.index

        if shift and self._last_selected_index is not None:
            # Range selection: select all items from anchor to clicked
            self._select_range(self._last_selected_index, clicked_index)
        else:
            # Regular click: toggle selection, update anchor point
            item.toggle_selection()
            self._last_selected_index = clicked_index

        self._update_stats()
        self._update_action_buttons()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Update buttons when highlight changes, and handle visual mode."""
        self._update_action_buttons()

        # In visual mode, toggle items as user navigates
        if self._toggle_mode and isinstance(event.item, ChapterPreviewItem):
            event.item.toggle_selection()
            self._update_stats()
            self._update_action_buttons()

    @on(Click, "#chapter-tree")
    def _on_chapter_tree_click(self, event: Click) -> None:
        """Handle clicks on the chapter tree ListView.

        This captures clicks at the ListView level since ListItem.on_click
        doesn't reliably fire in Textual. By the time this handler runs,
        ListView has already updated highlighted_child.

        Supports both Shift+Click and Ctrl+Click for range selection since
        some terminals intercept Shift+Click for text selection.
        """
        # Get the currently highlighted item (which was just clicked)
        chapter_tree = self.query_one("#chapter-tree", ListView)
        highlighted = chapter_tree.highlighted_child

        if not isinstance(highlighted, ChapterPreviewItem):
            return

        # Check for range selection modifier (shift OR ctrl, since terminals may intercept shift)
        range_modifier = event.shift or event.ctrl

        # Handle range selection with shift or ctrl
        if range_modifier and self._last_selected_index is not None:
            self._select_range(self._last_selected_index, highlighted.index)
        else:
            # Regular click: toggle selection and set anchor
            highlighted.toggle_selection()
            self._last_selected_index = highlighted.index

        self._update_stats()
        self._update_action_buttons()

    def _get_highlighted_item(self) -> ChapterPreviewItem | None:
        """Get the currently highlighted chapter item."""
        chapter_tree = self.query_one("#chapter-tree", ListView)
        if chapter_tree.highlighted_child:
            item = chapter_tree.highlighted_child
            if isinstance(item, ChapterPreviewItem):
                return item
        return None

    def _get_next_item(self, current: ChapterPreviewItem) -> ChapterPreviewItem | None:
        """Get the chapter item after the current one."""
        items = list(self.query(ChapterPreviewItem))
        try:
            idx = items.index(current)
            if idx + 1 < len(items):
                return items[idx + 1]
        except ValueError:
            pass
        return None

    def _update_action_buttons(self) -> None:
        """Update merge/delete/undo/edit button states based on selection."""
        selected_count = len(self._get_selected_items())
        selected_indices = self._get_selected_indices()
        highlighted = self._get_highlighted_item()

        merge_btn = self.query_one("#preview-merge", Button)
        delete_btn = self.query_one("#preview-delete", Button)
        undo_btn = self.query_one("#preview-undo", Button)
        edit_btn = self.query_one("#preview-edit", Button)

        # Update button labels with selection count
        if selected_count > 0:
            delete_btn.label = f"🗑️ Delete ({selected_count})"
        else:
            delete_btn.label = "🗑️ Delete"

        if selected_count >= 2:
            merge_btn.label = f"🔗 Merge ({selected_count})"
        else:
            merge_btn.label = "🔗 Merge"

        # Enable delete if at least one selected
        delete_btn.disabled = selected_count < 1

        # Enable merge if 2+ adjacent chapters selected
        if selected_count >= 2:
            # Check if adjacent
            selected_indices.sort()
            is_adjacent = all(
                selected_indices[i + 1] - selected_indices[i] == 1
                for i in range(len(selected_indices) - 1)
            )
            merge_btn.disabled = not is_adjacent
        else:
            merge_btn.disabled = True

        # Undo is enabled if there's something in the stack
        undo_btn.disabled = len(self._undo_stack) == 0

        # Edit is enabled if there's a highlighted item
        edit_btn.disabled = highlighted is None

    def _save_undo_state(self) -> None:
        """Save current chapters to undo stack (deep copy)."""
        if not self.preview_state:
            return

        snapshot = deepcopy(self.preview_state.chapters)
        self._undo_stack.append(snapshot)

        # Enforce stack size limit to prevent memory issues
        while len(self._undo_stack) > self.MAX_UNDO_STACK:
            self._undo_stack.pop(0)

    def _rebuild_chapter_list(self) -> None:
        """Rebuild the ListView from current chapters."""
        if not self.preview_state:
            return

        chapter_tree = self.query_one("#chapter-tree", ListView)
        chapter_tree.clear()

        for i, chapter in enumerate(self.preview_state.chapters):
            chapter_tree.append(ChapterPreviewItem(chapter, i))

    def merge_with_next(self) -> None:
        """Merge highlighted chapter with the one below it - visually combines them."""
        if not self.preview_state:
            return

        target_item = self._get_highlighted_item()
        if not target_item:
            self.app.notify("Highlight a chapter first", severity="warning")
            return

        next_item = self._get_next_item(target_item)
        if not next_item:
            self.app.notify("No chapter below to merge with", severity="warning")
            return

        # Save state for undo BEFORE making changes
        self._save_undo_state()

        target = target_item.chapter
        source = next_item.chapter

        # Combine titles
        target.title = f"{target.title} + {source.title}"

        # Merge content
        merged_content = []
        if target.original_content:
            merged_content.append(target.original_content)
        if source.original_content:
            merged_content.append(source.original_content)
        target.original_content = "\n\n".join(merged_content)

        # Combine stats
        target.word_count += source.word_count
        target.paragraph_count += source.paragraph_count

        # Remove the source chapter from the list
        self.preview_state.chapters.remove(source)

        # Rebuild the list view
        self._rebuild_chapter_list()

        # Mark state as modified
        self.preview_state.modified = True

        self._update_stats()
        self._update_action_buttons()
        self.app.notify(f"Merged: {target.title}", severity="information")

    def delete_chapter(self) -> None:
        """Delete the highlighted chapter from the list."""
        if not self.preview_state:
            return

        item = self._get_highlighted_item()
        if not item:
            self.app.notify("Highlight a chapter first", severity="warning")
            return

        # Prevent deleting the last chapter
        if len(self.preview_state.chapters) <= 1:
            self.app.notify("Cannot delete the last chapter", severity="error")
            return

        # Save state for undo BEFORE making changes
        self._save_undo_state()

        chapter = item.chapter

        # Remove from chapters list
        self.preview_state.chapters.remove(chapter)

        # Rebuild the list view
        self._rebuild_chapter_list()

        # Mark state as modified
        self.preview_state.modified = True

        self._update_stats()
        self._update_action_buttons()
        self.app.notify(f"Deleted: {chapter.title}", severity="information")

    def undo(self) -> None:
        """Undo the last merge or delete operation."""
        if not self.preview_state or not self._undo_stack:
            return

        # Restore chapters from undo stack
        self.preview_state.chapters = self._undo_stack.pop()

        # Rebuild the list view
        self._rebuild_chapter_list()

        self._update_stats()
        self._update_action_buttons()
        self.app.notify("Undo successful", severity="information")

    def _get_selected_items(self) -> list["ChapterPreviewItem"]:
        """Get all selected chapter items in order."""
        list_view = self.query_one("#chapter-tree", ListView)
        selected = []
        for item in list_view.children:
            if isinstance(item, ChapterPreviewItem) and item.is_selected:
                selected.append(item)
        return selected

    def _get_selected_indices(self) -> list[int]:
        """Get indices of all selected items."""
        list_view = self.query_one("#chapter-tree", ListView)
        indices = []
        for i, item in enumerate(list_view.children):
            if isinstance(item, ChapterPreviewItem) and item.is_selected:
                indices.append(i)
        return indices

    def _clear_all_selections(self) -> None:
        """Clear all selections."""
        list_view = self.query_one("#chapter-tree", ListView)
        for item in list_view.children:
            if isinstance(item, ChapterPreviewItem) and item.is_selected:
                item.is_selected = False
                item.remove_class("selected")
                item.refresh_display()

    def _select_range(self, start_index: int, end_index: int) -> None:
        """Select all chapters between start and end indices (inclusive).

        Args:
            start_index: Starting index (anchor point)
            end_index: Ending index (clicked item)
        """
        # Ensure start <= end
        if start_index > end_index:
            start_index, end_index = end_index, start_index

        items = list(self.query(ChapterPreviewItem))
        for item in items:
            if start_index <= item.index <= end_index:
                item.set_selected(True)

    def batch_delete(self) -> None:
        """Delete all selected chapters at once."""
        if not self.preview_state:
            return

        selected = self._get_selected_items()
        if not selected:
            self.app.notify("Select chapters first (click to select)", severity="warning")
            return

        # Prevent deleting all chapters
        remaining = len(self.preview_state.chapters) - len(selected)
        if remaining < 1:
            self.app.notify("Cannot delete all chapters. Keep at least one.", severity="error")
            return

        # Save state for undo
        self._save_undo_state()

        # Get chapters to delete
        chapters_to_delete = [item.chapter for item in selected]
        deleted_count = len(chapters_to_delete)

        # Remove chapters
        for chapter in chapters_to_delete:
            self.preview_state.chapters.remove(chapter)

        # Rebuild UI
        self._rebuild_chapter_list()
        self.preview_state.modified = True

        self._update_stats()
        self._update_action_buttons()
        self.app.notify(f"Deleted {deleted_count} chapter(s)", severity="information")

    def batch_merge(self) -> None:
        """Merge all selected chapters if they are adjacent."""
        if not self.preview_state:
            return

        indices = self._get_selected_indices()
        if len(indices) < 2:
            self.app.notify("Select at least 2 adjacent chapters to merge", severity="warning")
            return

        # Check if indices are consecutive (adjacent)
        indices.sort()
        is_adjacent = all(indices[i + 1] - indices[i] == 1 for i in range(len(indices) - 1))

        if not is_adjacent:
            self.app.notify("Selected chapters must be adjacent to merge", severity="error")
            return

        # Save state for undo
        self._save_undo_state()

        # Get chapters to merge (in order)
        chapters = [self.preview_state.chapters[i] for i in indices]
        target = chapters[0]

        # Combine titles
        titles = [c.title for c in chapters]
        target.title = " + ".join(titles)

        # Merge content
        contents = []
        for c in chapters:
            if c.original_content:
                contents.append(c.original_content)
        target.original_content = "\n\n".join(contents)

        # Sum stats
        target.word_count = sum(c.word_count for c in chapters)
        target.paragraph_count = sum(c.paragraph_count for c in chapters)

        # Remove merged chapters (all except first)
        for chapter in chapters[1:]:
            self.preview_state.chapters.remove(chapter)

        # Rebuild UI
        self._rebuild_chapter_list()
        self.preview_state.modified = True

        self._update_stats()
        self._update_action_buttons()
        self.app.notify(
            f"Merged {len(chapters)} chapters into '{target.title[:30]}...'",
            severity="information",
        )

    def edit_highlighted_title(self) -> None:
        """Edit the title of the highlighted chapter using an inline Input."""
        if not self.preview_state:
            return

        highlighted = self._get_highlighted_item()
        if not highlighted:
            self.app.notify("Highlight a chapter to edit its title", severity="warning")
            return

        # Create an Input widget
        input_widget = Input(
            value=highlighted.chapter.title,
            id="title-edit-input",
            placeholder="Enter new title...",
        )
        input_widget.chapter_item = highlighted  # Store reference to item

        # Replace the label temporarily with input
        label = highlighted.query_one(Label)
        label.display = False
        highlighted.mount(input_widget)
        input_widget.focus()

    def _finish_title_edit(self, input_widget, new_title: str) -> None:
        """Complete the title edit operation."""
        chapter_item = input_widget.chapter_item

        if new_title.strip():
            # Save undo state
            self._save_undo_state()

            # Update the chapter title
            chapter_item.chapter.title = new_title.strip()
            self.preview_state.modified = True

            self.app.notify(f"Renamed to: {new_title[:30]}...", severity="information")

        # Remove input and restore label
        input_widget.remove()
        label = chapter_item.query_one(Label)
        label.display = True
        chapter_item.refresh_display()

    def on_input_submitted(self, event) -> None:
        """Handle Enter key in title edit input."""
        if event.input.id == "title-edit-input":
            self._finish_title_edit(event.input, event.value)

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts for chapter editing.

        Supports:
        - e/E: Edit chapter title
        - Escape: Cancel title edit / exit visual mode
        - Space: Toggle selection on current item
        - V: Visual toggle mode (toggle selection while navigating)
        """
        if event.key == "e" or event.key == "E":
            # Edit highlighted chapter title
            self.edit_highlighted_title()
            event.stop()
        elif event.key == "escape":
            # Exit visual mode or cancel title edit
            if self._toggle_mode:
                self._exit_toggle_mode()
                event.stop()
            else:
                try:
                    input_widget = self.query_one("#title-edit-input", Input)
                    chapter_item = input_widget.chapter_item
                    input_widget.remove()
                    label = chapter_item.query_one(Label)
                    label.display = True
                    event.stop()
                except Exception:
                    pass  # No edit in progress
        elif event.key == "v" or event.key == "V":
            # Toggle visual mode
            if self._toggle_mode:
                self._exit_toggle_mode()
            else:
                self._enter_toggle_mode()
            event.stop()
        elif event.key == "space":
            # Space toggles selection on highlighted item
            highlighted = self._get_highlighted_item()
            if highlighted:
                highlighted.toggle_selection()
                self._last_selected_index = highlighted.index
                self._update_stats()
                self._update_action_buttons()
                event.stop()  # No edit in progress
