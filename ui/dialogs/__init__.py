"""Reexports de diálogos para compatibilidad con imports existentes.

Este paquete contiene los diálogos divididos en módulos más pequeños.
"""
from .file_renamer_dialog import FileRenamerDialog
from .live_photos_dialog import LivePhotosDialog
from .file_organizer_dialog import FileOrganizerDialog
from .heic_dialog import HeicDialog
from .settings_dialog import SettingsDialog
from .duplicates_exact_dialog import DuplicatesExactDialog
from .duplicates_similar_dialog import DuplicatesSimilarDialog
from .base_dialog import BaseDialog
from .about_dialog import AboutDialog
from .zero_byte_dialog import ZeroByteDialog


__all__ = [
    'BaseDialog',
    'FileRenamerDialog',
    'LivePhotosDialog',
    'FileOrganizerDialog',
    'HeicDialog',
    'DuplicatesExactDialog',
    'DuplicatesSimilarDialog',
    'SettingsDialog',
    'AboutDialog',
    'ZeroByteDialog',
]