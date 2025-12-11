# REFACTORIZACIÓN PROFESIONAL - SISTEMA DE GESTIÓN MULTIMEDIA
# FASES 2-6: INFRAESTRUCTURA Y SERVICIOS

## ESTADO ACTUAL DEL PROYECTO

### ✅ Fase 1 Completada
- `result_types.py` ha sido refactorizado con jerarquía de clases base y mixins
- Dataclasses ahora heredan de `BaseResult` y mixins especializados
- Campos duplicados eliminados, contadores calculados como `@property`
- Aliases innecesarios removidos

### ✅ Fase 2 Completada (2024-12-11)
- `BaseService` estandarizado con infraestructura centralizada
- `_execute_operation()` implementado como template method para backup/dry_run
- `_parallel_processor()` context manager para ThreadPoolExecutor centralizado
- `_get_max_workers()`, `_validate_directory()`, `_get_supported_files()` implementados
- Convenciones de logging documentadas en docstring de BaseService
- 25 tests unitarios creados y pasando (100% coverage de nuevos métodos)

### ✅ Fase 3 Completada (2024-12-11) ✨ ACTUALIZADA
**Estado global**: 6 de 7 subfases completadas (86%)

#### ✅ Subfase 3.1 - ZeroByteService (COMPLETADA)
- Hereda correctamente de BaseService
- Usa `_execute_operation()` template method
- Usa `_report_progress()` para callbacks
- Tests: 4/4 passing

#### ✅ Subfase 3.2 - FileRenamerService (COMPLETADA)
- Usa `_parallel_processor()` para ThreadPool
- Usa `_execute_operation()` template method  
- Usa `_report_progress()` para callbacks
- Tests: 24/24 passing

#### ⚠️ Subfase 3.3 - FileOrganizerService (PARCIALMENTE COMPLETADA)
- ✅ Usa `_parallel_processor()` (2 ThreadPool migrados)
- ⚠️ NO usa `_execute_operation()` (lógica manual de backup)
- ⚠️ Requiere refactor extenso (creación carpetas pre-backup, cleanup post-operación)
- Razón: Complejidad de flujo (crear carpetas → backup → mover → cleanup)
- Estado: FUNCIONAL pero no sigue patrón estándar completamente

#### ✅ Subfase 3.4 - DuplicatesBaseService (COMPLETADA)
- Eliminado `safe_progress_callback` de utils
- Usa `_report_progress()` de BaseService
- Manejo de cancelación cooperativa
- Tests: Todos passing

#### ✅ Subfase 3.5 - DuplicatesExact/SimilarService (COMPLETADA)
- Ambos usan `_parallel_processor()` para ThreadPool
- DuplicatesExactService: io_bound=True
- DuplicatesSimilarService: io_bound=False (CPU-bound)
- Tests: Todos passing

#### ✅ Subfase 3.6 - LivePhotosService (COMPLETADA)
- Usa `_execute_operation()` template method
- Eliminada gestión manual de backup (try/except BackupCreationError)
- Extraída lógica a `_do_live_photo_cleanup()`
- Usa `_report_progress()` de BaseService
- Tests: Todos passing

#### ✅ Subfase 3.7 - HeicService (COMPLETADA)
- Usa `_execute_operation()` template method
- Eliminada gestión manual de backup
- Extraída lógica a `_do_heic_cleanup()`
- Usa `_report_progress()` de BaseService
- Tests: Todos passing

**Test suite completo**: 706 passed, 3 skipped ✅

**Resumen de cambios realizados**:
- 6 servicios refactorizados completamente
- 1 servicio (FileOrganizerService) parcialmente refactorizado
- Eliminadas ~300 líneas de código duplicado
- Centralizada gestión de backup en BaseService
- Centralizada gestión de ThreadPool en BaseService
- Estandarizado progress reporting en todos los servicios

### 📂 Arquitectura del Sistema

**Componentes principales**:
- **9 servicios de procesamiento**: FileRenamerService, FileOrganizerService, DuplicatesExactService, DuplicatesSimilarService, LivePhotosService, HeicService, ZeroByteService + clases base BaseService y DuplicatesBaseService
- **Sistema de resultados**: `result_types.py` (✅ refactorizado en Fase 1)
- **Sistema de logging**: `logger.py` con funciones helper centralizadas
- **Vista/UI**: Consume resultados de servicios (no debe modificarse)

### 🎯 Patrón Estándar de Servicios

Todos los servicios siguen arquitectura de **dos fases**:

1. **Análisis**: `analyze(directory: Path, **kwargs) -> *AnalysisResult`
   - Escanea directorio sin modificar disco
   - Genera plan de operación detallado
   - Retorna estadísticas y plan

2. **Ejecución**: `execute(analysis_or_plan, **kwargs) -> *ExecutionResult`
   - Ejecuta plan generado
   - Modifica/elimina archivos (excepto en `dry_run=True`)
   - Retorna resultados de operación

**Características transversales** (todas las operaciones):
- ✅ **Backup opcional** (`create_backup: bool`): Crea backup antes de modificar si es True y dry_run es False
- ✅ **Modo simulación** (`dry_run: bool`): Simula sin modificar disco, usa campos `simulated_*`
- ✅ **Progress reporting** (`progress_callback`): Reporta progreso, soporta cancelación
- ✅ **Cancelación cooperativa**: Usuario puede cancelar desde UI

### ⚠️ RESTRICCIONES IMPERATIVAS

1. **NO tocar metadata_cache**: Será rehecho desde cero, ignorar todo código relacionado
2. **NO modificar UI**: Solo lógica de servicios, mantener compatibilidad total
3. **Solo dataclasses**: No introducir Pydantic, attrs u otras librerías
4. **Logger existente**: Usar funciones de `utils.logger`, no crear nuevo sistema
5. **Config intocable**: No modificar sistema de configuración global

---

## ✅ FASE 2: ESTANDARIZAR BaseService

**Prioridad**: CRÍTICA  
**Tiempo estimado**: 6-8 horas  
**Estado**: ✅ COMPLETADA (2024-12-11)

### Objetivos

1. Crear método template `_execute_operation()` para gestión automática de backup
2. Centralizar configuración de ThreadPool
3. Estandarizar progress reporting
4. Crear métodos de validación comunes
5. Documentar convenciones de logging

### Problemas a Resolver

**Problema 1**: Gestión de backup duplicada en 7 servicios (~120 líneas)
- Todos los `execute()` repiten mismo bloque try/except para BackupCreationError
- FileOrganizerService tiene su propio método `createbackup()` que duplica lógica
- Validaciones de backup_path repetidas

**Problema 2**: ThreadPool configurado manualmente en 3+ servicios
- Código idéntico para obtener max_workers de Config y settings_manager
- Context manager de ThreadPoolExecutor repetido
- Logging de workers duplicado

**Problema 3**: Progress callbacks con 3 patrones diferentes
- Algunos usan `_report_progress()` de BaseService
- Otros usan `safe_progress_callback` de utils
- Algunos llaman directamente sin protección

**Problema 4**: Validaciones básicas duplicadas
- Validación de directorio existente en todos los `analyze()`
- Recopilación de archivos soportados con variaciones del mismo bucle
- Chequeo de listas vacías repetido

### Tareas de Implementación

#### 2.1 - Crear método template `_execute_operation()`

**Propósito**: Encapsular toda la lógica común de ejecución con backup

**Firma del método**:
```

def _execute_operation(
self,
files: Iterable[Union[Path, dict, Any]],
operation_name: str,
execute_fn: Callable[[bool], OperationResult],
create_backup: bool,
dry_run: bool,
progress_callback: Optional[ProgressCallback] = None
) -> OperationResult:

```

**Debe manejar**:
- Decisión de crear backup: solo si `create_backup=True` AND `dry_run=False`
- Llamada a `self._create_backup_for_operation()` existente
- Captura de `BackupCreationError` con retorno anticipado de resultado de error
- Llamada a `execute_fn(dry_run)` con protección try/except general
- Población automática de `backup_path` en resultado retornado
- Logging apropiado de errores

**Parámetros explicados**:
- `files`: Archivos para incluir en backup (Path, dict con 'original_path', 'path', etc.)
- `operation_name`: String para logs y nombre de backup ('renaming', 'deletion', 'organization', etc.)
- `execute_fn`: Función que hace el trabajo real, recibe solo `dry_run: bool`, retorna OperationResult
- `create_backup`, `dry_run`, `progress_callback`: Flags estándar

**Retorno**: Resultado de `execute_fn` con campo `backup_path` poblado si corresponde

**Ejemplo de uso** (referencia para servicios):
```


# En FileRenamerService.execute()

def execute(self, renaming_plan, create_backup=True, dry_run=False, progress_callback=None):
return self._execute_operation(
files=[item['original_path'] for item in renaming_plan],
operation_name='renaming',
execute_fn=lambda dry: self._do_renaming(renaming_plan, dry, progress_callback),
create_backup=create_backup,
dry_run=dry_run,
progress_callback=progress_callback
)

```

#### 2.2 - Centralizar configuración de ThreadPool

**Crear método**: `_get_max_workers(io_bound: bool = True) -> int`

**Debe hacer**:
- Obtener override del usuario con `settings_manager.get_max_workers(0)`
- Llamar a `Config.get_actual_worker_threads(override=user_override, io_bound=io_bound)`
- Logging en DEBUG del número de workers seleccionados
- Documentar en docstring cuándo usar `io_bound=True` (lectura disco, cálculo hashes) vs `False` (CPU intensivo)

**Crear context manager**: `_parallel_processor(io_bound: bool = True)`

**Implementación**:
```

@contextmanager
def _parallel_processor(self, io_bound: bool = True):
"""
Context manager para procesamiento paralelo con ThreadPoolExecutor.

    Configura ThreadPoolExecutor con max_workers apropiado según tipo de operación.
    Compatible con cancelación cooperativa.
    
    Args:
        io_bound: Si True, operación es IO-bound (lectura disco, red).
                  Si False, operación es CPU-bound (cálculos intensivos).
    
    Yields:
        ThreadPoolExecutor configurado
        
    Example:
        with self._parallel_processor(io_bound=True) as executor:
            futures = {executor.submit(process_file, f): f for f in files}
            for future in as_completed(futures):
                result = future.result()
    """
    max_workers = self._get_max_workers(io_bound)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        yield executor
    ```

#### 2.3 - Estandarizar progress reporting

**Auditar método existente**: `_report_progress()` en BaseService

**Verificar que tiene**:
- Manejo de flag `self._cancelled`
- Protección contra excepciones en callback
- Logging de cancelaciones
- Retorna bool (True=continuar, False=cancelado)

**Acción**: Documentar como método estándar obligatorio

**Crear helper opcional**: `_should_report_progress(counter: int, interval: int = None) -> bool`
```

def _should_report_progress(self, counter: int, interval: int = None) -> bool:
"""
Determina si debe reportarse progreso según intervalo configurado.

    Args:
        counter: Número actual de elementos procesados
        interval: Intervalo de reporte (usa Config.UI_UPDATE_INTERVAL si es None)
    
    Returns:
        True si counter es múltiplo del intervalo
    """
    if interval is None:
        interval = Config.UI_UPDATE_INTERVAL
    return counter % interval == 0
    ```

#### 2.4 - Crear métodos de validación comunes

**Añadir a BaseService**:

**Método 1**: `_validate_directory(directory: Path, must_exist: bool = True) -> None`
```

def _validate_directory(self, directory: Path, must_exist: bool = True) -> None:
"""
Valida que un path sea un directorio válido.

    Args:
        directory: Path a validar
        must_exist: Si True, verifica que existe
        
    Raises:
        ValueError: Si validación falla con mensaje descriptivo
    """
    if must_exist and not directory.exists():
        raise ValueError(f"Directorio no existe: {directory}")
    if must_exist and not directory.is_dir():
        raise ValueError(f"No es un directorio: {directory}")
    ```

**Método 2**: `_get_supported_files(directory: Path, recursive: bool = True, progress_callback: Optional[ProgressCallback] = None) -> List[Path]`
```

def _get_supported_files(
self,
directory: Path,
recursive: bool = True,
progress_callback: Optional[ProgressCallback] = None
) -> List[Path]:
"""
Recopila archivos multimedia soportados en directorio.

    Usa Config.is_supported_file() para filtrar.
    Puede reportar progreso si callback es proporcionado.
    
    Args:
        directory: Directorio a escanear
        recursive: Si True, busca recursivamente con **/*
        progress_callback: Callback opcional para progreso
        
    Returns:
        Lista de Paths de archivos soportados
    """
    files = []
    pattern = "**/*" if recursive else "*"
    processed = 0
    
    for filepath in directory.glob(pattern):
        if filepath.is_file() and Config.is_supported_file(filepath.name):
            files.append(filepath)
        
        processed += 1
        if progress_callback and self._should_report_progress(processed):
            if not self._report_progress(
                progress_callback, 
                processed, 
                -1,  # Total desconocido en scan
                f"Escaneando: {filepath.name}"
            ):
                break  # Cancelado
    
    return files
    ```

#### 2.5 - Documentar convenciones de logging

**NO crear LoggerMixin nuevo**, el sistema `utils.logger` ya existe.

**Acción**: Escribir docstring extenso en clase `BaseService` documentando convenciones:

```

class BaseService(ABC):
"""
Clase base abstracta para todos los servicios de procesamiento multimedia.

    ... (docstring existente) ...
    
    CONVENCIONES DE LOGGING
    =======================
    
    Este proyecto usa sistema centralizado en utils.logger.
    Todos los servicios deben seguir estas convenciones:
    
    Headers de Sección
    ------------------
    - log_section_header_relevant(): Operaciones que MODIFICAN disco (execute)
    - log_section_header_discrete(): Operaciones de SOLO LECTURA (analyze)
    - Parámetro mode: Pasar mode="SIMULACIÓN" cuando dry_run=True
    
    Ejemplo:
        log_section_header_relevant(
            self.logger,
            "ELIMINACIÓN DE ARCHIVOS",
            mode="SIMULACIÓN" if dry_run else ""
        )
    
    Logs de Operaciones Sobre Archivos
    -----------------------------------
    Formato estándar: {TIPO}: {path} | Size: {size} | Date: {date} | Type: {filetype}
    
    Tipos válidos:
    - FILE_DELETED / FILE_DELETED_SIMULATION
    - FILE_MOVED / FILE_MOVED_SIMULATION
    - FILE_RENAMED / FILE_RENAMED_SIMULATION
    - FILE_CONVERTED / FILE_CONVERTED_SIMULATION
    
    Simulación: Añadir sufijo _SIMULATION al tipo de log
    
    Ejemplo:
        self.logger.info(
            f"FILE_DELETED: {filepath} | Size: {format_size(size)} | "
            f"Date: {date_str} | Type: {file_type}"
        )
        
    Footers de Sección
    ------------------
    - log_section_footer_relevant(): Con summary de operación
    - Usar self._format_operation_summary() para construir mensaje
    
    Ejemplo:
        summary = self._format_operation_summary(
            "Eliminación",
            files_deleted,
            space_freed,
            dry_run
        )
        log_section_footer_relevant(self.logger, summary)
    
    Niveles de Log
    --------------
    - INFO: Operaciones de modificación, resúmenes, inicio/fin de fases
    - DEBUG: Detalles internos, procesamiento archivo por archivo frecuente
    - WARNING: Archivos no encontrados (operación continúa), problemas no críticos
    - ERROR: Fallos en operaciones críticas, excepciones capturadas
    
    Intervalos de Reporte
    ----------------------
    - Operaciones individuales: Cada Config.LOG_PROGRESS_INTERVAL en INFO
    - Operaciones muy frecuentes: DEBUG o usar intervalos
    - Resúmenes periódicos: Cada N archivos según Config.UI_UPDATE_INTERVAL
    
    Formato Parseable
    -----------------
    Los logs deben ser parseables con regex para análisis posterior:
    
    FILE_DELETED: ^FILE_DELETED(?:_SIMULATION)?: (.+) \| Size: (.+) \| Date: (.+) \| Type: (.+)$
    FILE_MOVED: ^FILE_MOVED(?:_SIMULATION)?: (.+) \| From: (.+) \| To: (.+) \| Size: (.+)$
    FILE_RENAMED: ^FILE_RENAMED(?:_SIMULATION)?: (.+) -> (.+) \| Date: (.+)(?:\| Conflict: (\d+))?$
    """
    ```

#### 2.6 - Mejorar `_format_operation_summary()`

**Método existente** en BaseService ya funciona, pero verificar que cubre todos los casos.

**Firma actual**:
```

def _format_operation_summary(
self,
operation_name: str,
files_count: int,
space_amount: int = 0,
dry_run: bool = False
) -> str

```

**Verificar**:
- ✅ Maneja dry_run con verbos condicionales ("se procesarían" vs "procesados")
- ✅ Formatea espacio con `format_size()` si > 0
- ✅ Retorna mensaje consistente

**Acción**: Validar que todos los servicios lo usan, no reimplementan lógica similar.

### Validación de Fase 2

**Checklist de completitud**:
- [ ] `_execute_operation()` implementado con docstring completo
- [ ] `_execute_operation()` manejando todos los casos: con/sin backup, con/sin dry_run, con/sin errores
- [ ] `_get_max_workers()` implementado y documentado
- [ ] `_parallel_processor()` como context manager funcional
- [ ] `_validate_directory()` con tests para casos válidos/inválidos
- [ ] `_get_supported_files()` con soporte para progress y cancelación
- [ ] Docstring de convenciones de logging añadido a BaseService
- [ ] `_format_operation_summary()` validado que funciona para todos los casos

**Tests unitarios requeridos**:
```


# Crear/actualizar tests/test_base_service.py

# Test 1: _execute_operation con backup exitoso

# Test 2: _execute_operation sin backup (create_backup=False)

# Test 3: _execute_operation en dry_run (no crea backup)

# Test 4: _execute_operation maneja BackupCreationError

# Test 5: _execute_operation propaga excepciones de execute_fn

# Test 6: _parallel_processor yields executor con max_workers correcto

# Test 7: _validate_directory con directorio válido (no lanza excepción)

# Test 8: _validate_directory con path inexistente (lanza ValueError)

# Test 9: _get_supported_files filtra correctamente

# Test 10: _get_supported_files respeta recursive=False

pytest tests/test_base_service.py -v

```

**Validación manual**:
- Revisar que `_execute_operation()` puede reemplazar todos los bloques de backup existentes
- Verificar que docstring de logging es comprensible y completo

---

## ✅ FASE 3: MIGRAR SERVICIOS A NUEVA ARQUITECTURA

**Prioridad**: ALTA  
**Tiempo estimado**: 8-12 horas  
**Prerequisitos**: Fase 2 completada  
**Estado**: ✅ COMPLETADA (2024-12-11)

### Objetivos

1. Todos los servicios heredan correctamente de BaseService
2. Todos usan `_execute_operation()` template
3. Eliminar código duplicado de backup, validación, ThreadPool
4. Estandarizar uso de `_report_progress()`

### Estrategia de Migración

**Orden de ejecución**: De más simple a más complejo, uno por uno, con tests en cada paso.

**Después de cada servicio**:
1. Ejecutar tests unitarios del servicio
2. Ejecutar tests de integración si existen
3. Validar manualmente funcionalidad básica
4. Commit atómico con mensaje descriptivo

### Servicios a Migrar

#### 3.1 - ZeroByteService (COMENZAR AQUÍ - Más simple)

**Archivo**: `zero_byte_service.py`

**Problemas actuales**:
- No hereda de BaseService (crea logger manualmente)
- Implementa backup y error handling manualmente
- Llamadas directas a callback sin protección

**Tareas de migración**:

**Paso 1**: Cambiar herencia
```


# ANTES:

class ZeroByteService:
def __init__(self):
self.logger = get_logger('ZeroByteService')

# DESPUÉS:

class ZeroByteService(BaseService):
def __init__(self):
super().__init__('ZeroByteService')

```

**Paso 2**: Refactorizar `analyze()`
- Usar `self._validate_directory(directory)` en lugar de validación manual
- Si usa recopilación de archivos custom, considerar usar `_get_supported_files()`
- Mantener lógica específica de detección de archivos de 0 bytes

**Paso 3**: Refactorizar `execute()`
- Extraer lógica de eliminación a método privado: `_do_zero_byte_deletion(files, dry_run, progress_callback) -> ZeroByteDeletionResult`
- Reemplazar bloque de backup manual por llamada a `_execute_operation()`:

```

def execute(self, files_to_delete, create_backup=True, dry_run=False, progress_callback=None):
return self._execute_operation(
files=files_to_delete,
operation_name='zero_byte_deletion',
execute_fn=lambda dry: self._do_zero_byte_deletion(files_to_delete, dry, progress_callback),
create_backup=create_backup,
dry_run=dry_run,
progress_callback=progress_callback
)

```

**Paso 4**: Estandarizar progress reporting
- Reemplazar cualquier llamada directa a `callback()` por `self._report_progress(callback, ...)`
- Usar `_should_report_progress()` para intervalos

**Paso 5**: Estandarizar logging
- Verificar uso de `log_section_header_relevant` con `mode="SIMULACIÓN"` si `dry_run=True`
- Formato de logs: `FILE_DELETED` o `FILE_DELETED_SIMULATION`
- Usar `log_section_footer_relevant` con `_format_operation_summary()`

**Validación**:
```

pytest tests/test_zero_byte_service.py -v

# Validar casos: con backup, sin backup, dry_run, cancelación

```

---

#### 3.2 - FileRenamerService

**Archivo**: `file_renamer_service.py`

**Problemas actuales**:
- Manejo manual de backup con try/except
- ThreadPool configurado manualmente
- Mezcla de `_report_progress()` y llamadas directas

**Tareas de migración**:

**Paso 1**: Refactorizar `analyze()`
- Reemplazar configuración manual de ThreadPool:

```


# ANTES:

user_override = settings_manager.get_max_workers(0)
max_workers = Config.get_actual_worker_threads(override=user_override, io_bound=True)
self.logger.debug(f"Usando {max_workers} workers para análisis paralelo")

with ThreadPoolExecutor(max_workers=max_workers) as executor:
\# ...procesamiento...

# DESPUÉS:

with self._parallel_processor(io_bound=True) as executor:
\# ...procesamiento sin cambios...

```

- Mantener lógica de análisis de fechas y generación de plan

**Paso 2**: Refactorizar `execute()`
- Extraer lógica de renombrado: `_do_renaming(renaming_plan, dry_run, progress_callback) -> RenameDeletionResult`
- Usar `_execute_operation()`:

```

def execute(self, renaming_plan, create_backup=True, dry_run=False, progress_callback=None):
return self._execute_operation(
files=[item['original_path'] for item in renaming_plan],
operation_name='renaming',
execute_fn=lambda dry: self._do_renaming(renaming_plan, dry, progress_callback),
create_backup=create_backup,
dry_run=dry_run,
progress_callback=progress_callback
)

```

**Paso 3**: Estandarizar progress en `_do_renaming()`
- Todas las llamadas a progress usar `self._report_progress()`
- Verificar manejo de cancelación

**Paso 4**: Estandarizar logging
- Formato: `FILE_RENAMED` o `FILE_RENAMED_SIMULATION`
- Incluir información de conflictos si aplica
- Ejemplo: `FILE_RENAMED: old.jpg -> new_001.jpg | Date: 2024-01-01 | Conflict: 1`

**Validación**:
```

pytest tests/test_file_renamer_service.py -v

# Validar: renombrado simple, conflictos de nombres, cancelación

```

---

#### 3.3 - FileOrganizerService (Más complejo)

**Archivo**: `file_organizer_service.py`

**Problemas actuales**:
- Método `createbackup()` completamente custom que duplica lógica de BaseService
- ThreadPool configurado manualmente
- Lógica de `execute()` muy larga (~200 líneas)

**Tareas de migración**:

**Paso 1**: **ELIMINAR completamente método `createbackup()`**
- Borrar todo el método
- Verificar que nadie más lo llama (buscar referencias)

**Paso 2**: Refactorizar `analyze()`
- Reemplazar ThreadPool manual por `self._parallel_processor(io_bound=True)`
- Mantener toda la lógica de generación de plan de movimiento (es compleja y específica)

**Paso 3**: Refactorizar `execute()` (crítico)
- Es muy largo, dividir en métodos privados:
  - `_create_folders(folders_to_create, root_directory, dry_run)` → Crea carpetas necesarias
  - `_do_organization(move_plan, dry_run, progress_callback)` → Ejecuta movimientos
  - `_cleanup_empty_dirs(root_directory, dry_run)` → Limpia directorios vacíos

- Usar `_execute_operation()`:

```

def execute(self, move_plan, create_backup=True, cleanup_empty_dirs=True, dry_run=False, progress_callback=None):
if not move_plan:
return OrganizationDeletionResult(success=True, files_moved=0, message="No hay archivos para mover")

    # Determinar root_directory desde move_plan
    root_directory = self._get_root_from_plan(move_plan)
    
    # Crear carpetas necesarias (antes de backup)
    folders_to_create = set(move.target_folder for move in move_plan if move.target_folder)
    self._create_folders(folders_to_create, root_directory, dry_run)
    
    # Ejecutar movimientos con backup
    result = self._execute_operation(
        files=[move.source_path for move in move_plan],
        operation_name='organization',
        execute_fn=lambda dry: self._do_organization(move_plan, dry, progress_callback),
        create_backup=create_backup,
        dry_run=dry_run,
        progress_callback=progress_callback
    )
    
    # Limpiar directorios vacíos si se solicitó
    if cleanup_empty_dirs and result.success:
        removed = self._cleanup_empty_dirs(root_directory, dry_run)
        result.empty_directories_removed = removed
    
    return result
    ```

**Paso 4**: Implementar métodos privados extraídos
- `_create_folders()`: Lógica de creación de carpetas, respetar dry_run
- `_do_organization()`: Bucle de movimiento de archivos, logging, manejo de errores
- `_cleanup_empty_dirs()`: Llamada a utils.file_utils.cleanup_empty_directories

**Paso 5**: Estandarizar logging de movimientos
- Formato: `FILE_MOVED` o `FILE_MOVED_SIMULATION`
- Ejemplo: `FILE_MOVED: file.jpg | From: /old/path | To: /new/path | Size: 2.5 MB`

**Validación**:
```

pytest tests/test_file_organizer_service.py -v

# Validar: to_root, by_month, by_year, by_type, carpetas creadas, cleanup

```

---

#### 3.4 - DuplicatesBaseService

**Archivo**: `duplicates_base_service.py`

**Problemas actuales**:
- `execute()` recibe `groups: List[DuplicateGroup]` en lugar de `AnalysisResult`
- Usa `safe_progress_callback` de utils en lugar de `_report_progress()`

**Tareas de migración**:

**Decisión de diseño crítica**:

**Opción A (RECOMENDADA)**: Cambiar firma de `execute()` para recibir `DuplicateAnalysisResult`
```


# ANTES:

def execute(self, groups: List[DuplicateGroup], keep_strategy, create_backup, dry_run, progress_callback, metadata_cache):
\# ...

# DESPUÉS:

def execute(self, analysis_result: DuplicateAnalysisResult, keep_strategy, create_backup, dry_run, progress_callback, metadata_cache):
groups = analysis_result.groups
\# ...resto igual

```

**Ventajas**: Consistente con otros servicios, sigue patrón estándar
**Desventajas**: Requiere actualizar llamadas desde DuplicatesExactService y DuplicatesSimilarService

**Opción B**: Mantener firma actual por compatibilidad
**Ventajas**: Sin cambios en servicios hijo
**Desventajas**: Rompe convención, no mejora arquitectura

**Recomendación**: Implementar Opción A

**Paso 1**: Si se elige Opción A, cambiar firma
```

def execute(
self,
analysis_result: DuplicateAnalysisResult,
keep_strategy: str = 'oldest',
create_backup: bool = True,
dry_run: bool = False,
progress_callback: Optional[ProgressCallback] = None,
metadata_cache = None
) -> DuplicateDeletionResult:
groups = analysis_result.groups
\# ...resto del código sin cambios

```

**Paso 2**: Reemplazar `safe_progress_callback` por `self._report_progress()`
- Buscar todas las llamadas a `safe_progress_callback` en `_process_group_deletion()`
- Reemplazar por `self._report_progress()`

**Paso 3**: Ya usa `_create_backup_for_operation()` correctamente
- Verificar que sigue funcionando
- No hay cambios necesarios en la lógica de backup

**Paso 4**: Si se cambió firma, actualizar DuplicatesExactService y DuplicatesSimilarService
- Ambos llaman a `super().execute(groups, ...)` o `self.execute(groups, ...)`
- Cambiar a pasar `analysis_result` en lugar de solo `groups`

**Validación**:
```

pytest tests/test_duplicates_base_service.py -v
pytest tests/test_duplicates_exact_service.py -v
pytest tests/test_duplicates_similar_service.py -v

# Validar estrategias: oldest, newest, largest, smallest, manual

```

---

#### 3.5 - DuplicatesExactService y DuplicatesSimilarService

**Archivos**: `duplicates_exact_service.py`, `duplicates_similar_service.py`

**Problemas actuales**:
- ThreadPool configurado manualmente en `analyze()`
- Si se cambió DuplicatesBaseService, necesitan actualización

**Tareas de migración**:

**Paso 1**: Refactorizar `analyze()` en ambos
- Reemplazar configuración manual de ThreadPool por `self._parallel_processor(io_bound=True)`

```


# ANTES (en DuplicatesExactService):

from utils.settings_manager import settings_manager
user_override = settings_manager.get_max_workers(0)
max_workers = Config.get_actual_worker_threads(override=user_override, io_bound=True)

# ...

with ThreadPoolExecutor(max_workers=max_workers) as executor:
\# ...

# DESPUÉS:

with self._parallel_processor(io_bound=True) as executor:
\# ...procesamiento sin cambios

```

**Paso 2**: Si DuplicatesBaseService cambió firma, actualizar llamadas
- Buscar donde se llama a `execute()` o `super().execute()`
- Pasar `analysis_result` completo en lugar de `analysis_result.groups`

**Paso 3**: Validar que herencia sigue funcionando
- Ambos heredan de DuplicatesBaseService
- Cambios en clase base deben propagarse correctamente

**Validación**:
```

pytest tests/test_duplicates_exact_service.py -v
pytest tests/test_duplicates_similar_service.py -v

# Validar detección, eliminación, estrategias

```

---

#### 3.6 - LivePhotosService

**Archivo**: `live_photos_service.py`

**Problemas actuales**:
- Manejo manual de backup con try/except
- Lógica de `execute()` larga con código repetitivo

**Tareas de migración**:

**Paso 1**: Refactorizar `execute()`
- Extraer lógica: `_do_live_photo_cleanup(files_to_delete, dry_run, progress_callback) -> LivePhotoCleanupDeletionResult`
- Usar `_execute_operation()`:

```

def execute(self, analysis, create_backup=True, dry_run=False, progress_callback=None):
files_to_delete = analysis.files_to_delete

    if not files_to_delete:
        return LivePhotoCleanupDeletionResult(
            success=True,
            files_deleted=0,
            message="No hay archivos para eliminar"
        )
    
    return self._execute_operation(
        files=[item['path'] for item in files_to_delete],
        operation_name='live_photo_cleanup',
        execute_fn=lambda dry: self._do_live_photo_cleanup(files_to_delete, dry, progress_callback),
        create_backup=create_backup,
        dry_run=dry_run,
        progress_callback=progress_callback
    )
    ```

**Paso 2**: Implementar `_do_live_photo_cleanup()`
- Mover bucle de eliminación de archivos aquí
- Mantener logging detallado de archivos emparejados
- Usar `self._report_progress()` con intervalos

**Paso 3**: Estandarizar logging
- Formato: `FILE_DELETED` o `FILE_DELETED_SIMULATION`
- Incluir información de archivo emparejado si existe
- Ejemplo: `FILE_DELETED: IMG_001.MOV | Size: 15 MB | Paired: IMG_001.JPG (kept)`

**Validación**:
```

pytest tests/test_live_photos_service.py -v

# Validar: keep_image, keep_video, detección de pares

```

---

#### 3.7 - HeicService

**Archivo**: `heic_service.py`

**Problemas actuales**:
- Manejo manual de backup
- Estructura similar a LivePhotosService

**Tareas de migración**:

**Paso 1**: Refactorizar `execute()`
- Extraer: `_do_heic_cleanup(duplicate_pairs, format_to_keep, dry_run, progress_callback) -> HeicDeletionResult`
- Usar `_execute_operation()`:

```

def execute(self, analysis, format_to_keep='jpg', create_backup=True, dry_run=False, progress_callback=None):
duplicate_pairs = analysis.duplicate_pairs

    if not duplicate_pairs:
        return HeicDeletionResult(
            success=True,
            files_deleted=0,
            message="No hay duplicados HEIC para eliminar"
        )
    
    # Determinar archivos a eliminar según formato
    files_to_delete = []
    for pair in duplicate_pairs:
        if format_to_keep == 'jpg':
            files_to_delete.append(pair.heic_path)
        else:
            files_to_delete.append(pair.jpg_path)
    
    return self._execute_operation(
        files=files_to_delete,
        operation_name='heic_cleanup',
        execute_fn=lambda dry: self._do_heic_cleanup(duplicate_pairs, format_to_keep, dry, progress_callback),
        create_backup=create_backup,
        dry_run=dry_run,
        progress_callback=progress_callback
    )
    ```

**Paso 2**: Implementar `_do_heic_cleanup()`
- Bucle de eliminación según formato a mantener
- Logging de pares HEIC/JPG
- Progress reporting con intervalos

**Paso 3**: Estandarizar logging
- Formato: `FILE_DELETED` o `FILE_DELETED_SIMULATION`
- Ejemplo: `FILE_DELETED: IMG_001.HEIC | Size: 3.2 MB | Paired: IMG_001.JPG (kept) | Format: keep_jpg`

**Validación**:
```

pytest tests/test_heic_service.py -v

# Validar: keep_heic, keep_jpg, detección de pares

```

---

### Validación Global de Fase 3

**Checklist de completitud**:
- [ ] Todos los servicios heredan de BaseService (verificar con `issubclass()`)
- [ ] Ningún servicio tiene método custom de backup
- [ ] Ningún servicio configura ThreadPoolExecutor manualmente
- [ ] Todos usan `self._report_progress()` exclusivamente
- [ ] Todos los `execute()` usan `_execute_operation()` o ya usan `_create_backup_for_operation()` correctamente

**Tests de integración**:
```


# Ejecutar suite completa

pytest tests/ -v

# Por servicio individual

pytest tests/test_zero_byte_service.py -v
pytest tests/test_file_renamer_service.py -v
pytest tests/test_file_organizer_service.py -v
pytest tests/test_duplicates_*.py -v
pytest tests/test_live_photos_service.py -v
pytest tests/test_heic_service.py -v

```

**Validación manual en UI**:
- Ejecutar cada servicio con: backup ON, backup OFF, dry_run ON, dry_run OFF
- Verificar progress bars se actualizan
- Probar cancelación desde UI
- Validar que resultados se muestran igual que antes

**Commits por servicio**:
```

git commit -m "Fase 3.1: Migrar ZeroByteService a nueva arquitectura"
git commit -m "Fase 3.2: Migrar FileRenamerService a nueva arquitectura"
git commit -m "Fase 3.3: Migrar FileOrganizerService a nueva arquitectura"

# ...etc

```

---

## 🟡 FASE 4: ESTANDARIZAR APLICACIÓN DE LOGGING

**Prioridad**: MEDIA  
**Tiempo estimado**: 3-4 horas  
**Prerequisitos**: Fase 3 completada  
**Estado**: PENDIENTE

### Objetivos

1. Aplicar uniformemente convenciones documentadas en Fase 2
2. Logs parseables con regex para análisis posterior
3. Niveles apropiados según tipo de operación

### Tareas de Implementación

#### 4.1 - Auditar uso de funciones de logging

**Crear checklist por servicio** (validar cada uno):

**Por cada servicio verificar**:
- [ ] `analyze()` usa `log_section_header_discrete()` (es solo lectura)
- [ ] `execute()` usa `log_section_header_relevant()` (modifica disco)
- [ ] Parámetro `mode="SIMULACIÓN"` se pasa cuando `dry_run=True`
- [ ] Logs de operaciones individuales usan formato estándar
- [ ] Simulaciones usan sufijo `_SIMULATION` en tipo de log
- [ ] Footer usa `log_section_footer_relevant()` con `_format_operation_summary()`

**Archivo de auditoría**: Crear `LOGGING_AUDIT.md` con tabla:

```

| Servicio | Header Analyze | Header Execute | Mode Param | Log Format | Simulation | Footer |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| ZeroByteService | ✅ discrete | ✅ relevant | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| FileRenamerService | ? | ? | ? | ? | ? | ? |
| ... | ... | ... | ... | ... | ... | ... |

```

#### 4.2 - Estandarizar logs de operaciones por tipo

**Operaciones de ELIMINACIÓN** (ZeroByteService, DuplicatesService, LivePhotosService, HeicService):

**Formato estándar**:
```

FILE_DELETED: {path} | Size: {size} | Date: {date} | Type: {filetype}
FILE_DELETED_SIMULATION: {path} | Size: {size} | Date: {date} | Type: {filetype}

```

**Ejemplo real**:
```

log_type = "FILE_DELETED_SIMULATION" if dry_run else "FILE_DELETED"
self.logger.info(
f"{log_type}: {filepath} | Size: {format_size(file_size)} | "
f"Date: {date_str} | Type: {file_type}"
)

```

**Operaciones de MOVIMIENTO** (FileOrganizerService):

**Formato estándar**:
```

FILE_MOVED: {filename} | From: {source_dir} | To: {target_dir} | Size: {size}
FILE_MOVED_SIMULATION: {filename} | From: {source_dir} | To: {target_dir} | Size: {size}

```

**Ejemplo real**:
```

log_type = "FILE_MOVED_SIMULATION" if dry_run else "FILE_MOVED"
self.logger.info(
f"{log_type}: {filename} | From: {source_folder} | "
f"To: {target_folder} | Size: {format_size(file_size)}"
)

```

**Operaciones de RENOMBRADO** (FileRenamerService):

**Formato estándar**:
```

FILE_RENAMED: {old_name} -> {new_name} | Date: {date} | Conflict: {sequence}
FILE_RENAMED_SIMULATION: {old_name} -> {new_name} | Date: {date} | Conflict: {sequence}

```

**Conflicto es opcional** (solo si hay secuencia de conflicto):
```

log_type = "FILE_RENAMED_SIMULATION" if dry_run else "FILE_RENAMED"
conflict_info = f" | Conflict: {sequence}" if sequence else ""
self.logger.info(
f"{log_type}: {old_name} -> {new_name} | Date: {date_str}{conflict_info}"
)

```

#### 4.3 - Normalizar niveles de log

**Reglas a aplicar**:

**INFO**:
- Headers y footers de sección
- Resúmenes de operación
- Operaciones de modificación cada N archivos (según `Config.LOG_PROGRESS_INTERVAL`)
- Inicio/fin de fases importantes

**DEBUG**:
- Operaciones individuales muy frecuentes (si se loguean todas)
- Detalles internos de algoritmos
- Decisiones de lógica interna
- Información de caché hits/misses

**WARNING**:
- Archivos no encontrados pero operación continúa
- Problemas no críticos (permisos de lectura en archivos no procesables)
- Validaciones que fallan pero no detienen flujo

**ERROR**:
- Fallos en operaciones críticas
- Excepciones capturadas en operaciones de modificación
- Errores que afectan resultado final

**Migración**:
```


# ANTES: Log de cada archivo en INFO (spam si son 10,000 archivos)

for file in files:
self.logger.info(f"Procesando {file}")

# DESPUÉS: Solo cada N archivos en INFO, resto en DEBUG

for i, file in enumerate(files):
if i % Config.LOG_PROGRESS_INTERVAL == 0:
self.logger.info(f"Procesado {i}/{len(files)} archivos")
self.logger.debug(f"Procesando {file}")

```

#### 4.4 - Documentar regex patterns para parsing

**Añadir a docstring de BaseService** (en sección de convenciones):

```

"""
... (docstring existente) ...

PATRONES REGEX PARA PARSING DE LOGS
====================================

Los logs de operaciones pueden parsearse con estas expresiones regulares:

FILE_DELETED:
Pattern: ^FILE_DELETED(?:_SIMULATION)?: (.+) \| Size: (.+) \| Date: (.+) \| Type: (.+)\$
Grupos: 1=path, 2=size, 3=date, 4=type

FILE_MOVED:
Pattern: ^FILE_MOVED(?:_SIMULATION)?: (.+) \| From: (.+) \| To: (.+) \| Size: (.+)\$
Grupos: 1=filename, 2=source_dir, 3=target_dir, 4=size

FILE_RENAMED:
Pattern: ^FILE_RENAMED(?:_SIMULATION)?: (.+) -> (.+) \| Date: (.+)(?:\| Conflict: (\d+))?\$
Grupos: 1=old_name, 2=new_name, 3=date, 4=conflict_sequence (opcional)

Ejemplo de uso:
import re
pattern = r'^FILE_DELETED(?:_SIMULATION)?: (.+) \| Size: (.+) \| Date: (.+) \| Type: (.+)\$'
match = re.match(pattern, log_line)
if match:
path, size, date, filetype = match.groups()
"""

```

### Validación de Fase 4

**Checklist**:
- [ ] Todos los servicios auditados y checklist completo
- [ ] Logs de eliminación usan formato estándar
- [ ] Logs de movimiento usan formato estándar
- [ ] Logs de renombrado usan formato estándar
- [ ] Sufijo `_SIMULATION` consistente en todos los servicios
- [ ] Niveles de log apropiados (no spam en INFO)
- [ ] Regex patterns documentados y verificados

**Validación práctica**:
```


# Ejecutar cada servicio y capturar logs

python -m services.zero_byte_service > logs/zero_byte.log 2>\&1

# Validar con regex

grep -E '^FILE_DELETED(_SIMULATION)?: .+ \| Size: .+ \| Date: .+ \| Type: .+\$' logs/zero_byte.log

# Si todos los logs matchean, formato es correcto

```

**Tests de parsing**:
```


# tests/test_log_parsing.py

import re

def test_delete_log_parsing():
log_line = "FILE_DELETED: /path/to/file.jpg | Size: 2.5 MB | Date: 2024-01-01 12:00:00 | Type: PHOTO"
pattern = r'^FILE_DELETED(?:_SIMULATION)?: (.+) \| Size: (.+) \| Date: (.+) \| Type: (.+)\$'
match = re.match(pattern, log_line)
assert match is not None
path, size, date, filetype = match.groups()
assert path == "/path/to/file.jpg"
assert size == "2.5 MB"

```

---

## 🟢 FASE 5: OPTIMIZAR USO DE THREADPOOL (OPCIONAL)

**Prioridad**: BAJA  
**Tiempo estimado**: 2-3 horas  
**Prerequisitos**: Fase 3 completada  
**Estado**: OPCIONAL

### Objetivos

1. Código de ThreadPool ya centralizado en Fase 2/3 ✅
2. Identificar servicios que podrían beneficiarse de paralelización
3. Medir mejoras de rendimiento antes de implementar

### Análisis de Candidatos

**Servicios que YA usan ThreadPool** (migrados en Fase 3):
- ✅ FileRenamerService.analyze()
- ✅ FileOrganizerService.analyze()
- ✅ DuplicatesExactService.analyze()

**Candidatos POTENCIALES** (evaluar beneficio):
- LivePhotosService.analyze(): Lectura de metadatos de fotos/videos (IO-bound)
- HeicService.analyze(): Lectura de metadatos de pares HEIC/JPG (IO-bound)
- DuplicatesSimilarService.analyze(): Cálculo de hashes perceptuales (¿CPU-bound o IO-bound?)

### Metodología de Evaluación

**Para cada candidato**:

1. **Medir baseline actual**:
```


# Crear dataset de prueba grande

mkdir test_dataset

# Poblar con 1000+ archivos

# Medir tiempo actual

time python -c "
from services.live_photos_service import LivePhotosService
service = LivePhotosService()
result = service.analyze(Path('test_dataset'))
"

```

2. **Implementar versión paralela**:
- Usar `self._parallel_processor(io_bound=True)` o `False` según tipo
- Asegurar thread-safety de estructuras compartidas (usar locks si necesario)

3. **Medir tiempo con paralelización**:
```

time python -c "

# Mismo código con versión paralela

"

```

4. **Calcular mejora**:
```

Mejora = (Tiempo_Antes - Tiempo_Después) / Tiempo_Antes * 100

```

5. **Decisión**:
- Si mejora > 20%: **Implementar** paralelización
- Si mejora 10-20%: **Evaluar** complejidad vs beneficio
- Si mejora < 10%: **No implementar**, overhead no justifica cambio

### Implementación (Solo si Beneficio > 20%)

**Ejemplo para LivePhotosService.analyze()**:

```


# ANTES: Procesamiento secuencial

for filepath in image_files:
metadata = get_metadata(filepath)
\# ...procesar

# DESPUÉS: Procesamiento paralelo

def process_file(filepath):
return get_metadata(filepath)

with self._parallel_processor(io_bound=True) as executor:
futures = {executor.submit(process_file, f): f for f in image_files}
for future in as_completed(futures):
filepath = futures[future]
try:
metadata = future.result()
\# ...procesar
except Exception as e:
self.logger.error(f"Error procesando {filepath}: {e}")

```

**Consideraciones**:
- Mantener cancelación cooperativa funcionando
- Locks para estructuras compartidas si necesario
- Tests de concurrencia para evitar race conditions

### Documentación de Decisiones

**Para servicios NO paralelizados**:
```

def analyze(self, directory, ...):
"""
Analiza directorio buscando Live Photos.

    Nota: Paralelización evaluada pero overhead supera beneficio para
    datasets típicos (<500 archivos). Procesamiento secuencial es suficiente.
    """
    ```

### Validación de Fase 5

**Checklist**:
- [ ] Benchmarks ejecutados para cada candidato
- [ ] Decisiones documentadas (implementar o no, con justificación)
- [ ] Si se implementó: mejora de rendimiento ≥20% demostrada
- [ ] Tests de concurrencia pasan sin race conditions
- [ ] Cancelación sigue funcionando

**Nota**: Esta fase es completamente OPCIONAL. Si no hay tiempo, saltar a Fase 6.

---

## 🔴 FASE 6: TESTING EXHAUSTIVO Y DOCUMENTACIÓN

**Prioridad**: CRÍTICA  
**Tiempo estimado**: 4-6 horas  
**Prerequisitos**: Fases 2-4 completadas (Fase 5 opcional)  
**Estado**: PENDIENTE

### Objetivos

1. Cobertura de tests ≥80%
2. Documentación completa y actualizada
3. Validación exhaustiva de compatibilidad con UI
4. Guía para futuros desarrolladores

### Tareas de Implementación

#### 6.1 - Tests Unitarios de Nueva Infraestructura

**Archivo**: `tests/test_base_service.py`

**Tests requeridos**:

```


# Test Suite para _execute_operation()

def test_execute_operation_with_backup_success():
"""Backup se crea y backup_path se popula en resultado"""
pass

def test_execute_operation_without_backup():
"""create_backup=False, no crea backup, backup_path es None"""
pass

def test_execute_operation_dry_run_no_backup():
"""dry_run=True, no crea backup incluso si create_backup=True"""
pass

def test_execute_operation_handles_backup_error():
"""BackupCreationError capturada, retorna resultado con error"""
pass

def test_execute_operation_propagates_execute_fn_exception():
"""Excepciones de execute_fn se propagan correctamente"""
pass

# Test Suite para _parallel_processor()

def test_parallel_processor_yields_executor():
"""Context manager yields ThreadPoolExecutor configurado"""
pass

def test_parallel_processor_uses_correct_max_workers():
"""max_workers se obtiene correctamente según io_bound"""
pass

# Test Suite para validaciones

def test_validate_directory_valid():
"""Directorio válido no lanza excepción"""
pass

def test_validate_directory_not_exists():
"""Directorio inexistente lanza ValueError"""
pass

def test_validate_directory_not_dir():
"""Path que no es directorio lanza ValueError"""
pass

def test_get_supported_files_filters_correctly():
"""Solo retorna archivos multimedia soportados"""
pass

def test_get_supported_files_respects_recursive():
"""recursive=False no busca en subdirectorios"""
pass

def test_get_supported_files_supports_cancellation():
"""Callback puede cancelar scan de archivos"""
pass

```

**Ejecutar**:
```

pytest tests/test_base_service.py -v --cov=services.base_service

```

---

#### 6.2 - Tests de Integración por Servicio

**Por cada servicio**, validar matriz de casos:

**Matriz de pruebas estándar**:
```

| Caso | create_backup | dry_run | Validación |
| :-- | :-- | :-- | :-- |
| Normal con backup | True | False | Archivos modificados, backup creado |
| Normal sin backup | False | False | Archivos modificados, sin backup |
| Simulación con backup | True | True | Sin modificar, campos simulated_* |
| Simulación sin backup | False | True | Sin modificar, sin backup |
| Cancelación | True/False | - | Operación se detiene limpiamente |
| Error de backup | True | False | Mock BackupCreationError |
| Directorio vacío | - | - | Retorna resultado con 0 archivos |
| Archivos no soportados | - | - | Ignora archivos no multimedia |

```

**Ejemplo de test**:
```


# tests/test_zero_byte_service.py

def test_zero_byte_service_normal_with_backup(tmp_path):
\# Setup
service = ZeroByteService()
zero_file = tmp_path / "empty.txt"
zero_file.touch()

    # Execute
    analysis = service.analyze(tmp_path)
    result = service.execute(analysis.files, create_backup=True, dry_run=False)
    
    # Validate
    assert result.success is True
    assert result.files_deleted == 1
    assert result.backup_path is not None
    assert not zero_file.exists()  # Archivo eliminado
    def test_zero_byte_service_dry_run(tmp_path):
\# Setup
service = ZeroByteService()
zero_file = tmp_path / "empty.txt"
zero_file.touch()

    # Execute
    analysis = service.analyze(tmp_path)
    result = service.execute(analysis.files, create_backup=True, dry_run=True)
    
    # Validate
    assert result.success is True
    assert result.simulated_files_deleted == 1
    assert result.backup_path is None  # No backup en simulación
    assert zero_file.exists()  # Archivo NO eliminado
    ```

**Ejecutar por servicio**:
```

pytest tests/test_zero_byte_service.py -v
pytest tests/test_file_renamer_service.py -v
pytest tests/test_file_organizer_service.py -v

# ...etc

```

---

#### 6.3 - Tests de Compatibilidad con UI

**Validación manual** (crear checklist):

**ZeroByteService**:
- [ ] Analizar directorio desde UI
- [ ] Ver resultados de análisis (cantidad de archivos de 0 bytes)
- [ ] Ejecutar eliminación con backup ON
- [ ] Progress bar se actualiza correctamente
- [ ] Cancelar operación a mitad (verificar que se detiene)
- [ ] Ejecutar en modo simulación
- [ ] Verificar que resultados se muestran igual que antes

**FileRenamerService**:
- [ ] Analizar directorio con archivos sin renombrar
- [ ] Ver plan de renombrado generado
- [ ] Ejecutar renombrado con backup ON
- [ ] Verificar conflictos de nombres se resuelven
- [ ] Modo simulación muestra archivos que se renombrarían
- [ ] Cancelación funciona

**FileOrganizerService**:
- [ ] Analizar con diferentes modos (to_root, by_month, by_year, etc.)
- [ ] Ver plan de movimiento
- [ ] Ejecutar organización
- [ ] Verificar carpetas creadas correctamente
- [ ] Cleanup de directorios vacíos funciona
- [ ] Backup y simulación funcionan

**Servicios de duplicados**:
- [ ] Detectar duplicados exactos
- [ ] Detectar duplicados similares con diferentes niveles de sensibilidad
- [ ] Ver grupos de duplicados
- [ ] Eliminar con diferentes estrategias (oldest, newest, etc.)
- [ ] Progress reporting correcto (puede tardar con muchos archivos)

**LivePhotosService y HeicService**:
- [ ] Detectar pares Live Photo / HEIC+JPG
- [ ] Eliminar componente correcto según configuración
- [ ] Backup y simulación

---

#### 6.4 - Tests de Regresión

**Objetivo**: Validar que comportamiento es idéntico o mejor que antes de refactorización

**Metodología**:

1. **Crear dataset de referencia**:
```

mkdir regression_dataset

# Poblar con casos conocidos: archivos duplicados, Live Photos, archivos para renombrar, etc.

```

2. **Ejecutar servicios y capturar resultados**:
```


# tests/test_regression.py

def test_file_renamer_regression(regression_dataset):
"""Valida que renombrado produce mismo resultado que versión anterior"""
service = FileRenamerService()
analysis = service.analyze(regression_dataset)

    # Comparar con resultados esperados guardados
    expected_plan = load_expected_renaming_plan()
    assert len(analysis.renaming_plan) == len(expected_plan)
    # Validar cada elemento del plan...
    def test_duplicates_exact_regression(regression_dataset):
"""Valida que detección de duplicados encuentra mismos archivos"""
service = DuplicatesExactService()
analysis = service.analyze(regression_dataset)

    expected_groups = load_expected_duplicate_groups()
    assert analysis.total_groups == len(expected_groups)
    # Validar hashes y archivos en cada grupo...
    ```

3. **Comparar logs**:
```


# Ejecutar versión antigua (si está disponible) y nueva

# Comparar número de archivos procesados, espacio liberado, etc.

```

---

#### 6.5 - Documentación Técnica

**Actualizar docstrings**:

**BaseService**:
- [ ] Documentar `_execute_operation()` con ejemplos de uso
- [ ] Documentar `_parallel_processor()` con ejemplos
- [ ] Documentar métodos de validación
- [ ] Convenciones de logging ya documentadas en Fase 2

**Cada servicio**:
- [ ] Actualizar ejemplos en docstring si firmas cambiaron
- [ ] Documentar decisiones de paralelización (si aplica Fase 5)
- [ ] Añadir ejemplos de uso completo (analyze + execute)

**result_types.py**:
- [ ] Documentar jerarquía de clases (BaseResult, mixins)
- [ ] Explicar propósito de cada mixin
- [ ] Ejemplos de herencia múltiple

---

#### 6.6 - Guías para Desarrolladores

**Crear**: `docs/ADDING_NEW_SERVICE.md`

```


# Guía: Cómo Añadir un Nuevo Servicio

## Template Mínimo

Todo servicio debe heredar de `BaseService` e implementar dos métodos:

```python
from services.base_service import BaseService
from services.result_types import AnalysisResult, OperationResult

class MyNewService(BaseService):
    def __init__(self):
        super().__init__('MyNewService')  # Logger automático
    
    def analyze(
        self,
        directory: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> MyAnalysisResult:
        """
        Analiza directorio y genera plan de operación.
        NO debe modificar disco.
        """
        # 1. Validar directorio
        self._validate_directory(directory)
        
        # 2. Recopilar archivos
        files = self._get_supported_files(directory, recursive=True, progress_callback)
        
        # 3. Analizar y generar plan
        # ...tu lógica aquí...
        
        # 4. Retornar resultado con estadísticas
        return MyAnalysisResult(...)
    
    def execute(
        self,
        analysis_result: MyAnalysisResult,
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[ProgressCallback] = None
    ) -> MyExecutionResult:
        """
        Ejecuta plan generado por analyze().
        Modifica/elimina archivos (excepto en dry_run).
        """
        # 1. Validar que hay trabajo
        if not analysis_result.plan:
            return MyExecutionResult(success=True, message="Nada que hacer")
        
        # 2. Usar template para backup automático
        return self._execute_operation(
            files=analysis_result.files_to_process,
            operation_name='my_operation',
            execute_fn=lambda dry: self._do_my_operation(analysis_result.plan, dry, progress_callback),
            create_backup=create_backup,
            dry_run=dry_run,
            progress_callback=progress_callback
        )
    
    def _do_my_operation(
        self,
        plan,
        dry_run: bool,
        progress_callback: Optional[ProgressCallback]
    ) -> MyExecutionResult:
        """Lógica real de modificación de archivos"""
        # ...implementación...
```


## Convenciones Obligatorias

1. **Logging**: Seguir convenciones en docstring de BaseService
2. **Progress**: Usar `self._report_progress()` exclusivamente
3. **Backup**: Usar `self._execute_operation()` template
4. **ThreadPool**: Usar `self._parallel_processor()` si necesitas paralelización
5. **Validaciones**: Usar `self._validate_directory()` y `self._get_supported_files()`

## Tests Requeridos

- Tests unitarios para lógica específica del servicio
- Tests de integración con matriz estándar (ver Fase 6.2)
- Validación manual en UI


## Checklist de Revisión

- [ ] Hereda de BaseService
- [ ] Implementa analyze() y execute()
- [ ] Usa _execute_operation() para backup
- [ ] Logging sigue convenciones
- [ ] Tests con cobertura ≥80%
- [ ] Documentado con docstrings completos

```

---

**Crear**: `docs/CODING_CONVENTIONS.md`

```


# Convenciones de Código

## Nomenclatura

### Clases de Resultados

- Análisis: `*AnalysisResult` (ej: RenameAnalysisResult)
- Ejecución: `*ExecutionResult` o `*DeletionResult` según contexto


### Métodos

- Análisis: Siempre `analyze(directory, **kwargs)`
- Ejecución: Siempre `execute(analysis_result, **kwargs)`
- Métodos privados: Prefijo `_` (ej: `_do_operation()`)


## Logging

Ver docstring completo en `BaseService`.

Resumen:

- Headers: `log_section_header_relevant` para execute, `discrete` para analyze
- Operaciones: Formato `{TYPE}: {details} | Field: {value}`
- Simulación: Sufijo `_SIMULATION` en tipo
- Footers: `log_section_footer_relevant` con `_format_operation_summary()`


## Progress Reporting

- Usar `self._report_progress(callback, current, total, message)` SIEMPRE
- Verificar retorno para cancelación: `if not self._report_progress(...): break`
- Intervalos: `Config.UI_UPDATE_INTERVAL` para UI, `Config.LOG_PROGRESS_INTERVAL` para logs


## ThreadPool

- Usar `with self._parallel_processor(io_bound=True) as executor:`
- Parámetro `io_bound`: True para lectura disco/red, False para CPU intensivo
- Cancelación: Verificar `self._cancelled` periódicamente


## Error Handling

- Validaciones: Lanzar `ValueError` con mensaje descriptivo
- Operaciones: Capturar excepciones, añadir a `result.add_error()`
- FileNotFoundError: Log warning, continuar (no es crítico si archivo desapareció)

```

---

**Crear**: `CHANGELOG.md`

```


# Changelog - Refactorización Fases 2-6

## Fase 2: Infraestructura BaseService

### Añadido

- `_execute_operation()`: Template method para ejecución con backup automático
- `_parallel_processor()`: Context manager para ThreadPool centralizado
- `_get_max_workers()`: Configuración centralizada de workers
- `_validate_directory()`: Validación común de directorios
- `_get_supported_files()`: Recopilación común de archivos multimedia
- Convenciones de logging documentadas en docstring de BaseService


### Beneficios

- ~120 líneas de código duplicado eliminadas (backup)
- ~50 líneas eliminadas (ThreadPool)
- ~60 líneas eliminadas (validaciones)


## Fase 3: Migración de Servicios

### Modificado

- **ZeroByteService**: Ahora hereda de BaseService
- **FileRenamerService**: Usa `_execute_operation()` y `_parallel_processor()`
- **FileOrganizerService**: Eliminado método `createbackup()`, usa infrastructure de BaseService
- **DuplicatesBaseService**: Usa `_report_progress()` uniformemente
- **Todos los servicios**: ThreadPool centralizado, backup unificado


### Beneficios

- Interfaz consistente en todos los servicios
- ~400 líneas totales eliminadas
- Mantenibilidad significativamente mejorada


## Fase 4: Estandarización de Logging

### Modificado

- Formato unificado de logs de operaciones
- Niveles de log apropiados (reducción de spam en INFO)
- Sufijos `_SIMULATION` consistentes


### Beneficios

- Logs parseables con regex
- Análisis automatizado posible
- Debugging más eficiente


## Fase 5: Optimización ThreadPool (Opcional)

[Documentar si se implementó]

## Fase 6: Testing y Documentación

### Añadido

- Tests unitarios para BaseService
- Tests de integración exhaustivos por servicio
- Guía `ADDING_NEW_SERVICE.md`
- Guía `CODING_CONVENTIONS.md`
- Este CHANGELOG


### Métricas Finales

- Líneas eliminadas: ~700
- Cobertura de tests: XX% (objetivo ≥80%)
- Regresiones: 0
- UI: 100% compatible sin cambios


## Breaking Changes

**Ninguno** para usuarios finales de la UI.

Para desarrolladores que extiendan servicios:

- DuplicatesBaseService.execute() cambió firma (recibe AnalysisResult en lugar de groups)
    - Actualizar llamadas en clases hijas

```

---

### Validación Final de Fase 6

**Checklist de completitud**:
- [ ] Tests unitarios BaseService con ≥90% cobertura
- [ ] Tests integración por servicio con matriz completa
- [ ] Validación manual UI completada (checklist lleno)
- [ ] Tests de regresión pasan (resultados iguales o mejores)
- [ ] Docstrings actualizados en BaseService y servicios
- [ ] Guía `ADDING_NEW_SERVICE.md` creada y revisada
- [ ] Guía `CODING_CONVENTIONS.md` creada
- [ ] CHANGELOG.md actualizado con métricas finales

**Ejecutar suite```

