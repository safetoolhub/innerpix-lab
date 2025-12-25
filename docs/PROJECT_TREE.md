# Innerpix Lab - Project Structure

PyQt6 desktop application for photo/video management.

**Note:** Folders `__pycache__/`, files `__init__.py`, `tests/` and `.gitignore` elements are excluded for clarity.

```
.
├── dev-tools/
│   └── test_custom_spinbox.py
├── docs/
│   ├── PROJECT_TREE.md
│   └── Services.md
├── fixtures/
│   └── cache_test/
├── tests/
│   ├── unit/
│   │   ├── services/
│   │   │   ├── test_file_metadata_repository_cache.py  # 22 tests - Singleton, CRUD, persistence, thread-safety
│   │   │   ├── test_duplicates_exact_service.py        # 18 tests - Analysis, execution strategies, consecutive ops
│   │   │   ├── test_file_renamer_service.py            # 19 tests - Renaming logic, conflict resolution, cache updates
│   │   │   └── test_zero_byte_service.py               # 28 tests - Zero byte file detection
│   │   ├── ui/
│   │   └── utils/
│   │       └── test_date_utils_force_search.py          # Date extraction tests
│   ├── integration/
│   │   └── test_live_photos_integration.py
│   ├── performance/
│   │   └── test_large_dataset.py
│   ├── conftest.py
│   ├── README.md
│   └── test_base_service.py
├── scripts/
│   ├── demo_file_info_repository.py
│   ├── verify_refactor_smoke.py
│   └── verify_ui_imports.py
├── services/
│   ├── analysis_orchestrator.py
│   ├── base_service.py
│   ├── duplicates_base_service.py
│   ├── duplicates_exact_service.py
│   ├── duplicates_similar_service.py
│   ├── file_metadata_repository_cache.py
│   ├── file_metadata.py
│   ├── file_organizer_service.py
│   ├── file_renamer_service.py
│   ├── heic_service.py
│   ├── initial_scanner.py
│   ├── live_photos_service.py
│   ├── result_types.py
│   └── zero_byte_service.py
├── ui/
│   ├── dialogs/
│   │   ├── about_dialog.py
│   │   ├── base_dialog.py
│   │   ├── dialog_utils.py
│   │   ├── duplicates_exact_dialog.py
│   │   ├── duplicates_similar_dialog.py
│   │   ├── duplicates_similar_progress_dialog.py
│   │   ├── file_organizer_dialog.py
│   │   ├── file_renamer_dialog.py
│   │   ├── heic_dialog.py
│   │   ├── image_preview_dialog.py
│   │   ├── live_photos_dialog.py
│   │   ├── settings_dialog.py
│   │   └── zero_byte_dialog.py
│   ├── screens/
│   │   ├── analysis_phase_widget.py
│   │   ├── base_stage.py
│   │   ├── custom_spinbox.py
│   │   ├── dropzone_widget.py
│   │   ├── main_window.py
│   │   ├── progress_card.py
│   │   ├── similarity_handlers.py
│   │   ├── stage_1_window.py
│   │   ├── stage_2_window.py
│   │   ├── stage_3_window.py
│   │   ├── summary_card.py
│   │   └── tool_card.py
│   ├── styles/
│   │   ├── design_system.py
│   │   └── icons.py
│   └── workers/
│       ├── analysis_workers.py
│       ├── base_worker.py
│       ├── execution_workers.py
│       └── initial_analysis_worker.py
├── utils/
│   ├── callback_utils.py
│   ├── date_utils.py
│   ├── file_utils.py
│   ├── format_utils.py
│   ├── image_loader.py
│   ├── logger.py
│   ├── platform_utils.py
│   ├── screen_utils.py
│   ├── settings_manager.py
│   ├── storage.py
│   └── video_thumbnail.py
├── .github/
│   └── copilot-instructions.md
├── AGENTS.md
├── config.py
├── LICENSE
├── main.py
├── pytest.ini
├── requirements-dev.txt
└── requirements.txt
```
