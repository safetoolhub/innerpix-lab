## Pixaro Lab - AI coding assistant instructions

Pixaro Lab is a PyQt6 desktop app for managing photo/video collections (iOS-focused).
Core workflow: **analyze → preview → execute** with user confirmation at each step.

> **Project Structure:** See `PROJECT_TREE.md` for detailed directory layout and file descriptions.

> Nota: La carpeta `docs/` contiene notas internas del autor y NO debe procesarse ni considerarse parte del proyecto; son apuntes privados del autor.

### Architecture (3-layer pattern)

**Services** (`services/`) - Pure business logic, no UI dependencies
- Pattern: `analyze_*()` returns dataclass results, `execute_*()` accepts `create_backup=True`
- All use centralized logger: `from utils.logger import get_logger; self.logger = get_logger('ServiceName')`
- Return types: standardized dataclasses from `services/result_types.py` (e.g., `AnalysisResult`, `DeletionResult`, `OrganizationResult`)
- Examples: `FileRenamer.analyze_directory()`, `LivePhotoCleaner.execute_cleanup(create_backup=True)`
- Orchestrator: `AnalysisOrchestrator.run_full_analysis()` coordinates multiple services with callback system (progress/phase/partial), 100% PyQt6-free

**Workers** (`ui/workers.py`) - QThread background tasks to keep UI responsive
- Base class: `BaseWorker` provides `progress_update`, `finished`, `error` signals
- Pattern: use `_create_progress_callback()` for consistent progress reporting
- All inherit stop mechanism: `self._stop_requested` flag checked during long operations
- Unified worker: `AnalysisWorker` delegates to `AnalysisOrchestrator` (services/), only handles Qt threading/signals (~50 lines)

**Controllers** (`ui/controllers/`) - Bridge between UI and services, manage worker lifecycle
- Pattern: instantiate worker → connect signals → start thread → update UI on completion
- Handle preview dialogs (subclasses of `BaseDialog`), execute flows, and re-analysis triggers
- Example: `AnalysisController.start_analysis()` creates `AnalysisWorker`, connects to `ProgressController`

**UI Components** (`ui/dialogs/`, `ui/components/`)
- Dialogs extend `BaseDialog` which provides `add_backup_checkbox()` and `build_accepted_plan()` helpers
- Main window: `ui/main_window.py` orchestrates controllers, maintains `self.analysis_results` state
- Dialog utilities: `ui/dialogs/dialog_utils.py` provides shared functions:
  * `open_file()`: Cross-platform file opener (xdg-open/open/start)
  * `open_folder()`: Cross-platform folder opener with file selection
  * `show_file_details_dialog()`: Professional 2-column dialog with file info (no scroll, compact layout)
  - Responsive interface

**Icon usage and emojis (ENGLISH):**
- For cross-platform consistency, all UI icons MUST come from the central Icon Manager which uses qtawesome (Material Design icons). Do NOT use emojis anywhere in the UI or in source strings that are rendered as icons. Emojis produce inconsistent rendering across platforms and are forbidden in the codebase.

**Design guidelines (ENGLISH) — REQUIRED:**
- All visual styling for widgets, dialogs and windows MUST use only the tokens and classes exposed by the `DesignSystem` class in `ui/styles/design_system.py`.
- Inline styles, ad-hoc QSS strings, or alternative style modules are disallowed. If a style is missing from `DesignSystem`, raise an issue or request an extension to `DesignSystem` instead of adding inline styles.
- The `DesignSystem` is the single source of truth for colors, spacing, typography, radii and component classes. Follow it strictly.

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

**Storage abstraction** (`utils/storage.py`) - Platform-agnostic persistence
- Interface: `StorageBackend` (ABC) defines `get()`, `set()`, `remove()`, `clear()`, `contains()`, `sync()`
- `JsonStorageBackend`: File-based storage (default: `~/.pixaro_lab/settings.json`), no PyQt6 dependency
- `QSettingsBackend`: Wrapper for PyQt6 QSettings, native OS storage (registry/plist/ini)
- `SettingsManager` auto-detects: uses QSettings if PyQt6 available, else JSON
- **Benefits**: Utils layer 100% PyQt6-free, enables CLI scripts, faster tests, easy framework migration

**Platform utilities** (`utils/platform_utils.py`) - OS interaction without UI
- `open_file_with_default_app(path, error_callback)`: Opens files with system default app (xdg-open/open/start)
- `open_folder_in_explorer(path, select_file, error_callback)`: Opens folders with optional file selection
- Platform detection: `is_linux()`, `is_macos()`, `is_windows()`, `get_platform_info()`
- `get_default_file_manager()`: Detects system file manager (nautilus/Finder/explorer)
- **Benefits**: Reusable in CLI scripts, no PyQt6 dependency, integrated logging, robust validation
- UI wrappers in `dialog_utils.py` add QMessageBox for error display

**File utilities** (`utils/file_utils.py`)
- `calculate_file_hash()`: SHA256 with optional caching
- `to_path()`: flexible path extraction from objects/dicts (checks `path`, `source_path`, `original_path` attrs)
- `cleanup_empty_directories()`: recursive removal after file operations
- `find_next_available_name()`: generates conflict-free names with `_XXX` suffix

**Result types** (`services/result_types.py`)
- All service results are dataclasses with type safety and validation
- Base: `OperationResult` (success, errors list, message)
- Specialized: `RenameResult`, `DeletionResult`, `OrganizationResult`, `LivePhotoAnalysisResult`, etc.

**Dialog patterns** (all extend `BaseDialog` for consistent UX):

- **Organization dialog** (`ui/dialogs/organization_dialog.py`):
  * Three visualization modes: TO_ROOT, BY_MONTH, WHATSAPP_SEPARATE
  * Dynamic column headers per mode (e.g., TO_ROOT shows "Estado", BY_MONTH shows "Fecha")
  * TreeWidget with smart grouping (by destination/month/category)
  * Pagination system: 200 items/page, auto-activates at 500+ files
  * Context menu with file details and folder opening
  * Fast plan regeneration: `main_window._regenerate_organization_plan()` avoids full re-analysis when switching types

- **HEIC dialog** (`ui/dialogs/heic_dialog.py`):
  * TableWidget showing HEIC/JPG duplicate pairs side by side
  * Columns: HEIC file, size, JPG file, size
  * Context menu with "Ver detalles" for both HEIC and JPG files
  * Shows comparison metadata in details (file type, sizes)
  * Checkbox for backup creation before deletion

- **Renaming dialog** (`ui/dialogs/renaming_dialog.py`):
  * TableWidget showing original → new filename mappings
  * Columns: Original name, New name, Size, Conflict status
  * Context menu with file details showing rename metadata
  * Visual indicators for conflicts (⚠️) and sequences
  * Checkbox for backup creation and dry run mode

- **Live Photos dialog** (`ui/dialogs/live_photos_dialog.py`):
  * TreeWidget grouping by base name (photo groups)
  * Shows photo + video pairs for each Live Photo
  * Displays file sizes and types
  * Checkbox for backup creation before cleanup

- **Duplicates dialogs** (`ui/dialogs/duplicates_dialogs.py`):
  * Multiple strategies: keep first/last/largest/smallest
  * Preview showing files to keep vs delete
  * Hash-based duplicate detection
  * Checkbox for backup creation before deletion

### Developer Workflow

Setup: `uv venv --python 3.13 && source .venv/bin/activate && uv pip install -r requirements.txt`
- Note: `pillow-heif` requires system `libheif` library (apt/brew install)

Run: `source .venv/bin/activate && python main.py`
- Logs: `~/Documents/Pixaro_Lab/logs/` by default
- Use `utils.logger.set_global_log_level(logging.DEBUG)` for verbose output

### Code Quality Rules

- **Strict PEP 8**: use type hints where present, maintain existing patterns
- **No empty try/except**: avoid `except: pass` blocks
- **No legacy callbacks or compatibility wrappers**: single-author project, no backward compatibility needed
- **Preserve backup flows**: never remove `create_backup` parameters without explicit request


### Platform Notes

- Primary: Windows (some paths use `Path.home() / "Documents"`)
- Secondary: macOS/Linux supported
- Future: Android, iOS (that's why the UI must be separated from business logic)
- Qt environment: `main.py` sets `QT_LOGGING_RULES='qt.qpa.wayland=false'` to suppress Wayland warnings
