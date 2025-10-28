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
    info_group = QGroupBox("⚠️ Información Importante")
    info_group.setStyleSheet(
        "QGroupBox { font-weight: 600; color: #dc3545; border: 2px solid #f5c6cb; "
        "border-radius: 6px; margin-top: 12px; padding-top: 24px; background: #f8d7da; } "
        "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 8px; background: #f8d7da; }"
    )
    info_layout = QVBoxLayout(info_group)
    info_layout.setContentsMargins(16, 8, 16, 16)

    info_label = QLabel(
        "<p style='margin: 0 0 8px 0;'><b style='color: #721c24;'>⚠️ EJECUTAR ANTES DE RENOMBRAR ARCHIVOS</b></p>"
        "<p style='margin: 0 0 8px 0; color: #495057;'>"
        "Esta función detecta y limpia <b>Live Photos de iPhone</b> (parejas de foto + video .MOV).</p>"
        "<p style='margin: 0; color: #721c24;'>"
        "<b>ADVERTENCIA:</b> Si los archivos ya han sido renombrados, la detección puede fallar.</p>"
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
