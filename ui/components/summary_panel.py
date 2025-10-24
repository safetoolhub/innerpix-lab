from pathlib import Path
import traceback

from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
)
from PyQt5.QtCore import Qt

import config
from ui import styles

try:
    from ui import tabs as _tabs_module
except Exception:
    _tabs_module = None

from ui.helpers import service_available


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

    if service_available(window, 'live_photo_detector'):
        stack_layout.addWidget(make_full_btn('live_photos', '📱', 'Live Photos'))
    if service_available(window, 'heic_remover'):
        stack_layout.addWidget(make_full_btn('heic', '🖼️', 'Duplicados HEIC'))
    if service_available(window, 'directory_unifier'):
        stack_layout.addWidget(make_full_btn('unification', '📁', 'Unificar Directorios'))
    if service_available(window, 'renamer'):
        stack_layout.addWidget(make_full_btn('renaming', '📝', 'Renombrado'))
    # Duplicados siempre disponible en la UI actual
    stack_layout.addWidget(make_full_btn('duplicates', '🔍', 'Duplicados'))

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



class SummaryPanel(QWidget):
    """Componente SummaryPanel que encapsula el widget creado por
    `create_summary_panel`.
    """

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.panel = create_summary_panel(window)

    def get_widget(self):
        return self.panel

    def update(self, results):
        update_summary_panel(self.window, results)
