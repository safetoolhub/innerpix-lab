# Convenciones de Logging - PhotoKit Manager

## Introducción

Este documento establece las convenciones de logging para el proyecto PhotoKit Manager. Todos los módulos deben seguir estas pautas para asegurar logs consistentes, informativos y fáciles de depurar.

## Configuración del Logger

### Importación y Creación

Todos los servicios y controladores deben usar el logger centralizado:

```python
from utils.logger import get_logger

class MiServicio:
    def __init__(self):
        self.logger = get_logger('MiServicio')
```

### Cambio de Nivel de Log en Runtime

Para cambiar el nivel de log globalmente (afecta a TODOS los loggers):

```python
from utils.logger import set_global_log_level
import logging

# Cambiar a DEBUG para ver todos los logs
set_global_log_level(logging.DEBUG)

# Cambiar a ERROR para ver solo errores
set_global_log_level(logging.ERROR)
```

**Importante:** El cambio de nivel es global y afecta a todos los loggers de la aplicación instantáneamente.

### Formato de Log

El logger está configurado para mostrar:
- Fecha y hora (formato: YYYY-MM-DD HH:MM:SS)
- Nombre del módulo (jerárquico: PhotokitManager.NombreModulo)
- Nivel de log
- Mensaje (siempre en una sola línea, sin HTML)

Ejemplo de salida:
```
2025-10-28 14:30:45 - PhotokitManager.DuplicateDetector - INFO - Iniciando análisis de duplicados exactos en /path/to/dir
```

## Niveles de Log

### DEBUG
**Uso:** Detalles internos de bajo nivel, útiles solo durante debugging.

**Cuándo usar:**
- Valores de variables intermedias
- Flujo detallado de ejecución
- Información de debugging que normalmente no es necesaria

**Ejemplos:**
```python
self.logger.debug(f"Extensiones de foto configuradas: {self.photo_extensions}")
self.logger.debug(f"Conflicto detectado para {target_name}, buscando nombre alternativo")
self.logger.debug(f"Video registrado: {video.name} con nombre normalizado: {normalized_name}")
```

**NO usar para:**
- Operaciones importantes del sistema
- Errores o advertencias
- Resultados de operaciones principales

---

### INFO
**Uso:** Operaciones importantes completadas exitosamente.

**Cuándo usar:**
- Inicio y finalización de operaciones principales
- Resultados de análisis
- Confirmación de acciones completadas
- Estadísticas importantes

**Ejemplos:**
```python
self.logger.info(f"Iniciando análisis de duplicados exactos en {directory}")
self.logger.info(f"Análisis completado: {results['need_renaming']} archivos para renombrar")
self.logger.info(f"Eliminación completada: {results['files_deleted']} archivos eliminados")
self.logger.info(f"Backup creado en: {backup_path}")
```

**NO usar para:**
- Detalles internos (usar DEBUG)
- Situaciones de error (usar ERROR)
- Advertencias (usar WARNING)

---

### WARNING
**Uso:** Situaciones recuperables que merecen atención.

**Cuándo usar:**
- Archivos que no se pudieron procesar pero la operación continúa
- Datos faltantes o incompletos que se manejan con valores por defecto
- Condiciones inesperadas pero manejables
- Configuraciones subóptimas

**Ejemplos:**
```python
self.logger.warning(f"No se pudo procesar {file_path}: {e}")
self.logger.warning(f"No se pudo obtener fecha para {file_path.name}, usando fecha actual")
self.logger.warning(f"Saltando archivo que no existe: {file_path}")
self.logger.warning(f"Error creando grupo para {original_name}: {e}")
```

**NO usar para:**
- Errores críticos que detienen la operación (usar ERROR)
- Información normal del flujo (usar INFO)
- Debugging (usar DEBUG)

---

### ERROR
**Uso:** Errores que requieren atención inmediata.

**Cuándo usar:**
- Fallos críticos en operaciones
- Excepciones que impiden completar una tarea
- Problemas que afectan la integridad de datos
- Errores que el usuario debe conocer

**Ejemplos:**
```python
self.logger.error(f"Error crítico en renombrado: {str(e)}")
self.logger.error(f"Error eliminando {file_path}: {e}")
self.logger.error(f"Error creando backup: {e}")
self.logger.error(f"Archivo no existe: {move.source_path}")
```

**NO usar para:**
- Situaciones recuperables (usar WARNING)
- Validaciones normales del negocio
- Archivos individuales que fallan en lotes grandes

---

## Reglas Generales

### 1. Texto Plano en Una Sola Línea
❌ **NUNCA** incluir HTML en los logs. El sistema automáticamente:
- Elimina todas las etiquetas HTML (`<b>`, `<div>`, `<br>`, etc.)
- Convierte saltos de línea a espacios
- Normaliza múltiples espacios a uno solo
- Mantiene todo en una sola línea

```python
# MAL - pero se sanitizará automáticamente
self.logger.info("<b>Operación completada</b>")
self.logger.error("Error: <br>Archivo no encontrado")

# BIEN - texto plano directo
self.logger.info("Operación completada")
self.logger.error("Error: Archivo no encontrado")

# Ejemplo de sanitización automática:
self.logger.info("Línea 1<br>Línea 2<br/>Línea 3")
# Se guarda como: "Línea 1 Línea 2 Línea 3"
```

### 2. Mensajes Descriptivos
Los mensajes deben ser claros y autoexplicativos:

```python
# MAL
self.logger.info("Hecho")
self.logger.error("Error")

# BIEN
self.logger.info(f"Análisis completado: {total_files} archivos procesados")
self.logger.error(f"No se pudo acceder al archivo {file_path}: {error}")
```

### 3. Incluir Contexto Relevante
Siempre incluir información que ayude a entender el log:

```python
# MAL
self.logger.error("Error procesando archivo")

# BIEN
self.logger.error(f"Error procesando {file_path.name}: {type(e).__name__} - {str(e)}")
```

### 4. Evitar Logs Redundantes
No loguear lo mismo múltiples veces en el mismo contexto:

```python
# MAL
for file in files:
    self.logger.info(f"Procesando {file}")  # Demasiado verbose
    process(file)

# BIEN
self.logger.info(f"Procesando {len(files)} archivos")
for file in files:
    process(file)
```

### 5. Logs en Bucles
En operaciones con muchos elementos, usar logging moderado:

```python
# Para progreso en bucles largos
processed = 0
for item in items:
    process(item)
    processed += 1
    # Solo loguear cada N elementos o al finalizar
    if processed % 100 == 0:
        self.logger.debug(f"Procesados {processed}/{len(items)} elementos")

self.logger.info(f"Procesamiento completado: {processed} elementos")
```

### 6. Manejo de Excepciones
Siempre incluir información del error:

```python
try:
    risky_operation()
except Exception as e:
    # Incluir tipo de error y mensaje
    self.logger.error(f"Error en operación: {type(e).__name__} - {str(e)}")
    # Para debugging, incluir más contexto
    self.logger.debug(f"Detalles: {e}", exc_info=True)
```

## Ejemplos por Módulo

### Servicios (services/)

```python
class MiServicio:
    def __init__(self):
        self.logger = get_logger('MiServicio')
    
    def analyze(self, directory):
        self.logger.info(f"Iniciando análisis en: {directory}")
        
        try:
            # Operación principal
            results = self._do_analysis(directory)
            self.logger.info(f"Análisis completado: {results['total']} elementos encontrados")
            return results
        except Exception as e:
            self.logger.error(f"Error en análisis: {str(e)}")
            raise
    
    def _do_analysis(self, directory):
        self.logger.debug(f"Analizando directorio: {directory}")
        # ... implementación
```

### Controladores (ui/controllers/)

```python
class MiController(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.logger = get_logger('MiController')
    
    def execute_operation(self):
        self.logger.info("Iniciando operación desde UI")
        
        try:
            # Operación
            result = self.service.execute()
            self.logger.info(f"Operación completada: {result['status']}")
        except Exception as e:
            self.logger.error(f"Error en operación: {str(e)}")
            # Mostrar mensaje al usuario
```

## Verificación

### Checklist de Logging

Antes de hacer commit, verificar:

- [ ] Todos los servicios tienen `self.logger = get_logger('NombreServicio')`
- [ ] Todos los controladores tienen `self.logger = get_logger('NombreController')`
- [ ] No hay mensajes con HTML
- [ ] Se usan los niveles de log apropiados (DEBUG/INFO/WARNING/ERROR)
- [ ] Los mensajes son descriptivos y tienen contexto
- [ ] No hay logging excesivo en bucles
- [ ] Los errores incluyen información útil para debugging

## Herramientas

### Sanitización de Mensajes

El logger incluye sanitización automática que convierte cualquier contenido a una sola línea de texto plano:

```python
# Todos estos se convierten automáticamente a una línea sin HTML
self.logger.info("<b>Texto en negrita</b>")  
# → "Texto en negrita"

self.logger.info("Línea 1<br>Línea 2<br/>Línea 3")  
# → "Línea 1 Línea 2 Línea 3"

self.logger.info("Múltiples\n\n\nespacios    y     saltos")  
# → "Múltiples espacios y saltos"

self.logger.info("<div><p>HTML complejo</p><span>anidado</span></div>")  
# → "HTML complejoanidado"
```

### Cambio de Nivel de Log Globalmente

El sistema ahora soporta cambio de nivel en runtime que afecta a TODOS los loggers:

```python
from utils.logger import set_global_log_level
import logging

# Ver todos los logs (más verbose)
set_global_log_level(logging.DEBUG)

# Ver solo errores (menos verbose)
set_global_log_level(logging.ERROR)

# Restaurar a nivel normal
set_global_log_level(logging.INFO)
```

**Nota:** El cambio desde el diálogo de settings usa esta función automáticamente.

## Recursos Adicionales

- Documentación oficial de logging: https://docs.python.org/3/library/logging.html
- PEP 8 - Logging: https://peps.python.org/pep-0008/

---

**Última actualización:** 2025-10-28
**Autor:** PhotoKit Manager Team
