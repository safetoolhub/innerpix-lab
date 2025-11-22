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
- ALL styling via `DesignSystem` class only
- NO inline styles, ad-hoc QSS, or emojis
- Ask before adding/modifying styles

### Critical Patterns

**Backup**: All destructive ops accept `create_backup=True`
- `from utils.file_utils import launch_backup_creation`

**Config**: `from config import Config` (static class)
- `Config.APP_NAME`, `Config.is_supported_file()`, etc.

**Logging** (`utils/logger.py`)
- Init: `configure_logging(logs_dir, level="INFO")`
- Use: `get_logger('Module')` not print()
- Thread-safe with RLock

**Storage** (`utils/storage.py`)
- `JsonStorageBackend`: file-based, no PyQt6
- `QSettingsBackend`: native OS storage
- `SettingsManager` auto-detects

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

- Focus: services/utils, not UI
- Use fixtures: `temp_dir`, `create_test_image`, etc.
- Markers: `@pytest.mark.unit`, `@pytest.mark.slow`
- Coverage: services 80%+, utils 90%+
- Structure: Arrange-Act-Assert

```python
@pytest.mark.unit
class TestServiceAspect:
    def test_behavior(self, temp_dir):
        service = Service()
        result = service.method(temp_dir)
        assert result.success == True
```

See `tests/README.md` for details.

### Platform

- Primary: Windows
- Secondary: macOS/Linux
- Future: Android/iOS (UI/logic separation critical)
