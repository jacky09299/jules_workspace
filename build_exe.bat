@echo off
REM Clean up previous builds
rmdir /s /q build
rmdir /s /q dist
del *.spec

REM Run PyInstaller
pyinstaller --noconfirm --onefile --windowed --name "MarkItDownGUI" ^
    --hidden-import "markitdown" ^
    --hidden-import "tkinter" ^
    --collect-all "markitdown" ^
    --collect-all "openai" ^
    --collect-all "azure" ^
    main.py

echo Build complete. Executable is in dist/MarkItDownGUI.exe
pause
