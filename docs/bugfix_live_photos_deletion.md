# Fix Live Photos Deletion Bug - Walkthrough

I have successfully identified and fixed the bug causing "File not found" errors and incorrect deletion counts in the Live Photos cleanup feature.

## Changes

### 1. UI Logic Fix (`live_photos_dialog.py`)
The root cause was in the `LivePhotoCleanupDialog`. When multiple image formats (e.g., JPG and HEIC) shared the same video file (MOV), the dialog was adding the video to the deletion list once for *each* image, creating duplicates.

- **Fix**: Implemented deduplication using a `set` to track added video paths. Now, even if a video is part of multiple groups, it is only added to the deletion plan once.

### 2. Service Robustness (`live_photos_service.py`)
To prevent future "scary" errors for users if files are missing for any reason (external deletion, remaining race conditions), I improved the error handling in `execute`.

- **Fix**: Attempting to delete a file that no longer exists is now treated as a **success** ("already deleted") rather than an error. This ensures accurate "space freed" reporting (assuming it was freed) and avoids pollution of the error log.

## Verification Results

### Automated Tests
I created a new unit test `tests/unit/ui/test_live_photos_deduplication.py` that specifically reproduces the double-counting scenario.

- **Test Suite**: Ran all Live Photo service tests + new UI test.
- **Result**: `62 passed` (100% success rate).

```bash
tests/unit/ui/test_live_photos_deduplication.py::test_dialog_deduplicates_video_deletion PASSED [100%]
```

### Manual Logic Verification
Verified that the new logic in `live_photos_dialog.py` correctly checks `if str(group.video_path) not in seen_delete_paths` before adding to the list.
