"""
Safe file actions: trash and rename duplicate files.

Design rules:
  - Paths are NEVER accepted from the browser.  The caller passes a group_id
    and file_index, which are looked up in the server-side scan result.
  - "Keep at least one copy" is enforced here, not just in the UI.
  - Every file is re-verified (exists + hash still matches) before it is trashed.
  - Files go to the Recycle Bin / Trash (send2trash), never permanently deleted.
  - Every action is appended to an in-memory action log so Undo is possible.
  - Rename rejects names that contain path separators, '..' or reserved Windows names.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from detector.hasher import get_full_hash
from detector.models import DuplicateGroup, FileEntry

# Reserved Windows file/folder names (case-insensitive)
_WINDOWS_RESERVED = re.compile(
    r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)", re.IGNORECASE
)


# ── Action log ─────────────────────────────────────────────────────────────

@dataclass
class ActionRecord:
    action: str        # 'trash' or 'rename'
    original_path: str
    new_path: Optional[str] = None   # for rename
    undone: bool = False


_action_log: List[ActionRecord] = []


def get_action_log() -> List[ActionRecord]:
    return list(_action_log)


# ── Validation helpers ─────────────────────────────────────────────────────

def _safe_new_name(name: str) -> Optional[str]:
    """
    Validate a proposed new filename.
    Returns None with a reason if the name is unsafe.
    """
    name = name.strip()
    if not name:
        return None
    if "/" in name or "\\" in name:
        return None
    if ".." in name:
        return None
    if _WINDOWS_RESERVED.match(name):
        return None
    return name


def _verify_file(entry: FileEntry) -> bool:
    """Return True if the file still exists and its full hash still matches."""
    if not os.path.isfile(entry.path):
        return False
    current_hash = get_full_hash(entry.path)
    return current_hash == entry.md5


# ── Public actions ─────────────────────────────────────────────────────────

def trash_file(
    group: DuplicateGroup,
    file_index: int,
) -> tuple[bool, str]:
    """
    Send the file at *file_index* in *group* to the Recycle Bin.

    Returns (success, message).
    Enforces: the group must still have at least one file left after trashing.
    """
    try:
        from send2trash import send2trash
    except ImportError:
        return False, "send2trash is not installed. Run: pip install send2trash"

    if file_index < 0 or file_index >= len(group.files):
        return False, "Invalid file index."

    if len(group.files) <= 1:
        return False, "Cannot trash the only remaining copy in the group."

    entry = group.files[file_index]

    if not _verify_file(entry):
        return False, f"File no longer matches the scan result: {entry.path}"

    try:
        send2trash(entry.path)
    except Exception as exc:
        return False, f"Could not trash file: {exc}"

    record = ActionRecord(action="trash", original_path=entry.path)
    _action_log.append(record)

    # Remove from the in-memory group
    group.files.pop(file_index)

    return True, f"Moved to Recycle Bin: {entry.name}"


def rename_file(
    group: DuplicateGroup,
    file_index: int,
    new_name: str,
) -> tuple[bool, str]:
    """
    Rename the file at *file_index* in *group*.
    The file stays in the same folder; only the name changes.

    Returns (success, message).
    """
    if file_index < 0 or file_index >= len(group.files):
        return False, "Invalid file index."

    safe_name = _safe_new_name(new_name)
    if not safe_name:
        return False, f"Invalid file name: {new_name!r}"

    entry = group.files[file_index]

    if not _verify_file(entry):
        return False, f"File no longer matches the scan result: {entry.path}"

    new_path = os.path.join(entry.folder, safe_name)

    if os.path.exists(new_path):
        return False, f"A file with that name already exists: {new_path}"

    try:
        os.rename(entry.path, new_path)
    except OSError as exc:
        return False, f"Could not rename file: {exc}"

    record = ActionRecord(action="rename", original_path=entry.path, new_path=new_path)
    _action_log.append(record)

    # Update the in-memory entry
    group.files[file_index] = FileEntry(
        path=new_path,
        size=entry.size,
        mtime=entry.mtime,
        md5=entry.md5,
    )

    return True, f"Renamed to: {safe_name}"
