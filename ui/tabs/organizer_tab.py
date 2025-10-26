from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from ui.tabs.base_tab import create_details_textedit
from ui import styles


def create_organizer_tab(window):
    """Crea la pestaña de organización de archivos con diseño unificado"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(16)
    layout.setContentsMargins(20, 20, 20, 20)

    # ===== TÍTULO =====
    title = QLabel("📁 Organización de Archivos")
    title.setStyleSheet(
        "font-size: 20px; font-weight: 600; color: #212529; margin-bottom: 8px;"
    )
    layout.addWidget(title)

    # ===== INFORMACIÓN =====
    info_group = QGroupBox("Información")
    info_group.setStyleSheet(
        "QGroupBox { font-weight: 600; color: #495057; border: 1px solid #dee2e6; "
        "border-radius: 6px; margin-top: 12px; padding-top: 20px; } "
        "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 8px; background: white; }"
    )
    info_layout = QVBoxLayout(info_group)
    info_layout.setContentsMargins(16, 8, 16, 16)

    info_label = QLabel(
        "Esta función mueve todos los archivos encontrados en subdirectorios "
        "al <b>directorio raíz seleccionado</b>.<br><br>"
        "Útil para consolidar archivos dispersos en múltiples carpetas."
    )
    info_label.setStyleSheet(
        "color: #495057; font-size: 13px; line-height: 1.6;"
    )
    info_label.setWordWrap(True)
    info_layout.addWidget(info_label)
    layout.addWidget(info_group)

    # ===== RESULTADOS =====
    results_group = QGroupBox("Resultados del Análisis")
    results_group.setStyleSheet(
        "QGroupBox { font-weight: 600; color: #495057; border: 1px solid #dee2e6; "
        "border-radius: 6px; margin-top: 12px; padding-top: 20px; } "
        "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 8px; background: white; }"
    )
    results_layout = QVBoxLayout(results_group)
    results_layout.setContentsMargins(16, 8, 16, 16)

    create_details_textedit(
        window, 'org_details', results_layout,
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
    window.exec_org_btn = QPushButton("⚡ Organizar Archivos")
    window.exec_org_btn.setEnabled(False)
    window.exec_org_btn.setStyleSheet(styles.get_button_style("#28a745"))
    window.exec_org_btn.setMinimumHeight(36)
    window.exec_org_btn.setMinimumWidth(200)
    if hasattr(window, 'organize_files'):
        window.exec_org_btn.clicked.connect(window.organize_files)
    button_layout.addWidget(window.exec_org_btn)

    layout.addLayout(button_layout)

    return widget
