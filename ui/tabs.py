"""Módulo que contiene la lógica de creación de las pestañas de la UI.
Extraído desde `ui_helpers.py` para mejorar la modularidad.
Cada función recibe la instancia principal `window` cuando necesita acceder a
atributos o widgets de la ventana.
"""
from PyQt5.QtWidgets import (
    QTabWidget, QWidget, QTextEdit, QGroupBox, QRadioButton, QHBoxLayout,
    QVBoxLayout, QLabel, QPushButton, QSizePolicy, QFrame, QSlider, QButtonGroup
)
from PyQt5.QtCore import Qt, QTimer

from ui import styles


from ui.ui_helpers import service_available


def create_tabs_widget(window):
    tabs = QTabWidget()
    tabs.setStyleSheet(styles.STYLE_TAB_WIDGET)
    tabs.setVisible(False)
    window.tab_index_map = {}
    idx = 0
    if service_available(window, 'live_photo_detector'):
        tabs.addTab(create_live_photos_tab(window), "(1) 📱 Live Photos")
        window.tab_index_map['live_photos'] = idx
        idx += 1
    if service_available(window, 'heic_remover'):
        tabs.addTab(create_heic_tab(window), "(2) 🖼️ Duplicados HEIC")
        window.tab_index_map['heic'] = idx
        idx += 1
    if service_available(window, 'directory_unifier'):
        tabs.addTab(create_unification_tab(window), "(3) 📁 Unificar Directorios")
        window.tab_index_map['unification'] = idx
        idx += 1
    if service_available(window, 'renamer'):
        tabs.addTab(create_renaming_tab(window), "(4) 📝 Renombrado")
        window.tab_index_map['renaming'] = idx
        idx += 1

    # Tab 5: Duplicados. Mantener estructura existente
    if True:
        duplicates_tab = create_duplicates_tab(window)
        tabs.addTab(duplicates_tab, "(5) 🔍 Duplicados")

    return tabs


def open_summary_action(window, label_substr):
    if not hasattr(window, 'tabs_widget') or window.tabs_widget.count() == 0:
        return
    if hasattr(window, 'tab_index_map'):
        key_map = {
            'live photos': 'live_photos',
            'duplicados heic': 'heic',
            'unificar directorios': 'unification',
            'renombrado': 'renaming'
        }
        lookup = key_map.get(label_substr.lower())
        if lookup and lookup in window.tab_index_map:
            window.tabs_widget.setCurrentIndex(window.tab_index_map[lookup])
            window.tabs_widget.setVisible(True)
            return
    if window.tabs_widget.count() > 0:
        window.tabs_widget.setCurrentIndex(0)
        window.tabs_widget.setVisible(True)
    return


def create_renaming_tab(window):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    info = QLabel("""
            <p><strong>⚠️ IMPORTANTE: Ejecutar como último paso</strong></p>
            <p>Renombra archivos al formato: YYYYMMDD_HHMMSS.EXT</p>
            <p style='color: #dc3545;'><strong>ADVERTENCIA:</strong> Renombrar los archivos puede afectar a:</p>
            <ul style='color: #dc3545;'>
                <li>Detección de Live Photos</li>
                <li>Gestión de duplicados HEIC/JPG</li>
            </ul>
            <p style='color: #495057;'><em>Asegúrate de haber completado esas tareas antes de renombrar</em></p>
        """)
    info.setTextFormat(Qt.RichText)
    info.setStyleSheet("""
            QLabel {
                color: #495057;
                padding: 15px;
                background-color: #fff3cd;
                border: 1px solid #ffeeba;
                border-radius: 4px;
                margin-bottom: 10px;
            }
        """)
    layout.addWidget(info)

    window.rename_details = QTextEdit()
    window.rename_details.setReadOnly(True)
    window.rename_details.setMaximumHeight(200)
    window.rename_details.setPlaceholderText("Los detalles aparecerán después del análisis...")
    layout.addWidget(window.rename_details)

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    window.preview_rename_btn = QPushButton("📋 Renombrar archivos")
    window.preview_rename_btn.setEnabled(False)
    window.preview_rename_btn.clicked.connect(window.preview_renaming)
    window.preview_rename_btn.setStyleSheet(styles.get_button_style("#007bff"))
    button_layout.addWidget(window.preview_rename_btn)

    layout.addLayout(button_layout)
    layout.addStretch()
    return widget


def create_live_photos_tab(window):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    info = QLabel("""
            <p><strong>⚠️ IMPORTANTE: Ejecutar ANTES de renombrar archivos</strong></p>
            <p>Detecta y limpia Live Photos de iPhone (parejas de foto + video .MOV)</p>
            <p style='color: #dc3545;'><em>Si los archivos ya han sido renombrados, la detección puede fallar</em></p>
        """)
    info.setTextFormat(Qt.RichText)
    info.setStyleSheet("color: #495057; padding: 10px; background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 4px;")
    layout.addWidget(info)

    window.lp_details = QTextEdit()
    window.lp_details.setReadOnly(True)
    window.lp_details.setMaximumHeight(200)
    window.lp_details.setPlaceholderText("Los detalles aparecerán después del análisis...")
    layout.addWidget(window.lp_details)

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    window.exec_lp_btn = QPushButton("⚡ Limpiar Live Photos")
    window.exec_lp_btn.setEnabled(False)
    window.exec_lp_btn.clicked.connect(window.cleanup_live_photos)
    window.exec_lp_btn.setStyleSheet(styles.get_button_style("#28a745"))
    button_layout.addWidget(window.exec_lp_btn)

    layout.addLayout(button_layout)
    layout.addStretch()
    return widget


def create_unification_tab(window):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    info = QLabel("Mueve todos los archivos al directorio raíz")
    info.setStyleSheet("color: #6c757d; padding: 10px; font-style: italic;")
    layout.addWidget(info)

    window.unif_details = QTextEdit()
    window.unif_details.setReadOnly(True)
    window.unif_details.setMaximumHeight(200)
    window.unif_details.setPlaceholderText("Los detalles aparecerán después del análisis...")
    layout.addWidget(window.unif_details)

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    window.exec_unif_btn = QPushButton("⚡ Unificar Directorios")
    window.exec_unif_btn.setEnabled(False)
    window.exec_unif_btn.clicked.connect(window.unify_directories)
    window.exec_unif_btn.setStyleSheet(styles.get_button_style("#28a745"))
    button_layout.addWidget(window.exec_unif_btn)

    layout.addLayout(button_layout)
    layout.addStretch()
    return widget


def create_heic_tab(window):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    info = QLabel("Elimina duplicados cuando existen archivos HEIC y JPG con el mismo nombre")
    info.setStyleSheet("color: #6c757d; padding: 10px; font-style: italic;")
    layout.addWidget(info)

    window.heic_details = QTextEdit()
    window.heic_details.setReadOnly(True)
    window.heic_details.setMaximumHeight(200)
    window.heic_details.setPlaceholderText("Los detalles aparecerán después del análisis...")
    layout.addWidget(window.heic_details)

    button_layout = QHBoxLayout()
    button_layout.addStretch()

    window.exec_heic_btn = QPushButton("⚡ Eliminar Duplicados")
    window.exec_heic_btn.setEnabled(False)
    window.exec_heic_btn.clicked.connect(window.remove_heic)
    window.exec_heic_btn.setStyleSheet(styles.get_button_style("#28a745"))
    button_layout.addWidget(window.exec_heic_btn)

    layout.addLayout(button_layout)
    layout.addStretch()
    return widget


def create_duplicates_tab(window):
    # Importes locales para reducir dependencias en el módulo superior
    from PyQt5.QtWidgets import QSlider

    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setSpacing(12)
    layout.setContentsMargins(18, 18, 18, 18)

    # Título
    title = QLabel("🔍 Detección de Duplicados")
    title.setStyleSheet("font-size:18px; font-weight:600; color:#223; margin-bottom:6px;")
    layout.addWidget(title)

    panel = QGroupBox()
    panel.setFlat(True)
    panel_layout = QVBoxLayout(panel)
    panel_layout.setSpacing(10)
    panel_layout.setContentsMargins(12, 12, 12, 12)
    window.duplicate_mode_group = QButtonGroup()

    # ---- Opción Exactos ----
    exact_block = QFrame()
    exact_block.setStyleSheet(
        "QFrame {background:#f5f8fc; border-radius:8px; border: 1px solid #dbe7f3;}"
    )
    exact_layout = QVBoxLayout(exact_block)
    exact_layout.setContentsMargins(10, 8, 10, 8)
    window.exact_mode_radio = QRadioButton("⚡ Exactos (SHA256)")
    window.exact_mode_radio.setChecked(True)
    window.duplicate_mode_group.addButton(window.exact_mode_radio, 0)
    exact_layout.addWidget(window.exact_mode_radio)
    window.exact_info = QLabel("100% idénticos bit a bit.<br><b>Rápido</b> y seguro.")
    window.exact_info.setStyleSheet("margin-left:6px; color:#406283; font-size:13px; margin-bottom:2px;")
    window.exact_info.setWordWrap(True)
    exact_layout.addWidget(window.exact_info)
    panel_layout.addWidget(exact_block)

    # ---- Opción Similares ----
    similar_block = QFrame()
    similar_block.setStyleSheet(
        "QFrame {background:#f4fcf7; border-radius:8px; border: 1px solid #cbead6;}"
    )
    similar_layout = QVBoxLayout(similar_block)
    similar_layout.setContentsMargins(10, 8, 10, 8)
    window.similar_mode_radio = QRadioButton("🎨 Similares (Perceptual)")
    window.duplicate_mode_group.addButton(window.similar_mode_radio, 1)
    similar_layout.addWidget(window.similar_mode_radio)
    window.similar_info = QLabel(
        "Visualmente idénticos o muy parecidos.<br>"
        "<b>Permite encontrar copias redimensionadas o recomprimidas</b>, requiere revisión manual."
    )
    window.similar_info.setStyleSheet("margin-left:6px; color:#2e7650; font-size:13px; margin-bottom:2px;")
    window.similar_info.setWordWrap(True)
    similar_layout.addWidget(window.similar_info)

    # Slider y etiquetas siempre pegados (NUNCA stretch en medio)
    slider_row = QHBoxLayout()
    slider_row.setSpacing(8)
    slider_row.setContentsMargins(0,0,0,0)
    window.sens_low_lbl = QLabel("Baja")
    window.sens_low_lbl.setStyleSheet("color:#38845e; font-size:13px; margin-right:4px;")
    window.sensitivity_slider = QSlider(Qt.Horizontal)
    window.sensitivity_slider.setRange(0, 20)
    window.sensitivity_slider.setValue(10)
    window.sensitivity_slider.setFixedWidth(150)
    window.sensitivity_slider.setStyleSheet(
        "QSlider::groove:horizontal { height:6px; background:#b6e1c6; border-radius: 3px;} "
        "QSlider::handle:horizontal { background: #2e7650; border-radius:6px; width:18px;}"
    )
    window.sens_high_lbl = QLabel("Alta")
    window.sens_high_lbl.setStyleSheet("color:#38845e; font-size:13px; margin-left:4px;")
    window.sens_value_lbl = QLabel(f"Sensibilidad: {window.sensitivity_slider.value()}")
    window.sens_value_lbl.setStyleSheet("color:#277248; font-size:13px; margin-left:16px;")

    slider_row.addWidget(window.sens_low_lbl)
    slider_row.addWidget(window.sensitivity_slider)
    slider_row.addWidget(window.sens_high_lbl)
    slider_row.addWidget(window.sens_value_lbl)
    similar_layout.addLayout(slider_row)
    panel_layout.addWidget(similar_block)

    # Visibilidad/estado: el slider y etiquetas SIEMPRE en el layout, solo visibles en modo Similares
    def update_mode():
        ex = window.exact_mode_radio.isChecked()
        window.exact_info.setVisible(ex)
        window.similar_info.setVisible(not ex)
        visible = window.similar_mode_radio.isChecked()
        window.sensitivity_slider.setVisible(visible)
        window.sens_low_lbl.setVisible(visible)
        window.sens_high_lbl.setVisible(visible)
        window.sens_value_lbl.setVisible(visible)
    window.exact_mode_radio.toggled.connect(update_mode)
    window.similar_mode_radio.toggled.connect(update_mode)
    window.sensitivity_slider.valueChanged.connect(
        lambda v: window.sens_value_lbl.setText(f"Sensibilidad: {v}")
    )
    # Force initial mode update after setting defaults
    QTimer.singleShot(0, update_mode)

    layout.addWidget(panel)

    # Resultados del análisis
    results_group = QGroupBox("Resultados")
    results_layout = QVBoxLayout(results_group)
    window.duplicates_results_label = QLabel(
        "<span style='color:#888;'>Haz clic en <b>Analizar Duplicados</b> para comenzar.</span>"
    )
    window.duplicates_results_label.setWordWrap(True)
    window.duplicates_results_label.setStyleSheet("margin-top:2px; font-size:13px; background:none; border:none;")
    results_layout.addWidget(window.duplicates_results_label)
    layout.addWidget(results_group)

    layout.addStretch(1)

    btns = QHBoxLayout()
    window.analyze_duplicates_btn = QPushButton("🔍 Analizar Duplicados")
    window.analyze_duplicates_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    btns.addWidget(window.analyze_duplicates_btn)
    window.delete_exact_duplicates_btn = QPushButton("⚡ Eliminar Exactos")
    window.delete_exact_duplicates_btn.setVisible(False)
    btns.addWidget(window.delete_exact_duplicates_btn)
    window.review_similar_btn = QPushButton("🔍 Revisar Similares")
    window.review_similar_btn.setVisible(False)
    btns.addWidget(window.review_similar_btn)
    layout.addLayout(btns)

    window.analyze_duplicates_btn.clicked.connect(window.on_analyze_duplicates)
    window.delete_exact_duplicates_btn.clicked.connect(window.on_delete_exact_duplicates)
    window.review_similar_btn.clicked.connect(window.on_review_similar_duplicates)

    return tab


def _on_duplicate_mode_changed(window):
    """Maneja cambio en el modo de detección de duplicados"""
    is_similar_mode = window.similar_mode_radio.isChecked()
    # Algunos cambios en nombres de widgets en el módulo original usan
    # `sensitivity_container` y `sensitivity_value_label`; esta función
    # intenta mantener compatibilidad mínima con el resto de la app.
    try:
        window.sensitivity_container.setVisible(is_similar_mode)
    except Exception:
        pass

    # Ocultar botones de acción al cambiar de modo
    window.delete_exact_duplicates_btn.setVisible(False)
    window.review_similar_btn.setVisible(False)

    # Limpiar resultados previos
    window.duplicates_results_label.setText(
        "📂 Haz clic en 'Analizar' para comenzar la detección"
    )
    window.duplicate_analysis_results = None


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
    try:
        window.sensitivity_value_label.setText(f"Valor: {value} ({desc})")
    except Exception:
        # Mantener compatibilidad si no existe ese label
        try:
            window.sens_value_lbl.setText(f"Sensibilidad: {value} ({desc})")
        except Exception:
            pass
