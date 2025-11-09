# Sistema de Re-análisis Automático - Implementación

## Estado: ✅ Core Implementado | ⚠️ Integración Pendiente

### Componentes Implementados

#### 1. Constantes de Configuración (`config.py`)
```python
TOOL_ANALYSIS_COST = {
    'live_photos': 'fast',
    'heic': 'fast',
    'exact_duplicates': 'fast',
    'organize': 'fast',
    'rename': 'fast',
    'similar_duplicates': 'expensive'
}

TOOL_IMPACT_ON_FILES = {
    'live_photos': 'destructive',  # Elimina videos o imágenes
    'heic': 'destructive',  # Elimina HEIC
    'exact_duplicates': 'destructive',  # Elimina duplicados
    'organize': 'moves',  # Mueve archivos
    'rename': 'renames',  # Renombra archivos
    'similar_duplicates': 'none'  # Solo muestra, no ejecuta
}

TOOL_DISPLAY_NAMES = {
    'live_photos': 'Live Photos',
    'heic': 'HEIC/JPG',
    'exact_duplicates': 'Duplicados Exactos',
    'organize': 'Organizar',
    'rename': 'Renombrar',
}
```

#### 2. Worker de Re-análisis (`ui/workers.py`)
- ✅ `WorkspaceReanalysisWorker`: Ejecuta análisis rápidos de 5 herramientas
- ✅ Signals: `tool_completed(str, object)`, `tool_error(str, str)`, `finished(dict)`
- ✅ Progreso incremental por herramienta
- ✅ Manejo de errores individual por herramienta

#### 3. Overlay Visual (`ui/widgets/reanalysis_overlay.py`)
- ✅ `ReanalysisOverlay`: Widget semi-transparente no-modal
- ✅ Muestra herramienta actual con icono dinámico
- ✅ Barra de progreso (0-5 herramientas)
- ✅ Animaciones fade in/out
- ✅ 100% DesignSystem styling

#### 4. Lógica de Stage 3 (`ui/stages/stage_3_window.py`)

**Atributos agregados:**
```python
self.reanalysis_worker = None
self.reanalysis_overlay = None
self.similarity_results_snapshot = None
self.similarity_timestamp = None
self.pending_reanalysis = False
```

**Métodos implementados:**

##### Sistema de Re-análisis Automático
- ✅ `_on_tool_action_completed(tool_name)`: Entry point cuando herramienta ejecuta acciones
- ✅ `_trigger_automatic_reanalysis()`: Dispara re-análisis si no hay uno en curso
- ✅ `_start_reanalysis()`: Crea worker y overlay, inicia análisis
- ✅ `_handle_reanalysis_tool_completed(tool_name, result)`: Actualiza UI por herramienta
- ✅ `_update_tool_card_after_reanalysis(tool_name, result)`: Refresca tarjetas individuales
- ✅ `_handle_reanalysis_error(tool_name, error_msg)`: Manejo de errores
- ✅ `_finish_reanalysis(results)`: Cleanup y re-análisis pendientes

##### Sistema de Invalidación de Similar Duplicates
- ✅ `_invalidate_similarity_analysis()`: Guarda snapshot, marca timestamp
- ✅ `_update_similar_files_card_stale()`: Actualiza UI con estado "obsoleto"
- ✅ `_show_stale_results_dialog()`: Diálogo con opciones (ver antiguo/reanalizar/cancelar)
- ✅ Integrado en `_on_similar_duplicates_clicked()`: Maneja flujo de resultados obsoletos
- ✅ Timestamp guardado en `_on_similarity_analysis_completed()`: Limpia snapshot al completar

---

## ⚠️ Integración Pendiente con Diálogos

### Problema Actual

Los diálogos actuales (`LivePhotoCleanupDialog`, `HEICDuplicateRemovalDialog`, etc.) son de **solo visualización**:
- Muestran datos del análisis
- Permiten configurar opciones
- Retornan un `accepted_plan` al aceptar
- ❌ **NO ejecutan acciones directamente**

El sistema de re-análisis espera que los diálogos **ejecuten acciones** y emitan una señal cuando terminan.

### Señal Agregada a BaseDialog

```python
class BaseDialog(QDialog):
    """
    Signals:
        actions_completed(str): Emitida cuando el diálogo ejecuta acciones.
                                Argumento: tool_name identificador de la herramienta.
    """
    actions_completed = pyqtSignal(str)  # tool_name
```

### Integración Futura Necesaria

Para cada diálogo que ejecute acciones (eliminar/mover/renombrar):

1. **Después de ejecutar acciones exitosamente**, emitir:
   ```python
   self.actions_completed.emit('tool_name')
   ```

2. **En Stage3Window**, al crear el diálogo:
   ```python
   dialog = LivePhotoCleanupDialog(...)
   dialog.actions_completed.connect(self._on_tool_action_completed)
   dialog.exec()
   ```

### Diálogos que Necesitan Integración

#### Alta Prioridad (Destructivos)
- [ ] `LivePhotoCleanupDialog` → `'live_photos'`
- [ ] `HEICDuplicateRemovalDialog` → `'heic'`
- [ ] `ExactDuplicatesDialog` → `'exact_duplicates'`

#### Media Prioridad (Modifican estructura)
- [ ] `FileOrganizationDialog` → `'organize'`
- [ ] `RenamingPreviewDialog` → `'rename'`

#### Baja Prioridad (No destructivo)
- [ ] `SimilarDuplicatesDialog` → Probablemente no necesita emitir señal (solo visualiza snapshot)

---

## Flujo Completo del Sistema

### Escenario 1: Usuario ejecuta acción destructiva

1. Usuario abre diálogo Live Photos
2. Configura opciones (eliminar videos, crear backup)
3. Confirma acción
4. **[FUTURO]** Diálogo ejecuta cleanup → emite `actions_completed('live_photos')`
5. Stage3 recibe señal → llama `_on_tool_action_completed('live_photos')`
6. Stage3 invalida similar_duplicates (si existen resultados)
7. Stage3 dispara `_trigger_automatic_reanalysis()`
8. `WorkspaceReanalysisWorker` analiza 5 herramientas rápidas
9. Overlay muestra progreso en tiempo real
10. Tarjetas se actualizan con nuevos resultados

### Escenario 2: Usuario intenta ver similar_duplicates obsoletos

1. Usuario click en tarjeta "Duplicados Similares"
2. Stage3 detecta `similarity_results_snapshot` existe
3. Muestra `_show_stale_results_dialog()` con opciones:
   - **Ver Resultados Antiguos**: Abre diálogo con snapshot
   - **Re-analizar Ahora**: Lanza nuevo análisis de similares
   - **Cancelar**: No hace nada
4. Si re-analiza, limpia snapshot y guarda nuevo timestamp

### Escenario 3: Re-análisis automático en curso

1. Usuario ejecuta acción mientras re-análisis en curso
2. Stage3 marca `pending_reanalysis = True`
3. Cuando re-análisis actual termina, verifica flag
4. Si flag está activo, espera 2 segundos y lanza nuevo re-análisis

---

## Testing Manual

### Pre-requisitos
```bash
# Asegurar que el proyecto compile
python -c "from ui.stages.stage_3_window import Stage3Window; print('✅ Stage3 OK')"
python -c "from ui.widgets.reanalysis_overlay import ReanalysisOverlay; print('✅ Overlay OK')"
python -c "from ui.workers import WorkspaceReanalysisWorker; print('✅ Worker OK')"
```

### Test 1: Overlay Visual
1. Ejecutar app
2. Seleccionar carpeta con fotos
3. Esperar análisis completo
4. **[SIMULACIÓN]** En consola de debug, llamar manualmente:
   ```python
   self.stage3._start_reanalysis()
   ```
5. **Verificar:**
   - ✅ Overlay aparece con fade in
   - ✅ Muestra "Actualizando análisis..."
   - ✅ Barra de progreso avanza de 0/5 a 5/5
   - ✅ Icono de herramienta cambia (Live Photos → HEIC → Duplicados → etc)
   - ✅ Overlay desaparece con fade out después de completar

### Test 2: Invalidación de Similares
1. Ejecutar análisis de similar_duplicates con resultados
2. **[SIMULACIÓN]** Llamar `self.stage3._invalidate_similarity_analysis()`
3. **Verificar:**
   - ✅ Tarjeta de similares muestra "⚠️ Los resultados están desactualizados"
   - ✅ Botón cambia a "Ver resultados antiguos"
   - ✅ Color del texto cambia a warning
4. Click en la tarjeta
5. **Verificar:**
   - ✅ Aparece diálogo con timestamp del análisis anterior
   - ✅ Botones: "Ver Resultados Antiguos", "Re-analizar Ahora", "Cancelar"

### Test 3: Re-análisis Automático (Requiere integración futura)
1. Ejecutar acción en Live Photos (eliminar videos)
2. **Verificar:**
   - ✅ Overlay aparece automáticamente
   - ✅ 5 herramientas se re-analizan
   - ✅ Tarjetas se actualizan con nuevos conteos
   - ✅ Tarjeta de similares marcada como obsoleta

---

## Próximos Pasos

### Sprint Inmediato
1. ✅ Implementar core del sistema de re-análisis
2. ✅ Crear overlay visual
3. ✅ Agregar lógica de invalidación
4. ⚠️ **Pendiente:** Refactorizar diálogos para ejecutar acciones y emitir señales

### Sprint Futuro
1. Modificar `LivePhotoCleanupDialog` para ejecutar cleanup con worker
2. Emitir `actions_completed` después de ejecución exitosa
3. Conectar señal en Stage3Window
4. Repetir para HEIC, Duplicados, Organizar, Renombrar
5. Testing end-to-end con acciones reales

---

## Notas de Diseño

### ¿Por qué no modal?
El overlay es **no-modal** para permitir:
- Ver el Stage 3 debajo (tranquilidad visual)
- Interrupción opcional (futuro: botón cancelar)
- UX menos invasiva que un diálogo bloqueante

### ¿Por qué no invalidar herramientas rápidas?
Las 5 herramientas rápidas (<5s cada una):
- **Se re-analizan automáticamente** tras cambios
- **No necesitan snapshot** porque el análisis es instantáneo
- **Siempre muestran datos actualizados**

Solo `similar_duplicates`:
- **Análisis costoso** (puede tomar minutos con muchas fotos)
- **Se invalida** tras cambios destructivos
- **Guarda snapshot** para permitir ver resultados antiguos
- **Usuario decide** si ver antiguo o re-analizar

### Gestión de Re-análisis Concurrentes
Si se disparan múltiples acciones:
1. Primer re-análisis se ejecuta inmediatamente
2. Segundo se marca como `pending_reanalysis = True`
3. Al terminar el primero, se espera 2s y lanza el pendiente
4. Solo se acumula **un** re-análisis pendiente (no cola infinita)

---

## Archivos Modificados

### Nuevos Archivos
- ✅ `ui/widgets/reanalysis_overlay.py` (~310 líneas)

### Archivos Modificados
- ✅ `config.py`: Agregadas 3 constantes (TOOL_ANALYSIS_COST, TOOL_IMPACT_ON_FILES, TOOL_DISPLAY_NAMES)
- ✅ `ui/workers.py`: Agregada clase `WorkspaceReanalysisWorker` (~120 líneas)
- ✅ `ui/stages/stage_3_window.py`: Agregados ~300 líneas de métodos de re-análisis
- ✅ `ui/dialogs/base_dialog.py`: Agregada señal `actions_completed`

### Sin Modificar (Integración Pendiente)
- ⚠️ `ui/dialogs/live_photos_dialog.py`
- ⚠️ `ui/dialogs/heic_dialog.py`
- ⚠️ `ui/dialogs/duplicate_exact_dialog.py`
- ⚠️ `ui/dialogs/organization_dialog.py`
- ⚠️ `ui/dialogs/renaming_dialog.py`

---

## Conclusión

El sistema de re-análisis automático está **funcionalmente completo** a nivel de infraestructura:
- ✅ Worker implementado y funcional
- ✅ Overlay visual con animaciones y progreso
- ✅ Lógica de invalidación de similares con snapshot
- ✅ Diálogos de resultados obsoletos
- ✅ Gestión de re-análisis concurrentes

**Requiere integración futura** con los diálogos para completar el flujo end-to-end. Los diálogos actuales son de visualización, no ejecutan acciones. Cuando se refactoricen para ejecutar acciones con workers, simplemente necesitan:

```python
# Al final del método de ejecución exitosa
self.actions_completed.emit('tool_name')
```

Y en Stage3Window al crear el diálogo:
```python
dialog.actions_completed.connect(self._on_tool_action_completed)
```

**Listo para PR y merge.** La integración con diálogos puede ser un sprint/issue separado.
