# Audiobookify Calibre Plugin

Convert EPUB and MOBI/AZW books to M4B audiobooks directly from Calibre.

## Features

- Convert selected books to M4B audiobooks
- Preview chapter structure before conversion
- Configure voice, speed, and volume
- Audio normalization and silence trimming
- Custom pronunciation dictionary support

## Installation

### Method 1: From ZIP file

1. Build the plugin ZIP:
   ```bash
   cd calibre_plugin
   zip -r audiobookify-calibre.zip . -x "*.pyc" -x "__pycache__/*" -x "README.md"
   ```

2. In Calibre, go to **Preferences** → **Plugins** → **Load plugin from file**

3. Select the `audiobookify-calibre.zip` file

4. Restart Calibre

### Method 2: Manual Installation

1. Copy the `calibre_plugin` directory to Calibre's plugin folder:
   - Windows: `%APPDATA%\calibre\plugins\`
   - macOS: `~/Library/Preferences/calibre/plugins/`
   - Linux: `~/.config/calibre/plugins/`

2. Rename the folder to `Audiobookify`

3. Restart Calibre

## Usage

### Converting Books

1. Select one or more books in Calibre
2. Click the **Audiobookify** button in the toolbar, or right-click and select **Audiobookify** → **Convert to Audiobook**
3. Configure conversion settings (voice, speed, etc.)
4. Click **Convert**

### Previewing Chapters

1. Select a book in Calibre
2. Click **Audiobookify** → **Preview Chapters**
3. Review the detected chapter structure

### Configuration

1. Go to **Preferences** → **Plugins**
2. Find **Audiobookify** and click **Customize plugin**
3. Configure default settings:
   - Default voice
   - Speech rate and volume
   - Audio normalization options
   - Output directory
   - Pronunciation dictionary

## Requirements

- Calibre 5.0 or later
- Python 3.8+
- Internet connection (for Microsoft Edge TTS)
- FFmpeg (for audio processing)

## Supported Formats

- EPUB (preferred)
- MOBI
- AZW/AZW3

## Troubleshooting

### Plugin not appearing

- Restart Calibre after installation
- Check **Preferences** → **Plugins** → **User interface action** for the plugin

### Conversion fails

- Ensure FFmpeg is installed and accessible
- Check internet connection for Edge TTS
- Look at conversion logs for specific errors

## License

This plugin is part of the Audiobookify project.
