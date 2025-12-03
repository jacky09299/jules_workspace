#!/bin/bash
# Clean up previous builds
rm -rf build dist *.spec

# Run PyInstaller
# --onefile: Create a single executable file
# --windowed: Do not open a console window (for GUI apps)
# --name: Name of the executable
# --hidden-import: Explicitly import hidden dependencies
pyinstaller --noconfirm --onefile --windowed --name "MarkItDownGUI" \
    --hidden-import "markitdown" \
    --hidden-import "tkinter" \
    --collect-all "markitdown" \
    --collect-all "openai" \
    --collect-all "azure" \
    main.py

echo "Build complete. Executable is in dist/MarkItDownGUI"
