"""Paquete de pestañas: expone create_tabs_widget y open_summary_action.

Los submódulos implementan cada pestaña por separado para mejorar la
modularidad y permitir pruebas independientes.
"""
from .renaming_tab import create_renaming_tab
from .live_photos_tab import create_live_photos_tab
from .duplicates_tab import create_duplicates_tab
from .heic_tab import create_heic_tab
from .organizer_tab import create_organizer_tab

from PyQt5.QtWidgets import QTabWidget
from ui import styles

def create_tabs_widget(window):
    tabs = QTabWidget()
    tabs.setStyleSheet(styles.STYLE_TAB_WIDGET)
    tabs.setVisible(False)
    window.tab_index_map = {}
    idx = 0
    # Añadir siempre las pestañas en un orden fijo. La disponibilidad real
    # (habilitada/visible) será controlada por `update_tabs_availability`.
    
    # 1. Live Photos (debe ejecutarse ANTES de renombrar)
    tabs.addTab(create_live_photos_tab(window), "📱 Live Photos")
    window.tab_index_map['live_photos'] = idx
    idx += 1

    # 2. Duplicados HEIC (debe ejecutarse ANTES de renombrar)
    tabs.addTab(create_heic_tab(window), "🖼️ Duplicados HEIC")
    window.tab_index_map['heic'] = idx
    idx += 1

    # 3. Duplicados (puede ejecutarse en cualquier momento)
    duplicates_tab = create_duplicates_tab(window)
    tabs.addTab(duplicates_tab, "🔍 Duplicados")
    window.tab_index_map['duplicates'] = idx
    idx += 1

    # 4. Organizador (puede ejecutarse en cualquier momento)
    tabs.addTab(create_organizer_tab(window), "📁 Organizador")
    window.tab_index_map['organization'] = idx
    idx += 1

    # 5. Renombrado (debe ejecutarse ÚLTIMO)
    tabs.addTab(create_renaming_tab(window), "📝 Renombrado")
    window.tab_index_map['renaming'] = idx
    idx += 1

    # Guardar una lista inversa opcional (índice -> clave) por conveniencia
    # Esto puede usarse más adelante si se necesita iterar por índices.
    try:
        window.tab_keys_by_index = {v: k for k, v in window.tab_index_map.items()}
    except Exception:
        window.tab_keys_by_index = {}

    return tabs


def open_summary_action(window, label_substr):
    if not hasattr(window, 'tabs_widget') or window.tabs_widget.count() == 0:
        return
    if hasattr(window, 'tab_index_map'):
        key_map = {
            'live photos': 'live_photos',
            'duplicados heic': 'heic',
            'duplicados': 'duplicates',
            'organizador': 'organization',
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


def set_tab_enabled(window, key: str, enabled: bool):
    """Habilita o deshabilita la pestaña identificada por `key`.

    Usa `window.tab_index_map` para encontrar el índice. Si la pestaña no
    existe, no hace nada. En Qt5 no hay un método universal para ocultar/mostrar
    completamente una pestaña de forma portable, por lo que por ahora se usa
    `setTabEnabled` y también se asegura que el widget asociado reciba el mismo
    estado.
    """
    if not hasattr(window, 'tabs_widget') or not hasattr(window, 'tab_index_map'):
        return
    idx = window.tab_index_map.get(key)
    if idx is None:
        return
    try:
        window.tabs_widget.setTabEnabled(idx, enabled)
    except Exception:
        pass
    try:
        w = window.tabs_widget.widget(idx)
        if w is not None:
            w.setEnabled(enabled)
    except Exception:
        pass


def update_tabs_availability(window, results: dict):
    """Punto central para decidir la disponibilidad de las pestañas según
    `results` del análisis. Actualmente no restringe nada (habilita todo)
    para mantener el comportamiento previo; pero la lógica para evaluar
    `results` puede añadirse aquí en el futuro.

    Esta función será llamada por `MainWindow.on_analysis_finished`.
    """
    if not hasattr(window, 'tab_index_map'):
        return

    # Placeholder: habilitar todas las pestañas por defecto
    for key in window.tab_index_map.keys():
        set_tab_enabled(window, key, True)

    # Ejemplo futuro (comentado):
    # if results.get('heic', {}).get('total_duplicates', 0) == 0:
    #     set_tab_enabled(window, 'heic', False)
