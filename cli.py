"""
Command-line interface for Duplicate File Manager.
Uses the same find_duplicates() pipeline as the web app.
"""

from __future__ import annotations

from detector.service import find_duplicates


def main() -> None:
    folder = input("Enter folder path: ").strip()
    result = find_duplicates(folder)

    if result.error:
        print(f"\n❌ Error: {result.error}")
        return

    print(f"\nScanned {result.total_files} files in {result.duration_human}")
    print(f"Duplicate groups : {result.group_count}")
    print(f"Wasted space     : {result.wasted_human}")

    if result.skipped:
        print(f"\n⚠️  Skipped {len(result.skipped)} file(s):")
        for sk in result.skipped[:10]:
            print(f"  {sk.path}  →  {sk.reason}")
        if len(result.skipped) > 10:
            print(f"  ... and {len(result.skipped) - 10} more")

    if not result.groups:
        print("\n✅ No duplicate files found. Your folder is clean.")
        return

    print("\n" + "─" * 60)
    for group in result.groups:
        print(f"\n📁 Group #{group.group_id + 1}  |  {group.wasted_human} wasted")
        for i, f in enumerate(group.files):
            marker = "  [KEEP]" if i == 0 else "        "
            print(f"  {marker} {f.path}  ({f.mtime_human})")
    print("\n" + "─" * 60)


if __name__ == "__main__":
    main()
