"""
Data models for the duplicate file detector.
Pure Python dataclasses – no Flask dependency.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FileEntry:
    """Represents a single file that is part of a duplicate group."""
    path: str
    size: int            # bytes
    mtime: float         # seconds since epoch
    md5: str             # full MD5 hex digest

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def folder(self) -> str:
        return os.path.dirname(self.path)

    @property
    def size_human(self) -> str:
        """Human-readable file size (e.g. '4.2 MB')."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if self.size < 1024:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024
        return f"{self.size:.1f} PB"

    @property
    def mtime_human(self) -> str:
        """Human-readable modification time (ISO 8601 date)."""
        import datetime
        return datetime.datetime.fromtimestamp(self.mtime).strftime("%Y-%m-%d %H:%M")


@dataclass
class DuplicateGroup:
    """A set of files with identical content."""
    group_id: int
    files: List[FileEntry]

    @property
    def file_size(self) -> int:
        """Size of one copy in bytes."""
        return self.files[0].size if self.files else 0

    @property
    def wasted_bytes(self) -> int:
        """Bytes that could be freed by keeping only one copy."""
        return self.file_size * (len(self.files) - 1)

    @property
    def wasted_human(self) -> str:
        """Human-readable wasted space."""
        size = self.wasted_bytes
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @property
    def count(self) -> int:
        return len(self.files)


@dataclass
class SkippedFile:
    """A file that could not be read or hashed, with the reason."""
    path: str
    reason: str


@dataclass
class ScanResult:
    """The complete result of a scan operation."""
    groups: List[DuplicateGroup] = field(default_factory=list)
    total_files: int = 0
    total_bytes: int = 0
    wasted_bytes: int = 0
    duration_seconds: float = 0.0
    skipped: List[SkippedFile] = field(default_factory=list)
    error: Optional[str] = None   # top-level error (bad path, permission, etc.)

    @property
    def group_count(self) -> int:
        return len(self.groups)

    @property
    def wasted_human(self) -> str:
        size = self.wasted_bytes
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    @property
    def duration_human(self) -> str:
        s = self.duration_seconds
        if s < 1:
            return f"{s * 1000:.0f} ms"
        if s < 60:
            return f"{s:.1f} s"
        return f"{s / 60:.1f} min"
