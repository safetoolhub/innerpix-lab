from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
from ui.tabs.base_tab import create_details_textedit
from ui import styles
from utils.icons import icon_manager


def create_heic_tab(window):
    """Crea la pestaña de eliminación de duplicados HEIC/JPG con diseño unificado"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(16)
    layout.setContentsMargins(20, 20, 20, 20)

    # ===== TÍTULO =====
    title_container = QWidget()
    title_layout = QHBoxLayout(title_container)
    title_layout.setContentsMargins(0, 0, 0, 0)
    title_layout.setSpacing(10)
    
    title_icon = icon_manager.create_icon_label('heic', color='#2563eb', size=24)
    title_layout.addWidget(title_icon)
    
    title = QLabel("Eliminación de Duplicados HEIC/JPG")
    title.setStyleSheet(styles.STYLE_TAB_TITLE_LARGE)
    title_layout.addWidget(title)
    title_layout.addStretch()
    
    layout.addWidget(title_container)
    
    # ===== DESCRIPCIÓN BREVE =====
    desc = QLabel("Elimina archivos HEIC duplicados cuando existe la versión JPG con el mismo nombre")
    desc.setStyleSheet(styles.STYLE_TAB_DESC)
    layout.addWidget(desc)

    # ===== RECOMENDACIONES =====
    info_group = QGroupBox()
    info_group.setStyleSheet(styles.STYLE_GROUPBOX_INFO)
    info_layout = QVBoxLayout(info_group)
    info_layout.setContentsMargins(12, 12, 12, 12)

    info_label = QLabel(
        "<p style='margin: 0 0 6px 0;'><b style='color: #17a2b8;'>ℹ Recomendación:</b> "
        "Ejecutar antes de renombrar archivos</p>"
        "<p style='margin: 0; color: #495057; font-size: 12px;'>"
        "Se conservarán los archivos JPG y se eliminarán los HEIC correspondientes. "
        "La detección funciona mejor con nombres originales.</p>"
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
        window, 'heic_details', results_layout,
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
    window.exec_heic_btn = QPushButton(" Eliminar Duplicados HEIC")
    icon_manager.set_button_icon(window.exec_heic_btn, 'delete', color='#ffffff', size=16)
    window.exec_heic_btn.setEnabled(False)
    window.exec_heic_btn.setStyleSheet(styles.get_button_style("#28a745"))
    window.exec_heic_btn.setMinimumHeight(36)
    window.exec_heic_btn.setMinimumWidth(200)
    if hasattr(window, 'remove_heic'):
        window.exec_heic_btn.clicked.connect(window.remove_heic)
    button_layout.addWidget(window.exec_heic_btn)

    layout.addLayout(button_layout)

    return widget
