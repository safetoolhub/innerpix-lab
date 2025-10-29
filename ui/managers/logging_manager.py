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
        """Change the logs directory at runtime."""
        self.logs_directory = Path(new_dir)
        try:
            self.logs_directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.logs_directory = Path.cwd()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_directory / f"pixaro_lab_{timestamp}.log"

        root_logger = logging.getLogger()
        
        # Cerrar y remover handlers de archivo existentes
        for h in list(root_logger.handlers):
            if isinstance(h, logging.FileHandler):
                h.close()
                root_logger.removeHandler(h)

        # Crear nuevo file handler
        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        numeric_level = getattr(logging, self.log_level, logging.INFO)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)

        # Añadir stream handler si no existe
        has_stream = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
        if not has_stream:
            stream_h = logging.StreamHandler()
            stream_h.setFormatter(formatter)
            stream_h.setLevel(numeric_level)
            root_logger.addHandler(stream_h)

        # Actualizar nivel del logger de la app
        if hasattr(self, 'logger') and self.logger:
            self.logger.setLevel(numeric_level)

    def set_level(self, level_name: str) -> None:
        """Cambia el nivel de logging en caliente."""
        level = getattr(logging, str(level_name).upper(), logging.INFO)
        self.log_level = str(level_name).upper()
        self.logger.setLevel(level)
        logging.getLogger().setLevel(level)
