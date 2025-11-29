"""
Audiobookify Calibre Plugin - User Interface

Provides the interface action for converting books to audiobooks.
"""

from qt.core import QMenu, QToolButton

from calibre.gui2.actions import InterfaceAction
from calibre.gui2 import error_dialog, info_dialog


class AudiobookifyInterface(InterfaceAction):
    """Interface action for Audiobookify plugin."""
    
    name = 'Audiobookify'
    action_spec = (
        'Audiobookify',  # Text for menu/toolbar
        None,  # Icon (None for default)
        'Convert selected books to M4B audiobooks',  # Tooltip
        None  # Keyboard shortcut
    )
    popup_type = QToolButton.MenuButtonPopup
    action_add_menu = True
    
    def genesis(self):
        """Setup the plugin action."""
        # Create the menu
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)
        
        # Add menu items
        self.create_menu_action(
            self.menu,
            'convert_to_audiobook',
            'Convert to Audiobook',
            description='Convert selected books to M4B audiobooks',
            triggered=self.convert_selected
        )
        
        self.create_menu_action(
            self.menu,
            'preview_chapters',
            'Preview Chapters',
            description='Preview chapter structure before conversion',
            triggered=self.preview_chapters
        )
        
        self.menu.addSeparator()
        
        self.create_menu_action(
            self.menu,
            'configure',
            'Configure',
            description='Configure Audiobookify settings',
            triggered=self.show_configuration
        )
        
        # Connect the main toolbar button
        self.qaction.triggered.connect(self.convert_selected)
    
    def convert_selected(self):
        """Convert selected books to audiobooks."""
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return error_dialog(
                self.gui,
                'No books selected',
                'Please select one or more books to convert to audiobooks.',
                show=True
            )
        
        # Get book IDs
        book_ids = list(map(self.gui.library_view.model().id, rows))
        
        # Show conversion dialog
        from calibre_plugins.audiobookify.dialog import ConversionDialog
        dialog = ConversionDialog(self.gui, self.gui.current_db, book_ids)
        dialog.exec_()
    
    def preview_chapters(self):
        """Preview chapter structure of selected books."""
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return error_dialog(
                self.gui,
                'No books selected',
                'Please select a book to preview chapters.',
                show=True
            )
        
        # Get first selected book
        book_id = self.gui.library_view.model().id(rows[0])
        
        # Show preview dialog
        from calibre_plugins.audiobookify.dialog import PreviewDialog
        dialog = PreviewDialog(self.gui, self.gui.current_db, book_id)
        dialog.exec_()
    
    def show_configuration(self):
        """Show the configuration dialog."""
        self.interface_action_base_plugin.do_user_config(self.gui)
