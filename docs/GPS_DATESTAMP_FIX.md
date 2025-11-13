# Refactorización de select_chosen_date() - GPS DateStamp Fix

## Resumen

Se ha corregido un problema crítico en `utils/date_utils.py` donde GPS DateStamp tenía prioridad máxima sobre DateTimeOriginal, causando selección de fechas incorrectas.

## Problema Identificado

GPS DateStamp tenía prioridad máxima en la función `select_chosen_date()`, pero esto era incorrecto porque:

1. **GPS DateStamp está siempre en UTC** (sin zona horaria local)
2. **Muchos dispositivos REDONDEAN el GPS timestamp** a horas completas (ej: 20:00:00)
3. **GPS puede estar ausente o incorrecto** por problemas de señal
4. **EXIF 2.1 no incluía fecha en GPS**, solo hora

### Ejemplo Real del Problema

```python
# Metadatos de una imagen:
EXIF DateTimeOriginal: 2021-08-04 18:49:23 (+02:00)
GPS DateStamp:         2021-08-04 20:00:00

# Comportamiento ANTERIOR (incorrecto):
# Seleccionaba: GPS DateStamp (20:00:00) ❌

# Comportamiento NUEVO (correcto):
# Selecciona: DateTimeOriginal (18:49:23) ✅
```

## Cambios Implementados

### 1. Nueva Lógica de Priorización

**PASO 1 - PRIORIDAD MÁXIMA (Fechas EXIF de cámara):**
1. DateTimeOriginal con OffsetTimeOriginal (la más precisa)
2. DateTimeOriginal sin OffsetTimeOriginal
3. CreateDate
4. DateTimeDigitized

**Regla:** Se comparan TODAS estas fechas EXIF y se devuelve la MÁS ANTIGUA.
Si existe al menos una de estas fechas, NO se continúa a los siguientes pasos.

**PASO 2 - PRIORIDAD SECUNDARIA (Fechas alternativas):**
5. Fecha extraída del nombre de archivo (útil para WhatsApp)
6. Video metadata (creation_time de ffprobe)

**PASO 3 - VALIDACIÓN GPS (NO se usa como fecha principal):**
- GPS DateStamp se valida contra DateTimeOriginal
- Si difiere más de 24 horas, se registra warning
- GPS está en UTC y puede estar redondeado, por lo que NO es confiable

**PASO 4 - ÚLTIMO RECURSO (Fechas de sistema):**
7. creation_date y modification_date del sistema de archivos

### 2. Nueva Función de Validación GPS

Se agregó `_validate_gps_coherence()` que:
- Compara GPS DateStamp con la fecha EXIF seleccionada
- Calcula la diferencia en segundos
- Si la diferencia es > 24 horas (86400 segundos), registra un warning detallado
- Proporciona información clara sobre la posible causa del problema

```python
def _validate_gps_coherence(all_dates: dict, selected_date: datetime) -> None:
    """
    Valida coherencia entre GPS DateStamp y DateTimeOriginal.
    
    GPS DateStamp puede diferir significativamente de DateTimeOriginal debido a:
    - GPS está siempre en UTC (sin zona horaria local)
    - Muchos dispositivos redondean GPS timestamp a horas completas
    - GPS puede estar ausente o incorrecto por problemas de señal
    """
    # ... implementación ...
```

### 3. Actualización de Docstrings

Se actualizó completamente la documentación de `select_chosen_date()` para reflejar la nueva lógica correcta y proporcionar ejemplos actualizados.

## Archivos Modificados

1. **`utils/date_utils.py`**
   - Función `select_chosen_date()` completamente refactorizada
   - Nueva función `_validate_gps_coherence()` agregada
   - Docstrings actualizados con la lógica correcta

2. **`tests/unit/utils/test_date_utils.py`**
   - `test_gps_date_has_highest_priority`: Actualizado para verificar que DateTimeOriginal tiene prioridad
   - `test_exif_date_original_has_priority_over_digitized`: Actualizado para verificar que se selecciona la fecha EXIF más antigua

## Resultados de Tests

✅ **56/56 tests pasando** en `test_date_utils.py`

### Tests de Validación Ejecutados

```bash
TEST 1: Caso problemático original
  - Input: DateTimeOriginal=18:49:23, GPS=20:00:00
  - Output: ✅ DateTimeOriginal seleccionado
  
TEST 2: GPS coherente (diferencia < 24h)
  - Input: DateTimeOriginal=10:30:00, GPS=12:30:00
  - Output: ✅ DateTimeOriginal seleccionado, sin warning
  
TEST 3: WhatsApp sin EXIF
  - Input: filename_date, creation_date
  - Output: ✅ filename_date tiene prioridad
  
TEST 4: Múltiples fechas EXIF
  - Input: DateTimeOriginal=14:00, CreateDate=12:00, DateTimeDigitized=15:00
  - Output: ✅ CreateDate (la más antigua) seleccionada
  
TEST 5: Solo fechas del sistema de archivos
  - Input: creation_date, modification_date
  - Output: ✅ creation_date (la más antigua) seleccionada
```

### Sistema de Warnings GPS

```bash
Diferencia < 24h: NO genera warning ✅
Diferencia > 24h: SÍ genera warning con detalles ✅

Warning example:
"GPS DateStamp (2021-08-06 20:00:00) difiere significativamente de 
DateTimeOriginal (2021-08-04 18:49:23). Diferencia: 49.2 horas. 
Posible problema de zona horaria o GPS incorrecto."
```

## Cumplimiento de Requisitos

✅ **Strict PEP 8:** Código formateado correctamente  
✅ **Type hints:** Todos los parámetros y retornos tipados  
✅ **Docstrings completos:** Documentación detallada con ejemplos  
✅ **Preserva estructura:** No se modificaron otras funciones del módulo  
✅ **Tests actualizados:** Todos los tests pasando  
✅ **GPS validation:** Sistema de warnings implementado  
✅ **Logging apropiado:** Warnings informativos con detalles completos  

## Impacto

### Antes de la Refactorización
- GPS DateStamp (20:00:00) era seleccionado incorrectamente
- Fechas redondeadas y en UTC causaban imprecisiones
- No había validación de coherencia GPS

### Después de la Refactorización
- DateTimeOriginal (18:49:23) es correctamente seleccionado
- Se usa la fecha EXIF más precisa y confiable
- GPS se valida contra DateTimeOriginal con warnings informativos
- Mayor precisión en la selección de fechas para renombrado de archivos

## Conclusión

La refactorización corrige un problema crítico de priorización que afectaba la precisión de las fechas seleccionadas para el renombrado de archivos. DateTimeOriginal (la fecha real de captura según la cámara) ahora tiene la prioridad correcta sobre GPS DateStamp (que puede estar redondeado o en UTC).

---

**Fecha de cambio:** 2025-11-13  
**Módulo afectado:** `utils/date_utils.py`  
**Tests afectados:** `tests/unit/utils/test_date_utils.py`  
**Estado:** ✅ Completado y verificado
