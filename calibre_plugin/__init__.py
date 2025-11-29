"""
Audiobookify Calibre Plugin

Convert EPUB and MOBI/AZW books to M4B audiobooks directly from Calibre.
"""

from calibre.customize import InterfaceActionBase


class AudiobookifyPlugin(InterfaceActionBase):
    """Calibre plugin for converting ebooks to audiobooks."""
    
    name = 'Audiobookify'
    description = 'Convert EPUB and MOBI/AZW books to M4B audiobooks using Microsoft Edge TTS'
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'Audiobookify'
    version = (2, 3, 0)
    minimum_calibre_version = (5, 0, 0)
    
    # The actual plugin class (defined in ui.py)
    actual_plugin = 'calibre_plugins.audiobookify.ui:AudiobookifyInterface'
    
    def is_customizable(self):
        """This plugin has configuration options."""
        return True
    
    def config_widget(self):
        """Return the configuration widget."""
        from calibre_plugins.audiobookify.config import ConfigWidget
        return ConfigWidget()
    
    def save_settings(self, config_widget):
        """Save settings from the configuration widget."""
        config_widget.save_settings()
