"""
Step 4 – Generate MD5 hashes for files.

Two modes:
  - partial_hash : reads only the first PARTIAL_BYTES bytes.  Fast initial filter.
  - full_hash    : reads the whole file in CHUNK_SIZE chunks.

Using 1 MB chunks (vs the original 4 KB) reduces the number of read() calls
significantly for large files.
"""

from __future__ import annotations

import hashlib
from typing import Optional

CHUNK_SIZE = 1024 * 1024       # 1 MB per chunk for full hash
PARTIAL_BYTES = 64 * 1024      # 64 KB for the quick partial hash


def get_partial_hash(file_path: str) -> Optional[str]:
    """
    Hash only the first PARTIAL_BYTES bytes of the file.
    Returns the hex digest, or None if the file could not be read.
    """
    hasher = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            data = f.read(PARTIAL_BYTES)
            if data:
                hasher.update(data)
        return hasher.hexdigest()
    except OSError:
        return None


def get_full_hash(file_path: str) -> Optional[str]:
    """
    Hash the entire file in CHUNK_SIZE chunks.
    Returns the hex digest, or None if the file could not be read.
    """
    hasher = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return None
