"""
Utilidades para extracción de fechas de archivos multimedia
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

def get_file_date(file_path: Path) -> Optional[datetime]:
    """
    Obtiene la fecha más antigua disponible de un archivo

    Orden de prioridad:
    1. Fecha EXIF (si disponible)
    2. Fecha de creación del archivo
    3. Fecha de modificación del archivo

    Args:
        file_path: Ruta al archivo

    Returns:
        datetime o None si no se puede obtener
    """
    try:
        # Intentar obtener fecha EXIF primero (requiere librerías adicionales)
        exif_date = get_exif_date(file_path)
        if exif_date:
            return exif_date

        # Fallback a fechas del sistema de archivos
        stat = file_path.stat()

        # En Windows st_birthtime, en Unix usar st_mtime como fallback
        if hasattr(stat, 'st_birthtime'):
            # macOS/BSD
            creation_time = datetime.fromtimestamp(stat.st_birthtime)
        elif hasattr(stat, 'st_ctime'):
            # Unix/Linux - puede no ser fecha de creación real
            creation_time = datetime.fromtimestamp(stat.st_ctime)
        else:
            creation_time = None

        modification_time = datetime.fromtimestamp(stat.st_mtime)

        # Retornar la fecha más antigua
        if creation_time and modification_time:
            return min(creation_time, modification_time)
        elif modification_time:
            return modification_time
        elif creation_time:
            return creation_time

        return None

    except Exception as e:
        print(f"Error obteniendo fecha de {file_path}: {e}")
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

def format_normalized_name(date: datetime, file_type: str, extension: str, sequence: Optional[int] = None) -> str:
    """
    Genera nombre normalizado en formato YYYYMMDD_HHMMSS_TIPO_NNN.ext

    Args:
        date: Fecha del archivo
        file_type: 'PHOTO' o 'VIDEO'
        extension: Extensión del archivo (incluyendo punto)
        sequence: Número de secuencia opcional (para resolver conflictos)

    Returns:
        Nombre de archivo normalizado
    """
    date_str = date.strftime('%Y%m%d')
    time_str = date.strftime('%H%M%S')

    base_name = f"{date_str}_{time_str}_{file_type}"

    if sequence:
        base_name += f"_{sequence:03d}"

    return base_name + extension.upper()  # Usuario prefiere extensiones en mayúscula

def parse_normalized_name(filename: str) -> Optional[dict]:
    """
    Analiza si un nombre está ya normalizado y extrae sus componentes

    Args:
        filename: Nombre del archivo

    Returns:
        Dict con componentes o None si no está normalizado
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
            'is_normalized': True
        }

    except Exception:
        return None

def is_normalized_filename(filename: str) -> bool:
    """
    Verifica rápidamente si un archivo ya está normalizado

    Args:
        filename: Nombre del archivo

    Returns:
        True si ya está normalizado
    """
    return parse_normalized_name(filename) is not None
