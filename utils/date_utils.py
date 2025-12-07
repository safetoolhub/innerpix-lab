"""
Utilidades para extracción de fechas de archivos multimedia
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from functools import lru_cache
from utils.logger import get_logger

_logger = get_logger("DateUtils")


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
    
    if all_dates.get('creation_date'):
        fs_dates.append((
            all_dates['creation_date'],
            all_dates.get('creation_source', 'creation')
        ))
    
    if all_dates.get('modification_date'):
        fs_dates.append((
            all_dates['modification_date'],
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

def get_date_from_file(file_path: Path, verbose: bool = False, metadata_cache=None) -> Optional[datetime]:
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
        metadata_cache: Instancia opcional de FileMetadataCache para reutilizar fechas calculadas

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
        
        # OPTIMIZACIÓN 2: Usar versión cacheada para evitar lecturas EXIF repetidas
        # La clave incluye mtime para invalidar caché si el archivo se modifica
        mtime = file_path.stat().st_mtime
        all_dates = _get_all_file_dates_cached(str(file_path), mtime)
        
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
                if all_dates.get('creation_date'):
                    dates_str.append(f"{all_dates.get('creation_source', 'creation')}:{all_dates['creation_date'].strftime('%Y%m%d_%H%M%S')}")
                if all_dates.get('modification_date'):
                    dates_str.append(f"mtime:{all_dates['modification_date'].strftime('%Y%m%d_%H%M%S')}")
                
                log_func(
                    f"{file_path.name} | {' | '.join(dates_str)} → "
                    f"✓ {selected_source}:{selected_date.strftime('%Y%m%d_%H%M%S')}"
                )

        return selected_date

    except Exception as e:
        _logger.error(f"Error obteniendo fecha de {file_path}: {e}")
        return None


def get_exif_dates(file_path: Path) -> dict:
    """
    Extrae TODOS los campos de fecha EXIF disponibles de una imagen
    
    NOTA: Solo soporta imágenes (JPEG, PNG, etc.). No hay soporte para EXIF en videos por ahora.

    Args:
        file_path: Ruta a la imagen (NO videos)

    Returns:
        Dict con los campos de fecha EXIF encontrados:
        {
            'DateTimeOriginal': datetime or None,     # Fecha de captura original
            'CreateDate': datetime or None,           # Fecha de creación (DateTime en EXIF)
            'DateTimeDigitized': datetime or None,    # Fecha de digitalización
            'SubSecTimeOriginal': str or None,        # Subsegundos de precisión
            'OffsetTimeOriginal': str or None,        # Zona horaria de captura
            'GPSDateStamp': datetime or None,         # Timestamp GPS
            'Software': str or None                   # Software usado (detecta edición)
        }
    
    Examples:
        >>> # Imagen con EXIF completo
        >>> dates = get_exif_dates(Path('photo.jpg'))
        >>> dates['DateTimeOriginal']
        datetime(2023, 1, 15, 10, 30, 0)
        >>> dates['OffsetTimeOriginal']
        '+01:00'
        >>> dates['Software']
        'Adobe Photoshop CS6'
    """
    result = {
        'DateTimeOriginal': None,
        'CreateDate': None,
        'DateTimeDigitized': None,
        'SubSecTimeOriginal': None,
        'OffsetTimeOriginal': None,
        'GPSDateStamp': None,
        'Software': None
    }
    
    try:
        # Intentar con PIL/Pillow
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS

        # Para archivos HEIC, necesitamos pillow-heif
        if file_path.suffix.lower() in ['.heic', '.heif']:
            try:
                import pillow_heif
                pillow_heif.register_heif_opener()
            except ImportError:
                _logger.warning(f"pillow-heif no disponible, no se puede procesar {file_path.name}")
                return result

        with Image.open(file_path) as image:
            # Obtener datos EXIF - diferente para HEIC vs otros formatos
            exif_data = None
            
            if file_path.suffix.lower() in ['.heic', '.heif']:
                # Para HEIC, los metadatos están en image.info['exif'] como bytes
                exif_bytes = image.info.get('exif')
                if exif_bytes:
                    try:
                        exif_obj = Image.Exif()
                        exif_obj.load(exif_bytes)
                        exif_data = exif_obj._getexif()
                    except Exception:
                        pass
            else:
                # Para otros formatos, usar el método estándar
                exif_data = image._getexif()

            if exif_data:
                gps_info = None
                
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)

                    # Extraer cada campo de fecha EXIF
                    if tag == 'DateTimeOriginal':
                        try:
                            result['DateTimeOriginal'] = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                        except ValueError:
                            pass
                    elif tag == 'DateTime':  # Este es el CreateDate
                        try:
                            result['CreateDate'] = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                        except ValueError:
                            pass
                    elif tag == 'DateTimeDigitized':
                        try:
                            result['DateTimeDigitized'] = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                        except ValueError:
                            pass
                    elif tag == 'SubSecTimeOriginal':
                        result['SubSecTimeOriginal'] = str(value)
                    elif tag == 'OffsetTimeOriginal':
                        result['OffsetTimeOriginal'] = str(value)
                    elif tag == 'Software':
                        result['Software'] = str(value)
                    elif tag == 'GPSInfo':
                        gps_info = value
                
                # Procesar información GPS si existe
                if gps_info:
                    try:
                        gps_date = None
                        gps_time = None
                        
                        for gps_tag_id, gps_value in gps_info.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            
                            if gps_tag == 'GPSDateStamp':
                                gps_date = gps_value
                            elif gps_tag == 'GPSTimeStamp':
                                gps_time = gps_value
                        
                        # Combinar fecha y hora GPS
                        if gps_date and gps_time:
                            try:
                                # GPSDateStamp formato: 'YYYY:MM:DD'
                                # GPSTimeStamp formato: (HH, MM, SS) como tupla de racionales
                                date_str = gps_date.replace(':', '-')
                                
                                # Convertir tupla de racionales a hora
                                hours = int(gps_time[0]) if hasattr(gps_time[0], '__int__') else int(gps_time[0].numerator / gps_time[0].denominator)
                                minutes = int(gps_time[1]) if hasattr(gps_time[1], '__int__') else int(gps_time[1].numerator / gps_time[1].denominator)
                                seconds = int(gps_time[2]) if hasattr(gps_time[2], '__int__') else int(gps_time[2].numerator / gps_time[2].denominator)
                                
                                time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                                
                                result['GPSDateStamp'] = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S')
                            except (ValueError, AttributeError, IndexError, TypeError):
                                pass
                    except Exception:
                        pass

    except ImportError:
        # PIL no disponible, continuar sin EXIF
        pass
    except Exception as e:
        # Error accediendo a EXIF
        _logger.warning(f"Error extrayendo EXIF de {file_path.name}: {e}")
    
    return result


def extract_date_from_filename(filename: str) -> Optional[datetime]:
    """
    Extrae fecha del nombre de archivo usando patrones comunes.
    
    Esta función es útil cuando los metadatos EXIF no están disponibles o son poco confiables,
    como en imágenes recibidas por WhatsApp o screenshots.

    Args:
        filename: Nombre del archivo (con o sin ruta)

    Returns:
        datetime extraído o None si no se encuentra patrón válido
        
    Examples:
        >>> # WhatsApp
        >>> extract_date_from_filename('IMG-20241113-WA0001.jpg')
        datetime(2024, 11, 13, 0, 0)
        >>> extract_date_from_filename('VID-20231225-WA0042.mp4')
        datetime(2023, 12, 25, 0, 0)
        
        >>> # Screenshot con hora
        >>> extract_date_from_filename('Screenshot_20240101_153045.png')
        datetime(2024, 1, 1, 15, 30, 45)
        
        >>> # Cámara genérica
        >>> extract_date_from_filename('DSC_20231215_103022.jpg')
        datetime(2023, 12, 15, 10, 30, 22)
        
        >>> # Formato ISO
        >>> extract_date_from_filename('2024-03-15_vacation.jpg')
        datetime(2024, 3, 15, 0, 0)
        
        >>> # No hay patrón reconocible
        >>> extract_date_from_filename('random_photo.jpg')
        None
    """
    import re
    
    # Extraer solo el nombre del archivo sin ruta
    name = Path(filename).name
    
    # Patrón 1: WhatsApp - IMG-YYYYMMDD-WAXXXX.jpg o VID-YYYYMMDD-WAXXXX.mp4
    pattern_wa = r'(?:IMG|VID)-(\d{8})-WA\d+'
    match = re.search(pattern_wa, name)
    if match:
        try:
            date_str = match.group(1)
            return datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            pass
    
    # Patrón 2: Screenshot_YYYYMMDD_HHMMSS.png
    pattern_screenshot = r'Screenshot[_-](\d{8})[_-](\d{6})'
    match = re.search(pattern_screenshot, name, re.IGNORECASE)
    if match:
        try:
            date_str = match.group(1)
            time_str = match.group(2)
            return datetime.strptime(f"{date_str}_{time_str}", '%Y%m%d_%H%M%S')
        except ValueError:
            pass
    
    # Patrón 3: DSC_YYYYMMDD_HHMMSS.jpg (cámaras genéricas)
    pattern_camera = r'DSC[_-](\d{8})[_-](\d{6})'
    match = re.search(pattern_camera, name, re.IGNORECASE)
    if match:
        try:
            date_str = match.group(1)
            time_str = match.group(2)
            return datetime.strptime(f"{date_str}_{time_str}", '%Y%m%d_%H%M%S')
        except ValueError:
            pass
    
    # Patrón 4: YYYYMMDD_HHMMSS_* (formato general al inicio)
    pattern_generic_time = r'^(\d{8})[_-](\d{6})'
    match = re.search(pattern_generic_time, name)
    if match:
        try:
            date_str = match.group(1)
            time_str = match.group(2)
            return datetime.strptime(f"{date_str}_{time_str}", '%Y%m%d_%H%M%S')
        except ValueError:
            pass
    
    # Patrón 5: YYYYMMDD_* (formato general al inicio sin hora)
    pattern_generic_date = r'^(\d{8})[_-]'
    match = re.search(pattern_generic_date, name)
    if match:
        try:
            date_str = match.group(1)
            return datetime.strptime(date_str, '%Y%m%d')
        except ValueError:
            pass
    
    # Patrón 6: Formato ISO YYYY-MM-DD
    pattern_iso = r'(\d{4})-(\d{2})-(\d{2})'
    match = re.search(pattern_iso, name)
    if match:
        try:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return datetime(year, month, day)
        except (ValueError, OverflowError):
            pass
    
    return None


def get_video_metadata_date(file_path: Path) -> Optional[datetime]:
    """
    Extrae fecha de creación de archivos de video usando exiftool y ffprobe.
    
    PRIORIDAD:
    1. exiftool Keys:CreationDate - Para Live Photos de iPhone (campo correcto)
    2. ffprobe creation_time - Para otros videos
    
    Esta función requiere que exiftool o ffprobe esté instalado en el sistema.
    Si ninguno está disponible, devuelve None sin generar error.

    Args:
        file_path: Ruta al archivo de video

    Returns:
        datetime de la fecha de creación del video o None si no está disponible
        
    Examples:
        >>> # Live Photo MOV con Keys:CreationDate
        >>> get_video_metadata_date(Path('IMG_0017_HAYLIVE.MOV'))
        datetime(2019, 11, 13, 15, 38, 59)
        
        >>> # Video regular con metadata de creación
        >>> get_video_metadata_date(Path('video.mp4'))
        datetime(2024, 1, 15, 14, 30, 0)
        
        >>> # Video sin metadata
        >>> get_video_metadata_date(Path('video_without_metadata.mp4'))
        None
    """
    import shutil
    import subprocess
    import json
    
    # PRIORIDAD 1: Intentar leer Keys:CreationDate con exiftool (Live Photos)
    if shutil.which('exiftool'):
        try:
            result = subprocess.run(
                ['exiftool', '-Keys:CreationDate', '-d', '%Y:%m:%d %H:%M:%S', '-s3', str(file_path)],
                capture_output=True,
                text=True,
                timeout=3
            )
            
            if result.returncode == 0 and result.stdout.strip():
                creation_date_str = result.stdout.strip()
                try:
                    # Formato: "2019:11:13 15:38:59+01:00" o "2019:11:13 15:38:59"
                    # Extraer solo fecha y hora, ignorar zona horaria
                    if '+' in creation_date_str or '-' in creation_date_str[-6:]:
                        # Tiene zona horaria
                        date_part = creation_date_str.rsplit('+', 1)[0].rsplit('-', 1)[0]
                    else:
                        date_part = creation_date_str
                    
                    parsed_date = datetime.strptime(date_part.strip(), '%Y:%m:%d %H:%M:%S')
                    _logger.debug(f"Video {file_path.name}: usando Keys:CreationDate = {parsed_date}")
                    return parsed_date
                except ValueError as e:
                    _logger.debug(f"Error parseando Keys:CreationDate '{creation_date_str}': {e}")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            _logger.debug(f"Error ejecutando exiftool en {file_path.name}: {e}")
    
    # PRIORIDAD 2: Intentar ffprobe creation_time (videos regulares)
    if not shutil.which('ffprobe'):
        _logger.debug("Ni exiftool ni ffprobe disponibles")
        return None
    
    try:
        # Ejecutar ffprobe para obtener metadata
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_entries', 'format_tags=creation_time',
            str(file_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5  # Timeout de 5 segundos
        )
        
        if result.returncode != 0:
            return None
        
        # Parsear JSON
        metadata = json.loads(result.stdout)
        
        # Extraer creation_time
        if 'format-text' in metadata and 'tags' in metadata['format-text']:
            creation_time = metadata['format-text']['tags'].get('creation_time')
            
            if creation_time:
                try:
                    # Formato típico: '2024-01-15T14:30:00.000000Z'
                    # Intentar varios formatos comunes
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S']:
                        try:
                            parsed_date = datetime.strptime(creation_time, fmt)
                            _logger.debug(f"Video {file_path.name}: usando ffprobe creation_time = {parsed_date}")
                            return parsed_date
                        except ValueError:
                            continue
                except Exception:
                    pass
        
        return None
        
    except subprocess.TimeoutExpired:
        _logger.debug(f"Timeout ejecutando ffprobe en {file_path.name}")
        return None
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
        return None
    except Exception as e:
        _logger.debug(f"Error obteniendo metadata de video {file_path.name}: {e}")
        return None


def format_renamed_name(date: datetime, file_type: str, extension: str, sequence: Optional[int] = None) -> str:
    """
    Genera nombre de renombrado en formato YYYYMMDD_HHMMSS_TIPO_NNN.ext

    Args:
        date: Fecha del archivo
        file_type: 'PHOTO' o 'VIDEO'
        extension: Extensión del archivo (incluyendo punto)
        sequence: Número de secuencia opcional (para resolver conflictos)

    Returns:
        Nombre de archivo renombrado
    """
    date_str = date.strftime('%Y%m%d')
    time_str = date.strftime('%H%M%S')

    base_name = f"{date_str}_{time_str}_{file_type}"

    if sequence:
        base_name += f"_{sequence:03d}"

    return base_name + extension.upper()  # Usuario prefiere extensiones en mayúscula

def parse_renamed_name(filename: str) -> Optional[dict]:
    """
    Analiza si un nombre ya corresponde al formato renombrado y extrae sus componentes

    Args:
        filename: Nombre del archivo

    Returns:
        Dict con componentes o None si no está en formato renombrado
    """
    try:
        # Formato esperado: YYYYMMDD_HHMMSS_TIPO[_NNN].ext
        name = Path(filename).stem
        extension = Path(filename).suffix

        parts = name.split('_')

        if len(parts) < 3:
            return None

        # Verificar formato de fecha
        date_part = parts[0]
        if len(date_part) != 8 or not date_part.isdigit():
            return None

        # Verificar formato de tiempo
        time_part = parts[1]
        if len(time_part) != 6 or not time_part.isdigit():
            return None

        # Verificar tipo
        type_part = parts[2]
        if type_part not in ['PHOTO', 'VIDEO']:
            return None

        # Verificar secuencia opcional
        sequence = None
        if len(parts) == 4:
            seq_part = parts[3]
            if len(seq_part) == 3 and seq_part.isdigit():
                sequence = int(seq_part)
            else:
                return None
        elif len(parts) > 4:
            return None

        # Crear datetime
        try:
            file_date = datetime.strptime(f"{date_part}_{time_part}", '%Y%m%d_%H%M%S')
        except ValueError:
            return None

        return {
            'date': file_date,
            'type': type_part,
            'sequence': sequence,
            'extension': extension,
            'is_renamed': True
        }

    except (AttributeError, ValueError, IndexError, OSError):
        return None

def is_renamed_filename(filename: str) -> bool:
    """
    Verifica rápidamente si un archivo ya está en formato renombrado

    Args:
        filename: Nombre del archivo

    Returns:
        True si ya tiene formato de renombrado
    """
    return parse_renamed_name(filename) is not None


@lru_cache(maxsize=10000)
def _get_all_file_dates_cached(file_path_str: str, mtime: float) -> dict:
    """
    Versión cacheada de get_all_file_dates.
    
    OPTIMIZACIÓN: Usa LRU cache para evitar lecturas EXIF repetidas.
    La clave incluye mtime para invalidar caché si el archivo cambia.
    
    Args:
        file_path_str: Ruta como string (para hashabilidad)
        mtime: Timestamp de modificación (invalida cache si cambia)
    
    Returns:
        Dict con todas las fechas (mismo formato que get_all_file_dates)
    """
    return get_all_file_dates(Path(file_path_str))


def get_all_file_dates(file_path: Path) -> dict:
    """
    Obtiene toda la información de fechas disponible para un archivo
    
    NOTA: Esta función NO está cacheada directamente. Usa _get_all_file_dates_cached
    para aprovechar el caché en operaciones masivas.
    
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
            'creation_date': datetime or None,            # Fecha de creación FS
            'creation_source': str or None,               # Fuente de creación
            'modification_date': datetime or None,        # Fecha de modificación
            'access_date': datetime or None               # Fecha de acceso
        }
    """
    from config import Config
    
    result = {
        'exif_date_time_original': None,
        'exif_create_date': None,
        'exif_date_digitized': None,
        'exif_gps_date': None,
        'exif_offset_time': None,
        'exif_software': None,
        'video_metadata_date': None,
        'filename_date': None,
        'creation_date': None,
        'creation_source': None,
        'modification_date': None,
        'access_date': None
    }
    
    try:
        # 1. Intentar obtener todas las fechas EXIF disponibles (solo para imágenes)
        if Config.is_image_file(file_path):
            exif_dates = get_exif_dates(file_path)
            result['exif_date_time_original'] = exif_dates.get('DateTimeOriginal')
            result['exif_create_date'] = exif_dates.get('CreateDate')
            result['exif_date_digitized'] = exif_dates.get('DateTimeDigitized')
            result['exif_gps_date'] = exif_dates.get('GPSDateStamp')
            result['exif_offset_time'] = exif_dates.get('OffsetTimeOriginal')
            result['exif_software'] = exif_dates.get('Software')
        
        # 2. Intentar obtener metadata de video (solo si está habilitado en configuración)
        if Config.get_file_type(file_path) == 'VIDEO' and Config.USE_VIDEO_METADATA:
            result['video_metadata_date'] = get_video_metadata_date(file_path)
        
        # 3. Intentar extraer fecha del nombre de archivo
        result['filename_date'] = extract_date_from_filename(file_path.name)
        
        # 4. Obtener fechas del sistema de archivos
        stat = file_path.stat()
        
        # Fecha de creación (birth time en macOS/Unix, ctime en Windows/Linux)
        if hasattr(stat, 'st_birthtime'):
            result['creation_date'] = datetime.fromtimestamp(stat.st_birthtime)
            result['creation_source'] = 'birth'
        elif hasattr(stat, 'st_ctime'):
            result['creation_date'] = datetime.fromtimestamp(stat.st_ctime)
            result['creation_source'] = 'ctime'
        
        # Fecha de modificación
        result['modification_date'] = datetime.fromtimestamp(stat.st_mtime)
        
        # Fecha de último acceso
        result['access_date'] = datetime.fromtimestamp(stat.st_atime)
            
    except Exception as e:
        _logger.error(f"Error obteniendo fechas de {file_path}: {e}")
    
    return result
