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
    title.setStyleSheet(styles.STYLE_DUPLICATES_TITLE)
    layout.addWidget(title)
    
    # ===== DESCRIPCIÓN BREVE =====
    desc = QLabel("Busca archivos duplicados exactos (SHA256) o similares (análisis perceptual)")
    desc.setStyleSheet(styles.STYLE_DUPLICATES_DESC)
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
    card = QGroupBox("⚡ DUPLICADOS EXACTOS (SHA256)")
    card.setStyleSheet(styles.STYLE_DUPLICATES_EXACT_CARD)
    
    card_layout = QVBoxLayout(card)
    card_layout.setSpacing(8)
    card_layout.setContentsMargins(12, 12, 12, 12)
    
    # Descripción de funcionamiento
    help_label = QLabel("✓ Archivos 100% idénticos (hash SHA256)")
    help_label.setStyleSheet(styles.STYLE_DUPLICATES_HELP_LABEL)
    card_layout.addWidget(help_label)
    
    # Fila de estado + botón integrado
    status_row = QHBoxLayout()
    status_row.setSpacing(10)
    
    # Label de estado con instrucciones
    window.exact_status_label = QLabel("⏳ Analizando en el análisis inicial...")
    window.exact_status_label.setStyleSheet(styles.STYLE_DUPLICATES_STATUS_LABEL)
    window.exact_status_label.setWordWrap(True)
    status_row.addWidget(window.exact_status_label, 1)
    
    # Botón de revisar/eliminar (compacto, alineado a la derecha)
    window.delete_exact_duplicates_btn = QPushButton("📋 Revisar")
    window.delete_exact_duplicates_btn.setStyleSheet(styles.STYLE_DUPLICATES_REVIEW_BUTTON)
    window.delete_exact_duplicates_btn.setMinimumHeight(28)
    window.delete_exact_duplicates_btn.setMinimumWidth(100)
    window.delete_exact_duplicates_btn.setVisible(False)
    window.delete_exact_duplicates_btn.clicked.connect(window.on_delete_exact_duplicates)
    status_row.addWidget(window.delete_exact_duplicates_btn)
    
    card_layout.addLayout(status_row)
    
    # Área de detalles (sin scroll, altura fija)
    window.exact_details_text = QTextEdit()
    window.exact_details_text.setReadOnly(True)
    window.exact_details_text.setFixedHeight(105)
    window.exact_details_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    window.exact_details_text.setStyleSheet(styles.STYLE_DUPLICATES_DETAILS_TEXT)
    window.exact_details_text.setVisible(False)
    card_layout.addWidget(window.exact_details_text)
    
    return card


def _create_similar_duplicates_card(window) -> QGroupBox:
    """Crea el bloque de duplicados similares con estado y acciones integradas"""
    card = QGroupBox("🔍 DUPLICADOS SIMILARES (Perceptual)")
    card.setStyleSheet("""
        QGroupBox {
            font-weight: 700;
            font-size: 13px;
            border: 2px solid #9c27b0;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f3e5f5, stop:1 #ffffff);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 3px 12px;
            background-color: #9c27b0;
            color: white;
            border-radius: 4px;
            font-size: 13px;
        }
    """)
    
    card_layout = QVBoxLayout(card)
    card_layout.setSpacing(8)
    card_layout.setContentsMargins(12, 12, 12, 12)
    
    # Descripción de funcionamiento
    help_label = QLabel("🎨 Imágenes visualmente parecidas - Requiere análisis manual")
    help_label.setStyleSheet(styles.STYLE_DUPLICATES_SIMILAR_HELP)
    card_layout.addWidget(help_label)
    
    # Control de sensibilidad (compacto)
    from PyQt6.QtWidgets import QSlider
    
    sens_layout = QHBoxLayout()
    sens_layout.setSpacing(8)
    
    sens_label = QLabel("Sensibilidad:")
    sens_label.setStyleSheet(styles.STYLE_DUPLICATES_SENS_LABEL)
    sens_layout.addWidget(sens_label)
    
    window.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
    window.sensitivity_slider.setRange(0, 20)
    window.sensitivity_slider.setValue(10)
    window.sensitivity_slider.setFixedWidth(140)
    window.sensitivity_slider.setMaximumHeight(20)
    window.sensitivity_slider.setStyleSheet(styles.STYLE_SLIDER_SENSITIVITY)
    sens_layout.addWidget(window.sensitivity_slider)
    
    window.sens_value_label = QLabel("Media (10)")
    window.sens_value_label.setStyleSheet(styles.STYLE_DUPLICATES_SENS_VALUE)
    sens_layout.addWidget(window.sens_value_label)
    
    sens_layout.addStretch()
    card_layout.addLayout(sens_layout)
    
    # Conectar slider
    window.sensitivity_slider.valueChanged.connect(
        lambda v: _update_sensitivity_label(window, v)
    )
    
    # Fila de estado + botones integrados (en línea)
    status_row = QHBoxLayout()
    status_row.setSpacing(10)
    
    # Label de estado con instrucciones
    window.similar_status_label = QLabel("▶ Haz clic en 'Analizar' para buscar imágenes similares")
    window.similar_status_label.setStyleSheet(styles.STYLE_DUPLICATES_STATUS_LABEL)
    window.similar_status_label.setWordWrap(True)
    status_row.addWidget(window.similar_status_label, 1)
    
    # Botón de analizar (compacto)
    window.analyze_similar_btn = QPushButton("🔍 Analizar")
    window.analyze_similar_btn.setStyleSheet(styles.STYLE_DUPLICATES_ANALYZE_BUTTON)
    window.analyze_similar_btn.setMinimumHeight(28)
    window.analyze_similar_btn.setMinimumWidth(100)
    window.analyze_similar_btn.clicked.connect(window.on_analyze_similar_duplicates)
    status_row.addWidget(window.analyze_similar_btn)
    
    # Botón de cancelar (compacto, solo visible durante análisis)
    window.cancel_similar_btn = QPushButton("✕")
    window.cancel_similar_btn.setStyleSheet(styles.STYLE_DUPLICATES_CANCEL_BUTTON)
    window.cancel_similar_btn.setMinimumHeight(28)
    window.cancel_similar_btn.setMinimumWidth(35)
    window.cancel_similar_btn.setVisible(False)
    window.cancel_similar_btn.setToolTip("Cancelar análisis")
    window.cancel_similar_btn.clicked.connect(window.on_cancel_similar_analysis)
    status_row.addWidget(window.cancel_similar_btn)
    
    # Botón de revisar (compacto, solo visible cuando hay resultados)
    window.review_similar_btn = QPushButton("📋 Revisar")
    window.review_similar_btn.setStyleSheet(styles.STYLE_DUPLICATES_REVIEW_BUTTON)
    window.review_similar_btn.setMinimumHeight(28)
    window.review_similar_btn.setMinimumWidth(100)
    window.review_similar_btn.setVisible(False)
    window.review_similar_btn.clicked.connect(window.on_review_similar_duplicates)
    status_row.addWidget(window.review_similar_btn)
    
    card_layout.addLayout(status_row)
    
    # Área de detalles (sin scroll, altura fija)
    window.similar_details_text = QTextEdit()
    window.similar_details_text.setReadOnly(True)
    window.similar_details_text.setFixedHeight(120)
    window.similar_details_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    window.similar_details_text.setStyleSheet("""
        QTextEdit {
            background-color: white;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 8px;
            font-size: 11px;
            line-height: 1.4;
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
