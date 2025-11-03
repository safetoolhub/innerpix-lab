"""
SmartStatsBar - Barra expandible con estadísticas del análisis.

Componente que muestra estadísticas organizadas en 3 columnas:
- Columna 1: REDUNDANCIAS (Live Photos, HEIC)
- Columna 2: DUPLICADOS (Exactos, Similares)
- Columna 3: ORGANIZACIÓN (Renombrar, Organizar)
"""
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QFrame, QSizePolicy, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from utils.icons import icon_manager


def apply_stat_state(widget, state: str, key: str):
    """Aplica estilos visuales según el estado del stat.
    
    Args:
        widget: Widget del stat item
        state: 'detected', 'clean', 'not-analyzed'
        key: Clave del stat (para el objectName)
    """
    if state == 'detected':
        widget.setStyleSheet(
            f"QFrame#stat_{key} {{"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fef3c7, stop:1 #fde68a);"
            "  border: 1px solid #fbbf24;"
            "  border-radius: 6px;"
            "  padding: 6px 8px;"
            "}"
            f"QFrame#stat_{key}:hover {{"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fde68a, stop:1 #fcd34d);"
            "  border-color: #f59e0b;"
            "}"
        )
    elif state == 'clean':
        widget.setStyleSheet(
            f"QFrame#stat_{key} {{"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #d1fae5, stop:1 #a7f3d0);"
            "  border: 1px solid #6ee7b7;"
            "  border-radius: 6px;"
            "  padding: 6px 8px;"
            "}"
            f"QFrame#stat_{key}:hover {{"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a7f3d0, stop:1 #6ee7b7);"
            "  border-color: #34d399;"
            "}"
        )
    else:
        widget.setStyleSheet(
            f"QFrame#stat_{key} {{"
            "  background: #f8f9fa;"
            "  border: 1px solid #dee2e6;"
            "  border-radius: 6px;"
            "  padding: 6px 8px;"
            "}"
            f"QFrame#stat_{key}:hover {{"
            "  background: #e9ecef;"
            "}"
        )


class SmartStatsBar(QFrame):
    """Barra de Smart Stats con grid 3×2."""
    
    stat_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.smart_stats = {}
        self._init_ui()
    
    def _init_ui(self):
        """Inicializa la interfaz"""
        self.setStyleSheet(
            "QFrame {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 #fafbfc, stop:1 #ffffff);"
            "  border-top: 1px solid #e1e8ed;"
            "  border-bottom: 1px solid #cbd5e0;"
            "}"
        )
        self.setMinimumHeight(0)
        self.setMaximumHeight(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setVisible(False)
        
        layout = QHBoxLayout(self)
        # Añadir un poco más de margen inferior para evitar recorte visual
        layout.setContentsMargins(16, 8, 16, 12)
        layout.setSpacing(20)
        
        self.redundancies_column = self._create_stat_column(
            title="REDUNDANCIAS",
            stats_keys=['live_photos', 'heic']
        )
        layout.addWidget(self.redundancies_column, 1)
        
        vsep1 = self._create_separator()
        layout.addWidget(vsep1)
        
        self.duplicates_column = self._create_stat_column(
            title="DUPLICADOS",
            stats_keys=['duplicates_exact', 'duplicates_similar']
        )
        layout.addWidget(self.duplicates_column, 1)
        
        vsep2 = self._create_separator()
        layout.addWidget(vsep2)
        
        self.organization_column = self._create_stat_column(
            title="ORGANIZACIÓN",
            stats_keys=['renaming', 'organization']
        )
        layout.addWidget(self.organization_column, 1)
        
        self._initialize_stats_placeholders()
    
    def _create_separator(self):
        """Crea un separador vertical con gradiente sutil"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(
            "QFrame {"
            "  border: none;"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "    stop:0 transparent, "
            "    stop:0.2 rgba(120, 113, 108, 0.15), "
            "    stop:0.8 rgba(120, 113, 108, 0.15), "
            "    stop:1 transparent);"
            "  width: 1px;"
            "  margin: 0px 20px;"
            "}"
        )
        return separator
    
    def _create_stat_column(self, title: str, stats_keys: list):
        """Crea una columna de stats con un título y varios items"""
        column = QFrame()
        column.setStyleSheet("background: transparent; border: none;")
        
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "color: #64748b; "
            "font-size: 10px; "
            "font-weight: 600; "
            "letter-spacing: 0.05em; "
            "background: transparent; "
            "padding: 0px; "
            "margin-bottom: 0px;"
        )
        layout.addWidget(title_label)
        
        stats_container = QVBoxLayout()
        stats_container.setSpacing(6)
        
        for key in stats_keys:
            stat_widget = self._create_stat_item(key)
            self.smart_stats[key] = stat_widget
            stats_container.addWidget(stat_widget)
        
        layout.addLayout(stats_container)
        layout.addStretch()
        
        return column
    
    def _create_stat_item(self, key: str):
        """Crea un item de stat individual (clickeable)"""
        widget = QFrame()
        widget.setObjectName(f"stat_{key}")
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setFixedHeight(36)
        
        widget.setStyleSheet(
            "QFrame#stat_" + key + " {"
            "  background: #f8f9fa;"
            "  border: 1px solid #dee2e6;"
            "  border-radius: 6px;"
            "  padding: 6px 8px;"
            "}"
            "QFrame#stat_" + key + ":hover {"
            "  background: #e9ecef;"
            "}"
        )
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        icon_btn = QToolButton()
        icon_btn.setAutoRaise(True)
        icon_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        icon_btn.setFixedSize(QSize(16, 16))
        icon_btn.setIconSize(QSize(16, 16))
        icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_btn.setStyleSheet(
            "QToolButton { background: transparent; border: none; padding: 0px; margin: 0px; }"
        )
        icon_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(icon_btn)
        
        text_label = QLabel()
        text_label.setStyleSheet(
            "color: #64748b; "
            "font-size: 12px; "
            "font-weight: 400; "
            "background: transparent; "
            "border: none;"
        )
        text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(text_label, 1)
        
        value_label = QLabel()
        value_label.setStyleSheet(
            "color: #64748b; "
            "font-size: 12px; "
            "font-weight: 600; "
            "background: transparent; "
            "border: none;"
        )
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(value_label)
        
        widget.icon_label = icon_btn
        widget.text_label = text_label
        widget.value_label = value_label
        widget.stat_key = key

        widget.mousePressEvent = lambda event: self.stat_clicked.emit(key)

        return widget
    
    def _initialize_stats_placeholders(self):
        """Inicializa los stats con valores placeholder"""
        if 'live_photos' in self.smart_stats:
            widget = self.smart_stats['live_photos']
            icon_manager.set_button_icon(widget.icon_label, 'live-photo', color='#64748b', size=16)
            widget.text_label.setText("Live Photos")
            widget.value_label.setText("—")
            widget.setToolTip("Detecta pares de Live Photos (foto + video MOV)")
        
        if 'heic' in self.smart_stats:
            widget = self.smart_stats['heic']
            icon_manager.set_button_icon(widget.icon_label, 'heic', color='#64748b', size=16)
            widget.text_label.setText("HEIC Duplicados")
            widget.value_label.setText("—")
            widget.setToolTip("Duplicados HEIC con equivalente JPG")
        
        if 'duplicates_exact' in self.smart_stats:
            widget = self.smart_stats['duplicates_exact']
            icon_manager.set_button_icon(widget.icon_label, 'duplicate-exact', color='#64748b', size=16)
            widget.text_label.setText("Exactos")
            widget.value_label.setText("—")
            widget.setToolTip("Archivos duplicados por hash (contenido idéntico)")
        
        if 'duplicates_similar' in self.smart_stats:
            widget = self.smart_stats['duplicates_similar']
            icon_manager.set_button_icon(widget.icon_label, 'eye', color='#64748b', size=16)
            widget.text_label.setText("Similares")
            widget.value_label.setText("—")
            widget.setToolTip("Duplicados similares (requiere análisis manual)")
        
        if 'renaming' in self.smart_stats:
            widget = self.smart_stats['renaming']
            icon_manager.set_button_icon(widget.icon_label, 'rename', color='#64748b', size=16)
            widget.text_label.setText("Renombrar")
            widget.value_label.setText("—")
            widget.setToolTip("Archivos que necesitan renombrado normalizado")
        
        if 'organization' in self.smart_stats:
            widget = self.smart_stats['organization']
            icon_manager.set_button_icon(widget.icon_label, 'organize', color='#64748b', size=16)
            widget.text_label.setText("Organizar")
            widget.value_label.setText("—")
            widget.setToolTip("Archivos que pueden organizarse por fecha/carpeta")
    
    def clear_stats(self):
        """Reinicializa los stats con placeholders"""
        self._initialize_stats_placeholders()
    
    def update_stats(self, results):
        """Actualiza los Smart Stats con datos del análisis"""
        stats = results.get('stats', {})
        ren = results.get('renaming')
        lp = results.get('live_photos', {})
        org = results.get('organization')
        heic = results.get('heic')
        dup = results.get('duplicates')
        
        lp_count = lp.get('live_photos_found', 0) if isinstance(lp, dict) else (lp.live_photos_found if lp else 0)
        if 'live_photos' in self.smart_stats:
            widget = self.smart_stats['live_photos']
            if lp_count > 0:
                apply_stat_state(widget, 'detected', 'live_photos')
                icon_manager.set_button_icon(widget.icon_label, 'live-photo', color='#eab308', size=16)
                widget.value_label.setText(str(lp_count))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'live_photos')
                icon_manager.set_button_icon(widget.icon_label, 'live-photo', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Live Photos detectados: {lp_count:,}")
        
        heic_count = heic.total_duplicates if heic else 0
        if 'heic' in self.smart_stats:
            widget = self.smart_stats['heic']
            if heic_count > 0:
                apply_stat_state(widget, 'detected', 'heic')
                icon_manager.set_button_icon(widget.icon_label, 'heic', color='#eab308', size=16)
                widget.value_label.setText(str(heic_count))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'heic')
                icon_manager.set_button_icon(widget.icon_label, 'heic', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Archivos HEIC con duplicado JPG: {heic_count:,}")
        
        dup_exact = dup.total_exact_duplicates if (dup and hasattr(dup, 'total_exact_duplicates')) else 0
        if 'duplicates_exact' in self.smart_stats:
            widget = self.smart_stats['duplicates_exact']
            if dup_exact > 0:
                apply_stat_state(widget, 'detected', 'duplicates_exact')
                icon_manager.set_button_icon(widget.icon_label, 'duplicate-exact', color='#eab308', size=16)
                widget.value_label.setText(str(dup_exact))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'duplicates_exact')
                icon_manager.set_button_icon(widget.icon_label, 'duplicate-exact', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Duplicados exactos por hash: {dup_exact:,}")
        
        if 'duplicates_similar' in self.smart_stats:
            widget = self.smart_stats['duplicates_similar']
            apply_stat_state(widget, 'not-analyzed', 'duplicates_similar')
            icon_manager.set_button_icon(widget.icon_label, 'eye', color='#64748b', size=16)
            widget.value_label.setText("—")
            widget.value_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 400;")
            widget.setToolTip("Duplicados similares (requiere análisis manual)")
        
        ren_count = ren.need_renaming if ren else 0
        if 'renaming' in self.smart_stats:
            widget = self.smart_stats['renaming']
            if ren_count > 0:
                apply_stat_state(widget, 'detected', 'renaming')
                icon_manager.set_button_icon(widget.icon_label, 'rename', color='#eab308', size=16)
                widget.value_label.setText(str(ren_count))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'renaming')
                icon_manager.set_button_icon(widget.icon_label, 'rename', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Archivos que necesitan renombrado: {ren_count:,}")
        
        org_count = org.total_files_to_move if org else 0
        if 'organization' in self.smart_stats:
            widget = self.smart_stats['organization']
            if org_count > 0:
                apply_stat_state(widget, 'detected', 'organization')
                icon_manager.set_button_icon(widget.icon_label, 'organize', color='#eab308', size=16)
                widget.value_label.setText(str(org_count))
                widget.value_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: 600;")
            else:
                apply_stat_state(widget, 'clean', 'organization')
                icon_manager.set_button_icon(widget.icon_label, 'organize', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet("color: #10b981; font-size: 12px; font-weight: 600;")
            widget.text_label.setStyleSheet("color: #334155; font-size: 12px; font-weight: 400;")
            widget.setToolTip(f"Archivos que pueden organizarse: {org_count:,}")
