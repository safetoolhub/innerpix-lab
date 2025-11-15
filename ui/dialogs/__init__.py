"""Reexports de diálogos para compatibilidad con imports existentes.

Este paquete contiene los diálogos divididos en módulos más pequeños.
"""
from .file_renaming_dialog import RenamingPreviewDialog
from .live_photos_dialog import LivePhotoCleanupDialog
from .file_organizer_dialog import FileOrganizationDialog
from .heic_remover_dialog import HEICDuplicateRemovalDialog
from .settings_dialog import SettingsDialog
from .exact_copies_dialog import ExactCopiesDialog
from .similar_files_dialog import SimilarFilesDialog
from .base_dialog import BaseDialog
from .about_dialog import AboutDialog

__all__ = [
    'BaseDialog',
    'RenamingPreviewDialog',
    'LivePhotoCleanupDialog',
    'FileOrganizationDialog',
    'HEICDuplicateRemovalDialog',
    'ExactCopiesDialog',
    'SimilarFilesDialog',
    'SettingsDialog',
    'AboutDialog',
]