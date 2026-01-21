# 📋 PLAN DE REFACTOR COMPLETO - Servicio de Duplicados Similares

## 🎯 OBJETIVOS DEL REFACTOR

### Problemas Actuales Identificados

1. **Algoritmo impreciso al 100%**: La sensibilidad 100% muestra imágenes de ráfagas (ligeramente diferentes) cuando debería mostrar solo duplicados idénticos con diferentes resoluciones (ej: originales vs WhatsApp)

2. **Falta de modo automático**: Actualmente requiere selección manual de cada archivo. No existe modo automático para eliminación inteligente

3. **Algoritmos no claros**: La relación sensibilidad → distancia Hamming es confusa. El usuario no entiende claramente qué significa cada nivel

4. **Hash perceptual inadecuado**: Los hashes perceptuales (dhash, phash, ahash) están diseñados para detectar similitud visual, no duplicados exactos con diferentes resoluciones

### Solución Propuesta

**Implementar sistema dual de detección:**
- **Nivel 1 (100%)**: Duplicados idénticos (mismo contenido, diferente tamaño/compresión) usando **pHash + pHash contextual**
- **Nivel 2 (85-99%)**: Similares con pequeñas variaciones (recortes menores, ajustes ligeros)
- **Nivel 3 (50-84%)**: Similares con cambios moderados (filtros, ediciones)
- **Nivel 4 (30-49%)**: Similares remotos (composición similar)

---

## 📐 ARQUITECTURA PROPUESTA

### 1. Nuevo Sistema de Detección Multi-Nivel

```python
class SimilarityDetector:
    """
    Sistema de detección multi-nivel para archivos similares.
    Combina múltiples técnicas según el nivel de similitud deseado.
    """

    def __init__(self):
        self.perceptual_hasher = PerceptualHasher()
        self.content_hasher = ContentHasher()  # Nuevo: detecta contenido idéntico
        self.feature_detector = FeatureDetector()  # Nuevo: para niveles bajos
```

### 2. Estrategia de Hashing Mejorada

**Para 100% (Duplicados Idénticos):**
```python
class ContentHasher:
    """
    Detecta imágenes con contenido idéntico pero diferentes:
    - Resoluciones (original 4K vs WhatsApp 1080p)
    - Compresiones (RAW vs JPG, calidades diferentes)
    - Formatos (PNG vs JPG)

    Método: pHash + thumbnail hash + aspect ratio
    """

    def calculate_identity_signature(self, image_path: Path) -> IdentitySignature:
        """
        Genera firma de identidad que ignora:
        - Tamaño de imagen
        - Compresión JPEG
        - Formato de archivo

        Pero detecta diferencias en:
        - Contenido visual (píxeles)
        - Ráfagas de fotos
        - Ediciones
        """
        pass
```

**Para 85-99% (Similares con Variaciones Menores):**
```python
class PerceptualHasher:
    """
    Hash perceptual tradicional con mejoras:
    - pHash de alta resolución (16x16 o 32x32)
    - Tolerancia configurable
    - Normalización de brillo/contraste
    """
    pass
```

**Para 50-84% (Similares con Cambios Moderados):**
```python
class FeatureDetector:
    """
    Detección basada en características:
    - SIFT/ORB keypoints (opcional, más costoso)
    - Color histograms
    - Edge detection
    """
    pass
```

### 3. Modos de Operación

```python
class SimilarMode(Enum):
    """Modos de operación del servicio de similares"""
    MANUAL = "manual"        # Usuario selecciona qué eliminar (actual)
    AUTO_SMART = "auto_smart"  # Eliminación inteligente automática
    AUTO_SIZE = "auto_size"    # Elimina archivos más pequeños automáticamente
    AUTO_DATE = "auto_date"    # Mantiene archivos más recientes
```

#### 3.1 Modo Manual (Actual)
- Usuario revisa cada grupo
- Selecciona manualmente qué archivos eliminar
- Mantener comportamiento actual

#### 3.2 Modo Auto Smart (NUEVO)
**Lógica de eliminación inteligente:**

```python
def auto_select_files_to_delete(group: DuplicateGroup, mode: AutoStrategy) -> List[Path]:
    """
    Selección automática inteligente de archivos a eliminar.

    Criterios (en orden de prioridad):
    1. Mantener el archivo con mejor calidad (mayor resolución, menor compresión)
    2. Si hay archivo original y WhatsApp, eliminar WhatsApp
    3. Si hay diferentes formatos, mantener RAW/HEIC > JPG > PNG
    4. Mantener el archivo más antiguo (fecha de captura)
    5. Si hay empate, mantener el de mayor tamaño
    """

    # Detectar origen de archivos
    whatsapp_files = [f for f in group.files if is_whatsapp_file(f)]
    original_files = [f for f in group.files if f not in whatsapp_files]

    # Caso 1: Hay originales y WhatsApp → Eliminar WhatsApp
    if original_files and whatsapp_files:
        return whatsapp_files

    # Caso 2: Todos son similares → Mantener mayor resolución
    files_with_metadata = [
        (f, get_image_resolution(f), get_file_quality_score(f))
        for f in group.files
    ]

    # Ordenar por: resolución DESC, calidad DESC, fecha ASC
    files_with_metadata.sort(
        key=lambda x: (x[1], x[2], get_capture_date(x[0])),
        reverse=True
    )

    # Mantener el mejor, eliminar el resto
    keep_file = files_with_metadata[0][0]
    return [f for f in group.files if f != keep_file]
```

#### 3.3 Modo Auto Size (NUEVO)
```python
def auto_select_by_size(group: DuplicateGroup) -> List[Path]:
    """
    Elimina automáticamente los archivos más pequeños.
    Útil para eliminar versiones comprimidas/WhatsApp.
    """
    largest_file = max(group.files, key=lambda f: f.stat().st_size)
    return [f for f in group.files if f != largest_file]
```

#### 3.4 Modo Auto Date (NUEVO)
```python
def auto_select_by_date(group: DuplicateGroup, keep_newest: bool = True) -> List[Path]:
    """
    Mantiene el archivo más reciente (o más antiguo) basado en fecha de captura EXIF.
    """
    files_with_dates = [(f, get_best_date(f)) for f in group.files]
    files_with_dates.sort(key=lambda x: x[1], reverse=keep_newest)
    keep_file = files_with_dates[0][0]
    return [f for f in group.files if f != keep_file]
```

---

## 🔧 CAMBIOS EN CONFIG.PY

```python
class Config:
    # ========================================================================
    # CONFIGURACIÓN DE ARCHIVOS SIMILARES - REFACTORIZADO
    # ========================================================================

    # Niveles de detección
    SIMILARITY_LEVEL_IDENTICAL = 100    # Duplicados idénticos (diferentes resoluciones)
    SIMILARITY_LEVEL_VERY_HIGH = 90     # Muy similares (recortes mínimos)
    SIMILARITY_LEVEL_HIGH = 75          # Similares (ediciones ligeras)
    SIMILARITY_LEVEL_MEDIUM = 50        # Moderadamente similares
    SIMILARITY_LEVEL_LOW = 30           # Remotamente similares

    # Configuración de detección para nivel 100% (IDÉNTICOS)
    IDENTICAL_DETECTION_METHOD = "content_hash"  # "content_hash", "phash_strict", "combined"
    IDENTICAL_PHASH_SIZE = 32  # Hash de alta resolución para nivel 100%
    IDENTICAL_MAX_HAMMING = 2  # Máximo 2 bits de diferencia para considerar "idéntico"

    # Configuración de detección para niveles 85-99% (SIMILARES)
    SIMILAR_PHASH_SIZE = 16
    SIMILAR_ALGORITHM = "phash"  # phash más robusto que dhash para similitud

    # Configuración de detección para niveles 30-84% (VARIACIONES)
    VARIATION_PHASH_SIZE = 8
    VARIATION_USE_COLOR_HIST = True  # Usar histogramas de color adicionales

    # Modos automáticos
    AUTO_MODE_DEFAULT = "auto_smart"  # "manual", "auto_smart", "auto_size", "auto_date"
    AUTO_MODE_WHATSAPP_PRIORITY = True  # Priorizar eliminación de archivos WhatsApp
    AUTO_MODE_KEEP_RAW = True  # Siempre mantener archivos RAW si existen
    AUTO_MODE_PREFER_HIGHEST_RES = True  # Mantener resolución más alta
```

---

## 📦 NUEVAS ESTRUCTURAS DE DATOS

```python
@dataclass
class IdentitySignature:
    """
    Firma de identidad para detectar imágenes idénticas con diferentes resoluciones.
    """
    phash_32: int  # pHash de 32x32 (1024 bits)
    aspect_ratio: float  # Relación de aspecto (ancho/alto)
    thumbnail_hash: int  # Hash de thumbnail 8x8 normalizado
    color_profile: str  # Perfil de color dominante (HSV)
    edge_hash: int  # Hash de bordes/contornos principales

    def is_identical_to(self, other: 'IdentitySignature', tolerance: int = 2) -> bool:
        """
        Determina si dos firmas representan la misma imagen.
        Tolerancia: bits de diferencia permitidos (default: 2)
        """
        pass

@dataclass
class SimilarityAnalysisConfig:
    """Configuración para análisis de similitud"""
    level: int  # 30-100
    mode: SimilarMode  # manual, auto_smart, auto_size, auto_date
    detect_whatsapp: bool = True
    prefer_raw: bool = True
    keep_newest: bool = True  # Para modo auto_date

@dataclass
class EnhancedDuplicateGroup:
    """Grupo de duplicados con metadata enriquecida"""
    hash_value: str
    files: List[Path]
    total_size: int
    similarity_score: float

    # Metadata enriquecida
    whatsapp_files: List[Path] = field(default_factory=list)
    original_files: List[Path] = field(default_factory=list)
    file_qualities: Dict[Path, float] = field(default_factory=dict)  # Score de calidad 0-100
    file_resolutions: Dict[Path, Tuple[int, int]] = field(default_factory=dict)
    capture_dates: Dict[Path, datetime] = field(default_factory=dict)

    # Auto-selección
    auto_suggestion: Optional[List[Path]] = None  # Archivos sugeridos para eliminar
    auto_confidence: float = 0.0  # Confianza de la sugerencia 0-100
```

---

## 🔄 REFACTOR DEL SERVICIO PRINCIPAL

```python
class DuplicatesSimilarService(DuplicatesBaseService):
    """
    Servicio refactorizado con detección multi-nivel y modo automático.
    """

    def analyze(
        self,
        sensitivity: int = 100,
        mode: SimilarMode = SimilarMode.MANUAL,
        progress_callback: Optional[ProgressCallback] = None,
        **kwargs
    ) -> DuplicateAnalysisResult:
        """
        Analiza archivos similares con configuración especificada.

        Args:
            sensitivity: Nivel de similitud (30-100)
                - 100: Solo duplicados IDÉNTICOS (diferentes resoluciones/compresión)
                - 90-99: Muy similares (recortes mínimos, ajustes leves)
                - 75-89: Similares (ediciones ligeras, filtros suaves)
                - 50-74: Moderadamente similares
                - 30-49: Remotamente similares

            mode: Modo de operación
                - MANUAL: Usuario selecciona manualmente (default)
                - AUTO_SMART: Eliminación inteligente automática
                - AUTO_SIZE: Elimina archivos más pequeños
                - AUTO_DATE: Mantiene archivos más recientes
        """

        # Fase 1: Calcular hashes según nivel de sensibilidad
        if sensitivity == 100:
            analysis = self._detect_identical_duplicates(progress_callback)
        elif sensitivity >= 85:
            analysis = self._detect_very_similar(sensitivity, progress_callback)
        else:
            analysis = self._detect_similar(sensitivity, progress_callback)

        # Fase 2: Si modo automático, calcular sugerencias
        if mode != SimilarMode.MANUAL:
            analysis = self._calculate_auto_suggestions(analysis, mode)

        return analysis

    def _detect_identical_duplicates(
        self,
        progress_callback: Optional[ProgressCallback] = None
    ) -> DuplicateAnalysisResult:
        """
        Detecta duplicados IDÉNTICOS con diferentes resoluciones/compresión.

        Usa:
        - pHash de alta resolución (32x32)
        - Thumbnail hash normalizado
        - Aspect ratio matching
        - Threshold muy estricto (2 bits)
        """
        pass

    def _detect_very_similar(
        self,
        sensitivity: int,
        progress_callback: Optional[ProgressCallback] = None
    ) -> DuplicateAnalysisResult:
        """
        Detecta archivos muy similares (85-99%).
        Usa pHash de resolución media (16x16) con threshold ajustable.
        """
        pass

    def _detect_similar(
        self,
        sensitivity: int,
        progress_callback: Optional[ProgressCallback] = None
    ) -> DuplicateAnalysisResult:
        """
        Detecta archivos similares (30-84%).
        Usa pHash estándar + histogramas de color.
        """
        pass

    def _calculate_auto_suggestions(
        self,
        analysis: DuplicateAnalysisResult,
        mode: SimilarMode
    ) -> DuplicateAnalysisResult:
        """
        Calcula sugerencias automáticas de eliminación para cada grupo.
        Añade auto_suggestion y auto_confidence a cada grupo.
        """
        pass

    def execute(
        self,
        groups: List[DuplicateGroup],
        selections: Dict[int, List[Path]],
        mode: SimilarMode = SimilarMode.MANUAL,
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[ProgressCallback] = None
    ) -> DuplicateExecutionResult:
        """
        Ejecuta eliminación de duplicados.

        Args:
            groups: Grupos de duplicados
            selections: {group_index: [files_to_delete]} - Solo para modo MANUAL
            mode: Modo de ejecución
            create_backup: Crear backup antes de eliminar
            dry_run: Simulación sin cambios reales
        """

        if mode == SimilarMode.MANUAL:
            # Usar selecciones manuales
            files_to_delete = self._collect_manual_selections(groups, selections)
        else:
            # Usar sugerencias automáticas
            files_to_delete = self._collect_auto_selections(groups, mode)

        # Ejecutar eliminación
        return self._execute_deletion(
            files_to_delete,
            create_backup,
            dry_run,
            progress_callback
        )
```

---

## 🖥️ CAMBIOS EN LA UI (Dialogs)

### 1. Selector de Modo (Nuevo Widget)

```python
class SimilarModeSelector(QWidget):
    """
    Widget para seleccionar modo de operación:
    - Manual (actual)
    - Auto Smart (recomendado)
    - Auto Size
    - Auto Date
    """
    mode_changed = pyqtSignal(SimilarMode)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        # Radio buttons para cada modo
        self.manual_radio = QRadioButton("Manual")
        self.auto_smart_radio = QRadioButton("Auto Smart (Recomendado)")
        self.auto_size_radio = QRadioButton("Auto por Tamaño")
        self.auto_date_radio = QRadioButton("Auto por Fecha")

        # Tooltips explicativos
        self.manual_radio.setToolTip(
            "Selecciona manualmente qué archivos eliminar en cada grupo"
        )
        self.auto_smart_radio.setToolTip(
            "Eliminación inteligente automática:\n"
            "- Elimina versiones de WhatsApp si hay originales\n"
            "- Mantiene la mayor resolución\n"
            "- Prefiere archivos RAW sobre JPG"
        )
        # ... más tooltips
```

### 2. Indicador de Sugerencias Automáticas

```python
class GroupCardWithSuggestion(QFrame):
    """
    Tarjeta de grupo con indicador visual de sugerencia automática.
    """

    def __init__(self, group: EnhancedDuplicateGroup, parent=None):
        super().__init__(parent)
        self.group = group
        self._setup_ui()

    def _setup_ui(self):
        # ... UI existente ...

        # Si hay sugerencia automática, mostrar indicador
        if self.group.auto_suggestion:
            self._add_auto_suggestion_indicator()

    def _add_auto_suggestion_indicator(self):
        """
        Añade indicador visual de sugerencia automática:
        - Icono de IA/cerebro
        - Confianza de la sugerencia
        - Archivos sugeridos para eliminar (marcados)
        """
        suggestion_frame = QFrame()
        suggestion_layout = QHBoxLayout(suggestion_frame)

        # Icono
        icon_label = QLabel("🤖")

        # Texto
        confidence = self.group.auto_confidence
        confidence_color = (
            "green" if confidence >= 90 else
            "orange" if confidence >= 70 else
            "red"
        )

        text_label = QLabel(
            f"<b>Sugerencia Auto:</b> "
            f"<span style='color:{confidence_color}'>Confianza {confidence:.0f}%</span>"
        )

        # Botón para aplicar sugerencia
        apply_btn = QPushButton("Aplicar Sugerencia")
        apply_btn.clicked.connect(self._apply_auto_suggestion)

        suggestion_layout.addWidget(icon_label)
        suggestion_layout.addWidget(text_label)
        suggestion_layout.addStretch()
        suggestion_layout.addWidget(apply_btn)
```

### 3. Escala de Sensibilidad Mejorada

```python
class EnhancedSensitivitySlider(QWidget):
    """
    Slider de sensibilidad con indicadores visuales claros.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(30, 100)
        self.slider.setValue(100)

        # Etiquetas de rangos
        labels_layout = QHBoxLayout()

        ranges = [
            (100, "IDÉNTICOS", "Solo duplicados con diferente resolución/compresión"),
            (90, "MUY SIMILARES", "Recortes mínimos o ajustes leves"),
            (75, "SIMILARES", "Ediciones ligeras, filtros suaves"),
            (50, "MODERADOS", "Cambios visibles pero misma escena"),
            (30, "REMOTOS", "Composición similar")
        ]

        for value, label, description in ranges:
            marker = QVBoxLayout()

            value_label = QLabel(f"{value}%")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            text_label = QLabel(f"<b>{label}</b>")
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            desc_label = QLabel(f"<small>{description}</small>")
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setWordWrap(True)

            marker.addWidget(value_label)
            marker.addWidget(text_label)
            marker.addWidget(desc_label)

            labels_layout.addLayout(marker)
```

---

## 🧪 PLAN DE TESTING

### 1. Tests Unitarios Nuevos

```python
# tests/unit/services/test_duplicates_similar_refactor.py

class TestIdentityDetection:
    """Tests para detección de duplicados idénticos (100%)"""

    def test_identical_different_resolutions(self):
        """
        Verifica que detecta como idénticas:
        - Original 4K
        - Misma imagen en 1080p
        - Misma imagen en 720p
        """
        pass

    def test_identical_different_compression(self):
        """
        Verifica que detecta como idénticas:
        - Misma imagen JPG quality 100
        - Misma imagen JPG quality 80
        - Misma imagen JPG quality 50
        """
        pass

    def test_not_identical_burst_photos(self):
        """
        Verifica que NO detecta como idénticas:
        - Fotos de ráfaga (misma escena, fracciones de segundo)
        """
        pass

    def test_not_identical_edits(self):
        """
        Verifica que NO detecta como idénticas:
        - Original vs editada (filtro, ajustes)
        """
        pass

class TestAutoModes:
    """Tests para modos automáticos"""

    def test_auto_smart_whatsapp_vs_original(self):
        """
        Auto Smart debe eliminar WhatsApp cuando hay original
        """
        pass

    def test_auto_smart_prefer_highest_resolution(self):
        """
        Auto Smart debe mantener la resolución más alta
        """
        pass

    def test_auto_size_keeps_largest(self):
        """
        Auto Size debe mantener el archivo más grande
        """
        pass

    def test_auto_date_keeps_newest(self):
        """
        Auto Date debe mantener el archivo más reciente
        """
        pass

class TestSensitivityLevels:
    """Tests para diferentes niveles de sensibilidad"""

    def test_100_only_identical(self):
        """
        100% solo debe detectar duplicados idénticos
        """
        pass

    def test_90_very_similar(self):
        """
        90% debe detectar muy similares (recortes mínimos)
        """
        pass
```

### 2. Tests de Integración

```python
# tests/integration/test_similar_files_workflow.py

def test_full_workflow_manual_mode():
    """Test del flujo completo en modo manual"""
    pass

def test_full_workflow_auto_smart():
    """Test del flujo completo en modo auto smart"""
    pass

def test_consecutive_operations():
    """Test de operaciones consecutivas (analyze → execute → analyze)"""
    pass
```

### 3. Tests de Performance

```python
# tests/performance/test_similar_detection_performance.py

def test_large_dataset_10k_images():
    """
    Verifica que el análisis de 10K imágenes se completa en <5 minutos
    """
    pass

def test_clustering_efficiency():
    """
    Verifica que clustering usa BK-Tree eficientemente (O(N log N))
    """
    pass
```

---

## 📝 DOCUMENTACIÓN A ACTUALIZAR

### 1. Actualizar `.github/copilot-instructions.md`

```markdown
**Similar Files Analysis** - Multi-level detection system
- **100% (IDENTICAL)**: Content-identical duplicates with different resolutions/compression
  - Uses: pHash 32x32 + thumbnail hash + aspect ratio
  - Max Hamming: 2 bits
  - Detects: WhatsApp vs originals, different JPG qualities, format conversions
  - Does NOT detect: Burst photos, edits, crops

- **85-99% (VERY SIMILAR)**: Minor variations (minimal crops, slight adjustments)
  - Uses: pHash 16x16
  - Threshold: 2-10 bits

- **50-84% (SIMILAR)**: Moderate changes (filters, edits)
  - Uses: pHash 8x8 + color histograms

- **30-49% (REMOTE)**: Composition similarity
  - Uses: pHash 8x8 + loose threshold

**Auto Modes** (`SimilarMode`):
- `MANUAL`: User selects files to delete (default)
- `AUTO_SMART`: Intelligent auto-deletion (recommended)
  - Deletes WhatsApp versions when originals exist
  - Keeps highest resolution
  - Prefers RAW > HEIC > JPG
  - Keeps oldest capture date
- `AUTO_SIZE`: Deletes smaller files automatically
- `AUTO_DATE`: Keeps newest (or oldest) files

**Config Parameters**:
- `IDENTICAL_DETECTION_METHOD`: "content_hash", "phash_strict", "combined"
- `AUTO_MODE_DEFAULT`: Default auto mode for UI
- `AUTO_MODE_WHATSAPP_PRIORITY`: Prioritize WhatsApp deletion
- `AUTO_MODE_KEEP_RAW`: Always keep RAW files if they exist
```

### 2. Actualizar `AGENTS.md`

Añadir sección sobre el sistema de detección multi-nivel y modos automáticos.

---

## 🚀 PLAN DE IMPLEMENTACIÓN

### Fase 1: Fundamentos (Semana 1)
- [ ] Implementar `IdentitySignature` y `ContentHasher`
- [ ] Implementar detección de nivel 100% (idénticos)
- [ ] Tests unitarios para detección idéntica
- [ ] Validar que 100% NO detecta ráfagas

### Fase 2: Estructura Multi-Nivel (Semana 2)
- [ ] Refactorizar `DuplicatesSimilarService` con sistema multi-nivel
- [ ] Implementar `_detect_identical_duplicates()`
- [ ] Implementar `_detect_very_similar()`
- [ ] Implementar `_detect_similar()`
- [ ] Tests para cada nivel

### Fase 3: Modos Automáticos (Semana 3)
- [ ] Implementar `SimilarMode` enum
- [ ] Implementar `_calculate_auto_suggestions()`
- [ ] Implementar estrategias auto (smart, size, date)
- [ ] Tests para modos automáticos
- [ ] Integración con `execute()`

### Fase 4: UI y UX (Semana 4)
- [ ] Crear `SimilarModeSelector` widget
- [ ] Actualizar `DuplicatesSimilarDialog` con selector de modo
- [ ] Añadir `GroupCardWithSuggestion`
- [ ] Crear `EnhancedSensitivitySlider` con rangos claros
- [ ] Tests de UI

### Fase 5: Optimización y Pulido (Semana 5)
- [ ] Optimizar performance para datasets grandes (>10K)
- [ ] Ajustar thresholds basado en testing real
- [ ] Añadir logs detallados
- [ ] Documentación completa
- [ ] Tests de integración end-to-end

### Fase 6: Testing y Validación (Semana 6)
- [ ] Testing con datasets reales
- [ ] Validación de precisión al 100%
- [ ] Benchmark de performance
- [ ] Corrección de bugs detectados
- [ ] Release candidate

---

## 📊 MÉTRICAS DE ÉXITO

1. **Precisión al 100%**:
   - ✅ Detecta WhatsApp vs originales (mismo contenido, diferente resolución)
   - ✅ Detecta diferentes compresiones JPG
   - ✅ Detecta conversiones de formato (PNG ↔ JPG)
   - ❌ NO detecta ráfagas de fotos (diferentes por fracciones de segundo)
   - ❌ NO detecta ediciones/filtros

2. **Modo Automático**:
   - ✅ Auto Smart elimina correctamente en >95% de casos
   - ✅ Auto Size funciona sin errores
   - ✅ Auto Date respeta fechas EXIF

3. **Performance**:
   - ⏱️ <5 minutos para 10,000 imágenes (análisis completo)
   - ⏱️ <1 segundo para clustering con cualquier sensibilidad
   - 📦 Memoria < 2GB para 10,000 imágenes

4. **UX**:
   - 🎯 Usuario entiende claramente cada nivel de sensibilidad
   - 🤖 Sugerencias automáticas con >90% confianza
   - ✨ Interfaz intuitiva y moderna

---

## 🔍 CONSIDERACIONES ADICIONALES

### Dependencias Nuevas
```txt
# Posibles nuevas dependencias
opencv-python>=4.8.0  # Para detección de características (opcional)
scikit-image>=0.21.0  # Para procesamiento avanzado (opcional)
```

### Migración de Datos
- El cache existente de hashes perceptuales será compatible
- Añadir `version` al cache para futuras migraciones
- Documentar proceso de migración

### Compatibilidad
- Mantener API backwards compatible para `analyze()`
- Deprecar parámetros antiguos con warnings, no eliminar
- Añadir nuevos parámetros como opcionales

---

## ❓ PREGUNTAS PARA VALIDAR

1. **¿Qué hacer con grupos mixtos?** (ej: 2 idénticas + 1 de ráfaga)
   - Propuesta: Separar en sub-grupos con diferentes similarity_score

2. **¿Permitir múltiples archivos a mantener en auto mode?**
   - Propuesta: Por defecto mantener 1, opción avanzada para mantener N

3. **¿Qué hacer si auto_confidence < 70%?**
   - Propuesta: Fallback a modo manual para ese grupo

4. **¿Soportar videos en detección de idénticos?**
   - Propuesta: Fase 2, por ahora solo imágenes

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### ✅ Fase 1 Completada
- [x] Análisis del código actual
- [x] Identificación de problemas
- [x] Diseño de arquitectura multi-nivel
- [x] Plan de implementación detallado
- [x] Documentación del plan

### 🔄 Próximos Pasos
- [ ] Implementar `IdentitySignature` class
- [ ] Crear `ContentHasher` para detección de idénticos
- [ ] Refactorizar `DuplicatesSimilarService.analyze()` con multi-nivel
- [ ] Añadir modos automáticos
- [ ] Actualizar UI con nuevos controles
- [ ] Tests exhaustivos
- [ ] Validación con datasets reales