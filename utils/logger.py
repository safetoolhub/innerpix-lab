"""
Logger para Pixaro Lab

Convenciones de niveles de log:
- DEBUG: detalles internos de bajo nivel, útiles para debugging
- INFO: operaciones importantes completadas exitosamente
- WARNING: situaciones recuperables que merecen atención
- ERROR: errores que requieren atención inmediata

Todos los mensajes de log deben ser texto plano, sin HTML.
"""
import logging
import sys
import re


# Logger raíz para toda la aplicación
_ROOT_LOGGER_NAME = 'PixaroLab'
_root_logger = None
_current_level = logging.INFO


def _ensure_root_logger():
    """Asegura que el logger raíz esté configurado"""
    global _root_logger, _current_level
    
    if _root_logger is None:
        _root_logger = logging.getLogger(_ROOT_LOGGER_NAME)
        _root_logger.setLevel(_current_level)
        
        if not _root_logger.handlers:
            # Handler para consola
            handler = logging.StreamHandler(sys.stdout)
            # Formato mejorado con nombre del módulo para mejor trazabilidad
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            _root_logger.addHandler(handler)
    
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
    """Obtiene una instancia de logger"""
    if name:
        return SimpleLogger(name)
    return logger
