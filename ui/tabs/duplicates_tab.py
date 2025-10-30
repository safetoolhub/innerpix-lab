from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGroupBox, QFrame,
                             QHBoxLayout, QPushButton, QSizePolicy, QButtonGroup,
                             QRadioButton, QSlider)
from PyQt6.QtCore import Qt, QTimer
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
    title.setStyleSheet("font-size: 20px; font-weight: 600; color: #212529; margin-bottom: 4px;")
    layout.addWidget(title)
    
    # ===== DESCRIPCIÓN BREVE =====
    desc = QLabel("Busca archivos duplicados exactos (SHA256) o similares (análisis perceptual)")
    desc.setStyleSheet("font-size: 13px; color: #6c757d; margin-bottom: 8px;")
    layout.addWidget(desc)

    # ===== OPCIONES DE DETECCIÓN =====
    options_group = QGroupBox("Opciones de Detección")
    options_group.setStyleSheet(styles.STYLE_GROUPBOX_STANDARD)
    options_layout = QVBoxLayout(options_group)
    options_layout.setSpacing(8)
    options_layout.setContentsMargins(12, 8, 12, 12)
    window.duplicate_mode_group = QButtonGroup()


    # ---- Opción Exactos ----
    exact_block = QFrame()
    exact_block.setStyleSheet(styles.STYLE_FRAME_EXACT_MODE)
    exact_layout = QVBoxLayout(exact_block)
    exact_layout.setContentsMargins(10, 8, 10, 8)
    exact_layout.setSpacing(4)

    window.exact_mode_radio = QRadioButton("⚡ Duplicados Exactos (SHA256)")
    window.exact_mode_radio.setChecked(True)
    window.exact_mode_radio.setStyleSheet(styles.STYLE_RADIO_BUTTON_BOLD)
    window.duplicate_mode_group.addButton(window.exact_mode_radio, 0)
    exact_layout.addWidget(window.exact_mode_radio)

    window.exact_info = QLabel("Archivos 100% idénticos. Detección rápida y segura.")
    window.exact_info.setStyleSheet(styles.STYLE_LABEL_INFO_MARGIN)
    window.exact_info.setWordWrap(True)
    exact_layout.addWidget(window.exact_info)
    options_layout.addWidget(exact_block)

    # ---- Opción Similares ----
    similar_block = QFrame()
    similar_block.setStyleSheet(styles.STYLE_FRAME_SIMILAR_MODE)
    similar_layout = QVBoxLayout(similar_block)
    similar_layout.setContentsMargins(10, 8, 10, 8)
    similar_layout.setSpacing(4)

    window.similar_mode_radio = QRadioButton("🎨 Duplicados Similares (Perceptual)")
    window.similar_mode_radio.setStyleSheet(styles.STYLE_RADIO_BUTTON_BOLD)
    window.duplicate_mode_group.addButton(window.similar_mode_radio, 1)
    similar_layout.addWidget(window.similar_mode_radio)

    window.similar_info = QLabel(
        "Imágenes visualmente idénticas o muy parecidas. Detecta copias redimensionadas. Requiere revisión."
    )
    window.similar_info.setStyleSheet(styles.STYLE_LABEL_INFO_MARGIN)
    window.similar_info.setWordWrap(True)
    similar_layout.addWidget(window.similar_info)

    # Slider de sensibilidad
    slider_container = QFrame()
    slider_container.setStyleSheet("QFrame { background: transparent; border: none; }")
    slider_layout = QHBoxLayout(slider_container)
    slider_layout.setContentsMargins(20, 4, 10, 0)
    slider_layout.setSpacing(8)

    window.sens_low_lbl = QLabel("Baja")
    window.sens_low_lbl.setStyleSheet(styles.STYLE_LABEL_MUTED_SMALL)

    window.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
    window.sensitivity_slider.setRange(0, 20)
    window.sensitivity_slider.setValue(10)
    window.sensitivity_slider.setFixedWidth(140)
    window.sensitivity_slider.setStyleSheet(styles.STYLE_SLIDER_SENSITIVITY)

    window.sens_high_lbl = QLabel("Alta")
    window.sens_high_lbl.setStyleSheet(styles.STYLE_LABEL_MUTED_SMALL)

    window.sens_value_lbl = QLabel(f"Sensibilidad: {window.sensitivity_slider.value()}")
    window.sens_value_lbl.setStyleSheet(styles.STYLE_LABEL_SUCCESS_BOLD)

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

        # Limpiar resultados antiguos al cambiar de modo
        last_results = window.duplicate_detector.get_last_results()
        if last_results:
            # Verificar si el modo actual coincide con los resultados guardados
            current_mode = 'exact' if is_exact else 'perceptual'
            # last_results es un DuplicateAnalysisResult (dataclass)
            saved_mode = last_results.mode
            
            if current_mode != saved_mode:
                # El modo cambió, limpiar resultados y ocultar botones
                window.duplicate_detector.clear_last_results()
                window.delete_exact_duplicates_btn.setVisible(False)
                window.review_similar_btn.setVisible(False)
                
                # Mostrar mensaje indicando que se necesita analizar de nuevo
                from utils.format_utils import markdown_like_to_html
                mode_text = "exactos" if is_exact else "similares"
                try:
                    window.duplicates_details.setHtml(markdown_like_to_html(
                        f"ℹ️ **Modo cambiado a duplicados {mode_text}**\n\n"
                        f"Los resultados anteriores han sido limpiados.\n"
                        f"Haz clic en **'Analizar'** para buscar duplicados {mode_text}."
                    ))
                except Exception:
                    pass

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
        "border-radius: 6px; margin-top: 8px; padding-top: 20px; } "
        "QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 8px; background: white; }"
    )
    results_layout = QVBoxLayout(results_group)
    results_layout.setContentsMargins(12, 8, 12, 12)

    create_details_textedit(
        window, 'duplicates_details', results_layout,
        placeholder="Haz clic en 'Analizar Duplicados' para comenzar la detección...",
        max_height=180
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

    window.cancel_duplicates_btn = QPushButton("⏹ Cancelar Análisis")
    window.cancel_duplicates_btn.setStyleSheet(styles.get_button_style("#dc3545"))
    window.cancel_duplicates_btn.setMinimumHeight(36)
    window.cancel_duplicates_btn.setVisible(False)
    window.cancel_duplicates_btn.clicked.connect(window.on_cancel_duplicate_analysis)
    button_layout.addWidget(window.cancel_duplicates_btn)

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

