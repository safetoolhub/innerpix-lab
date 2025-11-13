"""
Logger para Pixaro Lab

Convenciones de niveles de log:
- DEBUG: detalles internos de bajo nivel, útiles para debugging
- INFO: operaciones importantes completadas exitosamente
- WARNING: situaciones recuperables que merecen atención
- ERROR: errores que requieren atención inmediata

Todos los mensajes de log deben ser texto plano, sin HTML.

Thread-safety:
- Los logs están protegidos con un lock para evitar mezclas en ambientes concurrentes
- El procesamiento paralelo no se ve afectado, solo se serializan las escrituras de logs

File management:
- Logs se escriben tanto a archivo como a consola
- Archivo de log timestamped en directorio configurable
- Método para cambiar directorio de logs en runtime
"""
import logging
import sys
import re
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional


# Logger raíz para toda la aplicación
_ROOT_LOGGER_NAME = 'PixaroLab'
_root_logger = None
_current_level = logging.INFO
_log_lock = threading.RLock()  # RLock permite re-entrada del mismo thread
_log_file: Optional[Path] = None
_logs_directory: Optional[Path] = None


class ThreadSafeHandler(logging.Handler):
    """
    Base handler thread-safe que usa un RLock para serializar escrituras de logs.
    
    RLock (re-entrant lock) permite que el mismo thread adquiera el lock
    múltiples veces, evitando deadlocks en log_block().
    
    Esto evita que los logs de múltiples threads se mezclen, manteniendo
    cada mensaje completo sin interrupciones.
    """
    
    def emit(self, record):
        """Emite el log usando el RLock global para thread-safety"""
        with _log_lock:
            super().emit(record)


class ThreadSafeStreamHandler(ThreadSafeHandler, logging.StreamHandler):
    """Stream handler con thread-safety"""
    pass


class ThreadSafeFileHandler(ThreadSafeHandler, logging.FileHandler):
    """File handler con thread-safety"""
    pass


def _ensure_root_logger():
    """Asegura que el logger raíz esté configurado"""
    global _root_logger, _current_level
    
    if _root_logger is None:
        _root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
        _root_logger.setLevel(_current_level)
        
        if not _root_logger.handlers:
            # Formato mejorado con nombre del módulo para mejor trazabilidad
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Handler thread-safe para consola
            stream_handler = ThreadSafeStreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            _root_logger.addHandler(stream_handler)
            
            # Handler thread-safe para archivo (si se ha configurado)
            if _log_file:
                try:
                    file_handler = ThreadSafeFileHandler(_log_file, encoding='utf-8')
                    file_handler.setFormatter(formatter)
                    _root_logger.addHandler(file_handler)
                except Exception as e:
                    # Si falla crear el archivo, solo usar consola
                    _root_logger.error(f"No se pudo crear archivo de log: {e}")
    
    return _root_logger


def set_global_log_level(level):
    """Configura el nivel de log globalmente para todos los loggers
    
    Args:
        level: logging.DEBUG, logging.INFO, logging.WARNING, o logging.ERROR
    """
    global _current_level
    _current_level = level
    
    # Actualizar el logger raíz
    root = _ensure_root_logger()
    root.setLevel(level)
    
    # Actualizar todos los loggers hijos
    for name in logging.Logger.manager.loggerDict:
        if name.startswith(_ROOT_LOGGER_NAME):
            logger = logging.getLogger(name)
            logger.setLevel(level)


class SimpleLogger:
    """Logger simplificado para la aplicación con niveles estandarizados"""

    def __init__(self, name="PhotokitManager"):
        # Crear logger hijo del logger raíz
        if name == "PhotokitManager":
            self.logger = _ensure_root_logger()
        else:
            # Crear como hijo del logger raíz para heredar configuración
            full_name = f"{_ROOT_LOGGER_NAME}.{name}"
            self.logger = logging.getLogger(full_name)
            self.logger.setLevel(_current_level)
            # Los handlers se heredan del padre, no agregar duplicados

    def debug(self, message):
        """Log de detalles internos para debugging"""
        self.logger.debug(self._sanitize_message(message))

    def info(self, message):
        """Log de operaciones importantes completadas"""
        self.logger.info(self._sanitize_message(message))

    def warning(self, message):
        """Log de situaciones recuperables"""
        self.logger.warning(self._sanitize_message(message))

    def error(self, message):
        """Log de errores que requieren atención"""
        self.logger.error(self._sanitize_message(message))
    
    def setLevel(self, level):
        """Configura el nivel de log para este logger específico"""
        self.logger.setLevel(level)
    
    def isEnabledFor(self, level):
        """Verifica si el logger está habilitado para el nivel especificado"""
        return self.logger.isEnabledFor(level)
    
    def log_block(self, level, *messages):
        """
        Registra múltiples mensajes de forma atómica (sin interrupciones).
        
        Útil para logging de secciones que deben aparecer juntas en el log,
        especialmente en ambientes concurrentes.
        
        Args:
            level: logging.INFO, logging.DEBUG, etc.
            *messages: Mensajes a registrar en bloque
            
        Example:
            logger.log_block(logging.INFO,
                "=" * 80,
                "*** INICIANDO OPERACIÓN",
                "*** Archivos: 10",
                "=" * 80
            )
        """
        with _log_lock:
            for message in messages:
                sanitized = self._sanitize_message(message)
                self.logger.log(level, sanitized)

    @staticmethod
    def _sanitize_message(message):
        """Asegura que el mensaje sea texto plano en una sola línea, sin HTML"""
        if not isinstance(message, str):
            message = str(message)
        
        # Reemplazar saltos de línea HTML con espacio
        message = re.sub(r'<br\s*/?>', ' ', message)
        
        # Remover todas las etiquetas HTML
        message = re.sub(r'<[^>]+>', '', message)
        
        # Decodificar entidades HTML comunes
        message = message.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        message = message.replace('&nbsp;', ' ')
        
        # Reemplazar múltiples saltos de línea con espacio
        message = re.sub(r'\n+', ' ', message)
        
        # Reemplazar múltiples espacios con uno solo
        message = re.sub(r'\s+', ' ', message)
        
        # Limpiar espacios al inicio y final
        message = message.strip()
        
        return message


# Instancia global
logger = SimpleLogger()


def get_logger(name=None):
    """Obtiene una instancia de logger
    
    Args:
        name: Nombre del módulo/componente. Si es None, retorna el logger global
        
    Returns:
        SimpleLogger: Instancia de logger configurada
    """
    if name:
        return SimpleLogger(name)
    return logger


def configure_logging(
    logs_dir: Optional[Path | str] = None,
    level: str = "INFO",
) -> tuple[Path, Path]:
    """
    Configura el sistema de logging con archivo y directorio.
    
    Debe llamarse al inicio de la aplicación antes de usar get_logger().
    Crea archivo de log timestamped y configura handlers para archivo y consola.
    
    Args:
        logs_dir: Directorio donde guardar logs. Si es None, usa el directorio actual
        level: Nivel de logging ("DEBUG", "INFO", "WARNING", "ERROR")
        
    Returns:
        tuple: (ruta_archivo_log, directorio_logs)
        
    Example:
        log_file, logs_dir = configure_logging(
            logs_dir=Path.home() / "Documents" / "MyApp" / "logs",
            level="INFO"
        )
    """
    global _log_file, _logs_directory, _current_level, _root_logger
    
    # Configurar directorio
    if logs_dir:
        _logs_directory = Path(logs_dir)
    else:
        _logs_directory = Path.cwd()
    
    try:
        _logs_directory.mkdir(parents=True, exist_ok=True)
    except Exception:
        _logs_directory = Path.cwd()
    
    # Crear archivo de log con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _log_file = _logs_directory / f"pixaro_lab_{timestamp}.log"
    
    # Configurar nivel
    _current_level = getattr(logging, level.upper(), logging.INFO)
    
    # Si el logger ya existe, limpiar handlers viejos
    if _root_logger is not None:
        for handler in _root_logger.handlers[:]:
            _root_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
    
    # Crear/configurar logger raíz
    _root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
    _root_logger.setLevel(_current_level)
    _root_logger.handlers = []  # Limpiar cualquier handler previo
    
    # Formato mejorado con nombre del módulo para mejor trazabilidad
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler thread-safe para consola
    stream_handler = ThreadSafeStreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    _root_logger.addHandler(stream_handler)
    
    # Handler thread-safe para archivo
    try:
        file_handler = ThreadSafeFileHandler(_log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        _root_logger.addHandler(file_handler)
    except Exception as e:
        _root_logger.error(f"No se pudo crear archivo de log: {e}")
    
    return _log_file, _logs_directory


def change_logs_directory(new_dir: Path | str) -> tuple[Path, Path]:
    """
    Cambia el directorio de logs en runtime y crea un nuevo archivo de log.
    
    Cierra el handler de archivo anterior y crea uno nuevo en el nuevo directorio.
    El StreamHandler de consola se mantiene sin cambios.
    
    Args:
        new_dir: Nuevo directorio para logs
        
    Returns:
        tuple: (ruta_nuevo_archivo_log, nuevo_directorio_logs)
        
    Example:
        new_log_file, new_logs_dir = change_logs_directory(
            Path.home() / "Documents" / "MyApp" / "logs"
        )
    """
    global _log_file, _logs_directory
    
    # Configurar nuevo directorio
    _logs_directory = Path(new_dir)
    try:
        _logs_directory.mkdir(parents=True, exist_ok=True)
    except Exception:
        _logs_directory = Path.cwd()
    
    # Crear nuevo archivo de log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _log_file = _logs_directory / f"pixaro_lab_{timestamp}.log"
    
    root = _ensure_root_logger()
    
    # Remover handlers de archivo viejos
    old_file_handlers = [
        h for h in root.handlers 
        if isinstance(h, (logging.FileHandler, ThreadSafeFileHandler))
    ]
    for handler in old_file_handlers:
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass  # Ignorar errores al cerrar
    
    # Crear nuevo file handler
    try:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler = ThreadSafeFileHandler(_log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(_current_level)
        root.addHandler(file_handler)
        
        root.info(f"Directorio de logs cambiado a: {_logs_directory}")
        root.info(f"Nuevo archivo de log: {_log_file}")
    except Exception as e:
        root.error(f"No se pudo crear nuevo archivo de log: {e}")
    
    return _log_file, _logs_directory


def get_log_file() -> Optional[Path]:
    """Retorna la ruta del archivo de log actual"""
    return _log_file


def get_logs_directory() -> Optional[Path]:
    """Retorna el directorio de logs actual"""
    return _logs_directory


# Funciones utilitarias para logging discreto (disponibles globalmente)
def log_section_header_discrete(logger, title: str, mode: str = ""):
    """
    Logging discreto de encabezado (para operaciones no relevantes como análisis).
    
    Args:
        logger: Instancia de logger
        title: Título de la sección
        mode: Modo opcional (ej: "SIMULACIÓN", "ANÁLISIS")
    
    Example:
        log_section_header_discrete(logger, "ANÁLISIS DE LIVE PHOTOS")
    """
    mode_label = f"[{mode.upper()}] " if mode else ""
    logger.log_block(
        logging.INFO,
        f"--- {mode_label}{title} ---"
    )


def log_section_footer_discrete(logger, result_summary: str):
    """
    Logging discreto de cierre (para operaciones no relevantes como análisis).
    
    Args:
        logger: Instancia de logger
        result_summary: Resumen del resultado
    
    Example:
        log_section_footer_discrete(logger, "Análisis completado: 5 Live Photos encontrados")
    """
    logger.log_block(
        logging.INFO,
        f"--- {result_summary} ---"
    )


def log_section_header_relevant(logger, title: str, mode: str = ""):
    """
    Logging estandarizado de encabezado con banner ASCII (para operaciones relevantes).
    
    Args:
        logger: Instancia de logger
        title: Título de la sección
        mode: Modo opcional (ej: "SIMULACIÓN", "ANÁLISIS")
    
    Example:
        log_section_header_relevant(logger, "INICIANDO RENOMBRADO", "SIMULACIÓN")
        # Resultado:
        # ================================================================================
        # *** [SIMULACIÓN] INICIANDO RENOMBRADO
        # ================================================================================
    """
    mode_label = f"[{mode.upper()}] " if mode else ""
    logger.log_block(
        logging.INFO,
        "=" * 80,
        f"*** {mode_label}{title}",
        "=" * 80
    )


def log_section_footer_relevant(logger, result_summary: str):
    """
    Logging estandarizado de cierre (para operaciones relevantes).
    
    Args:
        logger: Instancia de logger
        result_summary: Resumen del resultado
    
    Example:
        log_section_footer_relevant(logger, "Operación completada: 10 archivos procesados")
    """
    logger.log_block(
        logging.INFO,
        f"*** {result_summary}",
        "=" * 80
    )
