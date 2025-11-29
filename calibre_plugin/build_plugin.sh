#!/bin/bash
# Build Audiobookify Calibre Plugin

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_FILE="$PLUGIN_DIR/../audiobookify-calibre.zip"

echo "Building Audiobookify Calibre Plugin..."

cd "$PLUGIN_DIR"

# Remove old zip if exists
rm -f "$OUTPUT_FILE"

# Create new zip
zip -r "$OUTPUT_FILE" . \
    -x "*.pyc" \
    -x "__pycache__/*" \
    -x "README.md" \
    -x "build_plugin.sh" \
    -x ".DS_Store"

echo "Plugin built: $OUTPUT_FILE"
echo ""
echo "To install:"
echo "  1. Open Calibre"
echo "  2. Go to Preferences → Plugins"
echo "  3. Click 'Load plugin from file'"
echo "  4. Select $OUTPUT_FILE"
echo "  5. Restart Calibre"
