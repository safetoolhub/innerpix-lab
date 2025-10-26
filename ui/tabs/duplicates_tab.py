from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGroupBox, QFrame,
                             QHBoxLayout, QPushButton, QSizePolicy, QButtonGroup,
                             QRadioButton, QSlider)
from PyQt5.QtCore import Qt, QTimer
from ui.tabs.base_tab import create_details_textedit
from ui import styles


def create_duplicates_tab(window):
    """Crea la pestaña de detección de duplicados con diseño unificado"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(16)
    layout.setContentsMargins(20, 20, 20, 20)

    # ===== TÍTULO =====
    title = QLabel("🔍 Detección de Duplicados")
    title.setStyleSheet(
        "font-size: 20px; font-weight: 600; color: #212529; margin-bottom: 8px;"
    )
    layout.addWidget(title)

    # ===== OPCIONES DE DETECCIÓN =====
    options_group = QGroupBox("Opciones de Detección")
    options_group.setStyleSheet(
        "QGroupBox { font-weight: 600; color: #495057; border: 1px solid #dee2e6; "
        "border-radius: 6px; margin-top: 12px; padding-top: 20px; } "
        "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 8px; background: white; }"
    )
    options_layout = QVBoxLayout(options_group)
    options_layout.setSpacing(12)
    options_layout.setContentsMargins(16, 8, 16, 16)
    window.duplicate_mode_group = QButtonGroup()


    # ---- Opción Exactos ----
    exact_block = QFrame()
    exact_block.setStyleSheet(
        "QFrame { background: #f5f8fc; border-radius: 8px; border: 1px solid #d1e3f5; }"
    )
    exact_layout = QVBoxLayout(exact_block)
    exact_layout.setContentsMargins(12, 10, 12, 10)
    exact_layout.setSpacing(6)

    window.exact_mode_radio = QRadioButton("⚡ Duplicados Exactos (SHA256)")
    window.exact_mode_radio.setChecked(True)
    window.exact_mode_radio.setStyleSheet("font-weight: 500; font-size: 14px;")
    window.duplicate_mode_group.addButton(window.exact_mode_radio, 0)
    exact_layout.addWidget(window.exact_mode_radio)

    window.exact_info = QLabel("Archivos 100% idénticos bit a bit. Detección <b>rápida y segura</b>.")
    window.exact_info.setStyleSheet(
        "margin-left: 24px; color: #495057; font-size: 13px;"
    )
    window.exact_info.setWordWrap(True)
    exact_layout.addWidget(window.exact_info)
    options_layout.addWidget(exact_block)

    # ---- Opción Similares ----
    similar_block = QFrame()
    similar_block.setStyleSheet(
        "QFrame { background: #f4fcf7; border-radius: 8px; border: 1px solid #c3e6cb; }"
    )
    similar_layout = QVBoxLayout(similar_block)
    similar_layout.setContentsMargins(12, 10, 12, 10)
    similar_layout.setSpacing(6)

    window.similar_mode_radio = QRadioButton("🎨 Duplicados Similares (Perceptual)")
    window.similar_mode_radio.setStyleSheet("font-weight: 500; font-size: 14px;")
    window.duplicate_mode_group.addButton(window.similar_mode_radio, 1)
    similar_layout.addWidget(window.similar_mode_radio)

    window.similar_info = QLabel(
        "Archivos visualmente idénticos o muy parecidos. "
        "Detecta copias <b>redimensionadas o recomprimidas</b>. Requiere revisión manual."
    )
    window.similar_info.setStyleSheet(
        "margin-left: 24px; color: #495057; font-size: 13px;"
    )
    window.similar_info.setWordWrap(True)
    similar_layout.addWidget(window.similar_info)

    # Slider de sensibilidad
    slider_container = QFrame()
    slider_container.setStyleSheet("QFrame { background: transparent; border: none; }")
    slider_layout = QHBoxLayout(slider_container)
    slider_layout.setContentsMargins(24, 8, 12, 0)
    slider_layout.setSpacing(10)

    window.sens_low_lbl = QLabel("Baja")
    window.sens_low_lbl.setStyleSheet("color: #6c757d; font-size: 12px;")

    window.sensitivity_slider = QSlider(Qt.Horizontal)
    window.sensitivity_slider.setRange(0, 20)
    window.sensitivity_slider.setValue(10)
    window.sensitivity_slider.setFixedWidth(160)
    window.sensitivity_slider.setStyleSheet(
        "QSlider::groove:horizontal { height: 6px; background: #d4edda; border-radius: 3px; } "
        "QSlider::handle:horizontal { background: #28a745; border-radius: 7px; width: 14px; height: 14px; margin: -4px 0; }"
    )

    window.sens_high_lbl = QLabel("Alta")
    window.sens_high_lbl.setStyleSheet("color: #6c757d; font-size: 12px;")

    window.sens_value_lbl = QLabel(f"Sensibilidad: {window.sensitivity_slider.value()}")
    window.sens_value_lbl.setStyleSheet("color: #28a745; font-size: 13px; font-weight: 500;")

    slider_layout.addWidget(window.sens_low_lbl)
    slider_layout.addWidget(window.sensitivity_slider)
    slider_layout.addWidget(window.sens_high_lbl)
    slider_layout.addWidget(window.sens_value_lbl)
    slider_layout.addStretch()

    similar_layout.addWidget(slider_container)
    options_layout.addWidget(similar_block)

    layout.addWidget(options_group)

    # Función de actualización de modo
    def update_mode():
        is_exact = window.exact_mode_radio.isChecked()
        is_similar = window.similar_mode_radio.isChecked()

        # Mostrar/ocultar info según el modo seleccionado
        window.exact_info.setVisible(is_exact)
        window.similar_info.setVisible(is_similar)
        slider_container.setVisible(is_similar)

    window.exact_mode_radio.toggled.connect(update_mode)
    window.similar_mode_radio.toggled.connect(update_mode)
    window.sensitivity_slider.valueChanged.connect(
        lambda v: window.sens_value_lbl.setText(f"Sensibilidad: {v}")
    )

    # Aplicar estado inicial
    QTimer.singleShot(0, update_mode)

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
        window, 'duplicates_details', results_layout,
        placeholder="Haz clic en 'Analizar Duplicados' para comenzar la detección...",
        max_height=250
    )
    layout.addWidget(results_group)

    layout.addStretch()

    # ===== BOTONES DE ACCIÓN =====
    button_layout = QHBoxLayout()
    button_layout.setSpacing(10)

    window.analyze_duplicates_btn = QPushButton("🔍 Analizar Duplicados")
    window.analyze_duplicates_btn.setStyleSheet(styles.get_button_style("#007bff"))
    window.analyze_duplicates_btn.setMinimumHeight(36)
    window.analyze_duplicates_btn.clicked.connect(window.on_analyze_duplicates)
    button_layout.addWidget(window.analyze_duplicates_btn)

    window.delete_exact_duplicates_btn = QPushButton("⚡ Eliminar Duplicados Exactos")
    window.delete_exact_duplicates_btn.setStyleSheet(styles.get_button_style("#28a745"))
    window.delete_exact_duplicates_btn.setMinimumHeight(36)
    window.delete_exact_duplicates_btn.setVisible(False)
    window.delete_exact_duplicates_btn.clicked.connect(window.on_delete_exact_duplicates)
    button_layout.addWidget(window.delete_exact_duplicates_btn)

    window.review_similar_btn = QPushButton("🔍 Revisar Similares")
    window.review_similar_btn.setStyleSheet(styles.get_button_style("#17a2b8"))
    window.review_similar_btn.setMinimumHeight(36)
    window.review_similar_btn.setVisible(False)
    window.review_similar_btn.clicked.connect(window.on_review_similar_duplicates)
    button_layout.addWidget(window.review_similar_btn)

    layout.addLayout(button_layout)

    return widget



def _on_duplicate_mode_changed(window):
    """Maneja cambio en el modo de detección de duplicados"""
    # Ocultar botones de acción al cambiar de modo
    window.delete_exact_duplicates_btn.setVisible(False)
    window.review_similar_btn.setVisible(False)

    # Limpiar resultados previos
    window.duplicates_details.clear()
    window.duplicates_details.setPlaceholderText(
        "Haz clic en 'Analizar Duplicados' para comenzar la detección..."
    )

    # Resetear estado centralizado en el servicio DuplicateDetector
    if hasattr(window, 'duplicate_detector'):
        window.duplicate_detector.clear_last_results()


def _on_sensitivity_changed(window, value):
    """Actualiza el label del slider de sensibilidad"""
    descriptions = {
        0: "Muy Baja (Solo idénticos)",
        5: "Baja",
        10: "Media (Recomendado)",
        15: "Alta",
        20: "Muy Alta (Tolerante)"
    }
    closest = min(descriptions.keys(), key=lambda x: abs(x - value))
    desc = descriptions.get(value, descriptions[closest])
    window.sens_value_lbl.setText(f"Sensibilidad: {value} ({desc})")

