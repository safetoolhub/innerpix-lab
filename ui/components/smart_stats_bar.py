"""
SmartStatsBar - Componente de estadísticas inteligentes para TopBar.

Muestra resumen de análisis en 3 columnas:
- Redundancias: Live Photos, HEIC
- Duplicados: Exactos, Similares
- Organización: Renombrar, Organizar

Sistema de colores:
- Amarillo: Acción requerida (count > 0)
- Verde: Limpio (count == 0)
- Gris: No analizado
"""
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QCursor

from ui import styles
from utils.icons import icon_manager


def apply_stat_state(widget, state: str, key: str):
    """Aplica estilos según el estado del stat (amarillo/verde/gris).
    
    Args:
        widget: El widget QFrame del stat
        state: 'detected' (amarillo), 'clean' (verde), 'not-analyzed' (gris)
        key: Clave del stat para el objectName
    """
    widget.setStyleSheet(styles.get_topbar_stat_style(key, state))


class SmartStatsBar(QFrame):
    """Barra de estadísticas inteligentes con grid 3×2.
    
    Signals:
        stat_clicked: Se emite cuando el usuario hace click en un stat (str: key)
    """
    
    stat_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.smart_stats = {}
        self._init_ui()
    
    def _init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setStyleSheet(styles.STYLE_TOPBAR_SMART_STATS_CONTAINER)
        self.setMinimumHeight(0)
        self.setMaximumHeight(0)  # Inicialmente colapsado
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setVisible(False)
        
        container_layout = QHBoxLayout(self)
        container_layout.setContentsMargins(16, 8, 16, 8)
        container_layout.setSpacing(20)
        
        # === COLUMNA 1: REDUNDANCIAS ===
        self.redundancies_column = self._create_stat_column(
            title="REDUNDANCIAS",
            stats_keys=['live_photos', 'heic']
        )
        container_layout.addWidget(self.redundancies_column, 1)
        
        # Separador vertical
        vsep1 = self._create_separator()
        container_layout.addWidget(vsep1)
        
        # === COLUMNA 2: DUPLICADOS ===
        self.duplicates_column = self._create_stat_column(
            title="DUPLICADOS",
            stats_keys=['duplicates_exact', 'duplicates_similar']
        )
        container_layout.addWidget(self.duplicates_column, 1)
        
        # Separador vertical
        vsep2 = self._create_separator()
        container_layout.addWidget(vsep2)
        
        # === COLUMNA 3: ORGANIZACIÓN ===
        self.organization_column = self._create_stat_column(
            title="ORGANIZACIÓN",
            stats_keys=['renaming', 'organization']
        )
        container_layout.addWidget(self.organization_column, 1)
        
        # Inicializar stats con placeholders
        self._initialize_stats_placeholders()
    
    def _create_separator(self):
        """Crea un separador vertical con gradiente sutil"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(styles.STYLE_TOPBAR_SEPARATOR)
        return separator
    
    def _create_stat_column(self, title: str, stats_keys: list):
        """Crea una columna de stats con un título y varios items"""
        column = QFrame()
        column.setStyleSheet(styles.STYLE_TOPBAR_COLUMN)
        
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Título de la columna
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(styles.STYLE_TOPBAR_COLUMN_TITLE)
        layout.addWidget(title_label)
        
        # Container para los stats
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
        """Crea un item de stat individual (clickeable) con diseño [icono] Label    Número"""
        widget = QFrame()
        widget.setObjectName(f"stat_{key}")
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.setFixedHeight(36)
        
        # Estilo inicial (gris neutral - no analizado)
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
        
        # Icono
        icon_btn = QToolButton()
        icon_btn.setAutoRaise(True)
        icon_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        icon_btn.setFixedSize(QSize(16, 16))
        icon_btn.setIconSize(QSize(16, 16))
        icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_btn.setStyleSheet(styles.STYLE_TOPBAR_STAT_ICON)
        icon_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(icon_btn)
        
        # Label (texto descriptivo)
        text_label = QLabel()
        text_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_TEXT)
        text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(text_label, 1)
        
        # Número (valor del stat)
        value_label = QLabel()
        value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        value_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(value_label)
        
        # Guardar referencias
        widget.icon_label = icon_btn
        widget.text_label = text_label
        widget.value_label = value_label
        widget.stat_key = key

        # Conectar click
        widget.mousePressEvent = lambda event, k=key: self._on_stat_clicked(k)

        return widget
    
    def _on_stat_clicked(self, key: str):
        """Emite señal cuando se hace click en un stat"""
        self.stat_clicked.emit(key)
    
    def _initialize_stats_placeholders(self):
        """Inicializa los stats con valores placeholder"""
        # Columna 1: REDUNDANCIAS
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
        
        # Columna 2: DUPLICADOS
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
        
        # Columna 3: ORGANIZACIÓN
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
    
    def update_stats(self, results):
        """Actualiza los Smart Stats con datos del análisis usando sistema de color amarillo/verde/gris"""
        stats = results.get('stats', {})
        ren = results.get('renaming')
        lp = results.get('live_photos', {})
        org = results.get('organization')
        heic = results.get('heic')
        dup = results.get('duplicates')
        
        # === COLUMNA 1: REDUNDANCIAS ===
        
        # Live Photos
        lp_count = lp.get('live_photos_found', 0) if isinstance(lp, dict) else (lp.live_photos_found if lp else 0)
        if 'live_photos' in self.smart_stats:
            widget = self.smart_stats['live_photos']
            if lp_count > 0:
                apply_stat_state(widget, 'detected', 'live_photos')
                icon_manager.set_button_icon(widget.icon_label, 'live-photo', color='#eab308', size=16)
                widget.value_label.setText(str(lp_count))
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_WARNING)
            else:
                apply_stat_state(widget, 'clean', 'live_photos')
                icon_manager.set_button_icon(widget.icon_label, 'live-photo', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_SUCCESS)
            widget.text_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_TEXT_NORMAL)
            widget.setToolTip(f"Live Photos detectados: {lp_count:,}")
        
        # HEIC Duplicados
        heic_count = heic.total_duplicates if heic else 0
        if 'heic' in self.smart_stats:
            widget = self.smart_stats['heic']
            if heic_count > 0:
                apply_stat_state(widget, 'detected', 'heic')
                icon_manager.set_button_icon(widget.icon_label, 'heic', color='#eab308', size=16)
                widget.value_label.setText(str(heic_count))
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_WARNING)
            else:
                apply_stat_state(widget, 'clean', 'heic')
                icon_manager.set_button_icon(widget.icon_label, 'heic', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_SUCCESS)
            widget.text_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_TEXT_NORMAL)
            widget.setToolTip(f"Archivos HEIC con duplicado JPG: {heic_count:,}")
        
        # === COLUMNA 2: DUPLICADOS ===
        
        # Duplicados Exactos
        dup_exact = dup.total_exact_duplicates if (dup and hasattr(dup, 'total_exact_duplicates')) else 0
        if 'duplicates_exact' in self.smart_stats:
            widget = self.smart_stats['duplicates_exact']
            if dup_exact > 0:
                apply_stat_state(widget, 'detected', 'duplicates_exact')
                icon_manager.set_button_icon(widget.icon_label, 'duplicate-exact', color='#eab308', size=16)
                widget.value_label.setText(str(dup_exact))
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_WARNING)
            else:
                apply_stat_state(widget, 'clean', 'duplicates_exact')
                icon_manager.set_button_icon(widget.icon_label, 'duplicate-exact', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_SUCCESS)
            widget.text_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_TEXT_NORMAL)
            widget.setToolTip(f"Duplicados exactos por hash: {dup_exact:,}")
        
        # Duplicados Similares (no analizado por defecto)
        if 'duplicates_similar' in self.smart_stats:
            widget = self.smart_stats['duplicates_similar']
            apply_stat_state(widget, 'not-analyzed', 'duplicates_similar')
            icon_manager.set_button_icon(widget.icon_label, 'eye', color='#64748b', size=16)
            widget.value_label.setText("—")
            widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_NORMAL)
            widget.text_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_TEXT_MUTED)
            widget.setToolTip("Duplicados similares (requiere análisis manual)")
        
        # === COLUMNA 3: ORGANIZACIÓN ===
        
        # Renombrar
        ren_count = ren.need_renaming if ren else 0
        if 'renaming' in self.smart_stats:
            widget = self.smart_stats['renaming']
            if ren_count > 0:
                apply_stat_state(widget, 'detected', 'renaming')
                icon_manager.set_button_icon(widget.icon_label, 'rename', color='#eab308', size=16)
                widget.value_label.setText(str(ren_count))
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_WARNING)
            else:
                apply_stat_state(widget, 'clean', 'renaming')
                icon_manager.set_button_icon(widget.icon_label, 'rename', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_SUCCESS)
            widget.text_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_TEXT_NORMAL)
            widget.setToolTip(f"Archivos que necesitan renombrado: {ren_count:,}")
        
        # Organizar
        org_count = org.total_files_to_move if org else 0
        if 'organization' in self.smart_stats:
            widget = self.smart_stats['organization']
            if org_count > 0:
                apply_stat_state(widget, 'detected', 'organization')
                icon_manager.set_button_icon(widget.icon_label, 'organize', color='#eab308', size=16)
                widget.value_label.setText(str(org_count))
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_WARNING)
            else:
                apply_stat_state(widget, 'clean', 'organization')
                icon_manager.set_button_icon(widget.icon_label, 'organize', color='#10b981', size=16)
                widget.value_label.setText("✓")
                widget.value_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_VALUE_SUCCESS)
            widget.text_label.setStyleSheet(styles.STYLE_TOPBAR_STAT_TEXT_NORMAL)
            widget.setToolTip(f"Archivos que pueden organizarse: {org_count:,}")
    
    def clear_stats(self):
        """Reinicia stats a valores placeholder"""
        self._initialize_stats_placeholders()
