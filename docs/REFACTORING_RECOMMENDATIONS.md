# Recomendaciones de Refactorización - Pixaro Lab

**Fecha:** 7 de noviembre de 2025  
**Objetivo:** Lograr 100% desacoplamiento UI/lógica y estandarización de tipos de retorno

---

## 1. ANÁLISIS DE ESTADO ACTUAL

### 1.1 Arquitectura General ✅
La arquitectura de 3 capas está **bien implementada**:
- **Services:** Lógica de negocio sin dependencias de PyQt6
- **Workers:** Capa de threading Qt para operaciones en background
- **UI Stages:** Sistema de estados para flujo de la aplicación

### 1.2 Problemas Identificados ❌

#### **Problema #1: Inconsistencia en Tipos de Retorno**

**Servicios que retornan dataclasses (✅ correcto):**
```python
# FileRenamer.analyze_directory() -> RenameAnalysisResult
# FileRenamer.execute_renaming() -> RenameResult  
# FileOrganizer.analyze_directory_structure() -> OrganizationAnalysisResult
# FileOrganizer.execute_organization() -> OrganizationResult
# LivePhotoCleaner.execute_cleanup() -> LivePhotoCleanupResult
# DuplicateDetector.execute_deletion() -> DuplicateDeletionResult
```

**Servicios que retornan Dict (❌ inconsistente):**
```python
# HEICDuplicateRemover.analyze_heic_duplicates() -> Dict
# DuplicateDetector.analyze_exact_duplicates() -> Dict
# DuplicateDetector.analyze_similar_duplicates() -> Dict
# AnalysisOrchestrator.analyze_live_photos() -> Dict (wrapper sobre detector)
```

**Impacto:**
- Código frágil: acceso con strings `result['total_duplicates']` vs `result.total_duplicates`
- Sin validación de tipos en tiempo de compilación
- Dificulta refactorizaciones (renombrar keys rompe silenciosamente el código)
- No hay autocomplete en IDEs

#### **Problema #2: Conversión Dict ↔ Dataclass en múltiples capas**

**Ejemplo en `LivePhotoCleaner.execute_cleanup()`:**
```python
def execute_cleanup(self, cleanup_analysis: Union[LivePhotoCleanupAnalysisResult, Dict], ...):
    # Conversión manual para compatibilidad con código antiguo
    if isinstance(cleanup_analysis, dict):
        cleanup_analysis = LivePhotoCleanupAnalysisResult(
            total_files=cleanup_analysis.get('total_files', 0),
            # ... 7 líneas más de conversión manual
        )
```

**Problemas:**
- Duplicación de código de conversión
- Fácil olvidar actualizar conversiones al agregar campos
- Dificulta mantenimiento

#### **Problema #3: `FullAnalysisResult.to_dict()` rompe encapsulación**

**En `services/analysis_orchestrator.py`:**
```python
@dataclass
class FullAnalysisResult:
    # ... campos ...
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para compatibilidad con código existente"""
        return {
            'stats': {...},
            'renaming': self.renaming,  # ¿dataclass o dict?
            'live_photos': self.live_photos,  # Es Dict
            'heic': self.heic,  # Es Dict
            # ...
        }
```

**Problema:** Se supone que es una capa de adaptación, pero mezcla dataclasses y dicts internamente.

#### **Problema #4: Workers emiten `object` genérico**

**En `ui/workers.py`:**
```python
class BaseWorker(QThread):
    finished = pyqtSignal(object)  # Changed from dict to object to support dataclasses
```

**Problema:** Pérdida de type safety. La UI no sabe qué tipo esperar.

---

## 2. PLAN DE REFACTORIZACIÓN

### 2.1 FASE 1: Estandarizar Todos los Resultados como Dataclasses 🎯

**Prioridad:** ALTA  
**Esfuerzo:** Medio (2-3 horas)  
**Impacto:** Alto

#### Acciones:

**1. Completar `services/result_types.py`:**

Agregar dataclasses faltantes:

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

# Ya existe: HeicAnalysisResult (pero se usa Dict en el servicio)
# Asegurar que TODOS los servicios usen sus dataclasses

@dataclass
class DuplicateGroup:
    """Grupo de archivos duplicados (exactos o similares)"""
    files: List[Path] = field(default_factory=list)
    file_sizes: List[int] = field(default_factory=list)
    total_size: int = 0
    hash_value: Optional[str] = None  # Para exactos
    similarity_score: Optional[float] = None  # Para similares
    
    @property
    def count(self) -> int:
        return len(self.files)
    
    @property
    def duplicates_count(self) -> int:
        """Archivos duplicados (excluye el original)"""
        return max(0, len(self.files) - 1)


@dataclass  
class ExactDuplicatesAnalysisResult(DuplicateAnalysisResult):
    """Resultado específico de duplicados exactos - ya existe en result_types.py"""
    # mode='exact' es automático
    pass


@dataclass
class SimilarDuplicatesAnalysisResult(DuplicateAnalysisResult):
    """Resultado específico de duplicados similares - ya existe en result_types.py"""
    # mode='perceptual' es automático
    pass


# NUEVO: Análisis de Live Photos (detector retorna lista, necesita wrapper)
@dataclass
class LivePhotoDetectionResult(AnalysisResult):
    """Resultado de detección de Live Photos"""
    groups: List  # List[LivePhotoGroup] pero importar LivePhotoGroup crea dep circular
    total_groups: int = 0
    total_images: int = 0
    total_videos: int = 0
    total_space: int = 0
    space_to_free: int = 0  # Video space
    
    def __post_init__(self):
        super().__post_init__()
        self.total_groups = len(self.groups)
        if self.groups:
            self.total_space = sum(g.total_size for g in self.groups)
            self.space_to_free = sum(g.video_size for g in self.groups)
```

**2. Refactorizar servicios para usar dataclasses:**

```python
# services/heic_remover.py
def analyze_heic_duplicates(self, directory: Path, ...) -> HeicAnalysisResult:
    # Cambiar Dict por HeicAnalysisResult
    return HeicAnalysisResult(
        total_files=total_files,
        duplicate_pairs=duplicate_pairs,
        total_pairs=len(duplicate_pairs),
        # ... etc
    )

# services/duplicate_detector.py  
def analyze_exact_duplicates(self, directory: Path, ...) -> DuplicateAnalysisResult:
    # Cambiar Dict por DuplicateAnalysisResult
    return DuplicateAnalysisResult(
        mode='exact',
        groups=groups,
        total_groups=len(groups),
        # ... etc
    )

def analyze_similar_duplicates(self, directory: Path, ...) -> DuplicateAnalysisResult:
    return DuplicateAnalysisResult(
        mode='perceptual',
        groups=groups,
        sensitivity=sensitivity,
        # ... etc
    )
```

**3. Actualizar `AnalysisOrchestrator`:**

```python
@dataclass
class FullAnalysisResult:
    """Resultado completo de análisis - TODO TIPADO"""
    directory: Path
    scan: DirectoryScanResult
    phase_timings: Dict[str, PhaseTimingInfo] = field(default_factory=dict)
    
    # Todos dataclasses tipados
    renaming: Optional[RenameAnalysisResult] = None
    live_photos: Optional[LivePhotoDetectionResult] = None
    organization: Optional[OrganizationAnalysisResult] = None
    heic: Optional[HeicAnalysisResult] = None
    duplicates: Optional[DuplicateAnalysisResult] = None
    total_duration: float = 0.0
    
    # ELIMINAR to_dict() - forzar uso de dataclasses en UI
```

**4. Eliminar conversiones Union[Dataclass, Dict]:**

```python
# ANTES (LivePhotoCleaner.execute_cleanup):
def execute_cleanup(self, cleanup_analysis: Union[LivePhotoCleanupAnalysisResult, Dict], ...):
    if isinstance(cleanup_analysis, dict):
        cleanup_analysis = LivePhotoCleanupAnalysisResult(...)  # Conversión manual
    # ...

# DESPUÉS:
def execute_cleanup(self, cleanup_analysis: LivePhotoCleanupAnalysisResult, ...):
    # Sin conversión - SOLO acepta dataclass
    # ...
```

**5. Actualizar UI para usar dataclasses:**

```python
# ui/stages/stage_3_window.py
def __init__(self, main_window, selected_folder: str, analysis_results: FullAnalysisResult):
    # Cambiar Dict por FullAnalysisResult tipado
    self.analysis_results = analysis_results
    
def _populate_summary_card(self):
    # ANTES: self.analysis_results['stats']['total']
    # DESPUÉS: self.analysis_results.scan.total_files
    self.summary_card.set_stats(
        total_files=self.analysis_results.scan.total_files,
        images=self.analysis_results.scan.image_count,
        # ...
    )
```

---

### 2.2 FASE 2: Eliminar Dependencias Residuales PyQt6 en `utils/`

**Prioridad:** MEDIA  
**Esfuerzo:** Bajo (30 min)  
**Estado:** ✅ YA IMPLEMENTADO

Ya está correcto gracias a `utils/storage.py` con abstracción de backends.

---

### 2.3 FASE 3: Type Hints Estrictos en Workers

**Prioridad:** MEDIA  
**Esfuerzo:** Bajo (1 hora)

**Problema actual:**
```python
class BaseWorker(QThread):
    finished = pyqtSignal(object)  # Demasiado genérico
```

**Solución:**

Crear workers específicos con tipos estrictos:

```python
# ui/workers.py

# Worker base genérico (mantener para extensibilidad)
class BaseWorker(QThread):
    progress_update = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)  # Genérico
    error = pyqtSignal(str)
    # ...


# Worker tipado para análisis
class AnalysisWorker(BaseWorker):
    finished = pyqtSignal(FullAnalysisResult)  # TIPADO ESTRICTO
    partial_results = pyqtSignal(object)  # Mantener flexible para diferentes resultados parciales
    
    def run(self):
        # ...
        result: FullAnalysisResult = orchestrator.run_full_analysis(...)
        self.finished.emit(result)


# Worker tipado para renombrado
class RenamingWorker(BaseWorker):
    finished = pyqtSignal(RenameResult)  # TIPADO ESTRICTO
    
    def run(self):
        result: RenameResult = self.renamer.execute_renaming(...)
        self.finished.emit(result)


# Worker tipado para organización
class OrganizationWorker(BaseWorker):
    finished = pyqtSignal(OrganizationResult)  # TIPADO ESTRICTO
    # ...
```

**Beneficios:**
- Autocomplete en slots: `def on_finished(result: FullAnalysisResult)`
- Errores de tipo en tiempo de desarrollo
- Refactorizaciones seguras

---

### 2.4 FASE 4: Separar Lógica de Presentación en Diálogos

**Prioridad:** BAJA  
**Esfuerzo:** Alto (4-6 horas)  
**Beneficio:** Preparación para multi-plataforma

**Problema actual:**

Los diálogos (`ui/dialogs/`) mezclan lógica de presentación con lógica de negocio:

```python
# organization_dialog.py
def _populate_tree_widget(self):
    # Lógica de transformación de datos mezclada con lógica de Qt
    for move in moves:
        if self.current_mode == OrganizationMode.TO_ROOT:
            # ... cálculos de agrupación ...
        # ... QTreeWidgetItem creation ...
```

**Solución:**

Introducir **View Models** (MVVM pattern):

```python
# services/view_models.py (nueva capa)

@dataclass
class OrganizationTreeNode:
    """Nodo genérico del árbol de organización - sin Qt"""
    label: str
    children: List['OrganizationTreeNode'] = field(default_factory=list)
    file_count: int = 0
    total_size: int = 0
    is_conflict: bool = False
    metadata: Dict = field(default_factory=dict)  # Datos adicionales


class OrganizationViewModel:
    """Convierte OrganizationAnalysisResult en estructura de árbol sin Qt"""
    
    @staticmethod
    def build_tree(result: OrganizationAnalysisResult, mode: OrganizationMode) -> List[OrganizationTreeNode]:
        """Genera árbol de nodos según modo de visualización"""
        if mode == OrganizationMode.TO_ROOT:
            return OrganizationViewModel._build_to_root_tree(result)
        elif mode == OrganizationMode.BY_MONTH:
            return OrganizationViewModel._build_by_month_tree(result)
        # ...
        
    @staticmethod
    def _build_to_root_tree(result: OrganizationAnalysisResult) -> List[OrganizationTreeNode]:
        """Lógica PURA de agrupación - sin Qt"""
        nodes = []
        for subdir_name, data in result.subdirectories.items():
            node = OrganizationTreeNode(
                label=subdir_name,
                file_count=data['file_count'],
                total_size=data['total_size']
            )
            # Agregar hijos...
            nodes.append(node)
        return nodes
```

```python
# ui/dialogs/organization_dialog.py

def _populate_tree_widget(self):
    """Solo lógica de UI - delega transformación a ViewModel"""
    # 1. Obtener estructura de árbol del ViewModel
    tree_nodes = OrganizationViewModel.build_tree(self.result, self.current_mode)
    
    # 2. Renderizar en QTreeWidget (lógica Qt pura)
    self.tree_widget.clear()
    for node in tree_nodes:
        self._add_tree_node_to_widget(node)
        
def _add_tree_node_to_widget(self, node: OrganizationTreeNode, parent_item=None):
    """Convierte nodo genérico a QTreeWidgetItem"""
    item = QTreeWidgetItem()
    item.setText(0, node.label)
    item.setText(1, format_file_count(node.file_count))
    # ...
    if parent_item:
        parent_item.addChild(item)
    else:
        self.tree_widget.addTopLevelItem(item)
    
    for child in node.children:
        self._add_tree_node_to_widget(child, item)
```

**Beneficios:**
- `OrganizationViewModel` puede usarse en CLI, tests, otras UIs (Kivy/Flutter)
- Tests unitarios sin PyQt6
- Lógica de presentación reutilizable

---

## 3. MEJORAS ADICIONALES

### 3.1 Sistema de Eventos/Callbacks más Robusto

**Problema actual:**
```python
# Callbacks con tuplas (current, total, message) -> bool
def progress_callback(current: int, total: int, message: str) -> bool:
    # Retorna False para cancelar
```

**Mejora propuesta:**

```python
# utils/callback_utils.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable

class ProgressPhase(Enum):
    """Fases del progreso"""
    SCANNING = "scanning"
    ANALYZING = "analyzing"
    PROCESSING = "processing"
    FINALIZING = "finalizing"


@dataclass
class ProgressInfo:
    """Información estructurada de progreso"""
    current: int
    total: int
    message: str
    phase: ProgressPhase
    percentage: float = 0.0
    
    def __post_init__(self):
        if self.total > 0:
            self.percentage = (self.current / self.total) * 100


# Tipo de callback mejorado
ProgressCallback = Callable[[ProgressInfo], bool]


# Adaptador para código legacy
def adapt_legacy_callback(legacy_callback: Callable[[int, int, str], bool]) -> ProgressCallback:
    """Convierte callback antiguo (current, total, msg) a nuevo formato"""
    def wrapper(info: ProgressInfo) -> bool:
        return legacy_callback(info.current, info.total, info.message)
    return wrapper
```

**Uso:**
```python
# En servicios
def analyze_directory(self, directory: Path, progress_callback: Optional[ProgressCallback] = None):
    for i, file in enumerate(files):
        if progress_callback:
            info = ProgressInfo(
                current=i,
                total=len(files),
                message=f"Procesando {file.name}",
                phase=ProgressPhase.ANALYZING
            )
            if not progress_callback(info):
                break  # Cancelado
```

---

### 3.2 Testing sin UI

**Crear fixtures de dataclasses para tests:**

```python
# tests/fixtures/results.py

from services.result_types import *

def sample_rename_analysis_result() -> RenameAnalysisResult:
    """Fixture de resultado de análisis de renombrado"""
    return RenameAnalysisResult(
        total_files=100,
        already_renamed=50,
        need_renaming=40,
        cannot_process=10,
        conflicts=2,
        renaming_plan=[...],
        # ...
    )


# tests/test_organization_viewmodel.py
def test_organization_viewmodel_to_root():
    """Test de ViewModel sin PyQt6"""
    result = sample_organization_analysis_result()
    nodes = OrganizationViewModel.build_tree(result, OrganizationMode.TO_ROOT)
    
    assert len(nodes) > 0
    assert nodes[0].label == "Subdirectory1"
    assert nodes[0].file_count == 10
```

---

### 3.3 Configuración Centralizada de Comportamiento

**Problema:** Config es estático, difícil testear diferentes configuraciones.

**Mejora:**

```python
# config.py

from dataclasses import dataclass, field
from typing import List

@dataclass
class AppConfig:
    """Configuración de aplicación (instanciable para tests)"""
    app_name: str = "Pixaro Lab"
    min_phase_duration: float = 2.0
    final_delay_stage3: float = 0.5
    supported_image_extensions: List[str] = field(default_factory=lambda: ['.jpg', '.jpeg', '.png', ...])
    # ...
    
    def is_supported_file(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in self.supported_image_extensions or ext in self.supported_video_extensions


# Singleton global (para código existente)
Config = AppConfig()

# En tests:
def test_with_custom_config():
    test_config = AppConfig(min_phase_duration=0.1)  # Configuración rápida para tests
    # Usar test_config...
```

---

## 4. PRIORIZACIÓN Y ROADMAP

### Sprint 1 (Alta Prioridad - 3-4 horas)
- ✅ **FASE 1.1:** Crear dataclasses faltantes en `result_types.py`
- ✅ **FASE 1.2:** Refactorizar `HEICDuplicateRemover.analyze_heic_duplicates()` → `HeicAnalysisResult`
- ✅ **FASE 1.3:** Refactorizar `DuplicateDetector.analyze_*()` → `DuplicateAnalysisResult`
- ✅ **FASE 1.4:** Actualizar `AnalysisOrchestrator` para usar dataclasses tipados
- ✅ **FASE 1.5:** Eliminar conversiones `Union[Dataclass, Dict]` en `LivePhotoCleaner`

### Sprint 2 (Media Prioridad - 2 horas)
- ✅ **FASE 3:** Type hints estrictos en Workers
- ✅ **FASE 1.6:** Actualizar UI para acceder a dataclasses directamente
  * ✅ `stage_3_window.py` - Acceso con atributos en lugar de `.get()`
  * ✅ `live_photos_dialog.py` - Migrado a usar `LivePhotoDetectionResult` dataclass
  * ✅ `live_photo_detector.py` - `LivePhotoGroup` ahora es dataclass

### Sprint 3 (Baja Prioridad - Preparación futura)
- 🔮 **FASE 4:** View Models para separación UI/lógica
- 🔮 **Mejora 3.1:** Sistema de callbacks estructurado con `ProgressInfo`
- 🔮 **Mejora 3.2:** Tests sin UI usando fixtures de dataclasses

---

## 5. CHECKLIST DE VALIDACIÓN

Después de implementar FASE 1:

- [ ] `grep -r "-> Dict" services/` → Solo debe aparecer en métodos auxiliares internos
- [ ] `grep -r "Union\[.*Result, Dict\]" services/` → No debe haber ninguno
- [ ] Todos los métodos `analyze_*()` retornan subclases de `AnalysisResult`
- [ ] Todos los métodos `execute_*()` retornan subclases de `OperationResult`
- [ ] `FullAnalysisResult` tiene todos los campos tipados (no `Optional[Any]`)
- [ ] No hay conversiones manuales dict → dataclass en servicios

---

## 6. RESUMEN EJECUTIVO

**Estado Actual:** 60% desacoplado  
**Estado Objetivo:** 100% desacoplado + Type-safe

**Cambios Clave:**
1. **Estandarizar resultados** → Todos dataclasses, eliminar dicts
2. **Type hints estrictos** → Workers y signals tipados
3. **View Models** → Preparar para multi-plataforma (futuro)

**Beneficios Inmediatos:**
- ✅ Autocomplete en toda la codebase
- ✅ Errores de tipo en desarrollo (no en producción)
- ✅ Refactorizaciones seguras
- ✅ Tests más fáciles (sin PyQt6)

**Esfuerzo Total:** ~6-8 horas (distribuido en 3 sprints)

---

**Nota:** Este documento es una guía viva. Actualizar después de cada sprint completado.
