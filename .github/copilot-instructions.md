## Innerpix Lab - AI Assistant Instructions

PyQt6 desktop app for photo/video management oriented to privacy.

### Flujo de Análisis
1. **Stage 2**: Escaneo inicial multi-fase usando `InitialScanner.scan()` → `DirectoryScanResult`. 6 fases diferenciadas:
   - Fase 1 (FILE_CLASSIFICATION): Escaneo y clasificación de archivos por tipo → "Escaneando estructura de carpetas"
   - Fase 2 (FILESYSTEM_METADATA): Lectura de metadata del filesystem → "Obteniendo información de archivos"
   - Fase 3 (HASH): Cálculo de hashes SHA256 → "Calculando hashes de archivos"
   - Fase 4 (EXIF_IMAGES): Extracción de metadatos de imágenes → "Extrayendo metadatos de imágenes"
   - Fase 5 (EXIF_VIDEOS): Extracción de metadatos de videos → "Extrayendo metadatos de vídeos"
   - Fase 6 (BEST_DATE): Cálculo de mejor fecha disponible → "Determinando fecha óptima"
2. **Stage 3**: Análisis bajo demanda para cada herramienta
   - Live Photos: `LivePhotoService.analyze()` → `LivePhotosAnalysisResult`
   - HEIC/JPG: `HeicService.analyze()` → `HeicAnalysisResult`
   - Copias exactas: `DuplicatesExactService.analyze()` → `DuplicateAnalysisResult`
   - Archivos similares: `DuplicatesSimilarService.analyze()` → `DuplicateAnalysisResult`
   - Archivos vacíos: `ZeroByteService.analyze()` → `ZeroByteAnalysisResult`
   - Renombrar: `FileRenamer.analyze()` → `RenameAnalysisResult`
   - Organizar: `FileOrganizer.analyze()` → `OrganizationAnalysisResult`
- Detectors: `ExactCopiesDetector` (SHA256), `SimilarFilesDetector` (perceptual hash)
- Other services: `FileOrganizerService`, `FileRenamerService`, `HeicService`, `LivePhotoService` (singular, not LivePhotosService)

**File Metadata Repository Cache** (`services/file_metadata_repository_cache.py`) - Singleton cache system (SQLite migration ready)
- **Pattern**: `FileInfoRepositoryCache.get_instance()` - NOT passed as parameter to services
- **Population**: Use `populate_from_scan(files, strategy, stop_check_callback)` - bulk loading with strategies (incremental)
  - `FILESYSTEM_METADATA`: Solo filesystem metadata (rápido, OBLIGATORIO primero)
  - `HASH`: Solo SHA256 hashes (requiere FILESYSTEM_METADATA previo, para duplicados exactos)
  - `EXIF_IMAGES`: Solo EXIF de imágenes (requiere FILESYSTEM_METADATA previo, moderado)
  - `EXIF_VIDEOS`: Solo EXIF de videos (requiere FILESYSTEM_METADATA previo, muy costoso)
  - `BEST_DATE`: Calcula mejor fecha disponible (requiere EXIF previo, rápido)
- **Incremental workflow**: FILESYSTEM_METADATA siempre primero, luego estrategias específicas según necesidad
- **No Auto-fetch**: Repositorio pasivo. Si el dato no está en caché, retorna None o estructura vacía.
- **Consultas**: `get_file_metadata(path)`, `get_hash(path)`, `get_exif(path)`, `get_best_date(path)` - Solo lectura (O(1)).
- **Cancelación cooperativa**: `stop_check_callback` verifica cancelación en cada iteración del loop
- **Progress throttling**: Reporta cada 1% o cada 100 archivos (evita saturación Qt en datasets grandes)
- **Cache Management**:
  - `remove_file(path)`, `remove_files(paths)` - Después de operaciones destructivas
  - `move_file(old_path, new_path)` - Actualiza path en caché sin perder metadata (usado por FileRenamerService)
  - `set_max_entries(max)` - Ajuste dinámico con eviction LRU automático
  - `clear()` - Limpia todo entre datasets (usar `_invalidate_metadata_cache()` desde UI)
- **Persistence** (opcional):
  - `save_to_disk(path)` - Serializa cache completo a JSON con metadata y stats
  - `load_from_disk(path, validate=True)` - Deserializa cache, opcionalmente valida existencia de archivos
  - Formato versionado (version=1) para compatibilidad futura
  - Thread-safe con manejo robusto de errores (IOError, FileNotFoundError, ValueError)
- **LRU Eviction**: Score-based (EXIF video=20, EXIF imagen=12, hash=5) + age penalty
- **Stats**: `get_cache_statistics()` → `RepositoryStats` (total_files, files_with_hash, files_with_exif, cache_hits, cache_misses, hit_rate)
- **Thread-safe**: RLock para acceso concurrente + singleton lock
- **Magic methods**: `len(repo)`, `path in repo`, `repo[path]`
- **Future-proof**: Preparado para SQLite via Protocol interface (IFileRepository)

**Visual Identical Service** (`services/visual_identical_service.py`) - 100% visually identical copies
- **API**: `analyze()` → `VisualIdenticalAnalysisResult` with groups of perceptually identical files
- Uses perceptual hashing with threshold=0 (exact visual match)
- Automatic grouping and safe batch deletion with keep strategies (largest, smallest, oldest, newest)
- Result types: `VisualIdenticalGroup`, `VisualIdenticalAnalysisResult`, `VisualIdenticalExecutionResult`
- **Use case**: Detecting exact visual copies (same image in different formats/resolutions)

**Similar Files Analysis** (`services/duplicates_similar_service.py`) - 70-95% similar files
- **Standard API**: `analyze(sensitivity=85)` - Returns `DuplicateAnalysisResult`
- **Dialog API**: `get_analysis_for_dialog()` - Returns `DuplicatesSimilarAnalysis` for interactive UI
- `DuplicatesSimilarAnalysis`: Container for pre-calculated hashes, enables real-time re-clustering via `get_groups(sensitivity)`
- Internal methods:
  - `_calculate_perceptual_hashes(repo, callback, algorithm, hash_size, target, highfreq_factor)` - Expensive hash calculation (~5 min for 40k files), cached in memory
  - `_calculate_image_perceptual_hash(path, algorithm, hash_size, highfreq_factor)` - Hash for single image
  - `_calculate_video_perceptual_hash(path, algorithm, hash_size, highfreq_factor)` - Hash for single video (uses central frame)
- **Perceptual Hash Configuration** (via `Config`):
  - `PERCEPTUAL_HASH_ALGORITHM`: Algorithm to use ("dhash", "phash", "ahash"). Default: "phash"
    - dhash: Fast, good for crops/edits (compares adjacent pixel differences)
    - phash: Robust, DCT-based (better tolerance to size/brightness changes)
    - ahash: Fastest, simplest (compares with average brightness)
  - `PERCEPTUAL_HASH_SIZE`: Hash size (8, 16, 32). Default: 16 (256-bit hash)
  - `PERCEPTUAL_HASH_TARGET`: Files to process ("images", "videos", "both"). Default: "images"
  - `PERCEPTUAL_HASH_HIGHFREQ_FACTOR`: Highfreq factor for phash (4, 8). Default: 4
- Hamming distance: Perceptual hash comparison for similarity detection (bits depend on hash_size)
- Sensitivity scale: 70-95% in dialog (70=permissive more groups, 95=very similar few groups, 85=recommended)
- **Important**: For 100% identical files, use `VisualIdenticalService` instead
- **Use case**: Finding similar but not identical images (edits, crops, rotations)

**Initial Scanner** (`services/initial_scanner.py`) - Multi-phase Stage 2 scanner
- 6 fases secuenciales: FILE_CLASSIFICATION → FILESYSTEM_METADATA → HASH → EXIF_IMAGES → EXIF_VIDEOS → BEST_DATE
- Fase 1 separa escaneo/clasificación (muy rápida) de fase 2 que lee metadata del filesystem
- Callbacks: `phase_callback(phase_id, message)` para inicio, `progress_callback(PhaseProgress)` para progreso
- Población incremental usando `FileInfoRepositoryCache.populate_from_scan()` con estrategias específicas
- Cancelación: `request_stop()` detiene escaneo de forma segura
- Progreso reporta 0/total al inicio y total/total al final de cada fase

**File Metadata** (`services/file_metadata.py`) - Immutable data model
- Dataclass con: path, fs_size, fs_mtime, sha256, exif_* fields
- Propiedades: `is_image`, `is_video`, `has_hash`, `has_exif`, `extension`, `file_type`
- Serialización: `to_dict()` / `from_dict(data)` para persistencia
- Helper: `utils.file_utils.get_exif_from_image()` retorna dict con fechas EXIF disponibles

**Workers** (`ui/workers/`) - QThread background
- Base: `BaseWorker` with `progress_update`, `finished`, `error` signals
- Type-safe: hints on `__init__` and `run()`, TYPE_CHECKING for imports
- `InitialAnalysisWorker`: Stage 2 multi-phase scan worker, emits `phase_started(phase_id, message)`, `phase_completed(phase_id)`, `stats_update(dict)`
- On-demand workers: `LivePhotosAnalysisWorker`, `HeicAnalysisWorker`, `DuplicatesExactAnalysisWorker`, `VisualIdenticalAnalysisWorker`, `DuplicatesSimilarAnalysisWorker`, `ZeroByteAnalysisWorker`, `FileRenamerAnalysisWorker`, `FileOrganizerAnalysisWorker`

**UI Stages** (`ui/screens/`) - 3-stage flow
- Stage 1: Folder selector
- Stage 2: Analysis progress with graceful cancellation
  - Timeout: 30 segundos para cancelación cooperativa (datasets grandes)
  - Logging INFO cada 10% en fases 3, 4, 5, 6 (hash, EXIF images, EXIF videos, best date)
  - Invalidación de caché al volver a Stage 1 con `_invalidate_metadata_cache()`
- Stage 3: Tools grid → dialogs
- All extend `BaseStage`

## Critical Patterns

### Backup
All destructive ops accept `create_backup=True`
- `from utils.file_utils import launch_backup_creation`

### Simulation Mode
Dry-run mode for testing. No deletions/moves/renames.

### Config
`from config import Config` (static class)
- `Config.APP_NAME`, `Config.is_supported_file()`, etc.

### Logging (`utils/logger.py`)
- Init: `configure_logging(logs_dir, level="INFO", dual_log_enabled=True)`
- Use: `get_logger('Module')` not print()
- Dual logging: Creates 2 files when level=INFO/DEBUG and enabled:
  - Main log: All messages with level suffix (e.g., `innerpix_lab_20251204_220143_INFO.log`)
  - Warnings log: Only WARNING/ERROR (e.g., `innerpix_lab_20251204_220143_WARNERROR.log`)
- File deletion logs: Unified format `FILE_DELETED: <path> | Size: <size> | Type: <type> | Date: <date>`
  - Size usa `format_size()` desde `utils.format_utils` para mostrar unidades apropiadas (B, KB, MB, GB)
  - Import requerido: `from utils.format_utils import format_size`
- Simulation logs: `FILE_DELETED_SIMULATION:` prefix for dry-run operations
- Grep-friendly: `grep "FILE_DELETED:" logs/*.log` finds all deletions across tools
- Runtime control: `set_dual_log_enabled(bool)` to enable/disable on the fly

### Dialogs (extend `BaseDialog`)
- One Dialog per functionality
- settings_dialog for configuration
- about_dialog for app info

### UX Rules
- Professional Design
- Modern Design
- Consistent Design

**File Utils** (`utils/file_utils.py`) - Organized by thematic categories
- **FILE TYPE DETECTION**: `is_image_file()`, `is_video_file()`, `is_media_file()`, `is_supported_file()`, `get_file_type()`
- **SOURCE/ORIGIN DETECTION**: `detect_file_source()`, `is_whatsapp_file()`
- **FILE VALIDATION**: `validate_file_exists()`, `validate_directory_exists()`, `to_path()`
- **FILE HASHING**: `calculate_file_hash()`
- **BACKUP OPERATIONS**: `launch_backup_creation()`
- **FILE SYSTEM OPERATIONS**: `cleanup_empty_directories()`, `delete_file_securely()`, `find_next_available_name()`
- **METADATA EXTRACTION**: `get_file_stat_info()`, `get_exif_from_image()`, `get_exif_from_video()`
- **DATA STRUCTURES**: `FileInfo` (dataclass), `validate_and_get_file_info()`

## Development Workflow

**Date Utils** (`utils/date_utils.py`) - Date extraction and metadata retrieval
- **Core Functions**:
  - `select_best_date_from_file(file_metadata)` - Selects best representative creation date from FileMetadata (EXIF priority → filename → filesystem)
  - `get_all_metadata_from_file(file_path, force_search=False)` - Retrieves complete file metadata (cache-first, with force_search bypass)
  - `select_best_date_from_common_date_to_2_files(file1, file2, verbose=False)` - Compares dates for file pairs and gets the vest representative creation_date available in both files (Used by HEIC/JPG, Live Photos)
- **force_search Parameter**: 
  - When `True`, bypasses settings_manager configuration and forces extraction of all metadata (hash, EXIF)
  - Useful for on-demand analysis in dialogs requiring complete data
  - Default `False` respects user settings (precalculate_hashes, precalculate_image_exif, precalculate_video_exif)
- **Naming Functions**:
  - `format_renamed_name(date, file_type, extension, sequence)` - Generates standardized filename: YYYYMMDD_HHMMSS_TYPE[_SEQ].EXT
  - `is_renamed_filename(filename)` - Validates renamed filename pattern
  - `parse_renamed_name(filename)` - Extracts components from renamed filename
  - `extract_date_from_filename(filename)` - Extracts date from common filename patterns (IMG_*, WhatsApp, etc.)

**Other Utils**
- `callback_utils.py`, `format_utils.py`, `icons.py`

**Result Types** (`services/result_types.py`)
- **Base Classes**:
  - `BaseResult`: success, errors, message
  - `AnalysisResult`: Extends BaseResult, adds items_count, bytes_total, data
  - `ExecutionResult`: Extends BaseResult, adds items_processed, bytes_processed, files_affected, backup_path, dry_run
- **Analysis Results** (per service):
  - `RenameAnalysisResult`: renaming_plan, already_renamed, cannot_process, conflicts
  - `OrganizationAnalysisResult`: move_plan, root_directory, organization_type
  - `HeicAnalysisResult`: duplicate_pairs, heic_files, jpg_files, potential_savings_*
  - `DuplicateAnalysisResult`: groups, mode, total_duplicates, total_groups, space_wasted
  - `LivePhotosAnalysisResult`: groups, rejected_groups, potential_savings (property), total_space
    - Filtrado individual de imágenes: Si múltiples imágenes comparten nombre base con video, solo se rechazan las que excedan threshold
    - Grupos sin imágenes válidas van a `rejected_groups`
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
  - `zero_byte_dialog.py`: Gestión de archivos de cero bytes
  - `heic_dialog.py`: Gestión de pares HEIC/JPG, menú contextual
    - Muestra origen de fecha compartida entre pares HEIC/JPG
  - `live_photos_dialog.py`: Gestión de Live Photos (pares foto + video)
    - Muestra origen de fecha para imágenes y videos en columna dedicada
  - `duplicates_exact_dialog.py`: Gestión de duplicados exactos (SHA256), estrategias de eliminación
    - TreeWidget con columnas: Archivos, Tamaño, Fecha, Origen, Ubicación, Estado
    - Obtiene metadata del repositorio singleton con `FileInfoRepositoryCache.get_instance()`
    - Muestra origen de fecha (exif_datetime_original, mtime, etc.) en columna dedicada
  - `visual_identical_dialog.py`: Gestión de copias visuales idénticas (perceptual hash, threshold=0)
    - TreeView con estrategias: keep largest, smallest, oldest, newest
    - Paginación, búsqueda/filtro, menú contextual
    - Elimina copias exactas visualmente de forma automática y segura
  - `duplicates_similar_dialog.py`: Gestión de archivos similares (perceptual hash, 70-99%)
    - Slider de sensibilidad para ajuste en tiempo real
    - Revisión manual de grupos con archivos similares pero no idénticos
  - `file_organizer_dialog.py`: Organización de archivos, 3 modos (TO_ROOT, BY_MONTH, WHATSAPP_SEPARATE), paginación (200/page)
  - `file_renamer_dialog.py`: Renombrado de archivos, mapeos original → nuevo, indicadores de conflictos

- **Auxiliary Dialogs**:
  - `about_dialog.py`: Diálogo "Acerca de" con información de la aplicación
  - `settings_dialog.py`: Configuración de la aplicación
  - `dialog_utils.py`: Utilidades como `show_file_details_dialog()`, `open_file_with_default_app()`
  - `image_preview_dialog.py`: Visor de imágenes simple para previsualizaciones rápidas

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
- No empty try/except with pass
- Functions organized by thematic categories with section separators

### Testing
- **Framework**: pytest 9.0.2 + pytest-qt 4.5.0 + pytest-mock 3.15.1
- **Coverage**: 460+ tests passing (Dec 2025)
- **Test Structure**: Class-based organization (TestClassName), setup_method/teardown_method for isolation
- **Key Tests**:
  - `tests/unit/services/test_file_metadata_repository_cache.py` (22 tests) - Singleton, CRUD, persistence, thread-safety, LRU eviction
  - `tests/unit/services/test_duplicates_exact_service.py` (18 tests) - Analysis, execution strategies, dry run, consecutive operations
  - `tests/unit/services/test_file_renamer_service.py` (19 tests) - Renaming logic, conflict resolution, cache updates, idempotency
- **Integration Tests**: Verify consecutive operations (analyze → execute → analyze), multi-service interaction, cache consistency
- **Pattern**: Tests must verify behavior with repository singleton using `repo.clear()` in setup_method
- **Run Tests**: `source .venv/bin/activate && pytest` (full suite ~60s), `pytest tests/unit/services/test_*.py -v` (specific)

## Platform Support
- Primary: Windows
- Secondary: macOS/Linux
- Future: Android/iOS (UI/logic separation critical)

## Additional Notes

### Common Notes
- Directory selection: User chooses a root directory for recursive analysis including all subfolders; plans and results in dialogs are based on this scanned file set.
- All dialogs follow the preview → plan → execute pattern and respect the "backup-first" policy for destructive operations (backup option before delete/move/rename).
- Business logic is decoupled from UI (services in `services/`) and each Dialog acts as the user interface to inspect and accept plans generated by those services.

### Tech Stack and Scope
- InnerPix Lab is developed in Python and is a cross-platform desktop application (Linux, Windows, macOS).
- The desktop version uses Qt (e.g., PyQt6 / PySide6) for the UI.
- Simplicity and decoupling between business logic and UI are maintained to facilitate future iOS/Android migration. Mobile versions will be implemented with native libraries or the strategy decided at that time.
- For this reason, services in `services/` are PyQt6-free and act as the reusable layer that can be leveraged by future mobile implementations.
