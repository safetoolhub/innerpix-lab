# Especificaciones Técnicas del Refactor - Fase 2

Este documento contiene las especificaciones exactas de cada cambio requerido en la Fase 2 (eliminación de métodos deprecated).

---

## 📐 Especificaciones por Servicio

### 1. file_renamer_service.py

#### Cambio 1.1: Método `analyze()`

**Ubicación actual:** Líneas ~47-66 (método actual es alias)

**Estado actual:**
```python
def analyze(
    self,
    directory: Path,
    progress_callback: Optional[ProgressCallback] = None
) -> RenameAnalysisResult:
    """Método unificado - actualmente delega a analyze_directory()"""
    return self.analyze_directory(directory, progress_callback)
```

**Estado deseado:**
```python
def analyze(
    self,
    directory: Path,
    progress_callback: Optional[ProgressCallback] = None
) -> RenameAnalysisResult:
    """
    Analiza un directorio para renombrado.
    
    Este es el método estándar de análisis.
    
    Args:
        directory: Directorio a analizar
        progress_callback: Función callback(current, total, message)
        
    Returns:
        RenameAnalysisResult con análisis detallado
    """
    # COPIAR TODA LA LÓGICA de analyze_directory() AQUÍ (líneas ~100-250)
    self.logger.info(f"Analizando directorio para renombrado: {directory}")
    
    all_files = []
    for file_path in directory.rglob("*"):
        if file_path.is_file() and Config.is_supported_file(file_path.name):
            all_files.append(file_path)
    
    total_files = len(all_files)
    renaming_map = {}
    already_renamed = 0
    cannot_process = 0
    conflicts = 0
    files_by_year = Counter()
    renaming_plan = []
    issues = []
    
    # ... [RESTO DE LA LÓGICA - ver líneas 100-250 del archivo actual]
    
    return RenameAnalysisResult(
        success=True,
        total_files=total_files,
        already_renamed=already_renamed,
        need_renaming=need_renaming,
        cannot_process=cannot_process,
        conflicts=conflicts,
        files_by_year=dict(files_by_year),
        renaming_plan=renaming_plan,
        issues=issues
    )
```

**Método a eliminar:**
```python
# ELIMINAR COMPLETAMENTE (líneas ~100-250)
@deprecated(reason="Nomenclatura inconsistente", replacement="analyze()")
def analyze_directory(self, directory: Path, progress_callback: Optional[ProgressCallback] = None) -> RenameAnalysisResult:
    # ... todo el método
```

#### Cambio 1.2: Método `execute()`

**Ubicación actual:** Líneas ~68-94 (método actual es alias)

**Estado actual:**
```python
def execute(
    self,
    renaming_plan: List[Dict],
    create_backup: bool = True,
    dry_run: bool = False,
    progress_callback: Optional[ProgressCallback] = None
) -> RenameResult:
    """Método unificado - actualmente delega a execute_renaming()"""
    return self.execute_renaming(renaming_plan, create_backup, dry_run, progress_callback)
```

**Estado deseado:**
```python
def execute(
    self,
    renaming_plan: List[Dict],
    create_backup: bool = True,
    dry_run: bool = False,
    progress_callback: Optional[ProgressCallback] = None
) -> RenameResult:
    """
    Ejecuta el renombrado según el plan.
    
    Si el destino existe, busca siguiente sufijo disponible.
    
    Args:
        renaming_plan: Plan de renombrado del análisis
        create_backup: Si crear backup antes de proceder
        dry_run: Si True, simula la operación
        progress_callback: Callback para reportar progreso
        
    Returns:
        RenameResult con resultados de la operación
    """
    # COPIAR TODA LA LÓGICA de execute_renaming() AQUÍ (líneas ~255-400)
    if not renaming_plan:
        return RenameResult(
            success=True,
            files_renamed=0,
            message='No hay archivos para renombrar',
            dry_run=dry_run
        )

    mode_label = "SIMULACIÓN" if dry_run else ""
    self._log_section_header("INICIANDO RENOMBRADO DE ARCHIVOS", mode=mode_label)
    self.logger.info(f"*** Archivos a renombrar: {len(renaming_plan)}")

    results = RenameResult(success=True, dry_run=dry_run)

    try:
        # ... [RESTO DE LA LÓGICA - ver líneas 255-400]
        
    except Exception as e:
        # ... error handling
    
    return results
```

**Método a eliminar:**
```python
# ELIMINAR COMPLETAMENTE (líneas ~255-400)
@deprecated(reason="Nomenclatura inconsistente", replacement="execute()")
def execute_renaming(self, renaming_plan: List[Dict], ...) -> RenameResult:
    # ... todo el método
```

#### Cambio 1.3: Worker Update

**Archivo:** `ui/workers.py`  
**Línea:** ~316

**Estado actual:**
```python
results: 'RenameResult' = self.renamer.execute_renaming(
    self.renaming_plan,
    create_backup=self.create_backup,
    dry_run=self.dry_run,
    progress_callback=progress_callback
)
```

**Estado deseado:**
```python
results: 'RenameResult' = self.renamer.execute(
    self.renaming_plan,
    create_backup=self.create_backup,
    dry_run=self.dry_run,
    progress_callback=progress_callback
)
```

---

### 2. file_organizer_service.py

#### Cambio 2.1: Método `analyze()`

**Ubicación actual:** Líneas ~67-78 (método actual es alias)

**Estado deseado:**
```python
def analyze(
    self, 
    root_directory: Path, 
    organization_type: OrganizationType = OrganizationType.TO_ROOT, 
    progress_callback: Optional[ProgressCallback] = None
) -> OrganizationAnalysisResult:
    """
    Analiza la estructura de directorios para organización.

    Args:
        root_directory: Directorio raíz a analizar
        organization_type: Tipo de organización a realizar
        progress_callback: Función opcional (current, total, message) para reportar progreso

    Returns:
        OrganizationAnalysisResult con los archivos a organizar y el plan de movimientos
    """
    # COPIAR TODA LA LÓGICA de analyze_directory_structure() AQUÍ (líneas ~120-320)
    self.logger.info(f"Analizando estructura de directorios para organización ({organization_type.value}): {root_directory}")
    
    # ... [resto de la lógica]
    
    return OrganizationAnalysisResult(
        success=True,
        total_files=total_files_to_move,
        root_directory=str(root_directory),
        organization_type=organization_type.value,
        subdirectories=subdirectories,
        root_files=root_files,
        total_files_to_move=total_files_to_move,
        total_size_to_move=total_size_to_move,
        potential_conflicts=potential_conflicts,
        files_by_type=dict(files_by_type),
        move_plan=move_plan,
        folders_to_create=folders_to_create
    )
```

**Método a eliminar:**
```python
# ELIMINAR (líneas ~120-320)
@deprecated(reason="Nomenclatura inconsistente", replacement="analyze()")
def analyze_directory_structure(...):
```

#### Cambio 2.2: Método `execute()`

**Estado deseado:**
```python
def execute(
    self, 
    move_plan: List[FileMove], 
    create_backup: bool = True, 
    dry_run: bool = False, 
    progress_callback: Optional[ProgressCallback] = None
) -> OrganizationResult:
    """
    Ejecuta la organización de archivos.

    Args:
        move_plan: Lista de FileMove con las operaciones a realizar
        create_backup: Si crear backup antes de mover archivos
        dry_run: Si ejecutar en modo simulación (sin cambios reales)
        progress_callback: Función opcional (current, total, message) para reportar progreso

    Returns:
        OrganizationResult con el resultado de la operación
    """
    # COPIAR TODA LA LÓGICA de execute_organization() AQUÍ
    # ... [lógica completa del método]
```

**Método a eliminar:**
```python
# ELIMINAR
@deprecated(reason="Nomenclatura inconsistente", replacement="execute()")
def execute_organization(...):
```

#### Cambio 2.3: Worker Update

**Archivo:** `ui/workers.py`  
**Línea:** ~405

```python
# Cambiar:
results: 'OrganizationResult' = self.organizer.execute_organization(...)

# Por:
results: 'OrganizationResult' = self.organizer.execute(...)
```

---

### 3. heic_remover_service.py

#### Cambio 3.1: Método `analyze()`

**Ubicación actual:** Líneas ~115-130 (método actual es alias)

**Estado deseado:**
```python
def analyze(
    self, 
    directory: Path, 
    recursive: bool = True, 
    progress_callback: Optional[ProgressCallback] = None
) -> HeicAnalysisResult:
    """
    Analiza duplicados HEIC/JPG en un directorio.

    Args:
        directory: Directorio a analizar
        recursive: Si buscar recursivamente en subdirectorios
        progress_callback: Función opcional (current, total, message) para reportar progreso

    Returns:
        HeicAnalysisResult con los pares duplicados encontrados
    """
    # COPIAR TODA LA LÓGICA de analyze_heic_duplicates() AQUÍ (líneas ~150-315)
    self.logger.info(f"Analizando duplicados HEIC/JPG en: {directory}")
    
    # ... [resto de lógica]
    
    return HeicAnalysisResult(
        total_files=results['total_heic_files'] + results['total_jpg_files'],
        duplicate_pairs=duplicate_pairs,
        total_pairs=len(duplicate_pairs),
        heic_files=results['total_heic_files'],
        jpg_files=results['total_jpg_files'],
        total_size=self.stats['total_heic_size'] + self.stats['total_jpg_size'],
        potential_savings_keep_jpg=results['potential_savings_keep_jpg'],
        potential_savings_keep_heic=results['potential_savings_keep_heic'],
        orphan_heic=results.get('orphan_heic', []),
        orphan_jpg=results.get('orphan_jpg', []),
        compression_stats=results.get('compression_stats', {}),
        by_directory=results.get('by_directory', {})
    )
```

**Método a eliminar:**
```python
# ELIMINAR (líneas ~150-315)
@deprecated(reason="Nomenclatura inconsistente", replacement="analyze()")
def analyze_heic_duplicates(...):
```

#### Cambio 3.2: Método `execute()`

**Estado deseado:**
```python
def execute(
    self, 
    duplicate_pairs: List[DuplicatePair], 
    keep_format: str = 'jpg', 
    create_backup: bool = True, 
    dry_run: bool = False,
    progress_callback: Optional[ProgressCallback] = None
) -> HeicDeletionResult:
    """
    Ejecuta la eliminación de archivos HEIC duplicados.

    Args:
        duplicate_pairs: Lista de pares duplicados a procesar
        keep_format: 'jpg' o 'heic' - formato a mantener
        create_backup: Si crear backup antes de eliminar
        dry_run: Si solo simular sin eliminar archivos reales
        progress_callback: Callback para reportar progreso

    Returns:
        HeicDeletionResult con el resultado de la operación
    """
    # COPIAR TODA LA LÓGICA de execute_removal() AQUÍ (líneas ~330-485)
    if not duplicate_pairs:
        return HeicDeletionResult(
            success=True,
            files_deleted=0,
            space_freed=0,
            message='No hay archivos duplicados para eliminar',
            format_kept=keep_format,
            dry_run=dry_run
        )

    # Usar _log_section_header() en lugar de logging manual
    mode = "SIMULACIÓN" if dry_run else ""
    self._log_section_header("ELIMINACIÓN DE DUPLICADOS HEIC/JPG", mode=mode)
    self.logger.info(f"*** Pares a procesar: {len(duplicate_pairs)}")
    self.logger.info(f"*** Formato a conservar: {keep_format.upper()}")

    # ... [resto de lógica]
    
    return results
```

**Método a eliminar:**
```python
# ELIMINAR (líneas ~330-485)
@deprecated(reason="Nomenclatura inconsistente", replacement="execute()")
def execute_removal(...):
```

#### Cambio 3.3: Workers Update

**Archivo:** `ui/workers.py`  
**Líneas:** ~460, ~726

```python
# Línea ~460: Cambiar
results: 'HeicDeletionResult' = self.remover.execute_removal(...)
# Por:
results: 'HeicDeletionResult' = self.remover.execute(...)

# Línea ~726: Cambiar
result = detector.analyze_heic_duplicates(self.workspace_path, progress_callback=None)
# Por:
result = detector.analyze(self.workspace_path, progress_callback=None)
```

---

### 4. exact_copies_detector.py

#### Cambio 4.1: Método `analyze()`

**Ubicación actual:** Líneas ~30-40 (método actual es alias)

**Estado deseado:**
```python
def analyze(
    self,
    directory: Path,
    progress_callback: Optional[ProgressCallback] = None
) -> DuplicateAnalysisResult:
    """
    Analiza directorio buscando duplicados exactos (SHA256).
    
    Args:
        directory: Directorio a analizar
        progress_callback: Callback de progreso
        
    Returns:
        DuplicateAnalysisResult con grupos de duplicados exactos
    """
    # COPIAR TODA LA LÓGICA de analyze_exact_duplicates() AQUÍ (líneas ~50-160)
    self._log_section_header("INICIANDO ANÁLISIS DE DUPLICADOS EXACTOS (SHA256)")
    
    # ... [resto de lógica]
    
    return DuplicateAnalysisResult(
        success=True,
        mode='exact',
        groups=groups,
        total_files=total_files,
        total_groups=total_groups,
        total_duplicates=total_duplicates,
        space_wasted=space_wasted
    )
```

**Método a eliminar:**
```python
# ELIMINAR (líneas ~50-160)
@deprecated(reason="Nomenclatura inconsistente", replacement="analyze()")
def analyze_exact_duplicates(...):
```

#### Cambio 4.2: Workers Update

**Archivo:** `ui/workers.py`  
**Líneas:** ~511, ~729

```python
# Línea ~511: Cambiar
results = self.detector.analyze_exact_duplicates(self.workspace_path, progress_callback=progress_callback)
# Por:
results = self.detector.analyze(self.workspace_path, progress_callback=progress_callback)

# Línea ~729: Cambiar
result = detector.analyze_exact_duplicates(self.workspace_path, progress_callback=None)
# Por:
result = detector.analyze(self.workspace_path, progress_callback=None)
```

---

### 5. base_detector_service.py

#### Cambio 5.1: Método `execute()`

**Ubicación actual:** Líneas ~65-85 (método actual es alias)

**Estado deseado:**
```python
def execute(
    self,
    groups: List[DuplicateGroup],
    keep_strategy: str = 'oldest',
    create_backup: bool = True,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> DuplicateDeletionResult:
    """
    Ejecuta la eliminación de duplicados.

    Args:
        groups: Lista de grupos de duplicados
        keep_strategy: Estrategia para seleccionar archivo a mantener
            ('oldest', 'newest', 'largest', 'smallest', 'manual')
        create_backup: Si crear backup antes de eliminar
        dry_run: Si solo simular sin eliminar archivos reales
        progress_callback: Callback para reportar progreso

    Returns:
        DuplicateDeletionResult con estadísticas de la operación
    """
    # COPIAR TODA LA LÓGICA de execute_deletion() AQUÍ (líneas ~90-250)
    if not groups:
        return DuplicateDeletionResult(
            success=True,
            files_deleted=0,
            space_freed=0,
            keep_strategy=keep_strategy,
            dry_run=dry_run,
            message="No hay duplicados para eliminar"
        )

    # ... [resto de lógica]
    
    return results
```

**Método a eliminar:**
```python
# ELIMINAR (líneas ~90-250)
@deprecated(reason="Nomenclatura inconsistente", replacement="execute()")
def execute_deletion(...):
```

#### Cambio 5.2: Worker Update

**Archivo:** `ui/workers.py`  
**Línea:** ~564

```python
# Cambiar:
results: 'DuplicateDeletionResult' = self.detector.execute_deletion(...)
# Por:
results: 'DuplicateDeletionResult' = self.detector.execute(...)
```

---

## 📋 Checklist de Verificación Post-Cambios

Después de modificar cada servicio, verificar:

### Compilación
```bash
python -m compileall services/<nombre_servicio>.py
```

### Imports
```python
python -c "from services.<nombre_servicio> import <NombreClase>; print('✓ Import OK')"
```

### Métodos Disponibles
```python
python -c "
from services.<nombre_servicio> import <NombreClase>
service = <NombreClase>()
assert hasattr(service, 'analyze'), 'Falta analyze()'
assert hasattr(service, 'execute'), 'Falta execute()'
assert not hasattr(service, 'analyze_xxx'), 'Deprecated aún existe'
print('✓ Métodos correctos')
"
```

### Signatures
```python
python -c "
import inspect
from services.<nombre_servicio> import <NombreClase>
service = <NombreClase>()
sig = inspect.signature(service.analyze)
print(f'analyze signature: {sig}')
sig = inspect.signature(service.execute)
print(f'execute signature: {sig}')
"
```

### Tests Unitarios
```bash
pytest tests/unit/services/test_<nombre_servicio>.py -v
```

---

## 🎯 Orden de Implementación Recomendado

Procesar en este orden para minimizar interdependencias:

1. **base_detector_service.py** (base class)
   - Afecta: exact_copies_detector, similar_files_detector
   
2. **exact_copies_detector.py**
   - Depende: base_detector_service
   
3. **file_renamer_service.py**
   - Independiente
   
4. **file_organizer_service.py**
   - Independiente
   
5. **heic_remover_service.py**
   - Independiente

---

## 🔍 Patrones de Búsqueda

Para verificar completitud:

```bash
# No deben quedar decoradores @deprecated
grep -rn "@deprecated" services/

# No deben quedar llamadas a métodos antiguos en UI
grep -rn "analyze_directory\|execute_renaming" ui/
grep -rn "analyze_directory_structure\|execute_organization" ui/
grep -rn "analyze_heic_duplicates\|execute_removal" ui/
grep -rn "analyze_exact_duplicates" ui/
grep -rn "execute_deletion" ui/

# Verificar que existen los métodos nuevos
grep -rn "def analyze(" services/
grep -rn "def execute(" services/
```

---

## 📝 Template de Commit Message

```
refactor(services): remove deprecated methods in <ServiceName>

Migrated <ServiceName> to standardized analyze()/execute() pattern.

Changes:
- Merged analyze_xxx() → analyze()
- Merged execute_xxx() → execute()
- Updated workers to use new methods
- Removed @deprecated decorators

BREAKING CHANGE: Old method names (analyze_xxx, execute_xxx) no longer exist.

Affected:
- services/<service_file>.py
- ui/workers.py (lines X, Y)

Tests: All passing
Manual testing: ✓ Tool works correctly in UI
```

---

**Última actualización:** 12 Nov 2025  
**Ver también:** 
- `REFACTOR_ANALYSIS_2025.md` (análisis completo)
- `REFACTOR_COMMANDS.md` (comandos bash)
- `REFACTOR_SUMMARY.md` (resumen ejecutivo)
