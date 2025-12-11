# **PROMPT PARA REFACTORIZACIÓN PROFESIONAL DE SISTEMA DE GESTIÓN MULTIMEDIA**

## **CONTEXTO DEL PROYECTO**

### **Arquitectura Actual**

Sistema Python de gestión de archivos multimedia con **separación estricta lógica/vista**:

**Componentes principales**:

- **9 servicios de procesamiento**: `FileRenamerService`, `FileOrganizerService`, `DuplicatesExactService`, `DuplicatesSimilarService`, `LivePhotosService`, `HeicService`, `ZeroByteService` + clases base `BaseService` y `DuplicatesBaseService`
- **Sistema de resultados**: `result_types.py` con 14 dataclasses para intercambio de datos
- **Sistema de logging centralizado**: `logger.py` con funciones helper para formato estandarizado (`log_section_header_relevant`, `log_section_header_discrete`, `log_section_footer_relevant`, etc.)
- **Vista/UI**: Consume resultados de servicios sin conocer implementación interna

**Restricciones técnicas**:

- ✅ **Solo dataclasses**: No usar Pydantic, attrs u otras librerías para resultados
- ✅ **Logger centralizado**: Ya existe en `utils.logger`, usar sus funciones helper
- ✅ **UI intocable**: No modificar interfaz pública de servicios
- ✅ **Config global**: No modificar sistema de configuración


### **Patrón de Diseño Estándar**

Todos los servicios siguen arquitectura de **dos fases**:

**Fase 1 - Análisis**:

- Método: `analyze(directory: Path, **kwargs) -> *AnalysisResult`
- Propósito: Escanear, analizar, generar plan de operación
- No modifica disco
- Retorna dataclass con estadísticas y plan detallado

**Fase 2 - Ejecución**:

- Método: `execute(analysis_or_plan, **kwargs) -> *ExecutionResult`
- Propósito: Ejecutar plan generado en fase 1
- Modifica/elimina archivos (excepto en modo simulación)
- Retorna dataclass con resultados de operación

**Características transversales** (todas las operaciones soportan):

1. **Backup opcional** (`create_backup: bool`):
    - Si `True` y `dry_run=False`: Crea backup antes de modificar/eliminar
    - Usa `BaseService._create_backup_for_operation()`
    - Retorna `backup_path` en resultado
2. **Modo simulación** (`dry_run: bool`):
    - Si `True`: Simula sin modificar disco
    - Resultados usan campos `simulated_files_deleted`, `simulated_space_freed`
    - Logging con prefijos especiales (`_SIMULATION` o `[SIMULACIÓN]`)
3. **Progress reporting** (`progress_callback: Optional[Callable]`):
    - Todas las operaciones largas reportan progreso
    - Callback firma: `(current: int, total: int, message: str) -> Optional[bool]`
    - Retorno `False` = cancelar operación
4. **Cancelación cooperativa**:
    - Usuario puede cancelar desde UI
    - Servicios verifican periódicamente con `_report_progress()`

**NOTA CRÍTICA**: Todo lo relacionado con `metadata_cache` será **rehecho desde cero en el futuro**. No tocar, ignorar, no optimizar en esta refactorización.

***

## **PROBLEMAS DETECTADOS (12 Categorías)**

### **🔴 CRÍTICO 1: Result Types Fragmentados**

**Impacto**: ~200 líneas duplicadas, 14 clases con campos repetidos

**Síntomas**:

- Campos `success`, `errors`, `message` duplicados en TODAS las clases
- Campos `dry_run`, `simulated_files_deleted`, `simulated_space_freed` repetidos en 6 clases
- Campos `backup_path` repetidos en 5 clases
- Métodos `has_errors()`, `add_error()`, `error` (property) idénticos copiados
- Aliases innecesarios: `HeicDeletionResult` tiene `format_kept` Y `kept_format`
- Sincronización manual de contadores: `need_renaming = len(renaming_plan)` en `__post_init__`

**Causa raíz**: Desarrollo iterativo sin diseño inicial de jerarquía

***

### **🔴 CRÍTICO 2: Jerarquía de Servicios Inconsistente**

**Impacto**: ~150 líneas duplicadas, interfaz no uniforme

**Síntomas**:

- `ZeroByteService` NO hereda de `BaseService` (crea logger manualmente)
- `DuplicatesBaseService.execute()` tiene firma diferente (recibe `groups: List[DuplicateGroup]` en lugar de `AnalysisResult`)
- Métodos legacy: algunos servicios tienen `rename_files()`, `detect_in_directory()` además de `analyze()`/`execute()`
- Inconsistencia en nombres: `analyze()` vs `analyze_directory()` vs métodos custom

**Consecuencias**:

- Imposible crear decoradores/wrappers genéricos
- Autocompletado IDE inconsistente
- Dificulta onboarding de nuevos desarrolladores

***

### **🔴 CRÍTICO 3: Gestión de Backup Duplicada**

**Impacto**: ~120 líneas duplicadas en 7 servicios

**Ubicaciones del problema**:

1. **BaseService** tiene `_create_backup_for_operation()` (implementación correcta, centralizada) ✅
2. **FileOrganizerService** reimplementa completamente con `createbackup()` método propio ❌
3. **Todos los execute()** repiten este patrón idéntico:
    - Bloque try/except para `BackupCreationError`
    - Validación `if create_backup and not dry_run`
    - Manejo de caso `backup_path is None`
    - Retorno anticipado si falla backup
    - Población de `result.backup_path`

**Por qué ocurre**: No hay método template que centralice toda esta lógica

***

### **🟡 ALTO 4: Progress Callbacks con 3 Patrones Diferentes**

**Impacto**: ~80 líneas duplicadas, inconsistencia en manejo de cancelación

**Patrón 1** - `BaseService._report_progress()` (correcto):

- Maneja cancelación con flag interno
- Protege contra excepciones en callback
- Logging de cancelaciones
- Usado por: algunos servicios

**Patrón 2** - `utils.callback_utils.safe_progress_callback()`:

- Protección básica contra excepciones
- No maneja cancelación uniformemente
- Usado por: DuplicatesBaseService

**Patrón 3** - Llamadas directas sin protección:

- Sin manejo de excepciones
- Sin validación de None
- Usado por: ZeroByteService, algunos métodos de FileOrganizer

**Problemas adicionales**:

- Formatos de mensaje inconsistentes (una línea vs dos líneas)
- Intervalos de reporte diferentes (`Config.UI_UPDATE_INTERVAL` vs manual)
- Manejo de cancelación no uniforme (algunos servicios no verifican retorno)

***

### **🟡 ALTO 5: Logging Inconsistente (Sistema Centralizado No Usado Uniformemente)**

**Impacto**: ~100 líneas, logs no parseables, formato variado

**Contexto**: Ya existe `utils.logger` con helpers:

- `log_section_header_relevant()` / `log_section_header_discrete()`
- `log_section_footer_relevant()` / `log_section_footer_discrete()`
- Diferenciación: "relevant" para operaciones críticas, "discrete" para análisis

**Problemas detectados**:

1. **Criterio de uso inconsistente**:
    - Algunos servicios usan `header_relevant` para análisis (debería ser `discrete`)
    - No hay convención clara de cuándo usar cada uno
2. **Formato de logs de operaciones variado**:
    - Formato 1: `"FILE_DELETED: {path} | Size: {size}"`
    - Formato 2: `"FILEDELETED {path} Size {size}"`
    - Formato 3: `"File deleted: {path}"`
    - No hay formato estándar para parsear con regex/herramientas
3. **Prefijos de simulación inconsistentes**:
    - Opción A: `"FILE_DELETED_SIMULATION:"` (sufijo en tipo)
    - Opción B: `"[SIMULACIÓN] FILE_DELETED:"` (prefijo en mensaje)
    - Opción C: `"Simulación - Eliminado"` (texto libre)
4. **Niveles de log no estandarizados**:
    - Algunos servicios loguean operaciones individuales en INFO
    - Otros en DEBUG
    - No hay criterio uniforme

**Lo que NO se debe hacer**: No crear nuevo sistema de logging, **usar el existente** pero estandarizar su aplicación.

***

### **🟡 MEDIO 6: Validaciones Duplicadas**

**Impacto**: ~60 líneas repetidas en todos los `analyze()`

**Código duplicado**:

- Validación `if not directory.exists()` con misma excepción
- Validación `if not directory.is_dir()`
- Chequeo de lista vacía `if not files` con retorno anticipado
- Lógica de recopilación de archivos soportados (variaciones del mismo bucle)

**Por qué ocurre**: No hay mixin de validaciones comunes

***

### **🟡 MEDIO 7: Error Handling Duplicado**

**Impacto**: ~70 líneas, mismo patrón try/except en todos lados

**Código repetido en todos los execute()**:

- Try/except para `FileNotFoundError` con log warning y continue
- Try/except genérico con `results.add_error()` y logging
- Construcción de mensajes de error similares
- Manejo de archivos que desaparecen durante operación

***

### **🟡 MEDIO 8: ThreadPool con Código Casi Idéntico**

**Impacto**: ~50 líneas duplicadas

**Servicios que usan ThreadPoolExecutor**:

- `FileRenamerService.analyze()`: Procesamiento paralelo de archivos
- `FileOrganizerService.analyze()`: Recopilación de información
- `DuplicatesExactService.analyze()`: Cálculo de hashes

**Código duplicado en los 3**:

- Obtención de `max_workers` desde `Config` y `settings_manager`
- Context manager con mismo patrón de manejo
- Lógica de cancelación con ThreadPoolExecutor
- Logging de número de workers

**Por qué ocurre**: No hay abstracción en BaseService

***

### **🟢 BAJO 9: Estadísticas y Summaries**

**Impacto**: ~40 líneas

**Problema**: `BaseService._format_operation_summary()` existe pero:

- No todos los servicios lo usan
- Algunos reimplementan lógica similar
- Formato de summary no está 100% estandarizado

***

### **🟢 BAJO 10: Nombres Inconsistentes**

**Impacto**: Deuda técnica conceptual

**Inconsistencias**:

- Resultados de ejecución: `DeletionResult` vs `CleanupDeletionResult` vs `ExecutionResult`
- Análisis: `AnalysisResult` vs `DetectionResult` (LivePhotos usa ambos)
- Métodos: `analyze()` vs `analyze_directory()` en comentarios/docs

***

### **🟢 BAJO 11: Campos Calculados Ineficientes**

**Impacto**: Mantenibilidad

**Problema**: Campos que deberían ser `@property`:

- `RenameAnalysisResult.need_renaming` calculado en `__post_init__` pero puede desincronizarse
- `OrganizationAnalysisResult.total_files_to_move` sincronizado manualmente
- `DuplicateAnalysisResult` normaliza campos según modo en `__post_init__`
- `DuplicatePair` tiene `@property` correctamente, debería ser el estándar

***

### **🟢 BAJO 12: Metadata Cache Disperso**

**Impacto**: Será rehecho, pero actualmente inconsistente

**Problema actual**:

- Algunos servicios guardan como `self.metadata_cache`
- Otros usan `getattr(self, 'metadata_cache', None)`
- FileOrganizerService tiene lógica especial

**Acción**: **NO TOCAR EN ESTA REFACTORIZACIÓN** - Se rehará desde cero en el futuro.

***

## **PLAN DE REFACTORIZACIÓN (6 FASES SECUENCIALES)**

### **📋 FASE 1: Refactorizar `result_types.py`**

**Prioridad**: 🔴 CRÍTICA
**Tiempo estimado**: 4-6 horas
**Prerequisitos**: Ninguno
**Riesgo**: Bajo (no afecta lógica de negocio)

#### **Objetivos**:

1. Eliminar ~200 líneas de campos duplicados
2. Crear jerarquía clara con composición (herencia múltiple de dataclasses)
3. Convertir campos calculados a `@property`
4. Eliminar aliases innecesarios

#### **Acciones detalladas**:

**1.1 - Diseñar jerarquía de clases base**:

- Crear `BaseResult` con campos universales (`success`, `errors`, `message`)
- Implementar métodos comunes (`has_errors`, `error`, `add_error`)
- Simplificar `__post_init__` (solo llamar a `super().__post_init__()` si necesario)

**1.2 - Crear mixins especializados**:

- `BackupMixin`: Para operaciones que crean backup (`backup_path: Optional[str]`)
- `DryRunMixin`: Para modo simulación (`dry_run: bool`)
- `DryRunStatsMixin`: Extiende `DryRunMixin` con `simulated_files_deleted`, `simulated_space_freed`
- `FileListMixin`: Para operaciones que rastrean archivos (`deleted_files: List[str]`)

**1.3 - Refactorizar cada dataclass**:

- Cambiar herencia simple a herencia múltiple usando mixins apropiados
- Eliminar campos que ahora vienen de clases base/mixins
- Mantener solo campos específicos del dominio

**1.4 - Convertir contadores a propiedades calculadas**:

- `RenameAnalysisResult.need_renaming` → `@property` que retorna `len(self.renaming_plan)`
- `OrganizationAnalysisResult.total_files_to_move` → `@property` basado en `move_plan`
- `HeicAnalysisResult.total_pairs` → `@property` basado en `duplicate_pairs`
- Eliminar sincronizaciones manuales en `__post_init__`

**1.5 - Eliminar aliases redundantes**:

- `HeicDeletionResult.kept_format` → Eliminar, mantener solo `format_kept`
- Documentar en docstring si había alias legacy para referencia futura

**1.6 - Simplificar `__post_init__`**:

- Mantener solo validaciones críticas que no pueden ser `@property`
- Llamar a `super().__post_init__()` cuando corresponda
- Eliminar toda lógica de sincronización de contadores


#### **Validación de Fase 1**:

- ✅ Todas las dataclasses heredan de `BaseResult` (directa o indirectamente)
- ✅ No hay campos `success`, `errors`, `message` duplicados fuera de `BaseResult`
- ✅ Campos `simulated_*` solo en clases que heredan `DryRunStatsMixin`
- ✅ Contadores sincronizados son `@property`, no campos con `__post_init__`
- ✅ Tests unitarios de serialización/deserialización pasan
- ✅ Ninguna clase tiene alias de campos (eliminar `kept_format`, etc.)


#### **Criterio de completitud**:

- Ejecutar tests: `pytest tests/test_result_types.py -v`
- Verificar que UI puede deserializar todos los resultados sin cambios
- Contar líneas eliminadas (objetivo: ~200)

***

### **📋 FASE 2: Estandarizar `BaseService`**

**Prioridad**: 🔴 CRÍTICA
**Tiempo estimado**: 6-8 horas
**Prerequisitos**: Fase 1 completada
**Riesgo**: Medio (infraestructura crítica)

#### **Objetivos**:

1. Crear método template para `execute()` con backup automático
2. Centralizar manejo de ThreadPool
3. Estandarizar progress reporting
4. Crear mixins de validación
5. Documentar convenciones de uso de logger existente

#### **Acciones detalladas**:

**2.1 - Crear método template para ejecución con backup**:

Diseñar método `_execute_with_backup()` que encapsula:

- Lógica de decisión: ¿crear backup? (solo si `create_backup=True` y `dry_run=False`)
- Llamada a `_create_backup_for_operation()` con manejo de errores
- Captura de `BackupCreationError` con retorno anticipado de resultado de error
- Llamada a función de ejecución real (pasada como parámetro)
- Población automática de `backup_path` en resultado
- Manejo de excepciones genéricas con logging

**Parámetros del método**:

- `files`: Iterable de archivos/paths/dicts (para backup)
- `operation_name`: String para logging y nombre de backup
- `execute_fn`: Callable que ejecuta la operación real (recibe `dry_run: bool`)
- `create_backup`: Flag de backup
- `dry_run`: Flag de simulación
- `progress_callback`: Callback opcional

**Retorno**: Resultado de `execute_fn` con `backup_path` poblado si corresponde

**2.2 - Centralizar configuración de ThreadPool**:

Crear dos métodos complementarios:

**Método 1**: `_get_max_workers(io_bound: bool = True) -> int`

- Obtiene override del usuario desde `settings_manager`
- Llama a `Config.get_actual_worker_threads()`
- Logging de número de workers elegidos
- Documenta cuándo usar `io_bound=True` vs `False`

**Método 2**: `_parallel_processor(io_bound: bool = True)` como context manager

- Usa `_get_max_workers()` internamente
- Yields `ThreadPoolExecutor` configurado
- Manejo automático de shutdown
- Compatible con cancelación cooperativa

**2.3 - Estandarizar progress reporting**:

Auditar uso actual de `_report_progress()`:

- Ya existe en `BaseService` y funciona bien
- Problema: no todos los servicios lo usan
- Acción: Documentar como método estándar obligatorio
- Deprecar usos de `safe_progress_callback` de utils (migrar a `_report_progress`)

Considerar crear helper para intervalos:

- `_should_report_progress(counter: int) -> bool`: retorna True cada `Config.UI_UPDATE_INTERVAL`

**2.4 - Crear ValidationMixin en BaseService**:

Añadir métodos de validación como parte de `BaseService`:

**Método 1**: `_validate_directory(directory: Path, must_exist: bool = True)`

- Valida existencia si `must_exist=True`
- Valida que es directorio
- Lanza `ValueError` con mensaje descriptivo

**Método 2**: `_get_supported_files(directory: Path, recursive: bool = True) -> List[Path]`

- Recopila archivos multimedia soportados
- Usa `Config.is_supported_file()`
- Patrón `**/*` si recursive, `*` si no
- Opcionalmente puede reportar progreso

**2.5 - Documentar convenciones de logging**:

**NO crear nuevo LoggerMixin**, el sistema de `utils.logger` ya existe y funciona.

**Acción**: Escribir docstring en `BaseService` que documente:

**Convención de headers**:

- Usar `log_section_header_relevant()` para operaciones que modifican disco (execute)
- Usar `log_section_header_discrete()` para operaciones de solo lectura (analyze)
- Parámetro `mode` para indicar simulación: `mode="SIMULACIÓN"` cuando `dry_run=True`

**Convención de logs de operaciones**:

- Formato estándar: `{TYPE}: {path} | Size: {size} | Date: {date} | Type: {filetype}`
- Tipos válidos: `FILE_DELETED`, `FILE_MOVED`, `FILE_RENAMED`, `FILE_CONVERTED`
- Simulación: Añadir sufijo `_SIMULATION` al tipo (ej: `FILE_DELETED_SIMULATION`)

**Convención de footers**:

- Usar `log_section_footer_relevant()` con summary construido por `_format_operation_summary()`

**Niveles de log**:

- INFO: Operaciones de modificación, resúmenes, inicio/fin de fases
- DEBUG: Detalles internos, procesamiento archivo por archivo
- WARNING: Archivos no encontrados, problemas no críticos
- ERROR: Fallos en operaciones críticas

**2.6 - Mejorar `_format_operation_summary()`**:

Extender método existente para cubrir todos los casos de uso actuales:

- Añadir soporte para múltiples estadísticas (no solo archivos y espacio)
- Considerar parámetros opcionales para conflictos resueltos, carpetas creadas, etc.
- Mantener compatibilidad con llamadas existentes


#### **Validación de Fase 2**:

- ✅ `_execute_with_backup()` implementado con tests unitarios
- ✅ `_parallel_processor()` testeado con operaciones dummy
- ✅ Documentación de convenciones de logging en docstring de clase
- ✅ Métodos de validación con tests para casos edge
- ✅ Todos los tests existentes de servicios siguen pasando


#### **Criterio de completitud**:

- Ejecutar: `pytest tests/test_base_service.py -v`
- Revisar docstrings generados con `pydoc` o IDE
- Validar que `_execute_with_backup()` maneja todos los casos: con/sin backup, con/sin dry_run, con/sin errores

***

### **📋 FASE 3: Migrar Servicios a Nueva Arquitectura**

**Prioridad**: 🟡 ALTA
**Tiempo estimado**: 8-12 horas
**Prerequisitos**: Fases 1 y 2 completadas
**Riesgo**: Medio-Alto (modifica lógica de negocio)

#### **Objetivos**:

1. Todos los servicios heredan correctamente de `BaseService`
2. Todos usan `_execute_with_backup()` template
3. Eliminar código duplicado de backup, validación, ThreadPool
4. Estandarizar uso de `_report_progress()`

#### **Estrategia de migración**:

**Migrar uno por uno, de más simple a más complejo, con tests en cada paso**

#### **Acciones por servicio**:

**3.1 - ZeroByteService** (más simple, comenzar aquí):

**Problemas actuales**:

- No hereda de `BaseService`
- Crea logger manualmente con `get_logger('ZeroByteService')`
- Implementa backup y error handling manualmente

**Migración**:

1. Cambiar declaración de clase: `class ZeroByteService(BaseService)`
2. Modificar `__init__()`: llamar a `super().__init__('ZeroByteService')` y eliminar `self.logger = get_logger(...)`
3. Refactorizar `analyze()`: usar `_validate_directory()` y `_get_supported_files()` si aplica
4. Refactorizar `execute()`: extraer lógica de eliminación a método privado `_do_deletion()`, usar `_execute_with_backup()` template
5. Reemplazar llamadas directas a callback por `_report_progress()`
6. Tests: validar con/sin backup, con/sin dry_run

**3.2 - FileRenamerService**:

**Problemas actuales**:

- Manejo manual de backup con try/except
- ThreadPool con código manual de configuración
- Mezcla de `_report_progress()` y llamadas directas

**Migración**:

1. `analyze()`: reemplazar configuración manual de ThreadPool por `with self._parallel_processor(io_bound=True)`
2. `execute()`: extraer lógica de renombrado a `_do_renaming(plan, dry_run, progress_callback)`
3. `execute()`: reemplazar bloque de backup por llamada a `_execute_with_backup()`
4. Estandarizar todos los progress reports usando `_report_progress()`
5. Tests: validar operación paralela, cancelación, conflictos de nombres

**3.3 - FileOrganizerService** (más complejo):

**Problemas actuales**:

- Método `createbackup()` completamente custom (no usa `_create_backup_for_operation`)
- ThreadPool con código manual
- Lógica de `execute()` muy larga

**Migración**:

1. **Eliminar completamente** método `createbackup()`
2. `analyze()`: reemplazar ThreadPool manual por `_parallel_processor()`
3. `execute()`: extraer lógica de movimiento a `_do_organization(move_plan, dry_run, progress_callback)`
4. `execute()`: usar `_execute_with_backup()` pasando files de `move_plan`
5. Simplificar lógica de limpieza de directorios vacíos (extraer a método privado)
6. Tests: validar múltiples modos de organización (by_month, by_year, etc.), carpetas creadas

**3.4 - DuplicatesBaseService**:

**Problemas actuales**:

- `execute()` recibe `groups: List[DuplicateGroup]` en lugar de `AnalysisResult`
- Usa `safe_progress_callback` de utils en lugar de `_report_progress()`

**Migración**:

1. **Decisión de diseño**: ¿Cambiar firma de `execute()` o mantener compatibilidad?
    - Opción A (recomendada): Cambiar a `execute(analysis_result: DuplicateAnalysisResult, keep_strategy, ...)`
    - Opción B: Mantener firma pero extraer groups con `analysis_result.groups`
2. Reemplazar `safe_progress_callback` por `self._report_progress()` en `_process_group_deletion()`
3. Ya usa `_create_backup_for_operation()` correctamente, validar que sigue funcionando
4. Tests: validar estrategias de eliminación (oldest, newest, manual)

**3.5 - DuplicatesExactService y DuplicatesSimilarService**:

**Problemas actuales**:

- ThreadPool con configuración manual en `analyze()`
- Heredan de `DuplicatesBaseService`, heredarán cambios automáticamente

**Migración**:

1. `analyze()`: reemplazar configuración de ThreadPool por `_parallel_processor(io_bound=True)`
2. Validar que cambios en `DuplicatesBaseService` no rompen funcionalidad
3. Tests: validar detección de duplicados exactos/similares, eliminación

**3.6 - LivePhotosService**:

**Problemas actuales**:

- Manejo manual de backup
- Lógica de `execute()` larga con try/except repetitivo

**Migración**:

1. `execute()`: extraer lógica de eliminación a `_do_live_photo_cleanup(files_to_delete, dry_run, progress_callback)`
2. Usar `_execute_with_backup()` template
3. Estandarizar logging de operaciones (usar convenciones definidas)
4. Tests: validar modos keep_image, keep_video, detección de pares

**3.7 - HeicService**:

**Problemas actuales**:

- Manejo manual de backup
- Duplicación con LivePhotosService en estructura

**Migración**:

1. `execute()`: extraer lógica a `_do_heic_cleanup(pairs, format_to_keep, dry_run, progress_callback)`
2. Usar `_execute_with_backup()` template
3. Estandarizar logging
4. Tests: validar keep_heic, keep_jpg, detección de pares duplicados

#### **Validación de Fase 3**:

- ✅ Todos los servicios heredan de `BaseService` (verificar con `issubclass()`)
- ✅ Ningún servicio tiene método `createbackup()` custom
- ✅ Ningún servicio configura `ThreadPoolExecutor` manualmente
- ✅ Todos usan `_report_progress()` (no `safe_progress_callback` ni llamadas directas)
- ✅ Todos los tests de integración pasan para cada servicio
- ✅ UI funciona sin cambios (validación manual)


#### **Criterio de completitud**:

- Para cada servicio migrado: ejecutar su test suite completa
- Ejecutar tests de integración: `pytest tests/integration/ -v`
- Validar manualmente en UI: crear backup, dry_run, cancelación
- Contar líneas eliminadas por servicio (objetivo global: ~400 líneas)

***

### **📋 FASE 4: Estandarizar Aplicación de Logging**

**Prioridad**: 🟡 MEDIA
**Tiempo estimado**: 3-4 horas
**Prerequisitos**: Fase 3 completada
**Riesgo**: Bajo (solo afecta logs)

#### **Objetivos**:

1. Aplicar uniformemente convenciones de logging documentadas en Fase 2
2. Formato parseables para análisis posterior
3. Niveles apropiados

#### **Acciones detalladas**:

**4.1 - Auditar uso actual de funciones de logging**:

Crear checklist por servicio:

- ¿Usa `log_section_header_relevant` para execute?
- ¿Usa `log_section_header_discrete` para analyze?
- ¿Pasa parámetro `mode="SIMULACIÓN"` cuando `dry_run=True`?
- ¿Logs de operaciones siguen formato estándar?
- ¿Usa sufijo `_SIMULATION` para simulaciones?
- ¿Usa `log_section_footer_relevant` con `_format_operation_summary()`?

**4.2 - Estandarizar logs de operaciones por tipo**:

**Operaciones de eliminación**:

- Tipo: `FILE_DELETED` o `FILE_DELETED_SIMULATION`
- Formato: `FILE_DELETED: {path} | Size: {size} | Date: {date} | Type: {type}`
- Servicios: ZeroByteService, DuplicatesService, LivePhotosService, HeicService

**Operaciones de movimiento**:

- Tipo: `FILE_MOVED` o `FILE_MOVED_SIMULATION`
- Formato: `FILE_MOVED: {path} | From: {source_dir} | To: {target_dir} | Size: {size}`
- Servicios: FileOrganizerService

**Operaciones de renombrado**:

- Tipo: `FILE_RENAMED` o `FILE_RENAMED_SIMULATION`
- Formato: `FILE_RENAMED: {old_name} -> {new_name} | Date: {date} | Conflict: {seq}`
- Servicios: FileRenamerService

**Operaciones de conversión** (si aplica):

- Tipo: `FILE_CONVERTED` o `FILE_CONVERTED_SIMULATION`
- Formato: `FILE_CONVERTED: {path} | From: {format} | To: {format} | Size: {size}`

**4.3 - Normalizar niveles de log**:

**Establecer reglas**:

- **INFO**: Headers/footers de sección, resúmenes de operación, archivos procesados (cada N archivos según `Config.LOG_PROGRESS_INTERVAL`)
- **DEBUG**: Operaciones individuales muy frecuentes, detalles internos, decisiones de algoritmos
- **WARNING**: Archivos no encontrados pero operación continúa, problemas no críticos
- **ERROR**: Fallos en operaciones críticas, excepciones capturadas

**Migrar**:

- Operaciones de modificación de archivos: INFO (pero respetar intervalos)
- Detalles de detección de duplicados: DEBUG
- Archivos saltados: WARNING

**4.4 - Documentar formato para parsing**:

Crear regex patterns en docstring de `BaseService` para extraer información de logs:

Ejemplo:

```
Formato de logs parseables:

FILE_DELETED: Patrón: ^FILE_DELETED(?:_SIMULATION)?: (.+) \| Size: (.+) \| Date: (.+) \| Type: (.+)$
FILE_MOVED: Patrón: ^FILE_MOVED(?:_SIMULATION)?: (.+) \| From: (.+) \| To: (.+) \| Size: (.+)$
FILE_RENAMED: Patrón: ^FILE_RENAMED(?:_SIMULATION)?: (.+) -> (.+) \| Date: (.+)(?:\| Conflict: (\d+))?$
```


#### **Validación de Fase 4**:

- ✅ Todos los servicios usan headers/footers correctos
- ✅ Formato de logs de operaciones consistente y parseable
- ✅ Simulaciones usan sufijo `_SIMULATION` uniformemente
- ✅ Niveles de log apropiados según reglas definidas
- ✅ Regex patterns documentados pueden parsear logs reales


#### **Criterio de completitud**:

- Ejecutar operaciones de cada servicio y capturar logs
- Validar que regex patterns extraen información correctamente
- Verificar que logs son legibles para humanos y máquinas

***

### **📋 FASE 5: Optimizar Uso de ThreadPool**

**Prioridad**: 🟢 BAJA
**Tiempo estimado**: 2-3 horas
**Prerequisitos**: Fase 3 completada
**Riesgo**: Bajo (optimización)

#### **Objetivos**:

1. Código de ThreadPool centralizado (logrado en Fase 2/3)
2. Identificar servicios que podrían beneficiarse de paralelización
3. Medir mejoras de rendimiento

#### **Acciones detalladas**:

**5.1 - Identificar candidatos para paralelización**:

Candidatos actuales (ya usan ThreadPool):

- ✅ `FileRenamerService.analyze()`: Procesamiento de metadatos de archivos
- ✅ `FileOrganizerService.analyze()`: Recopilación de información de archivos
- ✅ `DuplicatesExactService.analyze()`: Cálculo de hashes SHA256

Candidatos potenciales (evaluar beneficio):

- `LivePhotosService.analyze()`: Lectura de metadatos de fotos/videos (IO-bound)
- `HeicService.analyze()`: Lectura de metadatos de pares HEIC/JPG (IO-bound)
- `DuplicatesSimilarService.analyze()`: Cálculo de hashes perceptuales (CPU-bound pero podría beneficiarse)

**5.2 - Evaluar beneficio vs complejidad**:

Para cada candidato potencial:

- Medir tiempo de ejecución actual con dataset de prueba grande (>1000 archivos)
- Implementar versión paralela usando `_parallel_processor()`
- Medir tiempo de ejecución paralelo
- Evaluar overhead vs beneficio (solo implementar si mejora >20%)

**5.3 - Implementar paralelización donde convenga**:

Si beneficio es significativo:

1. Refactorizar bucle secuencial a procesamiento paralelo
2. Asegurar thread-safety de estructuras de datos compartidas (usar locks si necesario)
3. Mantener cancelación cooperativa funcionando
4. Tests de rendimiento: validar mejora es consistente

**5.4 - Documentar decisiones**:

En docstring de servicios que NO se paralelizaron:

- Explicar por qué (ej: "Paralelización evaluada pero overhead supera beneficio para datasets típicos <500 archivos")


#### **Validación de Fase 5**:

- ✅ Servicios que usan ThreadPool tienen código centralizado (ya logrado en Fase 3)
- ✅ Nuevas paralelizaciones muestran mejora medible de rendimiento
- ✅ Cancelación sigue funcionando con operaciones paralelas
- ✅ No hay race conditions (validar con tests concurrentes)


#### **Criterio de completitud**:

- Ejecutar benchmarks: `pytest tests/benchmarks/ -v`
- Documentar mejoras de rendimiento en changelog

**Nota**: Esta fase es **opcional** si no hay tiempo. Fase 3 ya centraliza el código de ThreadPool, que era el objetivo principal.

***

### **📋 FASE 6: Testing Exhaustivo y Documentación**

**Prioridad**: 🔴 CRÍTICA
**Tiempo estimado**: 4-6 horas
**Prerequisitos**: Todas las fases anteriores
**Riesgo**: N/A (validación)

#### **Objetivos**:

1. Cobertura de tests ≥80%
2. Documentación actualizada y completa
3. Validación de compatibilidad con UI
4. Guía para futuros desarrolladores

#### **Acciones detalladas**:

**6.1 - Tests unitarios de nueva infraestructura**:

**Tests para `result_types.py`**:

- Instanciación de todas las dataclasses con valores mínimos
- Serialización/deserialización (si se usa)
- Propiedades calculadas retornan valores correctos
- Mixins funcionan con herencia múltiple
- `add_error()` modifica `success` correctamente

**Tests para `BaseService`**:

- `_execute_with_backup()` con todas las combinaciones: backup/no-backup, dry_run/real
- `_execute_with_backup()` maneja `BackupCreationError` correctamente
- `_parallel_processor()` yields executor configurado correctamente
- `_validate_directory()` lanza excepciones apropiadas
- `_get_supported_files()` filtra archivos correctamente
- `_report_progress()` maneja cancelación
- `_format_operation_summary()` formatea correctamente

**6.2 - Tests de integración por servicio**:

Para cada servicio, validar matriz de casos:

- **Análisis básico**: Directorio con archivos soportados
- **Ejecución normal**: Con modificación real de archivos
- **Modo dry_run**: Sin modificar archivos, campos `simulated_*` correctos
- **Con backup**: `backup_path` poblado, archivos respaldados
- **Sin backup**: `backup_path` es None
- **Cancelación**: Usuario cancela a mitad de operación
- **Errores**: Archivos no encontrados, permisos denegados, disco lleno (mockear)
- **Edge cases**: Directorio vacío, archivos ya procesados, conflictos de nombres

**6.3 - Tests de compatibilidad con UI**:

**Validación manual** (automatizar si es posible):

1. Cargar proyecto real en UI
2. Ejecutar cada servicio con diferentes configuraciones
3. Validar que progress bars se actualizan
4. Validar que resultados se muestran correctamente
5. Validar que cancelación funciona desde UI
6. Validar que backups se crean y restauran correctamente

**6.4 - Tests de regresión**:

**Comparar comportamiento antes/después**:

- Ejecutar cada servicio con dataset de referencia
- Comparar resultados (número de archivos procesados, espacio liberado, etc.)
- Validar que resultados son idénticos (o mejores si hubo bug fixes)
- Comparar logs generados (formato puede cambiar pero información debe ser equivalente)

**6.5 - Documentación técnica**:

**Actualizar docstrings**:

- `BaseService`: Documentar todos los métodos nuevos, convenciones de logging
- Cada servicio: Actualizar ejemplos de uso si cambiaron firmas
- `result_types.py`: Documentar jerarquía de clases, propósito de cada mixin

**Crear guías**:

1. **Guía de implementación de nuevo servicio**:
    - Template mínimo de servicio
    - Qué métodos implementar (analyze/execute)
    - Cómo usar `_execute_with_backup()`
    - Convenciones de logging
    - Cómo añadir tests
2. **Guía de convenciones de código**:
    - Nomenclatura de clases de resultados
    - Cuándo usar `log_section_header_relevant` vs `discrete`
    - Formato de logs de operaciones
    - Cuándo paralelizar con ThreadPool
3. **Changelog detallado**:
    - Resumen de cambios por fase
    - Breaking changes (si los hay)
    - Mejoras de rendimiento medibles
    - Líneas de código eliminadas

**6.6 - Revisión de código**:

**Checklist final**:

- ✅ No hay código comentado (eliminar o documentar por qué)
- ✅ No hay TODOs sin issue asociado
- ✅ No hay imports sin usar
- ✅ No hay variables sin usar
- ✅ Docstrings en todos los métodos públicos
- ✅ Type hints completos (verificar con `mypy` si se usa)


#### **Validación de Fase 6**:

- ✅ Cobertura de tests ≥80% (verificar con `pytest --cov`)
- ✅ Todos los tests pasan: unitarios, integración, regresión
- ✅ UI funciona sin cambios observables para el usuario
- ✅ Documentación generada con éxito (`pydoc`, Sphinx, etc.)
- ✅ Guías de desarrollo creadas y revisadas


#### **Criterio de completitud**:

- Ejecutar suite completa: `pytest --cov=services --cov-report=html`
- Validar cobertura por módulo
- Revisar HTML de cobertura para identificar gaps
- Validación manual exhaustiva de UI (checklist de casos de uso)

***

## **REGLAS IMPERATIVAS DE REFACTORIZACIÓN**

### **✅ HACER**:

1. **Mantener compatibilidad con UI**:
    - Firmas públicas de `analyze()` y `execute()` no deben cambiar
    - Estructura de resultados (dataclasses) puede cambiar internamente pero campos usados por UI deben existir
    - UI no debe requerir modificaciones
2. **Usar solo dataclasses para resultados**:
    - No introducir Pydantic, attrs, NamedTuple u otras alternativas
    - Herencia múltiple está permitida (es feature de dataclasses)
    - `@property` para campos calculados está permitido
3. **Respetar sistema de logging existente**:
    - Usar funciones de `utils.logger` (no crear nuevo sistema)
    - Aplicar convenciones definidas uniformemente
    - No modificar el módulo `logger.py`
4. **Tests primero para cambios críticos**:
    - Escribir test que falla antes de refactorizar lógica crítica
    - Validar que test pasa después de refactorizar
    - Mantener tests verdes en todo momento
5. **Commits atómicos y descriptivos**:
    - Un commit por fase o sub-fase lógica
    - Mensaje: "Fase X.Y: [Descripción]" (ej: "Fase 1.2: Crear mixins para result types")
    - Incluir tests en el mismo commit que el código
6. **Documentar decisiones de diseño**:
    - Comentarios para explicar "por qué" no "qué"
    - Docstrings exhaustivos en métodos públicos
    - Actualizar guías cuando se establezcan patrones
7. **Herencia múltiple para mixins**:
    - Aprovechar composición con mixins de dataclasses
    - Orden de herencia: `(BaseResult, Mixin1, Mixin2, ...)`
    - Siempre llamar `super().__post_init__()` si se sobreescribe
8. **Propiedades calculadas**:
    - Usar `@property` para contadores derivados
    - Eliminar sincronización manual en `__post_init__`
    - Documentar que es calculado en docstring

### **❌ NO HACER**:

1. **NO tocar metadata_cache**:
    - Será rehecho desde cero en el futuro
    - Ignorar todo código relacionado con caché de metadatos
    - No optimizar, no refactorizar, no mejorar
2. **NO cambiar firmas públicas sin consenso**:
    - `analyze(directory, **kwargs)` y `execute(result, **kwargs)` son contratos
    - Añadir parámetros opcionales está OK
    - Cambiar parámetros obligatorios requiere validar UI primero
3. **NO modificar `Config`**:
    - Sistema de configuración global fuera del alcance
    - No cambiar `Config.UI_UPDATE_INTERVAL`, `Config.LOG_PROGRESS_INTERVAL`, etc.
    - Usar valores existentes
4. **NO crear nuevo sistema de logging**:
    - `utils.logger` ya existe y funciona
    - No crear `LoggerMixin` con métodos nuevos
    - Documentar convenciones de uso, no reimplementar
5. **NO optimizar prematuramente**:
    - Enfoque en eliminar duplicación primero
    - Optimización de rendimiento solo en Fase 5 y con mediciones
    - No añadir complejidad sin beneficio demostrable
6. **NO refactorizar UI**:
    - Solo lógica de servicios
    - Vista/controladores intocables
    - Validar compatibilidad, no modificar
7. **NO usar decorators complejos**:
    - Mantener simplicidad y explícito
    - Favorecer composición sobre magia
    - Template methods son OK, decorators complejos no
8. **NO introducir dependencias nuevas**:
    - Solo stdlib y dependencias ya existentes del proyecto
    - No añadir librerías externas sin discusión
9. **NO dejar TODOs sin rastro**:
    - Si queda algo pendiente, crear issue/ticket
    - Referenciar issue en comentario: `# TODO(#123): ...`
    - No dejar TODOs huérfanos
10. **NO mezclar refactorización con nuevas features**:
    - Este es un trabajo de limpieza técnica
    - No añadir funcionalidad nueva
    - Si surge una idea, crear issue separado

***

## **CRITERIOS DE ÉXITO (KPIs)**

### **Métricas Cuantitativas**:

1. **Reducción de duplicación**:
    - ✅ Objetivo: ~700 líneas eliminadas
    - Medir: Comparar `wc -l` antes/después de refactorización
    - Meta mínima: 500 líneas (71%)
2. **Cobertura de tests**:
    - ✅ Objetivo: ≥80% cobertura
    - Medir: `pytest --cov=services --cov-report=term`
    - Meta mínima: 75%
3. **Jerarquía de clases**:
    - ✅ Objetivo: 100% servicios heredan de `BaseService`
    - Medir: Verificar con `issubclass()` o inspección manual
    - Meta mínima: 100% (no negociable)
4. **Regresiones**:
    - ✅ Objetivo: 0 regresiones
    - Medir: Tests existentes deben pasar al 100%
    - Meta mínima: 0 regresiones (no negociable)
5. **Rendimiento**:
    - ✅ Objetivo: ±5% tiempo de ejecución
    - Medir: Benchmarks con dataset estándar
    - Meta mínima: Sin degradación >10%

### **Métricas Cualitativas**:

1. **Interfaz consistente**:
    - ✅ Todos los servicios tienen `analyze()` y `execute()` con firmas similares
    - ✅ Autocompletado IDE funciona uniformemente
    - ✅ Nuevos desarrolladores pueden entender estructura en <1 hora
2. **Código mantenible**:
    - ✅ No hay métodos >100 líneas (extraer a métodos privados si supera)
    - ✅ No hay archivos >800 líneas (considerar split si supera)
    - ✅ Complejidad ciclomática razonable (usar herramienta como `radon`)
3. **Documentación completa**:
    - ✅ Todos los métodos públicos tienen docstring con Args/Returns/Raises
    - ✅ Guía de "Cómo añadir nuevo servicio" escrita y revisada
    - ✅ Convenciones de logging documentadas
4. **Logs útiles**:
    - ✅ Formato parseable con regex
    - ✅ Información suficiente para debugging
    - ✅ Niveles apropiados (no spam en INFO)
5. **Base sólida**:
    - ✅ Template claro para añadir nuevos servicios
    - ✅ Infraestructura reutilizable (backup, progress, validación)
    - ✅ Fácil evolucionar sin romper existente

***

## **ESTRATEGIA DE IMPLEMENTACIÓN**

### **Orden de Ejecución**:

1. **Fase 1** (result_types.py) → Independiente, alto impacto, bajo riesgo
2. **Fase 2** (base_service.py) → Crea infraestructura para resto
3. **Fase 3** (migración servicios) → Uno por uno, validar continuamente
4. **Fase 4** (logging) → Puede hacerse en paralelo con Fase 5
5. **Fase 5** (ThreadPool) → Opcional, solo si hay tiempo
6. **Fase 6** (testing) → Al final, valida todo

### **Duración Estimada**:

- **Total optimista**: 27-35 horas
- **Total realista**: 35-45 horas (considerando imprevistos)
- **Distribución**: ~40% Fase 3, ~20% Fase 1+2, ~20% Fase 6, ~20% resto


### **Punto de Control por Fase**:

Al final de cada fase:

1. Ejecutar suite de tests completa
2. Validar manualmente en UI casos básicos
3. Commit con mensaje descriptivo
4. Breve revisión de código (self-review o peer-review)
5. Decidir: ¿continuar a siguiente fase o hay problemas?

### **Rollback Plan**:

Si algo sale muy mal:

- Cada fase es un commit atómico → fácil revertir
- Tests deben estar verdes antes de continuar a siguiente fase
- Si Fase 3 falla en un servicio, continuar con otros y retomar después

***

## **CÓMO USAR ESTE PROMPT**

### **Para IA en IDE**:

1. **Alimentar contexto**: Proporcionar este prompt completo + archivos relevantes
2. **Empezar por Fase 1**: Pedir específicamente "Implementa Fase 1, paso 1.1"
3. **Validar cada paso**: Ejecutar tests antes de continuar al siguiente paso
4. **Iterar**: Completar fase antes de pasar a la siguiente
5. **Preguntar ante dudas**: Si surge decisión de diseño no clara, preguntar antes de implementar

### **Comandos Útiles**:

**Validar estado actual**:

```bash
# Ver líneas de código
find services -name "*.py" | xargs wc -l

# Ver cobertura de tests
pytest --cov=services --cov-report=term-missing

# Ver complejidad
radon cc services -a -nb
```

**Ejecutar tests por fase**:

```bash
# Fase 1
pytest tests/test_result_types.py -v

# Fase 2
pytest tests/test_base_service.py -v

# Fase 3 (por servicio)
pytest tests/test_zero_byte_service.py -v

# Todos
pytest tests/ -v --cov=services
```


***

## **PREGUNTAS PARA VALIDAR ANTES DE EMPEZAR**

1. ¿Existe suite de tests actual? Si no, crear tests básicos primero
2. ¿UI tiene tests automatizados o solo validación manual?
3. ¿Hay entorno de staging para validar antes de producción?
4. ¿Hay dataset de referencia para tests de regresión?
5. ¿Hay restricciones de compatibilidad con versiones antiguas de Python?

***

**¿Estás listo para empezar con la Fase 1 (refactorizar `result_types.py`)?**

Si es así, proporciona los archivos relevantes y especifica: **"Implementa Fase 1, paso 1.1: Diseñar jerarquía de clases base"**

