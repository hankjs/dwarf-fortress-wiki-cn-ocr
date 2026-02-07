# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dwarf Fortress Wiki OCR Tool - A PyQt5 desktop application that helps Chinese players understand in-game English text by performing OCR on screenshots and displaying matching Dwarf Fortress Wiki entries with bilingual support (EN/CN). Features include:
- **Sentence Translation**: MyMemory API-powered translation for multi-word OCR text
- **Dictionary Lookup**: ECDICT-based English dictionary (150万+ words)
- **Wiki Matching**: Fuzzy matching against 5000+ Dwarf Fortress wiki entries

**Tech Stack:** Python 3, PyQt5, Tesseract OCR, Pillow, ECDICT (SQLite), MyMemory Translation API

## Common Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Download ECDICT English dictionary database (optional, for dictionary support)
python scripts/download_ecdict.py

# Run the main application
python src/ocr_tool.py

# Alternative: use bundled launcher
run.bat
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test files
python tests/test_wiki_to_html.py -v
python tests/test_translation.py -v
```

### Data Processing
```bash
# Rebuild translation mapping from wiki_cn/ translations
python scripts/build_translation_map.py

# Split MediaWiki XML export into individual .txt files (one-time setup)
python scripts/split_wiki.py Dwarf+Fortress+Wiki-20260206192244.xml wiki
```

## Architecture Overview

### Four-Layer Translation System

The application uses a cascading translation strategy with four independent components:

**A. Sentence Translation (MyMemory API)**
   - Real-time translation of OCR text when multiple words detected
   - Uses MyMemory Translation API (500 free requests/day)
   - Game terminology pre-replaced before translation
   - Displayed in "🈯 翻译" tab in EntryListWidget
   - Asynchronous execution via QThread (non-blocking)

**B. Wiki Entry Translation System** (Three Priority Layers)

The app uses a cascading translation strategy for wiki entries:

1. **Human Translation Layer** (Highest Priority)
   - Complete manual translations in `wiki_cn/` directory
   - Files named `{EntryName}-CN.txt`
   - ~838 files (~16% coverage)

2. **Title Mapping Layer**
   - Entry name translations from `translation_map.json`
   - Auto-generated from existing `wiki_cn/` files
   - Used for entry titles and navigation

3. **Vocabulary Replacement Layer** (Fallback)
   - Word-by-word substitution using `vocabulary_map` from `translation_map.json`
   - ~1800+ term mappings
   - Applied when no manual translation exists
   - Marked with "⚠️ [临时翻译]" warning in UI

### Key Application Flow

```
User clicks screenshot → ScreenshotWindow (region selection)
  → OCR via Tesseract → Text normalization
  → Parallel query:
     ├─ Sentence translation (if multi-word) → Argos Translate + term protection
     ├─ Wiki entry matching (fuzzy + exact) → Load from wiki/wiki_cn
     └─ Dictionary lookup (ECDICT) with lemmatization
  → wiki_to_html conversion for wiki entries
  → Display in MainWindow:
     EntryListWidget (left sidebar):
       - 🈯 Translation (if multi-word OCR text)
       - 📚 Dictionary words
       - 📖 Wiki entries
     ContentDisplayWidget (right panel):
       - Click any entry → Display content with CN/EN toggle
```

### Critical Components

**`src/ocr_tool.py`** - Main application module (550+ lines)
- `TranslationWorker`: QThread for async translation (non-blocking)
- `MainWindow`: Entry point with screenshot button and wiki index building
- Handles OCR processing, wiki entry matching, and redirect resolution
- `_start_translation()`: Launches background translation thread
- `_on_translation_finished()`: Updates UI when translation completes

**`src/result_dialog.py`** - Result display module (496 lines)
- `ResultDialog`: Wiki content viewer with CN/EN toggle
- `WikiTextBrowser`: Custom QTextBrowser with async image loading
- `ImageDownloader`/`ImageUrlResolver`: Background threads for wiki images
- Global `_image_cache` for sharing loaded images across windows

**`src/screenshot.py`** - Screenshot capture module (71 lines)
- `ScreenshotWindow`: Full-screen overlay for region selection
- Handles mouse events and area selection with rubber band

**`src/translation.py`** - Translation utilities (82 lines)
- `load_translation_map()`: Loads translation_map.json
- `translate_content_by_vocab()`: Word-by-word translation with wiki syntax protection

**`src/dictionary.py`** - English dictionary module (300+ lines)
- `DictionaryManager`: ECDICT SQLite database interface
- `lookup_with_lemma()`: Word lookup with automatic lemmatization (running→run)
- `format_entry_as_html()`: Formats dictionary entries as HTML with phonetic, definition, etymology, etc.
- Supports fuzzy search and batch lookup
- Global singleton: `get_dictionary_manager()`

**`src/sentence_translator.py`** - Sentence translation module (180+ lines)
- `SentenceTranslator`: MyMemory API client with term protection
- `should_translate()`: Checks if text has multiple words (single words use dictionary)
- `translate()`: Translates text after pre-replacing game terminology
- `_preprocess_replace_terms()`: Replaces EN terms with CN before translation
- `_call_mymemory_api()`: Calls MyMemory Translation API
- Global singleton: `get_sentence_translator()`
- No installation needed, works with network connection

**`src/entry_list_widget.py`** - Search result list widget (200+ lines)
- `EntryListWidget`: Displays translation/dict/wiki results in three sections
- `set_entries()`: Populates lists with translation_entry, dict_entries, wiki_entries
- `select_first()`: Auto-selects first result (priority: translation > wiki > dict)
- Emits `entry_selected(index, type)` signal where type is "translation", "dict", or "wiki"

**`src/content_display_widget.py`** - Content display widget (250+ lines)
- `ContentDisplayWidget`: Right panel for displaying selected entry content
- `show_translation()`: Displays sentence translation with original/translated text
- `show_dict_entry()`: Displays dictionary entry with formatted HTML
- `show_wiki_entry()`: Displays wiki entry with CN/EN toggle support
- `toggle_language()`: Switches between EN/CN for wiki and translation entries
- `can_toggle_language()`: Returns True for translation and wiki entries

**`src/wiki_to_html.py`** - Wiki markup parser (417 lines)
- `wiki_to_html(content)`: Converts MediaWiki syntax to HTML
- Handles: `[[links]]`, `[[File:...]]`, bold/italic, tables, lists, code blocks
- Protects wiki syntax during HTML escaping
- Returns tuple: `(html_content, url_to_filename_mapping)`

**`translation_map.json`** - Translation database
- `title_map`: Entry name mappings (normalized key → EN/CN titles)
- `vocabulary_map`: Individual word translations (EN → CN)
- Generated by `scripts/build_translation_map.py`

### Normalization Rules

All wiki entry matching uses normalized keys:
```python
def normalize_key(text):
    """Remove all non-alphanumeric chars and lowercase"""
    return re.sub(r"[^a-zA-Z0-9]", "", text).lower()
```

Examples:
- `"Dwarf Fortress"` → `"dwarffortress"`
- `"Adder(Computing)"` → `"addercomputing"`

This normalization is applied to:
- OCR text before matching
- Wiki filenames when building index
- Translation map keys

### Wiki Entry Matching

The `match_wiki_entries()` method in `MainWindow`:
1. Splits OCR text into lines and words
2. Truncates at dots: `"Yourfirstfortress.txt"` → `"Yourfirstfortress"`
3. Normalizes each candidate
4. Performs **exact match** against `wiki_index`
5. Performs **substring match** (prefix or containment) for candidates ≥3 chars
6. Deduplicates results

### Redirect Handling

Wiki files may contain `#REDIRECT [[Target]]`:
- `read_wiki_content()` follows redirect chains (max 10 hops)
- Returns final content + resolved entry name
- Prevents infinite loops with visited set

## Important Implementation Details

### Wiki Markup Translation Protection

When using vocabulary-based translation (`translate_content_by_vocab`):
1. **Extract and protect** wiki syntax with placeholders:
   - `[[File:...]]`, `[[Image:...]]`
   - `[[link]]`, `[[link|display]]`
   - `{{templates}}`
   - URLs
2. **Apply vocabulary substitution** (sorted by word length, longest first)
3. **Restore protected syntax** from placeholders

This prevents breaking wiki markup during translation.

### Image Loading Strategy

Wiki images use MD5-based URL structure:
```python
filename = "DwarfFortress.png"
hash = md5(filename.encode()).hexdigest()
url = f"https://dwarffortresswiki.org/images/{hash[0]}/{hash[:2]}/{filename}"
```

**Two-stage loading:**
1. Try direct URL first (constructed from filename)
2. On 404: Query MediaWiki API for actual URL (handles Wikimedia Commons)

Images cached in global `_image_cache` dict to prevent re-downloading.

### HTML Conversion Order

In `wiki_to_html()`, processing order matters:
1. Protect `[[File:...]]` → placeholders
2. Protect existing HTML tags → placeholders
3. Apply `html.escape()` to content
4. Restore HTML tags
5. Restore file placeholders
6. Process external links `[http://...]`
7. Process wiki links `[[...]]`
8. Process MediaWiki tables `{| ... |}`
9. Process Markdown syntax (code, bold, italic, lists)
10. Convert `\n` → `<br>`

**Critical:** Tables must be processed BEFORE italic syntax to prevent `_LAND_HOLDER_` variable names from being italicized.

### PyQt5 Threading Rules

- File I/O and `Write` operations **must** run on main thread
- Background agents (`run_in_background=true`) **cannot** write files (permission auto-denied)
- Use `ImageDownloader` (QThread) for async network requests
- Emit signals to update UI from background threads

## File Naming Conventions

- **English wiki**: `wiki/{Title}.txt`
- **Chinese wiki**: `wiki_cn/{Title}-CN.txt`
- **Scripts**: `scripts/{purpose}.py`
- **Tests**: `tests/test_{module}.py`

## Translation Workflow

### Adding New Manual Translations

1. Create `wiki_cn/{EntryName}-CN.txt` with MediaWiki markup
2. Run `python scripts/build_translation_map.py` to update mapping
3. Test in application with language toggle

### Adding Vocabulary Terms

1. Edit `vocabulary_map` dict in `scripts/build_translation_map.py`
2. Run script to regenerate `translation_map.json`
3. Terms are sorted by length (longest first) during replacement

## Translation Rules (from Memory)

When translating wiki files, preserve ALL wiki markup:

1. **Keep as-is:** `{{Quality|...}}`, `{{av}}`, `{{creaturedesc}}`, `{{gamedata}}`, etc.
2. **Do NOT translate:** `#REDIRECT` lines, simple links `[[target]]`
3. **Translate label only:** `[[target|label]]` → `[[target|中文标签]]`
4. **Keep entirely as-is:** Multi-line `{{creaturedesc}}` blocks, `[[File:...|...|...]]`
5. **Preserve structure:** HTML comments, wiki tables, external URLs

## Code Style

- **Language:** Docstrings and comments in Chinese; code/vars in English
- **Naming:** `snake_case` for functions/vars, `PascalCase` for classes
- **Encoding:** All files UTF-8
- **String handling:** Use f-strings; user-facing text in Chinese

## Development Tips

- Tesseract OCR is bundled in `Tesseract-OCR/` (no separate installation needed)
- Run application from project root: `python src/ocr_tool.py`
- Large files (>30k tokens) should be read in chunks using `offset` and `limit` parameters
- The `wiki/` directory has ~5136 files; `wiki_cn/` has ~838 files
- Translation progress tracked in `TranTodo.md` (checkbox format)
- Remaining untranslated files listed in `todo_remaining.txt`
- **ECDICT dictionary**: Optional feature, download with `python scripts/download_ecdict.py`
  - File size: ~450MB (uncompressed SQLite database)
  - Location: `ecdict.db` in project root
  - Application works without it (wiki-only mode)

## Common Gotchas

1. **Path handling:** Scripts expect to run from project root
2. **Image URLs:** Some wiki images redirect to Wikimedia Commons (requires API lookup)
3. **Large files:** `Armor.txt` (~35k tokens), `Adventurermode.txt` (~317 lines) need chunked reading
4. **Redirect chains:** Some entries have multiple redirects; always follow to final target
5. **Normalized matching:** Wiki entry names are normalized (alphanumeric only) for matching
