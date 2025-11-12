"""
Utilidades compartidas para servicios.

Proporciona funciones reutilizables para operaciones comunes
que antes estaban duplicadas en múltiples servicios.
"""

from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from utils.logger import get_logger

logger = get_logger('ServiceUtils')


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


def create_service_backup(
    files: List[Path],
    directory: Path,
    service_name: str,
    progress_callback: Optional[Callable] = None
) -> Path:
    """
    Crea backup estandarizado para cualquier servicio.
    
    Elimina la necesidad de crear backups manualmente en cada servicio,
    delegando a la utilidad centralizada launch_backup_creation.
    
    Args:
        files: Lista de archivos a respaldar
        directory: Directorio base para el backup
        service_name: Nombre del servicio (usado en el nombre del backup)
        progress_callback: Callback opcional de progreso
    
    Returns:
        Path del directorio de backup creado
    
    Raises:
        Exception: Si falla la creación del backup
    
    Example:
        >>> files = [Path('/path/file1.jpg'), Path('/path/file2.jpg')]
        >>> backup_path = create_service_backup(
        ...     files, Path('/path'), 'heic_removal'
        ... )
        >>> print(backup_path)
        /path/.backups/backup_heic_removal_20231112_143022
    """
    from utils.file_utils import launch_backup_creation
    
    logger.info(f"Creando backup para {service_name}...")
    
    backup_path = launch_backup_creation(
        files,
        directory,
        backup_prefix=f'backup_{service_name}',
        progress_callback=progress_callback,
        metadata_name=f'{service_name}_metadata.txt'
    )
    
    logger.info(f"Backup creado exitosamente en: {backup_path}")
    return backup_path


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
    from utils.file_utils import validate_file_exists
    from utils.format_utils import format_size
    from utils.date_utils import get_file_date
    
    # Validar existencia
    validate_file_exists(file_path)
    
    # Obtener tamaño
    try:
        file_size = file_path.stat().st_size
        size_formatted = format_size(file_size)
    except Exception as e:
        logger.warning(f"Error obteniendo tamaño de {file_path}: {e}")
        file_size = 0
        size_formatted = "0 B"
    
    # Obtener fecha
    try:
        file_date = get_file_date(file_path, verbose=True)
        date_formatted = (
            file_date.strftime('%Y-%m-%d %H:%M:%S')
            if file_date else 'fecha desconocida'
        )
    except Exception as e:
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


def format_file_list(files: List[Path], max_display: int = 10) -> str:
    """
    Formatea lista de archivos para logging legible.
    
    Args:
        files: Lista de archivos
        max_display: Máximo número de archivos a mostrar
    
    Returns:
        String formateado con lista de archivos
    
    Example:
        >>> files = [Path('a.jpg'), Path('b.jpg'), Path('c.jpg')]
        >>> print(format_file_list(files, max_display=2))
        - a.jpg
        - b.jpg
        ... y 1 más
    """
    if not files:
        return "(ninguno)"
    
    lines = []
    for i, file_path in enumerate(files[:max_display]):
        lines.append(f"  - {file_path.name}")
    
    remaining = len(files) - max_display
    if remaining > 0:
        lines.append(f"  ... y {remaining} más")
    
    return "\n".join(lines)
