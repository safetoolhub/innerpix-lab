## Pixaro Lab - AI Assistant Instructions

PyQt6 desktop app for photo/video management. Workflow: **analyze → preview → execute**.
See `PROJECT_TREE.md` for structure. Ignore `docs/` (author's notes).

### Architecture (3-layer)

**Services** (`services/`) - Pure logic, no UI
- Pattern: `analyze()` returns dataclass, `execute()` accepts `create_backup=True`
- Logger: `from utils.logger import get_logger; self.logger = get_logger('ServiceName')`
- Returns: 100% typed dataclasses from `services/result_types.py`
- Orchestrator: `AnalysisOrchestrator.run_full_analysis()` → `FullAnalysisResult`
- Detectors: `ExactCopiesDetector` (SHA256), `SimilarFilesDetector` (perceptual hash)

**Metadata Cache** (`services/metadata_cache.py`) - Shared optimization system
- `FileMetadataCache`: Thread-safe cache for expensive operations
- Caches: SHA256 hashes, EXIF dates, file stats (size, type, timestamps)
- Shared across services: ExactCopiesDetector, HEICRemover share hashes
- Auto-sizing: `Config.get_max_cache_entries()` based on system RAM
- Lifecycle: Created in scan phase, passed to all services via orchestrator
- Invalidation: Auto-invalidates after destructive ops (delete/move)
- Stats: `get_stats()` for hits/misses/hit_rate monitoring
- Thread-safe: Uses RLock for concurrent access

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

**UI Stages** (`ui/stages/`) - 3-stage flow
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
  - Main log: All messages with level suffix (e.g., `pixaro_lab_20251204_220143_INFO.log`)
  - Warnings log: Only WARNING/ERROR (e.g., `pixaro_lab_20251204_220143_WARNERROR.log`)
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
- Base: `OperationResult`
- Analysis: `RenameAnalysisResult`, `OrganizationAnalysisResult`, etc.
- Operations: `RenameResult`, `DeletionResult`, etc.
- Rule: ALL services return dataclasses

**Dialogs** (extend `BaseDialog`)
- Organization: 3 modes (TO_ROOT, BY_MONTH, WHATSAPP_SEPARATE), pagination (200/page)
- HEIC: HEIC/JPG pairs, context menu
- Renaming: original → new mappings, conflict indicators
- Live Photos: photo + video pairs
- Duplicates: exact (SHA256) vs similar (perceptual), strategies, pagination

**UX Rules**
- Never show empty dialogs
- Show QMessageBox for no-results
- Update tool cards with clear messages

### Workflow

**Setup**: `uv venv --python 3.13 && source .venv/bin/activate && uv pip install -r requirements.txt`
**Run**: `source .venv/bin/activate && python main.py`
**Test**: `source .venv/bin/activate && pytest`
**Install**: `uv pip install <package>` (within venv)

**Logs**: `~/Documents/Pixaro_Lab/logs/`
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
