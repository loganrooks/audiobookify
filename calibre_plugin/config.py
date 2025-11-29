"""
Audiobookify Calibre Plugin - Configuration

Provides configuration widget and settings management.
"""

from qt.core import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSpinBox, QCheckBox, QLineEdit, QGroupBox, QFormLayout,
    QPushButton, QFileDialog
)

from calibre.utils.config import JSONConfig

# Plugin configuration
prefs = JSONConfig('plugins/audiobookify')

# Default settings
prefs.defaults['default_voice'] = 'en-US-AndrewNeural'
prefs.defaults['default_rate'] = 0
prefs.defaults['default_volume'] = 0
prefs.defaults['normalize_audio'] = True
prefs.defaults['trim_silence'] = False
prefs.defaults['silence_threshold'] = -40
prefs.defaults['max_silence'] = 2000
prefs.defaults['output_directory'] = ''
prefs.defaults['pronunciation_dict'] = ''


# Voice options
VOICES = [
    ('en-US-AndrewNeural', 'Andrew (US Male)'),
    ('en-US-JennyNeural', 'Jenny (US Female)'),
    ('en-US-GuyNeural', 'Guy (US Male)'),
    ('en-US-AriaNeural', 'Aria (US Female)'),
    ('en-GB-RyanNeural', 'Ryan (UK Male)'),
    ('en-GB-SoniaNeural', 'Sonia (UK Female)'),
    ('en-GB-LibbyNeural', 'Libby (UK Female)'),
    ('en-AU-WilliamNeural', 'William (AU Male)'),
    ('en-AU-NatashaNeural', 'Natasha (AU Female)'),
    ('en-CA-LiamNeural', 'Liam (CA Male)'),
    ('en-CA-ClaraNeural', 'Clara (CA Female)'),
]


class ConfigWidget(QWidget):
    """Configuration widget for Audiobookify plugin."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the configuration UI."""
        layout = QVBoxLayout(self)
        
        # Voice settings
        voice_group = QGroupBox('Voice Settings')
        voice_layout = QFormLayout(voice_group)
        
        self.voice_combo = QComboBox()
        for voice_id, voice_name in VOICES:
            self.voice_combo.addItem(voice_name, voice_id)
        voice_layout.addRow('Default Voice:', self.voice_combo)
        
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(-50, 50)
        self.rate_spin.setSuffix('%')
        voice_layout.addRow('Default Rate:', self.rate_spin)
        
        self.volume_spin = QSpinBox()
        self.volume_spin.setRange(-50, 50)
        self.volume_spin.setSuffix('%')
        voice_layout.addRow('Default Volume:', self.volume_spin)
        
        layout.addWidget(voice_group)
        
        # Audio settings
        audio_group = QGroupBox('Audio Processing')
        audio_layout = QFormLayout(audio_group)
        
        self.normalize_check = QCheckBox('Normalize audio levels')
        audio_layout.addRow('', self.normalize_check)
        
        self.trim_silence_check = QCheckBox('Trim excessive silence')
        audio_layout.addRow('', self.trim_silence_check)
        
        self.silence_thresh_spin = QSpinBox()
        self.silence_thresh_spin.setRange(-60, -20)
        self.silence_thresh_spin.setSuffix(' dBFS')
        audio_layout.addRow('Silence Threshold:', self.silence_thresh_spin)
        
        self.max_silence_spin = QSpinBox()
        self.max_silence_spin.setRange(500, 5000)
        self.max_silence_spin.setSuffix(' ms')
        audio_layout.addRow('Max Silence:', self.max_silence_spin)
        
        layout.addWidget(audio_group)
        
        # Output settings
        output_group = QGroupBox('Output Settings')
        output_layout = QFormLayout(output_group)
        
        output_dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText('Default: Same as book location')
        output_dir_layout.addWidget(self.output_dir_edit)
        browse_btn = QPushButton('Browse...')
        browse_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(browse_btn)
        output_layout.addRow('Output Directory:', output_dir_layout)
        
        pron_layout = QHBoxLayout()
        self.pron_dict_edit = QLineEdit()
        self.pron_dict_edit.setPlaceholderText('Optional pronunciation dictionary')
        pron_layout.addWidget(self.pron_dict_edit)
        pron_btn = QPushButton('Browse...')
        pron_btn.clicked.connect(self.browse_pron_dict)
        pron_layout.addWidget(pron_btn)
        output_layout.addRow('Pronunciation Dict:', pron_layout)
        
        layout.addWidget(output_group)
        
        # Stretch
        layout.addStretch()
    
    def browse_output_dir(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, 'Select Output Directory'
        )
        if directory:
            self.output_dir_edit.setText(directory)
    
    def browse_pron_dict(self):
        """Browse for pronunciation dictionary file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            'Select Pronunciation Dictionary',
            '',
            'Dictionary Files (*.json *.txt);;All Files (*)'
        )
        if filepath:
            self.pron_dict_edit.setText(filepath)
    
    def load_settings(self):
        """Load settings from config."""
        # Voice
        voice = prefs['default_voice']
        index = self.voice_combo.findData(voice)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
        
        self.rate_spin.setValue(prefs['default_rate'])
        self.volume_spin.setValue(prefs['default_volume'])
        
        # Audio
        self.normalize_check.setChecked(prefs['normalize_audio'])
        self.trim_silence_check.setChecked(prefs['trim_silence'])
        self.silence_thresh_spin.setValue(prefs['silence_threshold'])
        self.max_silence_spin.setValue(prefs['max_silence'])
        
        # Output
        self.output_dir_edit.setText(prefs['output_directory'])
        self.pron_dict_edit.setText(prefs['pronunciation_dict'])
    
    def save_settings(self):
        """Save settings to config."""
        prefs['default_voice'] = self.voice_combo.currentData()
        prefs['default_rate'] = self.rate_spin.value()
        prefs['default_volume'] = self.volume_spin.value()
        prefs['normalize_audio'] = self.normalize_check.isChecked()
        prefs['trim_silence'] = self.trim_silence_check.isChecked()
        prefs['silence_threshold'] = self.silence_thresh_spin.value()
        prefs['max_silence'] = self.max_silence_spin.value()
        prefs['output_directory'] = self.output_dir_edit.text()
        prefs['pronunciation_dict'] = self.pron_dict_edit.text()
