# Innerpix Lab - Estructura del Proyecto

Aplicación PyQt6 para gestión de colecciones de fotos/videos (enfoque iOS).

**Nota:** Las carpetas `__pycache__/` y los archivos `__init__.py`, así como `tests/` y los elementos de `.gitignore` están excluidos de este árbol para mayor claridad.

```
.
├── dev-tools
│   └── test_custom_spinbox.py
├── fixtures
│   └── cache_test
├── scripts
│   ├── verify_refactor_smoke.py
│   └── verify_ui_imports.py
├── services
│   ├── analysis_orchestrator.py
│   ├── base_service.py
│   ├── directory_scanner.py
│   ├── duplicates_base_service.py
│   ├── duplicates_exact_service.py
│   ├── duplicates_similar_service.py
│   ├── file_organizer_service.py
│   ├── file_renamer_service.py
│   ├── heic_service.py
│   ├── live_photos_service.py
│   ├── metadata_cache.py
│   ├── result_types.py
│   ├── view_models.py
│   └── zero_byte_service.py
├── ui
│   ├── dialogs
│   │   ├── about_dialog.py
│   │   ├── base_dialog.py
│   │   ├── dialog_utils.py
│   │   ├── duplicates_exact_similar_dialog.py
│   │   ├── file_organizer_dialog.py
│   │   ├── file_renamer_dialog.py
│   │   ├── heic_dialog.py
│   │   ├── live_photos_dialog.py
│   │   ├── settings_dialog.py
│   │   ├── duplicates_similar_dialog.py
│   │   ├── duplicates_similar_progress_dialog.py
│   │   └── zero_byte_dialog.py
│   ├── stages
│   │   ├── base_stage.py
│   │   ├── stage_1_window.py
│   │   ├── stage_2_window.py
│   │   └── stage_3_window.py
│   ├── styles
│   │   └── design_system.py
│   ├── widgets
│   │   ├── analysis_phase_widget.py
│   │   ├── custom_spinbox.py
│   │   ├── dropzone_widget.py
│   │   ├── progress_card.py
│   │   ├── summary_card.py
│   │   └── tool_card.py
│   ├── workers
│   │   ├── analysis_workers.py
│   │   ├── base_worker.py
│   │   └── execution_workers.py
│   └── main_window.py
├── utils
│   ├── callback_utils.py
│   ├── date_utils.py
│   ├── file_utils.py
│   ├── format_utils.py
│   ├── icons.py
│   ├── image_loader.py
│   ├── logger.py
│   ├── platform_utils.py
│   ├── screen_utils.py
│   ├── settings_manager.py
│   ├── storage.py
│   └── video_thumbnail.py
├── AGENTS.md
├── config.py
├── LICENSE
├── main.py
├── pytest.ini
├── requirements-dev.txt
└── requirements.txt

13 directories, 63 files
```
