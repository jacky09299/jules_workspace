# MarkItDown GUI

This is a GUI wrapper for the [MarkItDown](https://github.com/microsoft/markitdown) library, allowing you to convert various file formats to Markdown with ease. It supports optional integration with Azure Document Intelligence and OpenAI for advanced conversion features.

## Features

- **File Conversion:** Convert PDF, Word, PowerPoint, Excel, Images, and more to Markdown.
- **Batch Processing:** Select multiple files or entire folders for conversion.
- **Azure Document Intelligence:** Optional integration for enhanced document analysis.
- **OpenAI Integration:** Optional integration for describing images or enhanced text processing using LLMs.
- **Preview:** See the result of the last converted file directly in the app.

## Setup

1.  **Install Python:** Ensure you have Python 3.10+ installed.
2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: `requirements.txt` should contain `markitdown[all]`, `openai`, `pyinstaller`, `tkinter` (usually included with Python))*

## Usage

1.  **Run the Application:**
    ```bash
    python main.py
    ```
2.  **Add Files:** Use "Add Files" or "Add Folder" to select documents to convert.
3.  **Configure (Optional):**
    -   Enter your Azure Document Intelligence Endpoint if you have one.
    -   Enter your OpenAI API Key, Model (default: `gpt-4o`), and specific Prompt if you want to use LLM features.
4.  **Select Output:**
    -   Check "Save to source directory" to save the `.md` file next to the original file.
    -   Or uncheck it to select a custom output folder.
5.  **Convert:** Click "Convert All".

## Building the Executable (EXE)

To package the application as a standalone `.exe` file for Windows (or binary for Mac/Linux), use the provided build script.

### Prerequisites
Ensure `pyinstaller` is installed:
```bash
pip install pyinstaller
```

### Build Command
Run the build script:
```bash
./build_exe.sh
```
Or run the command manually:
```bash
pyinstaller --noconfirm --onefile --windowed --name "MarkItDownGUI" \
    --hidden-import "markitdown" \
    --hidden-import "tkinter" \
    --collect-all "markitdown" \
    --collect-all "openai" \
    --collect-all "azure" \
    main.py
```

The executable will be found in the `dist/` directory.
