# Algoritmo de Cálculo de Mejor Fecha (Best Date)

> **Función**: `select_best_date_from_file(file_metadata: FileMetadata) → (datetime, str)`  
> **Ubicación**: `utils/date_utils.py`  
> **Última actualización**: Febrero 2026

---

## Objetivo

Seleccionar la fecha más representativa y precisa para un archivo multimedia (foto/video) considerando múltiples fuentes de metadatos, priorizando la **fidelidad al momento de captura/creación original**.

---

## Principios de Diseño

1. **Prioridad estricta** sobre "fecha más antigua": DateTimeOriginal siempre gana sobre otras fechas EXIF, incluso si es más reciente
2. **Evitar metadatos corruptos**: Validaciones para detectar y descartar fechas erróneas (epoch 0, DateTimeDigitized corrupto, etc.)
3. **Maximizar precisión horaria**: Cuando hay múltiples fuentes con el mismo día, preferir la que tenga información horaria completa
4. **Transparencia**: El `source` retornado indica claramente la fuente utilizada

---

## Algoritmo Completo

### PASO 1: Validaciones Iniciales

#### 1.1. Parsear todas las fechas disponibles

```python
exif_date_time_original = parse(FileMetadata.exif_DateTimeOriginal)
exif_create_date = parse(FileMetadata.exif_DateTime)  # CreateDate
exif_date_digitized = parse(FileMetadata.exif_DateTimeDigitized)
exif_offset_time = FileMetadata.exif_OffsetTimeOriginal  # Zona horaria
```

#### 1.2. Filtrar epoch zero (1970-01-01 00:00:00)

Fechas EXIF con epoch 0 son **siempre descartadas** (metadatos corruptos o no inicializados).

```python
def _is_epoch_zero_date(dt: datetime) -> bool:
    return dt == datetime(1970, 1, 1, 0, 0, 0)
```

#### 1.3. Convertir fechas del filesystem

```python
fs_ctime = datetime.fromtimestamp(FileMetadata.fs_ctime)  # Creation/change time
fs_mtime = datetime.fromtimestamp(FileMetadata.fs_mtime)  # Modification time
```

---

### PASO 2: PRIORIDAD MÁXIMA - Fechas EXIF de Cámara

**Prioridad estricta** (no seleccionar la más antigua, sino la primera válida):

#### 2.1. DateTimeOriginal con OffsetTimeOriginal (PRIORIDAD #1)
```python
if exif_date_time_original and not _is_epoch_zero_date(exif_date_time_original) and exif_offset_time:
    return exif_date_time_original, f"EXIF DateTimeOriginal ({exif_offset_time})"
```

**Razón**: Es la fecha de captura exacta con zona horaria. **La más confiable**.

---

#### 2.2. DateTimeOriginal sin OffsetTimeOriginal (PRIORIDAD #2)
```python
if exif_date_time_original and not _is_epoch_zero_date(exif_date_time_original):
    return exif_date_time_original, 'EXIF DateTimeOriginal'
```

**Razón**: Fecha de captura exacta, aunque sin zona horaria.

---

#### 2.3. CreateDate (PRIORIDAD #3)
```python
if exif_create_date and not _is_epoch_zero_date(exif_create_date):
    return exif_create_date, 'EXIF CreateDate'
```

**Razón**: Fecha de creación digital del archivo (normalmente igual a DateTimeOriginal).

---

#### 2.4. DateTimeDigitized (PRIORIDAD #4 - Último recurso EXIF)
```python
if exif_date_digitized and not _is_epoch_zero_date(exif_date_digitized):
    return exif_date_digitized, 'EXIF DateTimeDigitized'
```

**Razón**: Fecha de digitalización. **Puede estar corrupta** en cámaras antiguas, por eso es la última opción EXIF.

**Ejemplo real**: `IMG_20161015_113122.jpg` tenía:
- `DateTimeOriginal`: 2016-10-15 11:31:22 ✅ (correcta)
- `DateTimeDigitized`: 2002-12-08 12:00:00 ❌ (corrupta)

La prioridad estricta evita seleccionar la fecha corrupta de 2002.

---

### PASO 3: PRIORIDAD SECUNDARIA - Fechas Alternativas

Si no hay EXIF disponible, buscar fechas alternativas:

#### 3.1. Fecha del Nombre de Archivo (con validación de precisión)

```python
filename_date = extract_date_from_filename(file_metadata.path.name)

if filename_date:
    # Caso especial: filename sin hora (00:00:00) pero mtime tiene el mismo día
    if (filename_date.hour == 0 and filename_date.minute == 0 and filename_date.second == 0):
        if fs_mtime:
            if (filename_date.year == fs_mtime.year and 
                filename_date.month == fs_mtime.month and 
                filename_date.day == fs_mtime.day):
                # mtime es más precisa (tiene hora real)
                return fs_mtime, 'mtime (more precise than filename)'
    
    # En cualquier otro caso, usar filename
    return filename_date, 'Filename'
```

**Patrones soportados**:
- `IMG_20230515_143045.jpg` → 2023-05-15 14:30:45
- `IMG-20230515-WA0001.jpg` (WhatsApp) → 2023-05-15 00:00:00
- `DSC_20230515_120000.jpg` → 2023-05-15 12:00:00
- `20230515_143045.jpg` → 2023-05-15 14:30:45

**Regla de precisión horaria**:

| Filename | mtime | Fecha seleccionada | Razón |
|----------|-------|-------------------|-------|
| `IMG-20230515-WA0001.jpg`<br>(2023-05-15 **00:00:00**) | 2023-05-15 **14:30:45** | **mtime** (14:30:45) | Mismo día, mtime tiene hora real |
| `IMG_20230515_143045.jpg`<br>(2023-05-15 **14:30:45**) | 2023-05-15 14:30:47 | **filename** (14:30:45) | Filename ya tiene hora precisa |
| `IMG-20230515-WA0001.jpg`<br>(2023-05-15 **00:00:00**) | 2023-05-20 10:00:00 | **filename** (2023-05-15) | Días diferentes, mantener filename |

**Ejemplo real**:
```
Archivo: IMG-20230515-WA0001.jpg
- filename_date: 2023-05-15 00:00:00 (sin hora, WhatsApp)
- fs_mtime: 2023-05-15 14:30:45 (hora real)
→ Selecciona: mtime (más precisa)
```

---

#### 3.2. Video Metadata (solo para videos)

```python
if file_metadata.is_video and exif_create_date:
    return exif_create_date, 'Video Metadata'
```

**Razón**: Para videos, `exif_DateTime` (CreateDate) suele ser la fecha de grabación.

---

### PASO 4: ÚLTIMO RECURSO - Filesystem Dates

Si no hay EXIF ni fecha en filename, usar fechas del sistema de archivos:

```python
fs_dates = []

if fs_ctime:
    fs_dates.append((fs_ctime, 'ctime'))  # o 'birth' en macOS

if fs_mtime:
    fs_dates.append((fs_mtime, 'mtime'))

if fs_dates:
    earliest_fs = min(fs_dates, key=lambda x: x[0])  # La más antigua
    return earliest_fs[0], earliest_fs[1]
```

**Nota**: Estas fechas son **poco confiables** porque cambian al copiar/mover archivos.

---

### PASO 5: Sin Fechas Disponibles

```python
return None, None
```

---

## Validaciones Adicionales

### GPS DateStamp (Solo Validación, NO Selección)

GPS DateStamp **nunca se usa como fecha principal** debido a:
- Siempre está en **UTC** (sin zona horaria local)
- Muchos dispositivos **redondean** el timestamp a horas completas
- Puede estar **ausente o incorrecto** por problemas de señal

**Validación de coherencia**:
```python
if exif_gps_date and selected_date:
    diff_seconds = abs((exif_gps_date - selected_date).total_seconds())
    if diff_seconds > 86400:  # Más de 24 horas
        logger.warning(f"GPS date diverges from DateTimeOriginal by {diff_seconds/3600:.1f} hours")
```

---

## Resumen de Prioridades

```
PASO 1: EXIF CAMERA DATES (Prioridad Estricta)
├─ 1. DateTimeOriginal + OffsetTimeOriginal
├─ 2. DateTimeOriginal
├─ 3. CreateDate
└─ 4. DateTimeDigitized

PASO 2: FECHAS ALTERNATIVAS
├─ 5. Filename Date
│   └─ Validación: Si hora=00:00:00 y mismo día que mtime → usar mtime
└─ 6. Video Metadata

PASO 3: VALIDACIÓN GPS (no seleccionable)
└─ GPS DateStamp → Solo warning si diverge >24h

PASO 4: FILESYSTEM (Último Recurso)
├─ 7. fs_ctime (o birth en macOS)
└─ 8. fs_mtime

PASO 5: SIN FECHAS
└─ None, None
```

---

## Casos de Uso Reales

### Caso 1: Foto con EXIF Completo
```
IMG_20161015_113122.jpg
- DateTimeOriginal: 2016-10-15 11:31:22 ✅
- DateTimeDigitized: 2002-12-08 12:00:00 (corrupto)
→ Selecciona: DateTimeOriginal (prioridad estricta)
```

### Caso 2: WhatsApp sin EXIF
```
IMG-20230515-WA0001.jpg
- Sin EXIF
- filename_date: 2023-05-15 00:00:00 (sin hora)
- fs_mtime: 2023-05-15 14:30:45
→ Selecciona: mtime (más precisa que filename)
```

### Caso 3: Screenshot sin Metadatos
```
Screenshot_20230515.png
- Sin EXIF
- filename_date: 2023-05-15 00:00:00
- fs_mtime: 2023-05-20 10:00:00 (días diferentes)
→ Selecciona: filename (día más realista que mtime)
```

### Caso 4: Archivo Copiado/Movido
```
DSC_1234.jpg
- Sin EXIF
- Sin fecha en filename
- fs_ctime: 2024-01-15 (fecha de copia)
- fs_mtime: 2024-01-15 (fecha de copia)
→ Selecciona: fs_ctime (única opción, aunque poco confiable)
```

---

## Testing

El algoritmo cuenta con **95 tests unitarios** que validan:
- Prioridad estricta EXIF (no selección de más antigua)
- Validación de precisión filename vs mtime
- Detección de metadatos corruptos (epoch 0)
- Manejo de dates strings en múltiples formatos
- Coherencia GPS vs EXIF

**Ejecutar tests**:
```bash
pytest tests/unit/utils/test_date_utils.py -v
```

---

## Historial de Cambios

### Febrero 2026
- **Prioridad estricta**: Cambiado de "seleccionar la más antigua" a "primera válida por prioridad"
  - Evita seleccionar `DateTimeDigitized` corrupta sobre `DateTimeOriginal` válida
- **Precisión horaria filename vs mtime**: Si filename tiene 00:00:00 y mismo día que mtime, preferir mtime
  - Mejora precisión en archivos WhatsApp y screenshots sin hora

### Enero 2026
- Validación de epoch zero dates
- Soporte para timezone normalization en `select_best_date_from_common_date_to_2_files`

---

## Referencias

- **Estándar EXIF**: [EXIF 2.32 Specification](https://www.cipa.jp/std/documents/e/DC-008-Translation-2019-E.pdf)
- **GPS DateStamp Issues**: [Why GPS timestamps can be unreliable](https://photo.stackexchange.com/questions/56054)
- **Función principal**: [utils/date_utils.py::select_best_date_from_file](../utils/date_utils.py)
- **Tests**: [tests/unit/utils/test_date_utils.py](../tests/unit/utils/test_date_utils.py)
