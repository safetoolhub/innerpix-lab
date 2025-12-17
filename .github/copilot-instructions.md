## Innerpix Lab - AI Assistant Instructions

PyQt6 desktop app for photo/video management oriented to privacy.

### Flujo de Análisis
1. **Stage 2**: Escaneo inicial multi-fase usando `InitialScanner.scan()` → `DirectoryScanResult`. 4 fases diferenciadas:
   - Fase 1 (BASIC): Análisis de estructura del directorio → "Analizando estructura de la carpeta"
   - Fase 2 (HASH): Cálculo de hashes SHA256 → "Calculando hashes de los archivos"
   - Fase 3 (EXIF_IMAGES): Extracción de metadatos de imágenes → "Obteniendo metadatos de las imagenes"
   - Fase 4 (EXIF_VIDEOS): Extracción de metadatos de videos → "Obteniendo metadatos de los videos"
2. **Stage 3**: Análisis bajo demanda para cada herramienta
   - Live Photos: `LivePhotoService.analyze()` → `LivePhotosAnalysisResult`
   - HEIC/JPG: `HeicService.analyze()` → `HeicAnalysisResult`
   - Copias exactas: `DuplicatesExactService.analyze()` → `DuplicateAnalysisResult`
   - Archivos similares: `DuplicatesSimilarService.analyze()` → `DuplicateAnalysisResult`
   - Archivos vacíos: `ZeroByteService.analyze()` → `ZeroByteAnalysisResult`
   - Renombrar: `FileRenamer.analyze()` → `RenameAnalysisResult`
   - Organizar: `FileOrganizer.analyze()` → `OrganizationAnalysisResult`
- Detectors: `ExactCopiesDetector` (SHA256), `SimilarFilesDetector` (perceptual hash)
- Other services: `FileOrganizerService`, `FileRenamerService`, `HeicRemoverService`, `LivePhotosService`

**File Metadata Repository Cache** (`services/file_metadata_repository_cache.py`) - Singleton cache system (SQLite migration ready)
- **Pattern**: `FileInfoRepositoryCache.get_instance()` - NOT passed as parameter to services
- **Population**: Use `populate_from_scan(files, strategy)` - bulk loading with strategies (incremental)
  - `BASIC`: Solo filesystem metadata (rápido, OBLIGATORIO primero)
  - `HASH`: Solo SHA256 hashes (requiere BASIC previo, para duplicados exactos)
  - `EXIF_IMAGES`: Solo EXIF de imágenes (requiere BASIC previo, moderado)
  - `EXIF_VIDEOS`: Solo EXIF de videos (requiere BASIC previo, muy costoso)
  - `EXIF_ALL`: EXIF de imágenes + videos (requiere BASIC previo, muy costoso)
  - `FULL`: Hash + EXIF completo (requiere BASIC previo, extremadamente costoso)
- **Incremental workflow**: BASIC siempre primero, luego estrategias específicas según necesidad
- **Auto-fetch**: Si metadata básica no existe, las estrategias la crean automáticamente
- **Auto-fetch**: `get_file_metadata(path, auto_fetch=True)`, `get_hash(path, auto_fetch=True)`, `get_exif(path, auto_fetch=False)`
- **Cache Management**:
  - `remove_file(path)`, `remove_files(paths)` - Después de operaciones destructivas
  - `set_max_entries(max)` - Ajuste dinámico con eviction LRU automático
  - `clear()` - Limpia todo entre datasets
- **Persistence** (opcional):
  - `save_to_disk(path)` - Serializa cache completo a JSON con metadata y stats
  - `load_from_disk(path, validate=True)` - Deserializa cache, opcionalmente valida existencia de archivos
  - Formato versionado (version=1) para compatibilidad futura
  - Thread-safe con manejo robusto de errores (IOError, FileNotFoundError, ValueError)
- **LRU Eviction**: Score-based (EXIF video=20, EXIF imagen=12, hash=5) + age penalty
- **Stats**: `get_stats()` → `RepositoryStats` (total_files, files_with_hash, files_with_exif, cache_hits, cache_misses, hit_rate)
- **Thread-safe**: RLock para acceso concurrente + singleton lock
- **Magic methods**: `len(repo)`, `path in repo`, `repo[path]`
- **Future-proof**: Preparado para SQLite via Protocol interface (IFileRepository)

**Similar Files Analysis** (`services/duplicates_similar_service.py`) - Two-phase system
- Phase 1: `analyze_initial()` - Expensive perceptual hash calculation (~5 min for 40k files)
- Phase 2: `get_groups(sensitivity)` - Fast clustering with adjustable sensitivity (<1 sec)
- `SimilarFilesAnalysis`: Container for pre-calculated hashes, enables real-time re-clustering
- `find_new_groups()`: Incremental analysis for new files vs existing dataset
- Serialization: `save_to_file()` / `load_from_file()` for instant cache reload
- Hamming distance: 64-bit perceptual hash comparison for similarity detection
- Sensitivity scale: 30-100% (30=permissive, 100=identical only, 85=recommended)

**Initial Scanner** (`services/initial_scanner.py`) - Multi-phase Stage 2 scanner
- 4 fases secuenciales: BASIC → HASH → EXIF_IMAGES → EXIF_VIDEOS
- Callbacks: `phase_callback(phase_id, message)` para inicio, `progress_callback(PhaseProgress)` para progreso
- Población incremental usando `FileInfoRepositoryCache.populate_from_scan()` con estrategias específicas
- Cancelación: `request_stop()` detiene escaneo de forma segura
- Clasificación automática: separa imágenes, videos y otros según extensión

**File Metadata** (`services/file_metadata.py`) - Immutable data model
- Dataclass con: path, fs_size, fs_mtime, sha256, exif_* fields
- Propiedades: `is_image`, `is_video`, `has_hash`, `has_exif`, `extension`, `file_type`
- Serialización: `to_dict()` / `from_dict(data)` para persistencia
- Helper: `utils.file_utils.get_exif_from_image()` retorna dict con fechas EXIF disponibles

**Workers** (`ui/workers/`) - QThread background
- Base: `BaseWorker` with `progress_update`, `finished`, `error` signals
- Type-safe: hints on `__init__` and `run()`, TYPE_CHECKING for imports
- `InitialAnalysisWorker`: Stage 2 multi-phase scan worker, emits `phase_started(phase_id, message)`, `phase_completed(phase_id)`, `stats_update(dict)`
- On-demand workers: `LivePhotosAnalysisWorker`, `HeicAnalysisWorker`, `DuplicatesExactAnalysisWorker`, etc.

**UI Stages** (`ui/screens/`) - 3-stage flow
- Stage 1: Folder selector
- Stage 2: Analysis progress
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

**File Utils** (`utils/file_utils.py`)
- Type detection: `is_image_file()`, `is_video_file()`, `is_media_file()`, `is_supported_file()`, `get_file_type()`
- Hash & paths: `calculate_file_hash()`, `to_path()`, `find_next_available_name()`
- Cleanup: `cleanup_empty_directories()`, `delete_file_securely()`
- Validation: `validate_directory_exists()`, `validate_file_exists()`

## Development Workflow

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

## Code Quality
- PEP 8 + type hints
- All services return dataclasses (no dicts)
- All public methods typed
- No empty try/except with pass

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
