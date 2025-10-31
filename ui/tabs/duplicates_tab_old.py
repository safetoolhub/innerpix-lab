from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QGroupBox, QFrame,
                             QHBoxLayout, QPushButton, QSizePolicy, QTextEdit)
from PyQt6.QtCore import Qt
from ui import styles


def create_duplicates_tab(window):
    """Crea la pestaña de detección de duplicados con bloques independientes"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(8)
    layout.setContentsMargins(15, 12, 15, 12)

    # ===== TÍTULO =====
    title = QLabel("🔍 Detección de Duplicados")
    title.setStyleSheet("font-size: 16px; font-weight: 600; color: #212529;")
    layout.addWidget(title)
    
    # ===== DESCRIPCIÓN BREVE =====
    desc = QLabel("Busca archivos duplicados exactos (SHA256) o similares (análisis perceptual)")
    desc.setStyleSheet("font-size: 11px; color: #6c757d; margin-bottom: 4px;")
    layout.addWidget(desc)

    # ========================================================================
    # BLOQUE 1: DUPLICADOS EXACTOS
    # ========================================================================
    exact_card = _create_exact_duplicates_card(window)
    layout.addWidget(exact_card)
    
    # ========================================================================
    # BLOQUE 2: DUPLICADOS SIMILARES
    # ========================================================================
    similar_card = _create_similar_duplicates_card(window)
    layout.addWidget(similar_card)

    layout.addStretch()

    return widget


def _create_exact_duplicates_card(window) -> QGroupBox:
    """Crea el bloque de duplicados exactos con estado y acciones integradas"""
    card = QGroupBox("⚡ Duplicados Exactos (SHA256)")
    card.setStyleSheet("""
        QGroupBox {
            font-weight: 600;
            font-size: 13px;
            color: #2c5aa0;
            border: 1px solid #e3f2fd;
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 16px;
            background: #fafafa;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            background: white;
        }
    """)
    
    card_layout = QVBoxLayout(card)
    card_layout.setSpacing(6)
    card_layout.setContentsMargins(10, 8, 10, 8)
    
    # Fila de estado + botón integrado
    status_row = QHBoxLayout()
    status_row.setSpacing(8)
    
    # Label de estado (más compacto)
    window.exact_status_label = QLabel("⏳ Pendiente de análisis")
    window.exact_status_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #495057;")
    window.exact_status_label.setWordWrap(True)
    status_row.addWidget(window.exact_status_label, 1)
    
    # Botón de revisar/eliminar (compacto, alineado a la derecha)
    window.delete_exact_duplicates_btn = QPushButton("� Revisar")
    window.delete_exact_duplicates_btn.setStyleSheet("""
        QPushButton {
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #218838;
        }
        QPushButton:pressed {
            background-color: #1e7e34;
        }
    """)
    window.delete_exact_duplicates_btn.setMaximumHeight(24)
    window.delete_exact_duplicates_btn.setMaximumWidth(90)
    window.delete_exact_duplicates_btn.setVisible(False)
    window.delete_exact_duplicates_btn.clicked.connect(window.on_delete_exact_duplicates)
    status_row.addWidget(window.delete_exact_duplicates_btn)
    
    card_layout.addLayout(status_row)
    
    # Área de detalles (compacta, inicialmente oculta)
    window.exact_details_text = QTextEdit()
    window.exact_details_text.setReadOnly(True)
    window.exact_details_text.setMaximumHeight(60)
    window.exact_details_text.setStyleSheet("""
        QTextEdit {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 6px;
            font-size: 10px;
        }
    """)
    window.exact_details_text.setVisible(False)
    card_layout.addWidget(window.exact_details_text)
    
    return card


def _create_similar_duplicates_card(window) -> QGroupBox:
    """Crea el bloque de duplicados similares con estado y acciones integradas"""
    card = QGroupBox("🎨 Duplicados Similares (Perceptual)")
    card.setStyleSheet("""
        QGroupBox {
            font-weight: 600;
            font-size: 13px;
            color: #9c27b0;
            border: 1px solid #f3e5f5;
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 16px;
            background: #fafafa;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            background: white;
        }
    """)
    
    card_layout = QVBoxLayout(card)
    card_layout.setSpacing(6)
    card_layout.setContentsMargins(10, 8, 10, 8)
    
    # Control de sensibilidad (compacto)
    from PyQt6.QtWidgets import QSlider
    
    sens_layout = QHBoxLayout()
    sens_layout.setSpacing(8)
    
    sens_label = QLabel("Sensibilidad:")
    sens_label.setStyleSheet("font-size: 11px; color: #495057; font-weight: 600;")
    sens_layout.addWidget(sens_label)
    
    window.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
    window.sensitivity_slider.setRange(0, 20)
    window.sensitivity_slider.setValue(10)
    window.sensitivity_slider.setFixedWidth(140)
    window.sensitivity_slider.setMaximumHeight(20)
    window.sensitivity_slider.setStyleSheet(styles.STYLE_SLIDER_SENSITIVITY)
    sens_layout.addWidget(window.sensitivity_slider)
    
    window.sens_value_label = QLabel("Media (10)")
    window.sens_value_label.setStyleSheet("font-size: 10px; color: #6c757d;")
    sens_layout.addWidget(window.sens_value_label)
    
    sens_layout.addStretch()
    card_layout.addLayout(sens_layout)
    
    # Conectar slider
    window.sensitivity_slider.valueChanged.connect(
        lambda v: _update_sensitivity_label(window, v)
    )
    
    # Fila de estado + botones integrados (en línea)
    status_row = QHBoxLayout()
    status_row.setSpacing(8)
    
    # Label de estado
    window.similar_status_label = QLabel("⏳ No analizado")
    window.similar_status_label.setStyleSheet("font-size: 12px; font-weight: 600; color: #495057;")
    window.similar_status_label.setWordWrap(True)
    status_row.addWidget(window.similar_status_label, 1)
    
    # Botón de analizar (compacto)
    window.analyze_similar_btn = QPushButton("🔍 Analizar")
    window.analyze_similar_btn.setStyleSheet(styles.get_button_style("#007bff"))
    window.analyze_similar_btn.setMaximumHeight(28)
    window.analyze_similar_btn.setMaximumWidth(100)
    window.analyze_similar_btn.clicked.connect(window.on_analyze_similar_duplicates)
    status_row.addWidget(window.analyze_similar_btn)
    
    # Botón de cancelar (compacto, solo visible durante análisis)
    window.cancel_similar_btn = QPushButton("⏹")
    window.cancel_similar_btn.setStyleSheet(styles.get_button_style("#dc3545"))
    window.cancel_similar_btn.setMaximumHeight(28)
    window.cancel_similar_btn.setMaximumWidth(40)
    window.cancel_similar_btn.setVisible(False)
    window.cancel_similar_btn.setToolTip("Cancelar análisis")
    window.cancel_similar_btn.clicked.connect(window.on_cancel_similar_analysis)
    status_row.addWidget(window.cancel_similar_btn)
    
    # Botón de revisar (compacto, solo visible cuando hay resultados)
    window.review_similar_btn = QPushButton("� Revisar")
    window.review_similar_btn.setStyleSheet(styles.get_button_style("#17a2b8"))
    window.review_similar_btn.setMaximumHeight(28)
    window.review_similar_btn.setMaximumWidth(100)
    window.review_similar_btn.setVisible(False)
    window.review_similar_btn.clicked.connect(window.on_review_similar_duplicates)
    status_row.addWidget(window.review_similar_btn)
    
    card_layout.addLayout(status_row)
    
    # Área de detalles (compacta, inicialmente oculta)
    window.similar_details_text = QTextEdit()
    window.similar_details_text.setReadOnly(True)
    window.similar_details_text.setMaximumHeight(60)
    window.similar_details_text.setStyleSheet("""
        QTextEdit {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 6px;
            font-size: 10px;
        }
    """)
    window.similar_details_text.setVisible(False)
    card_layout.addWidget(window.similar_details_text)
    
    return card


def _update_sensitivity_label(window, value: int):
    """Actualiza el label del slider de sensibilidad"""
    descriptions = {
        0: "Muy Baja",
        5: "Baja",
        10: "Media",
        15: "Alta",
        20: "Muy Alta"
    }
    
    # Encontrar la descripción más cercana
    closest = min(descriptions.keys(), key=lambda x: abs(x - value))
    if abs(value - closest) <= 2:
        desc = descriptions[closest]
    else:
        desc = "Personalizada"
    
    window.sens_value_label.setText(f"{desc} ({value})")

