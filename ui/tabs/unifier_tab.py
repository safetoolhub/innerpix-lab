from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from ui.tabs.base_tab import create_info_label, create_details_textedit, create_action_button


def create_unification_tab(window):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    info = create_info_label("Mueve todos los archivos al directorio raíz", rich=False, extra_style="color: #6c757d; padding: 10px; font-style: italic;")
    layout.addWidget(info)

    create_details_textedit(window, 'unif_details', layout)

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    create_action_button(window, 'exec_unif_btn', "⚡ Unificar Directorios", 'unify_directories', color="#28a745")
    button_layout.addWidget(window.exec_unif_btn)

    layout.addLayout(button_layout)
    layout.addStretch()
    return widget
