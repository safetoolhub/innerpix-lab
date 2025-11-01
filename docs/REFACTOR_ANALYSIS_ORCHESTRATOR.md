# Refactoring: Analysis Orchestrator

## Contexto

**Prioridad 3** de la refactorización platform-agnostic: separar la lógica de análisis completo de directorios de los workers de Qt.

### Problema Original

`AnalysisWorker` en `ui/workers.py` mezclaba dos responsabilidades:
- Lógica de negocio: coordinar múltiples servicios de análisis
- Threading Qt: emitir señales para actualizar UI

Esto impedía:
- Ejecutar análisis completos desde CLI/scripts sin PyQt6
- Testear la lógica de coordinación independientemente
- Reutilizar el flujo de análisis en otros contextos

## Solución Implementada

### 1. Nuevo Servicio: `services/analysis_orchestrator.py`

**Clase Principal: `AnalysisOrchestrator`**

Coordina todos los servicios de análisis con un sistema de callbacks flexible:

```python
class AnalysisOrchestrator:
    """Orquesta análisis completo sin dependencias UI"""
    
    @staticmethod
    def scan_directory(directory_path: Path) -> DirectoryScanResult:
        """Escanea y clasifica archivos del directorio"""
        # Retorna imágenes, videos, otros archivos
    
    @staticmethod
    def run_full_analysis(
        directory_path: Path,
        analyze_renaming: bool = True,
        analyze_live_photos: bool = True,
        analyze_organization: bool = True,
        analyze_heic: bool = True,
        analyze_duplicates: bool = True,
        find_similar_duplicates: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
        phase_callback: Optional[Callable[[str], None]] = None,
        partial_callback: Optional[Callable[[str, Any], None]] = None
    ) -> FullAnalysisResult:
        """Ejecuta análisis completo con callbacks opcionales"""
```

**Dataclasses de Resultado:**

```python
@dataclass
class DirectoryScanResult:
    """Resultado del escaneo inicial"""
    images: List[Path]
    videos: List[Path]
    others: List[Path]
    total_files: int
    total_size_mb: float

@dataclass
class FullAnalysisResult:
    """Resultado del análisis completo"""
    scan_result: DirectoryScanResult
    rename_result: Optional[RenameResult]
    live_photos_result: Optional[LivePhotoAnalysisResult]
    organization_result: Optional[OrganizationResult]
    heic_result: Optional[HEICRemovalResult]
    exact_duplicates_result: Optional[DuplicateDetectionResult]
    similar_duplicates_result: Optional[DuplicateDetectionResult]
    errors: List[str]
    # ... timestamps y métricas
```

**Sistema de Callbacks:**

- `progress_callback(message: str)`: Mensajes de progreso generales
- `phase_callback(phase_name: str)`: Notificación de inicio de fase
- `partial_callback(phase_name: str, result: Any)`: Resultados parciales disponibles

Este diseño permite usar los mismos callbacks para:
- **GUI**: emitir señales Qt → actualizar widgets
- **CLI**: print() → mostrar en terminal
- **Tests**: acumular en listas → verificar comportamiento

### 2. Simplificación de `ui/workers.py`

**AnalysisWorker Refactorizado (~155 líneas → ~50 líneas):**

```python
class AnalysisWorker(BaseWorker):
    def __init__(self, directory_path, ...):
        super().__init__()
        self.directory_path = directory_path
        self.analyze_renaming = analyze_renaming
        # ... flags de análisis
    
    def run(self):
        try:
            # Delegación directa al orchestrator
            result = AnalysisOrchestrator.run_full_analysis(
                directory_path=Path(self.directory_path),
                analyze_renaming=self.analyze_renaming,
                # ... pasar flags
                progress_callback=lambda msg: self.progress_update.emit(msg),
                phase_callback=lambda phase: self.phase_started.emit(phase),
                partial_callback=self._handle_partial_result
            )
            
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
    
    def _handle_partial_result(self, phase_name: str, result: Any):
        """Convierte resultados parciales en señales Qt"""
        self.partial_result_ready.emit(phase_name, result)
```

**Beneficios:**
- Worker solo maneja threading + señales Qt
- Toda la lógica de análisis está en `AnalysisOrchestrator`
- No hay duplicación de código
- Fácil mantener sincronizados CLI y GUI

### 3. Bug Fix: `services/duplicate_detector.py`

**Problema:** Import condicional de `imagehash` causaba `NameError` en type hints:

```python
try:
    import imagehash
except ImportError:
    pass  # ❌ imagehash queda indefinido

def _calculate_perceptual_hash(...) -> Optional[imagehash.ImageHash]:
    # NameError si imagehash no se importó
```

**Solución:** Establecer variable a None cuando falla:

```python
try:
    import imagehash
except ImportError:
    imagehash = None  # ✅ Variable definida

def _calculate_perceptual_hash(...) -> Optional[any]:
    # Type hint genérico, sin NameError
```

## Uso

### Desde CLI (sin PyQt6)

```python
from pathlib import Path
from services.analysis_orchestrator import AnalysisOrchestrator

def print_progress(msg: str):
    print(f"  {msg}")

def print_phase(phase: str):
    print(f"\n📌 Fase: {phase}")

result = AnalysisOrchestrator.run_full_analysis(
    directory_path=Path("/path/to/photos"),
    analyze_renaming=True,
    analyze_live_photos=True,
    progress_callback=print_progress,
    phase_callback=print_phase
)

print(f"✅ Análisis completado: {result.total_files} archivos")
```

### Desde GUI (con PyQt6)

```python
class AnalysisController:
    def start_analysis(self, directory: str):
        worker = AnalysisWorker(
            directory_path=directory,
            analyze_renaming=True,
            # ... flags
        )
        
        # Conectar señales Qt
        worker.progress_update.connect(self.progress_controller.update_status)
        worker.phase_started.connect(self._handle_phase)
        worker.finished.connect(self._on_analysis_complete)
        
        worker.start()
```

## Testing

### Tests Unitarios: `tests/test_analysis_orchestrator.py`

```python
def test_scan_directory(test_directory):
    """Verifica escaneo básico sin análisis"""
    result = AnalysisOrchestrator.scan_directory(test_directory)
    assert result.total_files == 5
    assert len(result.images) == 3

def test_full_analysis_with_callbacks(test_directory):
    """Verifica que callbacks se invocan correctamente"""
    progress_messages = []
    phases = []
    
    result = AnalysisOrchestrator.run_full_analysis(
        directory_path=test_directory,
        progress_callback=lambda msg: progress_messages.append(msg),
        phase_callback=lambda phase: phases.append(phase)
    )
    
    assert len(progress_messages) > 0
    assert "Renaming" in phases
```

### Demo CLI: `tests/demo_orchestrator_cli.py`

Script ejecutable que demuestra uso sin PyQt6:

```bash
# Crear directorio temporal de prueba
tmpdir=$(mktemp -d)
touch "$tmpdir/photo1.jpg" "$tmpdir/photo2.png" "$tmpdir/video1.mov"

# Ejecutar análisis sin PyQt6
python tests/demo_orchestrator_cli.py "$tmpdir" --no-organization --no-heic

# Limpiar
rm -rf "$tmpdir"
```

**Salida típica:**
```
🔍 Análisis de Directorio: /tmp/tmp.xxx
  Escaneando archivos...
  Total: 3 archivos
  - Imágenes: 2
  - Videos: 1
  - Otros: 0

📌 Fase: Renaming
  Analizando nombres de archivos...
  ✅ 0 archivos necesitan renombre

📌 Fase: Live Photos
  Detectando Live Photos...
  ✅ 0 pares de Live Photo encontrados

✅ Análisis completado exitosamente
```

## Verificación

### Test CLI (sin PyQt6)
```bash
python tests/demo_orchestrator_cli.py /ruta/a/fotos
```

### Test GUI (con PyQt6)
```bash
python main.py
# 1. Seleccionar directorio
# 2. Iniciar análisis
# 3. Verificar progreso en UI
```

### Verificar logs
```bash
tail -f ~/Documents/Pixaro_Lab/logs/pixaro_lab_*.log
```

**Líneas esperadas:**
```
AnalysisOrchestrator - INFO - === Iniciando análisis completo de: /path ===
AnalysisOrchestrator - INFO - Escaneo completado: X imágenes, Y videos, Z otros
AnalysisOrchestrator - INFO - Fase 'Renaming' completada en X.XX segundos
AnalysisOrchestrator - INFO - === Análisis completo finalizado ===
```

## Impacto en Arquitectura

### Antes (Prioridad 3)
```
AnalysisWorker (155 líneas)
├── Coordina servicios ❌ lógica de negocio
├── Emite señales Qt ✅ responsabilidad correcta
└── No reutilizable fuera de Qt ❌
```

### Después (Prioridad 3 ✅)
```
AnalysisOrchestrator (400+ líneas)
├── Coordina servicios ✅ 100% platform-free
├── Sistema de callbacks ✅ flexible UI/CLI
└── Testeable independientemente ✅

AnalysisWorker (50 líneas)
├── Delega a orchestrator ✅ separation of concerns
├── Solo maneja Qt threading ✅ responsabilidad única
└── Convierte callbacks → señales ✅ thin wrapper
```

## Beneficios Conseguidos

1. **Separación de Responsabilidades**
   - Orchestrator: lógica de coordinación
   - Worker: threading Qt + señales
   - Servicios: análisis específicos

2. **Platform-Agnostic**
   - `services/analysis_orchestrator.py` sin imports de PyQt6
   - Ejecutable desde CLI/scripts/tests sin GUI
   - Callbacks genéricos adaptables a cualquier UI

3. **Testabilidad**
   - Tests unitarios sin mock de Qt
   - Demo CLI verifica comportamiento completo
   - Fácil reproducir bugs en contexto CLI

4. **Mantenibilidad**
   - Una sola fuente de verdad para flujo de análisis
   - Workers simples, fáciles de entender
   - Cambios en lógica no afectan UI

5. **Reutilización**
   - Mismo orchestrator para GUI/CLI/batch scripts
   - Callbacks permiten adaptar a diferentes contextos
   - Resultados tipados facilitan integración

## Notas de Implementación

### Callbacks vs Señales Qt

**Callbacks (Orchestrator):**
```python
# Genérico, funciona en cualquier contexto
progress_callback("Procesando archivo X")
```

**Señales Qt (Worker):**
```python
# Específico de Qt, solo en GUI
self.progress_update.emit("Procesando archivo X")
```

**Patrón de conversión en Worker:**
```python
progress_callback=lambda msg: self.progress_update.emit(msg)
```

### Type Hints con Imports Condicionales

**❌ Problema:**
```python
try:
    import imagehash
except ImportError:
    pass

def func() -> Optional[imagehash.ImageHash]:  # NameError
```

**✅ Solución:**
```python
try:
    import imagehash
except ImportError:
    imagehash = None

def func() -> Optional[any]:  # Type hint genérico
```

### Callbacks Opcionales

Todos los callbacks son `Optional[Callable[...]]`:
- Si son `None`, simplemente no se invocan
- Permite usar orchestrator sin callbacks (tests simples)
- Progreso detallado solo cuando se necesita

## Próximos Pasos Sugeridos

1. **Performance Monitoring**
   - `FullAnalysisResult` ya incluye timestamps
   - Considerar agregar profiling de fases lentas

2. **Orchestrators Adicionales**
   - `ExecutionOrchestrator` para operaciones destructivas
   - `BackupOrchestrator` para estrategias de backup

3. **Integración Tests**
   - Tests de flujo completo GUI usando `QTest`
   - Verificar que señales Qt se emiten correctamente

4. **CLI Tool**
   - Script completo CLI usando orchestrators
   - Argumentos para controlar qué análisis ejecutar

## Referencias

- **Código**: `services/analysis_orchestrator.py` (~400 líneas)
- **Tests**: `tests/test_analysis_orchestrator.py` (~200 líneas)
- **Demo**: `tests/demo_orchestrator_cli.py` (~100 líneas)
- **Worker**: `ui/workers.py` (AnalysisWorker simplificado)

## Resumen

✅ **Objetivo conseguido**: Lógica de análisis 100% independiente de PyQt6

- `services/analysis_orchestrator.py`: sin imports de Qt
- `ui/workers.py`: solo threading + señales
- Ejecutable desde CLI sin dependencias GUI
- Tests sin mocks complejos
- Arquitectura limpia y mantenible
