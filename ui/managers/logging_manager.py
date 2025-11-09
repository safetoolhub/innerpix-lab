"""Logging manager for Pixaro Lab.

Encapsulates logging configuration so that the UI modules (and others)
can rely on a single place to configure and obtain a logger, log file
path and logs directory.

Usage:
    manager = LoggingManager(default_dir=..., level="INFO", logger_name="PixaroLab")
    logger = manager.logger
"""
from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class LoggingManager:
    """Configure logging and expose a configured logger and log paths.

    Args:
        default_dir: Path or str pointing to directory where logs will be stored.
        level: logging level name (e.g. 'INFO', 'DEBUG'). Case-insensitive.
        logger_name: Name for the application logger to retrieve.
    """

    def __init__(
        self,
        default_dir: Optional[Path | str] = None,
        level: str = "INFO",
        logger_name: str = "PixaroLab",
    ) -> None:
        self.logs_directory = Path(default_dir or Path.cwd())
        self.log_level = (str(level) or "INFO").upper()

        try:
            self.logs_directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.logs_directory = Path.cwd()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_directory / f"pixaro_lab_{timestamp}.log"

        numeric_level = getattr(logging, self.log_level, logging.INFO)
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
            force=True,
        )

        self.logger = logging.getLogger(logger_name)

    def change_logs_directory(self, new_dir: Path | str) -> None:
        """
        Change the logs directory at runtime.
        
        IMPORTANTE: No cierra handlers antiguos inmediatamente para evitar bloqueos
        con threads activos. Los handlers viejos seguirán escribiendo hasta que
        los threads terminen naturalmente.
        """
        self.logs_directory = Path(new_dir)
        try:
            self.logs_directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.logs_directory = Path.cwd()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_directory / f"pixaro_lab_{timestamp}.log"

        root_logger = logging.getLogger()
        
        # ✅ ESTRATEGIA: NO cerrar handlers viejos inmediatamente
        # Si hay threads activos (workers cancelados), h.close() puede bloquear.
        # En su lugar, simplemente añadimos el nuevo handler.
        # Los handlers viejos se limpiarán solos cuando terminen los threads.
        
        # Verificar si ya existe un handler para el nuevo archivo
        new_file_str = str(self.log_file)
        has_new_handler = any(
            isinstance(h, logging.FileHandler) and h.baseFilename == new_file_str
            for h in root_logger.handlers
        )
        
        if has_new_handler:
            # Ya existe un handler para este archivo, no hacer nada
            return

        # Crear nuevo file handler (sin cerrar los viejos)
        try:
            file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)
            numeric_level = getattr(logging, self.log_level, logging.INFO)
            file_handler.setLevel(numeric_level)
            root_logger.addHandler(file_handler)
            
            # Log en el nuevo archivo
            if hasattr(self, 'logger'):
                self.logger.info(f"Directorio de logs cambiado a: {self.logs_directory}")
                self.logger.info(f"Nuevo archivo de log: {self.log_file}")
                
        except Exception as e:
            # Si no se puede crear el nuevo handler, al menos registrar el error
            if hasattr(self, 'logger'):
                self.logger.error(f"No se pudo crear nuevo handler de logs: {e}")
            return

        # Añadir stream handler si no existe
        has_stream = any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) 
                        for h in root_logger.handlers)
        if not has_stream:
            try:
                stream_h = logging.StreamHandler()
                formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                stream_h.setFormatter(formatter)
                stream_h.setLevel(numeric_level)
                root_logger.addHandler(stream_h)
            except Exception:
                pass  # No crítico si falla el stream handler

        # Actualizar nivel del logger de la app
        if hasattr(self, 'logger') and self.logger:
            self.logger.setLevel(numeric_level)
        
        # NOTA: Los handlers viejos permanecerán activos. En una aplicación de escritorio
        # esto no es crítico ya que:
        # 1. El cambio de directorio es poco frecuente
        # 2. Los archivos viejos seguirán recibiendo algunos logs hasta que se cierre la app
        # 3. Es preferible esto a bloquear la UI esperando que los threads terminen

    def set_level(self, level_name: str) -> None:
        """Cambia el nivel de logging en caliente."""
        level = getattr(logging, str(level_name).upper(), logging.INFO)
        self.log_level = str(level_name).upper()
        self.logger.setLevel(level)
        logging.getLogger().setLevel(level)
