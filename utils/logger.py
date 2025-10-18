"""
Logger mínimo para PhotoKit Manager
"""
import logging
import sys


class SimpleLogger:
    """Logger simplificado para la aplicación"""

    def __init__(self, name="PhotokitManager"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            # Handler para consola
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

    def warning(self, message):
        self.logger.warning(message)

    def debug(self, message):
        self.logger.debug(message)


# Instancia global
logger = SimpleLogger()


def get_logger(name=None):
    """Obtiene una instancia de logger"""
    if name:
        return SimpleLogger(name)
    return logger
