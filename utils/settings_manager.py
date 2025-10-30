"""
Gestor de configuración persistente usando QSettings.
Maneja preferencias de usuario que persisten entre sesiones.
"""
import logging
from pathlib import Path
from typing import Any, Optional
from PyQt6.QtCore import QSettings

from utils.logger import get_logger


class SettingsManager:
    """Gestor centralizado de configuración de usuario persistente"""

    # Constantes para claves de configuración
    # === DIRECTORIOS ===
    KEY_LOGS_DIR = "directories/logs"
    KEY_BACKUP_DIR = "directories/backups"

    # === COMPORTAMIENTO ===
    KEY_AUTO_BACKUP = "behavior/auto_backup_enabled"
    KEY_CONFIRM_OPERATIONS = "behavior/confirm_operations"
    KEY_CONFIRM_DELETE = "behavior/confirm_delete"
    KEY_SHOW_NOTIFICATIONS = "behavior/show_notifications"
    KEY_SOUND_NOTIFICATIONS = "behavior/sound_notifications"
    KEY_AUTO_ANALYZE = "behavior/auto_analyze_on_open"

    # === LOGGING ===
    KEY_LOG_LEVEL = "logging/level"

    # === AVANZADO ===
    KEY_DRY_RUN_DEFAULT = "advanced/dry_run_default"
    KEY_MAX_WORKERS = "advanced/max_workers"

    # === VENTANA ===
    KEY_WINDOW_GEOMETRY = "window/geometry"
    KEY_WINDOW_STATE = "window/state"

    def __init__(self, organization: str = "PixaroLab", application: str = "Pixaro Lab"):
        """
        Inicializa el gestor de configuración.

        Args:
            organization: Nombre de la organización
            application: Nombre de la aplicación
        """
        self.settings = QSettings(organization, application)
        self.logger = get_logger('SettingsManager')
        self.logger.debug(f"SettingsManager inicializado. Archivo: {self.settings.fileName()}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración.

        Args:
            key: Clave de configuración
            default: Valor por defecto si no existe

        Returns:
            Valor guardado o default
        """
        value = self.settings.value(key, default)
        self.logger.debug(f"get({key}) = {value} (default={default})")
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Guarda un valor de configuración.

        Args:
            key: Clave de configuración
            value: Valor a guardar
        """
        self.logger.debug(f"set({key}, {value})")
        self.settings.setValue(key, value)
        self.settings.sync()  # Forzar guardado inmediato

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Obtiene un valor booleano de configuración.

        Args:
            key: Clave de configuración
            default: Valor por defecto

        Returns:
            Valor booleano
        """
        value = self.settings.value(key, default)
        # QSettings puede devolver strings "true"/"false" en algunos casos
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value)

    def get_int(self, key: str, default: int = 0) -> int:
        """
        Obtiene un valor entero de configuración.

        Args:
            key: Clave de configuración
            default: Valor por defecto

        Returns:
            Valor entero
        """
        value = self.settings.value(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_path(self, key: str, default: Optional[Path] = None) -> Optional[Path]:
        """
        Obtiene un valor de ruta de configuración.

        Args:
            key: Clave de configuración
            default: Valor por defecto

        Returns:
            Path o None
        """
        value = self.settings.value(key, default)
        if value is None:
            return default
        return Path(value)

    def remove(self, key: str) -> None:
        """
        Elimina una clave de configuración.

        Args:
            key: Clave a eliminar
        """
        self.logger.debug(f"remove({key})")
        self.settings.remove(key)
        self.settings.sync()

    def clear_all(self) -> None:
        """Elimina toda la configuración guardada"""
        self.logger.warning("Limpiando toda la configuración")
        self.settings.clear()
        self.settings.sync()

    def has_key(self, key: str) -> bool:
        """
        Verifica si existe una clave.

        Args:
            key: Clave a verificar

        Returns:
            True si existe
        """
        return self.settings.contains(key)

    # === MÉTODOS DE CONVENIENCIA PARA CONFIGURACIÓN COMÚN ===

    def get_auto_backup_enabled(self) -> bool:
        """Obtiene si los backups automáticos están habilitados (por defecto True)"""
        return self.get_bool(self.KEY_AUTO_BACKUP, True)

    def set_auto_backup_enabled(self, enabled: bool) -> None:
        """Establece si los backups automáticos están habilitados"""
        self.set(self.KEY_AUTO_BACKUP, enabled)

    def get_log_level(self, default: str = "INFO") -> str:
        """Obtiene el nivel de log guardado"""
        return str(self.get(self.KEY_LOG_LEVEL, default)).upper()

    def set_log_level(self, level: str) -> None:
        """Establece el nivel de log"""
        self.set(self.KEY_LOG_LEVEL, level.upper())

    def get_logs_directory(self, default: Optional[Path] = None) -> Optional[Path]:
        """Obtiene el directorio de logs configurado"""
        return self.get_path(self.KEY_LOGS_DIR, default)

    def set_logs_directory(self, path: Path) -> None:
        """Establece el directorio de logs"""
        self.set(self.KEY_LOGS_DIR, str(path))

    def get_backup_directory(self, default: Optional[Path] = None) -> Optional[Path]:
        """Obtiene el directorio de backups configurado"""
        return self.get_path(self.KEY_BACKUP_DIR, default)

    def set_backup_directory(self, path: Path) -> None:
        """Establece el directorio de backups"""
        self.set(self.KEY_BACKUP_DIR, str(path))

    def get_confirm_operations(self) -> bool:
        """Obtiene si se debe confirmar operaciones (por defecto True)"""
        return self.get_bool(self.KEY_CONFIRM_OPERATIONS, True)

    def get_confirm_delete(self) -> bool:
        """Obtiene si se debe confirmar eliminaciones (por defecto True)"""
        return self.get_bool(self.KEY_CONFIRM_DELETE, True)

    def get_show_notifications(self) -> bool:
        """Obtiene si se deben mostrar notificaciones (por defecto True)"""
        return self.get_bool(self.KEY_SHOW_NOTIFICATIONS, True)

    def get_auto_analyze(self) -> bool:
        """Obtiene si se debe auto-analizar al abrir directorio (por defecto False)"""
        return self.get_bool(self.KEY_AUTO_ANALYZE, False)

    def get_max_workers(self, default: int = 4) -> int:
        """Obtiene el número máximo de workers"""
        return self.get_int(self.KEY_MAX_WORKERS, default)


# Instancia global del gestor de configuración
settings_manager = SettingsManager()
