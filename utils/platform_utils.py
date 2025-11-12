"""
Utilidades multiplataforma para operaciones del sistema operativo.
Funciones independientes de UI para interactuar con el SO (abrir archivos, carpetas, etc.)
"""

import subprocess
import platform
from pathlib import Path
from typing import Optional, Callable
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


def get_default_file_manager() -> Optional[str]:
    """
    Intenta detectar el gestor de archivos predeterminado del sistema.
    
    Returns:
        Nombre del gestor de archivos o None si no se puede detectar
    """
    system = platform.system()
    
    if system == 'Linux':
        # Intentar detectar el file manager en Linux
        managers = ['nautilus', 'dolphin', 'thunar', 'pcmanfm', 'nemo', 'caja']
        for manager in managers:
            try:
                result = subprocess.run(['which', manager], 
                                      capture_output=True, 
                                      text=True,
                                      timeout=1)
                if result.returncode == 0:
                    return manager
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        return 'xdg-open'  # Fallback
        
    elif system == 'Darwin':
        return 'Finder'
        
    elif system == 'Windows':
        return 'explorer'
        
    return None
