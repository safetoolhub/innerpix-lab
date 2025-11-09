# Fix: Cancelación de Análisis con Muchos Archivos

## Problema Identificado

Al analizar directorios con muchos archivos (50,000+), específicamente en la fase de Live Photos, la aplicación se quedaba colgada cuando el usuario intentaba cancelar el análisis.

### Causas Raíz

#### 1. **Servicios sin verificación de cancelación**
Varios servicios NO verificaban el valor de retorno del `progress_callback` para detectar solicitudes de cancelación:

- ❌ `LivePhotoDetector.detect_in_directory()` - Ignoraba el retorno del callback
- ❌ `HEICRemover.analyze_heic_duplicates()` - Ignoraba el retorno del callback  
- ❌ `FileOrganizer.analyze_directory_structure()` - Ignoraba el retorno del callback en múltiples puntos

**Estado de otros servicios:**
- ✅ `FileRenamer.analyze_directory()` - Ya verificaba correctamente (usa `safe_progress_callback`)
- ✅ `ExactCopiesDetector.analyze_exact_duplicates()` - Ya verificaba correctamente (usa `safe_progress_callback`)
- ✅ `AnalysisOrchestrator.scan_directory()` - Ya verificaba correctamente

#### 2. **Stage2 sin timeout en `worker.wait()`**
El método `_cancel_and_return_to_stage_1()` y `cleanup()` en `Stage2Window` usaban `worker.wait()` sin timeout, lo que provocaba bloqueos indefinidos si el worker no respondía inmediatamente.

```python
# ANTES (código problemático)
self.analysis_worker.stop()
self.analysis_worker.wait()  # ⚠️ Puede colgarse indefinidamente
```

### Comportamiento Esperado del Callback

El `progress_callback` debe seguir este contrato:

```python
def progress_callback(current: int, total: int, message: str) -> bool:
    """
    Retorna:
        - True: Continuar procesamiento
        - False: CANCELAR procesamiento inmediatamente
    """
```

Cuando el worker detecta `_stop_requested = True`, el callback retorna `False` para señalizar la cancelación a los servicios.

## Soluciones Implementadas

### 1. LivePhotoDetector - Verificación de cancelación

**Archivo:** `services/live_photo_detector.py`

**Problema adicional encontrado:** Con datasets grandes (47,000 archivos: 30,853 fotos + 13,863 videos), el método `_detect_live_photos()` procesaba todas las fotos sin reportar progreso ni verificar cancelación, causando la impresión de que la app estaba colgada.

**Problemas específicos:**
1. No reportaba progreso durante el matching (fase más lenta)
2. Logs DEBUG excesivos (30,853+ líneas) ralentizaban el procesamiento
3. No verificaba cancelación en el bucle de matching
4. El callback no se pasaba al método interno `_detect_live_photos()`

```python
# ANTES - detect_in_directory()
for file_path in all_files:
    if progress_callback:
        progress_callback(processed, total_files, "Detectando Live Photos")
    
    ext = file_path.suffix.upper()
    self.logger.debug(f"Analizando archivo: {file_path.name} con extensión {ext}")  # ⚠️ 47k logs!
    
    if ext in self.photo_extensions:
        self.logger.debug(f"Encontrada foto: {file_path.name}")  # ⚠️ 30k logs!
        photos.append(file_path)
    # ...

# ANTES - _detect_live_photos() sin progreso ni cancelación
def _detect_live_photos(self, photos: List[Path], videos: List[Path]) -> List[LivePhotoGroup]:
    groups = []
    video_map = defaultdict(list)
    for video in videos:
        normalized_name = self._normalize_name(video.stem)
        video_map[normalized_name].append(video)
        self.logger.debug(f"Video registrado...")  # ⚠️ 13k logs!

    for photo in photos:  # ⚠️ 30k iteraciones sin progreso ni cancelación!
        normalized_name = self._normalize_name(photo.stem)
        self.logger.debug(f"Buscando video para foto...")  # ⚠️ 30k logs!
        # ... matching lento sin feedback ...

# DESPUÉS - detect_in_directory()
self.logger.info(f"Escaneando {total_files} archivos para detectar Live Photos")

for file_path in all_files:
    if progress_callback:
        # Si el callback retorna False, el usuario canceló - detener inmediatamente
        if not progress_callback(processed, total_files, "Detectando Live Photos"):
            self.logger.info("Detección de Live Photos cancelada por el usuario")
            return []  # Retornar lista vacía al cancelar
    
    ext = file_path.suffix.upper()
    # ✅ Logs DEBUG eliminados para archivos individuales
    
    if ext in self.photo_extensions:
        photos.append(file_path)
    # ...

self.logger.info(f"Encontrados: {len(photos)} fotos, {len(videos)} videos")
self.logger.info("Iniciando matching de Live Photos...")

# Pasar callback al método interno
groups = self._detect_live_photos(photos, videos, progress_callback)

if groups is None:  # Cancelación durante matching
    return []

# DESPUÉS - _detect_live_photos() con progreso y cancelación
def _detect_live_photos(self, photos: List[Path], videos: List[Path], 
                       progress_callback=None) -> List[LivePhotoGroup]:
    """Ahora acepta callback y reporta progreso"""
    groups = []
    total_photos = len(photos)
    
    self.logger.info(f"Construyendo mapa de videos ({len(videos)} videos)...")
    
    # Crear mapa sin logs excesivos
    video_map = defaultdict(list)
    for video in videos:
        normalized_name = self._normalize_name(video.stem)
        video_map[normalized_name].append(video)

    self.logger.info(f"Mapa de videos construido con {len(video_map)} nombres únicos")
    self.logger.info(f"Procesando {total_photos} fotos para matching...")

    # Matching con progreso cada 1000 fotos
    for idx, photo in enumerate(photos, 1):
        # ✅ Reportar progreso cada 1000 fotos
        if idx % 1000 == 0:
            self.logger.info(
                f"Procesadas {idx}/{total_photos} fotos, "
                f"{len(groups)} Live Photos encontrados hasta ahora"
            )
            
            # ✅ Verificar cancelación
            if progress_callback:
                if not progress_callback(idx, total_photos, "Matching Live Photos"):
                    self.logger.info("Matching de Live Photos cancelado por el usuario")
                    return None  # Señal de cancelación
        
        # Matching sin logs DEBUG
        normalized_name = self._normalize_name(photo.stem)
        if normalized_name in video_map:
            # ... crear grupos ...

    self.logger.info(f"Matching completado: {len(groups)} Live Photos encontrados")
    return groups
```

**Beneficio:** 
- Con 47,000 archivos: El usuario ve progreso cada 1000 fotos (47 actualizaciones)
- Logs limpios: Solo 5-10 líneas INFO en lugar de 70,000+ líneas DEBUG
- Cancelación: Verificada cada 1000 fotos en la fase de matching
- Performance: Sin sobrecarga de I/O por logging excesivo

### 2. HEICRemover - Verificación de cancelación

**Archivo:** `services/heic_remover.py`

```python
# ANTES
for file_path in all_files:
    if progress_callback:
        progress_callback(processed, total_files, "Analizando HEIC/JPG duplicados")
    # ... procesar archivo ...

# DESPUÉS
for file_path in all_files:
    if progress_callback:
        if not progress_callback(processed, total_files, "Analizando HEIC/JPG duplicados"):
            self.logger.info("Análisis de HEIC/JPG cancelado por el usuario")
            # Retornar resultado vacío al cancelar
            return {
                'directory': directory,
                'duplicate_pairs': [],
                # ... estructura vacía completa ...
            }
    # ... procesar archivo ...
```

### 3. FileOrganizer - Verificación de cancelación en múltiples bucles

**Archivo:** `services/file_organizer.py`

Este servicio tiene **3 puntos de verificación** porque usa `ThreadPoolExecutor` en varios lugares:

```python
# Punto 1: Procesar archivos de raíz (con ThreadPoolExecutor)
for future in as_completed(futures):
    processed_files += 1
    if progress_callback:
        if not progress_callback(processed_files, total_files, "Analizando estructura..."):
            self.logger.info("Análisis de organización cancelado por el usuario")
            executor.shutdown(wait=False, cancel_futures=True)  # ⚠️ Importante!
            return OrganizationAnalysisResult(success=False, ...)

# Punto 2: Procesar archivos de raíz (sin ThreadPoolExecutor)
if progress_callback:
    if not progress_callback(processed_files, total_files, "Analizando estructura..."):
        return OrganizationAnalysisResult(success=False, ...)

# Punto 3: Procesar subdirectorios (con ThreadPoolExecutor)
for future in as_completed(futures):
    processed_files += 1
    if progress_callback:
        if not progress_callback(processed_files, total_files, "Analizando estructura..."):
            executor.shutdown(wait=False, cancel_futures=True)
            return OrganizationAnalysisResult(success=False, ...)
```

**Nota importante:** Al cancelar con `ThreadPoolExecutor` activo, se debe llamar a `executor.shutdown(wait=False, cancel_futures=True)` para detener las tareas pendientes.

### 4. Stage2Window - Timeout en `worker.wait()`

**Archivo:** `ui/stages/stage_2_window.py`

#### Método `_cancel_and_return_to_stage_1()`:

```python
# ANTES
if self.analysis_worker and self.analysis_worker.isRunning():
    self.analysis_worker.stop()
    self.analysis_worker.wait()  # ⚠️ Puede colgarse indefinidamente

# DESPUÉS
if self.analysis_worker and self.analysis_worker.isRunning():
    self.analysis_worker.stop()
    
    # Esperar con timeout para evitar bloqueos indefinidos
    if not self.analysis_worker.wait(5000):  # 5 segundos de timeout
        self.logger.warning("Worker no respondió en 5 segundos, terminando forzosamente")
        self.analysis_worker.terminate()
        # Esperar un poco más después de terminate
        self.analysis_worker.wait(1000)
    else:
        self.logger.info("Worker detenido correctamente")
```

#### Método `cleanup()`:

```python
# ANTES
if self.analysis_worker and self.analysis_worker.isRunning():
    self.analysis_worker.stop()
    self.analysis_worker.wait()

# DESPUÉS
if self.analysis_worker and self.analysis_worker.isRunning():
    self.logger.info("Deteniendo worker durante cleanup...")
    self.analysis_worker.stop()
    
    # Esperar con timeout para evitar bloqueos indefinidos
    if not self.analysis_worker.wait(5000):  # 5 segundos de timeout
        self.logger.warning("Worker no respondió durante cleanup, terminando forzosamente")
        self.analysis_worker.terminate()
        self.analysis_worker.wait(1000)
    else:
        self.logger.info("Worker detenido correctamente durante cleanup")
```

**Beneficio:** Si un servicio no responde, la UI no se congela indefinidamente. Después de 5 segundos se fuerza la terminación.

## Flujo de Cancelación Completo

```
Usuario presiona "Cancelar"
    ↓
Stage2Window._on_cancel_requested()
    ↓
Muestra diálogo de confirmación
    ↓
Usuario confirma "Seleccionar otra carpeta"
    ↓
Stage2Window._cancel_and_return_to_stage_1()
    ↓
analysis_worker.stop()  (marca _stop_requested = True)
    ↓
BaseWorker._create_progress_callback() retorna False
    ↓
Servicio (LivePhotoDetector/HEICRemover/FileOrganizer) detecta False
    ↓
Servicio detiene procesamiento y retorna resultado vacío
    ↓
Worker termina naturalmente
    ↓
Stage2Window espera max 5s con timeout
    ↓
Si no responde: worker.terminate() forzoso
    ↓
Transición a Stage1 completada
```

## Testing

### Escenario de Prueba

1. **Dataset:** Directorio con 50,000 archivos mixtos (imágenes/videos)
2. **Fase crítica:** Live Photos (fase más lenta por patrón de matching)
3. **Acción:** Presionar "Cancelar" durante la fase de Live Photos
4. **Resultado esperado:**
   - Cancelación detectada en < 1 segundo
   - Worker termina en < 5 segundos
   - UI permanece responsiva
   - Transición a Stage1 exitosa

### Comandos de Testing

```bash
# Ejecutar aplicación en modo debug
source .venv/bin/activate
python main.py

# Logs detallados en:
~/Documents/Pixaro_Lab/logs/pixaro_lab_YYYYMMDD_HHMMSS.log
```

Buscar en logs:
- `"Detección de Live Photos cancelada por el usuario"` - Servicio detectó cancelación
- `"Worker no respondió en 5 segundos"` - Timeout alcanzado (solo si hay problemas)
- `"Worker detenido correctamente"` - Terminación exitosa

## Archivos Modificados

- ✅ `services/live_photo_detector.py` - Añadida verificación de cancelación
- ✅ `services/heic_remover.py` - Añadida verificación de cancelación
- ✅ `services/file_organizer.py` - Añadidas 3 verificaciones de cancelación
- ✅ `ui/stages/stage_2_window.py` - Añadidos timeouts en `wait()` (2 métodos)

## Servicios Verificados (Ya Correctos)

- ✅ `services/file_renamer.py` - Usa `safe_progress_callback`
- ✅ `services/exact_copies_detector.py` - Usa `safe_progress_callback`
- ✅ `services/analysis_orchestrator.py` - Verifica retorno del callback
- ✅ `ui/workers.py` - `BaseWorker._create_progress_callback()` maneja correctamente `_stop_requested`

## Mejoras Futuras (Opcional)

1. **Progreso granular en ThreadPoolExecutor**: Actualmente se reporta cada archivo, pero con 50k archivos podría optimizarse a cada N archivos.

2. **Callback timeout interno**: Añadir timeout dentro de los servicios para detectar si el callback tarda demasiado (señal de UI congelada).

3. **Tests unitarios de cancelación**: Crear tests automatizados que verifiquen la cancelación en cada servicio.

## Referencias

- `docs/LOGGING_CONVENTIONS.md` - Convenciones de logging usadas
- `utils/callback_utils.py` - Utilidad `safe_progress_callback` para pattern consistente
- `ui/workers.py` - Implementación de `BaseWorker` y manejo de `_stop_requested`

---

## Fix Adicional: LivePhotoDetector Aparentemente Colgado (47k archivos)

### Problema Reportado

```
Usuario: "la fase de análisis de live photos llega hasta el ultimo archivo pero no acaba. 
No continua con la siguiente fase (con 47000 archivos)."

Log:
2025-11-09 17:02:11,124 - LivePhotoDetector - INFO - Detectando Live Photos en: /path
2025-11-09 17:02:15,520 - LivePhotoDetector - INFO - Encontrados: 30853 fotos, 13863 videos
[... silencio total, app parece colgada ...]
```

### Diagnóstico

El detector **no estaba colgado**, estaba procesando **30,853 fotos** en el método `_detect_live_photos()` sin reportar progreso. Con el matching de nombres normalizados, esto toma varios minutos sin feedback visual.

**Problemas identificados:**

1. **Sin progreso en fase crítica**: El método `_detect_live_photos()` no aceptaba `progress_callback`
2. **Logs DEBUG excesivos**: 70,000+ líneas de DEBUG ralentizaban I/O del disco
   - Cada foto: `"Analizando archivo: X con extensión Y"` (30,853 logs)
   - Cada foto: `"Encontrada foto: X"` (30,853 logs)
   - Cada video: `"Video registrado: X con nombre normalizado: Y"` (13,863 logs)
3. **Sin verificación de cancelación** en el bucle de matching más lento

### Solución Implementada

#### 1. Eliminación de logs DEBUG excesivos

```python
# ANTES: 70,000+ líneas de log
for file_path in all_files:
    ext = file_path.suffix.upper()
    self.logger.debug(f"Analizando archivo: {file_path.name} con extensión {ext}")
    if ext in self.photo_extensions:
        self.logger.debug(f"Encontrada foto: {file_path.name}")
        photos.append(file_path)

# DESPUÉS: Solo logs agregados informativos
self.logger.info(f"Escaneando {total_files} archivos para detectar Live Photos")
# ... bucle sin logs individuales ...
self.logger.info(f"Encontrados: {len(photos)} fotos, {len(videos)} videos")
```

#### 2. Añadido progreso cada 1000 fotos en matching

```python
# ANTES: Sin progreso en _detect_live_photos()
def _detect_live_photos(self, photos: List[Path], videos: List[Path]):
    # ... 30,853 iteraciones sin feedback ...

# DESPUÉS: Progreso cada 1000 fotos
def _detect_live_photos(self, photos: List[Path], videos: List[Path], progress_callback=None):
    self.logger.info(f"Construyendo mapa de videos ({len(videos)} videos)...")
    # ... construir video_map ...
    
    self.logger.info(f"Procesando {total_photos} fotos para matching...")
    
    for idx, photo in enumerate(photos, 1):
        if idx % 1000 == 0:
            self.logger.info(
                f"Procesadas {idx}/{total_photos} fotos, "
                f"{len(groups)} Live Photos encontrados hasta ahora"
            )
            
            # Verificar cancelación cada 1000 fotos
            if progress_callback:
                if not progress_callback(idx, total_photos, "Matching Live Photos"):
                    return None  # Cancelación
```

#### 3. Logs estructurados informativos

```
# Logs que el usuario ve ahora (ejemplo con 47k archivos):
2025-11-09 17:02:11 - INFO - Escaneando 47690 archivos para detectar Live Photos
2025-11-09 17:02:15 - INFO - Encontrados: 30853 fotos, 13863 videos
2025-11-09 17:02:15 - INFO - Construyendo mapa de videos (13863 videos)...
2025-11-09 17:02:16 - INFO - Mapa de videos construido con 12450 nombres únicos
2025-11-09 17:02:16 - INFO - Procesando 30853 fotos para matching...
2025-11-09 17:02:25 - INFO - Procesadas 1000/30853 fotos, 87 Live Photos encontrados hasta ahora
2025-11-09 17:02:35 - INFO - Procesadas 2000/30853 fotos, 156 Live Photos encontrados hasta ahora
2025-11-09 17:02:45 - INFO - Procesadas 3000/30853 fotos, 234 Live Photos encontrados hasta ahora
...
2025-11-09 17:07:20 - INFO - Procesadas 30000/30853 fotos, 2891 Live Photos encontrados hasta ahora
2025-11-09 17:07:28 - INFO - Matching completado: 2934 Live Photos encontrados
2025-11-09 17:07:28 - INFO - Detectados 2934 grupos de Live Photos
```

### Impacto

**ANTES (47k archivos):**
- Usuario ve: `"Encontrados: 30853 fotos, 13863 videos"` → **silencio total por 5-10 minutos**
- Logs: 70,000+ líneas DEBUG ralentizan I/O
- Usuario piensa: "¿Está colgada la app?"
- No puede cancelar porque no hay verificación en el bucle crítico

**DESPUÉS (47k archivos):**
- Usuario ve progreso cada 1000 fotos (30 actualizaciones durante el matching)
- Logs: ~10-15 líneas INFO limpias y útiles
- Tiempo estimado visible: "Procesadas X/30853 fotos"
- Puede cancelar cada 1000 fotos si lo desea

### Tiempo de Procesamiento Esperado

Con 30,853 fotos y 13,863 videos:
- **Construcción de mapa:** ~1 segundo
- **Matching por foto:** ~0.01 segundos (lookup en dict + comparación de paths)
- **Total estimado:** 30,853 × 0.01s = **~5 minutos**
- **Progreso reportado:** Cada 10 segundos aprox (1000 fotos)

**Conclusión:** El proceso es largo pero **no está colgado**. Ahora el usuario lo sabe porque ve progreso constante.
