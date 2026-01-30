# Plan de Mejoras para InnerPix Lab 2026

> **Documento de análisis técnico y plan de mejoras**  
> Creado: 29 Enero 2026  
> Versión actual: 0.8

---

## Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Análisis del Estado Actual](#análisis-del-estado-actual)
3. [Mejoras de Arquitectura y Código](#mejoras-de-arquitectura-y-código)
4. [Nuevas Funcionalidades Propuestas](#nuevas-funcionalidades-propuestas)
5. [Mejoras de UX/UI](#mejoras-de-uxui)
6. [Optimización de Rendimiento](#optimización-de-rendimiento)
7. [Testing y Calidad](#testing-y-calidad)
8. [Priorización y Roadmap](#priorización-y-roadmap)

---

## Resumen Ejecutivo

InnerPix Lab es una aplicación sólida con una arquitectura bien diseñada que sigue patrones claros (separación UI/lógica, servicios singleton, dataclasses para resultados). Sin embargo, hay oportunidades significativas de mejora en varias áreas:

**Fortalezas Identificadas:**
- ✅ Arquitectura limpia con servicios PyQt6-free (facilita migración futura a móvil)
- ✅ Sistema de caché centralizado (FileInfoRepositoryCache) preparado para SQLite
- ✅ Patrón consistente de análisis → plan → ejecución con backup y dry-run
- ✅ Threading bien gestionado con workers dedicados
- ✅ Sistema de logging robusto con dual-log y thread-safety
- ✅ 590+ tests automatizados

**Áreas de Mejora Prioritarias:**
- 🔧 Código heredado en servicios de duplicados necesita refactorización
- 🔧 Falta persistencia de caché entre sesiones
- 🔧 Videos no se procesan en detección de similares
- 🔧 UX inconsistente en mensajes post-operación
- 🔧 Sin sistema de internacionalización (i18n)

---

## Análisis del Estado Actual

### Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                         UI Layer (PyQt6)                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐ │
│  │ Stage 1 │  │ Stage 2 │  │ Stage 3 │  │ Dialogs + Workers   │ │
│  └────┬────┘  └────┬────┘  └────┬────┘  └──────────┬──────────┘ │
└───────┼────────────┼────────────┼───────────────────┼───────────┘
        │            │            │                   │
        ▼            ▼            ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Services Layer (PyQt6-free)                  │
│  ┌──────────────┐  ┌─────────────────────────────────────────┐  │
│  │ BaseService  │◄─┤ Duplicates, HEIC, LivePhotos, Organizer │  │
│  └──────────────┘  │ Renamer, ZeroByte, VisualIdentical      │  │
│                    └─────────────────────────────────────────┘  │
│         ▲                           ▲                           │
│         │                           │                           │
│  ┌──────┴─────────────┐  ┌─────────┴─────────────────────────┐ │
│  │ FileMetadataRepo   │  │ InitialScanner (6 phases)         │ │
│  │ (Singleton Cache)  │  │ FILESYSTEM→HASH→EXIF→BEST_DATE    │ │
│  └────────────────────┘  └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Servicios Actuales y Capacidades

| Servicio | Estado | Funcionalidad | Limitaciones |
|----------|--------|---------------|--------------|
| `DuplicatesExactService` | ✅ Estable | SHA256 100% idénticos | Ninguna crítica |
| `VisualIdenticalService` | ✅ Estable | Perceptual hash 100% | Solo imágenes |
| `DuplicatesSimilarService` | ⚠️ Mejorable | Clustering BK-Tree optimizado | Solo imágenes, UX mejorable |
| `HeicService` | ✅ Estable | Pares HEIC/JPG | Ninguna crítica |
| `LivePhotoService` | ✅ Estable | iPhone Live Photos | Ninguna crítica |
| `FileOrganizerService` | ✅ Estable | Múltiples estrategias | UI pagination mejorable |
| `FileRenamerService` | ✅ Estable | Formato estándar con fechas | Ninguna crítica |
| `ZeroByteService` | ✅ Estable | Archivos vacíos | Simple, funciona bien |

---

## Mejoras de Arquitectura y Código

### 1. ALTA PRIORIDAD: Refactorización de Servicios de Duplicados

**Problema:** Los servicios `DuplicatesExactService` y `DuplicatesSimilarService` mantienen código heredado de cuando estaban fusionados, con herencia innecesaria de `DuplicatesBaseService`.

**Solución Propuesta:**

```python
# ANTES: Herencia confusa
class DuplicatesExactService(DuplicatesBaseService):
    # Hereda execute() de base pero no lo necesita igual
    
# DESPUÉS: Composición clara
class DuplicatesExactService(BaseService):
    def __init__(self):
        super().__init__('DuplicatesExactService')
        self._deletion_handler = DuplicateDeletionHandler()  # Composición
    
    def execute(self, analysis_result, ...):
        return self._deletion_handler.delete_with_strategy(...)
```

**Cambios específicos:**
1. Extraer `DuplicateDeletionHandler` como clase utilitaria para lógica de eliminación con estrategia
2. `DuplicatesExactService` hereda directamente de `BaseService`
3. `DuplicatesSimilarService` hereda directamente de `BaseService`
4. `DuplicatesBaseService` se renombra a `DuplicateDeletionHandler` o se elimina

**Impacto:** ~200 líneas de código más limpio, mantenimiento más fácil

---

### 2. ALTA PRIORIDAD: Persistencia de Caché entre Sesiones

**Problema:** El `FileInfoRepositoryCache` tiene métodos `save_to_disk()` y `load_from_disk()` pero no se usan en producción. Cada sesión recalcula todo.

**Solución Propuesta:**

```python
# En config.py - añadir
CACHE_PERSISTENCE_ENABLED = True
CACHE_AUTO_SAVE_INTERVAL_SECONDS = 300  # Cada 5 minutos

# En MainWindow - al seleccionar carpeta
def _on_folder_selected(self, folder_path):
    repo = FileInfoRepositoryCache.get_instance()
    cache_file = self._get_cache_file_for_folder(folder_path)
    
    if cache_file.exists():
        loaded = repo.load_from_disk(cache_file, validate=True)
        if loaded > 0:
            self.logger.info(f"Caché restaurada: {loaded} archivos")
            # Opcionalmente verificar si hay archivos nuevos
            self._check_for_new_files(folder_path, repo)
```

**Beneficios:**
- Tiempo de inicio reducido en ~80% para carpetas ya analizadas
- Mejor UX para usuarios frecuentes
- Base para análisis incremental

**Implementación:**
1. Crear método `_get_cache_file_for_folder(folder)` que genera hash del path
2. Guardar caché automáticamente al completar Stage 2
3. Validar integridad al cargar (verificar que archivos aún existen)
4. Añadir botón "Forzar re-análisis" en Stage 1

---

### 3. MEDIA PRIORIDAD: Migración a SQLite

**Problema:** El repositorio en memoria limita datasets muy grandes y no persiste entre sesiones de forma robusta.

**Estado actual:** La arquitectura está preparada (interfaz `IFileRepository`, métodos `to_dict`/`from_dict` en `FileMetadata`)

**Plan de migración:**

```python
# Phase 1: Implementar SQLiteFileRepository
class SQLiteFileRepository:
    """Backend SQLite para FileInfoRepositoryCache"""
    
    def __init__(self, db_path: Path):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
    
    def _create_tables(self):
        """
        CREATE TABLE files (
            path TEXT PRIMARY KEY,
            fs_size INTEGER,
            fs_ctime REAL,
            fs_mtime REAL,
            sha256 TEXT,
            best_date TEXT,
            best_date_source TEXT,
            exif_json TEXT,
            perceptual_hash TEXT,  -- NUEVO: para similar duplicates
            created_at REAL,
            updated_at REAL
        );
        CREATE INDEX idx_files_sha256 ON files(sha256);
        CREATE INDEX idx_files_size ON files(fs_size);
        """
```

**Beneficios:**
- Soporte para datasets de >500k archivos
- Queries eficientes por hash, tamaño, fecha
- Persistencia robusta con transacciones
- Base para futuras funcionalidades (historial, estadísticas)

---

### 4. MEDIA PRIORIDAD: Sistema de Plugins/Extensiones

**Problema:** Añadir nuevas herramientas requiere modificar múltiples archivos (service, dialog, card, tools_definitions).

**Solución:** Sistema de auto-registro de herramientas

```python
# services/base_service.py
class ToolRegistry:
    """Registro global de herramientas"""
    _tools: Dict[str, 'ToolPlugin'] = {}
    
    @classmethod
    def register(cls, tool: 'ToolPlugin'):
        cls._tools[tool.id] = tool
    
    @classmethod
    def get_all(cls) -> List['ToolPlugin']:
        return list(cls._tools.values())

@dataclass
class ToolPlugin:
    id: str
    definition: ToolDefinition  # De tools_definitions.py
    service_class: Type[BaseService]
    dialog_class: Type[BaseDialog]
    card_class: Type[QWidget]

# Uso en cada servicio
@ToolRegistry.register
class ZeroBytePlugin(ToolPlugin):
    id = 'zero_byte'
    definition = TOOL_ZERO_BYTE
    service_class = ZeroByteService
    dialog_class = ZeroByteDialog
    card_class = ZeroByteCard
```

---

### 5. BAJA PRIORIDAD: Tipado Estricto con Protocols

**Problema:** Algunos servicios aceptan tipos genéricos (`Any`, `dict`) donde deberían usar tipos específicos.

**Solución:** Implementar Protocols para contracts claros

```python
# services/protocols.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class AnalyzableService(Protocol):
    """Contrato para servicios con fase de análisis"""
    def analyze(
        self, 
        progress_callback: Optional[ProgressCallback] = None,
        **kwargs
    ) -> AnalysisResult: ...

@runtime_checkable
class ExecutableService(Protocol):
    """Contrato para servicios con fase de ejecución"""
    def execute(
        self,
        analysis_result: AnalysisResult,
        dry_run: bool = False,
        create_backup: bool = True,
        **kwargs
    ) -> ExecutionResult: ...
```

---

## Nuevas Funcionalidades Propuestas

### ALTA PRIORIDAD

#### 1. Soporte de Videos en Detección de Similares

**Estado actual:** `DuplicatesSimilarService` y `VisualIdenticalService` solo procesan imágenes.

**Implementación:**

```python
# services/video_hash_service.py
class VideoHashService:
    """Calcula hashes perceptuales de videos extrayendo keyframes"""
    
    def calculate_video_hash(self, video_path: Path) -> Optional[str]:
        """
        Extrae keyframes y calcula hash combinado.
        
        Estrategia:
        1. Extraer 5 frames: 0%, 25%, 50%, 75%, 100% de duración
        2. Calcular phash de cada frame
        3. Combinar hashes (XOR o concatenación)
        """
        frames = self._extract_keyframes(video_path, count=5)
        if not frames:
            return None
        
        hashes = [imagehash.phash(frame) for frame in frames]
        combined = self._combine_hashes(hashes)
        return str(combined)
```

**Config:**
```python
# En config.py
PERCEPTUAL_HASH_TARGET = "both"  # "images", "videos", "both"
VIDEO_HASH_KEYFRAME_COUNT = 5
VIDEO_HASH_TIMEOUT_SECONDS = 10
```

---

#### 2. Detección de Capturas de Pantalla

**Descripción:** Identificar screenshots automáticamente para organización/limpieza.

```python
# services/screenshot_service.py
class ScreenshotService(BaseService):
    """Detecta y gestiona capturas de pantalla"""
    
    # Patrones de nombre
    SCREENSHOT_PATTERNS = [
        r'^Screenshot[_\s-]',
        r'^Captura[_\s-]',
        r'^Screen[_\s-]',
        r'^IMG_\d{4}\.(PNG|png)$',  # iOS screenshots
    ]
    
    # Resoluciones típicas de screenshots
    SCREENSHOT_RESOLUTIONS = {
        (1170, 2532),  # iPhone 13/14
        (1284, 2778),  # iPhone 13/14 Pro Max
        (1920, 1080),  # Full HD desktop
        (2560, 1440),  # QHD desktop
    }
    
    def analyze(self, ...):
        """
        Detecta screenshots por:
        1. Patrón de nombre
        2. Resolución típica
        3. Software en EXIF (si disponible)
        """
```

**UI:** Nueva categoría "Limpieza" con tool card.

---

#### 3. Eliminación Selectiva de Metadatos

**Descripción:** Limpiar información sensible (GPS, dispositivo) antes de compartir.

```python
# services/metadata_cleaner_service.py
@dataclass
class MetadataCleanerAnalysisResult(AnalysisResult):
    files_with_gps: List[Path]
    files_with_device_info: List[Path]
    files_with_software_info: List[Path]
    
class MetadataCleanerService(BaseService):
    """Detecta y elimina metadatos sensibles"""
    
    SENSITIVE_TAGS = [
        'GPSLatitude', 'GPSLongitude', 'GPSAltitude',
        'Make', 'Model', 'Software',
        'Artist', 'Copyright', 'ImageDescription',
    ]
    
    def execute(self, analysis_result, tags_to_remove: List[str], ...):
        """Elimina tags especificados usando exiftool"""
        for file_path in analysis_result.files:
            # exiftool -GPSLatitude= -GPSLongitude= file.jpg
            self._remove_tags(file_path, tags_to_remove)
```

---

#### 4. Conversión de Formatos (HEIC → JPG)

**Descripción:** Convertir archivos incompatibles a formatos universales.

```python
# services/format_converter_service.py
class FormatConverterService(BaseService):
    """Conversión entre formatos multimedia"""
    
    CONVERSIONS = {
        'heic_to_jpg': {'from': ['.heic', '.heif'], 'to': '.jpg'},
        'png_to_jpg': {'from': ['.png'], 'to': '.jpg'},
        'mov_to_mp4': {'from': ['.mov'], 'to': '.mp4'},
    }
    
    def analyze(self, conversion_type: str, quality: int = 90, ...):
        """Analiza archivos convertibles y estima tamaño resultante"""
    
    def execute(self, ..., keep_original: bool = True):
        """Convierte archivos y opcionalmente elimina originales"""
```

---

### MEDIA PRIORIDAD

#### 5. Detección de Imágenes Borrosas

```python
# services/blur_detection_service.py
class BlurDetectionService(BaseService):
    """Detecta imágenes borrosas usando operador Laplaciano"""
    
    def _calculate_blur_score(self, image_path: Path) -> float:
        """
        Score basado en varianza del Laplaciano.
        < 100: muy borrosa
        100-500: algo borrosa
        > 500: nítida
        """
        import cv2
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        return cv2.Laplacian(img, cv2.CV_64F).var()
```

---

#### 6. Agrupación por Eventos/Sesiones

```python
# services/event_grouper_service.py
class EventGrouperService(BaseService):
    """Agrupa fotos por eventos basándose en proximidad temporal"""
    
    DEFAULT_GAP_HOURS = 3  # Fotos separadas por >3h = eventos diferentes
    
    def analyze(self, gap_hours: int = DEFAULT_GAP_HOURS, ...):
        """
        Agrupa archivos por:
        1. Fecha (best_date)
        2. Ubicación GPS (si disponible)
        3. Nombre de carpeta original
        """
```

---

#### 7. Detección de Duplicados con Diferente Aspect Ratio

```python
# services/aspect_ratio_duplicates_service.py
class AspectRatioDuplicatesService(BaseService):
    """Detecta mismas imágenes con diferentes proporciones"""
    
    def _compare_ignoring_borders(self, img1, img2) -> float:
        """
        Compara contenido central ignorando bordes.
        Útil para detectar:
        - Posts de Instagram con marcos blancos
        - Fotos recortadas a diferentes ratios
        """
```

---

### BAJA PRIORIDAD (Futuro)

#### 8. Historial de Operaciones

```python
# services/history_service.py
class OperationHistoryService:
    """Registra todas las operaciones para auditoría y deshacer"""
    
    def record_operation(self, operation: OperationRecord):
        """Guarda operación en base de datos"""
    
    def undo_operation(self, operation_id: str) -> bool:
        """Revierte operación si es posible (archivos en backup)"""
```

---

#### 9. Estadísticas y Dashboards

```python
# services/statistics_service.py
class StatisticsService:
    """Genera estadísticas de la biblioteca"""
    
    def get_overview(self) -> LibraryOverview:
        """
        Returns:
            - Total archivos por tipo
            - Distribución por año/mes
            - Espacio usado por categoría
            - Top 10 carpetas más grandes
        """
```

---

## Mejoras de UX/UI

### 1. ALTA PRIORIDAD: Mensajes Post-Operación Consistentes

**Problema:** Los mensajes después de ejecutar operaciones son inconsistentes entre herramientas.

**Solución:**

```python
# ui/dialogs/base_dialog.py
class BaseDialog:
    def show_operation_result(
        self,
        success: bool,
        items_processed: int,
        space_freed: int = 0,
        dry_run: bool = False,
        backup_path: Optional[Path] = None
    ):
        """Muestra resultado de operación de forma consistente"""
        
        if dry_run:
            title = "Simulación completada"
            icon = QMessageBox.Icon.Information
            message = f"Se simularía el procesamiento de {items_processed} archivos."
        elif success:
            title = "Operación completada"
            icon = QMessageBox.Icon.Information
            message = f"Se procesaron {items_processed} archivos."
            if space_freed > 0:
                message += f"\nEspacio liberado: {format_size(space_freed)}"
            if backup_path:
                message += f"\n\nBackup creado en:\n{backup_path}"
        else:
            title = "Error en operación"
            icon = QMessageBox.Icon.Warning
            message = "La operación no se completó correctamente."
```

---

### 2. ALTA PRIORIDAD: Sistema de Notificaciones

**Problema:** No hay feedback para operaciones largas que el usuario puede haber olvidado.

```python
# ui/components/notification_toast.py
class NotificationToast(QWidget):
    """Toast notification no intrusiva"""
    
    def show_success(self, message: str, duration_ms: int = 3000): ...
    def show_warning(self, message: str, duration_ms: int = 5000): ...
    def show_error(self, message: str, duration_ms: int = 0): ...  # Permanente
    
# Uso
self.toast.show_success("Análisis completado: 1,234 archivos procesados")
```

---

### 3. MEDIA PRIORIDAD: Internacionalización (i18n)

**Problema:** Todos los textos están hardcodeados en español.

**Solución:**

```python
# utils/i18n.py
from typing import Dict
import json

class I18n:
    _translations: Dict[str, Dict[str, str]] = {}
    _current_locale: str = 'es'
    
    @classmethod
    def load_translations(cls, locale: str):
        path = Path(__file__).parent / 'locales' / f'{locale}.json'
        cls._translations[locale] = json.loads(path.read_text())
    
    @classmethod
    def t(cls, key: str, **kwargs) -> str:
        """Traduce una clave con interpolación opcional"""
        template = cls._translations.get(cls._current_locale, {}).get(key, key)
        return template.format(**kwargs)

# Uso
from utils.i18n import I18n as _
button.setText(_('buttons.delete_selected'))  # "Eliminar seleccionados"
label.setText(_('messages.files_found', count=42))  # "42 archivos encontrados"
```

**Estructura de archivos:**
```
utils/
  locales/
    es.json
    en.json
    fr.json
```

---

### 4. MEDIA PRIORIDAD: Modo Oscuro/Claro

**Problema:** Solo hay un tema disponible.

```python
# ui/styles/themes.py
class Theme:
    LIGHT = {
        'background': '#FFFFFF',
        'surface': '#F5F5F5',
        'text': '#212121',
        ...
    }
    DARK = {
        'background': '#121212',
        'surface': '#1E1E1E', 
        'text': '#E0E0E0',
        ...
    }

# ui/styles/design_system.py
class DesignSystem:
    _current_theme = Theme.LIGHT
    
    @classmethod
    def set_theme(cls, theme: dict):
        cls._current_theme = theme
        # Actualizar todas las constantes de color
```

---

### 5. BAJA PRIORIDAD: Preview Mejorado de Imágenes

```python
# ui/components/enhanced_image_preview.py
class EnhancedImagePreview(QWidget):
    """
    Preview mejorado con:
    - Zoom con rueda del ratón
    - Pan arrastrando
    - Comparación lado a lado
    - Histograma
    - Info EXIF superpuesta
    """
```

---

## Optimización de Rendimiento

### 1. ALTA PRIORIDAD: Cálculo Paralelo de Hashes Perceptuales

**Problema:** El cálculo de hashes perceptuales es el cuello de botella para similar duplicates.

**Optimización:**

```python
# services/parallel_hash_calculator.py
class ParallelHashCalculator:
    """Calculador de hashes con paralelismo óptimo"""
    
    def calculate_batch(
        self, 
        files: List[Path],
        algorithm: str = 'phash',
        max_workers: int = None
    ) -> Dict[Path, str]:
        """
        Optimizaciones:
        1. Usar ProcessPoolExecutor para CPU-bound (no ThreadPool)
        2. Batch loading de imágenes pequeñas en memoria
        3. Caching de resultados en repositorio
        """
        max_workers = max_workers or Config.get_cpu_bound_workers()
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._calc_hash, f, algorithm): f 
                for f in files
            }
            ...
```

---

### 2. MEDIA PRIORIDAD: Lazy Loading en Diálogos

**Problema:** Diálogos con muchos grupos cargan todo al abrirse.

```python
# ui/dialogs/lazy_group_container.py
class LazyGroupContainer(QScrollArea):
    """Contenedor que carga grupos bajo demanda"""
    
    def __init__(self, groups: List[Any], render_func: Callable):
        self._all_groups = groups
        self._render_func = render_func
        self._loaded_range = (0, 0)
        
    def _on_scroll(self, value: int):
        """Carga grupos visibles + buffer"""
        visible_start = self._calculate_visible_start(value)
        visible_end = visible_start + self._visible_count
        
        # Buffer de 10 grupos arriba y abajo
        load_start = max(0, visible_start - 10)
        load_end = min(len(self._all_groups), visible_end + 10)
        
        self._ensure_loaded(load_start, load_end)
```

---

### 3. MEDIA PRIORIDAD: Índices en Repositorio para Queries Frecuentes

```python
# En FileInfoRepositoryCache
class FileInfoRepositoryCache:
    def __init__(self):
        # Índices en memoria para queries O(1)
        self._by_hash: Dict[str, Set[Path]] = defaultdict(set)
        self._by_size: Dict[int, Set[Path]] = defaultdict(set)
        self._by_extension: Dict[str, Set[Path]] = defaultdict(set)
        self._by_date: Dict[date, Set[Path]] = defaultdict(set)
    
    def add_file(self, path: Path, metadata: FileMetadata):
        # Actualizar todos los índices
        self._cache[path] = metadata
        if metadata.sha256:
            self._by_hash[metadata.sha256].add(path)
        self._by_size[metadata.fs_size].add(path)
        ...
```

---

## Testing y Calidad

### 1. ALTA PRIORIDAD: Tests de Integración End-to-End

**Problema:** Los tests actuales son principalmente unitarios. Faltan tests E2E.

```python
# tests/e2e/test_full_workflow.py
class TestFullWorkflow:
    """Tests que simulan el flujo completo de usuario"""
    
    def test_analyze_and_delete_duplicates(self, temp_dir, create_test_images):
        """
        1. Crear directorio con duplicados conocidos
        2. Ejecutar Stage 1 → Stage 2 → Stage 3
        3. Abrir DuplicatesExactDialog
        4. Ejecutar eliminación
        5. Verificar archivos eliminados correctamente
        6. Verificar backup existe
        7. Verificar caché actualizada
        """
    
    def test_cancellation_preserves_state(self, ...):
        """Verificar que cancelar en Stage 2 no corrompe datos"""
```

---

### 2. MEDIA PRIORIDAD: Property-Based Testing

```python
# tests/property/test_services_properties.py
from hypothesis import given, strategies as st

class TestServiceProperties:
    
    @given(st.lists(st.binary(min_size=1, max_size=1000)))
    def test_exact_duplicates_detects_all(self, file_contents):
        """Property: SHA256 siempre detecta contenidos idénticos"""
        # Crear archivos con contenidos dados
        # Verificar que todos los idénticos se agrupan
    
    @given(st.integers(min_value=0, max_value=100))
    def test_similarity_threshold_monotonic(self, sensitivity):
        """Property: Mayor sensibilidad → menos grupos (o igual)"""
```

---

### 3. MEDIA PRIORIDAD: Benchmark Suite

```python
# tests/performance/benchmark_suite.py
class BenchmarkSuite:
    """Benchmarks automatizados para detectar regresiones"""
    
    DATASETS = {
        'small': 100,
        'medium': 1000,
        'large': 10000,
        'huge': 50000,
    }
    
    def benchmark_hash_calculation(self, dataset_size: str):
        """Mide tiempo de cálculo de hashes"""
    
    def benchmark_clustering(self, dataset_size: str):
        """Mide tiempo de clustering BK-Tree"""
    
    def benchmark_memory_usage(self, dataset_size: str):
        """Mide uso de memoria del repositorio"""
```

---

## Priorización y Roadmap

### Fase 1: Estabilización y Calidad (Q1 2026)

| Tarea | Prioridad | Esfuerzo | Impacto |
|-------|-----------|----------|---------|
| Refactorizar servicios de duplicados | Alta | 2 días | Alto |
| Mensajes post-operación consistentes | Alta | 1 día | Alto |
| Tests E2E básicos | Alta | 3 días | Alto |
| Persistencia de caché | Alta | 2 días | Alto |

### Fase 2: Funcionalidades Core (Q2 2026)

| Tarea | Prioridad | Esfuerzo | Impacto |
|-------|-----------|----------|---------|
| Soporte videos en similares | Alta | 4 días | Alto |
| Detección de screenshots | Alta | 2 días | Medio |
| Eliminación de metadatos | Alta | 3 días | Alto |
| Conversión HEIC→JPG | Media | 3 días | Alto |

### Fase 3: UX y Rendimiento (Q3 2026)

| Tarea | Prioridad | Esfuerzo | Impacto |
|-------|-----------|----------|---------|
| Sistema de notificaciones | Media | 2 días | Medio |
| Internacionalización (i18n) | Media | 5 días | Alto |
| Modo oscuro | Media | 3 días | Medio |
| Lazy loading en diálogos | Media | 2 días | Medio |

### Fase 4: Avanzado (Q4 2026)

| Tarea | Prioridad | Esfuerzo | Impacto |
|-------|-----------|----------|---------|
| Migración a SQLite | Media | 5 días | Alto |
| Detección de borrosas | Baja | 3 días | Medio |
| Agrupación por eventos | Baja | 4 días | Medio |
| Sistema de plugins | Baja | 5 días | Alto |

---

## Apéndice: Bugs Conocidos

### Documentados en TODO.txt

1. **Bug en Similar Duplicates:** Si se elimina 1 archivo y se vuelve a Stage 3, al abrir de nuevo se queda colgado
   - **Causa probable:** Estado del análisis no se invalida correctamente
   - **Solución:** Invalidar `duplicates_similar` en ScanSnapshot al completar ejecución

2. **Mensajes inconsistentes en cards:** Los mensajes en Stage 3 después de usar herramientas son confusos
   - **Solución:** Implementar `show_operation_result()` consistente

3. **Videos en Similar Files:** No se procesan videos, solo imágenes
   - **Solución:** Implementar `VideoHashService`

### Detectados en Análisis

4. **Falta validación de rutas de backup:** No se verifica que el directorio de backup exista antes de crear
   - **Solución:** Añadir validación en `Config.DEFAULT_BACKUP_DIR`

5. **Perceptual hash no se cachea:** Se recalcula cada vez que se abre Similar Duplicates
   - **Solución:** Guardar hash perceptual en `FileMetadata` y poblar en `InitialScanner`

---

## Conclusión

InnerPix Lab tiene una base sólida y una arquitectura bien pensada. Las mejoras propuestas se centran en:

1. **Robustez:** Persistencia, tests E2E, manejo de errores
2. **Funcionalidad:** Videos en similares, screenshots, metadatos
3. **UX:** Mensajes consistentes, i18n, temas
4. **Rendimiento:** Cálculo paralelo, lazy loading, índices

La implementación gradual siguiendo el roadmap permitirá evolucionar la aplicación manteniendo estabilidad.

---

*Documento generado por análisis exhaustivo del código fuente el 29 de Enero de 2026*
