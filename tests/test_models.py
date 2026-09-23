"""
Unit tests for the data-model helpers in detector/models.py.
"""

from __future__ import annotations

import time

from detector.models import DuplicateGroup, FileEntry, ScanResult, SkippedFile


def _entry(size: int = 1000) -> FileEntry:
    return FileEntry(path="/tmp/f.txt", size=size, mtime=time.time(), md5="abc")


class TestFileEntry:

    def test_name_extracted_from_path(self):
        f = FileEntry(path="/foo/bar/baz.txt", size=10, mtime=0, md5="x")
        assert f.name == "baz.txt"

    def test_folder_extracted_from_path(self):
        f = FileEntry(path="/foo/bar/baz.txt", size=10, mtime=0, md5="x")
        assert f.folder == "/foo/bar"

    def test_size_human_bytes(self):
        f = _entry(500)
        assert f.size_human == "500.0 B"

    def test_size_human_kilobytes(self):
        f = _entry(2048)
        assert f.size_human == "2.0 KB"

    def test_size_human_megabytes(self):
        f = _entry(5 * 1024 * 1024)
        assert "MB" in f.size_human

    def test_size_human_does_not_mutate_field(self):
        """Regression: size_human must not modify self.size."""
        f = _entry(5 * 1024 * 1024)
        original = f.size
        _ = f.size_human
        _ = f.size_human   # call twice – would expose mutation
        assert f.size == original, "size_human must not modify the size field"

    def test_mtime_human_format(self):
        import datetime
        ts = datetime.datetime(2025, 6, 15, 12, 30).timestamp()
        f = FileEntry(path="/x", size=1, mtime=ts, md5="y")
        assert f.mtime_human == "2025-06-15 12:30"


class TestDuplicateGroup:

    def test_wasted_bytes_two_copies(self):
        f1 = _entry(1000)
        f2 = _entry(1000)
        g = DuplicateGroup(group_id=0, files=[f1, f2])
        assert g.wasted_bytes == 1000

    def test_wasted_bytes_three_copies(self):
        files = [_entry(500) for _ in range(3)]
        g = DuplicateGroup(group_id=0, files=files)
        assert g.wasted_bytes == 1000

    def test_count(self):
        g = DuplicateGroup(group_id=0, files=[_entry(), _entry(), _entry()])
        assert g.count == 3

    def test_wasted_human_not_empty(self):
        g = DuplicateGroup(group_id=0, files=[_entry(2048), _entry(2048)])
        assert "KB" in g.wasted_human or "B" in g.wasted_human

    def test_empty_group_file_size_zero(self):
        g = DuplicateGroup(group_id=0, files=[])
        assert g.file_size == 0
        assert g.wasted_bytes == 0


class TestScanResult:

    def test_group_count_property(self):
        g = DuplicateGroup(group_id=0, files=[_entry(), _entry()])
        from detector.models import ScanResult
        r = ScanResult(groups=[g, g], wasted_bytes=200)
        assert r.group_count == 2

    def test_duration_human_milliseconds(self):
        r = ScanResult(duration_seconds=0.045)
        assert "ms" in r.duration_human

    def test_duration_human_seconds(self):
        r = ScanResult(duration_seconds=3.7)
        assert "s" in r.duration_human

    def test_duration_human_minutes(self):
        r = ScanResult(duration_seconds=125)
        assert "min" in r.duration_human

    def test_wasted_human_bytes(self):
        r = ScanResult(wasted_bytes=512)
        assert "B" in r.wasted_human

    def test_wasted_human_megabytes(self):
        r = ScanResult(wasted_bytes=2 * 1024 * 1024)
        assert "MB" in r.wasted_human

    def test_error_defaults_none(self):
        r = ScanResult()
        assert r.error is None

    def test_skipped_defaults_empty(self):
        r = ScanResult()
        assert r.skipped == []
