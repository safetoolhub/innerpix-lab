"""Logging manager for PhotoKit Manager.

Encapsulates logging configuration so that the UI modules (and others)
can rely on a single place to configure and obtain a logger, log file
path and logs directory.

Usage:
    manager = LoggingManager(default_dir=..., level="INFO", logger_name="PhotokitManager")
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
        logger_name: str = "PhotokitManager",
    ) -> None:
        self.logs_directory = Path(default_dir or Path.cwd())
        self.log_level = (str(level) or "INFO").upper()

        # Ensure the directory exists
        try:
            self.logs_directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If mkdir fails for any reason, fallback to current working dir
            self.logs_directory = Path.cwd()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_directory / f"photokit_manager_{timestamp}.log"

        # Configure root/basic logging with both file and stderr handlers.
        # Use force=True to replace any previous configuration (consistent with
        # the previous behaviour in MainWindow).
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

        # Instance logger for the application
        self.logger = logging.getLogger(logger_name)

    def change_logs_directory(self, new_dir: Path | str) -> None:
        """Change the logs directory at runtime.

        Note: this does not reconfigure existing handlers; it only updates the
        target path for future log files.
        """
        self.logs_directory = Path(new_dir)
        try:
            self.logs_directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.logs_directory = Path.cwd()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_directory / f"photokit_manager_{timestamp}.log"

        # Reconfigure handlers so future logs go to the new file immediately.
        try:
            root_logger = logging.getLogger()
            # Close and remove existing FileHandler instances
            for h in list(root_logger.handlers):
                try:
                    if isinstance(h, logging.FileHandler):
                        try:
                            h.close()
                        except Exception:
                            pass
                        try:
                            root_logger.removeHandler(h)
                        except Exception:
                            pass
                except Exception:
                    # Ignore handler introspection errors
                    pass

            # Create new FileHandler for the new log file
            try:
                file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
                formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                file_handler.setFormatter(formatter)
                # Ensure handler level aligns with configured level
                numeric_level = getattr(logging, self.log_level, logging.INFO)
                file_handler.setLevel(numeric_level)
                root_logger.addHandler(file_handler)
            except Exception:
                # If creating a FileHandler fails, leave root handlers as-is
                pass

            # Ensure there's at least one StreamHandler for console output
            has_stream = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
            if not has_stream:
                try:
                    stream_h = logging.StreamHandler()
                    stream_h.setFormatter(formatter)
                    stream_h.setLevel(numeric_level)
                    root_logger.addHandler(stream_h)
                except Exception:
                    pass

            # Also update the application logger's handlers/level if present
            try:
                app_logger = logging.getLogger(self.logger.name) if getattr(self, 'logger', None) else None
                if app_logger:
                    app_logger.setLevel(numeric_level)
            except Exception:
                pass
        except Exception:
            # Non-fatal: do not raise to the UI
            pass

    def set_level(self, level_name: str) -> None:
        """Cambia el nivel de logging en caliente.

        level_name: nombre del nivel (p.ej. 'DEBUG', 'INFO'). Actualiza el
        logger expuesto y el nivel interno.
        """
        try:
            level = getattr(logging, str(level_name).upper(), logging.INFO)
            self.log_level = str(level_name).upper()
            # Actualizar nivel del logger de la aplicación
            try:
                self.logger.setLevel(level)
            except Exception:
                pass
            # También actualizar el root logger por si hay referencias directas
            try:
                logging.getLogger().setLevel(level)
            except Exception:
                pass
        except Exception:
            # No propagar excepciones de logging para no romper la UI
            pass
