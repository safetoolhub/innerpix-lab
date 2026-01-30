# InnerPix Lab - Development Guide

> **Privacy-first photo/video management desktop application**  
> PyQt6 • Python 3.13+ • Cross-platform (Linux, Windows, macOS)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Patterns](#architecture--patterns)
3. [Core Components](#core-components)
4. [Development Workflow](#development-workflow)
5. [Testing Guidelines](#testing-guidelines)
6. [Code Quality Standards](#code-quality-standards)
7. [Platform Support](#platform-support)

---

## Project Overview

### Purpose
InnerPix Lab is a desktop application for managing, organizing, and optimizing photo/video collections with absolute privacy. All processing is 100% local—no cloud, no telemetry, no external connections.

### Tech Stack
- **Language**: Python 3.13+
- **UI Framework**: PyQt6
- **Package Manager**: uv
- **Testing**: pytest 9.0.2 + pytest-qt 4.5.0 + pytest-mock 3.15.1
- **Platforms**: Linux (primary), Windows, macOS

### Key Principles
1. **Privacy First**: All operations are offline and local
2. **UI/Logic Separation**: Business logic in `services/` (PyQt6-free), UI in `ui/`
3. **Type Safety**: PEP 8 + comprehensive type hints
4. **Dataclass Results**: All service outputs are immutable dataclasses
5. **Backup-First Policy**: Destructive operations always offer backups

---

## Architecture & Patterns

### Project Structure
```
innerpix-lab/
├── services/          # Business logic (PyQt6-free)
│   ├── *_service.py   # Service implementations
│   └── result_types.py # Dataclass result definitions
├── ui/
│   ├── screens/       # 3-stage workflow UI
│   ├── dialogs/       # Tool-specific dialogs
│   ├── workers/       # QThread background workers
│   ├── styles/        # DesignSystem + icons
│   └── tools_definitions.py # Centralized tool metadata
├── utils/             # Reusable utilities
└── tests/             # pytest test suites
```

### Core Patterns

#### Service Pattern
All services follow this contract:
```python
class SomeService:
    def analyze(self) -> SomeAnalysisResult:
        """Returns immutable dataclass with analysis results"""
        
    def execute(self, create_backup=True, dry_run=False) -> SomeExecutionResult:
        """Executes destructive operations with backup/simulation support"""
```

#### Singleton Cache Pattern
```python
# FileMetadata repository - singleton, NOT passed as parameter
repo = FileInfoRepositoryCache.get_instance()
metadata = repo.get_file_metadata(path)  # O(1) lookup
```

#### Worker Pattern
```python
# QThread workers for background operations
class SomeWorker(BaseWorker):
    progress_update = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
```

---

## Core Components

### 1. File Metadata Repository Cache
**Location**: `services/file_metadata_repository_cache.py`

**Pattern**: Singleton cache system (SQLite migration ready)
- `FileInfoRepositoryCache.get_instance()` - NOT passed as parameter to services
- **Population strategies** (incremental, must be called in order):
  - `FILESYSTEM_METADATA`: Fast, MANDATORY first (size, mtime, etc.)
  - `HASH`: SHA256 hashes (for exact duplicates)
  - `EXIF_IMAGES`: Image metadata (moderate cost)
  - `EXIF_VIDEOS`: Video metadata (very expensive)
  - `BEST_DATE`: Best representative date (fast, requires EXIF)
- **Operations**:
  - `get_file_metadata(path)`, `get_hash(path)`, `get_exif(path)`, `get_best_date(path)` - O(1) reads
  - `remove_file(path)`, `move_file(old, new)` - After destructive ops
  - `clear()` - Between datasets
  - `save_to_disk(path)`, `load_from_disk(path)` - Persistence (optional)
- **Features**: LRU eviction, thread-safe (RLock), progress throttling, cooperative cancellation

### 2. Initial Scanner
**Location**: `services/initial_scanner.py`

**6-phase Stage 2 scanner**:
1. `FILE_CLASSIFICATION`: File type detection → "Escaneando estructura de carpetas"
2. `FILESYSTEM_METADATA`: Read filesystem metadata → "Obteniendo información de archivos"
3. `HASH`: Calculate SHA256 hashes → "Calculando hashes de archivos"
4. `EXIF_IMAGES`: Extract image EXIF → "Extrayendo metadatos de imágenes"
5. `EXIF_VIDEOS`: Extract video EXIF → "Extrayendo metadatos de vídeos"
6. `BEST_DATE`: Calculate best date → "Determinando fecha óptima"

**Callbacks**:
- `phase_callback(phase_id, message)` - Phase start
- `progress_callback(PhaseProgress)` - Progress updates
- `request_stop()` - Graceful cancellation (30s timeout)

### 3. Analysis Services

#### Duplicates & Cleanup
- **`DuplicatesExactService`**: SHA256-based exact copies → `DuplicateAnalysisResult`
- **`VisualIdenticalService`**: Perceptual hash (threshold=0) for 100% visual matches → `VisualIdenticalAnalysisResult`
- **`DuplicatesSimilarService`**: 70-95% similarity detection → `DuplicateAnalysisResult`
  - Real-time re-clustering with sensitivity slider
  - Perceptual hash config: algorithm (phash/dhash/ahash), size (8/16/32), target (images/videos/both)
- **`ZeroByteService`**: 0-byte empty files → `ZeroByteAnalysisResult`
- **`HeicService`**: HEIC/JPG duplicate pairs → `HeicAnalysisResult`
- **`LivePhotoService`**: iPhone Live Photos (image + MOV) → `LivePhotosAnalysisResult`

#### Organization
- **`FileRenamerService`**: Standardize filenames (YYYYMMDD_HHMMSS_TYPE.ext) → `RenameAnalysisResult`
- **`FileOrganizerService`**: Reorganize by date/structure → `OrganizationAnalysisResult`

### 4. UI Workflow (3 Stages)

#### Stage 1: Folder Selection
- User selects root directory for recursive analysis

#### Stage 2: Analysis Progress
- Multi-phase scanning with graceful cancellation
- Progress reporting (0/total → total/total per phase)
- Logging: INFO every 10% for phases 3-6
- Cache invalidation when returning to Stage 1

#### Stage 3: Tools Grid
**8 Tools organized in 3 categories** (centralized in `ui/tools_definitions.py`):

**Category 1: Limpieza y espacio** (Libera espacio eliminando archivos innecesarios)
- **Archivos vacíos**: 0-byte files safe to delete
- **Live Photos**: iPhone image + MOV pairs
- **Duplicados HEIC/JPG**: HEIC/JPG duplicate pairs
- **Copias exactas**: 100% identical files (SHA256)

**Category 2: Detección visual** (Encuentra imágenes visualmente similares)
- **Copias visualmente idénticas**: 100% visual matches (perceptual hash, threshold=0)
- **Archivos similares**: 70-95% similar images (edits, crops, resolutions)

**Category 3: Organización** (Ordena y renombra tu colección)
- **Organización inteligente**: Reorganize by date structure
- **Renombrado completo**: Standardize filenames with dates

**Tool Cards Pattern**:
- Receive `analysis_results` and `on_click_callback`
- Exception: Organizar and Renombrar don't require prior analysis
- Definitions: `ToolDefinition` dataclass (id, title, short_description, long_description, icon_name)
- Categories: `ToolCategory` dataclass (id, title, description, tool_ids)

### 5. Result Types
**Location**: `services/result_types.py`

**Base Classes**:
- `BaseResult`: success, errors, message
- `AnalysisResult`: items_count, bytes_total, data
- `ExecutionResult`: items_processed, bytes_processed, files_affected, backup_path, dry_run

**Service-Specific Results**: Each service has dedicated `*AnalysisResult` and `*ExecutionResult` dataclasses.

**Rule**: ALL services return dataclasses (never dicts or tuples)

### 6. Utilities

#### File Utils (`utils/file_utils.py`)
Organized by thematic categories:
- **FILE TYPE DETECTION**: `is_image_file()`, `is_video_file()`, `is_media_file()`, `get_file_type()`
- **SOURCE/ORIGIN DETECTION**: `detect_file_source()`, `is_whatsapp_file()`
- **FILE VALIDATION**: `validate_file_exists()`, `validate_directory_exists()`, `to_path()`
- **FILE HASHING**: `calculate_file_hash()` (SHA256)
- **BACKUP OPERATIONS**: `launch_backup_creation()`
- **FILE SYSTEM OPERATIONS**: `delete_file_securely()`, `cleanup_empty_directories()`, `find_next_available_name()`
- **METADATA EXTRACTION**: `get_file_stat_info()`, `get_exif_from_image()`, `get_exif_from_video()`

#### Date Utils (`utils/date_utils.py`)
- `select_best_date_from_file(file_metadata)` - Best date from FileMetadata (EXIF → filename → filesystem)
- `get_all_metadata_from_file(path, force_search=False)` - Complete metadata (cache-first)
- `select_best_date_from_common_date_to_2_files(file1, file2)` - Best common date for pairs
- `format_renamed_name(date, file_type, ext, seq)` - YYYYMMDD_HHMMSS_TYPE[_SEQ].EXT
- `extract_date_from_filename(filename)` - Parse dates from IMG_*, WhatsApp patterns

#### Platform Utils (`utils/platform_utils.py`)
- **System Tools**: `check_ffprobe()`, `check_exiftool()`, `are_video_tools_available()`
- **File Operations**: `open_file_with_default_app()`, `open_folder_in_explorer()`
- **Platform Detection**: `is_linux()`, `is_macos()`, `is_windows()`
- **Hardware Info**: `get_cpu_count()`, `get_system_ram_gb()`, `get_system_info()`

#### Logging (`utils/logger.py`)
- **Init**: `configure_logging(logs_dir, level="INFO", dual_log_enabled=True)`
- **Usage**: `get_logger('ModuleName')` - Never use print()
- **Dual Logging**: Creates 2 files (main log + warnings-only log)
  - Main: `innerpix_lab_YYYYMMDD_HHMMSS_INFO.log`
  - Warnings: `innerpix_lab_YYYYMMDD_HHMMSS_WARNERROR.log`
- **File Deletion Format**: `FILE_DELETED: <path> | Size: <size> | Type: <type> | Date: <date>`
  - Always use `format_size()` from `utils.format_utils` for human-readable sizes
  - Simulation: `FILE_DELETED_SIMULATION:` prefix
- **Grep-friendly**: `grep "FILE_DELETED:" logs/*.log` finds all deletions
- **Runtime Control**: `set_dual_log_enabled(bool)` to toggle on/off

### 7. Dialogs
**Base**: All dialogs extend `BaseDialog` from `ui/dialogs/base_dialog.py`

**Common Methods**:
- `add_backup_checkbox()` - Backup option for destructive ops
- `add_dry_run_checkbox()` - Simulation mode toggle
- `create_tip_button(tip_message, width=450)` - Collapsible info popup

**Tool Dialogs**:
- `zero_byte_dialog.py` - Empty files management
- `heic_dialog.py` - HEIC/JPG pairs with context menu
- `live_photos_dialog.py` - Live Photos (image + video) management
- `duplicates_exact_dialog.py` - Exact copies with keep strategies
- `visual_identical_dialog.py` - Visual copies (perceptual hash = 0)
- `duplicates_similar_dialog.py` - Similar files (70-95% slider)
- `file_organizer_dialog.py` - File organization (3 modes, pagination)
- `file_renamer_dialog.py` - Rename preview with conflict indicators

**Auxiliary Dialogs**:
- `about_dialog.py` - App info and tutorial
- `settings_dialog.py` - Configuration
- `image_preview_dialog.py` - Quick image viewer

**UX Rules**:
- Never show empty dialogs (use QMessageBox for no-results)
- Follow preview → plan → execute pattern
- Update tool cards with clear status messages

---

## Development Workflow

### Environment Setup
```bash
# Create virtual environment with Python 3.13
uv venv --python 3.13
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

### Running the Application
```bash
source .venv/bin/activate
python main.py
```

### Running Tests
```bash
source .venv/bin/activate

# Full test suite (~60s, 590+ tests)
pytest

# Ignore performance tests
pytest --ignore=tests/performance

# Specific test file
pytest tests/unit/services/test_*.py -v

# With coverage
pytest --cov=services --cov-report=html
```

### Installing New Packages
```bash
# Within activated venv
uv pip install <package-name>

# Update requirements
uv pip freeze > requirements.txt
```

### Logs Location
- **Path**: `~/Documents/Innerpix_Lab/logs/`
- **Debug Mode**: `utils.logger.set_global_log_level(logging.DEBUG)`

---

## Testing Guidelines

### Framework
- **pytest 9.0.2** + **pytest-qt 4.5.0** + **pytest-mock 3.15.1**
- **Coverage**: 590+ tests passing (as of Jan 2026)

### Test Organization
```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Multi-service interactions
├── performance/    # Large dataset benchmarks
└── ui/             # PyQt6 UI tests
```

### Test Structure
- **Class-based**: Organize by functionality (e.g., `TestBasics`, `TestAnalyze`, `TestExecute`)
- **setup_method/teardown_method**: Ensure test isolation
- **Fixtures**: Centralized in `tests/conftest.py`

### Critical Patterns
1. **Singleton Repository**: Always use `repo = FileInfoRepositoryCache.get_instance()` and `repo.clear()` in setup_method
2. **FileMetadata Creation**: Include ALL required fields (path, fs_size, fs_ctime, fs_mtime, fs_atime)
3. **Repository API**: Use `repo.add_file(path, metadata)` with TWO parameters
4. **Integration Tests**: Verify consecutive operations (analyze → execute → analyze) to detect state bugs

### Test Types
- **Unit**: Fast, isolated, no I/O (mock filesystem)
- **Integration**: Multi-service interaction, cache consistency
- **Performance**: Large datasets (40k+ files), benchmarks
- **UI**: PyQt6 widgets (manual testing preferred when no automation)

### Test Naming
- **Pattern**: `test_<behavior>_when_<condition>` or `test_<behavior>_<scenario>`
- **Example**: `test_analyze_detects_duplicates_when_identical_hashes`

### Key Test Files
- `tests/unit/services/test_file_metadata_repository_cache.py` (22 tests) - Singleton, CRUD, persistence, LRU
- `tests/unit/services/test_duplicates_exact_service.py` (18 tests) - Analysis, execution, dry-run
- `tests/unit/services/test_file_renamer_service.py` (19 tests) - Renaming, conflicts, idempotency
- `tests/unit/services/test_perceptual_hash_algorithms.py` - Perceptual hash algorithms (phash/dhash/ahash)

### Testing Best Practices
- **No network access**: Tests must run offline (mock external I/O)
- **Deterministic**: Same input = same output (avoid random data)
- **Fast**: Unit tests should complete in milliseconds
- **Isolated**: No shared state between tests
- **Clear failures**: Assertions should explain what went wrong

---

## Code Quality Standards

### Style Guide
- **PEP 8**: Follow Python style guide
- **Type Hints**: All public functions and methods
- **Docstrings**: Use for classes and non-trivial functions
- **Imports**: Organized (standard → third-party → local)
  - Use `isort` for automatic organization

### Naming Conventions
- **Descriptive names**: Avoid single-letter variables (except loop indices)
- **Snake_case**: Functions, variables, modules
- **PascalCase**: Classes, dataclasses
- **UPPER_CASE**: Constants

### Code Organization
- **Services**: Business logic only, PyQt6-free
- **Dataclasses**: All service results (never dicts or tuples)
- **Functions**: Group by thematic categories with section separators
- **No try/except pass**: Always handle or log errors

### Error Handling
- **Never silent failures**: No bare `except: pass`
- **Logging**: Use `get_logger()` for all errors
- **User feedback**: Show meaningful error messages in UI

### Type Safety
```python
# ✅ Good
def analyze(self) -> AnalysisResult:
    return AnalysisResult(success=True, items_count=10)

# ❌ Bad
def analyze(self):
    return {"success": True, "items": 10}
```

### Backup & Simulation
- **All destructive operations**: Accept `create_backup=True` parameter
- **Dry-run mode**: Implement `dry_run=False` parameter
- **Logging**: Use `FILE_DELETED:` or `FILE_DELETED_SIMULATION:` prefixes

### Configuration
- **Config class**: `from config import Config`
- **Static access**: `Config.APP_NAME`, `Config.is_supported_file()`, etc.
- **No hardcoded values**: Use Config constants

### Design System
- **DesignSystem**: Use for all UI styling
- **No inline QSS**: Avoid manual stylesheets
- **Icons**: Use `icon_manager` from `ui/styles/icons.py`

---

## Platform Support

### Current Support
- **Primary**: Linux (Ubuntu, Fedora, Arch)
- **Secondary**: Windows 10/11, macOS 12+
- **Future**: Android, iOS (via native rewrite leveraging PyQt6-free services)

### Cross-Platform Considerations
- **Path separators**: Use `Path` from `pathlib`
- **Platform detection**: Use `utils.platform_utils` helpers
- **System tools**: Check availability (ffprobe, exiftool) before use
- **File operations**: Use cross-platform abstractions

---

## FAQ

### Where should I put new business logic?
In `services/` as a PyQt6-free service. UI code should only orchestrate and render.

### How do I test UI changes?
1. Run the application manually: `python main.py`
2. Use tests in `tests/ui/` if available
3. Prefer manual testing for complex UI flows

### How do I debug crashes?
1. Check logs in `~/Documents/Innerpix_Lab/logs/`
2. Enable DEBUG logging: `utils.logger.set_global_log_level(logging.DEBUG)`
3. Use `pytest -vv` for verbose test output

### How do I add a new tool?
1. Create service in `services/` with `analyze()` and `execute()`
2. Add result types to `services/result_types.py`
3. Add tool definition to `ui/tools_definitions.py`
4. Create dialog in `ui/dialogs/`
5. Create tool card in `ui/cards/`
6. Add worker in `ui/workers/` if needed
7. Write tests in `tests/unit/services/`

### How do I handle large datasets?
- Use cooperative cancellation: Check `stop_check_callback()` in loops
- Implement progress throttling: Report every 1% or 100 items
- Use incremental cache population: Start with FILESYSTEM_METADATA
- Consider pagination: Show 200 items per page in dialogs

---

## Additional Resources

### Common Notes
- **Directory selection**: User chooses root directory → recursive analysis of all subfolders
- **Backup policy**: All destructive operations offer backup before delete/move/rename
- **Preview pattern**: All dialogs follow preview → plan → execute flow
- **UI/Logic decoupling**: Services are reusable, dialogs are UI-only

### Tech Stack Evolution
- **Current**: PyQt6 desktop (Linux, Windows, macOS)
- **Future**: Native mobile apps (iOS, Android) reusing PyQt6-free services
- **Strategy**: Maintain strict UI/logic separation for future portability

---

**Last Updated**: January 2026  
**Test Coverage**: 590+ tests passing  
**Python Version**: 3.13+  
**UI Framework**: PyQt6
