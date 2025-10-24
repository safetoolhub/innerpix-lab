from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from ui.tabs.base_tab import create_info_label, create_details_textedit, create_action_button


def create_heic_tab(window):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    info = create_info_label("Elimina duplicados cuando existen archivos HEIC y JPG con el mismo nombre", rich=False, extra_style="color: #6c757d; padding: 10px; font-style: italic;")
    layout.addWidget(info)

    create_details_textedit(window, 'heic_details', layout)

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    create_action_button(window, 'exec_heic_btn', "⚡ Eliminar Duplicados", 'remove_heic', color="#28a745")
    button_layout.addWidget(window.exec_heic_btn)

    layout.addLayout(button_layout)
    layout.addStretch()
    return widget
