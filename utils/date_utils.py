"""
Utilidades para extracción de fechas de archivos multimedia
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from utils.logger import get_logger

_logger = get_logger("DateUtils")

def get_file_date(file_path: Path, verbose: bool = False) -> Optional[datetime]:
    """
    Obtiene la fecha más antigua disponible de un archivo

    Orden de prioridad:
    1. Fecha EXIF (si disponible)
    2. Fecha de creación del archivo
    3. Fecha de modificación del archivo

    Args:
        file_path: Ruta al archivo
        verbose: Si True, muestra análisis detallado en modo INFO. Si False, solo en DEBUG

    Returns:
        datetime o None si no se puede obtener
    """
    try:
        # Determinar si mostrar logging detallado
        show_details = verbose or _logger.isEnabledFor(logging.DEBUG)
        log_func = _logger.info if verbose else _logger.debug
        
        # 1. Intentar obtener fecha EXIF
        exif_date = get_exif_date(file_path)

        # 2. Obtener fecha de creación
        stat = file_path.stat()
        creation_time = None
        creation_source = None
        
        if hasattr(stat, 'st_birthtime'):
            creation_time = datetime.fromtimestamp(stat.st_birthtime)
            creation_source = 'birth'
        elif hasattr(stat, 'st_ctime'):
            creation_time = datetime.fromtimestamp(stat.st_ctime)
            creation_source = 'ctime'

        # 3. Obtener fecha de modificación
        modification_time = datetime.fromtimestamp(stat.st_mtime)

        # Seleccionar la fecha más antigua
        selected_date = None
        selected_source = None
        
        if exif_date:
            selected_date = exif_date
            selected_source = 'EXIF'
        elif creation_time and modification_time:
            if creation_time <= modification_time:
                selected_date = creation_time
                selected_source = creation_source
            else:
                selected_date = modification_time
                selected_source = 'mtime'
        elif modification_time:
            selected_date = modification_time
            selected_source = 'mtime'
        elif creation_time:
            selected_date = creation_time
            selected_source = creation_source

        # Log compacto en una sola línea con toda la información
        if show_details and selected_date:
            # Formato compacto: nombre | fechas disponibles → seleccionada
            dates_str = []
            if exif_date:
                dates_str.append(f"EXIF:{exif_date.strftime('%Y%m%d_%H%M%S')}")
            if creation_time:
                dates_str.append(f"{creation_source}:{creation_time.strftime('%Y%m%d_%H%M%S')}")
            dates_str.append(f"mtime:{modification_time.strftime('%Y%m%d_%H%M%S')}")
            
            log_func(
                f"{file_path.name} | {' | '.join(dates_str)} → "
                f"✓ {selected_source}:{selected_date.strftime('%Y%m%d_%H%M%S')}"
            )

        return selected_date

    except Exception as e:
        _logger.error(f"Error obteniendo fecha de {file_path}: {e}")
        return None

def get_exif_date(file_path: Path) -> Optional[datetime]:
    """
    Intenta extraer fecha EXIF de una imagen

    Args:
        file_path: Ruta a la imagen

    Returns:
        datetime o None si no se puede obtener
    """
    try:
        # Intentar con PIL/Pillow
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(file_path) as image:
            exif_data = image._getexif()

            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)

                    # Buscar fecha original
                    if tag in ['DateTimeOriginal', 'DateTime', 'DateTimeDigitized']:
                        try:
                            return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                        except ValueError:
                            continue

        return None

    except ImportError:
        # PIL no disponible, continuar sin EXIF
        return None
    except Exception as e:
        # Error accediendo a EXIF
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


def get_all_file_dates(file_path: Path) -> dict:
    """
    Obtiene toda la información de fechas disponible para un archivo
    
    Returns:
        Dict con todas las fechas encontradas y sus fuentes:
        {
            'exif_date': datetime or None,
            'creation_date': datetime or None,
            'creation_source': 'birth'/'ctime' or None,
            'modification_date': datetime or None,
            'access_date': datetime or None,
            'selected_date': datetime or None,
            'selected_source': str or None
        }
    """
    result = {
        'exif_date': None,
        'creation_date': None,
        'creation_source': None,
        'modification_date': None,
        'access_date': None,
        'selected_date': None,
        'selected_source': None
    }
    
    try:
        # 1. Intentar obtener fecha EXIF
        result['exif_date'] = get_exif_date(file_path)
        
        # 2. Obtener fechas del sistema de archivos
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
        
        # 3. Seleccionar la fecha más antigua (lógica del get_file_date original)
        if result['exif_date']:
            result['selected_date'] = result['exif_date']
            result['selected_source'] = 'EXIF'
        elif result['creation_date'] and result['modification_date']:
            if result['creation_date'] <= result['modification_date']:
                result['selected_date'] = result['creation_date']
                result['selected_source'] = result['creation_source']
            else:
                result['selected_date'] = result['modification_date']
                result['selected_source'] = 'mtime'
        elif result['modification_date']:
            result['selected_date'] = result['modification_date']
            result['selected_source'] = 'mtime'
        elif result['creation_date']:
            result['selected_date'] = result['creation_date']
            result['selected_source'] = result['creation_source']
            
    except Exception as e:
        _logger.error(f"Error obteniendo fechas de {file_path}: {e}")
    
    return result
