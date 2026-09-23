"""
Tests for the duplicate detection pipeline.

Each test creates a temporary directory, populates it with files, runs
find_duplicates() and asserts the expected outcome.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from detector.service import find_duplicates


# ── Helpers ────────────────────────────────────────────────────────────────

def make_file(directory: str, name: str, content: bytes) -> str:
    path = os.path.join(directory, name)
    with open(path, "wb") as f:
        f.write(content)
    return path


# ── Tests ──────────────────────────────────────────────────────────────────

class TestFindDuplicates:

    def test_identical_files_are_detected(self, tmp_path):
        """Two files with the same content → one group with two entries."""
        make_file(str(tmp_path), "a.txt", b"hello world")
        make_file(str(tmp_path), "b.txt", b"hello world")

        result = find_duplicates(str(tmp_path))

        assert result.error is None
        assert result.group_count == 1
        assert result.groups[0].count == 2

    def test_different_content_not_duplicates(self, tmp_path):
        """Two files with different content → no duplicates."""
        make_file(str(tmp_path), "a.txt", b"hello world")
        make_file(str(tmp_path), "b.txt", b"different content")

        result = find_duplicates(str(tmp_path))

        assert result.error is None
        assert result.group_count == 0

    def test_same_size_different_content_not_duplicates(self, tmp_path):
        """Same size but different bytes → no duplicates (hash stage catches this)."""
        make_file(str(tmp_path), "a.bin", b"AAAA")
        make_file(str(tmp_path), "b.bin", b"BBBB")

        result = find_duplicates(str(tmp_path))

        assert result.error is None
        assert result.group_count == 0

    def test_empty_files_skipped_by_default(self, tmp_path):
        """Zero-byte files are excluded (min_size=1)."""
        make_file(str(tmp_path), "empty1.txt", b"")
        make_file(str(tmp_path), "empty2.txt", b"")

        result = find_duplicates(str(tmp_path))

        assert result.group_count == 0

    def test_nested_folders(self, tmp_path):
        """Duplicates in different sub-folders are detected."""
        sub = tmp_path / "sub"
        sub.mkdir()

        make_file(str(tmp_path), "original.bin", b"unique data here")
        make_file(str(sub), "copy.bin", b"unique data here")

        result = find_duplicates(str(tmp_path))

        assert result.group_count == 1
        paths = {f.path for f in result.groups[0].files}
        assert len(paths) == 2

    def test_multiple_groups(self, tmp_path):
        """Three distinct duplicate pairs → two groups."""
        make_file(str(tmp_path), "a1.txt", b"content-alpha")
        make_file(str(tmp_path), "a2.txt", b"content-alpha")
        make_file(str(tmp_path), "b1.txt", b"content-beta")
        make_file(str(tmp_path), "b2.txt", b"content-beta")
        make_file(str(tmp_path), "unique.txt", b"only one of these")

        result = find_duplicates(str(tmp_path))

        assert result.group_count == 2

    def test_single_file_no_duplicates(self, tmp_path):
        """A folder with one file has no duplicates."""
        make_file(str(tmp_path), "only.txt", b"solo")

        result = find_duplicates(str(tmp_path))

        assert result.group_count == 0
        assert result.total_files == 1

    def test_wasted_bytes_calculated(self, tmp_path):
        """Wasted bytes = (copies - 1) * file_size."""
        content = b"x" * 1000
        make_file(str(tmp_path), "a.bin", content)
        make_file(str(tmp_path), "b.bin", content)
        make_file(str(tmp_path), "c.bin", content)

        result = find_duplicates(str(tmp_path))

        assert result.group_count == 1
        assert result.wasted_bytes == 2000

    def test_stats_populated(self, tmp_path):
        """ScanResult carries total_files, total_bytes, duration."""
        make_file(str(tmp_path), "f.txt", b"abc")

        result = find_duplicates(str(tmp_path))

        assert result.total_files == 1
        assert result.total_bytes == 3
        assert result.duration_seconds >= 0

    def test_hardlinks_not_duplicates(self, tmp_path):
        """
        Hardlinked files share the same inode.  The scanner deduplicates
        by (device, inode) so they must NOT appear as duplicates.

        Skipped on Windows if the OS does not expose a non-zero inode
        (e.g. NTFS via the standard stat() call) or if hardlinks are not
        supported (requires elevated privileges or Developer Mode).
        """
        src = tmp_path / "original.bin"
        src.write_bytes(b"hardlink content")
        link = tmp_path / "link.bin"

        try:
            os.link(str(src), str(link))
        except (OSError, NotImplementedError):
            pytest.skip("Hardlinks not supported in this environment")

        # Check whether the OS reports a non-zero inode; if not, the
        # deduplication path will not trigger and the test is moot.
        if os.stat(str(src)).st_ino == 0:
            pytest.skip(
                "st_ino is 0 on this OS/filesystem; "
                "hardlink deduplication requires a real inode number"
            )

        result = find_duplicates(str(tmp_path))

        # Should be 0 groups because both paths point to the same inode
        assert result.group_count == 0

    def test_bad_path_returns_error(self, tmp_path):
        """A non-existent path returns a ScanResult with error set."""
        result = find_duplicates(str(tmp_path / "does_not_exist"))

        assert result.error is not None
        assert result.group_count == 0

    def test_file_path_instead_of_dir(self, tmp_path):
        """Passing a file path instead of a folder returns an error."""
        f = make_file(str(tmp_path), "file.txt", b"hi")

        result = find_duplicates(f)

        assert result.error is not None

    def test_empty_path_returns_error(self):
        """An empty string returns an error."""
        result = find_duplicates("")

        assert result.error is not None

    def test_result_sorted_by_wasted_space(self, tmp_path):
        """Groups are sorted largest-wasted-first."""
        # Group A: 3 copies of 100 bytes → 200 bytes wasted
        for i in range(3):
            make_file(str(tmp_path), f"big{i}.bin", b"B" * 100)

        # Group B: 2 copies of 10 bytes → 10 bytes wasted
        for i in range(2):
            make_file(str(tmp_path), f"small{i}.bin", b"S" * 10)

        result = find_duplicates(str(tmp_path))

        assert result.group_count == 2
        assert result.groups[0].wasted_bytes >= result.groups[1].wasted_bytes
