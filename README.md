# Duplicate File Manager

A full-stack Flask web application that recursively scans a folder, identifies duplicate files by content (using MD5 hashing), and lets you safely manage (delete, rename) them.

## Features

- 🔍 **Recursive scan** – walks every sub-folder and groups files first by size, then by MD5 hash
- ⚡ **Multi-stage filtering** – only files with matching sizes are hashed, cutting unnecessary I/O
- 🛡️ **Safe deletion** – sends files to the Recycle Bin (never permanent delete), keeps at least one copy, re-verifies the file before acting
- ↩️ **Undo** – every action is logged so you can restore files
- 📊 **Summary stats** – total files scanned, duplicate groups found, space you can free, time taken
- 🎨 **Clean UI** – Canva-inspired design with a responsive hero layout

## Quick Start

```bash
# 1. Clone and create a virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app (local only – binds to 127.0.0.1)
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## CLI usage

```bash
python cli.py
# Enter folder path: C:\Users\You\Pictures
```

## Architecture

```
DuplicateFileDetector/
├── app.py              – Flask entry point (127.0.0.1 only)
├── config.py           – SECRET_KEY, MIN_FILE_SIZE, CHUNK_SIZE
├── cli.py              – Command-line interface (no Flask)
├── detector/
│   ├── models.py       – FileEntry, DuplicateGroup, ScanResult dataclasses
│   ├── scanner.py      – os.scandir walk, inode dedup, symlink skip
│   ├── size_group.py   – group/filter by size
│   ├── hasher.py       – partial + full MD5 hash
│   ├── duplicate_finder.py – group by hash, extract groups
│   ├── service.py      – single find_duplicates(root) pipeline
│   └── actions.py      – safe trash/rename, re-verify, action log
├── templates/
│   ├── base.html       – shared head, navbar, blocks
│   ├── home.html
│   ├── service.html
│   ├── action.html
│   └── about.html
├── static/
│   ├── css/            – base.css, hero.css, results.css
│   ├── js/             – scan.js
│   └── images/
└── tests/              – pytest test suite
```

## Security notes

- The app binds to `127.0.0.1` only — never deploy publicly without authentication
- File paths are never accepted from the browser for deletion; only server-side IDs are used
- The server enforces "keep at least one copy" regardless of what the UI sends
- Every file is re-verified (exists + hash match) before being trashed
- CSRF protection on every POST (Flask-WTF)

## Pipeline

1. Walk the folder tree with `os.scandir`, collect `(path, size, inode)` for regular, non-symlink files
2. Group by size; discard groups with only one file
3. Hash the first 64 KB of each candidate; discard groups where the partial hashes differ
4. Full MD5 of remaining candidates; group by hash
5. Return `ScanResult` with groups, stats and a list of skipped files

## License

MIT
