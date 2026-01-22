# Plan de Refactorización: Duplicados Similares

**Fecha**: Enero 2025  
**Estado**: Pendiente de validación

---

## 1. Resumen del Problema

La funcionalidad de detección de archivos similares (`duplicates_similar`) tiene múltiples problemas:

### 1.1 Problemas de Arquitectura
- **Flujo de análisis diferente al resto de tools**: Usa un handler separado (`SimilarityAnalysisHandler`) y un diálogo de progreso dedicado (`SimilarFilesProgressDialog`), cuando todas las demás tools siguen el patrón unificado de `_run_analysis_and_open_dialog()`.
- **Acoplamiento excesivo**: El `SimilarityAnalysisHandler` tiene lógica que debería estar en el servicio o en stage_3.

### 1.2 Problemas de UX
- **Sistema de batches confuso**: El sistema de carga progresiva no funciona correctamente y confunde al usuario.
- **Slider de sensibilidad sin contexto claro**: El usuario no entiende qué significa 30% vs 100%.
- **Falta modo automático seguro**: No hay forma de eliminar rápidamente archivos visualmente idénticos (100% similitud) de forma automática.
- **Grupos vacíos según sensibilidad**: Al cambiar sensibilidad, a veces aparece vacío sin explicación.

### 1.3 Problemas Técnicos
- **Configuración de algoritmo perceptual no utilizada correctamente**: Los parámetros en `Config` están definidos pero el usuario no los controla.
- **No hay verificación de datos EXIF requeridos**: Si se necesitan fechas EXIF para ordenar duplicados, no se valida que estén en caché.

---

## 2. Propuesta de Solución

### 2.1 Separar en DOS Herramientas Independientes

En lugar de una única tool compleja, crear dos tools separadas y claras:

#### **Tool A: "Copias Visuales Idénticas"** (Nueva)
- **Propósito**: Detectar archivos que son visualmente IDÉNTICOS al 100% (aunque tengan metadatos o resolución diferente).
- **Casos de uso**: Fotos enviadas por WhatsApp, copias redimensionadas, screenshots repetidos.
- **Flujo**:
  1. Análisis con sensibilidad 100% (automático, sin slider)
  2. Mostrar TreeView con grupos de archivos idénticos (similar a `duplicates_exact_dialog`)
  3. Estrategias automáticas: "Conservar mejor calidad", "Conservar más antiguo", "Conservar más reciente"
  4. Ejecución masiva sin necesidad de revisar uno a uno
- **UI**: Similar a `DuplicatesExactDialog` con TreeView y estrategias

#### **Tool B: "Archivos Similares"** (Refactorizada)  
- **Propósito**: Detectar archivos SIMILARES pero no idénticos (ediciones, recortes, rotaciones).
- **Casos de uso**: Encontrar fotos editadas vs originales, diferentes versiones.
- **Flujo**:
  1. Análisis completo de hashes perceptuales
  2. Slider de sensibilidad (70-99%) para ajustar detección
  3. Navegación por grupos para revisar y decidir manualmente
  4. Selección individual dentro de cada grupo
- **UI**: Mantener navegación visual por grupos

### 2.2 Unificar el Flujo de Análisis con Otras Tools

Eliminar `SimilarityAnalysisHandler` y el tratamiento especial en stage_3. Usar el mismo patrón que `duplicates_exact`, `live_photos`, etc.:

```python
# En stage_3_window._on_tool_clicked():
elif tool_id == 'visual_identical':
    should_analyze = True  # Siempre analizar
elif tool_id == 'duplicates_similar':
    should_analyze = True  # Siempre analizar
```

### 2.3 Simplificar el Servicio

**Separar en dos servicios**:
1. `VisualIdenticalService` - Solo sensibilidad 100%, optimizado
2. `DuplicatesSimilarService` - Rango 70-99%, para similares no idénticos

O alternativamente, mantener un único servicio pero con dos métodos de análisis claros:
- `analyze_identical()` → Para Tool A
- `analyze_similar(sensitivity)` → Para Tool B

### 2.4 Eliminar Sistema de Batches en UI

El problema del sistema de batches:
- Es confuso para el usuario ("Cargar más grupos")
- Genera grupos vacíos según sensibilidad
- La lógica de `find_new_groups()` es innecesariamente compleja

**Solución**: Hacer clustering completo en el servicio y cargar todos los grupos en el diálogo. Para datasets muy grandes (>50K archivos), mostrar advertencia y usar paginación simple (no batches incrementales).

### 2.5 Validación de Datos EXIF Necesarios

Antes de abrir el diálogo de similares, verificar si los datos necesarios están en caché:

```python
def _validate_required_data(self) -> bool:
    """Verifica que los datos necesarios estén en caché."""
    repo = FileInfoRepositoryCache.get_instance()
    
    # Para ordenar por fecha necesitamos EXIF de imágenes
    if not settings_manager.get_bool(SettingsManager.KEY_PRECALCULATE_IMAGE_EXIF):
        # Mostrar diálogo: "Para ordenar por fecha se necesitan metadatos EXIF"
        # Ofrecer: [Ir a Settings] [Continuar sin fechas]
        return False
    return True
```

---

## 3. Plan de Implementación Detallado

### Fase 1: Crear Nueva Tool "Copias Visuales Idénticas"

#### 1.1 Nuevo Servicio (o método)
```
services/visual_identical_service.py
```
- Reutiliza la lógica de hash perceptual existente
- Fija sensibilidad al 100% (threshold = 0)
- Retorna `VisualIdenticalAnalysisResult` con grupos

#### 1.2 Nuevo Diálogo
```
ui/dialogs/visual_identical_dialog.py
```
- Basado en `DuplicatesExactDialog` (TreeView con grupos)
- Columnas: Archivo, Tamaño, Resolución, Fecha, Origen, Ubicación
- Estrategias: keep_largest, keep_smallest, keep_oldest, keep_newest
- Checkbox de selección por grupo
- Sin slider de sensibilidad

#### 1.3 Nueva Tool Card
```
ui/screens/tool_cards/visual_identical_card.py
```
- Icono: 'image-multiple' o 'content-copy'
- Título: "Copias Visuales Idénticas"
- Descripción: "Detecta fotos idénticas visualmente aunque tengan diferente resolución o metadatos"

#### 1.4 Nuevo Worker
```
ui/workers/analysis_workers.py
```
- `VisualIdenticalAnalysisWorker` siguiendo el patrón existente

### Fase 2: Refactorizar Tool "Archivos Similares"

#### 2.1 Simplificar Servicio
- Eliminar `_cached_analysis` y usar siempre análisis fresco (o manejado por stage_3)
- Eliminar `find_new_groups()` - ya no se necesita batches
- Mantener `get_analysis_for_dialog()` pero simplificado

#### 2.2 Refactorizar Diálogo
- Eliminar sistema de batches (`_load_next_batch`, `batch_size`, etc.)
- Simplificar: cargar todos los grupos al inicio
- Mantener slider de sensibilidad (70-99%)
- Mantener navegación visual por grupos
- Añadir filtro de sensibilidad mínima (ej: solo mostrar >80%)

#### 2.3 Eliminar Handler Separado
- Borrar `ui/screens/similarity_handlers.py`
- Mover la lógica necesaria a `stage_3_window.py` usando el patrón unificado

### Fase 3: Unificar Flujo en Stage 3

#### 3.1 Modificar `stage_3_window.py`
- Eliminar importación y uso de `SimilarityAnalysisHandler`
- Añadir `visual_identical` y `duplicates_similar` al `worker_map`
- Usar el mismo patrón `_run_analysis_and_open_dialog()` para ambas

#### 3.2 Actualizar Grid de Tools
- Añadir nueva card "Copias Visuales Idénticas" en sección "Limpieza y Espacio"
- Mover "Archivos Similares" a sección propia o renombrar sección

### Fase 4: Validación de Datos y Mensajes

#### 4.1 Verificación de EXIF
- Antes de abrir diálogo, verificar configuración de análisis
- Mostrar mensaje si faltan datos necesarios
- Ofrecer ir a Settings o continuar

#### 4.2 Mensajes Claros al Usuario
- "0 grupos encontrados" → Explicar por qué
- Mostrar número de archivos analizados vs grupos encontrados
- Indicar tiempo estimado de análisis

### Fase 5: Limpieza y Documentación

#### 5.1 Eliminar Código Obsoleto
- `ui/screens/similarity_handlers.py` (completo)
- `ui/dialogs/duplicates_similar_progress_dialog.py` (reemplazar por QProgressDialog estándar)
- Sistema de batches en `duplicates_similar_dialog.py`

#### 5.2 Actualizar Documentación
- `copilot-instructions.md`
- `AGENTS.md`
- Tests obsoletos en `tests/`

---

## 4. Estructura de Archivos Final

### Archivos Nuevos
```
services/visual_identical_service.py          # Nuevo servicio
ui/dialogs/visual_identical_dialog.py         # Nuevo diálogo
ui/screens/tool_cards/visual_identical_card.py # Nueva card
```

### Archivos Modificados
```
services/duplicates_similar_service.py        # Simplificado
ui/dialogs/duplicates_similar_dialog.py       # Sin batches
ui/screens/stage_3_window.py                  # Flujo unificado
ui/screens/tool_cards/__init__.py             # Exportar nueva card
ui/workers/analysis_workers.py                # Nuevo worker
config.py                                     # Ajustar constantes
.github/copilot-instructions.md               # Documentación
AGENTS.md                                     # Documentación
```

### Archivos a Eliminar
```
ui/screens/similarity_handlers.py             # Handler obsoleto
ui/dialogs/duplicates_similar_progress_dialog.py  # Usar QProgressDialog estándar
```

---

## 5. Consideraciones Técnicas

### 5.1 Rendimiento para >100K Archivos
- El cálculo de hashes perceptuales es O(N), ~5min para 40K archivos
- El clustering con BK-Tree es O(N log N), muy rápido
- Para datasets muy grandes, mostrar advertencia y progreso claro

### 5.2 Memoria
- Los hashes perceptuales ocupan poco espacio (~100 bytes/archivo)
- El problema de memoria está en la UI al mostrar muchos grupos
- Solución: Paginación simple (no batches incrementales)

### 5.3 Algoritmo Perceptual
- Usar configuración de `Config` (phash/dhash/ahash)
- No exponer al usuario la selección de algoritmo (es técnico)
- Valor por defecto: phash con hash_size=16 (buen balance)

---

## 6. Criterios de Éxito

1. **Funcionalidad**: Ambas tools detectan correctamente los archivos
2. **Usabilidad**: El usuario entiende qué hace cada tool sin ayuda
3. **Consistencia**: El flujo es idéntico al de otras tools (análisis → diálogo)
4. **Rendimiento**: Funciona correctamente con datasets de 100K+ archivos
5. **Mantenibilidad**: Código más simple y siguiendo patrones existentes

---

## 7. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Regresión en detección | Media | Alto | Tests exhaustivos antes de eliminar código |
| Pérdida de funcionalidad batch | Baja | Medio | La paginación simple es más confiable |
| Confusión de usuarios existentes | Media | Bajo | Mantener nombres similares, documentar cambios |

---

## 8. Próximos Pasos

1. **Validar este plan** con el usuario
2. **Fase 1**: Crear nueva tool "Copias Visuales Idénticas"
3. **Fase 2**: Refactorizar "Archivos Similares"
4. **Fase 3**: Unificar flujo en Stage 3
5. **Fase 4**: Validación de datos y mensajes
6. **Fase 5**: Limpieza y documentación
7. **Testing**: Crear nuevos tests desde cero
