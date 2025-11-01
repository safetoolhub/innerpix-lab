from pathlib import Path
import traceback

from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy,
)
from PyQt6.QtCore import Qt

from config import Config
from ui import styles

# Nota: la disponibilidad real de las pestañas se decide mediante
# `TabController` (accesible como `window.tab_controller`) y
# `update_tabs_availability`.


def create_summary_panel(window):
    """Crea el panel lateral de resumen y asigna widgets relevantes a `window`.
    Devuelve el widget panel (QFrame).
    """
    panel = QFrame()
    panel.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
    panel.setStyleSheet(styles.STYLE_SUMMARY_PANEL)
    panel.setMaximumWidth(360)

    layout = QVBoxLayout(panel)
    layout.setSpacing(8)
    layout.setContentsMargins(8, 8, 8, 8)

    title = QLabel("📊 RESUMEN")
    title.setStyleSheet(styles.STYLE_SUMMARY_TITLE)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(title)

    # Badge de estado del análisis
    status_badge = QLabel("⏸️ Listo para analizar")
    status_badge.setStyleSheet(
        "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e9ecef);"
        "border: 1px solid #dee2e6;"
        "border-radius: 6px;"
        "padding: 6px 12px;"
        "color: #495057;"
        "font-size: 11px;"
        "font-weight: 600;"
    )
    status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(status_badge)
    window.analysis_status_badge = status_badge

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
        chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chip.setStyleSheet(chip_style)
        chip.setContentsMargins(6, 4, 6, 4)
        stats_top_row.addWidget(chip)
        window.stats_labels[key] = chip

    info_layout.addLayout(stats_top_row)

    stats_bottom_row = QHBoxLayout()
    stats_bottom_row.setSpacing(8)
    total_chip = QLabel(window.stats_labels['total'].text())
    total_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
    actions_card.setStyleSheet(styles.STYLE_FRAME_TRANSPARENT)
    actions_layout = QVBoxLayout(actions_card)
    actions_layout.setSpacing(6)
    actions_layout.setContentsMargins(0, 0, 0, 0)

    actions_title = QLabel("⚙️ Herramientas disponibles")
    actions_title.setStyleSheet(styles.STYLE_LABEL_TITLE_DARK)
    actions_layout.addWidget(actions_title)

    window.summary_action_buttons = {}
    stack_layout = QVBoxLayout()
    stack_layout.setSpacing(6)

    def make_full_btn(key, emoji, label_text):
        btn = QPushButton(f"{emoji} {label_text}")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(36)
        btn.setStyleSheet(styles.STYLE_SUMMARY_ACTION_BUTTON + "QPushButton { text-align: left; padding-left: 12px; }")
        def _invoke():
            # Usar TabController centralizado (se asume que existe en la app)
            tc = getattr(window, 'tab_controller', None)
            if tc is None:
                # Si no existe, no hacemos nada (se asumió TabController siempre presente)
                return
            tc.open_summary_action(label_text)

        btn.clicked.connect(_invoke)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        window.summary_action_buttons[key] = btn
        return btn

    # Añadir siempre los botones (la visibilidad/estado real se controlará
    # más tarde mediante el `TabController` y su método
    # `update_tabs_availability`).
    # ORDEN: Live Photos → HEIC → Duplicados → Organizador → Renombrado
    stack_layout.addWidget(make_full_btn('live_photos', '📱', 'Live Photos'))
    stack_layout.addWidget(make_full_btn('heic', '🖼️', 'Limpieza HEIC/JPG'))
    stack_layout.addWidget(make_full_btn('duplicates', '🔍', 'Duplicados'))
    stack_layout.addWidget(make_full_btn('organization', '📁', 'Organizador'))
    stack_layout.addWidget(make_full_btn('renaming', '📝', 'Renombrado'))

    actions_layout.addLayout(stack_layout)

    layout.addWidget(actions_card)

    # ===== ÁREA DE PROGRESO =====
    # Crear un área fija para el progreso debajo de las funcionalidades
    # para evitar desplazamientos verticales del interfaz
    progress_area = QFrame()
    progress_area.setStyleSheet(
        "QFrame {"
        "  background: transparent;"
        "  border: none;"
        "  padding: 0px;"
        "}"
    )
    progress_area.setFixedHeight(90)  # Altura fija para mantener consistencia vertical
    progress_layout = QVBoxLayout(progress_area)
    progress_layout.setSpacing(6)
    progress_layout.setContentsMargins(0, 8, 0, 0)

    # Etiqueta de estado con emoji
    progress_label = QLabel("⏸️ Listo")
    progress_label.setStyleSheet(
        "font-weight: 600; "
        "color: #2c3e50; "
        "font-size: 13px; "
        "background: transparent; "
        "border: none; "
        "padding: 4px 0px;"
    )
    progress_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
    progress_layout.addWidget(progress_label)

    # Barra de progreso estilo moderno sin marco doble
    from PyQt6.QtWidgets import QProgressBar
    progress_bar = QProgressBar()
    progress_bar.setStyleSheet(
        "QProgressBar {"
        "  border: none;"
        "  border-radius: 6px;"
        "  text-align: center;"
        "  background-color: #e9ecef;"
        "  height: 24px;"
        "  font-size: 11px;"
        "  font-weight: 600;"
        "  color: #2c3e50;"
        "}"
        "QProgressBar::chunk {"
        "  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        "    stop:0 #4CAF50, stop:0.5 #66BB6A, stop:1 #81C784);"
        "  border-radius: 6px;"
        "}"
    )
    progress_bar.setMaximum(100)
    progress_bar.setValue(0)
    progress_bar.setTextVisible(True)
    progress_layout.addWidget(progress_bar)

    # Estado adicional (texto pequeño informativo)
    progress_detail = QLabel("")
    progress_detail.setStyleSheet(
        "color: #6c757d; "
        "font-size: 11px; "
        "background: transparent; "
        "border: none; "
        "padding: 2px 0px;"
    )
    progress_detail.setAlignment(Qt.AlignmentFlag.AlignLeft)
    progress_detail.setWordWrap(True)
    progress_layout.addWidget(progress_detail)

    # Añadir stretch para empujar todo hacia arriba
    progress_layout.addStretch()

    # Inicialmente oculto (solo el contenido, el área mantiene espacio)
    progress_label.setVisible(False)
    progress_bar.setVisible(False)
    progress_detail.setVisible(False)

    # Guardar referencias en window para que ProgressController pueda accederlas
    window.summary_progress_area = progress_area
    window.summary_progress_label = progress_label
    window.summary_progress_bar = progress_bar
    window.summary_progress_detail = progress_detail

    layout.addWidget(progress_area)

    layout.addStretch()
    panel.setVisible(False)
    return panel


def _format_time_ago(timestamp_str: str) -> str:
    """Formatea un timestamp ISO en texto 'hace X tiempo'"""
    from datetime import datetime
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        delta = now - timestamp
        
        seconds = delta.total_seconds()
        if seconds < 60:
            return "hace menos de 1 minuto"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"hace {minutes} min"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"hace {hours}h"
        else:
            days = int(seconds / 86400)
            return f"hace {days}d"
    except Exception:
        return "recientemente"


def update_summary_panel(window, results):
    stats = results.get('stats', {})
    images_txt = f"🖼️ Imágenes: {stats.get('images', 0):,}"
    videos_txt = f"🎥 Videos: {stats.get('videos', 0):,}"
    total_txt = f"📊 Total: {stats.get('total', 0):,}"
    
    if 'images' in window.stats_labels:
        window.stats_labels['images'].setText(images_txt)
    if 'videos' in window.stats_labels:
        window.stats_labels['videos'].setText(videos_txt)
    if 'total' in window.stats_labels:
        window.stats_labels['total'].setText(total_txt)
    
    # Actualizar badge de estado del análisis
    if hasattr(window, 'analysis_status_badge'):
        from utils.settings_manager import settings_manager
        timestamp = settings_manager.get_analysis_timestamp()
        if timestamp:
            time_ago = _format_time_ago(timestamp)
            window.analysis_status_badge.setText(f"✓ Analizado {time_ago}")
            window.analysis_status_badge.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d4edda, stop:1 #c3e6cb);"
                "border: 1px solid #c3e6cb;"
                "border-radius: 6px;"
                "padding: 6px 12px;"
                "color: #155724;"
                "font-size: 11px;"
                "font-weight: 600;"
            )
        else:
            window.analysis_status_badge.setText("✓ Análisis completado")
            window.analysis_status_badge.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d4edda, stop:1 #c3e6cb);"
                "border: 1px solid #c3e6cb;"
                "border-radius: 6px;"
                "padding: 6px 12px;"
                "color: #155724;"
                "font-size: 11px;"
                "font-weight: 600;"
            )

    ren = results.get('renaming')  # RenameAnalysisResult (dataclass)
    lp = results.get('live_photos', {})  # Todavía es dict (desde workers.py)
    org = results.get('organization')  # OrganizationAnalysisResult (dataclass)
    heic = results.get('heic')  # HEICAnalysisResult (dataclass) o None
    dup = results.get('duplicates')  # DuplicateAnalysisResult (dataclass) o None

    if hasattr(window, 'summary_action_buttons'):
        if 'live_photos' in window.summary_action_buttons:
            lp_count = lp.get('live_photos_found', 0) if isinstance(lp, dict) else (lp.live_photos_found if lp else 0)
            window.summary_action_buttons['live_photos'].setText(f"📱 Live Photos   {lp_count:,}")
        if 'heic' in window.summary_action_buttons:
            heic_count = heic.total_duplicates if heic else 0
            window.summary_action_buttons['heic'].setText(f"🖼️ Limpieza HEIC/JPG   {heic_count:,}")
        if 'duplicates' in window.summary_action_buttons:
            # Mostrar contador si hay resultados del análisis inicial de duplicados exactos
            if dup is not None:
                dup_count = dup.total_duplicates if hasattr(dup, 'total_duplicates') else 0
                window.summary_action_buttons['duplicates'].setText(f"🔍 Duplicados   {dup_count:,}")
            else:
                # Solo mostrar "Pendiente" si no se ha ejecutado el análisis inicial
                window.summary_action_buttons['duplicates'].setText("🔍 Duplicados   —")
        if 'organization' in window.summary_action_buttons:
            org_count = org.total_files_to_move if org else 0
            window.summary_action_buttons['organization'].setText(f"📁 Organizador   {org_count:,}")
        if 'renaming' in window.summary_action_buttons:
            ren_count = ren.need_renaming if ren else 0
            window.summary_action_buttons['renaming'].setText(f"📝 Renombrado   {ren_count:,}")



def set_analysis_status_not_analyzed(window):
    """Establece el badge de estado a 'No analizado'"""
    if hasattr(window, 'analysis_status_badge'):
        window.analysis_status_badge.setText("⚠️ No analizado")
        window.analysis_status_badge.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff3cd, stop:1 #ffeaa7);"
            "border: 1px solid #ffc107;"
            "border-radius: 6px;"
            "padding: 6px 12px;"
            "color: #856404;"
            "font-size: 11px;"
            "font-weight: 600;"
        )


def set_analysis_status_analyzing(window):
    """Establece el badge de estado a 'Analizando...'"""
    if hasattr(window, 'analysis_status_badge'):
        window.analysis_status_badge.setText("⏳ Analizando...")
        window.analysis_status_badge.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d1ecf1, stop:1 #bee5eb);"
            "border: 1px solid #bee5eb;"
            "border-radius: 6px;"
            "padding: 6px 12px;"
            "color: #0c5460;"
            "font-size: 11px;"
            "font-weight: 600;"
        )


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
    
    def set_status_not_analyzed(self):
        """Establece estado a 'No analizado'"""
        set_analysis_status_not_analyzed(self.window)
    
    def set_status_analyzing(self):
        """Establece estado a 'Analizando...'"""
        set_analysis_status_analyzing(self.window)
