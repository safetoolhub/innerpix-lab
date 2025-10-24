from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt
from ui.tabs.base_tab import create_info_label, create_details_textedit, create_action_button


def create_renaming_tab(window):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    info = create_info_label(
        """
            <p><strong>⚠️ IMPORTANTE: Ejecutar como último paso</strong></p>
            <p>Renombra archivos al formato: YYYYMMDD_HHMMSS.EXT</p>
            <p style='color: #dc3545;'><strong>ADVERTENCIA:</strong> Renombrar los archivos puede afectar a:</p>
            <ul style='color: #dc3545;'>
                <li>Detección de Live Photos</li>
                <li>Gestión de duplicados HEIC/JPG</li>
            </ul>
            <p style='color: #495057;'><em>Asegúrate de haber completado esas tareas antes de renombrar</em></p>
        """,
        rich=True,
        extra_style=None
    )
    layout.addWidget(info)

    create_details_textedit(window, 'rename_details', layout)

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    create_action_button(window, 'preview_rename_btn', "📋 Renombrar archivos", 'preview_renaming', color="#007bff")
    button_layout.addWidget(window.preview_rename_btn)

    layout.addLayout(button_layout)
    layout.addStretch()
    return widget
