"""Reexports de diálogos para compatibilidad con imports existentes.

Este paquete contiene los diálogos divididos en módulos más pequeños.
"""
from .renaming_dialog import RenamingPreviewDialog
from .live_photos_dialog import LivePhotoCleanupDialog
from .directory_dialog import DirectoryUnificationDialog
from .heic_dialog import HEICDuplicateRemovalDialog
from .settings_dialog import SettingsDialog
from .duplicates_dialogs import ExactDuplicatesDialog, SimilarDuplicatesDialog
from .base_dialog import BaseDialog

__all__ = [
    'BaseDialog',
    'RenamingPreviewDialog',
    'LivePhotoCleanupDialog',
    'DirectoryUnificationDialog',
    'HEICDuplicateRemovalDialog',
    'SettingsDialog',
    'ExactDuplicatesDialog',
    'SimilarDuplicatesDialog',
]
