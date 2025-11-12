"""
Diálogo de Organización de Archivos - Versión 2.0
Permite elegir el tipo de organización en tiempo real y ver los resultados dinámicamente
"""
from pathlib import Path
from collections import defaultdict
from typing import Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QDialogButtonBox, QCheckBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QComboBox, QPushButton, QFrame,
    QApplication, QMenu, QWidget,  QProgressBar
)
from PyQt6.QtGui import QColor, QFont, QCursor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread

from config import Config
from utils.format_utils import format_size
from utils.date_utils import get_file_date
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from utils.logger import get_logger
from services.file_organizer_service import FileOrganizer, OrganizationType
from services.result_types import OrganizationAnalysisResult
from .base_dialog import BaseDialog


class OrganizationWorker(QThread):
    """Worker para análisis de organización en background"""
    
    finished = pyqtSignal(OrganizationAnalysisResult)
    progress = pyqtSignal(int, int, str)
    error = pyqtSignal(str)
    
    def __init__(self, root_directory: Path, organization_type: OrganizationType):
        super().__init__()
        self.root_directory = root_directory
        self.organization_type = organization_type
        self.organizer = FileOrganizer()
        self.logger = get_logger("OrganizationWorker")
    
    def run(self):
        """Ejecuta el análisis"""
        try:
            self.logger.info(f"Analizando con tipo: {self.organization_type.value}")
            
            def progress_callback(current, total, message):
                self.progress.emit(current, total, message)
                return True  # Continue processing
            
            result = self.organizer.analyze_directory_structure(
                self.root_directory,
                self.organization_type,
                progress_callback
            )
            self.finished.emit(result)
            
        except Exception as e:
            self.logger.error(f"Error en análisis: {e}", exc_info=True)
            self.error.emit(str(e))


class FileOrganizationDialog(BaseDialog):
    """
    Diálogo profesional para organización de archivos con:
    - Selector de tipo de organización en tiempo real
    - Análisis dinámico al cambiar tipo
    - UX profesional siguiendo DesignSystem
    - Sin emojis, usando Icon Manager
    """
    
    # Configuración de paginación
    ITEMS_PER_PAGE = 200
    MAX_ITEMS_WITHOUT_PAGINATION = 500

    def __init__(self, initial_analysis: OrganizationAnalysisResult, parent=None):
        super().__init__(parent)
        self.logger = get_logger("FileOrganizationDialog")
        
        # Datos principales
        self.root_directory = Path(initial_analysis.root_directory)
        self.analysis = initial_analysis
        self.current_organization_type = OrganizationType(initial_analysis.organization_type)
        self.accepted_plan = None
        
        # Datos filtrados y paginación
        self.filtered_moves = list(initial_analysis.move_plan)
        self.current_page = 0
        self.total_pages = 0
        
        # Worker para análisis
        self.worker: Optional[OrganizationWorker] = None
        self.is_analyzing = False
        
        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz"""
        self.setWindowTitle("Organización de Archivos")
        self.setModal(True)
        self.resize(1200, 800)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_20)
        
        # === HEADER COMPACTO CON MÉTRICAS ===
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='folder-settings',
            title='Organización de archivos',
            description='Reorganiza tu colección según diferentes criterios. Selecciona un tipo y revisa el plan.',
            metrics=[
                {
                    'value': str(self.analysis.total_files_to_move),
                    'label': 'Archivos',
                    'color': DesignSystem.COLOR_PRIMARY
                },
                {
                    'value': str(len(self.analysis.subdirectories)),
                    'label': 'Subdirs',
                    'color': '#9c27b0'
                },
                {
                    'value': format_size(self.analysis.total_size_to_move),
                    'label': 'Tamaño',
                    'color': '#ff9800'
                }
            ]
        )
        main_layout.addWidget(self.header_frame)
        
        # Contenedor con márgenes para el resto del contenido
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(DesignSystem.SPACE_16)
        content_layout.setContentsMargins(
            DesignSystem.SPACE_24,
            DesignSystem.SPACE_12,
            DesignSystem.SPACE_24,
            0
        )
        main_layout.addWidget(content_container)
        
        # === SELECTOR DE TIPO ===
        self.type_selector = self._create_type_selector()
        content_layout.addWidget(self.type_selector)
        
        # === INFORMACIÓN DE CARPETAS ===
        self.folders_info_widget = self._create_folders_info()
        if self.folders_info_widget:
            content_layout.addWidget(self.folders_info_widget)
        
        # === BARRA DE HERRAMIENTAS ===
        toolbar = self._create_toolbar()
        content_layout.addLayout(toolbar)
        
        # === TREE WIDGET ===
        self.files_tree = self._create_tree_widget()
        content_layout.addWidget(self.files_tree, 1)  # Stretch factor 1
        
        # === PAGINACIÓN ===
        self.pagination_widget = self._create_pagination_controls()
        content_layout.addWidget(self.pagination_widget)
        
        # === PROGRESS BAR (inicialmente oculto) ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                text-align: center;
                background-color: {DesignSystem.COLOR_BG_1};
            }}
            QProgressBar::chunk {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
        """)
        content_layout.addWidget(self.progress_bar)
        
        # === OPCIONES ===
        options_group = self._create_options_group()
        content_layout.addWidget(options_group)
        
        # === BOTONES ===
        self.buttons = self._create_action_buttons()
        content_layout.addWidget(self.buttons)
        
        # Actualizar vista inicial
        self._update_all_ui()
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())

    def _create_type_selector(self) -> QWidget:
        """Crea selector de tipo de organización usando el método centralizado de BaseDialog."""
        options = [
            (OrganizationType.TO_ROOT, "folder-open", "Mover a Raíz",
             "Mueve todos los archivos al directorio raíz eliminando subdirectorios"),
            (OrganizationType.BY_MONTH, "calendar_month", "Por Mes",
             "Organiza en carpetas mensuales (YYYY_MM) según la fecha del archivo"),
            (OrganizationType.WHATSAPP_SEPARATE, "mobile", "Separar WhatsApp",
             "Separa archivos de WhatsApp en carpeta dedicada, resto a la raíz")
        ]
        
        return self._create_option_selector(
            title="Elige cómo organizar los archivos",
            title_icon='options',
            options=options,
            selected_value=self.current_organization_type,
            on_change_callback=self._on_type_changed
        )
    
    def _on_type_changed(self, new_type: OrganizationType):
        """Maneja el cambio de tipo de organización"""
        if new_type == self.current_organization_type:
            return
        
        self.logger.info(f"Cambiando tipo de organización: {self.current_organization_type.value} -> {new_type.value}")
        self.current_organization_type = new_type
        
        # Iniciar análisis en background
        self._start_analysis(new_type)
    
    def _start_analysis(self, org_type: OrganizationType):
        """Inicia análisis en background"""
        if self.is_analyzing and self.worker and self.worker.isRunning():
            self.logger.warning("Ya hay un análisis en curso")
            return
        
        self.is_analyzing = True
        self._set_ui_loading_state(True)
        
        # Crear y configurar worker
        self.worker = OrganizationWorker(self.root_directory, org_type)
        self.worker.finished.connect(self._on_analysis_finished)
        self.worker.progress.connect(self._on_analysis_progress)
        self.worker.error.connect(self._on_analysis_error)
        
        # Iniciar
        self.worker.start()
    
    def _on_analysis_finished(self, result: OrganizationAnalysisResult):
        """Maneja la finalización del análisis"""
        self.logger.info(f"Análisis completado: {result.total_files_to_move} archivos")
        self.analysis = result
        self.filtered_moves = list(result.move_plan)
        self.current_page = 0
        
        self._set_ui_loading_state(False)
        self._update_all_ui()
        self.is_analyzing = False
    
    def _on_analysis_progress(self, current: int, total: int, message: str):
        """Maneja el progreso del análisis"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{message} - {current}/{total}")
    
    def _on_analysis_error(self, error_msg: str):
        """Maneja errores en el análisis"""
        from PyQt6.QtWidgets import QMessageBox
        self.logger.error(f"Error en análisis: {error_msg}")
        self._set_ui_loading_state(False)
        self.is_analyzing = False
        QMessageBox.critical(self, "Error", f"Error al analizar:\n{error_msg}")
    
    def _set_ui_loading_state(self, loading: bool):
        """Activa/desactiva el estado de carga"""
        self.progress_bar.setVisible(loading)
        self.files_tree.setEnabled(not loading)
        self.ok_button.setEnabled(not loading and self.analysis.total_files_to_move > 0)
        
        # Deshabilitar opciones de tipo durante análisis
        if hasattr(self, 'type_selector'):
            button_group = self.type_selector.property("button_group")
            if button_group:
                for button in button_group.buttons():
                    button.setEnabled(not loading)
    
    def _update_all_ui(self):
        """Actualiza toda la UI con los datos actuales"""
        
        # Actualizar header con métricas
        self._update_header_metrics()
        
        # Actualizar info de carpetas
        self._update_folders_info()
        
        # Actualizar tree
        self._update_tree()
        
        # Actualizar botón OK
        self._update_ok_button()
        
        # Re-aplicar estilos a las cards de selección
        if hasattr(self, 'type_selector'):
            self._update_option_selector_styles(
                self.type_selector,
                [OrganizationType.TO_ROOT, OrganizationType.BY_MONTH, OrganizationType.WHATSAPP_SEPARATE],
                self.current_organization_type
            )
    
    def _update_header_metrics(self):
        """Actualiza las métricas del header compacto"""
        # Buscar y actualizar los QLabel de las métricas existentes en lugar de recrear el header
        main_layout = self.header_frame.layout()
        if not main_layout:
            return
        
        # Las métricas están en un QHBoxLayout al final del main_layout
        metrics_layout = None
        for i in range(main_layout.count()):
            item = main_layout.itemAt(i)
            if item and item.layout() and isinstance(item.layout(), QHBoxLayout):
                # El último QHBoxLayout con múltiples widgets es el de métricas
                if item.layout().count() > 1:
                    metrics_layout = item.layout()
        
        if not metrics_layout:
            return
        
        # Actualizar cada métrica (son QWidget con QVBoxLayout conteniendo value_label y label_widget)
        metrics_data = [
            str(self.analysis.total_files_to_move),
            str(len(self.analysis.subdirectories)),
            format_size(self.analysis.total_size_to_move)
        ]
        
        for idx, new_value in enumerate(metrics_data):
            if idx < metrics_layout.count():
                metric_widget = metrics_layout.itemAt(idx).widget()
                if metric_widget and metric_widget.layout():
                    # El primer hijo del layout es el value_label
                    value_label = metric_widget.layout().itemAt(0).widget()
                    if value_label and isinstance(value_label, QLabel):
                        value_label.setText(new_value)
    
    def _update_type_selector_styles(self):
        """Actualiza los estilos de las cards de selección según el tipo actual"""
        for org_type in OrganizationType:
            card_name = f"option-card-{org_type.value}"
            card = self.findChild(QFrame, card_name)
            if card:
                is_selected = org_type == self.current_organization_type
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
                
                # Actualizar colores de iconos manualmente
                self._update_card_icon_colors(card, org_type, is_selected)

    def _update_card_icon_colors(self, card: QFrame, org_type: OrganizationType, is_selected: bool):
        """Actualiza el color del icono en una card específica"""
        # Encontrar el icono (es el segundo QLabel en el layout horizontal del header)
        header_layout = card.layout().itemAt(0).layout()  # Primer item es el header_layout
        if header_layout and header_layout.count() >= 2:
            icon_label = header_layout.itemAt(1).widget()  # Segundo widget es el icono
            if isinstance(icon_label, QLabel):
                icon_name = self._get_icon_name_for_type(org_type)
                icon_manager.set_label_icon(
                    icon_label,
                    icon_name,
                    size=DesignSystem.ICON_SIZE_XL,
                    color=DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_PRIMARY
                )

    def _get_icon_name_for_type(self, org_type: OrganizationType) -> str:
        """Devuelve el nombre del icono para un tipo de organización"""
        if org_type == OrganizationType.TO_ROOT:
            return "folder-open"
        elif org_type == OrganizationType.BY_MONTH:
            return "calendar_month"
        elif org_type == OrganizationType.WHATSAPP_SEPARATE:
            return "mobile"
        return "folder"

    
    def _create_metrics_section(self) -> QWidget:
        """Crea panel de métricas dinámico"""
        self.metrics_container = QWidget()
        self.metrics_layout = QHBoxLayout(self.metrics_container)
        self.metrics_layout.setContentsMargins(0, 0, 0, 0)
        self.metrics_layout.setSpacing(DesignSystem.SPACE_12)
        
        self._update_metrics()
        return self.metrics_container
    
    def _update_metrics(self):
        """Actualiza las métricas"""
        # Limpiar layout
        while self.metrics_layout.count():
            child = self.metrics_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Métricas principales
        metrics_data = [
            ("Total archivos", self.analysis.total_files_to_move, DesignSystem.COLOR_PRIMARY),
            ("Subdirectorios", len(self.analysis.subdirectories), "#9c27b0"),
            ("Tamaño total", format_size(self.analysis.total_size_to_move), "#ff9800"),
        ]
        
       
        # Métricas por tipo
        if self.analysis.files_by_type:
            types_text = " | ".join([
                f"{file_type}: {count}" 
                for file_type, count in sorted(self.analysis.files_by_type.items())
            ])
            types_label = QLabel(types_text)
            types_label.setStyleSheet(f"""
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_8}px;
            """)
            self.metrics_layout.addWidget(types_label)
        
        # Advertencia de conflictos
        if self.analysis.potential_conflicts > 0:
            conflicts_label = QLabel(f"{self.analysis.potential_conflicts} conflictos de nombres")
            conflicts_label.setStyleSheet(f"""
                background-color: {DesignSystem.COLOR_BG_4};
                color: {DesignSystem.COLOR_WARNING};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                padding: {DesignSystem.SPACE_8}px;
                border-radius: {DesignSystem.RADIUS_BASE}px;
            """)
            self.metrics_layout.addWidget(conflicts_label)
        
        self.metrics_layout.addStretch()
    
    def _create_folders_info(self) -> Optional[QWidget]:
        """Crea sección de información de carpetas a crear"""
        # Inicializar atributos siempre
        self.folders_info_container = None
        self.folders_info_label = None
        
        if not self.analysis.folders_to_create:
            return None
        
        self.folders_info_container = QFrame()
        self.folders_info_container.setStyleSheet(f"""
            QFrame {{ 
                background-color: #e3f2fd; 
                border-left: 3px solid {DesignSystem.COLOR_PRIMARY};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px;
            }}
        """)
        
        layout = QVBoxLayout(self.folders_info_container)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_6, DesignSystem.SPACE_12, DesignSystem.SPACE_6)
        
        self.folders_info_label = QLabel()
        self.folders_info_label.setWordWrap(True)
        self.folders_info_label.setTextFormat(Qt.TextFormat.RichText)
        self.folders_info_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: #1976d2;
        """)
        layout.addWidget(self.folders_info_label)
        
        self._update_folders_info()
        return self.folders_info_container
    
    def _update_folders_info(self):
        """Actualiza la información de carpetas"""
        if not self.folders_info_label:
            return
        
        folders = sorted(self.analysis.folders_to_create)
        count = len(folders)
        
        if count == 0:
            if self.folders_info_container:
                self.folders_info_container.setVisible(False)
            return
        
        if self.folders_info_container:
            self.folders_info_container.setVisible(True)
        
        if count <= 10:
            folders_text = ", ".join(folders)
        else:
            folders_text = ", ".join(folders[:10]) + f"... (+{count - 10} más)"
        
        self.folders_info_label.setText(f"Se crearán {count} carpetas: <b>{folders_text}</b>")
    
    def _create_toolbar(self) -> QHBoxLayout:
        """Crea barra de herramientas con filtros"""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(DesignSystem.SPACE_8)
        
        # Búsqueda
        search_icon = QLabel()
        icon_manager.set_label_icon(search_icon, 'search', size=DesignSystem.ICON_SIZE_SM)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre...")
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setMaximumWidth(200)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_8}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
        """)
        toolbar.addWidget(search_icon)
        toolbar.addWidget(self.search_input)
        
        # Separador
        sep = QLabel("|")
        sep.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER};")
        toolbar.addWidget(sep)
        
        # Filtro por tipo
        type_label = QLabel("Tipo:")
        type_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px;")
        self.type_combo = QComboBox()
        types = ["Todos"] + sorted(list(self.analysis.files_by_type.keys()))
        self.type_combo.addItems(types)
        self.type_combo.currentTextChanged.connect(self._apply_filters)
        self.type_combo.setMaximumWidth(120)
        toolbar.addWidget(type_label)
        toolbar.addWidget(self.type_combo)
        
        # Filtro por subdirectorio (solo para to_root y whatsapp)
        if self.current_organization_type in [OrganizationType.TO_ROOT, OrganizationType.WHATSAPP_SEPARATE]:
            subdir_label = QLabel("Origen:")
            subdir_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px;")
            self.subdir_combo = QComboBox()
            subdirs = ["Todos"] + sorted(list(self.analysis.subdirectories.keys()))
            self.subdir_combo.addItems(subdirs)
            self.subdir_combo.currentTextChanged.connect(self._apply_filters)
            self.subdir_combo.setMaximumWidth(250)
            toolbar.addWidget(subdir_label)
            toolbar.addWidget(self.subdir_combo)
        else:
            self.subdir_combo = None
        
        # Filtro solo conflictos
        self.conflicts_checkbox = QCheckBox("Solo conflictos")
        self.conflicts_checkbox.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px;")
        self.conflicts_checkbox.stateChanged.connect(self._apply_filters)
        toolbar.addWidget(self.conflicts_checkbox)
        
        # Botón limpiar
        clear_btn = QPushButton("Limpiar")
        clear_btn.setProperty("class", "secondary-small")
        icon_manager.set_button_icon(clear_btn, 'close', size=DesignSystem.ICON_SIZE_SM)
        clear_btn.clicked.connect(self._clear_filters)
        clear_btn.setMaximumWidth(100)
        toolbar.addWidget(clear_btn)
        
        # Contador
        self.counter_label = QLabel()
        self.counter_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_PRIMARY};
            margin-left: {DesignSystem.SPACE_12}px;
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        toolbar.addWidget(self.counter_label)
        
        toolbar.addStretch()
        return toolbar
    
    def _create_tree_widget(self) -> QTreeWidget:
        """Crea TreeWidget con configuración dinámica"""
        tree = QTreeWidget()
        
        # Configurar columnas según tipo
        self._configure_tree_columns(tree)
        
        tree.setAlternatingRowColors(True)
        tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tree.itemDoubleClicked.connect(self._on_file_double_clicked)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._show_context_menu)
        tree.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                outline: none;
                background-color: {DesignSystem.COLOR_SURFACE};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QTreeWidget::item {{
                border: none;
                outline: none;
                padding: {DesignSystem.SPACE_4}px;
            }}
            QTreeWidget::item:hover {{
                background-color: #f0f7ff;
            }}
        """)
        tree.setToolTip(
            "Doble clic en archivo para abrirlo\n"
            "Clic derecho para ver detalles y opciones"
        )
        
        return tree
    
    def _configure_tree_columns(self, tree: QTreeWidget):
        """Configura las columnas del tree según el tipo de organización"""
        org_type = self.current_organization_type
        
        if org_type == OrganizationType.TO_ROOT:
            tree.setHeaderLabels(["Archivo", "Origen", "Tamaño", "Estado"])
            tree.setColumnWidth(0, 380)
            tree.setColumnWidth(1, 180)
            tree.setColumnWidth(2, 100)
            tree.setColumnWidth(3, 250)
        elif org_type == OrganizationType.BY_MONTH:
            tree.setHeaderLabels(["Archivo", "Fecha", "Origen", "Tamaño"])
            tree.setColumnWidth(0, 400)
            tree.setColumnWidth(1, 120)
            tree.setColumnWidth(2, 200)
            tree.setColumnWidth(3, 100)
        else:  # WHATSAPP_SEPARATE
            tree.setHeaderLabels(["Archivo", "Origen", "Destino", "Tamaño"])
            tree.setColumnWidth(0, 400)
            tree.setColumnWidth(1, 200)
            tree.setColumnWidth(2, 150)
            tree.setColumnWidth(3, 100)
    
    def _create_pagination_controls(self) -> QWidget:
        """Crea controles de paginación"""
        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BG_1};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px;
            }}
        """)
        layout = QHBoxLayout(widget)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        # Botones de navegación
        button_style = f"""
            QPushButton {{
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
        """
        
        self.first_page_btn = QPushButton("Primera")
        self.first_page_btn.setProperty("class", "secondary-small")
        self.first_page_btn.clicked.connect(self._go_first_page)
        self.first_page_btn.setStyleSheet(button_style)
        layout.addWidget(self.first_page_btn)
        
        self.prev_page_btn = QPushButton("Anterior")
        self.prev_page_btn.setProperty("class", "secondary-small")
        self.prev_page_btn.clicked.connect(self._go_prev_page)
        self.prev_page_btn.setStyleSheet(button_style)
        layout.addWidget(self.prev_page_btn)
        
        self.page_label = QLabel()
        self.page_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            padding: 0 {DesignSystem.SPACE_16}px;
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)
        
        self.next_page_btn = QPushButton("Siguiente")
        self.next_page_btn.setProperty("class", "secondary-small")
        self.next_page_btn.clicked.connect(self._go_next_page)
        self.next_page_btn.setStyleSheet(button_style)
        layout.addWidget(self.next_page_btn)
        
        self.last_page_btn = QPushButton("Última")
        self.last_page_btn.setProperty("class", "secondary-small")
        self.last_page_btn.clicked.connect(self._go_last_page)
        self.last_page_btn.setStyleSheet(button_style)
        layout.addWidget(self.last_page_btn)
        
        layout.addStretch()
        
        # Items per page
        layout.addWidget(QLabel("Items por página:"))
        self.items_per_page_combo = QComboBox()
        self.items_per_page_combo.addItems(["100", "200", "500", "Todos"])
        self.items_per_page_combo.setCurrentText("200")
        self.items_per_page_combo.currentTextChanged.connect(self._change_items_per_page)
        self.items_per_page_combo.setMaximumWidth(100)
        layout.addWidget(self.items_per_page_combo)
        
        widget.setVisible(False)
        return widget
    
    def _create_options_group(self) -> QFrame:
        """Crea grupo de opciones usando método centralizado con opción extra"""
        from PyQt6.QtWidgets import QFrame, QVBoxLayout
        from ui.styles.design_system import DesignSystem
        
        # Crear contenedor principal
        container = QFrame()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(int(DesignSystem.SPACE_12))
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Opciones de seguridad + limpieza de directorios vacíos
        security_options = self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            show_cleanup_empty_dirs=True,
            backup_label="Crear backup antes de mover",
            dry_run_label="Modo simulación (no mover archivos realmente)",
            cleanup_label="Eliminar directorios vacíos"
        )
        container_layout.addWidget(security_options)
        
        return container
    
    def _create_action_buttons(self) -> QDialogButtonBox:
        """Crea botones de acción con estilo Material Design"""
        ok_enabled = self.analysis.total_files_to_move > 0
        if ok_enabled:
            size_formatted = format_size(self.analysis.total_size_to_move)
            ok_text = f"Organizar Archivos ({self.analysis.total_files_to_move} archivos, {size_formatted})"
        else:
            ok_text = "Sin archivos para organizar"
        
        buttons = self.make_ok_cancel_buttons(
            ok_text=ok_text,
            ok_enabled=ok_enabled,
            button_style='primary'
        )
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        
        return buttons
    
    def _update_ok_button(self):
        """Actualiza el texto y estado del botón OK"""
        ok_enabled = self.analysis.total_files_to_move > 0
        self.ok_button.setEnabled(ok_enabled and not self.is_analyzing)
        
        if ok_enabled:
            size_formatted = format_size(self.analysis.total_size_to_move)
            ok_text = f"Organizar Archivos ({self.analysis.total_files_to_move} archivos, {size_formatted})"
        else:
            ok_text = "Sin archivos para organizar"
        
        self.ok_button.setText(ok_text)
    
    # === FILTROS ===
    
    def _apply_filters(self):
        """Aplica filtros a la lista de movimientos"""
        search_text = self.search_input.text().lower()
        type_filter = self.type_combo.currentText()
        subdir_filter = self.subdir_combo.currentText() if self.subdir_combo else "Todos"
        show_only_conflicts = self.conflicts_checkbox.isChecked()
        
        self.filtered_moves = []
        
        for move in self.analysis.move_plan:
            # Filtro de búsqueda
            if search_text and search_text not in move.original_name.lower():
                continue
            
            # Filtro por tipo
            if type_filter != "Todos" and move.file_type != type_filter:
                continue
            
            # Filtro por subdirectorio
            if subdir_filter != "Todos" and move.subdirectory != subdir_filter:
                continue
            
            # Filtro solo conflictos
            if show_only_conflicts and not move.has_conflict:
                continue
            
            self.filtered_moves.append(move)
        
        self.current_page = 0
        self._update_tree()
    
    def _clear_filters(self):
        """Limpia todos los filtros"""
        self.search_input.clear()
        self.type_combo.setCurrentIndex(0)
        if self.subdir_combo:
            self.subdir_combo.setCurrentIndex(0)
        self.conflicts_checkbox.setChecked(False)
    
    # === PAGINACIÓN ===
    
    def _go_first_page(self):
        self.current_page = 0
        QTimer.singleShot(0, self._update_tree)
    
    def _go_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            QTimer.singleShot(0, self._update_tree)
    
    def _go_next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            QTimer.singleShot(0, self._update_tree)
    
    def _go_last_page(self):
        self.current_page = max(0, self.total_pages - 1)
        QTimer.singleShot(0, self._update_tree)
    
    def _change_items_per_page(self, text: str):
        if text == "Todos":
            self.ITEMS_PER_PAGE = len(self.filtered_moves)
        else:
            self.ITEMS_PER_PAGE = int(text)
        self.current_page = 0
        QTimer.singleShot(0, self._update_tree)
    
    # === ACTUALIZACIÓN DEL TREE ===
    
    def _update_tree(self):
        """Actualiza el TreeWidget con los datos filtrados"""
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        
        try:
            total_filtered = len(self.filtered_moves)
            use_pagination = total_filtered > self.MAX_ITEMS_WITHOUT_PAGINATION
            
            if use_pagination:
                self.total_pages = (total_filtered + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE
                start_idx = self.current_page * self.ITEMS_PER_PAGE
                end_idx = min(start_idx + self.ITEMS_PER_PAGE, total_filtered)
                items_to_show = self.filtered_moves[start_idx:end_idx]
                
                self.pagination_widget.setVisible(True)
                self.page_label.setText(
                    f"Página {self.current_page + 1} de {self.total_pages} "
                    f"(mostrando {start_idx + 1}-{end_idx} de {total_filtered})"
                )
                
                self.first_page_btn.setEnabled(self.current_page > 0)
                self.prev_page_btn.setEnabled(self.current_page > 0)
                self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
                self.last_page_btn.setEnabled(self.current_page < self.total_pages - 1)
            else:
                items_to_show = self.filtered_moves
                self.pagination_widget.setVisible(False)
            
            # Limpiar tree
            self.files_tree.clear()
            
            # Reconfigurar columnas si cambió el tipo
            self._configure_tree_columns(self.files_tree)
            
            # Poblar según tipo
            org_type = self.current_organization_type
            if org_type == OrganizationType.TO_ROOT:
                self._populate_tree_to_root(items_to_show)
            elif org_type == OrganizationType.BY_MONTH:
                self._populate_tree_by_month(items_to_show)
            else:  # WHATSAPP_SEPARATE
                self._populate_tree_whatsapp(items_to_show)
            
            # Actualizar contador
            total = len(self.analysis.move_plan)
            if use_pagination:
                self.counter_label.setText(
                    f"Mostrando {len(items_to_show)} de {total_filtered} archivos filtrados ({total} total)"
                )
            else:
                if total_filtered == total:
                    self.counter_label.setText(f"Mostrando {total_filtered} archivos")
                else:
                    self.counter_label.setText(f"Mostrando {total_filtered} de {total} archivos")
        
        finally:
            QApplication.restoreOverrideCursor()
    
    def _populate_tree_to_root(self, moves):
        """Poblar tree para TO_ROOT"""
        # Agrupar por subdirectorio
        by_subdir = defaultdict(list)
        for move in moves:
            by_subdir[move.subdirectory].append(move)
        
        # Crear nodo raíz
        total_moves = len(moves)
        total_size_all = sum(m.size for m in moves)
        total_conflicts = sum(1 for m in moves if m.has_conflict)
        
        root_parent = QTreeWidgetItem()
        root_parent.setText(0, "Raíz del directorio")
        root_parent.setText(1, "")
        root_parent.setText(2, f"{total_moves} archivos")
        if total_conflicts > 0:
            root_parent.setText(3, f"{total_conflicts} conflictos | {format_size(total_size_all)}")
            root_parent.setForeground(3, QColor(DesignSystem.COLOR_ERROR))
        else:
            root_parent.setText(3, format_size(total_size_all))
        
        root_font = QFont()
        root_font.setBold(True)
        root_font.setPointSize(11)
        root_parent.setFont(0, root_font)
        root_parent.setForeground(0, QColor(DesignSystem.COLOR_PRIMARY))
        
        self.files_tree.addTopLevelItem(root_parent)
        
        # Subnodos por subdirectorio
        for subdir in sorted(by_subdir.keys()):
            moves_in_subdir = by_subdir[subdir]
            total_size = sum(m.size for m in moves_in_subdir)
            conflicts = sum(1 for m in moves_in_subdir if m.has_conflict)
            
            subdir_node = QTreeWidgetItem()
            subdir_node.setText(0, f"  Desde: {subdir}")
            subdir_node.setText(1, f"{len(moves_in_subdir)} archivos")
            subdir_node.setText(2, format_size(total_size))
            if conflicts > 0:
                subdir_node.setText(3, f"{conflicts} conflictos")
                subdir_node.setForeground(3, QColor(DesignSystem.COLOR_ERROR))
            
            subdir_font = QFont()
            subdir_font.setBold(True)
            subdir_node.setFont(0, subdir_font)
            subdir_node.setForeground(0, QColor(DesignSystem.COLOR_TEXT_SECONDARY))
            
            root_parent.addChild(subdir_node)
            
            # Archivos
            for move in sorted(moves_in_subdir, key=lambda m: m.original_name):
                child = QTreeWidgetItem()
                child.setText(0, f"    {move.original_name}")
                child.setText(1, subdir)
                child.setText(2, format_size(move.size))
                
                if move.has_conflict:
                    child.setText(3, f"→ {move.new_name}")
                    child.setForeground(3, QColor(DesignSystem.COLOR_ERROR))
                else:
                    child.setText(3, "OK")
                    child.setForeground(3, QColor(DesignSystem.COLOR_SUCCESS))
                
                child.setData(0, Qt.ItemDataRole.UserRole, move)
                subdir_node.addChild(child)
            
            if len(moves_in_subdir) <= 20:
                subdir_node.setExpanded(True)
            
            if root_parent.childCount() % 10 == 0:
                QApplication.processEvents()
        
        root_parent.setExpanded(True)
    
    def _populate_tree_by_month(self, moves):
        """Poblar tree para BY_MONTH"""
        # Agrupar por carpeta destino
        by_folder = defaultdict(list)
        for move in moves:
            folder = move.target_folder or "Sin fecha"
            by_folder[folder].append(move)
        
        for folder in sorted(by_folder.keys(), reverse=True):
            moves_in_folder = by_folder[folder]
            total_size = sum(m.size for m in moves_in_folder)
            
            parent = QTreeWidgetItem()
            parent.setText(0, f"{folder}/")
            parent.setText(1, "")
            parent.setText(2, f"{len(moves_in_folder)} archivos")
            parent.setText(3, format_size(total_size))
            
            parent_font = QFont()
            parent_font.setBold(True)
            parent.setFont(0, parent_font)
            parent.setForeground(0, QColor(DesignSystem.COLOR_PRIMARY))
            
            self.files_tree.addTopLevelItem(parent)
            
            for move in sorted(moves_in_folder, key=lambda m: m.original_name):
                child = QTreeWidgetItem()
                child.setText(0, f"  {move.original_name}")
                
                try:
                    file_date = get_file_date(move.source_path)
                    if file_date:
                        child.setText(1, file_date.strftime("%Y-%m-%d"))
                    else:
                        child.setText(1, "Sin fecha")
                except Exception:
                    child.setText(1, "Error")
                
                child.setText(2, move.subdirectory)
                child.setText(3, format_size(move.size))
                child.setData(0, Qt.ItemDataRole.UserRole, move)
                
                parent.addChild(child)
            
            if len(moves_in_folder) <= 20:
                parent.setExpanded(True)
            
            if self.files_tree.topLevelItemCount() % 10 == 0:
                QApplication.processEvents()
    
    def _populate_tree_whatsapp(self, moves):
        """Poblar tree para WHATSAPP_SEPARATE"""
        whatsapp_moves = []
        other_moves = []
        
        for move in moves:
            is_whatsapp = (
                'whatsapp' in move.subdirectory.lower() or
                'WhatsApp' in str(move.source_path) or
                (move.original_name.startswith(('IMG-', 'VID-')) and '-WA' in move.original_name)
            )
            
            if is_whatsapp:
                whatsapp_moves.append(move)
            else:
                other_moves.append(move)
        
        if whatsapp_moves:
            self._create_whatsapp_category_node("WhatsApp/", whatsapp_moves, "WhatsApp/")
        
        if other_moves:
            self._create_whatsapp_category_node("Raíz del directorio", other_moves, "Raíz")
    
    def _create_whatsapp_category_node(self, title: str, moves, destination: str):
        """Crea nodo de categoría para WhatsApp"""
        total_size = sum(m.size for m in moves)
        
        parent = QTreeWidgetItem()
        parent.setText(0, title)
        parent.setText(1, "")
        parent.setText(2, f"{len(moves)} archivos → {destination}")
        parent.setText(3, format_size(total_size))
        
        parent_font = QFont()
        parent_font.setBold(True)
        parent.setFont(0, parent_font)
        
        if "WhatsApp" in destination:
            parent.setForeground(0, QColor("#25d366"))
        else:
            parent.setForeground(0, QColor(DesignSystem.COLOR_PRIMARY))
        
        self.files_tree.addTopLevelItem(parent)
        
        for move in sorted(moves, key=lambda m: m.original_name):
            child = QTreeWidgetItem()
            child.setText(0, f"  {move.original_name}")
            child.setText(1, move.subdirectory if move.subdirectory != "." else "Raíz")
            child.setText(2, destination)
            child.setText(3, format_size(move.size))
            child.setData(0, Qt.ItemDataRole.UserRole, move)
            
            parent.addChild(child)
        
        if len(moves) <= 20:
            parent.setExpanded(True)
    
    # === EVENTOS ===
    
    def _on_file_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Abre el archivo con doble clic"""
        move = item.data(0, Qt.ItemDataRole.UserRole)
        if not move:
            return
        
        from .dialog_utils import open_file
        open_file(move.source_path, self)
    
    def _show_context_menu(self, position):
        """Muestra menú contextual"""
        item = self.files_tree.itemAt(position)
        if not item:
            return
        
        move = item.data(0, Qt.ItemDataRole.UserRole)
        if not move:
            return
        
        menu = QMenu(self)
        
        # Abrir archivo
        open_file_action = menu.addAction("Abrir archivo")
        open_file_action.triggered.connect(lambda: self._open_file(move.source_path))
        
        # Abrir carpeta origen
        open_source_action = menu.addAction("Abrir carpeta origen")
        open_source_action.triggered.connect(lambda: self._open_folder(move.source_path.parent))
        
        # Abrir carpeta destino
        if move.target_path.parent.exists():
            open_target_action = menu.addAction("Abrir carpeta destino")
            open_target_action.triggered.connect(lambda: self._open_folder(move.target_path.parent))
        
        menu.addSeparator()
        
        # Ver detalles
        details_action = menu.addAction("Ver detalles completos")
        details_action.triggered.connect(lambda: self._show_file_details(move))
        
        menu.exec(self.files_tree.viewport().mapToGlobal(position))
    
    def _open_file(self, file_path: Path):
        """Abre un archivo"""
        from .dialog_utils import open_file
        open_file(file_path, self)
    
    def _open_folder(self, folder_path: Path):
        """Abre una carpeta"""
        from .dialog_utils import open_folder
        open_folder(folder_path, self)
    
    def _show_file_details(self, move):
        """Muestra detalles del archivo"""
        from .dialog_utils import show_file_details_dialog
        
        additional_info = {
            'original_name': move.original_name,
            'new_name': move.new_name,
            'file_type': move.file_type,
            'target_path': move.target_path,
            'conflict': move.has_conflict,
            'sequence': move.sequence if move.has_conflict else None,
            'metadata': {
                'Subdirectorio origen': move.subdirectory,
            }
        }
        
        if move.target_folder:
            additional_info['metadata']['Carpeta destino'] = move.target_folder
        
        show_file_details_dialog(move.source_path, self, additional_info)
    
    def accept(self):
        """Acepta el diálogo y construye el plan"""
        # Pasar el analysis completo + parámetros por separado
        self.accepted_plan = {
            'analysis': self.analysis,  # Ya es OrganizationAnalysisResult dataclass
            'cleanup_empty_dirs': self.is_cleanup_enabled(),
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        super().accept()
