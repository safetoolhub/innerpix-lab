"""
Funciones auxiliares reutilizables para la UI extraídas de `main_window.py`.
Cada función recibe la instancia principal `window` cuando necesita acceder a
atributos o widgets de la ventana.
"""
from pathlib import Path
import traceback

from PyQt5.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
    QTextEdit, QGroupBox, QProgressBar, QLineEdit, QButtonGroup,
    QRadioButton
)
from PyQt5.QtCore import Qt, QTimer

import config
from ui import styles

try:
    from ui import tabs as _tabs_module
except Exception:
    _tabs_module = None


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
        def _invoke():
            try:
                if _tabs_module:
                    _tabs_module.open_summary_action(window, label_text)
                    return
            except Exception:
                pass
            # Fallback: ensure any existing tabs_widget is shown
            try:
                if hasattr(window, 'tabs_widget') and window.tabs_widget.count() > 0:
                    window.tabs_widget.setCurrentIndex(0)
                    window.tabs_widget.setVisible(True)
            except Exception:
                pass

        btn.clicked.connect(_invoke)
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


# NOTE: tab-creation helpers were moved to `ui.tabs` to improve modularity.
# `main_window` importa `ui.tabs` directamente y `ui_helpers` ya no expone
# esas funciones. Los botones del panel de resumen llaman a `ui.tabs` vía
# el helper `_invoke` definido en `make_full_btn` arriba.



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
    """Formatea un tamaño en bytes a una cadena legible.

    Soporta Bytes, KB, MB y GB. Usa potencias de 1024.
    Maneja valores None o negativos de forma segura.
    """
    try:
        if bytes_size is None:
            return "0 B"
        size = float(bytes_size)
    except Exception:
        return "0 B"

    if size < 0:
        # Mantener el signo y formatear el absoluto
        return f"-{format_size(abs(size))}"

    # Bytes
    if size < 1024:
        return f"{int(size)} B"

    # Kilobytes
    kb = size / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"

    # Megabytes
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f} MB"

    # Gigabytes and above
    gb = mb / 1024
    return f"{gb:.2f} GB"


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
