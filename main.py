from detector.scanner import get_all_files
from detector.size_group import group_by_size, filter_size_groups
from detector.duplicate_finder import group_by_hash, get_duplicates

if __name__ == "__main__":
    folder = input("Enter folder path: ")

    files = get_all_files(folder)
    print(f"Total files found: {len(files)}")

    size_map = group_by_size(files)
    size_groups = filter_size_groups(size_map)

    hash_map = group_by_hash(size_groups)
    duplicates = get_duplicates(hash_map)

    if not duplicates:
        print("No duplicate files found.")
    else:
        print("\nDuplicate files:")
        for group in duplicates:
            print("\n--- Duplicate Group ---")
            for file in group:
                print(file)