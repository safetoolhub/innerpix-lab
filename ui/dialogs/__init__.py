"""Reexports de diálogos para compatibilidad con imports existentes.

Este paquete contiene los diálogos divididos en módulos más pequeños.
"""
from .file_renamer_dialog import RenamingPreviewDialog
from .live_photos_dialog import LivePhotoCleanupDialog
from .file_organizer_dialog import FileOrganizationDialog
from .heic_dialog import HeicDuplicateRemovalDialog
from .settings_dialog import SettingsDialog
from .duplicates_exact_similar_dialog import ExactCopiesDialog
from .duplicates_similar_dialog import SimilarFilesDialog
from .base_dialog import BaseDialog
from .about_dialog import AboutDialog

__all__ = [
    'BaseDialog',
    'RenamingPreviewDialog',
    'LivePhotoCleanupDialog',
    'FileOrganizationDialog',
    'HeicDuplicateRemovalDialog',
    'ExactCopiesDialog',
    'SimilarFilesDialog',
    'SettingsDialog',
    'AboutDialog',
]