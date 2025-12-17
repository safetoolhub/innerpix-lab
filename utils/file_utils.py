"""Utilities for file operations shared across services.

Organized by thematic categories:

1. FILE TYPE DETECTION:
   - is_image_file(filename)
   - is_video_file(filename)
   - is_media_file(filename)
   - is_supported_file(filename)
   - get_file_type(filename)

2. SOURCE/ORIGIN DETECTION:
   - detect_file_source(filename, file_path, exif_data)
   - is_whatsapp_file(filename, file_path)

3. FILE VALIDATION:
   - validate_file_exists(path)
   - validate_directory_exists(path)
   - to_path(obj, attr_names)

4. FILE HASHING:
   - calculate_file_hash(file_path, chunk_size, cache)

5. BACKUP OPERATIONS:
   - launch_backup_creation(files, base_directory, backup_prefix, progress_callback, metadata_name)

6. FILE SYSTEM OPERATIONS:
   - cleanup_empty_directories(root_directory)
   - delete_file_securely(file_path)
   - find_next_available_name(base_path, base_name, extension)

7. METADATA EXTRACTION:
   - get_file_stat_info(file_path)
   - get_exif_from_image(file_path)
   - get_exif_from_video(file_path)

8. DATA STRUCTURES:
   - FileInfo (dataclass)
   - validate_and_get_file_info(file_path)

These are pure helpers designed to centralize duplicated code from services.
"""
from pathlib import Path
from datetime import datetime
import shutil
import re
from typing import Iterable, Optional, Tuple, List, Callable
import hashlib
from dataclasses import dataclass
from utils.format_utils import format_size
from utils.callback_utils import safe_progress_callback
from utils.logger import get_logger

# =============================================================================
# CONSTANTS
# =============================================================================

# Patrones de WhatsApp (iPhone y Android)
WHATSAPP_PATTERNS = [
    r'^IMG-\d{8}-WA\d{4}\..*$',  # IMG-20231025-WA0001.jpg (Android)
    r'^VID-\d{8}-WA\d{4}\..*$',  # VID-20231025-WA0001.mp4 (Android)
    r'^AUD-\d{8}-WA\d{4}\..*$',  # AUD-20231025-WA0001.opus (Android)
    r'^PTT-\d{8}-WA\d{4}\..*$',  # PTT (voice notes)
    r'^WhatsApp\s+Image\s+\d{4}-\d{2}-\d{2}\s+at\s+.*\..*$',  # WhatsApp Image 2023-10-25 at 12.34.56.jpg
    r'^WhatsApp\s+Video\s+\d{4}-\d{2}-\d{2}\s+at\s+.*\..*$',  # WhatsApp Video 2023-10-25 at 12.34.56.mp4
    r'^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}(_\d{3})?\.(jpg|jpeg|png|mp4|mov|heic)$',  # UUID format (iPhone export) with optional suffix
]


# =============================================================================
# FILE TYPE DETECTION
# =============================================================================

def is_image_file(filename: str | Path) -> bool:
    """
    Verifica si un archivo es una imagen soportada.
    
    Args:
        filename: Nombre o Path del archivo a verificar
    
    Returns:
        True si es una imagen soportada, False en caso contrario
    """
    from config import Config
    ext = Path(filename).suffix.lower()
    return ext in Config.SUPPORTED_IMAGE_EXTENSIONS


def is_video_file(filename: str | Path) -> bool:
    """
    Verifica si un archivo es un video soportado.
    
    Args:
        filename: Nombre o Path del archivo a verificar
    
    Returns:
        True si es un video soportado, False en caso contrario
    """
    from config import Config
    ext = Path(filename).suffix.lower()
    return ext in Config.SUPPORTED_VIDEO_EXTENSIONS


def is_media_file(filename: str | Path) -> bool:
    """
    Verifica si un archivo es multimedia soportado (imagen o video).
    
    Args:
        filename: Nombre o Path del archivo a verificar
    
    Returns:
        True si es multimedia soportado, False en caso contrario
    """
    return is_image_file(filename) or is_video_file(filename)


def is_supported_file(filename: str | Path) -> bool:
    """
    Verifica si un archivo es soportado.
    
    Args:
        filename: Nombre o Path del archivo a verificar
    
    Returns:
        True si es soportado, False en caso contrario
    """
    return is_media_file(filename)


def get_file_type(filename: str | Path) -> str:
    """
    Obtiene el tipo de archivo.
    
    Args:
        filename: Nombre o Path del archivo
    
    Returns:
        'PHOTO', 'VIDEO', u 'OTHER'
    """
    if is_image_file(filename):
        return 'PHOTO'
    elif is_video_file(filename):
        return 'VIDEO'
    else:
        return 'OTHER'


# =============================================================================
# SOURCE/ORIGIN DETECTION
# =============================================================================

def detect_file_source(filename: str, file_path: Optional[Path] = None, exif_data: Optional[dict] = None) -> str:
    """
    Detecta la fuente/origen de un archivo basándose en patrones y metadata.
    
    Args:
        filename: Nombre del archivo
        file_path: Path completo del archivo (opcional, para análisis de ruta)
        exif_data: Datos EXIF del archivo (opcional, para detectar dispositivo)
    
    Returns:
        Fuente detectada: 'WhatsApp', 'iPhone', 'Android', 'Screenshot', 
                         'Camera', 'Scanner', 'Unknown'
    
    Examples:
        >>> detect_file_source('IMG-20231025-WA0001.jpg')
        'WhatsApp'
        >>> detect_file_source('IMG_1234.HEIC')
        'iPhone'
        >>> detect_file_source('Screenshot_2023.png')
        'Screenshot'
    """
    filename_lower = filename.lower()
    
    # 1. WhatsApp (máxima prioridad)
    if is_whatsapp_file(filename, file_path):
        return 'WhatsApp'
    
    # 2. Screenshots
    screenshot_patterns = [
        r'^screenshot[_\s-]',  # Screenshot_...
        r'^captura[_\s-]',     # Captura de pantalla
        r'^screen[_\s-]',      # Screen_...
        r'^scrnshot',          # Scrnshot_...
    ]
    if any(re.match(pattern, filename_lower) for pattern in screenshot_patterns):
        return 'Screenshot'
    
    # 3. iPhone (HEIC, IMG_XXXX, formato Live Photo)
    if filename_lower.endswith('.heic'):
        return 'iPhone'
    # iPhone patterns: IMG_XXXX.JPG, IMG_EXXXX.JPG (edits), IMG_XXXX.MOV, with optional _NNN suffix
    if re.match(r'^img_[e]?\d{4}(_\d{3})?\.(jpg|jpeg|png|mov|mp4)$', filename_lower):
        return 'iPhone'
    
    # 4. Android (patrón típico)
    android_patterns = [
        r'^pxl_\d{8}(_\d{3})?\..*$',       # Google Pixel
        r'^img-\d{8}(_\d{3})?\..*$',       # Algunos Android (sin WA)
        r'^\d{8}_\d{6}(_\d{3})?\..*$',      # Samsung: YYYYMMDD_HHMMSS
        r'^signal-\d{4}(_\d{3})?\..*$',     # Signal app
    ]
    if any(re.match(pattern, filename_lower) for pattern in android_patterns):
        return 'Android'
    
    # 5. Cámara digital (DSC, DCIM patterns)
    camera_patterns = [
        r'^dsc[_-]?\d+(_\d{3})?\.',      # DSC_0001.jpg or DSC_0001_001.jpg
        r'^p\d{7}(_\d{3})?\.',           # P0001234.jpg
        r'^_dsc\d+(_\d{3})?\.',          # _DSC1234.jpg (Nikon)
        r'^img_\d{4,}(_\d{3})?\.',       # IMG_12345.jpg (cámaras Canon, etc.)
    ]
    if any(re.match(pattern, filename_lower) for pattern in camera_patterns):
        return 'Camera'
    
    # 6. Escáner
    scanner_patterns = [
        r'^scan[_\s-]',       # Scan_...
        r'^scanned[_\s-]',    # Scanned_...
        r'^escanear',         # Escanear_...
    ]
    if any(re.match(pattern, filename_lower) for pattern in scanner_patterns):
        return 'Scanner'
    
    # 7. EXIF data (si está disponible)
    if exif_data:
        model = exif_data.get('Model', '').lower()
        make = exif_data.get('Make', '').lower()
        
        if 'iphone' in model or 'iphone' in make:
            return 'iPhone'
        if 'samsung' in make or 'pixel' in model or 'android' in model:
            return 'Android'
        if model or make:  # Cualquier otra cámara con metadata
            return 'Camera'
    
    # 8. Análisis de ruta (último recurso)
    if file_path:
        path_str = str(file_path).lower()
        if 'whatsapp' in path_str:
            return 'WhatsApp'
        if 'dcim' in path_str or 'camera' in path_str:
            return 'Camera'
        if 'screenshot' in path_str:
            return 'Screenshot'
    
    return 'Unknown'


def is_whatsapp_file(filename: str, file_path: Path = None) -> bool:
    """Verifica si un archivo es de WhatsApp basándose en su nombre y/o ruta.
    
    Detecta archivos de WhatsApp por:
    1. Patrones de nombre conocidos (IMG-WA, VID-WA, WhatsApp Image, etc.)
    2. Formato UUID de iPhone (82DB60A3-002F-4FAE-80FC-96082431D247.jpg)
    3. Ruta que contenga "whatsapp" en cualquier nivel
    
    Args:
        filename: Nombre del archivo
        file_path: Path completo del archivo (opcional)
    
    Returns:
        True si el nombre coincide con patrones de WhatsApp o está en carpeta WhatsApp
    
    Examples:
        >>> is_whatsapp_file('IMG-20231025-WA0001.jpg')
        True
        >>> is_whatsapp_file('82DB60A3-002F-4FAE-80FC-96082431D247.jpg')
        True
        >>> is_whatsapp_file('photo.jpg', Path('/photos/WhatsApp/photo.jpg'))
        True
        >>> is_whatsapp_file('vacation.jpg', Path('/photos/vacation.jpg'))
        False
    """
    # Verificar por nombre (patrones conocidos)
    for pattern in WHATSAPP_PATTERNS:
        if re.match(pattern, filename, re.IGNORECASE):
            return True
    
    # Verificar por ruta (carpeta contiene "whatsapp" en cualquier nivel)
    if file_path:
        path_str = str(file_path).lower()
        if 'whatsapp' in path_str:
            return True
    
    return False


# =============================================================================
# FILE VALIDATION
# =============================================================================

def validate_file_exists(path) -> Path:
    """Normalize input to Path and verify the file exists and is a file.

    Args:
        path: str or Path-like to validate

    Returns:
        Path object for the validated file

    Raises:
        FileNotFoundError: if the path does not exist or is not a file
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {p}")
    if not p.is_file():
        raise FileNotFoundError(f"No es un archivo válido: {p}")
    return p


def validate_directory_exists(path) -> Path:
    """Normalize input to Path and verify the directory exists.

    Args:
        path: str or Path-like to validate

    Returns:
        Path object for the validated directory

    Raises:
        FileNotFoundError: if the path does not exist
        NotADirectoryError: if the path is not a directory
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"El directorio no existe: {p}")
    if not p.is_dir():
        raise NotADirectoryError(f"La ruta no es un directorio: {p}")
    return p


def to_path(obj, attr_names=('path', 'source_path', 'original_path')) -> Path:
    """Convierte un objeto flexible a Path.

    Args:
        obj: str, bytes, Path, dict o objeto con atributos
        attr_names: tuple de nombres de atributos a buscar

    Returns:
        Path: ruta del archivo

    Raises:
        ValueError: si no se puede extraer una ruta válida
    """
    if isinstance(obj, (str, bytes)):
        return Path(obj)
    if isinstance(obj, Path):
        return obj
    if isinstance(obj, dict):
        for k in attr_names:
            if k in obj:
                return Path(obj[k])
        if obj:
            return Path(next(iter(obj.values())))
    for k in attr_names:
        if hasattr(obj, k):
            return Path(getattr(obj, k))

    try:
        return Path(obj)
    except (TypeError, ValueError) as e:
        raise ValueError(f"No se pudo convertir {type(obj).__name__} a Path") from e


# =============================================================================
# FILE HASHING
# =============================================================================

def calculate_file_hash(file_path: Path, chunk_size: int = 8192, cache: Optional[dict] = None) -> str:
    """Calculate SHA256 hash of a file.

    If a cache dict is provided, the function will store and reuse computed hashes
    keyed by the file's string path.
    
    Raises:
        FileNotFoundError: Si el archivo no existe
        PermissionError: Si no hay permisos para leer el archivo
        IOError: Si hay un error de I/O durante la lectura
    """
    key = str(file_path)
    if cache is not None and key in cache:
        return cache[key]

    try:
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                sha256.update(chunk)

        digest = sha256.hexdigest()
        if cache is not None:
            cache[key] = digest
        return digest
    except FileNotFoundError:
        logger = get_logger('file_utils')
        logger.error(f"Archivo no encontrado: {file_path}")
        raise
    except PermissionError as e:
        logger = get_logger('file_utils')
        logger.error(f"Permiso denegado al leer {file_path.name}: {e}")
        raise
    except IOError as e:
        logger = get_logger('file_utils')
        logger.error(f"Error de I/O leyendo {file_path.name}: {e}")
        raise


# =============================================================================
# BACKUP OPERATIONS
# =============================================================================

def _ensure_backup_dir(backup_dir: Path):
    """Crea el directorio de backup si no existe (helper privado)."""
    backup_dir.mkdir(parents=True, exist_ok=True)


def launch_backup_creation(
    files: Iterable[Path],
    base_directory: Path,
    backup_prefix: str = "backup",
    progress_callback=None,
    metadata_name: Optional[str] = None
) -> Path:
    """Create a backup directory and copy the given files preserving relative paths.

    Args:
        files: Iterable of Path objects to back up
        base_directory: Base directory used to compute relative paths
        backup_prefix: Prefix used to name the backup folder
        progress_callback: optional callback (current, total, message)
        metadata_name: filename used to store metadata (defaults to backup_prefix + '_metadata.txt')

    Returns:
        Path to the created backup directory
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{backup_prefix}_{base_directory.name}_{timestamp}"

    from config import Config
    backup_root = Config.DEFAULT_BACKUP_DIR

    backup_path = backup_root / backup_name
    _ensure_backup_dir(backup_path)

    files_list = []
    for item in files:
        try:
            normalized = to_path(item)
            files_list.append(normalized)
        except ValueError as ve:
            raise ValueError(
                f"launch_backup_creation: cannot normalize item to a path: type={type(item).__name__}, repr={repr(item)}"
            ) from ve

    total = len(files_list)
    copied = 0
    total_size = 0

    for file_path in files_list:
        try:
            if base_directory in file_path.parents:
                relative_path = file_path.relative_to(base_directory)
            else:
                relative_path = file_path.parent.name / file_path.name

            dest = backup_path / relative_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest)
            copied += 1
            total_size += file_path.stat().st_size

            safe_progress_callback(progress_callback, copied, total, f"Creando backup: {backup_path} ({copied}/{total})")

        except PermissionError as e:
            logger = get_logger('file_utils')
            logger.error(f"Permiso denegado al copiar {file_path.name}: {e}")
            raise PermissionError(f"No se pudo crear backup de {file_path.name}: permiso denegado") from e
        except FileNotFoundError as e:
            logger = get_logger('file_utils')
            logger.error(f"Archivo no encontrado: {file_path}")
            raise FileNotFoundError(f"Archivo {file_path.name} no encontrado durante backup") from e
        except OSError as e:
            logger = get_logger('file_utils')
            logger.error(f"Error de I/O copiando {file_path.name}: {e}")
            raise OSError(f"Error creando backup de {file_path.name}: {e}") from e
        except Exception as e:
            logger = get_logger('file_utils')
            logger.error(f"Error inesperado en backup de {file_path.name}: {type(e).__name__}: {e}")
            raise

    # Write metadata
    metadata_name = metadata_name or f"{backup_prefix}_metadata.txt"
    metadata_path = backup_path / metadata_name
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(f"BACKUP: {backup_prefix}\n")
        f.write(f"Creado: {datetime.now()}\n")
        f.write(f"Directorio base: {base_directory}\n")
        f.write(f"Archivos respaldados: {copied}\n")
        f.write(f"Tamaño total: {format_size(total_size)}\n")
        f.write("\nARCHIVOS RESPALDADOS:\n")
        for p in files_list:
            f.write(f"- {p}\n")

    return backup_path


# =============================================================================
# FILE SYSTEM OPERATIONS
# =============================================================================

def cleanup_empty_directories(root_directory: Path) -> int:
    """Remove empty directories under root_directory (excluding root).

    Returns the number of directories removed.
    """
    removed_count = 0
    logger = get_logger('file_utils')
    for item in sorted(root_directory.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if item.is_dir() and item != root_directory:
            try:
                if not any(item.iterdir()):
                    item.rmdir()
                    removed_count += 1
            except PermissionError:
                logger.debug(f"Permiso denegado al eliminar directorio: {item.name}")
            except OSError as e:
                logger.debug(f"No se pudo eliminar directorio {item.name}: {e}")
    return removed_count


def delete_file_securely(file_path: Path) -> bool:
    """
    Elimina un archivo de forma segura (intentando enviar a la papelera primero).
    Si send2trash no está disponible, usa eliminación permanente.
    
    Args:
        file_path: Ruta del archivo a eliminar
        
    Returns:
        True si se eliminó correctamente
    """
    logger = get_logger('file_utils')
    try:
        try:
            from send2trash import send2trash
            send2trash(str(file_path))
            logger.debug(f"Archivo enviado a papelera: {file_path.name}")
        except ImportError:
            # Fallback a eliminación permanente si no hay send2trash
            file_path.unlink()
            logger.debug(f"Archivo eliminado permanentemente: {file_path.name}")
        return True
    except PermissionError as e:
        logger.warning(f"Permiso denegado al eliminar {file_path.name}: {e}")
        return False
    except FileNotFoundError:
        logger.debug(f"Archivo ya no existe: {file_path.name}")
        return False
    except OSError as e:
        logger.error(f"Error de I/O eliminando {file_path.name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado eliminando {file_path.name}: {type(e).__name__}: {e}")
        return False


def find_next_available_name(base_path: Path, base_name: str, extension: str) -> Tuple[str, int]:
    """Find next available filename with numeric suffix (XXX) in base_path.

    Returns (new_name, sequence)
    
    Si el nombre base termina en un sufijo numérico de 3 dígitos (_XXX), lo reemplaza.
    Si termina en un sufijo numérico de otra longitud (_X, _XX, _XXXX), lo preserva y añade el nuevo sufijo.
    """
    parts = base_name.split('_')
    
    # Detectar si tiene un sufijo numérico de 3 dígitos (patrón estándar)
    if len(parts) >= 4 and len(parts[-1]) == 3 and parts[-1].isdigit():
        base_without_suffix = '_'.join(parts[:-1])
        start_sequence = int(parts[-1])
    else:
        # No tiene sufijo de 3 dígitos, usar el nombre completo como base
        base_without_suffix = base_name
        start_sequence = 0

    existing_sequences = set()
    for file_path in base_path.iterdir():
        if file_path.is_file() and file_path.stem.startswith(base_without_suffix):
            file_parts = file_path.stem.split('_')
            if file_parts and len(file_parts[-1]) == 3 and file_parts[-1].isdigit():
                existing_sequences.add(int(file_parts[-1]))

    if existing_sequences:
        sequence = max(existing_sequences) + 1
    else:
        sequence = start_sequence + 1 if start_sequence > 0 else 1

    while sequence in existing_sequences:
        sequence += 1

    new_name = f"{base_without_suffix}_{sequence:03d}{extension}"
    return new_name, sequence


# =============================================================================
# METADATA EXTRACTION
# =============================================================================

def get_file_stat_info(file_path: Path, resolve_path: bool = True) -> dict:
    """
    Obtiene información básica del sistema de archivos para un archivo.
    
    Función centralizada para evitar duplicación de código al obtener
    metadatos del sistema de archivos.
    
    Args:
        file_path: Ruta del archivo
        resolve_path: Si True, incluye el path resuelto en el resultado
        
    Returns:
        Diccionario con size, ctime, mtime, atime y opcionalmente resolved_path
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        PermissionError: Si no hay permisos para acceder al archivo
        OSError: Si hay un error de I/O
    """
    try:
        stat_info = file_path.stat()
        result = {
            'size': stat_info.st_size,
            'ctime': stat_info.st_ctime,
            'mtime': stat_info.st_mtime,
            'atime': stat_info.st_atime
        }
        
        if resolve_path:
            result['resolved_path'] = file_path.resolve()
        
        return result
    except FileNotFoundError:
        logger = get_logger('file_utils')
        logger.error(f"Archivo no encontrado: {file_path}")
        raise
    except PermissionError as e:
        logger = get_logger('file_utils')
        logger.error(f"Permiso denegado al acceder a {file_path.name}: {e}")
        raise
    except OSError as e:
        logger = get_logger('file_utils')
        logger.error(f"Error de I/O obteniendo info de {file_path.name}: {e}")
        raise


def get_exif_from_image(file_path: Path) -> dict:
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
        >>> dates = get_exif_from_image(Path('photo.jpg'))
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
                logger = get_logger('file_utils')
                logger.warning(f"pillow-heif no disponible, no se puede procesar {file_path.name}")
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
        logger = get_logger('file_utils')
        logger.warning(f"Error extrayendo EXIF de {file_path.name}: {e}")
    
    return result


def get_exif_from_video(file_path: Path) -> Optional[datetime]:
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
        >>> get_exif_from_video(Path('IMG_0017_HAYLIVE.MOV'))
        datetime(2019, 11, 13, 15, 38, 59)
        
        >>> # Video regular con metadata de creación
        >>> get_exif_from_video(Path('video.mp4'))
        datetime(2024, 1, 15, 14, 30, 0)
        
        >>> # Video sin metadata
        >>> get_exif_from_video(Path('video_without_metadata.mp4'))
        None
    """
    import subprocess
    import json
    
    logger = get_logger('file_utils')
    
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
                    logger.debug(f"Video {file_path.name}: usando Keys:CreationDate = {parsed_date}")
                    return parsed_date
                except ValueError as e:
                    logger.debug(f"Error parseando Keys:CreationDate '{creation_date_str}': {e}")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.debug(f"Error ejecutando exiftool en {file_path.name}: {e}")
    
    # PRIORIDAD 2: Intentar ffprobe creation_time (videos regulares)
    if not shutil.which('ffprobe'):
        logger.debug("Ni exiftool ni ffprobe disponibles")
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
        if 'format' in metadata and 'tags' in metadata['format']:
            creation_time = metadata['format']['tags'].get('creation_time')
            
            if creation_time:
                try:
                    # Formato típico: '2024-01-15T14:30:00.000000Z'
                    # Intentar varios formatos comunes
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S']:
                        try:
                            parsed_date = datetime.strptime(creation_time, fmt)
                            logger.debug(f"Video {file_path.name}: usando ffprobe creation_time = {parsed_date}")
                            return parsed_date
                        except ValueError:
                            continue
                except Exception:
                    pass
        
        return None
        
    except subprocess.TimeoutExpired:
        logger.debug(f"Timeout ejecutando ffprobe en {file_path.name}")
        return None
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
        return None
    except Exception as e:
        logger.debug(f"Error obteniendo metadata de video {file_path.name}: {e}")
        return None


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FileInfo:
    """
    Información estándar de archivo para logging y procesamiento.
    
    Attributes:
        path: Path original del archivo
        size: Tamaño en bytes
        size_formatted: Tamaño formateado (ej: "5.2 MB")
        date: datetime de modificación
        date_formatted: Fecha formateada (ej: "2023-11-12 14:30:22")
    """
    path: Path
    size: int
    size_formatted: str
    date: Optional[datetime]
    date_formatted: str


def validate_and_get_file_info(file_path: Path) -> FileInfo:
    """
    Obtiene información estándar de archivo para logging y procesamiento.
    
    Centraliza la lógica de obtención de información de archivos
    que estaba duplicada en múltiples servicios.
    
    Args:
        file_path: Path del archivo a inspeccionar
    
    Returns:
        FileInfo con información completa del archivo
    
    Raises:
        FileNotFoundError: Si el archivo no existe
        Exception: Si hay error obteniendo información
    
    Example:
        >>> info = validate_and_get_file_info(Path('/path/photo.jpg'))
        >>> print(info.size_formatted)
        '2.5 MB'
        >>> print(info.date_formatted)
        '2023-11-12 14:30:22'
    """
    # Validar existencia
    validate_file_exists(file_path)
    
    # Obtener tamaño
    try:
        file_size = file_path.stat().st_size
        size_formatted = format_size(file_size)
    except Exception as e:
        logger = get_logger('ServiceUtils')
        logger.warning(f"Error obteniendo tamaño de {file_path}: {e}")
        file_size = 0
        size_formatted = "0 B"
    
    # Obtener fecha
    try:
        file_date = get_date_from_file(file_path, verbose=True)
        date_formatted = (
            file_date.strftime('%Y%m%d_%H%M%S')
            if file_date else 'fecha desconocida'
        )
    except Exception as e:
        logger = get_logger('ServiceUtils')
        logger.warning(f"Error obteniendo fecha de {file_path}: {e}")
        file_date = None
        date_formatted = 'fecha desconocida'
    
    return FileInfo(
        path=file_path,
        size=file_size,
        size_formatted=size_formatted,
        date=file_date,
        date_formatted=date_formatted
    )
