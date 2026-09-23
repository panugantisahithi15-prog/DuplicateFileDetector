"""
Steps 5 & 6 – Multi-stage hashing to find duplicate groups.

Stage A: partial hash (first 64 KB) – fast, eliminates most non-duplicates
Stage B: full hash – definitive comparison for remaining candidates

Returns a list of (hash, [(path, size, mtime), ...]) for groups with > 1 file.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from detector.hasher import get_full_hash, get_partial_hash


def _group_by_hash_fn(
    candidates: List[List[Tuple[str, int, float]]],
    hash_fn,
) -> Tuple[List[List[Tuple[str, int, float]]], List[Tuple[str, str]]]:
    """
    Hash every file in *candidates* using *hash_fn*.
    Returns:
      - groups  : list of file groups with identical hashes (>1 member)
      - skipped : list of (path, reason) for files that could not be hashed
    """
    hash_map: Dict[str, List[Tuple[str, int, float]]] = {}
    skipped: List[Tuple[str, str]] = []

    for group in candidates:
        for entry in group:
            path = entry[0]
            h = hash_fn(path)
            if h is None:
                skipped.append((path, "Could not read file for hashing"))
                continue
            hash_map.setdefault(h, []).append(entry)

    groups = [g for g in hash_map.values() if len(g) > 1]
    return groups, skipped


def find_duplicate_groups(
    size_groups: List[List[Tuple[str, int, float]]],
) -> Tuple[List[Tuple[str, List[Tuple[str, int, float]]]], List[Tuple[str, str]]]:
    """
    Run two-stage hashing on *size_groups*.

    Returns:
      - duplicate_groups : list of (full_md5, [file_entries])
      - skipped          : list of (path, reason)
    """
    all_skipped: List[Tuple[str, str]] = []

    # Stage A: partial hash
    partial_groups, sk = _group_by_hash_fn(size_groups, get_partial_hash)
    all_skipped.extend(sk)

    # Stage B: full hash on the survivors
    full_hash_map: Dict[str, List[Tuple[str, int, float]]] = {}
    for group in partial_groups:
        for entry in group:
            path = entry[0]
            h = get_full_hash(path)
            if h is None:
                all_skipped.append((path, "Could not read file for full hash"))
                continue
            full_hash_map.setdefault(h, []).append(entry)

    duplicate_groups = [
        (md5, entries)
        for md5, entries in full_hash_map.items()
        if len(entries) > 1
    ]
    return duplicate_groups, all_skipped
