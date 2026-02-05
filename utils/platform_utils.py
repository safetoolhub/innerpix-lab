"""
Utilidades multiplataforma para operaciones del sistema operativo.
Funciones independientes de UI para interactuar con el SO (abrir archivos, carpetas, etc.)
"""

import subprocess
import platform
import os
import shutil
import psutil
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass
from utils.logger import get_logger


logger = get_logger('PlatformUtils')


# =============================================================================
# SYSTEM TOOLS DETECTION
# =============================================================================

@dataclass
class ToolStatus:
    """Estado de una herramienta del sistema."""
    name: str
    available: bool
    path: Optional[str] = None
    version: Optional[str] = None
    error: Optional[str] = None


def find_executable(name: str) -> Optional[str]:
    """
    Busca un ejecutable en el PATH del sistema de forma multiplataforma.
    
    Args:
        name: Nombre del ejecutable (sin extensión en Windows)
    
    Returns:
        Ruta completa al ejecutable si se encuentra, None si no existe
    """
    # shutil.which funciona en Windows, Linux y macOS
    return shutil.which(name)


def get_tool_version(tool_name: str, version_args: list[str], timeout: int = 5) -> Optional[str]:
    """
    Obtiene la versión de una herramienta ejecutando un comando.
    
    Args:
        tool_name: Nombre del ejecutable
        version_args: Argumentos para obtener la versión (ej: ['-version'], ['-ver'])
        timeout: Tiempo máximo de espera en segundos
    
    Returns:
        String con la versión o None si falla
    """
    try:
        result = subprocess.run(
            [tool_name] + version_args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def check_ffprobe() -> ToolStatus:
    """
    Verifica si ffprobe está instalado y obtiene su versión.
    
    Returns:
        ToolStatus con información sobre ffprobe
    """
    path = find_executable('ffprobe')
    if not path:
        return ToolStatus(
            name='ffprobe',
            available=False,
            error='No instalado - Necesario para duración de videos'
        )
    
    version_output = get_tool_version('ffprobe', ['-version'])
    version = None
    if version_output:
        # Extraer primera línea: "ffprobe version X.X.X ..."
        first_line = version_output.split('\n')[0]
        version = first_line[:50] if len(first_line) > 50 else first_line
    
    return ToolStatus(
        name='ffprobe',
        available=True,
        path=path,
        version=version
    )


def check_exiftool() -> ToolStatus:
    """
    Verifica si exiftool está instalado y obtiene su versión.
    
    Returns:
        ToolStatus con información sobre exiftool
    """
    path = find_executable('exiftool')
    if not path:
        return ToolStatus(
            name='exiftool',
            available=False,
            error='No instalado - Necesario para fechas de Live Photos'
        )
    
    version = get_tool_version('exiftool', ['-ver'])
    
    return ToolStatus(
        name='exiftool',
        available=True,
        path=path,
        version=version
    )


def are_video_tools_available() -> bool:
    """
    Verifica si las herramientas necesarias para extraer metadatos de video están disponibles.
    
    Para extraer metadatos de video (duración, fecha de creación) se necesita
    al menos una de estas herramientas: ffprobe o exiftool.
    
    Returns:
        True si al menos una herramienta está disponible, False si ninguna
    """
    return find_executable('ffprobe') is not None or find_executable('exiftool') is not None


def check_all_video_tools() -> Tuple[ToolStatus, ToolStatus]:
    """
    Verifica el estado de todas las herramientas de video.
    
    Returns:
        Tupla con (ffprobe_status, exiftool_status)
    """
    return check_ffprobe(), check_exiftool()


# =============================================================================
# CLIPBOARD OPERATIONS
# =============================================================================

def copy_to_clipboard(text: str, error_callback: Optional[Callable[[str], None]] = None) -> bool:
    """
    Copia texto al portapapeles de forma multiplataforma.
    
    Usa PyQt6 QClipboard internamente, que funciona en Linux, Windows y macOS.
    
    Args:
        text: Texto a copiar al portapapeles
        error_callback: Función opcional para manejar errores. Recibe el mensaje de error.
                       Si no se proporciona, los errores se registran en el log.
    
    Returns:
        True si se copió correctamente, False si hubo error
        
    Example:
        >>> from utils.platform_utils import copy_to_clipboard
        >>> copy_to_clipboard("/home/user/photos/IMG_001.jpg")
        True
    """
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QClipboard
        
        # QApplication debe existir para acceder al clipboard
        app = QApplication.instance()
        if app is None:
            error_msg = "No hay instancia de QApplication disponible"
            logger.warning(error_msg)
            if error_callback:
                error_callback(error_msg)
            return False
        
        clipboard = app.clipboard()
        clipboard.setText(text)
        logger.debug(f"Texto copiado al portapapeles: {text[:50]}..." if len(text) > 50 else f"Texto copiado al portapapeles: {text}")
        return True
        
    except ImportError as e:
        error_msg = f"PyQt6 no está disponible para operaciones de clipboard: {e}"
        logger.error(error_msg)
        if error_callback:
            error_callback(error_msg)
        return False
    except Exception as e:
        error_msg = f"Error al copiar al portapapeles: {e}"
        logger.error(error_msg)
        if error_callback:
            error_callback(error_msg)
        return False


def get_install_instructions() -> Dict[str, str]:
    """
    Obtiene instrucciones de instalación de herramientas según el SO.
    
    Returns:
        Diccionario con instrucciones por sistema operativo
    """
    return {
        'linux_debian': 'sudo apt install ffmpeg libimage-exiftool-perl',
        'linux_fedora': 'sudo dnf install ffmpeg perl-Image-ExifTool',
        'linux_arch': 'sudo pacman -S ffmpeg perl-image-exiftool',
        'macos': 'brew install ffmpeg exiftool',
        'windows': 'Descargar desde ffmpeg.org y exiftool.org'
    }


def get_current_os_install_hint() -> str:
    """
    Obtiene la sugerencia de instalación para el SO actual.
    
    Returns:
        String con el comando o instrucción de instalación
    """
    system = platform.system()
    
    if system == 'Linux':
        # Intentar detectar la distribución
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if 'debian' in content or 'ubuntu' in content or 'mint' in content:
                    return 'sudo apt install ffmpeg libimage-exiftool-perl'
                elif 'fedora' in content or 'rhel' in content or 'centos' in content:
                    return 'sudo dnf install ffmpeg perl-Image-ExifTool'
                elif 'arch' in content or 'manjaro' in content:
                    return 'sudo pacman -S ffmpeg perl-image-exiftool'
        except (FileNotFoundError, PermissionError):
            pass
        return 'sudo apt install ffmpeg libimage-exiftool-perl'  # Default to Debian
    elif system == 'Darwin':
        return 'brew install ffmpeg exiftool'
    elif system == 'Windows':
        return 'Descargar desde ffmpeg.org y exiftool.org'
    else:
        return 'Consulta la documentación de tu sistema operativo'


# =============================================================================
# FILE OPERATIONS
# =============================================================================


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
