## Pixaro Lab - AI coding assistant instructions

Pixaro Lab is a PyQt6 desktop app for managing photo/video collections (iOS-focused).
Core workflow: **analyze → preview → execute** with user confirmation at each step.

> **Project Structure:** See `PROJECT_TREE.md` for detailed directory layout and file descriptions.

### Architecture (3-layer pattern)

**Services** (`services/`) - Pure business logic, no UI dependencies
- Pattern: `analyze_*()` returns dataclass results, `execute_*()` accepts `create_backup=True`
- All use centralized logger: `from utils.logger import get_logger; self.logger = get_logger('ServiceName')`
- Return types: standardized dataclasses from `services/result_types.py` (e.g., `AnalysisResult`, `DeletionResult`, `OrganizationResult`)
- Examples: `FileRenamer.analyze_directory()`, `LivePhotoCleaner.execute_cleanup(create_backup=True)`

**Workers** (`ui/workers.py`) - QThread background tasks to keep UI responsive
- Base class: `BaseWorker` provides `progress_update`, `finished`, `error` signals
- Pattern: use `_create_progress_callback()` for consistent progress reporting
- All inherit stop mechanism: `self._stop_requested` flag checked during long operations
- Unified worker: `AnalysisWorker` runs full directory analysis (renaming, live photos, organization, HEIC, duplicates)

**Controllers** (`ui/controllers/`) - Bridge between UI and services, manage worker lifecycle
- Pattern: instantiate worker → connect signals → start thread → update UI on completion
- Handle preview dialogs (subclasses of `BaseDialog`), execute flows, and re-analysis triggers
- Example: `AnalysisController.start_analysis()` creates `AnalysisWorker`, connects to `ProgressController`

**UI Components** (`ui/tabs/`, `ui/dialogs/`, `ui/components/`)
- Tabs inherit from patterns in `ui/tabs/base_tab.py` (info labels, action buttons, details text)
- Dialogs extend `BaseDialog` which provides `add_backup_checkbox()` and `build_accepted_plan()` helpers
- Main window: `ui/main_window.py` orchestrates controllers, maintains `self.analysis_results` state

### Critical Patterns

**Backup-first operations**: All destructive operations accept `create_backup=True` (default)
- Implementation: `from utils.file_utils import launch_backup_creation`
- Creates timestamped backup dir with metadata file listing all affected files
- Example pattern in `services/heic_remover.py:execute_removal()`, `services/live_photo_cleaner.py:execute_cleanup()`
- UI: `BaseDialog.add_backup_checkbox()` provides user control, `is_backup_enabled()` reads state

**Config access**: All configuration is accessed via the `Config` class
- Import: `from config import Config`
- Static values: `Config.APP_NAME`, `Config.DEFAULT_LOG_DIR`, `Config.SUPPORTED_IMAGE_EXTENSIONS`
- Helper methods: `Config.is_supported_file()`, `Config.get_file_type()`, `Config.is_image_file()`
- All methods are @classmethod, no instance needed

**Logging conventions** (see `docs/LOGGING_CONVENTIONS.md`)
- Use `get_logger('ModuleName')` not print()
- Levels: DEBUG for internals, INFO for operations/results, WARNING for recoverable issues, ERROR for failures
- All logs written to timestamped file in `Config.DEFAULT_LOG_DIR`

**File utilities** (`utils/file_utils.py`)
- `calculate_file_hash()`: SHA256 with optional caching
- `to_path()`: flexible path extraction from objects/dicts (checks `path`, `source_path`, `original_path` attrs)
- `cleanup_empty_directories()`: recursive removal after file operations
- `find_next_available_name()`: generates conflict-free names with `_XXX` suffix

**Result types** (`services/result_types.py`)
- All service results are dataclasses with type safety and validation
- Base: `OperationResult` (success, errors list, message)
- Specialized: `RenameResult`, `DeletionResult`, `OrganizationResult`, `LivePhotoAnalysisResult`, etc.

### Developer Workflow

Setup: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Note: `pillow-heif` requires system `libheif` library (apt/brew install)

Run: `python main.py` (launches PyQt6 GUI)
- Logs: `~/Documents/Pixaro_Lab/logs/` by default
- Use `utils.logger.set_global_log_level(logging.DEBUG)` for verbose output

Debugging: Check `ui.managers.logging_manager.LoggingManager` for log file location
- Main window exposes: `self.logger`, `self.log_file`, `self.logs_directory`

### Code Quality Rules

- **Strict PEP 8**: use type hints where present, maintain existing patterns
- **No empty try/except**: avoid `except: pass` blocks
- **No legacy callbacks**: single-author project, no backward compatibility needed
- **Preserve backup flows**: never remove `create_backup` parameters without explicit request
- **Test UI paths**: run app locally and exercise analysis → preview → execute for file operations

### Platform Notes

- Primary: Windows (some paths use `Path.home() / "Documents"`)
- Secondary: macOS/Linux supported
- Qt environment: `main.py` sets `QT_LOGGING_RULES='qt.qpa.wayland=false'` to suppress Wayland warnings

