"""
Utilidades para extracción de fechas de archivos multimedia
"""
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple, Protocol, Any, runtime_checkable

try:
    # Intento de importar FileMetadata si existe en el path indicado por el usuario
    # o donde se encuentre realmente en el proyecto
    from services.file_metadata import FileMetadata
except ImportError:
    pass

from functools import lru_cache
from utils.logger import get_logger

_logger = get_logger("DateUtils")


# Protocolo para definir la estructura esperada de FileInfo/FileMetadata
# según la especificación del usuario
@runtime_checkable
class FileInfoProtocol(Protocol):
    path: Path
    # Campos EXIF (opcionales, datetime)
    exif_date_time_original: Optional[datetime]
    exif_create_date: Optional[datetime]
    exif_modify_date: Optional[datetime]
    # Timestamps del filesystem (opcionales, datetime)
    atime: Optional[datetime]
    ctime: Optional[datetime]
    mtime: Optional[datetime]


def get_best_creation_date(
    file1: Any, 
    file2: Any,
    verbose: bool = False
) -> Optional[Tuple[datetime, datetime, str]]:
    """
    Compara las fechas de creación más realistas posibles de dos archivos de imagen.
    
    Devuelve una tupla con (fecha_file1, fecha_file2, fuente) donde las fechas son
    del mismo tipo para ambos archivos (nunca mezcla EXIF con filesystem).
    Usado por HEICService para determinar la fecha correcta de los pares de archivos.
    
    Prioriza fidelidad al momento de captura/creación original:
    1. EXIF DateTimeOriginal (Captura exacta)
    2. EXIF CreateDate (Creación digital)
    3. EXIF ModifyDate (Última modificación EXIF)
    4. Filesystem ctime (Change time - creación/metadatos)
    5. Filesystem mtime (Modify time - contenido)
    6. Filesystem atime (Access time - último recurso)
    
    Args:
        file1: Objeto con metadatos del primer archivo (FileInfo/FileMetadata)
        file2: Objeto con metadatos del segundo archivo (FileInfo/FileMetadata)
        
    Returns:
        Tuple[datetime, datetime, str]: (fecha1, fecha2, fuente_usada)
        None: Si no se puede determinar ninguna fecha válida común
        
    Examples:
        >>> from types import SimpleNamespace
        >>> dt1 = datetime(2023, 1, 1, 12, 0, 0)
        >>> dt2 = datetime(2023, 1, 2, 12, 0, 0)
        >>> f1 = SimpleNamespace(path='f1', exif_date_time_original=dt1)
        >>> f2 = SimpleNamespace(path='f2', exif_date_time_original=dt2)
        >>> get_best_creation_date(f1, f2)
        (datetime.datetime(2023, 1, 1, 12, 0), datetime.datetime(2023, 1, 2, 12, 0), 'exif_date_time_original')
    """
    # Validar que los objetos tienen los atributos necesarios
    # Se usa getattr para seguridad si los objetos no cumplen estrictamente el protocolo
    
    def _get_val(obj, *attrs):
        for attr in attrs:
            val = getattr(obj, attr, None)
            if val is not None:
                if verbose: _logger.debug(f"      - Found {attr} on {getattr(obj, 'path', 'file')}: {val}")
                return val
        return None

    def _to_dt(val):
        if val is None: return None
        if isinstance(val, datetime): return val
        if isinstance(val, (int, float)): return datetime.fromtimestamp(val)
        return None

    def _fmt(dt):
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f') if dt else 'None'

    if verbose:
        _logger.debug(f"DEBUG: Comparing dates for {getattr(file1, 'path', 'f1')} and {getattr(file2, 'path', 'f2')}")

    # ---------------------------------------------------------
    # 1. PRIORIDAD: AMBOS TIENEN EXIF VÁLIDOS
    # ---------------------------------------------------------
    
    # Priority 1: EXIF DateTimeOriginal
    file1_datetime_original = _to_dt(_get_val(file1, 'exif_date_time_original', 'exif_DateTimeOriginal'))
    file2_datetime_original = _to_dt(_get_val(file2, 'exif_date_time_original', 'exif_DateTimeOriginal'))
    
    if verbose: _logger.debug(f"    - EXIF DateTimeOriginal: file1={_fmt(file1_datetime_original)}, file2={_fmt(file2_datetime_original)}")
    if file1_datetime_original is not None and file2_datetime_original is not None:
        if verbose: _logger.debug("    => Match found: exif_date_time_original")
        _logger.debug(f"Source selected: exif_date_time_original for {getattr(file1, 'path', 'f1')} and {getattr(file2, 'path', 'f2')}")
        return file1_datetime_original, file2_datetime_original, 'exif_date_time_original'
        
    # Priority 2: EXIF CreateDate
    file1_create_date = _to_dt(_get_val(file1, 'exif_create_date', 'exif_CreateDate', 'exif_DateTimeDigitized'))
    file2_create_date = _to_dt(_get_val(file2, 'exif_create_date', 'exif_CreateDate', 'exif_DateTimeDigitized'))
    
    if verbose: _logger.debug(f"    - EXIF CreateDate: file1={_fmt(file1_create_date)}, file2={_fmt(file2_create_date)}")
    if file1_create_date is not None and file2_create_date is not None:
        if verbose: _logger.debug("    => Match found: exif_create_date")
        _logger.debug(f"Source selected: exif_create_date for {getattr(file1, 'path', 'f1')} and {getattr(file2, 'path', 'f2')}")
        return file1_create_date, file2_create_date, 'exif_create_date'
        
    # Priority 3: EXIF ModifyDate
    file1_modify_date = _to_dt(_get_val(file1, 'exif_modify_date', 'exif_DateTime'))
    file2_modify_date = _to_dt(_get_val(file2, 'exif_modify_date', 'exif_DateTime'))
    
    if verbose: _logger.debug(f"    - EXIF ModifyDate: file1={_fmt(file1_modify_date)}, file2={_fmt(file2_modify_date)}")
    if file1_modify_date is not None and file2_modify_date is not None:
        if verbose: _logger.debug("    => Match found: exif_modify_date")
        _logger.debug(f"Source selected: exif_modify_date for {getattr(file1, 'path', 'f1')} and {getattr(file2, 'path', 'f2')}")
        return file1_modify_date, file2_modify_date, 'exif_modify_date'

    # -------------------------------------------------------------------------
    # 2. FILESYSTEM FALLBACK (Solo uno o ninguno tiene EXIF)
    # -------------------------------------------------------------------------
    # Buscamos la fecha más antigua común entre mtime, ctime y atime.
    # Priorizar la fecha más antigua ayuda a encontrar la fecha original incluso
    # si el archivo fue copiado (reseteando ctime) o modificado (reseteando mtime).
    
    # Fuentes a evaluar en orden de relevancia lógica (mtime suele ser la más real)
    filesystem_sources = [
        ('mtime', 'fs_mtime'),
        ('ctime', 'fs_ctime'),
        ('atime', 'fs_atime')
    ]
    
    common_candidates = []
    
    # Solo consideramos fuentes que ESTÉN PRESENTES EN AMBOS archivos
    for attr_name, source_label in filesystem_sources:
        date_f1 = _to_dt(_get_val(file1, attr_name, f'fs_{attr_name}'))
        date_f2 = _to_dt(_get_val(file2, attr_name, f'fs_{attr_name}'))
        
        if date_f1 and date_f2:
            common_candidates.append({
                'date1': date_f1,
                'date2': date_f2,
                'source': source_label
            })
            
    if common_candidates:
        # Seleccionamos la combinación que contenga la fecha absoluta más antigua
        # Para evitar sesgos, comparamos el mínimo de ambas fechas en cada candidato
        best_match = min(common_candidates, key=lambda candidate: min(candidate['date1'], candidate['date2']))
        
        result_date1 = best_match['date1']
        result_date2 = best_match['date2']
        selected_source = best_match['source']
        
        # Log de advertencia si la fuente elegida no es la de modificación (mtime)
        if selected_source != 'fs_mtime':
            # Extraer todos los valores para un log informativo completo
            file1_stats = {source: _fmt(_to_dt(_get_val(file1, source, f'fs_{source}'))) for source, _ in filesystem_sources}
            file2_stats = {source: _fmt(_to_dt(_get_val(file2, source, f'fs_{source}'))) for source, _ in filesystem_sources}
            
            _logger.warning(
                f"ANOMALÍA DE FECHAS: Se ha seleccionado '{selected_source}' por ser la fuente común más antigua "
                f"entre {getattr(file1, 'path', 'f1')} y {getattr(file2, 'path', 'f2')}.\n"
                f"File 1: mtime={file1_stats['mtime']}, ctime={file1_stats['ctime']}, atime={file1_stats['atime']}\n"
                f"File 2: mtime={file2_stats['mtime']}, ctime={file2_stats['ctime']}, atime={file2_stats['atime']}"
            )
        elif verbose:
            _logger.debug(f"    => Match found: {selected_source} (Earliest common FS date)")
            
        return result_date1, result_date2, selected_source

    # -------------------------------------------------------------------------
    # 3. FALLBACK FINAL
    # -------------------------------------------------------------------------
    if verbose: _logger.debug("    !! NO COMMON DATE SOURCE FOUND !!")
    return None


def validate_date_coherence(all_dates: dict) -> dict:
    """
    Valida coherencia entre fechas y detecta anomalías en metadatos.
    
    Esta función aplica varias reglas de validación para detectar metadatos corruptos,
    archivos editados, o transferencias recientes que pueden afectar la confiabilidad
    de las fechas.

    Args:
        all_dates: Dict con todas las fechas del archivo (estructura de get_all_file_dates)

    Returns:
        Dict con resultado de validación:
        {
            'is_valid': bool,              # True si pasa todas las validaciones críticas
            'warnings': list[str],         # Lista de códigos de advertencia
            'confidence': str              # 'high', 'medium', 'low'
        }
        
    Códigos de advertencia:
        - 'EXIF_AFTER_MTIME': EXIF posterior a modification_date (sospechoso)
        - 'EXIF_DIVERGENCE': Más de 1 año entre campos EXIF (probable corrupción)
        - 'DIGITIZED_BEFORE_ORIGINAL': DateTimeDigitized anterior a DateTimeOriginal (imposible)
        - 'RECENT_TRANSFER': Más de 7 días entre creation_date y EXIF (transferencia)
        - 'SOFTWARE_DETECTED': Campo Software presente (archivo editado)
        - 'GPS_DIVERGENCE': GPS date muy diferente de EXIF (más de 1 día)
        
    Examples:
        >>> # Fechas coherentes
        >>> dates = {
        ...     'exif_date_time_original': datetime(2023, 1, 15, 10, 30),
        ...     'modification_date': datetime(2023, 1, 16, 12, 0)
        ... }
        >>> validate_date_coherence(dates)
        {'is_valid': True, 'warnings': [], 'confidence': 'high'}
        
        >>> # EXIF posterior a mtime (sospechoso)
        >>> dates = {
        ...     'exif_date_time_original': datetime(2024, 1, 15, 10, 30),
        ...     'modification_date': datetime(2023, 1, 16, 12, 0)
        ... }
        >>> validate_date_coherence(dates)
        {'is_valid': False, 'warnings': ['EXIF_AFTER_MTIME'], 'confidence': 'low'}
    """
    from datetime import timedelta
    
    warnings = []
    is_valid = True
    
    # Extraer fechas relevantes
    exif_original = all_dates.get('exif_date_time_original')
    exif_create = all_dates.get('exif_create_date')
    exif_digitized = all_dates.get('exif_date_digitized')
    exif_gps = all_dates.get('exif_gps_date')
    exif_software = all_dates.get('exif_software')
    modification_date = all_dates.get('modification_date')
    creation_date = all_dates.get('creation_date')
    
    # Validación 1: EXIF posterior a modification_date (sospechoso)
    if exif_original and modification_date:
        if exif_original > modification_date:
            warnings.append('EXIF_AFTER_MTIME')
            is_valid = False
    
    # Validación 2: Divergencia entre campos EXIF (más de 1 año)
    exif_dates = [d for d in [exif_original, exif_create, exif_digitized] if d is not None]
    if len(exif_dates) >= 2:
        min_exif = min(exif_dates)
        max_exif = max(exif_dates)
        if (max_exif - min_exif) > timedelta(days=365):
            warnings.append('EXIF_DIVERGENCE')
            is_valid = False
    
    # Validación 3: DateTimeDigitized anterior a DateTimeOriginal (imposible)
    if exif_original and exif_digitized:
        if exif_digitized < exif_original:
            warnings.append('DIGITIZED_BEFORE_ORIGINAL')
            is_valid = False
    
    # Validación 4: Transferencia reciente (creation_date muy diferente de EXIF)
    if exif_original and creation_date:
        diff = abs((creation_date - exif_original).days)
        if diff > 7:
            warnings.append('RECENT_TRANSFER')
            # No marca como inválido, solo advertencia
    
    # Validación 5: Software detectado (archivo editado)
    if exif_software:
        warnings.append('SOFTWARE_DETECTED')
        # No marca como inválido, solo informativo
    
    # Validación 6: GPS date muy diferente de EXIF
    if exif_gps and exif_original:
        diff = abs((exif_gps - exif_original).days)
        if diff > 1:
            warnings.append('GPS_DIVERGENCE')
            # No marca como inválido, puede ser zona horaria
    
    # Determinar nivel de confianza
    if not is_valid:
        confidence = 'low'
    elif len(warnings) >= 2:
        confidence = 'medium'
    elif len(warnings) == 1:
        confidence = 'medium'
    else:
        confidence = 'high'
    
    return {
        'is_valid': is_valid,
        'warnings': warnings,
        'confidence': confidence
    }


def select_chosen_date(all_dates: dict) -> tuple[Optional[datetime], Optional[str]]:
    """
    Selecciona la fecha más representativa de un archivo según lógica de priorización avanzada.
    
    LÓGICA DE PRIORIZACIÓN (CORREGIDA):
    
    PASO 1 - PRIORIDAD MÁXIMA (Fechas EXIF de cámara):
    1. DateTimeOriginal con OffsetTimeOriginal (la más precisa)
    2. DateTimeOriginal sin OffsetTimeOriginal
    3. CreateDate
    4. DateTimeDigitized
    
    Regla: Se comparan TODAS estas fechas EXIF y se devuelve la MÁS ANTIGUA.
    Si existe al menos una de estas fechas, NO se continúa a los siguientes pasos.
    
    PASO 2 - PRIORIDAD SECUNDARIA (Fechas alternativas):
    5. Fecha extraída del nombre de archivo
       - Útil para WhatsApp y otros archivos sin EXIF
       - Patrones: IMG-YYYYMMDD-WA, Screenshot_YYYYMMDD_HHMMSS, etc.
    
    6. Video metadata (creation_time de ffprobe)
       - Para archivos de video
    
    PASO 3 - VALIDACIÓN GPS (NO se usa como fecha principal):
    - GPS DateStamp se valida contra DateTimeOriginal
    - Si difiere más de 24 horas, se registra warning
    - GPS está en UTC y puede estar redondeado, por lo que NO es confiable
    
    PASO 4 - ÚLTIMO RECURSO (Fechas de sistema):
    7. creation_date y modification_date del sistema de archivos
       - Se comparan ambas y se devuelve la más antigua
       - Menos confiables por cambiar al copiar/mover
    
    VALIDACIÓN:
    - Llama a validate_date_coherence() para detectar metadatos corruptos
    - Loguea warnings encontrados
    - Valida coherencia entre GPS DateStamp y DateTimeOriginal
    
    Args:
        all_dates: Dict con todas las fechas disponibles (estructura de get_all_file_dates)

    Returns:
        Tupla (fecha_seleccionada, fuente_seleccionada)
        - fecha_seleccionada: datetime de la fecha según la prioridad
        - fuente_seleccionada: string descriptivo de la fuente
        - Devuelve (None, None) si no hay fechas disponibles
    
    Examples:
        >>> # Imagen con EXIF completo
        >>> dates = {
        ...     'exif_date_time_original': datetime(2021, 8, 4, 18, 49, 23),
        ...     'exif_gps_date': datetime(2021, 8, 4, 20, 0, 0),
        ...     'exif_offset_time': '+02:00'
        ... }
        >>> select_chosen_date(dates)
        (datetime(2021, 8, 4, 18, 49, 23), 'EXIF DateTimeOriginal (+02:00)')
        
        >>> # WhatsApp sin EXIF
        >>> dates = {
        ...     'filename_date': datetime(2024, 11, 13, 0, 0),
        ...     'creation_date': datetime(2024, 11, 15, 12, 0)
        ... }
        >>> select_chosen_date(dates)
        (datetime(2024, 11, 13, 0, 0), 'Filename')
    """
    # Validar coherencia de fechas
    validation = validate_date_coherence(all_dates)
    
    # Loguear warnings si existen
    if validation['warnings']:
        _logger.debug(f"Warnings de coherencia: {', '.join(validation['warnings'])} (confidence: {validation['confidence']})")
    
    # ============================================================================
    # PASO 1: PRIORIDAD MÁXIMA - Fechas EXIF de cámara (devolver la más antigua)
    # ============================================================================
    exif_camera_dates = []
    
    # DateTimeOriginal con zona horaria
    if all_dates.get('exif_date_time_original') and all_dates.get('exif_offset_time'):
        exif_camera_dates.append((
            all_dates['exif_date_time_original'],
            f"EXIF DateTimeOriginal ({all_dates['exif_offset_time']})"
        ))
    
    # DateTimeOriginal sin zona horaria
    elif all_dates.get('exif_date_time_original'):
        exif_camera_dates.append((
            all_dates['exif_date_time_original'],
            'EXIF DateTimeOriginal'
        ))
    
    # CreateDate
    if all_dates.get('exif_create_date'):
        exif_camera_dates.append((
            all_dates['exif_create_date'],
            'EXIF CreateDate'
        ))
    
    # DateTimeDigitized
    if all_dates.get('exif_date_digitized'):
        exif_camera_dates.append((
            all_dates['exif_date_digitized'],
            'EXIF DateTimeDigitized'
        ))
    
    # Si hay al menos una fecha EXIF de cámara, devolver la más antigua
    if exif_camera_dates:
        earliest_exif = min(exif_camera_dates, key=lambda x: x[0])
        selected_date, source = earliest_exif
        
        # Validar coherencia GPS vs DateTimeOriginal
        _validate_gps_coherence(all_dates, selected_date)
        
        return selected_date, source
    
    # ============================================================================
    # PASO 2: PRIORIDAD SECUNDARIA - Fechas alternativas
    # ============================================================================
    
    # Fecha del nombre de archivo
    if all_dates.get('filename_date'):
        return all_dates['filename_date'], 'Filename'
    
    # Video metadata
    if all_dates.get('video_metadata_date'):
        return all_dates['video_metadata_date'], 'Video Metadata'
    
    # ============================================================================
    # PASO 3: GPS DateStamp - Solo para validación (ya ejecutado en PASO 1)
    # ============================================================================
    # La validación GPS se ejecuta en el PASO 1 si hay fechas EXIF disponibles
    # GPS no se usa como fecha principal debido a problemas de redondeo y UTC
    
    # ============================================================================
    # PASO 4: ÚLTIMO RECURSO - Fechas del sistema de archivos
    # ============================================================================
    fs_dates = []
    
    if all_dates.get('filesystem_creation_date'):
        fs_dates.append((
            all_dates['filesystem_creation_date'],
            all_dates.get('filesystem_creation_source', 'creation')
        ))
    
    if all_dates.get('filesystem_modification_date'):
        fs_dates.append((
            all_dates['filesystem_modification_date'],
            'mtime'
        ))
    
    if fs_dates:
        earliest_fs = min(fs_dates, key=lambda x: x[0])
        return earliest_fs[0], earliest_fs[1]
    
    # No hay fechas disponibles
    return None, None


def _normalize_date_source(source: str) -> str:
    """
    Normaliza el nombre de la fuente de fecha al formato de caché.
    
    Convierte los nombres descriptivos de select_chosen_date() al formato
    compacto usado en metadata_cache.
    
    Args:
        source: Nombre de fuente de select_chosen_date() 
                (ej: 'EXIF DateTimeOriginal (+02:00)', 'Filename', 'mtime')
    
    Returns:
        Nombre normalizado para caché:
        - 'exif_datetime_original_tz': DateTimeOriginal con timezone
        - 'exif_datetime_original': DateTimeOriginal sin timezone
        - 'exif_create_date': CreateDate
        - 'exif_datetime_digitized': DateTimeDigitized
        - 'filename': Extraída del nombre de archivo
        - 'video': Metadata de video  
        - 'mtime': Modification time
        - 'ctime': Creation time
        - 'other': Cualquier otra fuente
    """
    if not source:
        return 'unknown'
    
    source_lower = source.lower()
    
    # EXIF DateTimeOriginal con timezone
    if 'datetimeoriginal' in source_lower and '(' in source:
        return 'exif_datetime_original_tz'
    
    # EXIF DateTimeOriginal sin timezone
    if 'datetimeoriginal' in source_lower:
        return 'exif_datetime_original'
    
    # EXIF CreateDate
    if 'createdate' in source_lower:
        return 'exif_create_date'
    
    # EXIF DateTimeDigitized
    if 'datetimedigitized' in source_lower or 'digitized' in source_lower:
        return 'exif_datetime_digitized'
    
    # Filename
    if 'filename' in source_lower:
        return 'filename'
    
    # Video metadata
    if 'video' in source_lower:
        return 'video'
    
    # Filesystem timestamps
    if source_lower == 'mtime':
        return 'mtime'
    if source_lower in ['ctime', 'creation', 'birthtime']:
        return 'ctime'
    
    # Otras fuentes desconocidas
    return 'other'


def _validate_gps_coherence(all_dates: dict, selected_date: datetime) -> None:
    """
    Valida coherencia entre GPS DateStamp y DateTimeOriginal.
    
    GPS DateStamp puede diferir significativamente de DateTimeOriginal debido a:
    - GPS está siempre en UTC (sin zona horaria local)
    - Muchos dispositivos redondean GPS timestamp a horas completas
    - GPS puede estar ausente o incorrecto por problemas de señal
    
    Esta función registra warnings cuando la diferencia es mayor a 24 horas.
    
    Args:
        all_dates: Dict con todas las fechas disponibles
        selected_date: Fecha seleccionada (normalmente DateTimeOriginal)
    """
    gps_date = all_dates.get('exif_gps_date')
    
    if not gps_date:
        return
    
    # Calcular diferencia en segundos
    diff_seconds = abs((gps_date - selected_date).total_seconds())
    
    # GPS debe estar dentro de ±24 horas de DateTimeOriginal
    if diff_seconds > 86400:  # 24 horas en segundos
        diff_hours = diff_seconds / 3600
        _logger.warning(
            f"GPS DateStamp ({gps_date.strftime('%Y-%m-%d %H:%M:%S')}) difiere "
            f"significativamente de DateTimeOriginal ({selected_date.strftime('%Y-%m-%d %H:%M:%S')}). "
            f"Diferencia: {diff_hours:.1f} horas. "
            f"Posible problema de zona horaria o GPS incorrecto."
        )

def get_date_from_file(file_path: Path, verbose: bool = False, metadata_cache=None, skip_expensive_ops: bool = False) -> Optional[datetime]:
    """
    Extrae la fecha más representativa de un archivo mediante análisis de múltiples fuentes.
    
    Esta función es un wrapper conveniente que:
    1. Intenta obtener la fecha desde metadata_cache si está disponible
    2. Si no está cacheada, recopila todas las fechas disponibles (EXIF y sistema de archivos)
    3. Delega la lógica de priorización a select_chosen_date()
    4. Cachea el resultado en metadata_cache para reutilización futura
    5. Opcionalmente registra información detallada del proceso
    
    La lógica de priorización está implementada en select_chosen_date() y prioriza
    los metadatos EXIF sobre las fechas del sistema de archivos.

    Args:
        file_path: Ruta al archivo a analizar
        verbose: Si True, muestra análisis detallado en modo INFO. Si False, solo en DEBUG
        metadata_cache: Instancia opcional de FileInfoRepositoryCache para reutilizar fechas calculadas
        skip_expensive_ops: Si True y metadata_cache no tiene la fecha, usa fallback rápido (mtime)
                           en lugar de calcular con ffprobe/EXIF. Útil para análisis masivos.

    Returns:
        datetime: Fecha seleccionada según la lógica de priorización
        None: Si no se puede obtener ninguna fecha válida
        
    See Also:
        select_chosen_date(): Implementación de la lógica de priorización
        get_all_file_dates(): Extracción de todas las fechas disponibles
    """
    try:
        # OPTIMIZACIÓN 1: Intentar obtener de metadata_cache primero
        if metadata_cache:
            cached_date, cached_source = metadata_cache.get_selected_date(file_path)
            if cached_date is not None:
                _logger.debug(f"✓ Fecha obtenida de caché: {file_path.name} = {cached_source}")
                return cached_date
        
        # Si skip_expensive_ops y no está en caché, usar fallback rápido (filesystem_modification_date)
        if skip_expensive_ops and metadata_cache:
            # Usar API consistente del cache (puede tener mtime cacheado del scan)
            mtime_date = metadata_cache.get_filesystem_modification_date(file_path)
            if mtime_date:
                _logger.debug(f"⚡ Fecha rápida (filesystem_modification_date) para {file_path.name}: {mtime_date}")
                return mtime_date
            # Fallback final si el cache no tiene nada (edge case)
            mtime_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            _logger.debug(f"⚡ Fecha rápida (st_mtime directo) para {file_path.name}: {mtime_date}")
            return mtime_date
        
        # OPTIMIZACIÓN 2: Usar versión cacheada para evitar lecturas EXIF repetidas
        # La clave incluye mtime para invalidar caché si el archivo se modifica
        all_dates = get_all_file_dates(file_path)
        
        # Seleccionar la fecha más antigua según prioridad
        selected_date, selected_source = select_chosen_date(all_dates)
        
        # OPTIMIZACIÓN 3: Cachear resultado en metadata_cache para futuros usos
        if metadata_cache and selected_date:
            # Normalizar el nombre de la fuente al formato de caché
            normalized_source = _normalize_date_source(selected_source)
            metadata_cache.set_selected_date(file_path, selected_date, normalized_source)
        
        # OPTIMIZACIÓN 4: Solo formatear strings si realmente se va a loguear
        # Esto evita overhead de formateo cuando logging está en INFO/WARNING
        if verbose or _logger.isEnabledFor(logging.DEBUG):
            if selected_date:
                # Lazy evaluation: solo construir el mensaje si se necesita
                log_func = _logger.info if verbose else _logger.debug
                
                # Formato compacto: nombre | fechas disponibles → seleccionada
                dates_str = []
                
                # Mostrar TODOS los campos EXIF disponibles
                if all_dates.get('exif_date_time_original'):
                    tz = f" {all_dates.get('exif_offset_time')}" if all_dates.get('exif_offset_time') else ""
                    dates_str.append(f"EXIF_DTO:{all_dates['exif_date_time_original'].strftime('%Y%m%d_%H%M%S')}{tz}")
                if all_dates.get('exif_create_date'):
                    dates_str.append(f"EXIF_CD:{all_dates['exif_create_date'].strftime('%Y%m%d_%H%M%S')}")
                if all_dates.get('exif_date_digitized'):
                    dates_str.append(f"EXIF_DD:{all_dates['exif_date_digitized'].strftime('%Y%m%d_%H%M%S')}")
                if all_dates.get('exif_gps_date'):
                    dates_str.append(f"GPS:{all_dates['exif_gps_date'].strftime('%Y%m%d_%H%M%S')}")
                
                # Mostrar metadata de video
                if all_dates.get('video_metadata_date'):
                    dates_str.append(f"Video:{all_dates['video_metadata_date'].strftime('%Y%m%d_%H%M%S')}")
                
                # Mostrar fecha del nombre de archivo
                if all_dates.get('filename_date'):
                    dates_str.append(f"Filename:{all_dates['filename_date'].strftime('%Y%m%d_%H%M%S')}")
                
                # Mostrar software si está presente
                if all_dates.get('exif_software'):
                    dates_str.append(f"SW:{all_dates['exif_software'][:20]}")  # Truncar a 20 chars
                
                # Mostrar fechas del sistema de archivos
                if all_dates.get('filesystem_creation_date'):
                    dates_str.append(f"{all_dates.get('filesystem_creation_source', 'creation')}:{all_dates['filesystem_creation_date'].strftime('%Y%m%d_%H%M%S')}")
                if all_dates.get('filesystem_modification_date'):
                    dates_str.append(f"mtime:{all_dates['filesystem_modification_date'].strftime('%Y%m%d_%H%M%S')}")
                
                log_func(
                    f"{file_path.name} | {' | '.join(dates_str)} → "
                    f"✓ {selected_source}:{selected_date.strftime('%Y%m%d_%H%M%S')}"
                )

        return selected_date

    except Exception as e:
        _logger.error(f"Error obteniendo fecha de {file_path}: {e}")
        return None


def format_renamed_name(date: datetime, file_type: str, extension: str, sequence: Optional[int] = None) -> str:
    """
    Genera nombre de archivo renombrado en formato estandarizado
    
    Args:
        date: Fecha a usar en el nombre
        file_type: Tipo de archivo ('PHOTO', 'VIDEO', etc.)
        extension: Extensión del archivo (incluyendo punto)
        sequence: Número de secuencia opcional para evitar conflictos
        
    Returns:
        Nombre de archivo formateado: YYYYMMDD_HHMMSS_TYPE[_SEQ].EXT
        
    Examples:
        >>> from datetime import datetime
        >>> format_renamed_name(datetime(2023, 1, 15, 10, 30, 45), 'PHOTO', '.jpg')
        '20230115_103045_PHOTO.JPG'
        
        >>> format_renamed_name(datetime(2023, 1, 15, 10, 30, 45), 'VIDEO', '.mov', sequence=5)
        '20230115_103045_VIDEO_005.MOV'
    """
    base_name = date.strftime('%Y%m%d_%H%M%S')
    type_part = f"_{file_type}"
    
    if sequence is not None and sequence > 0:
        sequence_part = f"_{sequence:03d}"
    else:
        sequence_part = ""
    
    extension_part = extension.upper()
    
    return f"{base_name}{type_part}{sequence_part}{extension_part}"


def is_renamed_filename(filename: str) -> bool:
    """
    Verifica si un nombre de archivo sigue el patrón de nombres renombrados
    
    Args:
        filename: Nombre del archivo a verificar
        
    Returns:
        True si el nombre sigue el patrón YYYYMMDD_HHMMSS_TYPE[_SEQ].EXT
        
    Examples:
        >>> is_renamed_filename('20230115_103045_PHOTO.JPG')
        True
        
        >>> is_renamed_filename('20230115_103045_VIDEO_042.MOV')
        True
        
        >>> is_renamed_filename('IMG_1234.JPG')
        False
    """
    import re
    
    # Patrón: YYYYMMDD_HHMMSS_TYPE[_SEQ].EXT
    pattern = r'^\d{8}_\d{6}_[A-Z]+(?:_\d{3})?\.[A-Z]{2,4}$'
    return bool(re.match(pattern, filename))


def parse_renamed_name(filename: str | Path) -> Optional[dict]:
    """
    Parsea un nombre de archivo renombrado y extrae sus componentes
    
    Args:
        filename: Nombre del archivo o Path object
        
    Returns:
        Dict con componentes o None si no es un nombre válido:
        {
            'date': datetime,
            'type': str,  # 'PHOTO' o 'VIDEO'
            'sequence': int or None,
            'extension': str,  # '.JPG', '.MOV', etc.
            'is_renamed': bool  # Siempre True si llega aquí
        }
        
    Examples:
        >>> parse_renamed_name('20230115_103045_PHOTO.JPG')
        {'date': datetime(2023, 1, 15, 10, 30, 45), 'type': 'PHOTO', 'sequence': None, 'extension': '.JPG', 'is_renamed': True}
        
        >>> parse_renamed_name('20230115_103045_VIDEO_042.MOV')
        {'date': datetime(2023, 1, 15, 10, 30, 45), 'type': 'VIDEO', 'sequence': 42, 'extension': '.MOV', 'is_renamed': True}
    """
    if isinstance(filename, Path):
        filename = filename.name
    
    if not is_renamed_filename(filename):
        return None
    
    import re
    
    # Patrón con grupos nombrados - solo acepta PHOTO y VIDEO
    pattern = r'^(?P<date>\d{8}_\d{6})_(?P<type>PHOTO|VIDEO)(?:_(?P<sequence>\d{3}))?\.(?P<ext>[A-Z]{2,4})$'
    match = re.match(pattern, filename)
    
    if not match:
        return None
    
    groups = match.groupdict()
    
    # Parsear fecha
    date_str = groups['date']
    try:
        parsed_date = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
    except ValueError:
        return None
    
    # Parsear secuencia
    sequence = None
    if groups['sequence']:
        try:
            sequence = int(groups['sequence'])
        except ValueError:
            return None
    
    return {
        'date': parsed_date,
        'type': groups['type'],
        'sequence': sequence,
        'extension': f".{groups['ext']}",
        'is_renamed': True
    }


def extract_date_from_filename(filename: str) -> Optional[datetime]:
    """
    Intenta extraer una fecha del nombre de archivo usando patrones comunes
    
    Args:
        filename: Nombre del archivo (sin path)
        
    Returns:
        datetime si se encuentra un patrón válido, None en caso contrario
        
    Patrones soportados:
        - IMG_YYYYMMDD_HHMMSS.ext
        - DSC_YYYYMMDD_HHMMSS.ext  
        - YYYYMMDD_HHMMSS.ext
        - YYYY-MM-DD_HH-MM-SS.ext
        - WhatsApp: IMG-YYYYMMDD-WAXXXX.ext
    """
    import re
    from pathlib import Path
    
    # Remover extensión
    name_without_ext = Path(filename).stem
    
    # Patrones de fecha comunes en nombres de archivo
    patterns = [
        # IMG_20231113_123456 o DSC_20231113_123456
        r'(?:IMG|DSC)_(\d{8})_(\d{6})',
        # 20231113_123456 (sin prefijo)
        r'^(\d{8})_(\d{6})',
        # YYYY-MM-DD_HH-MM-SS
        r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})',
        # WhatsApp: IMG-20231113-WA0001
        r'IMG-(\d{8})-WA\d+',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name_without_ext)
        if match:
            groups = match.groups()
            
            try:
                if len(groups) == 2:  # YYYYMMDD_HHMMSS
                    date_str, time_str = groups
                    year, month, day = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
                    hour, minute, second = int(time_str[:2]), int(time_str[2:4]), int(time_str[4:6])
                    
                elif len(groups) == 6:  # YYYY-MM-DD_HH-MM-SS
                    year, month, day, hour, minute, second = map(int, groups)
                    
                elif len(groups) == 1:  # WhatsApp IMG-YYYYMMDD
                    date_str = groups[0]
                    year, month, day = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8])
                    hour = minute = second = 0  # WhatsApp no incluye hora
                    
                else:
                    continue
                    
                # Validar rangos básicos
                if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
                    continue
                    
                return datetime(year, month, day, hour, minute, second)
                
            except (ValueError, TypeError):
                continue
    
    return None


def get_all_file_dates(file_path: Path) -> dict:
    """
    Obtiene toda la información de fechas disponible para un archivo
    
    Args:
        file_path: Ruta al archivo a analizar
    
    Returns:
        Dict con todas las fechas encontradas y sus fuentes:
        {
            'exif_date_time_original': datetime or None,  # DateTimeOriginal
            'exif_create_date': datetime or None,         # CreateDate/DateTime
            'exif_date_digitized': datetime or None,      # DateTimeDigitized
            'exif_gps_date': datetime or None,            # GPS DateStamp
            'exif_offset_time': str or None,              # Zona horaria
            'exif_software': str or None,                 # Software usado
            'video_metadata_date': datetime or None,      # Metadata de video
            'filename_date': datetime or None,            # Fecha del nombre
            'filesystem_creation_date': datetime or None, # Fecha de creación FS
            'filesystem_creation_source': str or None,    # Fuente de creación
            'filesystem_modification_date': datetime or None, # Fecha de modificación
            'filesystem_access_date': datetime or None    # Fecha de acceso
        }
    """
    from config import Config
    from utils.file_utils import get_exif_from_image, get_exif_from_video, is_image_file, get_file_type
    
    result = {
        'exif_date_time_original': None,
        'exif_create_date': None,
        'exif_date_digitized': None,
        'exif_gps_date': None,
        'exif_offset_time': None,
        'exif_software': None,
        'video_metadata_date': None,
        'filename_date': None,
        'filesystem_creation_date': None,
        'filesystem_creation_source': None,
        'filesystem_modification_date': None,
        'filesystem_access_date': None
    }
    
    try:
        # 1. Intentar obtener todas las fechas EXIF disponibles (solo para imágenes)
        if is_image_file(file_path):
            exif_dates = get_exif_from_image(file_path)
            result['exif_date_time_original'] = exif_dates.get('DateTimeOriginal')
            result['exif_create_date'] = exif_dates.get('CreateDate')
            result['exif_date_digitized'] = exif_dates.get('DateTimeDigitized')
            result['exif_gps_date'] = exif_dates.get('GPSDateStamp')
            result['exif_offset_time'] = exif_dates.get('OffsetTimeOriginal')
            result['exif_software'] = exif_dates.get('Software')
        
        # 2. Intentar obtener metadata de video (solo si está habilitado en configuración)
        if get_file_type(file_path) == 'VIDEO' and Config.USE_VIDEO_METADATA:
            result['video_metadata_date'] = get_exif_from_video(file_path)
        
        # 3. Intentar extraer fecha del nombre de archivo
        result['filename_date'] = extract_date_from_filename(file_path.name)
        
        # 4. Obtener fechas del sistema de archivos
        stat = file_path.stat()
        
        # Fecha de creación (birth time en macOS/Unix, ctime en Windows/Linux)
        if hasattr(stat, 'st_birthtime'):
            result['filesystem_creation_date'] = datetime.fromtimestamp(stat.st_birthtime)
            result['filesystem_creation_source'] = 'birth'
        elif hasattr(stat, 'st_ctime'):
            result['filesystem_creation_date'] = datetime.fromtimestamp(stat.st_ctime)
            result['filesystem_creation_source'] = 'ctime'
        
        # Fecha de modificación
        result['filesystem_modification_date'] = datetime.fromtimestamp(stat.st_mtime)
        
        # Fecha de último acceso
        result['filesystem_access_date'] = datetime.fromtimestamp(stat.st_atime)
            
    except Exception as e:
        _logger.error(f"Error obteniendo fechas de {file_path}: {e}")
    
    return result
