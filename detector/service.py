"""
Public API for the duplicate detection pipeline.

Both the Flask web app and the CLI call find_duplicates() here.
They never need to touch the lower-level modules directly.
"""

from __future__ import annotations

import os
import time
from typing import Optional

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
