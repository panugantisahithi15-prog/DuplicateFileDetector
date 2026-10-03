"""
Public API for the duplicate detection pipeline.

Both the Flask web app and the CLI call find_duplicates() here.
They never need to touch the lower-level modules directly.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict
from typing import List, Optional

from detector.duplicate_finder import find_duplicate_groups
from detector.models import DuplicateGroup, FileEntry, ScanResult, SkippedFile
from detector.scanner import get_all_files
from detector.size_group import filter_size_groups, group_by_size


def find_duplicates(
    root: str,
    min_size: int = 1,
) -> ScanResult:
    """
    Scan *root* recursively and return a ScanResult.

    Parameters
    ----------
    root:      absolute path to the folder to scan
    min_size:  minimum file size in bytes to consider (default 1 = skip empty files)

    Returns a ScanResult.  On a top-level error (bad path, etc.) ScanResult.error
    is set and the other fields are empty.
    """
    # ── 0. Validate root ──────────────────────────────────────────────────────
    if not root or not root.strip():
        return ScanResult(error="Please enter a folder path.")

    root = root.strip()

    if not os.path.exists(root):
        return ScanResult(error=f"Path does not exist: {root}")

    if not os.path.isdir(root):
        return ScanResult(error=f"Path is not a folder: {root}")

    start = time.perf_counter()

    # ── 1. Walk the tree ──────────────────────────────────────────────────────
    file_entries, scan_skipped = get_all_files(root, min_size=min_size)

    total_files = len(file_entries)
    total_bytes = sum(e[1] for e in file_entries)

    # ── 2. Group by size; discard singletons ──────────────────────────────────
    size_map = group_by_size(file_entries)
    size_groups = filter_size_groups(size_map)

    # ── 3. Two-stage hashing ──────────────────────────────────────────────────
    if size_groups:
        raw_groups, hash_skipped = find_duplicate_groups(size_groups)
    else:
        raw_groups, hash_skipped = [], []

    all_skipped = scan_skipped + hash_skipped

    # ── 4. Build result objects ───────────────────────────────────────────────
    groups = []
    wasted = 0

    for gid, (md5, entries) in enumerate(raw_groups):
        file_objs = [
            FileEntry(
                path=e[0],
                size=e[1],
                mtime=e[2],
                md5=md5,
            )
            for e in entries
        ]
        group = DuplicateGroup(group_id=gid, files=file_objs)
        wasted += group.wasted_bytes
        groups.append(group)

    # Sort: largest wasted space first
    groups.sort(key=lambda g: g.wasted_bytes, reverse=True)

    skipped_objs = [SkippedFile(path=p, reason=r) for p, r in all_skipped]

    duration = time.perf_counter() - start

    return ScanResult(
        groups=groups,
        total_files=total_files,
        total_bytes=total_bytes,
        wasted_bytes=wasted,
        duration_seconds=duration,
        skipped=skipped_objs,
    )


def find_duplicates_from_uploads(
    upload_files: list,
    min_size: int = 1,
) -> ScanResult:
    """
    Detect duplicates from browser-uploaded FileStorage objects.

    Hashes are computed entirely in memory — no temp files written to disk.
    The returned ScanResult has upload_mode=True, which disables the
    trash/rename actions (real filesystem paths are not available).

    Parameters
    ----------
    upload_files : list of Werkzeug FileStorage objects
    min_size     : minimum file size in bytes (default 1 = skip zero-byte)
    """
    if not upload_files:
        return ScanResult(error="No files received.", upload_mode=True)

    start = time.perf_counter()
    now = time.time()

    raw: List[tuple] = []   # (relative_path, size, bytes)
    skipped = []

    for f in upload_files:
        # Werkzeug sets filename to webkitRelativePath when webkitdirectory is used
        rel_path = f.filename or "unknown"
        try:
            data = f.read()
        except Exception as exc:
            skipped.append((rel_path, str(exc)))
            continue
        if len(data) < min_size:
            continue
        raw.append((rel_path, len(data), data))

    if not raw:
        return ScanResult(
            error="No readable files found (folder may be empty or all files below minimum size).",
            upload_mode=True,
        )

    total_files = len(raw)
    total_bytes = sum(s for _, s, _ in raw)

    # Group by size — files with different sizes cannot be duplicates
    size_map: dict = defaultdict(list)
    for path, size, data in raw:
        size_map[size].append((path, data))

    groups = []
    wasted = 0
    gid = 0

    for size, items in size_map.items():
        if len(items) < 2:
            continue
        # Hash every candidate in this size bucket
        hash_map: dict = defaultdict(list)
        for path, data in items:
            h = hashlib.md5(data).hexdigest()
            hash_map[h].append((path, size))
        for md5, entries in hash_map.items():
            if len(entries) < 2:
                continue
            file_objs = [
                FileEntry(path=path, size=file_size, mtime=now, md5=md5)
                for path, file_size in entries
            ]
            group = DuplicateGroup(group_id=gid, files=file_objs)
            wasted += group.wasted_bytes
            groups.append(group)
            gid += 1

    groups.sort(key=lambda g: g.wasted_bytes, reverse=True)

    duration = time.perf_counter() - start

    return ScanResult(
        groups=groups,
        total_files=total_files,
        total_bytes=total_bytes,
        wasted_bytes=wasted,
        duration_seconds=duration,
        skipped=[SkippedFile(path=p, reason=r) for p, r in skipped],
        upload_mode=True,
    )
