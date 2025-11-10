from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QGroupBox, QButtonGroup, QRadioButton,
    QCheckBox, QDialogButtonBox, QPushButton,
    QHBoxLayout, QVBoxLayout as QVLayout, QFrame, QTreeWidget, QTreeWidgetItem, QLineEdit,
    QComboBox, QMessageBox, QMenu, QWidget
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices, QColor
from config import Config
from services.exact_copies_detector import DuplicateGroup
from utils.format_utils import format_size
from utils.logger import get_logger
from ui import ui_styles
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from .base_dialog import BaseDialog
from .dialog_utils import show_file_details_dialog
from datetime import datetime


class ExactCopiesDialog(BaseDialog):
    """
    Diálogo para gestionar copias exactas.
    
    Muestra fotos y vídeos idénticos digitalmente (mismo SHA256),
    incluso si tienen nombres diferentes. Permite eliminar duplicados
    con diferentes estrategias de conservación.
    """
    
    # Constantes para paginación
    INITIAL_LOAD = 50
    LOAD_INCREMENT = 50
    WARNING_THRESHOLD = 200
    
    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.logger = get_logger('ExactCopiesDialog')
        self.analysis = analysis
        self.keep_strategy = 'oldest'
        self.accepted_plan = None
        
        # Estado de grupos
        self.all_groups = analysis.groups  # Todos los grupos originales
        self.filtered_groups = analysis.groups  # Grupos después de filtrar
        self.loaded_count = 0  # Cuántos grupos se han cargado en el tree
        
        # Referencias a widgets
        self.tree_widget = None
        self.search_input = None
        self.filter_combo = None
        self.groups_info_label = None
        self.load_more_btn = None
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Gestionar copias exactas")
        self.setModal(True)
        self.resize(1000, 700)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(int(DesignSystem.SPACE_16))
        layout.setContentsMargins(
            int(DesignSystem.SPACE_24),
            int(DesignSystem.SPACE_20),
            int(DesignSystem.SPACE_24),
            int(DesignSystem.SPACE_20)
        )
        
        # Header con icono y explicación
        explanation = self._create_explanation_frame(
            'content-copy',
            'Copias exactas detectadas',
            'Se han detectado archivos idénticos (100% mismo contenido digital SHA256). '
            'Puedes eliminar las copias redundantes conservando un original por grupo.'
        )
        layout.addWidget(explanation)
        
        # Métricas inline
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(int(DesignSystem.SPACE_12))
        
        # Grupos de duplicados
        groups_metric = self._create_metric_card(
            str(self.analysis.total_groups),
            "Grupos de duplicados",
            DesignSystem.COLOR_PRIMARY
        )
        metrics_layout.addWidget(groups_metric)
        
        # Copias a eliminar
        copies_metric = self._create_metric_card(
            str(self.analysis.total_duplicates),
            "Copias redundantes",
            DesignSystem.COLOR_WARNING
        )
        metrics_layout.addWidget(copies_metric)
        
        # Espacio recuperable
        space_metric = self._create_metric_card(
            format_size(self.analysis.space_wasted),
            "Espacio recuperable",
            DesignSystem.COLOR_SUCCESS
        )
        metrics_layout.addWidget(space_metric)
        
        metrics_layout.addStretch()
        layout.addLayout(metrics_layout)
        
        # Selector de estrategia con cards
        strategy_selector = self._create_strategy_selector()
        layout.addWidget(strategy_selector)
        
        # Advertencia si hay muchos grupos
        if len(self.all_groups) > self.WARNING_THRESHOLD:
            warning_many = QLabel(
                f"Hay {len(self.all_groups)} grupos de duplicados. "
                f"Se cargarán inicialmente {self.INITIAL_LOAD} grupos. "
                f"Usa la búsqueda y filtros para encontrar grupos específicos más rápido."
            )
            warning_many.setTextFormat(Qt.TextFormat.RichText)
            warning_many.setWordWrap(True)
            warning_many.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                               stop:0 {DesignSystem.COLOR_BG_1}, 
                                               stop:1 {DesignSystem.COLOR_BG_2});
                    border: none;
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_12}px;
                    color: {DesignSystem.COLOR_TEXT_SECONDARY};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                }}
            """)
            layout.addWidget(warning_many)
        
        # Barra de herramientas (búsqueda, filtros y acciones)
        toolbar_layout = QHBoxLayout()
        
        # Búsqueda
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)
        
        search_icon = QLabel()
        icon_manager.set_label_icon(search_icon, 'search', size=14)
        search_layout.addWidget(search_icon)
        
        search_text = QLabel("Buscar:")
        search_layout.addWidget(search_text)
        
        toolbar_layout.addWidget(search_container)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nombre de archivo o ruta...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: {DesignSystem.SPACE_8}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
            QLineEdit:focus {{
                border-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        toolbar_layout.addWidget(self.search_input, 2)
        
        # Filtro por tamaño
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(4)
        
        filter_icon = QLabel()
        icon_manager.set_label_icon(filter_icon, 'chart-bar', size=14)
        filter_layout.addWidget(filter_icon)
        
        filter_text = QLabel("Filtrar:")
        filter_layout.addWidget(filter_text)
        
        toolbar_layout.addWidget(filter_container)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "Todos los grupos",
            "Solo grupos >10 MB",
            "Solo grupos >50 MB",
            "Solo grupos >100 MB",
            "Solo grupos con 3+ archivos",
            "Solo grupos con 5+ archivos"
        ])
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                padding: {DesignSystem.SPACE_8}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
            }}
        """)
        toolbar_layout.addWidget(self.filter_combo, 1)
        
        # Separador visual
        separator_line = QFrame()
        separator_line.setFrameShape(QFrame.Shape.VLine)
        separator_line.setFrameShadow(QFrame.Shadow.Sunken)
        toolbar_layout.addWidget(separator_line)
        
        # Botón "Mostrar Todos" integrado en la barra
        show_all_btn = QPushButton("Ver Todos")
        icon_manager.set_button_icon(show_all_btn, 'eye', size=16)
        show_all_btn.setToolTip("Cargar y mostrar todos los grupos de duplicados")
        show_all_btn.clicked.connect(self._load_all_groups)
        show_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
        """)
        show_all_btn.setStyleSheet(DesignSystem.get_tooltip_style() + show_all_btn.styleSheet())
        toolbar_layout.addWidget(show_all_btn)
        
        # Información de grupos cargados (inline, sin fondo)
        self.groups_info_label = QLabel()
        self.groups_info_label.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            padding: {DesignSystem.SPACE_6}px;
        """)
        toolbar_layout.addWidget(self.groups_info_label)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Tree widget para mostrar grupos expandibles
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Archivo/Grupo", "Tamaño", "Fecha Modificación", "Ruta", "Estado"])
        self.tree_widget.setColumnWidth(0, 250)
        self.tree_widget.setColumnWidth(1, 100)
        self.tree_widget.setColumnWidth(2, 150)
        self.tree_widget.setColumnWidth(3, 300)
        self.tree_widget.setColumnWidth(4, 100)
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                background-color: {DesignSystem.COLOR_SURFACE};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
            QTreeWidget::item {{
                padding: {DesignSystem.SPACE_6}px;
            }}
            QTreeWidget::item:hover {{
                background-color: {DesignSystem.COLOR_BG_2};
            }}
            QTreeWidget::item:selected {{
                background-color: {DesignSystem.COLOR_SECONDARY};
            }}
        """)
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tree_widget)
        
        # Botón de paginación (solo "Cargar Más")
        pagination_layout = QHBoxLayout()
        
        self.load_more_btn = QPushButton(f"Cargar {self.LOAD_INCREMENT} Más Grupos")
        icon_manager.set_button_icon(self.load_more_btn, 'down', size=16)
        self.load_more_btn.clicked.connect(self._load_more_groups)
        self.load_more_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SECONDARY};
                color: {DesignSystem.COLOR_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_16}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_SECONDARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_BORDER};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """)
        pagination_layout.addWidget(self.load_more_btn)
        
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)
        
        # Cargar grupos iniciales
        self._load_initial_groups()
        
        # Opciones de seguridad
        options_group = QGroupBox("Opciones de Seguridad")
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet(f"QGroupBox {{ font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; padding-top: {DesignSystem.SPACE_12}px; }}")
        options_layout = QVLayout(options_group)
        options_layout.setContentsMargins(
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_8),
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_8)
        )
        options_layout.setSpacing(int(DesignSystem.SPACE_8))
        
        # Backup checkbox (primero)
        self.add_backup_checkbox(options_layout, "Crear backup antes de eliminar (Recomendado)")
        
        # Simulación checkbox (segundo)
        self.dry_run_checkbox = QCheckBox("Modo simulación (no eliminar archivos realmente)")
        # Leer configuración para establecer estado por defecto
        from utils.settings_manager import settings_manager
        dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, False)
        # Asegurar que es un booleano
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() in ('true', '1', 'yes')
        self.dry_run_checkbox.setChecked(bool(dry_run_default))
        options_layout.addWidget(self.dry_run_checkbox)
        layout.addWidget(options_group)

        # Botones
        buttons = self.make_ok_cancel_buttons(ok_text="Eliminar Ahora")
        # apply danger style to ok button
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        icon_manager.set_button_icon(ok_btn, 'delete', size=16)
        ok_btn.setStyleSheet(ui_styles.STYLE_DANGER_BUTTON)
        layout.addWidget(buttons)
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())
    
    def _create_strategy_selector(self) -> QFrame:
        """Crea selector de estrategia con cards interactivas.
        
        Returns:
            QFrame con las cards de selección de estrategia
        """
        frame = QFrame()
        frame.setObjectName("strategy-selector-frame")
        frame.setStyleSheet(f"""
            QFrame#strategy-selector-frame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(int(DesignSystem.SPACE_12))
        
        # Título
        title_layout = QHBoxLayout()
        title_icon = QLabel()
        icon_manager.set_label_icon(
            title_icon, 
            'rule', 
            size=int(DesignSystem.ICON_SIZE_LG)
        )
        title_layout.addWidget(title_icon)
        
        title_label = QLabel("Elige qué archivo conservar en cada grupo")
        title_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # ButtonGroup para RadioButtons
        self.strategy_button_group = QButtonGroup(self)
        
        # Cards layout
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(int(DesignSystem.SPACE_12))
        
        # Estrategias disponibles
        strategies = [
            ('oldest', 'access_time', 'Mantener el más antiguo', 
             'Conserva el archivo con fecha de modificación más antigua. Recomendado para preservar originales.'),
            ('newest', 'update', 'Mantener el más reciente', 
             'Conserva el archivo con fecha de modificación más reciente. Útil para versiones editadas.'),
            ('largest', 'expand', 'Mantener el más grande', 
             'Conserva el archivo de mayor tamaño. Útil para preservar calidad máxima.'),
            ('smallest', 'compress', 'Mantener el más pequeño', 
             'Conserva el archivo de menor tamaño. Maximiza espacio liberado.')
        ]
        
        # Crear una card por cada estrategia
        for strategy_key, icon_name, title, description in strategies:
            is_selected = (strategy_key == self.keep_strategy)
            
            # Crear RadioButton
            radio = QRadioButton()
            radio.setChecked(is_selected)
            radio.toggled.connect(
                lambda checked, s=strategy_key: self._on_strategy_changed(s) if checked else None
            )
            self.strategy_button_group.addButton(radio)
            
            # Crear card usando el método de BaseDialog
            card = self._create_selection_card(
                f"strategy-{strategy_key}",
                icon_name,
                title,
                description,
                is_selected,
                radio
            )
            cards_layout.addWidget(card)
        
        layout.addLayout(cards_layout)
        
        return frame
    
    def _on_strategy_changed(self, new_strategy: str) -> None:
        """Maneja el cambio de estrategia de eliminación.
        
        Args:
            new_strategy: Nueva estrategia seleccionada ('oldest', 'newest', 'largest', 'smallest')
        """
        if new_strategy == self.keep_strategy:
            return
        
        self.logger.info(f"Cambiando estrategia de eliminación: {self.keep_strategy} -> {new_strategy}")
        self.keep_strategy = new_strategy
        
        # Actualizar estilos de las cards
        self._update_strategy_cards_styles()
        
        # Actualizar estado de archivos en el tree
        self._update_status_labels()
    
    def _update_strategy_cards_styles(self) -> None:
        """Actualiza los estilos de las cards de estrategia según la selección actual."""
        strategies = ['oldest', 'newest', 'largest', 'smallest']
        
        for strategy in strategies:
            card_name = f"strategy-card-{strategy}"
            card = self.findChild(QFrame, card_name)
            
            if card:
                is_selected = (strategy == self.keep_strategy)
                card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
                        border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
                        border-radius: {DesignSystem.RADIUS_BASE}px;
                        padding: {DesignSystem.SPACE_12}px;
                    }}
                    QFrame#{card_name}:hover {{
                        border-color: {DesignSystem.COLOR_PRIMARY};
                        background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
                    }}
                    QFrame#{card_name} QLabel {{
                        color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
                        font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
                    }}
                    QFrame#{card_name} QLabel#title-label {{
                        font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                    }}
                    QFrame#{card_name} QLabel#desc-label {{
                        color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
                        font-weight: {DesignSystem.FONT_WEIGHT_NORMAL};
                    }}
                """)
                
                # Actualizar color del icono
                self._update_card_icon_color(card, strategy, is_selected)
    
    def _update_card_icon_color(self, card: QFrame, strategy: str, is_selected: bool) -> None:
        """Actualiza el color del icono en una card de estrategia.
        
        Args:
            card: QFrame de la card
            strategy: Nombre de la estrategia
            is_selected: Si la card está seleccionada
        """
        icon_map = {
            'oldest': 'access_time',
            'newest': 'update',
            'largest': 'expand',
            'smallest': 'compress'
        }
        
        # Encontrar el icono (segundo QLabel en el header layout)
        header_layout = card.layout().itemAt(0).layout()  # Primer item es el header_layout
        if header_layout and header_layout.count() >= 2:
            icon_label = header_layout.itemAt(1).widget()  # Segundo widget es el icono
            if isinstance(icon_label, QLabel):
                icon_manager.set_label_icon(
                    icon_label,
                    icon_map.get(strategy, 'rule'),
                    size=int(DesignSystem.ICON_SIZE_XL),
                    color=DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_PRIMARY
                )
    
    def _load_initial_groups(self):
        """Carga los primeros grupos según INITIAL_LOAD"""
        self.loaded_count = 0
        self._load_groups_batch(self.INITIAL_LOAD)
    
    def _load_more_groups(self):
        """Carga el siguiente lote de grupos"""
        self._load_groups_batch(self.LOAD_INCREMENT)
    
    def _load_all_groups(self):
        """Carga todos los grupos restantes"""
        remaining = len(self.filtered_groups) - self.loaded_count
        if remaining > 100:
            reply = QMessageBox.question(
                self,
                "Cargar Todos",
                f"Esto cargará {remaining} grupos más. Puede tardar un momento. ¿Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self._load_groups_batch(remaining)
    
    def _load_groups_batch(self, count: int):
        """Carga un lote de grupos en el tree widget"""
        start_idx = self.loaded_count
        end_idx = min(start_idx + count, len(self.filtered_groups))
        
        for i in range(start_idx, end_idx):
            group = self.filtered_groups[i]
            self._add_group_to_tree(group, i + 1)
        
        self.loaded_count = end_idx
        self._update_info_label()
        
        # Deshabilitar botón si ya no hay más grupos
        if self.loaded_count >= len(self.filtered_groups):
            self.load_more_btn.setEnabled(False)
            self.load_more_btn.setText("Todos los Grupos Cargados")
            icon_manager.set_button_icon(self.load_more_btn, 'check', size=16)
        else:
            remaining = len(self.filtered_groups) - self.loaded_count
            self.load_more_btn.setText(f"Cargar {min(self.LOAD_INCREMENT, remaining)} Más Grupos")
            icon_manager.set_button_icon(self.load_more_btn, 'refresh', size=16)
    
    def _add_group_to_tree(self, group: DuplicateGroup, group_number: int):
        """Añade un grupo como nodo padre expandible en el tree"""
        # Nodo padre del grupo
        group_item = QTreeWidgetItem(self.tree_widget)
        file_count = len(group.files)
        # Espacio a liberar = tamaño total - archivo más grande (que se conservará)
        largest_file_size = max(f.stat().st_size for f in group.files)
        space_to_free = group.total_size - largest_file_size
        group_item.setText(0, f"Grupo {group_number} - {file_count} archivos")
        group_item.setText(1, format_size(group.total_size))
        group_item.setText(2, "")
        group_item.setText(3, "")
        group_item.setText(4, f"Libera: {format_size(space_to_free)}")
        
        # Estilo del grupo padre
        font = group_item.font(0)
        font.setBold(True)
        group_item.setFont(0, font)
        group_item.setBackground(0, Qt.GlobalColor.lightGray)
        
        # Determinar qué archivo mantener según estrategia
        if self.keep_strategy == 'oldest':
            keep_file = min(group.files, key=lambda f: f.stat().st_mtime)
        else:  # newest
            keep_file = max(group.files, key=lambda f: f.stat().st_mtime)
        
        # Añadir archivos como hijos
        for file_path in group.files:
            file_item = QTreeWidgetItem(group_item)
            
            # Icono según tipo de archivo
            ext = file_path.suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                icon_name = "image"
            elif ext in ['.mov', '.mp4', '.avi', '.mkv']:
                icon_name = "video"
            elif ext in ['.heic', '.heif']:
                icon_name = "camera"
            else:
                icon_name = "file"
            
            file_item.setIcon(0, icon_manager.get_icon(icon_name, size=16))
            file_item.setText(0, file_path.name)
            file_item.setText(1, format_size(file_path.stat().st_size))
            
            # Fecha de modificación
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            file_item.setText(2, mtime.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Ruta (truncada si es muy larga)
            path_str = str(file_path.parent)
            if len(path_str) > 50:
                path_str = "..." + path_str[-47:]
            file_item.setText(3, path_str)
            
            # Estado: mantener o eliminar
            is_keep = file_path == keep_file
            if is_keep:
                file_item.setText(4, "Mantener")
                file_item.setForeground(4, Qt.GlobalColor.darkGreen)
            else:
                file_item.setText(4, "Eliminar")
                file_item.setForeground(4, Qt.GlobalColor.red)
            
            # Guardar referencia al archivo en el item
            file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)
            
            # Tooltip con ruta completa
            file_item.setToolTip(0, str(file_path))
            file_item.setToolTip(3, str(file_path))
    
    def _update_status_labels(self):
        """Actualiza las etiquetas de estado según la estrategia seleccionada"""
        # Recorrer todos los grupos cargados y actualizar el estado
        for i in range(self.tree_widget.topLevelItemCount()):
            group_item = self.tree_widget.topLevelItem(i)
            
            # Obtener archivos del grupo
            files = []
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                filepath = child.data(0, Qt.ItemDataRole.UserRole)
                if filepath:
                    files.append(filepath)
            
            if not files:
                continue
            
            # Determinar archivo a mantener según estrategia
            if self.keep_strategy == 'oldest':
                keep_file = min(files, key=lambda f: f.stat().st_mtime)
            elif self.keep_strategy == 'newest':
                keep_file = max(files, key=lambda f: f.stat().st_mtime)
            elif self.keep_strategy == 'largest':
                keep_file = max(files, key=lambda f: f.stat().st_size)
            elif self.keep_strategy == 'smallest':
                keep_file = min(files, key=lambda f: f.stat().st_size)
            else:
                keep_file = files[0]  # Fallback
            
            # Actualizar estado de cada archivo hijo
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                filepath = child.data(0, Qt.ItemDataRole.UserRole)
                
                if filepath == keep_file:
                    child.setText(4, "Mantener")
                    child.setForeground(4, QColor(DesignSystem.COLOR_SUCCESS))
                else:
                    child.setText(4, "Eliminar")
                    child.setForeground(4, QColor(DesignSystem.COLOR_ERROR))
    
    def _update_info_label(self):
        """Actualiza el label de información de grupos"""
        total_filtered = len(self.filtered_groups)
        total_original = len(self.all_groups)
        
        if total_filtered < total_original:
            # Hay filtros aplicados
            self.groups_info_label.setText(
                f"Mostrando grupos {1 if self.loaded_count > 0 else 0}-{self.loaded_count} "
                f"de {total_filtered} grupos filtrados (de {total_original} totales)"
            )
        else:
            # Sin filtros
            self.groups_info_label.setText(
                f"Mostrando grupos {1 if self.loaded_count > 0 else 0}-{self.loaded_count} de {total_original}"
            )
    
    def _on_search_changed(self):
        """Maneja cambios en la búsqueda"""
        search_text = self.search_input.text().strip().lower()
        self._apply_filters(search_text)
    
    def _on_filter_changed(self):
        """Maneja cambios en el filtro de tamaño/cantidad"""
        search_text = self.search_input.text().strip().lower()
        self._apply_filters(search_text)
    
    def _apply_filters(self, search_text: str = ""):
        """Aplica búsqueda y filtros a los grupos"""
        filtered = self.all_groups
        
        # Aplicar búsqueda por texto
        if search_text:
            filtered = [
                group for group in filtered
                if any(search_text in str(f).lower() for f in group.files)
            ]
        
        # Aplicar filtro de combo
        filter_idx = self.filter_combo.currentIndex()
        if filter_idx == 1:  # >10 MB
            filtered = [g for g in filtered if g.total_size > 10 * 1024 * 1024]
        elif filter_idx == 2:  # >50 MB
            filtered = [g for g in filtered if g.total_size > 50 * 1024 * 1024]
        elif filter_idx == 3:  # >100 MB
            filtered = [g for g in filtered if g.total_size > 100 * 1024 * 1024]
        elif filter_idx == 4:  # 3+ archivos
            filtered = [g for g in filtered if len(g.files) >= 3]
        elif filter_idx == 5:  # 5+ archivos
            filtered = [g for g in filtered if len(g.files) >= 5]
        
        # Actualizar grupos filtrados y recargar
        self.filtered_groups = filtered
        self.tree_widget.clear()
        self.loaded_count = 0
        
        if len(self.filtered_groups) == 0:
            # No hay resultados
            self.groups_info_label.setText("No se encontraron grupos que coincidan con los filtros")
            self.load_more_btn.setEnabled(False)
        else:
            # Cargar primeros grupos
            self._load_initial_groups()
            self.load_more_btn.setEnabled(self.loaded_count < len(self.filtered_groups))
    
    def _on_item_double_clicked(self, item, column):
        """Maneja doble click en un item del tree"""
        # Obtener el archivo asociado al item
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if file_path and isinstance(file_path, Path):
            # Es un archivo, abrirlo
            self._open_file(file_path)
        else:
            # Es un grupo, expandir/colapsar
            item.setExpanded(not item.isExpanded())
    
    def _show_context_menu(self, position):
        """Muestra el menú contextual para un archivo"""
        from .dialog_utils import open_file, open_folder
        
        item = self.tree_widget.itemAt(position)
        if not item:
            return
        
        # Obtener el archivo asociado al item
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path or not isinstance(file_path, Path):
            return  # Es un grupo padre, no mostrar menú
        
        menu = QMenu(self)
        
        # Acción: Abrir archivo
        open_action = menu.addAction("Abrir archivo")
        open_action.triggered.connect(lambda: open_file(file_path, self))
        
        # Acción: Abrir carpeta
        open_folder_action = menu.addAction("Abrir carpeta contenedora")
        open_folder_action.triggered.connect(lambda: open_folder(file_path.parent, self))
        
        menu.addSeparator()
        
        # Acción: Ver detalles
        details_action = menu.addAction("Ver detalles del archivo")
        details_action.triggered.connect(lambda: self._show_file_details(file_path))
        
        menu.exec(self.tree_widget.viewport().mapToGlobal(position))
    
    def _show_file_details(self, file_path: Path):
        """Muestra diálogo con detalles del archivo"""
        # Determinar el estado del archivo (mantener/eliminar)
        # Buscar en qué grupo está este archivo
        status_info = None
        for group in self.filtered_groups:
            if file_path in group.files:
                # Determinar qué archivo se mantiene
                if self.keep_strategy == 'oldest':
                    keep_file = min(group.files, key=lambda f: f.stat().st_mtime)
                else:
                    keep_file = max(group.files, key=lambda f: f.stat().st_mtime)
                
                is_keep = file_path == keep_file
                status_info = {
                    'metadata': {
                        'Estado': 'Se mantendrá' if is_keep else 'Se eliminará',
                        'Grupo': f'{len(group.files)} archivos duplicados',
                        'Espacio grupo': format_size(group.total_size),
                        'Estrategia': 'Mantener más antiguo' if self.keep_strategy == 'oldest' else 'Mantener más reciente'
                    }
                }
                break
        
        show_file_details_dialog(file_path, self, status_info)
    
    def _open_file(self, file_path: Path):
        """Abre un archivo con la aplicación predeterminada del sistema"""
        if file_path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
        else:
            QMessageBox.warning(
                self,
                "Archivo no encontrado",
                f"No se encontró el archivo:\n{file_path}"
            )
    
    def accept(self):
        self.accepted_plan = {
            'groups': self.analysis.groups,
            'keep_strategy': self.keep_strategy,
            'create_backup': self.backup_checkbox.isChecked(),
            'dry_run': self.dry_run_checkbox.isChecked()
        }
        super().accept()
