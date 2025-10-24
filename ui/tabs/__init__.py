"""Paquete de pestañas: expone create_tabs_widget y open_summary_action.

Los submódulos implementan cada pestaña por separado para mejorar la
modularidad y permitir pruebas independientes.
"""
from .renaming_tab import create_renaming_tab
from .live_photos_tab import create_live_photos_tab
from .duplicates_tab import create_duplicates_tab
from .heic_tab import create_heic_tab
from .unifier_tab import create_unification_tab

from PyQt5.QtWidgets import QTabWidget
from ui import styles

def create_tabs_widget(window):
    tabs = QTabWidget()
    tabs.setStyleSheet(styles.STYLE_TAB_WIDGET)
    tabs.setVisible(False)
    window.tab_index_map = {}
    idx = 0
    # Import service_available lazily to avoid circular imports with ui.helpers
    from ui.helpers import service_available

    if service_available(window, 'live_photo_detector'):
        tabs.addTab(create_live_photos_tab(window), "(1) 📱 Live Photos")
        window.tab_index_map['live_photos'] = idx
        idx += 1
    if service_available(window, 'heic_remover'):
        tabs.addTab(create_heic_tab(window), "(2) 🖼️ Duplicados HEIC")
        window.tab_index_map['heic'] = idx
        idx += 1
    if service_available(window, 'directory_unifier'):
        tabs.addTab(create_unification_tab(window), "(3) 📁 Unificar Directorios")
        window.tab_index_map['unification'] = idx
        idx += 1
    if service_available(window, 'renamer'):
        tabs.addTab(create_renaming_tab(window), "(4) 📝 Renombrado")
        window.tab_index_map['renaming'] = idx
        idx += 1

    # Duplicados siempre disponible en UI actual
    duplicates_tab = create_duplicates_tab(window)
    tabs.addTab(duplicates_tab, "(5) 🔍 Duplicados")
    window.tab_index_map['duplicates'] = idx
    idx += 1

    return tabs


def open_summary_action(window, label_substr):
    if not hasattr(window, 'tabs_widget') or window.tabs_widget.count() == 0:
        return
    if hasattr(window, 'tab_index_map'):
        key_map = {
            'live photos': 'live_photos',
            'duplicados heic': 'heic',
            'duplicados': 'duplicates',
            'unificar directorios': 'unification',
            'renombrado': 'renaming'
        }
        lookup = key_map.get(label_substr.lower())
        if lookup and lookup in window.tab_index_map:
            window.tabs_widget.setCurrentIndex(window.tab_index_map[lookup])
            window.tabs_widget.setVisible(True)
            return
    if window.tabs_widget.count() > 0:
        window.tabs_widget.setCurrentIndex(0)
        window.tabs_widget.setVisible(True)
    return
