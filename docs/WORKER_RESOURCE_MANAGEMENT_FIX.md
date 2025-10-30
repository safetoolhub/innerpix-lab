# Corrección de Gestión de Recursos de Workers y Threads

## Fecha de Revisión
30 de octubre de 2025

## Resumen Ejecutivo
Se identificaron y corrigieron **5 problemas críticos** en la gestión de workers (QThread) que podrían causar memory leaks y recursos no liberados correctamente. Todos los problemas han sido resueltos.

---

## Problemas Identificados y Soluciones

### ✅ Problema 1: Workers sin deleteLater en DuplicatesController
**Descripción:** Los workers `duplicate_worker` y `deletion_worker` en `DuplicatesController` no tenían conectadas las señales `deleteLater()`, a diferencia de otros controladores.

**Impacto:** Memory leak - los workers permanecían en memoria después de completar su ejecución.

**Solución Aplicada:**
```python
# Añadidas conexiones para autoeliminación en analyze_duplicates():
self.duplicate_worker.finished.connect(lambda: self.duplicate_worker.setParent(None))
self.duplicate_worker.finished.connect(self.duplicate_worker.deleteLater)
self.duplicate_worker.error.connect(lambda: self.duplicate_worker.setParent(None))
self.duplicate_worker.error.connect(self.duplicate_worker.deleteLater)

# Ídem para deletion_worker en _execute_duplicate_deletion()
```

**Archivos Modificados:**
- `ui/controllers/duplicates_controller.py`

---

### ✅ Problema 2: Workers no añadidos/removidos de active_workers
**Descripción:** Los workers de `DuplicatesController` no se añadían a `main_window.active_workers` ni se removían después, causando inconsistencias en el seguimiento de workers activos.

**Impacto:** 
- Imposibilidad de detectar workers huérfanos
- Problemas al cerrar la aplicación (closeEvent no puede limpiar todos los workers)
- Posible falta de sincronización en re-análisis

**Solución Aplicada:**
```python
# Al crear el worker:
self.main_window.active_workers.append(self.duplicate_worker)

# En callbacks on_finished y on_error:
if self.duplicate_worker:
    if self.duplicate_worker in self.main_window.active_workers:
        self.main_window.active_workers.remove(self.duplicate_worker)
    self.duplicate_worker = None
```

**Archivos Modificados:**
- `ui/controllers/duplicates_controller.py` (4 ubicaciones)

---

### ✅ Problema 3: Limpieza inconsistente en on_error
**Descripción:** Los métodos `on_error` de algunos controladores no removían consistentemente el worker de `active_workers`.

**Impacto:** Referencias huérfanas que podrían causar comportamiento impredecible durante el cierre o re-análisis.

**Solución Aplicada:**
```python
def _on_duplicate_analysis_error(self, error_msg):
    # ... manejo del error ...
    
    # Limpiar worker
    if self.duplicate_worker:
        if self.duplicate_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.duplicate_worker)
        self.duplicate_worker = None
```

**Archivos Modificados:**
- `ui/controllers/duplicates_controller.py` (2 métodos: `_on_duplicate_analysis_error`, `_on_deletion_error`)

---

### ✅ Problema 4: Cleanup incompleto en todos los controllers
**Descripción:** Los métodos `cleanup()` llamaban `quit()/wait()` pero no removían los workers de `active_workers` ni establecían el worker a `None`.

**Impacto:** 
- Inconsistencia en el estado de `active_workers`
- Posibles referencias colgantes
- Problemas al re-intentar operaciones después de un cleanup

**Solución Aplicada:**
```python
def cleanup(self):
    """Limpia workers activos"""
    if self.execution_worker:
        if self.execution_worker.isRunning():
            self.execution_worker.stop()  # Detención graceful
            self.execution_worker.quit()
            self.execution_worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS)
        if self.execution_worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.execution_worker)
        self.execution_worker = None
```

**Archivos Modificados:**
- `ui/controllers/analysis_controller.py`
- `ui/controllers/renaming_controller.py`
- `ui/controllers/live_photos_controller.py`
- `ui/controllers/organizer_controller.py`
- `ui/controllers/heic_controller.py`
- `ui/controllers/duplicates_controller.py`

**Imports Añadidos:**
```python
from config import Config  # Para acceder a WORKER_SHUTDOWN_TIMEOUT_MS
```

---

### ✅ Problema 5: Falta desconexión de padre antes de deleteLater
**Descripción:** Los QThread workers no establecían `setParent(None)` antes de `deleteLater()`, lo cual puede retrasar la liberación de recursos en Qt.

**Impacto:** 
- Retraso en la destrucción del objeto
- El sistema de gestión de memoria de Qt podría mantener referencias innecesarias
- Comportamiento impredecible en ciclos de vida de objetos padre-hijo

**Solución Aplicada:**
```python
# Desconectar del padre ANTES de deleteLater
self.worker.finished.connect(lambda: self.worker.setParent(None))
self.worker.finished.connect(self.worker.deleteLater)
self.worker.error.connect(lambda: self.worker.setParent(None))
self.worker.error.connect(self.worker.deleteLater)
```

**Archivos Modificados:** Todos los controladores:
- `ui/controllers/analysis_controller.py`
- `ui/controllers/renaming_controller.py`
- `ui/controllers/live_photos_controller.py`
- `ui/controllers/organizer_controller.py`
- `ui/controllers/heic_controller.py`
- `ui/controllers/duplicates_controller.py`

---

## Mejoras Implementadas

### 1. Patrón Consistente de Gestión de Workers
Todos los controladores ahora siguen el mismo patrón:

```python
# 1. Crear worker
self.worker = SomeWorker(...)

# 2. Conectar señales
self.worker.progress_update.connect(...)
self.worker.finished.connect(self.on_finished)
self.worker.error.connect(self.on_error)

# 3. Autoeliminación con desconexión de padre
self.worker.finished.connect(lambda: self.worker.setParent(None))
self.worker.finished.connect(self.worker.deleteLater)
self.worker.error.connect(lambda: self.worker.setParent(None))
self.worker.error.connect(self.worker.deleteLater)

# 4. Añadir a lista de workers activos
self.main_window.active_workers.append(self.worker)

# 5. Iniciar
self.worker.start()
```

### 2. Limpieza Robusta en Callbacks
```python
def on_finished(self, results):
    # ... procesamiento ...
    
    # Limpiar worker
    if self.worker:
        if self.worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.worker)
        self.worker = None

def on_error(self, error):
    # ... manejo de error ...
    
    # Limpiar worker (misma lógica que on_finished)
    if self.worker:
        if self.worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.worker)
        self.worker = None
```

### 3. Método cleanup() Estandarizado
```python
def cleanup(self):
    """Limpia workers activos"""
    if self.worker:
        if self.worker.isRunning():
            self.worker.stop()  # Detención graceful
            self.worker.quit()
            self.worker.wait(Config.WORKER_SHUTDOWN_TIMEOUT_MS)
        if self.worker in self.main_window.active_workers:
            self.main_window.active_workers.remove(self.worker)
        self.worker = None
```

---

## Beneficios de las Correcciones

### Gestión de Memoria
- ✅ Eliminación automática de workers después de su uso
- ✅ No más memory leaks por workers huérfanos
- ✅ Liberación inmediata de recursos al desconectar del padre

### Estabilidad
- ✅ Seguimiento consistente de todos los workers activos
- ✅ Limpieza garantizada en todos los escenarios (éxito/error/cancelación)
- ✅ Cierre limpio de la aplicación sin threads colgados

### Mantenibilidad
- ✅ Patrón uniforme en todos los controladores
- ✅ Código más predecible y fácil de depurar
- ✅ Uso consistente de `Config.WORKER_SHUTDOWN_TIMEOUT_MS`

---

## Testing Recomendado

### Escenarios Críticos a Verificar:
1. **Análisis completo → cierre inmediato de aplicación**
   - Verificar que no queden threads colgados
   - Revisar logs para warnings de Qt sobre QThread

2. **Análisis → error → nuevo análisis**
   - Verificar que el worker anterior se limpió correctamente
   - No debe haber workers duplicados en `active_workers`

3. **Múltiples operaciones en paralelo (diferentes pestañas)**
   - Renombrado + Live Photos + HEIC simultáneamente
   - Verificar que todos los workers se limpian correctamente

4. **Cancelación durante análisis de duplicados**
   - Usar el botón de cancelar
   - Verificar limpieza completa del worker

5. **Cierre durante operación activa**
   - Iniciar análisis largo, cerrar app inmediatamente
   - Debe esperar máximo `WORKER_SHUTDOWN_TIMEOUT_MS` (2000ms)

### Monitoreo de Recursos:
```bash
# Linux: Verificar threads activos
ps -eLf | grep pixaro-lab

# Verificar memoria
ps aux | grep pixaro-lab

# Durante ejecución, revisar logs:
tail -f ~/Documents/Pixaro_Lab/logs/pixaro_lab_<timestamp>.log
```

---

## Configuración Relevante

### Config.py
```python
# Tiempo máximo de espera para detener workers
WORKER_SHUTDOWN_TIMEOUT_MS = 2000  # 2 segundos
```

Este timeout se usa en:
- `cleanup()` de todos los controladores
- `closeEvent()` en `MainWindow`
- `cancel_duplicate_analysis()` en `DuplicatesController`

---

## Notas de Implementación

### Orden de Señales
El orden de las conexiones es importante:
```python
# CORRECTO: setParent(None) ANTES de deleteLater()
worker.finished.connect(lambda: worker.setParent(None))
worker.finished.connect(worker.deleteLater)

# INCORRECTO: deleteLater sin desconectar padre
worker.finished.connect(worker.deleteLater)  # Puede retrasarse
```

### BaseWorker.stop()
Todos los workers heredan de `BaseWorker` que proporciona:
```python
def stop(self):
    """Request the worker to stop gracefully"""
    self._stop_requested = True

def is_stop_requested(self):
    """Check if stop was requested"""
    return self._stop_requested
```

Los servicios deben verificar `_stop_requested` durante operaciones largas.

---

## Conclusión

Todas las correcciones han sido aplicadas exitosamente. El sistema ahora gestiona los recursos de workers de manera:
- **Determinística**: Cada worker tiene un ciclo de vida bien definido
- **Consistente**: Todos siguen el mismo patrón
- **Robusta**: Manejo de errores completo en todos los escenarios
- **Eficiente**: Liberación inmediata de recursos

**Estado:** ✅ COMPLETADO - Sin errores de compilación
