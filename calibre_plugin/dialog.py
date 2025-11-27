"""
Audiobookify Calibre Plugin - Dialogs

Provides conversion and preview dialogs.
"""

from qt.core import (
    Qt, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QProgressBar, QTextEdit, QGroupBox, QFormLayout,
    QSpinBox, QCheckBox, QLineEdit, QFileDialog, QListWidget,
    QListWidgetItem, QDialogButtonBox
)

from calibre.gui2 import error_dialog, info_dialog


# Default voice options
VOICES = [
    ('en-US-AndrewNeural', 'Andrew (US Male)'),
    ('en-US-JennyNeural', 'Jenny (US Female)'),
    ('en-GB-RyanNeural', 'Ryan (UK Male)'),
    ('en-GB-SoniaNeural', 'Sonia (UK Female)'),
    ('en-AU-WilliamNeural', 'William (AU Male)'),
    ('en-AU-NatashaNeural', 'Natasha (AU Female)'),
]


class ConversionDialog(QDialog):
    """Dialog for converting books to audiobooks."""
    
    def __init__(self, gui, db, book_ids):
        super().__init__(gui)
        self.gui = gui
        self.db = db.new_api
        self.book_ids = book_ids
        
        self.setWindowTitle('Convert to Audiobook')
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        self.load_book_info()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Book list
        books_group = QGroupBox('Books to Convert')
        books_layout = QVBoxLayout(books_group)
        self.book_list = QListWidget()
        books_layout.addWidget(self.book_list)
        layout.addWidget(books_group)
        
        # Settings
        settings_group = QGroupBox('Conversion Settings')
        settings_layout = QFormLayout(settings_group)
        
        # Voice selection
        self.voice_combo = QComboBox()
        for voice_id, voice_name in VOICES:
            self.voice_combo.addItem(voice_name, voice_id)
        settings_layout.addRow('Voice:', self.voice_combo)
        
        # Speech rate
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(-50, 50)
        self.rate_spin.setValue(0)
        self.rate_spin.setSuffix('%')
        settings_layout.addRow('Speech Rate:', self.rate_spin)
        
        # Volume adjustment
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(-50, 50)
        self.volume_spin.setValue(0)
        self.volume_spin.setSuffix('%')
        settings_layout.addRow('Volume:', self.volume_spin)
        
        # Normalization
        self.normalize_check = QCheckBox('Normalize audio levels')
        self.normalize_check.setChecked(True)
        settings_layout.addRow('', self.normalize_check)
        
        # Silence trimming
        self.trim_silence_check = QCheckBox('Trim excessive silence')
        self.trim_silence_check.setChecked(False)
        settings_layout.addRow('', self.trim_silence_check)
        
        # Output directory
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText('Default: Same as book location')
        output_layout.addWidget(self.output_edit)
        browse_btn = QPushButton('Browse...')
        browse_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(browse_btn)
        settings_layout.addRow('Output:', output_layout)
        
        layout.addWidget(settings_group)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Log output
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(100)
        self.log.setVisible(False)
        layout.addWidget(self.log)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.start_conversion)
        buttons.rejected.connect(self.reject)
        self.convert_btn = buttons.button(QDialogButtonBox.Ok)
        self.convert_btn.setText('Convert')
        layout.addWidget(buttons)
    
    def load_book_info(self):
        """Load information about selected books."""
        for book_id in self.book_ids:
            title = self.db.field_for('title', book_id)
            authors = self.db.field_for('authors', book_id)
            author_str = ', '.join(authors) if authors else 'Unknown'
            
            item = QListWidgetItem(f'{title} by {author_str}')
            item.setData(Qt.UserRole, book_id)
            self.book_list.addItem(item)
    
    def browse_output(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, 'Select Output Directory'
        )
        if directory:
            self.output_edit.setText(directory)
    
    def start_conversion(self):
        """Start the conversion process."""
        self.progress.setVisible(True)
        self.log.setVisible(True)
        self.convert_btn.setEnabled(False)
        
        voice = self.voice_combo.currentData()
        rate = self.rate_spin.value()
        volume = self.volume_spin.value()
        
        self.log.append(f'Starting conversion with voice: {voice}')
        self.log.append(f'Rate: {rate}%, Volume: {volume}%')
        
        # TODO: Implement actual conversion using a worker thread
        # For now, show a message
        info_dialog(
            self,
            'Conversion Started',
            'Audiobook conversion has been queued.\n\n'
            'Note: Full conversion requires the audiobookify package '
            'to be installed and configured.',
            show=True
        )
        
        self.accept()


class PreviewDialog(QDialog):
    """Dialog for previewing book chapters."""
    
    def __init__(self, gui, db, book_id):
        super().__init__(gui)
        self.gui = gui
        self.db = db.new_api
        self.book_id = book_id
        
        title = self.db.field_for('title', book_id)
        self.setWindowTitle(f'Chapter Preview - {title}')
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        self.setup_ui()
        self.load_chapters()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Info label
        self.info_label = QLabel('Detected chapters:')
        layout.addWidget(self.info_label)
        
        # Chapter list
        self.chapter_list = QListWidget()
        layout.addWidget(self.chapter_list)
        
        # Summary
        self.summary_label = QLabel('')
        layout.addWidget(self.summary_label)
        
        # Close button
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def load_chapters(self):
        """Load and display chapters from the book."""
        # Get the book format
        formats = self.db.formats(self.book_id)
        
        if not formats:
            self.info_label.setText('No formats available for this book.')
            return
        
        # Prefer EPUB, then MOBI, then AZW3
        format_priority = ['EPUB', 'MOBI', 'AZW3', 'AZW']
        selected_format = None
        for fmt in format_priority:
            if fmt in formats:
                selected_format = fmt
                break
        
        if not selected_format:
            selected_format = formats[0]
        
        self.info_label.setText(f'Chapters from {selected_format} format:')
        
        # TODO: Use audiobookify's chapter detection
        # For now, show placeholder
        self.chapter_list.addItem('Chapter 1: Introduction')
        self.chapter_list.addItem('Chapter 2: Getting Started')
        self.chapter_list.addItem('Chapter 3: Main Content')
        self.chapter_list.addItem('...')
        
        self.summary_label.setText(
            'Note: Install audiobookify for full chapter detection.'
        )
