"""
Funciones auxiliares reutilizables para la UI extraídas de `main_window.py`.
Cada función recibe la instancia principal `window` cuando necesita acceder a
atributos o widgets de la ventana.
"""
from pathlib import Path
import traceback

from PyQt5.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
    QTabWidget, QWidget, QTextEdit, QGroupBox, QProgressBar, QLineEdit, QButtonGroup,
    QRadioButton
)
from PyQt5.QtCore import Qt, QTimer

import config
from ui import styles


def _service_available(window, attr_name: str) -> bool:
    return hasattr(window, attr_name) and getattr(window, attr_name) is not None


def create_summary_panel(window):
    """Crea el panel lateral de resumen y asigna widgets relevantes a `window`.
    Devuelve el widget panel (QFrame).
    """
    panel = QFrame()
    panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
    panel.setStyleSheet(styles.STYLE_SUMMARY_PANEL)
    panel.setMaximumWidth(360)

    layout = QVBoxLayout(panel)
    layout.setSpacing(8)
    layout.setContentsMargins(8, 8, 8, 8)

    title = QLabel("📊 RESUMEN")
    title.setStyleSheet(styles.STYLE_SUMMARY_TITLE)
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)

    info_card = QFrame()
    info_card.setStyleSheet(
        "background: linear-gradient(#ffffff, #fbfdff);"
        "border: 1px solid #e6eef6; border-radius: 10px;"
        "padding: 10px;"
    )
    info_layout = QVBoxLayout(info_card)
    info_layout.setSpacing(8)
    info_layout.setContentsMargins(8, 8, 8, 8)

    stats_top_row = QHBoxLayout()
    stats_top_row.setSpacing(8)

    window.stats_labels = {
        'images': QLabel("🖼️ —"),
        'videos': QLabel("🎥 —"),
        'total': QLabel("📊 —")
    }

    chip_style = (
        "background: #ffffff;"
        "border: 1px solid #e1eef9;"
        "border-radius: 8px;"
        "padding: 6px 10px;"
        "color: #1f2d3d;"
    )

    for key in ['images', 'videos']:
        chip = QLabel(window.stats_labels[key].text())
        chip.setAlignment(Qt.AlignCenter)
        chip.setStyleSheet(chip_style)
        chip.setContentsMargins(6, 4, 6, 4)
        stats_top_row.addWidget(chip)
        window.stats_labels[key] = chip

    info_layout.addLayout(stats_top_row)

    stats_bottom_row = QHBoxLayout()
    stats_bottom_row.setSpacing(8)
    total_chip = QLabel(window.stats_labels['total'].text())
    total_chip.setAlignment(Qt.AlignCenter)
    total_chip.setStyleSheet(
        "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f0f8ff, stop:1 #e6f2ff);"
        "border: 1px solid #cfe8ff; border-radius: 8px; padding: 8px 10px; font-weight: 600; color: #0b3b66;"
    )
    total_chip.setContentsMargins(6, 6, 6, 6)
    stats_bottom_row.addWidget(total_chip)
    window.stats_labels['total'] = total_chip

    info_layout.addLayout(stats_bottom_row)
    layout.addWidget(info_card)

    actions_card = QFrame()
    actions_card.setStyleSheet("background: transparent;")
    actions_layout = QVBoxLayout(actions_card)
    actions_layout.setSpacing(6)
    actions_layout.setContentsMargins(0, 0, 0, 0)

    actions_title = QLabel("⚙️ Funcionalidades disponibles")
    actions_title.setStyleSheet("font-weight: bold; color: #2c3e50;")
    actions_layout.addWidget(actions_title)

    window.summary_action_buttons = {}
    stack_layout = QVBoxLayout()
    stack_layout.setSpacing(6)

    def make_full_btn(key, emoji, label_text):
        btn = QPushButton(f"{emoji} {label_text}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(36)
        btn.setStyleSheet(styles.STYLE_SUMMARY_ACTION_BUTTON + "QPushButton { text-align: left; padding-left: 12px; }")
        btn.clicked.connect(lambda: open_summary_action(window, label_text))
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        window.summary_action_buttons[key] = btn
        return btn

    if _service_available(window, 'live_photo_detector'):
        stack_layout.addWidget(make_full_btn('live_photos', '📱', 'Live Photos'))
    if _service_available(window, 'heic_remover'):
        stack_layout.addWidget(make_full_btn('heic', '🖼️', 'Duplicados HEIC'))
    if _service_available(window, 'directory_unifier'):
        stack_layout.addWidget(make_full_btn('unification', '📁', 'Unificar Directorios'))
    if _service_available(window, 'renamer'):
        stack_layout.addWidget(make_full_btn('renaming', '📝', 'Renombrado'))

    actions_layout.addLayout(stack_layout)

    tasks_brief = QFrame()
    tasks_layout = QVBoxLayout(tasks_brief)
    tasks_layout.setSpacing(4)
    tasks_layout.setContentsMargins(0, 6, 0, 0)

    actions_layout.addWidget(tasks_brief)
    layout.addWidget(actions_card)

    layout.addStretch()
    panel.setVisible(False)
    return panel


def create_tabs_widget(window):
    tabs = QTabWidget()
    tabs.setStyleSheet(styles.STYLE_TAB_WIDGET)
    tabs.setVisible(False)
    window.tab_index_map = {}
    idx = 0
    if _service_available(window, 'live_photo_detector'):
        tabs.addTab(create_live_photos_tab(window), "(1) 📱 Live Photos")
        window.tab_index_map['live_photos'] = idx
        idx += 1
    if _service_available(window, 'heic_remover'):
        tabs.addTab(create_heic_tab(window), "(2) 🖼️ Duplicados HEIC")
        window.tab_index_map['heic'] = idx
        idx += 1
    if _service_available(window, 'directory_unifier'):
        tabs.addTab(create_unification_tab(window), "(3) 📁 Unificar Directorios")
        window.tab_index_map['unification'] = idx
        idx += 1
    if _service_available(window, 'renamer'):
        tabs.addTab(create_renaming_tab(window), "(4) 📝 Renombrado")
        window.tab_index_map['renaming'] = idx
        idx += 1
    
    # Tab 5: Duplicados. TODO: ponerle misma estructura que las otras
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
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QLabel, QGroupBox, QRadioButton, QHBoxLayout,
        QButtonGroup, QPushButton, QSlider, QSizePolicy, QFrame
    )
    from PyQt5.QtCore import Qt

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
    window.sensitivity_container.setVisible(is_similar_mode)
    
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
    
    # Buscar descripción más cercana
    closest = min(descriptions.keys(), key=lambda x: abs(x - value))
    desc = descriptions.get(value, descriptions[closest])
    
    window.sensitivity_value_label.setText(f"Valor: {value} ({desc})")



def create_progress_bar(window, parent_layout):
    window.progress_group = QGroupBox("📊 Progreso")
    progress_layout = QVBoxLayout(window.progress_group)

    window.progress_label = QLabel("Listo para procesar")
    window.progress_label.setStyleSheet(styles.STYLE_PROGRESS_LABEL)
    progress_layout.addWidget(window.progress_label)

    window.progress_bar = QProgressBar()
    window.progress_bar.setStyleSheet(styles.STYLE_PROGRESS_BAR)
    progress_layout.addWidget(window.progress_bar)

    window.progress_group.setVisible(False)
    parent_layout.addWidget(window.progress_group)


def update_summary_panel(window, results):
    stats = results.get('stats', {})
    images_txt = f"🖼️ Imágenes: {stats.get('images', 0):,}"
    videos_txt = f"🎥 Videos: {stats.get('videos', 0):,}"
    total_txt = f"📊 Total: {stats.get('total', 0):,}"
    try:
        if 'images' in window.stats_labels:
            window.stats_labels['images'].setText(images_txt)
        if 'videos' in window.stats_labels:
            window.stats_labels['videos'].setText(videos_txt)
        if 'total' in window.stats_labels:
            window.stats_labels['total'].setText(total_txt)
    except Exception:
        pass

    ren = results.get('renaming', {})
    lp = results.get('live_photos', {})
    unif = results.get('unification', {})
    heic = results.get('heic', {})

    if hasattr(window, 'summary_action_buttons'):
        if 'live_photos' in window.summary_action_buttons:
            window.summary_action_buttons['live_photos'].setText(f"📱 Live Photos   {lp.get('live_photos_found', 0):,}")
        if 'heic' in window.summary_action_buttons:
            window.summary_action_buttons['heic'].setText(f"🖼️ Duplicados HEIC   {heic.get('total_duplicates', 0):,}")
        if 'unification' in window.summary_action_buttons:
            window.summary_action_buttons['unification'].setText(f"📁 Unificar Directorios   {unif.get('total_files_to_move', 0):,}")
        if 'renaming' in window.summary_action_buttons:
            window.summary_action_buttons['renaming'].setText(f"📝 Renombrado   {ren.get('need_renaming', 0):,}")


def update_tab_details(window, results):
    if results.get('renaming'):
        ren = results['renaming']
        html = f"""
                <p><strong>Total archivos:</strong> {ren.get('total_files', 0):,}</p>
                <p><strong>✅ Ya renombrados:</strong> {ren.get('already_renamed', 0):,}</p>
                <p><strong>📝 A renombrar:</strong> {ren.get('need_renaming', 0):,}</p>
                <p><strong>⚠️ No procesables:</strong> {ren.get('cannot_process', 0):,}</p>
                <p><strong>🔄 Conflictos:</strong> {ren.get('conflicts', 0):,}</p>
            """
        if ren.get('need_renaming', 0) > 0:
            info_html = f"""
                    <div style='margin-top:10px; padding:10px; border-radius:8px; background:#f8f9fa; color:#6c757d;'>
                        <strong>Información:</strong>
                        <div>Al aceptar el diálogo de preview se ejecutará el renombrado automáticamente.</div>
                        <div>Marca la opción de backup en el diálogo si deseas crear una copia antes de renombrar.</div>
                    </div>
                """
            html += info_html
        window.rename_details.setHtml(html)

    if results.get('live_photos'):
        lp = results['live_photos']
        total_groups = len(lp.get('groups', []))
        total_space = sum(group.get('total_size', 0) for group in lp.get('groups', []))
        space_to_free = sum(group.get('video_size', 0) for group in lp.get('groups', []))
        html = f"""
                <p><strong>📱 Live Photos encontrados:</strong> {total_groups:,}</p>
                <p><strong>💾 Espacio total:</strong> {format_size(total_space)}</p>
                <p><strong>💾 Espacio a liberar (mantener imagen):</strong> {format_size(space_to_free)}</p>
            """
        window.lp_details.setHtml(html)

    if results.get('unification'):
        unif = results['unification']
        total_size = unif.get('total_size_to_move', 0)
        html = f"""
                <p><strong>📁 Subdirectorios:</strong> {len(unif.get('subdirectories', {})):,}</p>
                <p><strong>📄 Archivos a mover:</strong> {unif.get('total_files_to_move', 0):,}</p>
                <p><strong>💾 Tamaño total:</strong> {format_size(total_size)}</p>
                <p><strong>⚠️ Conflictos potenciales:</strong> {unif.get('potential_conflicts', 0):,}</p>
            """
        window.unif_details.setHtml(html)

    if results.get('heic'):
        heic = results['heic']
        savings_jpg = heic.get('potential_savings_keep_jpg', 0)
        savings_heic = heic.get('potential_savings_keep_heic', 0)
        html = f"""
                <p><strong>♻️ Pares detectados:</strong> {heic.get('total_duplicates', 0):,}</p>
                <p><strong>🖼️ Archivos HEIC:</strong> {heic.get('total_heic_files', 0):,}</p>
                <p><strong>📸 Archivos JPG:</strong> {heic.get('total_jpg_files', 0):,}</p>
                <p><strong>💾 Ahorro (mantener JPG):</strong> {format_size(savings_jpg)}</p>
                <p><strong>💾 Ahorro (mantener HEIC):</strong> {format_size(savings_heic)}</p>
            """
        window.heic_details.setHtml(html)


def get_button_style(window, color):
    return styles.get_button_style(color)


def show_progress(window, maximum, message="Procesando"):
    """Muestra la barra de progreso en modo indeterminado y actualiza la etiqueta.

    El parámetro `maximum` se ignora intencionalmente para operaciones que
    modifican archivos: siempre mostramos un feedback "busy" en lugar de
    porcentajes que pueden ser engañosos o permanecer en 0%.
    """
    try:
        window.progress_group.setVisible(True)
    except Exception:
        # Si la UI no está en estado de mostrar, simplemente no hacer nada
        return

    # Forzar modo indeterminado para dar feedback continuo al usuario
    try:
        window.progress_bar.setMaximum(0)
    except Exception:
        try:
            # intento de fallback leve
            window.progress_bar.setMaximum(100)
            window.progress_bar.setValue(0)
        except Exception:
            pass

    # Actualizar etiqueta siempre con el mensaje proporcionado (incluye estado de backup)
    try:
        window.progress_label.setText(message)
    except Exception:
        pass


def hide_progress(window):
    def _hide():
        try:
            window.progress_bar.setMaximum(100)
            window.progress_bar.setValue(0)
        except Exception:
            pass
        window.progress_group.setVisible(False)

    QTimer.singleShot(1000, _hide)


def show_results_html(window, html: str, show_generic_status: bool = False):
    try:
        if show_generic_status:
            try:
                window.logger.info('Operación completada — revisa el log para detalles')
            except Exception:
                try:
                    window.setWindowTitle(f"{config.config.APP_NAME} — Operación completada")
                except Exception:
                    pass
    except Exception:
        pass


def format_size(bytes_size):
    mb_size = bytes_size / (1024 * 1024)
    if mb_size >= 1024:
        gb_size = mb_size / 1024
        return f"{gb_size:.2f} GB"
    else:
        return f"{mb_size:.1f} MB"


def reset_analysis_ui(window, reinsert_analyze=True):
    window.analyze_btn.setText("🔍 Seleccionar Directorio y Analizar")
    window.analyze_btn.setEnabled(True)

    if hasattr(window, 'reanalyze_btn'):
        window.reanalyze_btn.setVisible(False)
    if hasattr(window, 'change_dir_btn'):
        window.change_dir_btn.setVisible(False)

    if reinsert_analyze:
        try:
            if window.analyze_btn.parent() is None:
                window.actions_layout.addWidget(window.analyze_btn)
            window.analyze_btn.setVisible(True)
        except Exception:
            pass

    window.summary_panel.setVisible(False)
    window.tabs_widget.setVisible(False)

    window.preview_rename_btn.setEnabled(False)
    window.exec_lp_btn.setEnabled(False)
    window.exec_unif_btn.setEnabled(False)
    window.exec_heic_btn.setEnabled(False)

    if hasattr(window, 'rename_details'):
        window.rename_details.clear()
    if hasattr(window, 'norm_details'):
        window.norm_details.clear()
    window.lp_details.clear()
    window.unif_details.clear()
    window.heic_details.clear()

    if hasattr(window, 'directory_edit') and reinsert_analyze:
        window.directory_edit.clear()
        window.directory_edit.setPlaceholderText("Selecciona un directorio para analizar...")

    try:
        if 'images' in window.stats_labels:
            window.stats_labels['images'].setText("🖼️ Imágenes: —")
        if 'videos' in window.stats_labels:
            window.stats_labels['videos'].setText("🎥 Videos: —")
        if 'total' in window.stats_labels:
            window.stats_labels['total'].setText("📊 Total: —")
    except Exception:
        pass

    window.analysis_results = None
    window.last_analyzed_directory = None

    try:
        try:
            window.logger.info("Directorio cambiado: análisis anterior limpiado")
        except Exception:
            try:
                window.setWindowTitle(f"{config.config.APP_NAME} — Análisis limpiado")
            except Exception:
                pass
    except Exception:
        try:
            window.logger.info("Directorio cambiado: análisis anterior limpiado")
        except Exception:
            pass

    window.logger.info("UI reiniciada tras cambio de directorio")
