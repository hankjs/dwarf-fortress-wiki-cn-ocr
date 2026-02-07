# Dwarf Fortress Wiki OCR Tool - AGENTS.md

## Project Overview

This is a **Dwarf Fortress Wiki OCR and Translation Tool** designed to help Chinese players understand in-game English text. The tool allows users to take screenshots of the game, perform OCR (Optical Character Recognition) to extract English text, and then automatically look up matching entries from the Dwarf Fortress Wiki with bilingual (English/Chinese) support.

### Key Features
- Screenshot-based OCR for English text recognition
- Automatic wiki entry matching from OCR results
- Bilingual display (English/Chinese toggle)
- Local wiki database for offline access
- Support for wiki internal link navigation
- Image loading from Dwarf Fortress Wiki

## Technology Stack

- **Language**: Python 3
- **GUI Framework**: PyQt5 >= 5.15.0
- **OCR Engine**: Tesseract OCR (bundled in `Tesseract-OCR/`)
- **OCR Python Binding**: pytesseract >= 0.3.10
- **Image Processing**: Pillow >= 9.0.0

## Project Structure

```
df-ocr/
├── src/                           # Source code directory
│   ├── __init__.py
│   ├── ocr_tool.py                # Main GUI application entry point
│   └── wiki_to_html.py            # Wiki format to HTML converter
├── tests/                         # Unit tests directory
│   ├── __init__.py
│   ├── test_translation.py        # Translation functionality tests
│   └── test_wiki_to_html.py       # Wiki to HTML conversion tests
├── split_wiki.py                  # MediaWiki XML splitter
├── build_translation_map.py       # Build translation dictionary from wiki_cn
├── translate_large_files.py       # Large file translation rules (placeholder)
├── requirements.txt               # Python dependencies
├── translation_map.json           # Generated translation dictionary
├── Dwarf+Fortress+Wiki-*.xml      # Raw MediaWiki XML export (source data)
├── wiki/                          # English wiki entries (~5136 files)
│   ├── Aardvark.txt
│   ├── Dwarf.txt
│   └── ...
├── wiki_cn/                       # Chinese translations (~838 files)
│   ├── Aardvark-CN.txt
│   ├── Dwarf-CN.txt
│   └── ...
└── Tesseract-OCR/                 # Bundled Tesseract OCR engine
    ├── tessdata/                  # Language models
    └── tesseract.exe
```

## Core Modules

### 1. `src/ocr_tool.py`
Main application module with PyQt5 GUI.

**Key Classes:**
- `MainWindow` - Main application window with screenshot button
- `ScreenshotWindow` - Full-screen overlay for region selection
- `ResultDialog` - OCR results and wiki content display
- `WikiTextBrowser` - Custom text browser with async image loading
- `ImageDownloader` - Background thread for wiki image fetching

**Workflow:**
1. User clicks "截图并识别词条" (Screenshot and Recognize)
2. `ScreenshotWindow` captures selected screen region
3. OCR extracts English text using Tesseract
4. Text is matched against `wiki_index` (normalized keys)
5. Matching wiki entries displayed in `ResultDialog`
6. User can toggle between English/Chinese content

### 2. `src/wiki_to_html.py`
Converts MediaWiki markup to HTML for display.

**Key Function:**
- `wiki_to_html(content)` - Converts wiki markup to HTML

**Supported Syntax:**
- Wiki links: `[[Link]]` → `<a href="wiki:Link">`
- Wiki links with display: `[[Link|Display]]` → `<a href="wiki:Link">Display</a>`
- Images: `[[File:Image.png|widthpx]]` → `<img>`
- Bold: `'''text'''` or `**text**` → `<b>`
- Italic: `*text*` or `_text_` → `<i>`
- Headings: `==text==` (H2), `=text=` (H3)
- Code blocks: \`\`\`code\`\`\` → `<pre><code>`
- Inline code: \`code\` → `<code>`
- Tables: `{| ... |}` → `<table>`
- Lists: `- item`, `* item`, `1. item` → `<ul>`, `<ol>`

### 3. `split_wiki.py`
Parses MediaWiki XML export into individual `.txt` files.

**Usage:**
```bash
python split_wiki.py [input_xml] [output_dir]
```

**Features:**
- SAX-based streaming parser for memory efficiency
- Sanitizes filenames (removes Windows-invalid characters)
- Compacts multi-line templates to single-line format
- Skips files ending with "raw" suffix
- Organizes by namespace subdirectories

### 4. `build_translation_map.py`
Builds translation mapping from existing Chinese translations.

**Output:** `translation_map.json`
```json
{
  "title_map": {
    "aardvark": {"en": "Aardvark", "cn": "土豚"}
  },
  "vocabulary_map": {
    "dwarf": "矮人",
    "fortress": "要塞"
  }
}
```

**Translation Strategy:**
1. Extract mappings from `wiki_cn/*-CN.txt` files
2. Build normalized key mapping (lowercase alphanumeric only)
3. Include extensive hardcoded vocabulary map for game terminology

### 5. `wiki/` and `wiki_cn/` Data Directories

**File Naming Convention:**
- English: `{Title}.txt`
- Chinese: `{Title}-CN.txt`

**Content Format:**
- MediaWiki markup syntax
- Redirects: `#REDIRECT [[TargetPage]]`
- Internal links: `[[Link]]` or `[[Link|DisplayText]]`
- Images: `[[File:ImageName.png|widthpx]]`

## Build and Run Commands

### Installation
```bash
# Install Python dependencies
pip install -r requirements.txt
```

### Run Application
```bash
# Run the OCR tool (from project root)
python src/ocr_tool.py
```

### Build Translation Map
```bash
# Regenerate translation_map.json from wiki_cn files
python build_translation_map.py
```

### Split Wiki XML (One-time setup)
```bash
# Split MediaWiki XML into individual files
python split_wiki.py Dwarf+Fortress+Wiki-20260206192244.xml wiki
```

### Run Tests
```bash
# Run all tests
python -m pytest tests/

# Or run individual test files
python tests/test_translation.py
python tests/test_wiki_to_html.py
```

## Translation System Architecture

### Three-Layer Translation Strategy

1. **Human Translation Layer** (Highest Priority)
   - Files in `wiki_cn/` directory
   - Complete manual translations of wiki entries
   - Matched by normalized entry name

2. **Title Mapping Layer**
   - `title_map` in `translation_map.json`
   - Maps English entry names to Chinese titles
   - Used for entry name display

3. **Vocabulary Replacement Layer** (Fallback)
   - `vocabulary_map` in `translation_map.json`
   - Word-by-word replacement using regex
   - Longer words matched first to avoid partial replacements
   - Marked with "⚠️ [临时翻译]" (Temporary Translation) warning

### Normalization Rules
```python
def normalize_key(text):
    """只保留字母数字并转小写"""
    return re.sub(r"[^a-zA-Z0-9]", "", text).lower()
```

Examples:
- `Dwarf Fortress` → `dwarffortress`
- `Adamantine` → `adamantine`
- `Adder(Computing)` → `addercomputing`

## Wiki Entry Matching Logic

### Matching Algorithm (`match_wiki_entries`)
1. Split OCR text into lines and words
2. Truncate at dot characters (e.g., `Yourfirstfortress.txt` → `Yourfirstfortress`)
3. Normalize each candidate
4. Exact match against `wiki_index`
5. Substring match (prefix match or containment)
6. Return deduplicated matches

### Redirect Handling (`read_wiki_content`)
- Follows `#REDIRECT [[Target]]` chains
- Maximum 10 redirects to prevent loops
- Returns final content and resolved entry name

## Code Style Guidelines

### Naming Conventions
- **Variables/Functions**: `snake_case` (PEP 8)
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private Methods**: `_leading_underscore`

### Comments
- Primary documentation language: **Chinese**
- Docstrings explain purpose and behavior
- Inline comments for complex logic

### Import Order
1. Standard library imports
2. Third-party imports (PyQt5, PIL, pytesseract)
3. Local module imports

### String Handling
- All source files use `utf-8` encoding
- User-facing strings in Chinese
- Internal keys/identifiers in English

## Testing Strategy

### Manual Testing
1. Run `python ocr_tool.py`
2. Click screenshot button
3. Select region with English text
4. Verify OCR accuracy
5. Verify wiki entry matching
6. Test language toggle button

### Unit Testing
- `test_translation.py` - Tests vocabulary mapping
- Run: `python test_translation.py`

### Test Data
- Use `wiki/` entries for matching tests
- Use `translation_map.json` for vocabulary tests

## Development Workflow

### Adding New Translations
1. Create `{EntryName}-CN.txt` in `wiki_cn/`
2. Run `build_translation_map.py` to update JSON
3. Test in OCR tool

### Updating Wiki Data
1. Download new MediaWiki XML export
2. Run `split_wiki.py` to regenerate `wiki/`
3. Manually merge with existing translations

### Adding Vocabulary
1. Edit `vocabulary_map` in `build_translation_map.py`
2. Run script to regenerate `translation_map.json`
3. Test translation in UI

## Security Considerations

- Tesseract-OCR is bundled locally (no network dependency for OCR)
- Wiki images loaded from `dwarffortresswiki.org` (external HTTPS)
- No user data persists except cached images in memory
- File paths sanitized to prevent directory traversal

## Known Limitations

1. **Translation Coverage**: Only ~16% of wiki entries have Chinese translations (838/5136)
2. **OCR Accuracy**: Dependent on Tesseract English model quality
3. **Image Loading**: Requires internet connection for wiki images
4. **Vocabulary Translation**: Word-for-word replacement lacks context awareness

## Related Documentation

- `TranTodo.md` - Translation progress tracking (todo list format)
- `todo_remaining.txt` - List of files pending translation
- `requirements.txt` - Python package dependencies
