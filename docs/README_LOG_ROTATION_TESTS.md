# Tests de Rotación de Logs

Suite completa de tests para verificar el correcto funcionamiento del sistema de rotación de logs de Pixaro Lab.

## 📋 Cobertura de Tests

### ✅ TestLogRotationBySize
Tests que verifican la rotación por tamaño de archivo:

- **test_rotation_occurs_when_exceeding_max_size**: Verifica que el archivo se rota automáticamente al superar `MAX_LOG_FILE_SIZE_MB` durante una sesión activa
- **test_rotation_resets_file_size**: Verifica que después de rotar, el archivo actual comienza con tamaño pequeño (casi vacío)

### ✅ TestLogRotationBackupCount
Tests que verifican el respeto a `MAX_LOG_BACKUP_COUNT`:

- **test_creates_correct_number_of_backups**: Verifica que se crean exactamente N archivos rotados (.1, .2, .3, ..., .N)
- **test_old_backups_are_deleted**: Verifica que los archivos más antiguos se eliminan al exceder el límite
- **test_backup_numbering_sequence**: Verifica que .1 es el más reciente, .2 el anterior, etc.

### ✅ TestLogRotationMultipleSessions
Tests para rotación entre múltiples sesiones:

- **test_existing_file_rotates_on_init_if_too_large**: Verifica que un archivo existente que ya excede el límite se rota al inicializar el logger
- **test_multiple_init_sessions_respect_backup_count**: Verifica que múltiples inicializaciones del logger respetan el límite acumulado

### ✅ TestLogRotationDualLogging
Tests para dual logging:

- **test_both_logs_rotate_independently**: Verifica que el log principal y el de warnings rotan de forma independiente

### ✅ TestLogRotationEdgeCases
Tests para casos borde:

- **test_rotation_with_zero_backup_count_disabled**: Verifica que con `backupCount=0` la rotación está deshabilitada (comportamiento esperado de Python)
- **test_rotation_preserves_log_content**: Verifica que no se pierden mensajes durante la rotación
- **test_rotation_with_concurrent_writes**: Verifica thread-safety con escrituras concurrentes usando el RLock global

## 🚀 Ejecutar Tests

```bash
# Todos los tests de rotación
pytest tests/unit/utils/test_log_rotation.py -v

# Con salida detallada
pytest tests/unit/utils/test_log_rotation.py -v -s

# Con cobertura
pytest tests/unit/utils/test_log_rotation.py --cov=utils.logger --cov-report=term-missing

# Solo una clase específica
pytest tests/unit/utils/test_log_rotation.py::TestLogRotationBySize -v

# Solo un test específico
pytest tests/unit/utils/test_log_rotation.py::TestLogRotationBySize::test_rotation_occurs_when_exceeding_max_size -v
```

## 📊 Resultados

- **Total de tests**: 11
- **Estado**: ✅ Todos pasando
- **Cobertura**: 46% del módulo `utils/logger.py`
- **Tiempo de ejecución**: ~50-100 segundos (depende del hardware)

## 🔍 Qué Validan Estos Tests

### 1. Rotación por Tamaño
- ✅ Los archivos rotan al alcanzar `MAX_LOG_FILE_SIZE_MB` (10 MB)
- ✅ El archivo rotado (.1) tiene ~10 MB
- ✅ El archivo actual después de rotar es pequeño (<5 MB)

### 2. Gestión de Backups
- ✅ Se crean máximo `MAX_LOG_BACKUP_COUNT` archivos
- ✅ Los archivos más antiguos se eliminan automáticamente
- ✅ La numeración es consecutiva: .1, .2, .3, etc.
- ✅ .1 es siempre el más reciente (mayor timestamp)

### 3. Comportamiento Multi-Sesión
- ✅ Archivos grandes existentes se rotan al inicializar
- ✅ Múltiples sesiones respetan el límite total de backups

### 4. Dual Logging
- ✅ El log principal (INFO) y el de warnings (WARNERROR) rotan independientemente
- ✅ Cada uno respeta su propio límite de tamaño

### 5. Thread Safety
- ✅ Escrituras concurrentes desde múltiples threads funcionan correctamente
- ✅ No hay corrupción de archivos con el RLock global

### 6. Edge Cases
- ✅ `backupCount=0` deshabilita la rotación (comportamiento estándar de Python)
- ✅ No se pierden mensajes durante la rotación
- ✅ El contenido se preserva correctamente en archivos rotados

## 🐛 Bug Fix Validado

Estos tests validan la corrección del bug reportado:

> "El sistema de rotado de logs no funciona dentro de una misma sesión. El archivo de log excede el límite marcado en config.py"

**Problema identificado**: `MAX_LOG_BACKUP_COUNT = 0` deshabilitaba la rotación (RotatingFileHandler interpreta 0 como "nunca rotar", no "ilimitado")

**Solución implementada**: 
1. Cambiar `MAX_LOG_BACKUP_COUNT` de 0 a 9999
2. Implementar correctamente `ThreadSafeRotatingFileHandler.emit()` para llamar a `shouldRollover()` y `doRollover()`

**Validación**:
- `test_rotation_occurs_when_exceeding_max_size` ✅
- `test_rotation_resets_file_size` ✅
- `test_creates_correct_number_of_backups` ✅

## 📝 Notas Técnicas

### Duración de Tests
Los tests son necesariamente lentos (~50-100 segundos) porque:
- Escriben 10 MB de datos reales por rotación
- Provocan múltiples rotaciones (3-4 por test)
- Total: 40-60 MB escritos por test suite completa

### Optimizaciones Aplicadas
- Uso de backup counts pequeños (2-3) en tests para reducir tiempo
- Detección temprana de rotación (break cuando se crea .1)
- Mensajes de ~250 bytes para predecir con precisión el número de mensajes necesarios

### Thread Safety
El RLock global `_log_lock` garantiza:
- No interleaving de mensajes
- Rotación atómica (shouldRollover + doRollover + write)
- Sin corrupción en escrituras concurrentes

## 🎯 Próximos Pasos

Si necesitas extender los tests:
1. **Performance tests**: Medir tiempo de rotación con datasets grandes
2. **Stress tests**: Probar con 100+ rotaciones y verificar estabilidad
3. **Filesystem tests**: Validar comportamiento con discos llenos o permisos limitados
4. **Integration tests**: Verificar rotación durante uso real de las 7 herramientas

## 📚 Referencias

- Módulo probado: `utils/logger.py`
- Configuración: `config.py` (MAX_LOG_FILE_SIZE_MB, MAX_LOG_BACKUP_COUNT)
- Python RotatingFileHandler: https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler
