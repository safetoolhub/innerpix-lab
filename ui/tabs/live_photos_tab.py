from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from ui.tabs.base_tab import create_details_textedit
from ui import styles


def create_live_photos_tab(window):
    """Crea la pestaña de limpieza de Live Photos con diseño unificado"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(16)
    layout.setContentsMargins(20, 20, 20, 20)

    # ===== TÍTULO =====
    title = QLabel("🎬 Limpieza de Live Photos")
    title.setStyleSheet(
        "font-size: 20px; font-weight: 600; color: #212529; margin-bottom: 8px;"
    )
    layout.addWidget(title)

    # ===== INFORMACIÓN IMPORTANTE =====
    info_group = QGroupBox()
    info_group.setStyleSheet(styles.STYLE_GROUPBOX_INFO)
    info_layout = QVBoxLayout(info_group)
    info_layout.setContentsMargins(16, 16, 16, 16)

    info_label = QLabel(
        "<p style='margin: 0 0 12px 0; font-size: 14px;'><b style='color: #17a2b8;'>💡 Recomendación de Uso</b></p>"
        "<p style='margin: 0 0 8px 0; color: #0c5460;'><b>📌 Mejor momento para ejecutar:</b> Antes de renombrar archivos</p>"
        "<p style='margin: 0 0 12px 0; color: #495057;'>"
        "Esta función detecta y limpia <b>Live Photos de iPhone</b>, que consisten en una imagen JPG "
        "acompañada de un video MOV corto.</p>"
        "<p style='margin: 0; color: #0c5460;'>"
        "<b>Nota:</b> La detección funciona mejor cuando los archivos mantienen sus nombres originales. "
        "Si ya has renombrado los archivos, algunos Live Photos podrían no detectarse correctamente.</p>"
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
        window, 'lp_details', results_layout,
        placeholder="Los detalles del análisis aparecerán aquí después de seleccionar un directorio...",
        max_height=250
    )
    layout.addWidget(results_group)

    layout.addStretch()

    # ===== BOTONES DE ACCIÓN =====
    button_layout = QHBoxLayout()
    button_layout.setSpacing(10)
    button_layout.addStretch()

    from PyQt6.QtWidgets import QPushButton
    window.exec_lp_btn = QPushButton("⚡ Limpiar Live Photos")
    window.exec_lp_btn.setEnabled(False)
    window.exec_lp_btn.setStyleSheet(styles.get_button_style("#28a745"))
    window.exec_lp_btn.setMinimumHeight(36)
    window.exec_lp_btn.setMinimumWidth(200)
    if hasattr(window, 'cleanup_live_photos'):
        window.exec_lp_btn.clicked.connect(window.cleanup_live_photos)
    button_layout.addWidget(window.exec_lp_btn)

    layout.addLayout(button_layout)

    return widget
