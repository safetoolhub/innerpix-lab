"""Shim de compatibilidad para la ubicación antigua `ui.tabs`.

Ahora cada pestaña vive en `ui/tabs/*.py`. Este módulo reexporta la API
anterior para evitar romper imports existentes.
"""
from ui.tabs import create_tabs_widget, open_summary_action

__all__ = [
    'create_tabs_widget',
    'open_summary_action',
]
