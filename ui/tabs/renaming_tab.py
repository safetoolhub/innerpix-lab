from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from ui.tabs.base_tab import create_details_textedit
from ui import styles


def create_renaming_tab(window):
    """Crea la pestaña de renombrado de archivos con diseño unificado"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(16)
    layout.setContentsMargins(20, 20, 20, 20)

    # ===== TÍTULO =====
    title = QLabel("📝 Renombrado de Archivos")
    title.setStyleSheet(styles.STYLE_TAB_TITLE)
    layout.addWidget(title)

    # ===== INFORMACIÓN IMPORTANTE =====
    info_group = QGroupBox("⚠️ Información Importante")
    info_group.setStyleSheet(styles.STYLE_GROUPBOX_WARNING)
    info_layout = QVBoxLayout(info_group)
    info_layout.setContentsMargins(16, 8, 16, 16)

    info_label = QLabel(
        "<p style='margin: 0 0 8px 0;'><b style='color: #721c24;'>⚠️ EJECUTAR COMO ÚLTIMO PASO</b></p>"
        "<p style='margin: 0 0 8px 0; color: #495057;'>"
        "Esta función renombra archivos al formato: <b>YYYYMMDD_HHMMSS.EXT</b></p>"
        "<p style='margin: 0 0 4px 0; color: #721c24;'><b>ADVERTENCIA:</b> Renombrar los archivos puede afectar a:</p>"
        "<ul style='margin: 0 0 0 20px; padding: 0; color: #721c24;'>"
        "<li>Detección de Live Photos</li>"
        "<li>Gestión de duplicados HEIC/JPG</li>"
        "</ul>"
        "<p style='margin: 8px 0 0 0; color: #495057;'>"
        "<em>Asegúrate de haber completado esas tareas antes de renombrar.</em></p>"
    )
    info_label.setWordWrap(True)
    info_layout.addWidget(info_label)
    layout.addWidget(info_group)

    # ===== RESULTADOS =====
    results_group = QGroupBox("Resultados del Análisis")
    results_group.setStyleSheet(styles.STYLE_GROUPBOX_STANDARD)
    results_layout = QVBoxLayout(results_group)
    results_layout.setContentsMargins(16, 8, 16, 16)

    create_details_textedit(
        window, 'rename_details', results_layout,
        placeholder="Los detalles del análisis aparecerán aquí después de seleccionar un directorio...",
        max_height=250
    )
    layout.addWidget(results_group)

    layout.addStretch()

    # ===== BOTONES DE ACCIÓN =====
    button_layout = QHBoxLayout()
    button_layout.setSpacing(10)
    button_layout.addStretch()

    from PyQt5.QtWidgets import QPushButton
    window.preview_rename_btn = QPushButton("📋 Renombrar Archivos")
    window.preview_rename_btn.setEnabled(False)
    window.preview_rename_btn.setStyleSheet(styles.get_button_style("#007bff"))
    window.preview_rename_btn.setMinimumHeight(36)
    window.preview_rename_btn.setMinimumWidth(200)
    if hasattr(window, 'preview_renaming'):
        window.preview_rename_btn.clicked.connect(window.preview_renaming)
    button_layout.addWidget(window.preview_rename_btn)

    layout.addLayout(button_layout)

    return widget
