# Refactorización del Sistema de Análisis - Stage 2

## 📋 Resumen

Se ha refactorizado completamente el sistema de análisis para mejorar la experiencia del usuario con timing controlado y visualización progresiva de 7 fases.

## 🎯 Objetivos Logrados

1. **Timing mínimo de 2 segundos por fase**: Cada fase del análisis tiene una duración mínima garantizada de 2 segundos, incluso si el análisis real es más rápido
2. **7 fases visuales claras**: El usuario ve el progreso a través de 7 fases distintas
3. **Delay de 2s antes de Stage 3**: Se espera 2 segundos después de completar todas las fases antes de transicionar
4. **Separación de responsabilidades**: La lógica de negocio (orchestrator) está completamente separada de la UI

## 🔄 Arquitectura del Sistema

### 1. Fases del Análisis

El análisis se divide en **7 fases visuales**:

| # | ID | Descripción | Servicios involucrados |
|---|---|---|---|
| 1 | `scan` | Escaneo de archivos | Escaneo recursivo del directorio |
| 2 | `renaming` | Análisis de nombres | `FileRenamer` |
| 3 | `live_photos` | Detección de Live Photos | `LivePhotoDetector` |
| 4 | `heic` | Duplicados HEIC/JPG | `HEICRemover` |
| 5 | `duplicates` | Duplicados exactos | `DuplicateDetector` |
| 6 | `organization` | Análisis de organización | `FileOrganizer` |
| 7 | `finalizing` | Finalizando análisis | Post-procesamiento |

### 2. Flujo de Datos

```
┌─────────────────┐
│  Stage2Window   │  (UI)
│  - Muestra fases│
│  - Recibe señales│
└────────┬────────┘
         │
         │ Señales Qt (phase_update, phase_completed)
         ▼
┌─────────────────┐
│ AnalysisWorker  │  (QThread)
│  - Gestiona timing mínimo (2s/fase)
│  - Emite señales Qt
│  - Delay de 2s final
└────────┬────────┘
         │
         │ Callbacks Python
         ▼
┌──────────────────┐
│AnalysisOrchestrator│  (Lógica pura)
│  - Coordina servicios
│  - Registra timestamps
│  - Sin dependencias Qt
└──────────────────┘
```

### 3. Clases de Datos

#### `PhaseTimingInfo`
Información de timing de cada fase:
```python
@dataclass
class PhaseTimingInfo:
    phase_id: str          # ID único de la fase
    phase_name: str        # Nombre descriptivo
    start_time: float      # Timestamp de inicio
    end_time: float        # Timestamp de fin
    duration: float        # Duración real en segundos
    
    def needs_delay(self, min_duration: float = 2.0) -> float:
        """Calcula si necesita delay para alcanzar duración mínima"""
```

#### `FullAnalysisResult`
Resultado completo del análisis:
```python
@dataclass
class FullAnalysisResult:
    directory: Path
    scan: DirectoryScanResult
    phase_timings: Dict[str, PhaseTimingInfo]  # ← NUEVO
    renaming: Optional[Any] = None
    live_photos: Optional[Dict] = None
    organization: Optional[Any] = None
    heic: Optional[Any] = None
    duplicates: Optional[Any] = None
    total_duration: float = 0.0  # ← NUEVO
```

## 🔧 Componentes Modificados

### 1. `AnalysisOrchestrator` (services/)

**Cambios principales:**
- Importa `time` para registrar timestamps
- Crea `PhaseTimingInfo` para cada fase
- Almacena timings en `phase_timings` dict
- Calcula `total_duration` del análisis completo
- Emite `phase_callback(phase_id)` con IDs simples (sin emojis)

**Ejemplo de código:**
```python
# Fase 1: Escaneo inicial
if phase_callback:
    phase_callback("scan")  # ← ID simple

phase_start = time.time()
scan_result = self.scan_directory(directory, progress_callback)
phase_end = time.time()

result.phase_timings['scan'] = PhaseTimingInfo(
    phase_id='scan',
    phase_name='Escaneo de archivos',
    start_time=phase_start,
    end_time=phase_end,
    duration=phase_end - phase_start
)
```

### 2. `AnalysisWorker` (ui/)

**Cambios principales:**
- Nueva señal: `phase_completed = pyqtSignal(str)`
- Constante: `MIN_PHASE_DURATION = 2.0` segundos
- Método: `_ensure_min_phase_duration()` aplica delay si necesario
- Delay final de 2s antes de emitir `finished`

**Flujo de timing:**
```python
def phase_callback(phase_id: str):
    # Completar fase anterior con delay mínimo
    if self.phase_timings:
        last_phase_id = list(self.phase_timings.keys())[-1]
        last_timing = self.phase_timings[last_phase_id]
        self._ensure_min_phase_duration(last_phase_id, last_timing['duration'])
        self.phase_completed.emit(last_phase_id)
    
    # Iniciar nueva fase
    self.phase_timings[phase_id] = {
        'start_time': time.time(),
        'duration': 0.0
    }
    self.phase_update.emit(phase_id)
```

### 3. `Stage2Window` (ui/stages/)

**Cambios principales:**
- Eliminado sistema de `phase_timers` (ahora el worker gestiona timing)
- Nuevos callbacks: `_on_phase_started()` y `_on_phase_completed()`
- Transición inmediata a Stage 3 (el delay ya se aplicó en worker)

**Callbacks simplificados:**
```python
def _on_phase_started(self, phase_id: str):
    """Marca fase como 'running'"""
    self.phase_widget.set_phase_status(phase_id, 'running')
    self.current_phase = phase_id

def _on_phase_completed(self, phase_id: str):
    """Marca fase como 'completed' (timing ya aplicado)"""
    self.phase_widget.set_phase_status(phase_id, 'completed')

def _on_analysis_finished(self, results):
    """Transición inmediata (delay de 2s ya aplicado en worker)"""
    self.save_analysis_results(results)
    self.main_window._transition_to_state_3(results)
```

### 4. `AnalysisPhaseWidget` (ui/widgets/)

**Cambios principales:**
- 7 fases en lugar de 4
- Nuevo estado: `'error'` con icono y color rojo
- Método: `reset_all_phases()` para reintentar análisis

**Fases definidas:**
```python
phases = [
    ("scan", "Escaneando archivos del directorio..."),
    ("renaming", "Analizando nombres de archivos..."),
    ("live_photos", "Detectando Live Photos..."),
    ("heic", "Buscando duplicados HEIC/JPG..."),
    ("duplicates", "Identificando duplicados exactos..."),
    ("organization", "Analizando estructura de carpetas..."),
    ("finalizing", "Finalizando análisis...")
]
```

## 📊 Formato de Resultados

Los resultados del análisis se guardan con esta estructura:

```python
{
    'stats': {
        'total': 1234,
        'images': 890,
        'videos': 234,
        'others': 110
    },
    'renaming': RenameAnalysisResult,
    'live_photos': {
        'groups': [...],
        'total_space': ...,
        'space_to_free': ...,
        'live_photos_found': ...
    },
    'heic': HEICAnalysisResult,
    'duplicates': DuplicateAnalysisResult,
    'organization': OrganizationAnalysisResult,
    'phase_timings': {
        'scan': {
            'phase_id': 'scan',
            'phase_name': 'Escaneo de archivos',
            'duration': 0.5,
            'start_time': ...,
            'end_time': ...
        },
        # ... resto de fases
    },
    'total_duration': 15.7  # segundos totales
}
```

## ⏱️ Gestión de Timing

### Sistema de Timing Mínimo

Cada fase tiene un **timing mínimo garantizado de 2 segundos**:

1. **Orchestrator** registra `start_time` y `end_time` de cada fase
2. **Worker** calcula la duración real: `duration = end_time - start_time`
3. **Worker** aplica delay si necesario: `if duration < 2.0: sleep(2.0 - duration)`
4. **Worker** emite `phase_completed` solo después de aplicar el delay

### Delay Final

Después de completar todas las fases:
1. Worker completa la última fase con timing mínimo
2. Worker espera **2 segundos adicionales**: `time.sleep(2.0)`
3. Worker emite `finished` con resultados completos
4. Stage2Window transiciona inmediatamente a Stage 3

**Ventaja:** El usuario siempre ve todas las fases completadas durante al menos 2 segundos antes de cambiar de pantalla.

## 🧪 Testing

Para probar el sistema de timing:

```python
# Test con carpeta pequeña (análisis rápido)
# Debería tomar al menos 14 segundos (7 fases × 2s)
orchestrator = AnalysisOrchestrator()
result = orchestrator.run_full_analysis(
    Path("/path/to/small/folder"),
    renamer=FileRenamer(),
    # ... resto de servicios
)

# Verificar timings
for phase_id, timing in result.phase_timings.items():
    print(f"{phase_id}: {timing.duration:.2f}s")
    assert timing.duration >= 2.0  # Con el delay aplicado en worker
```

## 🔄 Compatibilidad con Stage 3

El Stage 3 sigue funcionando sin cambios:
- Recibe `analysis_results` como siempre (formato dict)
- Accede a `stats`, `live_photos`, `heic`, `duplicates`, etc.
- Campos nuevos (`phase_timings`, `total_duration`) disponibles pero opcionales

## 📝 Notas Importantes

1. **No emojis en phase_id**: Los phase_id son strings simples (`'scan'`, `'renaming'`) sin emojis para evitar problemas de encoding
2. **Timing en Worker, no en Stage**: El timing mínimo se aplica en el worker (capa Qt), no en el orchestrator (lógica pura)
3. **Delay final obligatorio**: Siempre hay 2 segundos de espera antes de ir a Stage 3
4. **Logs detallados**: El orchestrator y worker generan logs con timing info para debugging

## 🚀 Mejoras Implementadas

- [x] **Timing configurable en config.py**: Ahora se puede ajustar `MIN_PHASE_DURATION_SECONDS` y `FINAL_DELAY_BEFORE_STAGE3_SECONDS` en `config.py`
- [x] **Barra de progreso real para fase de escaneo**: La fase de escaneo ahora muestra progreso real (X de Y archivos) con barra de progreso y porcentaje
- [x] **Corrección de cards en Stage 3**: Arreglado problema que mostraba "realizando análisis" - ahora muestra datos reales de Live Photos, HEIC y duplicados

## 🚀 Mejoras Futuras Posibles

- [ ] Timing configurable por usuario en UI de settings (slider 1-5s)
- [ ] Animaciones entre cambios de fase
- [ ] Cancelación más granular (por fase)
- [ ] Timing adaptativo basado en tamaño del directorio
- [ ] Barra de progreso para otras fases largas (duplicados, hashing)
