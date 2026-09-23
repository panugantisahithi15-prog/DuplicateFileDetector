"""
Steps 2 & 3 – Group files by size, then discard groups with only one member.

Input is the list of (path, size, mtime) tuples produced by scanner.get_all_files.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def group_by_size(
    file_entries: List[Tuple[str, int, float]],
) -> Dict[int, List[Tuple[str, int, float]]]:
    """
    Return a dict mapping size (bytes) -> list of (path, size, mtime).
    """
    size_map: Dict[int, List[Tuple[str, int, float]]] = {}
    for entry in file_entries:
        size = entry[1]
        size_map.setdefault(size, []).append(entry)
    return size_map


def filter_size_groups(
    size_map: Dict[int, List[Tuple[str, int, float]]],
) -> List[List[Tuple[str, int, float]]]:
    """
    Return only groups with more than one file (candidates for duplicates).
    """
    return [group for group in size_map.values() if len(group) > 1]
