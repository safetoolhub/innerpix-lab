from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt
from ui.tabs.base_tab import create_info_label, create_details_textedit, create_action_button


def create_live_photos_tab(window):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    info = create_info_label(
        """
            <p><strong>⚠️ IMPORTANTE: Ejecutar ANTES de renombrar archivos</strong></p>
            <p>Detecta y limpia Live Photos de iPhone (parejas de foto + video .MOV)</p>
            <p style='color: #dc3545;'><em>Si los archivos ya han sido renombrados, la detección puede fallar</em></p>
        """,
        rich=True,
        extra_style="color: #495057; padding: 10px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 4px;"
    )
    layout.addWidget(info)

    create_details_textedit(window, 'lp_details')

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    create_action_button(window, 'exec_lp_btn', "⚡ Limpiar Live Photos", 'cleanup_live_photos', color="#28a745")
    button_layout.addWidget(window.exec_lp_btn)

    layout.addLayout(button_layout)
    layout.addStretch()
    return widget
