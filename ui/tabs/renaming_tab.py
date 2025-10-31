from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
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
    title.setStyleSheet(styles.STYLE_TAB_TITLE_LARGE)
    layout.addWidget(title)
    
    # ===== DESCRIPCIÓN BREVE =====
    desc = QLabel("Renombra archivos al formato: YYYYMMDD_HHMMSS_[VIDEO|PHOTO]_nnn.EXT")
    desc.setStyleSheet(styles.STYLE_TAB_DESC)
    layout.addWidget(desc)

    # ===== RECOMENDACIONES =====
    info_group = QGroupBox()
    info_group.setStyleSheet(styles.STYLE_GROUPBOX_INFO)
    info_layout = QVBoxLayout(info_group)
    info_layout.setContentsMargins(12, 12, 12, 12)

    info_label = QLabel(
        "<p style='margin: 0 0 6px 0;'><b style='color: #17a2b8;'>💡 Recomendación:</b> "
        "Ejecutar como paso final del proceso</p>"
        "<p style='margin: 0; color: #495057; font-size: 12px;'>"
        "Completa primero la limpieza de Live Photos y duplicados HEIC/JPG. "
        "Renombrar antes dificulta la detección automática.</p>"
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
        max_height=200
    )
    layout.addWidget(results_group)

    layout.addStretch()

    # ===== BOTONES DE ACCIÓN =====
    button_layout = QHBoxLayout()
    button_layout.setSpacing(10)
    button_layout.addStretch()

    from PyQt6.QtWidgets import QPushButton
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
