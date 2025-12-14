## Innerpix Lab - AI Assistant Instructions

PyQt6 desktop app for photo/video management. Workflow: **analyze → preview → execute**.
See `PROJECT_TREE.md` for structure. Ignore `docs/` (author's notes).

### Flujo de Análisis
1. **Stage 2**: Escaneo inicial usando `DirectoryScanner.scan()` → `DirectoryScanResult`. Para analisis de ficheros y de metadatos. No se analizan tools especificas
2. **Stage 3**: Análisis bajo demanda para cada herramienta
   - Live Photos: `LivePhotoService.analyze()` → `LivePhotosAnalysisResult`
   - HEIC/JPG: `HeicService.analyze()` → `HeicAnalysisResult`
   - Copias exactas: `DuplicatesExactService.analyze()` → `DuplicateAnalysisResult`
   - Archivos similares: `DuplicatesSimilarService.analyze()` → `DuplicateAnalysisResult`
   - Archivos vacíos: `ZeroByteService.analyze()` → `ZeroByteAnalysisResult`
   - Renombrar: `FileRenamer.analyze()` → `RenameAnalysisResult`
   - Organizar: `FileOrganizer.analyze()` → `OrganizationAnalysisResult`
- Detectors: `ExactCopiesDetector` (SHA256), `SimilarFilesDetector` (perceptual hash)

**File Info Repository** (`services/file_info_repository.py`) - Singleton file information repository
- `FileInfoRepository`: Thread-safe singleton for file metadata and expensive operations
- Pattern: Services access via `FileInfoRepository.get_instance()` - NOT passed as parameter
- Auto-fetch: Methods retrieve data if cached, calculate/fetch if not (e.g., `get_hash()`)
- Uses: `utils.file_utils.calculate_file_hash()` instead of reimplementing
- Caches: SHA256 hashes, EXIF dates, file stats (size, type, timestamps)
- Shared across services: ExactCopiesDetector, HEICRemover share hashes
- Lifecycle: Singleton created in scan phase, services access directly
- Invalidation: `clear()` after destructive ops or dataset change
- Stats: `get_stats()` for hits/misses/hit_rate, `log_stats()` for logging
- Performance: `get_file_count()` optimized (O(1) vs len(get_all_files()))
- Thread-safe: Uses RLock for concurrent access + singleton lock
- Magic methods: `len(repo)`, `path in repo`, `repo.get_or_create(path)`
- Future-proof: Prepared for SQLite/PostgreSQL migration via Protocol interface
- Logging: Professional logging with `utils.logger.get_logger('FileInfoRepository')`

**Similar Files Analysis** (`services/similar_files_detector.py`) - Two-phase system
- Phase 1: `analyze_initial()` - Expensive perceptual hash calculation (~5 min for 40k files)
- Phase 2: `get_groups(sensitivity)` - Fast clustering with adjustable sensitivity (<1 sec)
- `SimilarFilesAnalysis`: Container for pre-calculated hashes, enables real-time re-clustering
- `find_new_groups()`: Incremental analysis for new files vs existing dataset
- Serialization: `save_to_file()` / `load_from_file()` for instant cache reload
- Hamming distance: 64-bit perceptual hash comparison for similarity detection
- Sensitivity scale: 30-100% (30=permissive, 100=identical only, 85=recommended)

**Workers** (`ui/workers.py`) - QThread background
- Base: `BaseWorker` with `progress_update`, `finished`, `error` signals
- Type-safe: hints on `__init__` and `run()`, TYPE_CHECKING for imports
- Unified: `AnalysisWorker` delegates to orchestrator

**UI Stages** (`ui/screens/`) - 3-stage flow
- Stage 1: Folder selector
- Stage 2: Analysis progress
- Stage 3: Tools grid → dialogs
- All extend `BaseStage`

**UI Components**
- Widgets: ToolCard, ProgressCard, SummaryCard, etc.
- Dialogs: extend `BaseDialog` with `add_backup_checkbox()`
- Design: `ui/styles/design_system.py` (single source of truth)
- Icons: qtawesome Material Design (NO emojis)
- Utils: `dialog_utils.py` (`open_file`, `open_folder`, `show_file_details_dialog`)

**Design Rules**
- ALL styling via `DesignSystem` class only.
- No inline styles, ad-hoc QSS, or emojis
- Ask before adding/modifying styles
- Remember that CSS is not available fully, it has to be compatible with qt

### Critical Patterns

**Backup**: All destructive ops accept `create_backup=True`
- `from utils.file_utils import launch_backup_creation`

**Config**: `from config import Config` (static class)
- `Config.APP_NAME`, `Config.is_supported_file()`, etc.

**Logging** (`utils/logger.py`)
- Init: `configure_logging(logs_dir, level="INFO", dual_log_enabled=True)`
- Use: `get_logger('Module')` not print()
- Thread-safe with RLock
- Dual logging: Creates 2 files when level=INFO/DEBUG and enabled:
  - Main log: All messages with level suffix (e.g., `innerpix_lab_20251204_220143_INFO.log`)
  - Warnings log: Only WARNING/ERROR (e.g., `innerpix_lab_20251204_220143_WARNERROR.log`)
- File deletion logs: Unified format `FILE_DELETED: <path> | Size: <size> | Type: <type> | Date: <date>`
- Simulation logs: `FILE_DELETED_SIMULATION:` prefix for dry-run operations
- Grep-friendly: `grep "FILE_DELETED:" logs/*.log` finds all deletions across tools
- Runtime control: `set_dual_log_enabled(bool)` to enable/disable on the fly

**Storage** (`utils/storage.py`)
- `JsonStorageBackend`: file-based, no PyQt6
- `QSettingsBackend`: native OS storage
- `SettingsManager` auto-detects
- Settings keys include: `KEY_DUAL_LOG_ENABLED` for dual logging preference

**Platform** (`utils/platform_utils.py`)
- `open_file_with_default_app`, `open_folder_in_explorer`
- Platform detection: `is_linux()`, `is_macos()`, `is_windows()`

**File Utils** (`utils/file_utils.py`)
- `calculate_file_hash()`, `to_path()`, `cleanup_empty_directories()`, `find_next_available_name()`

**Date Utils** (`utils/date_utils.py`)
- `select_chosen_date()`: EXIF → filename → video → filesystem
- GPS DateStamp: validation only (NOT primary source)

**Other Utils**
- `callback_utils.py`, `format_utils.py`, `icons.py`

**Result Types** (`services/result_types.py`)
- **Base Classes**:
  - `BaseResult`: success, errors, message
  - `AnalysisResult`: Extends BaseResult, adds items_count, bytes_total, data
  - `ExecutionResult`: Extends BaseResult, adds items_processed, bytes_processed, files_affected, backup_path, dry_run
- **Analysis Results** (per service):
  - `RenameAnalysisResult`: renaming_plan, already_renamed, cannot_process, conflicts
  - `OrganizationAnalysisResult`: move_plan, root_directory, organization_type, folders_to_create
  - `HeicAnalysisResult`: duplicate_pairs, heic_files, jpg_files, potential_savings_*
  - `DuplicateAnalysisResult`: groups, mode, total_duplicates, total_groups, space_wasted
  - `LivePhotosAnalysisResult`: groups, space_to_free, total_space
  - `ZeroByteAnalysisResult`: files
- **Execution Results** (per service):
  - `RenameExecutionResult`: renamed_files, conflicts_resolved
  - `OrganizationExecutionResult`: empty_directories_removed, moved_files, folders_created
  - `HeicExecutionResult`: format_kept
  - `DuplicateExecutionResult`: files_kept, keep_strategy
  - `LivePhotosExecutionResult`
  - `ZeroByteExecutionResult`
- **Directory Scanner Types**:
  - `DirectoryScanResult`: total_files, images, videos, others, metadata_cache, total_size, extensions breakdown
  - `ScanSnapshot`: directory, scan
- **Rule**: ALL services return dataclasses (no dicts)

**Dialogs** (extend `BaseDialog`)
- **Base Classes**:
  - `BaseDialog`: Clase base con métodos comunes como `add_backup_checkbox()`, `add_dry_run_checkbox()`

- **Tool Dialogs**:
  - `duplicates_exact_dialog.py`: Gestión de duplicados exactos (SHA256), estrategias de eliminación
  - `duplicates_similar_dialog.py`: Gestión de duplicados similares (perceptual hash), ajuste de sensibilidad en tiempo real
  - `duplicates_similar_progress_dialog.py`: Diálogo de progreso para análisis de similares
  - `file_organizer_dialog.py`: Organización de archivos, 3 modos (TO_ROOT, BY_MONTH, WHATSAPP_SEPARATE), paginación (200/page)
  - `file_renamer_dialog.py`: Renombrado de archivos, mapeos original → nuevo, indicadores de conflictos
  - `heic_dialog.py`: Gestión de pares HEIC/JPG, menú contextual
  - `live_photos_dialog.py`: Gestión de Live Photos (pares foto + video)
  - `zero_byte_dialog.py`: Gestión de archivos de cero bytes

- **Auxiliary Dialogs**:
  - `about_dialog.py`: Diálogo "Acerca de" con información de la aplicación
  - `settings_dialog.py`: Configuración de la aplicación
  - `dialog_utils.py`: Utilidades como `show_file_details_dialog()`, `open_file_with_default_app()`

**UX Rules**
- Never show empty dialogs
- Show QMessageBox for no-results
- Update tool cards with clear messages

### Workflow

**Setup**: `uv venv --python 3.13 && source .venv/bin/activate && uv pip install -r requirements.txt`
**Run**: `source .venv/bin/activate && python main.py`
**Test**: `source .venv/bin/activate && pytest`
**Install**: `uv pip install <package>` (within venv)

**Logs**: `~/Documents/Innerpix_Lab/logs/`
**Debug**: `utils.logger.set_global_log_level(logging.DEBUG)`

### Code Quality

- PEP 8 + type hints
- All services return dataclasses (no dicts)
- All public methods typed
- No empty try/except
- Preserve `create_backup` params
- `DesignSystem` only for styling

### Testing

- Use fixtures: `temp_dir`, `create_test_image`, etc.
- Markers: `@pytest.mark.unit`, `@pytest.mark.slow`
- Structure: Arrange-Act-Assert

**Test Structure**:
```
tests/
├── conftest.py              # Shared fixtures (temp_dir, create_test_image, etc.)
├── unit/                    # Unit tests (isolated logic)
│   ├── services/           # Service tests (all 6 tools covered)
│   │   ├── test_metadata_cache.py
│   │   ├── test_exact_copies_detector.py
│   │   ├── test_similar_files_detector.py
│   │   ├── test_live_photos_service.py
│   │   ├── test_heic_remover_service.py
│   │   ├── test_file_organizer_service.py
│   │   └── test_analysis_orchestrator.py
│   └── utils/              # Utils tests (file_utils, date_utils, etc.)
├── integration/            # Integration tests (multiple components)
├── performance/            # Performance tests (large datasets)
└── ui/                     # UI tests (minimal, PyQt6 required)
```

**Pytest Markers**:
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Tests >1 second
- `@pytest.mark.performance` - Large dataset tests
- Functional: `live_photos`, `duplicates`, `similar`, `heic`, `renaming`, `organization`

**Key Fixtures** (`conftest.py`):
- `temp_dir` - Auto-cleanup temp directory
- `create_test_image(path, size, color, format)` - Image factory
- `create_test_video(path, size)` - Video factory
- `create_live_photo_pair(dir, name)` - Photo+video pair
- `sample_live_photos_directory(temp_dir)` - Complete test dataset

**Running Tests**:
```bash
pytest                              # All tests
pytest tests/unit/                  # Unit tests only
pytest -m "unit and not slow"       # Fast unit tests
pytest -k "cache"                   # Tests matching "cache"
pytest --cov=services --cov=utils --cov-report=html  # With coverage
```

**Test Pattern**:
```python
@pytest.mark.unit
class TestServiceAspect:
    def test_behavior(self, temp_dir):
        # Arrange
        service = Service()
        # Act
        result = service.method(temp_dir)
        # Assert
        assert result.success == True
```

**Coverage Requirements**:
- Services: 80%+ (comprehensive business logic)
- Utils: 90%+ (critical shared code)
- HTML reports: `htmlcov/index.html`

See `tests/README.md` for details.

### Platform

- Primary: Windows
- Secondary: macOS/Linux
- Future: Android/iOS (UI/logic separation critical)
