"""
Step 1 – Walk the folder tree and collect file entries.

Uses os.scandir (gives stat data for free) instead of os.walk.
Skips symlinks to avoid following loops.
Deduplicates by (device, inode) so hardlinked files are not
reported as duplicates.
"""

from __future__ import annotations

import os
from typing import List, Tuple


def get_all_files(
    folder_path: str,
    min_size: int = 1,
) -> Tuple[List[Tuple[str, int, float]], List[Tuple[str, str]]]:
    """
    Walk *folder_path* recursively and return:
        - files  : list of (path, size_bytes, mtime)
        - skipped: list of (path, reason) for files that could not be read

    Only regular, non-symlink files of at least *min_size* bytes are included.
    Hardlinks to the same inode are deduplicated (only the first path is kept).
    """
    files: List[Tuple[str, int, float]] = []
    skipped: List[Tuple[str, str]] = []
    seen_inodes: set = set()

    def _walk(dir_path: str) -> None:
        try:
            entries = list(os.scandir(dir_path))
        except PermissionError as exc:
            skipped.append((dir_path, f"Permission denied: {exc}"))
            return
        except OSError as exc:
            skipped.append((dir_path, str(exc)))
            return

        for entry in entries:
            try:
                # Skip symlinks entirely (avoid loops and false duplicates)
                if entry.is_symlink():
                    continue

                if entry.is_dir(follow_symlinks=False):
                    _walk(entry.path)
                    continue

                if not entry.is_file(follow_symlinks=False):
                    continue

                # Use os.stat() rather than entry.stat() so that on Windows
                # NTFS we get the real st_ino (entry.stat returns 0 there).
                stat = os.stat(entry.path, follow_symlinks=False)
                size = stat.st_size

                # Skip files below minimum size (default: skip zero-byte files)
                if size < min_size:
                    continue

                # Deduplicate hardlinks.
                # On Windows, st_ino may be 0 (unsupported), in which case
                # we skip inode deduplication to avoid treating all files as
                # the same inode.
                if stat.st_ino != 0:
                    inode_key = (stat.st_dev, stat.st_ino)
                    if inode_key in seen_inodes:
                        continue
                    seen_inodes.add(inode_key)

                files.append((entry.path, size, stat.st_mtime))

            except PermissionError as exc:
                skipped.append((entry.path, f"Permission denied: {exc}"))
            except OSError as exc:
                skipped.append((entry.path, str(exc)))

    _walk(folder_path)
    return files, skipped
