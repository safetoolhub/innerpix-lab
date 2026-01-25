# Innerpix Lab - Project Structure

PyQt6 desktop application for photo/video management.

**Note:** Folders `__pycache__/`, files `__init__.py`, `tests/` and `.gitignore` elements are excluded for clarity.

```
.
├── AGENTS.md
├── config.py
├── dev-tools/
│   ├── benchmark_clustering.py
│   ├── debug_all_exif_tags.py
│   ├── save_analysis_cache.py
│   ├── test_custom_spinbox.py
│   ├── test_default_sensitivity.py
│   ├── test_image_dimensions.py
│   └── verify_heic_bug_fix.py
├── docs/
│   ├── OPTIMIZATION_SIMILAR_FILES.md
│   ├── OPTIMIZATION_SIMILAR_FILES_OLD.md
│   ├── PLAN_DUPLICATES_SIMILAR_REFACTOR.md
│   ├── PLAN_SIMILAR_sonnet.md
│   ├── PROJECT_FUNCTIONALITIES.md
│   ├── PROJECT_TREE.md
│   ├── SIMILAR_FILES_SIZE_PRIORITIZATION.md
│   └── TODO.txt
├── LICENSE
├── main.py
├── pytest.ini
├── requirements-dev.txt
├── requirements.txt
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
│   ├── visual_identical_service.py
│   └── zero_byte_service.py
├── tests/
│   ├── conftest.py
│   ├── integration/
│   │   └── test_live_photos_integration.py
│   ├── performance/
│   │   ├── test_bktree_performance.py
│   │   └── test_large_dataset.py
│   ├── README.md
│   ├── test_base_service.py
│   ├── test_heic_service_refactor.py
│   ├── test_window_size.py
│   ├── ui/
│   │   ├── test_duplicates_similar_dialog.py
│   │   └── test_zero_byte_dialog.py
│   ├── unit/
│   │   ├── README_DYNAMIC_CONFIG_TESTS.md
│   │   ├── services/
│   │   │   ├── test_duplicates_exact_service.py
│   │   │   ├── test_duplicates_similar_service.py
│   │   │   ├── test_file_metadata_repository_cache.py
│   │   │   ├── test_file_renamer_service.py
│   │   │   ├── test_live_photos_service.py
│   │   │   ├── test_perceptual_hash_algorithms.py
│   │   │   ├── test_size_prioritization.py
│   │   │   ├── test_visual_identical_service.py
│   │   │   └── test_zero_byte_service.py
│   │   ├── test_dynamic_config.py
│   │   └── utils/
│   │       ├── test_callback_utils.py
│   │       ├── test_date_utils_force_search.py
│   │       ├── test_date_utils.py
│   │       ├── test_file_utils.py
│   │       ├── test_format_utils.py
│   │       ├── test_log_rotation_production.py
│   │       ├── test_log_rotation.py
│   │       ├── test_platform_utils.py
│   │       ├── test_screen_utils.py
│   │       └── test_storage.py
├── ui/
│   ├── dialogs/
│   │   ├── about_dialog.py
│   │   ├── base_dialog.py
│   │   ├── dialog_utils.py
│   │   ├── duplicates_exact_dialog.py
│   │   ├── duplicates_similar_dialog.py
│   │   ├── file_organizer_dialog.py
│   │   ├── file_renamer_dialog.py
│   │   ├── heic_dialog.py
│   │   ├── image_preview_dialog.py
│   │   ├── live_photos_dialog.py
│   │   ├── settings_dialog.py
│   │   ├── visual_identical_dialog.py
│   │   └── zero_byte_dialog.py
│   ├── screens/
│   │   ├── analysis_phase_widget.py
│   │   ├── base_stage.py
│   │   ├── custom_spinbox.py
│   │   ├── dropzone_widget.py
│   │   ├── main_window.py
│   │   ├── progress_card.py
│   │   ├── stage_1_window.py
│   │   ├── stage_2_window.py
│   │   ├── stage_3_window.py
│   │   ├── summary_card.py
│   │   ├── tool_card.py
│   │   └── tool_cards/
│   │       ├── duplicates_exact_card.py
│   │       ├── duplicates_similar_card.py
│   │       ├── file_organizer_card.py
│   │       ├── file_renamer_card.py
│   │       ├── heic_card.py
│   │       ├── live_photos_card.py
│   │       ├── visual_identical_card.py
│   │       └── zero_byte_card.py
│   ├── styles/
│   │   ├── design_system.py
│   │   └── icons.py
│   └── workers/
│       ├── analysis_workers.py
│       ├── base_worker.py
│       ├── execution_workers.py
│       └── initial_analysis_worker.py
└── utils/
    ├── callback_utils.py
    ├── date_utils.py
    ├── file_utils.py
    ├── format_utils.py
    ├── image_loader.py
    ├── logger.py
    ├── platform_utils.py
    ├── screen_utils.py
    ├── settings_manager.py
    ├── storage.py
    └── video_thumbnail.py
```
