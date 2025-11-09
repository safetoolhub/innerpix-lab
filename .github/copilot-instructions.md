## Pixaro Lab - AI coding assistant instructions

Pixaro Lab is a PyQt6 desktop app for managing photo/video collections (iOS-focused).
Core workflow: **analyze → preview → execute** with user confirmation at each step.

> **Project Structure:** See `PROJECT_TREE.md` for detailed directory layout and file descriptions.

> Note: The `docs/` folder contains the author's internal notes and should NOT be processed or considered part of the project; they are the author's private notes.

### Architecture (3-layer pattern)

**Services** (`services/`) - Pure business logic, no UI dependencies
- Pattern: `analyze_*()` returns dataclass results, `execute_*()` accepts `create_backup=True`
- All use centralized logger: `from utils.logger import get_logger; self.logger = get_logger('ServiceName')`
- Return types: **100% standardized dataclasses** from `services/result_types.py` 
  * All services return typed dataclasses: `RenameAnalysisResult`, `LivePhotoDetectionResult`, `OrganizationAnalysisResult`, `HeicAnalysisResult`, `DuplicateAnalysisResult`
  * All execution methods return: `RenameResult`, `LivePhotoCleanupResult`, `OrganizationResult`, `HeicDeletionResult`, `DuplicateDeletionResult`

- Examples: `FileRenamer.analyze_directory()` → `RenameAnalysisResult`, `LivePhotoCleaner.execute_cleanup()` → `LivePhotoCleanupResult`
- Orchestrator: `AnalysisOrchestrator.run_full_analysis()` → `FullAnalysisResult` (100% typed fields), coordinates multiple services with callback system (progress/phase/partial), 100% PyQt6-free
- Specialized detectors):
  * `ExactCopiesDetector` (`exact_copies_detector.py`): SHA256-based exact copy detection, 100% identical files
  * `SimilarFilesDetector` (`similar_files_detector.py`): Perceptual hash-based similar detection using imagehash/cv2
  * Both share `DuplicateGroup` dataclass and `execute_deletion()` pattern
  * Analysis returns `DuplicateAnalysisResult` with `mode='exact'` or `mode='perceptual'`

**Workers** (`ui/workers.py`) - QThread background tasks to keep UI responsive
- Base class: `BaseWorker` provides `progress_update`, `finished`, `error` signals
- **Type Safety:**
  * All `__init__` and `run()` methods have type hints
  * All workers override `finished` signal with semantic type documentation
  * Uses `TYPE_CHECKING` imports to avoid circular dependencies
  * Forward references with strings (e.g., `renamer: 'FileRenamer'`)
- Pattern: use `_create_progress_callback()` for consistent progress reporting
- All inherit stop mechanism: `self._stop_requested` flag checked during long operations
- Unified worker: `AnalysisWorker` delegates to `AnalysisOrchestrator` (services/), only handles Qt threading/signals (~100 lines)
- Worker types: `AnalysisWorker`, `RenamingWorker`, `LivePhotoCleanupWorker`, `FileOrganizerWorker`, `HEICRemovalWorker`, `DuplicateAnalysisWorker`, `SimilarFilesAnalysisWorker`, `DuplicateDeletionWorker`

**UI Stages** (`ui/stages/`) - 3-stage application flow implemented with separate window classes
- **Stage 1** (`stage_1_window.py`): Folder selector and welcome screen
- **Stage 2** (`stage_2_window.py`): Analysis progress with visual phase feedback (timers ensure 1+ second visibility per phase)
- **Stage 3** (`stage_3_window.py`): Tools grid with clickable cards leading to dialogs
- Transitions: Stage 1 → Stage 2 → Stage 3 (no going back without re-selection)
- Each stage inherits from `BaseStage` which provides common utilities like animations, persistence, and navigation

**UI Components** (`ui/widgets/`, `ui/dialogs/`, `ui/styles/`)
- **Widgets**: Reusable components (ToolCard, ProgressCard, AnalysisPhaseWidget, SummaryCard, DropzoneWidget)
- **Dialogs**: All extend `BaseDialog` which provides `add_backup_checkbox()` and `build_accepted_plan()` helpers
- **Design System**: Centralized styling in `ui/styles/design_system.py` (single source of truth for colors, spacing, typography)
- **Legacy Styles**: `ui/ui_styles.py` contains old CSS constants (being phased out)
- Dialog utilities: `ui/dialogs/dialog_utils.py` provides shared functions:
  * `open_file()`: Cross-platform file opener (xdg-open/open/start)
  * `open_folder()`: Cross-platform folder opener with file selection
  * `show_file_details_dialog()`: Professional 2-column dialog with file info (no scroll, compact layout)

**Icon usage and emojis:**
- For cross-platform consistency, all UI icons MUST come from the central Icon Manager which uses qtawesome (Material Design icons). Do NOT use emojis anywhere in the UI or in source strings that are rendered as icons. Emojis produce inconsistent rendering across platforms and are forbidden in the codebase.

**Design guidelines**
- All visual styling for widgets, dialogs and windows MUST use only the tokens and classes exposed by the `DesignSystem` class in `ui/styles/design_system.py`.
- Inline styles, ad-hoc QSS strings, or alternative style modules are disallowed. If a style is missing from `DesignSystem`, raise an issue or request an extension to `DesignSystem` instead of adding inline styles.
- The `DesignSystem` is the single source of truth for colors, spacing, typography, radii and component classes. Follow it strictly. In case you need to add new styles or modify any of them ask me explicitely. I want control over the additions to this module.

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

**Additional UI modules**:
- `ui/helpers.py`: Reusable UI helper functions extracted from main_window.py
- `ui/managers/logging_manager.py`: Centralized logging management for UI components
- `ui/validators/directory_validator.py`: Directory validation utilities for UI
- `utils/settings_manager.py`: High-level settings management using storage backends

**File utilities** (`utils/file_utils.py`)
- `calculate_file_hash()`: SHA256 with optional caching
- `to_path()`: flexible path extraction from objects/dicts (checks `path`, `source_path`, `original_path` attrs)
- `cleanup_empty_directories()`: recursive removal after file operations
- `find_next_available_name()`: generates conflict-free names with `_XXX` suffix

**Additional utilities**:
- `utils/callback_utils.py`: Safe progress callback handling utilities
- `utils/date_utils.py`: Date extraction utilities for multimedia files
- `utils/format_utils.py`: Reusable formatting functions (format_size, format_file_count, etc.)
- `utils/icons.py`: Centralized icon management system using QtAwesome (Material Design icons)

**Result types** (`services/result_types.py`)
- **Status:** 
- Base: `OperationResult` (success, errors list, message)
- Analysis results: `RenameAnalysisResult`, `OrganizationAnalysisResult`, `LivePhotoCleanupAnalysisResult`, `LivePhotoDetectionResult`, `DuplicateAnalysisResult`, `HeicAnalysisResult`
- Operation results: `RenameResult`, `OrganizationResult`, `DeletionResult`, `LivePhotoCleanupResult`, `DuplicateDeletionResult`, `HeicDeletionResult`
- **Rule:** ALL services return dataclasses from this module, NEVER return raw dicts

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

- **Duplicates dialogs**:
  * **Exact copies** (`ui/dialogs/exact_copies_dialog.py`): SHA256 hash-based exact match detection
    - TreeWidget with expandable groups showing identical files
    - Strategies: keep first/last/largest/smallest/manual
    - Pagination for large result sets (50 initial, 50 increment)
    - Search and filter capabilities
    - Checkbox for backup creation before deletion
  * **Similar files** (`ui/dialogs/similar_files_dialog.py`): Perceptual hash-based visual similarity
    - Two-phase analysis: expensive hash calculation once, fast reclustering on-demand
    - Interactive sensitivity slider (30-100%) with real-time result updates
    - TreeWidget with similarity scores and dynamic grouping
    - Instant statistics updates (groups count, recoverable space)
    - Checkbox for backup creation before deletion

### Developer Workflow

Setup: `uv venv --python 3.13 && source .venv/bin/activate && uv pip install -r requirements.txt`
- Note: `pillow-heif` requires system `libheif` library (apt/brew install)

Run: `source .venv/bin/activate && python main.py`
- Logs: `~/Documents/Pixaro_Lab/logs/` by default
- Use `utils.logger.set_global_log_level(logging.DEBUG)` for verbose output

Project files:
- `PROJECT_TREE.md`: Complete project structure and file descriptions
- `CHANGELOG.md`: Version history and changes
- `.vscode/`: VS Code workspace configuration (launch, tasks, settings, keybindings)

### Code Quality Rules

- **Strict PEP 8**: use type hints where present, maintain existing patterns
- **Type Safety Priority** ✅:
  * ✅ All services return dataclasses (see `services/result_types.py`)
  * ✅ No more `Union[Dataclass, Dict]` - single type per interface
  * ✅ All public methods typed: `def analyze_foo(path: Path) -> FooAnalysisResult:`
  * ✅ All workers 100% typed: `__init__`, `run()`, and semantic signal documentation
  * ✅ TYPE_CHECKING pattern for avoiding circular imports
  * ✅ View Models created for UI/logic separation (`services/view_models.py`)
  * 🎯 **100% desacoplamiento UI/Lógica:** CUMPLIDO
- **No empty try/except**: avoid `except: pass` blocks
- **Dataclass-first**: When adding new services, ALWAYS return dataclasses from `result_types.py`
- **View Model pattern**: Use View Models from `services/view_models.py` for presentation logic (optional integration)
- **Preserve backup flows**: never remove `create_backup` parameters without explicit request
- **Import resolution**: `ui/ui_styles.py` contains legacy CSS constants (being phased out), `ui/styles/design_system.py` is the single source of truth for current styling


### Platform Notes

- Primary: Windows (some paths use `Path.home() / "Documents"`)
- Secondary: macOS/Linux supported
- Future: Android, iOS (that's why the UI must be separated from business logic)
- Qt environment: `main.py` sets `QT_LOGGING_RULES='qt.qpa.wayland=false'` to suppress Wayland warnings
