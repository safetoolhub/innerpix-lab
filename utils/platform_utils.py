"""
Utilidades multiplataforma para operaciones del sistema operativo.
Funciones independientes de UI para interactuar con el SO (abrir archivos, carpetas, etc.)
"""

import subprocess
import platform
import os
import psutil
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from utils.logger import get_logger


logger = get_logger('PlatformUtils')


def open_file_with_default_app(file_path: Path, 
                                error_callback: Optional[Callable[[str], None]] = None) -> bool:
    """
    Abre un archivo con la aplicación predeterminada del sistema operativo.
    
    Esta función es independiente de UI y puede usarse en scripts CLI.
    
    Args:
        file_path: Ruta del archivo a abrir
        error_callback: Función opcional para manejar errores. Recibe el mensaje de error.
                       Si no se proporciona, los errores se registran en el log.
    
    Returns:
        True si el archivo se abrió correctamente, False si hubo error
        
    Example:
        >>> from pathlib import Path
        >>> from utils.platform_utils import open_file_with_default_app
        >>> 
        >>> # Uso simple
        >>> open_file_with_default_app(Path("photo.jpg"))
        >>> 
        >>> # Con callback de error
        >>> def handle_error(msg):
        ...     print(f"Error: {msg}")
        >>> open_file_with_default_app(Path("photo.jpg"), error_callback=handle_error)
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        error_msg = f"El archivo no existe: {file_path}"
        logger.warning(error_msg)
        if error_callback:
            error_callback(error_msg)
        return False
    
    if not file_path.is_file():
        error_msg = f"La ruta no es un archivo: {file_path}"
        logger.warning(error_msg)
        if error_callback:
            error_callback(error_msg)
        return False
    
    try:
        system = platform.system()
        logger.debug(f"Abriendo archivo en {system}: {file_path}")
        
        if system == 'Linux':
            subprocess.Popen(['xdg-open', str(file_path)], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        elif system == 'Darwin':  # macOS
            subprocess.Popen(['open', str(file_path)],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        elif system == 'Windows':
            subprocess.Popen(['start', str(file_path)], shell=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        else:
            error_msg = f"Sistema operativo no soportado: {system}"
            logger.error(error_msg)
            if error_callback:
                error_callback(error_msg)
            return False
        
        logger.info(f"Archivo abierto correctamente: {file_path.name}")
        return True
        
    except Exception as e:
        error_msg = f"Error al abrir archivo: {str(e)}"
        logger.error(error_msg)
        if error_callback:
            error_callback(error_msg)
        return False


def open_folder_in_explorer(folder_path: Path,
                            select_file: Optional[Path] = None,
                            error_callback: Optional[Callable[[str], None]] = None) -> bool:
    """
    Abre una carpeta en el explorador de archivos del sistema operativo.
    
    Esta función es independiente de UI y puede usarse en scripts CLI.
    
    Args:
        folder_path: Ruta de la carpeta a abrir
        select_file: Archivo opcional dentro de la carpeta a seleccionar/resaltar
        error_callback: Función opcional para manejar errores. Recibe el mensaje de error.
                       Si no se proporciona, los errores se registran en el log.
    
    Returns:
        True si la carpeta se abrió correctamente, False si hubo error
        
    Example:
        >>> from pathlib import Path
        >>> from utils.platform_utils import open_folder_in_explorer
        >>> 
        >>> # Abrir carpeta
        >>> open_folder_in_explorer(Path("/home/user/photos"))
        >>> 
        >>> # Abrir carpeta y seleccionar archivo
        >>> open_folder_in_explorer(Path("/home/user/photos"), 
        ...                         select_file=Path("/home/user/photos/image.jpg"))
    """
    folder_path = Path(folder_path)
    
    if not folder_path.exists():
        error_msg = f"La carpeta no existe: {folder_path}"
        logger.warning(error_msg)
        if error_callback:
            error_callback(error_msg)
        return False
    
    if not folder_path.is_dir():
        error_msg = f"La ruta no es una carpeta: {folder_path}"
        logger.warning(error_msg)
        if error_callback:
            error_callback(error_msg)
        return False
    
    try:
        system = platform.system()
        logger.debug(f"Abriendo carpeta en {system}: {folder_path}")
        
        if system == 'Linux':
            # En Linux, xdg-open no soporta selección de archivo directamente
            if select_file and select_file.exists():
                # Intentar usar el file manager específico si está disponible
                try:
                    # Intentar con nautilus (GNOME)
                    subprocess.Popen(['nautilus', '--select', str(select_file)],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                except FileNotFoundError:
                    # Si nautilus no está disponible, solo abrir la carpeta
                    subprocess.Popen(['xdg-open', str(folder_path)],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(['xdg-open', str(folder_path)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                               
        elif system == 'Darwin':  # macOS
            if select_file and select_file.exists():
                # macOS soporta -R para revelar/seleccionar archivo
                subprocess.Popen(['open', '-R', str(select_file)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(['open', str(folder_path)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                               
        elif system == 'Windows':
            if select_file and select_file.exists():
                # Windows Explorer soporta /select para seleccionar archivo
                subprocess.Popen(['explorer', '/select,', str(select_file)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(['explorer', str(folder_path)],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
        else:
            error_msg = f"Sistema operativo no soportado: {system}"
            logger.error(error_msg)
            if error_callback:
                error_callback(error_msg)
            return False
        
        logger.info(f"Carpeta abierta correctamente: {folder_path.name}")
        return True
        
    except Exception as e:
        error_msg = f"Error al abrir carpeta: {str(e)}"
        logger.error(error_msg)
        if error_callback:
            error_callback(error_msg)
        return False


def is_linux() -> bool:
    """Retorna True si el sistema operativo es Linux"""
    return platform.system() == 'Linux'


def is_macos() -> bool:
    """Retorna True si el sistema operativo es macOS"""
    return platform.system() == 'Darwin'


def is_windows() -> bool:
    """Retorna True si el sistema operativo es Windows"""
    return platform.system() == 'Windows'


# ============================================================================
# SYSTEM HARDWARE INFO
# ============================================================================

def get_cpu_count() -> int:
    """
    Obtiene el número de CPUs/cores del sistema.
    
    Returns:
        Número de cores, o 4 si no se puede detectar
    """
    try:
        # os.cpu_count() funciona en Linux, macOS y Windows
        return os.cpu_count() or 4
    except Exception:
        return 4


def get_system_ram_gb() -> float:
    """
    Obtiene la RAM total del sistema en GB.
    
    Returns:
        RAM en GB, o 8.0 si no se puede detectar
    """
    try:
        # psutil es cross-platform
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        # psutil no disponible, asumir 8GB por defecto
        # Fallback básico podría implementarse para cada OS, pero 8GB es seguro
        return 8.0
    except Exception:
        return 8.0


def get_system_info(
    max_cache_entries_func: Optional[Any] = None,
    large_dataset_threshold_func: Optional[Any] = None,
    auto_open_threshold_func: Optional[Any] = None,
    io_workers_func: Optional[Any] = None,
    cpu_workers_func: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Obtiene información completa del sistema para logging.
    Acepta funciones opcionales para obtener valores de configuración que dependen del sistema.
    
    Returns:
        Dict con ram_gb, ram_available_gb, cpu_count, etc.
    """
    ram_gb = get_system_ram_gb()
    
    try:
        ram_available_gb = psutil.virtual_memory().available / (1024 ** 3)
        psutil_available = True
    except (ImportError, Exception):
        ram_available_gb = None
        psutil_available = False
    
    info = {
        'ram_total_gb': ram_gb,
        'ram_available_gb': ram_available_gb,
        'psutil_available': psutil_available,
        'cpu_count': get_cpu_count(),
        'os': platform.system(),
        'os_release': platform.release()
    }

    # Add optional config-dependent values if functions are provided
    if max_cache_entries_func:
        info['max_cache_entries'] = max_cache_entries_func()
    if large_dataset_threshold_func:
        info['large_dataset_threshold'] = large_dataset_threshold_func()
    if auto_open_threshold_func:
        info['auto_open_threshold'] = auto_open_threshold_func()
    if io_workers_func:
        info['io_workers'] = io_workers_func()
    if cpu_workers_func:
        info['cpu_workers'] = cpu_workers_func()
        
    return info
