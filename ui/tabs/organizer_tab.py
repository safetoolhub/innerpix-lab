from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QRadioButton, QButtonGroup
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
    title.setStyleSheet(styles.STYLE_TAB_TITLE_LARGE)
    layout.addWidget(title)
    
    # ===== DESCRIPCIÓN BREVE =====
    desc = QLabel("Organiza archivos de subdirectorios según diferentes criterios de clasificación")
    desc.setStyleSheet(styles.STYLE_TAB_DESC)
    layout.addWidget(desc)

    # ===== TIPO DE ORGANIZACIÓN =====
    org_type_group = QGroupBox("Tipo de Organización")
    org_type_group.setStyleSheet(styles.STYLE_GROUPBOX_STANDARD)
    org_type_layout = QVBoxLayout(org_type_group)
    org_type_layout.setContentsMargins(12, 4, 12, 8)
    org_type_layout.setSpacing(2)

    # Crear grupo de botones de radio
    window.org_type_button_group = QButtonGroup()

    # Opción 1: Mover a raíz
    window.org_type_root = QRadioButton("Mover a raíz - Consolida archivos en el directorio principal")
    window.org_type_root.setChecked(True)  # Por defecto
    window.org_type_root.setStyleSheet(styles.STYLE_RADIO_BUTTON)
    window.org_type_button_group.addButton(window.org_type_root, 0)
    org_type_layout.addWidget(window.org_type_root)

    # Opción 2: Clasificar por meses
    window.org_type_by_month = QRadioButton("Por meses (YYYY_MM) - Carpetas organizadas por fecha del archivo")
    window.org_type_by_month.setStyleSheet(styles.STYLE_RADIO_BUTTON)
    window.org_type_button_group.addButton(window.org_type_by_month, 1)
    org_type_layout.addWidget(window.org_type_by_month)

    # Opción 3: Separar WhatsApp
    window.org_type_whatsapp = QRadioButton("Separar WhatsApp - Carpeta específica para archivos de WhatsApp")
    window.org_type_whatsapp.setStyleSheet(styles.STYLE_RADIO_BUTTON)
    window.org_type_button_group.addButton(window.org_type_whatsapp, 2)
    org_type_layout.addWidget(window.org_type_whatsapp)

    # Conectar señal para re-generar plan cuando cambie el tipo de organización
    # OPTIMIZACIÓN: No re-analiza la estructura completa, solo regenera el plan de movimiento
    if hasattr(window, '_regenerate_organization_plan'):
        window.org_type_button_group.buttonClicked.connect(
            lambda: window._regenerate_organization_plan() if window.current_directory else None
        )

    layout.addWidget(org_type_group)

    # ===== RECOMENDACIONES =====
    info_group = QGroupBox()
    info_group.setStyleSheet(styles.STYLE_GROUPBOX_INFO)
    info_layout = QVBoxLayout(info_group)
    info_layout.setContentsMargins(12, 12, 12, 12)

    info_label = QLabel(
        "<p style='margin: 0; color: #495057; font-size: 12px;'>"
        "Los conflictos de nombres se resuelven automáticamente añadiendo sufijos numéricos.</p>"
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
        window, 'org_details', results_layout,
        placeholder="Los detalles del análisis aparecerán aquí después de seleccionar un directorio...",
        max_height=180
    )
    layout.addWidget(results_group)

    layout.addStretch()

    # ===== BOTONES DE ACCIÓN =====
    button_layout = QHBoxLayout()
    button_layout.setSpacing(10)
    button_layout.addStretch()

    from PyQt6.QtWidgets import QPushButton
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
