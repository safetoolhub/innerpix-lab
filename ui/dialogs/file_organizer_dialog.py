"""
Diálogo de Organización de Archivos
Permite elegir el tipo de organización en tiempo real y ver los resultados dinámicamente
"""
from pathlib import Path
from collections import defaultdict
from typing import Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QDialogButtonBox, QCheckBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QComboBox, QPushButton, QFrame,
    QApplication, QMenu, QWidget, QProgressBar, QTabWidget, QRadioButton, QButtonGroup,
    QStackedWidget, QScrollArea
)
from PyQt6.QtGui import QColor, QFont, QCursor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread

from config import Config
from utils.format_utils import format_size
from utils.date_utils import select_best_date_from_file, get_all_metadata_from_file
from utils.file_utils import is_whatsapp_file
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from utils.logger import get_logger
from services.file_organizer_service import FileOrganizerService, OrganizationType
from services.result_types import OrganizationAnalysisResult
from ui.workers import FileOrganizerAnalysisWorker
from .base_dialog import BaseDialog


class FileOrganizerDialog(BaseDialog):
    """
    Diálogo profesional para organización de archivos con:
    - Selector de tipo de organización en tiempo real
    - Análisis dinámico al cambiar tipo
    - UX profesional siguiendo DesignSystem
    - Sin emojis, usando Icon Manager
    """
    
    # Constantes para carga progresiva
    INITIAL_LOAD = 100
    LOAD_INCREMENT = 100
    WARNING_THRESHOLD = 500

    def __init__(self, initial_analysis: OrganizationAnalysisResult, parent=None):
        super().__init__(parent)
        self.logger = get_logger("FileOrganizationDialog")
        
        # Datos principales
        self.root_directory = Path(initial_analysis.root_directory)
        self.initial_analysis = initial_analysis  # Guardar para referencia pero no usar inicialmente
        self.analysis = None  # Empezar sin análisis hasta que el usuario seleccione
        self.current_organization_type = None  # Sin tipo seleccionado inicialmente
        self.accepted_plan = None
        
        # Datos de archivos
        self.all_moves = []  # Empezar vacío
        self.filtered_moves = []  # Empezar vacío hasta que el usuario seleccione
        self.loaded_count = 0
        
        # Worker para análisis
        self.worker: Optional[FileOrganizerAnalysisWorker] = None
        self.is_analyzing = False
        
        # Flag para evitar disparar eventos durante la construcción de la UI
        self.ui_initialized = False
        
        # Referencia a la barra de paginación
        self.pagination_bar = None
        
        self.init_ui()

    def init_ui(self):
        """Inicializa la interfaz"""
        self.setWindowTitle("Organización de Archivos")
        self.setModal(True)
        self.resize(1400, 800)
        
        # Inicializar progress bar temprano para evitar crashes si se disparan señales durante la construcción de la UI
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_20)
        
        # === HEADER COMPACTO CON MÉTRICAS ===
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='folder-cog',
            title='Organización de Archivos',
            description='Elige cómo organizar tus archivos',
            metrics=[
                {
                    'label': 'Total',
                    'value': str(self.analysis.items_count) if self.analysis else '0'
                },
                {
                    'label': 'Organizar',
                    'value': str(self.analysis.files_to_move) if self.analysis else '0'
                },
                {
                    'label': 'Tamaño',
                    'value': format_size(self.analysis.bytes_total) if self.analysis else '0 B'
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
        
        # === SELECTOR DE ESTRATEGIA ===
        self.selection_ui = self._create_selection_ui()
        content_layout.addWidget(self.selection_ui)
        
        # === INFORMACIÓN DE CARPETAS ===
        self.folders_info_widget = self._create_folders_info()
        if self.folders_info_widget:
            content_layout.addWidget(self.folders_info_widget)
        
        # === BARRA DE FILTROS UNIFICADA ===
        self.filter_bar = self._create_filter_bar()
        content_layout.addWidget(self.filter_bar)
        
        # === TREE WIDGET ===
        self.files_tree = self._create_tree_widget()
        content_layout.addWidget(self.files_tree, 1)  # Stretch factor 1
        
        # === BARRA DE CARGA PROGRESIVA ===
        self.pagination_bar = self._create_progressive_loading_bar(
            on_load_more=self._load_more_items,
            on_load_all=self._load_all_items
        )
        content_layout.addWidget(self.pagination_bar)

        # === PROGRESS BAR (inicialmente oculto) ===
        # self.progress_bar ya inicializado al principio
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
        
        # NO actualizar vista inicial - dejar vacío hasta que el usuario seleccione
        # self._update_all_ui()
        
        # Marcar UI como inicializada para permitir eventos
        self.ui_initialized = True
        
        # Inicializar la selección de estrategia y las opciones (ahora que la UI está lista)
        self._initialize_strategy_selection()

    def _create_selection_ui(self) -> QWidget:
        """Crea la nueva interfaz de selección con Estrategia + Opciones Contextuales"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # 1. Selector de Estrategia (Tarjetas Horizontales)
        strategy_container = QWidget()
        strategy_layout = QHBoxLayout(strategy_container)
        strategy_layout.setContentsMargins(0, 0, 0, 0)
        strategy_layout.setSpacing(DesignSystem.SPACE_12)
        
        # Definir estrategias
        self.strategies = {
            'date': {
                'icon': 'calendar-month', 
                'label': 'Por Fecha', 
                'tooltip': 'Organizar archivos cronológicamente (Año, Mes...)',
                'types': [OrganizationType.BY_MONTH, OrganizationType.BY_YEAR, OrganizationType.BY_YEAR_MONTH]
            },
            'type': {
                'icon': 'image', 
                'label': 'Por Tipo', 
                'tooltip': 'Agrupar por tipo de archivo (Fotos, Videos...)',
                'types': [OrganizationType.BY_TYPE]
            },
            'source': {
                'icon': 'devices', 
                'label': 'Por Fuente', 
                'tooltip': 'Agrupar por dispositivo de origen (Cámara, WhatsApp...)',
                'types': [OrganizationType.BY_SOURCE]
            },
            'cleanup': {
                'icon': 'folder-open', 
                'label': 'Todo junto', 
                'tooltip': 'Mover todo a la raíz y eliminar carpetas vacías',
                'types': [OrganizationType.TO_ROOT]
            }
        }
        
        self.strategy_cards = {}
        
        # Crear tarjetas
        for key, data in self.strategies.items():
            card = self._create_strategy_card(key, data)
            strategy_layout.addWidget(card)
            self.strategy_cards[key] = card
            
        layout.addWidget(strategy_container)
        
        # 2. Panel de Opciones Contextuales (Stacked Widget)
        self.settings_stack = QStackedWidget()
        self.settings_stack.setStyleSheet(f"""
            QStackedWidget {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
        """)
        
        # Página 0: Configuración de Fecha
        self.date_settings_page = self._create_date_settings_page()
        self.settings_stack.addWidget(self.date_settings_page)
        
        # Página 1: Configuración de Tipo
        self.type_settings_page = self._create_type_source_settings_page("type")
        self.settings_stack.addWidget(self.type_settings_page)
        
        # Página 2: Configuración de Fuente
        self.source_settings_page = self._create_type_source_settings_page("source")
        self.settings_stack.addWidget(self.source_settings_page)
        
        # Página 3: Configuración de Limpieza
        self.cleanup_settings_page = self._create_cleanup_settings_page()
        self.settings_stack.addWidget(self.cleanup_settings_page)
        
        layout.addWidget(self.settings_stack)
        
        layout.addWidget(self.settings_stack)
        
        return container

    def _create_strategy_card(self, key: str, data: dict) -> QFrame:
        """Crea una tarjeta de estrategia seleccionable"""
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setProperty("strategy_key", key)
        card.setToolTip(data['tooltip'])
        
        # Layout de la tarjeta
        layout = QVBoxLayout(card)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icono
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, data['icon'], size=DesignSystem.ICON_SIZE_LG, color=DesignSystem.COLOR_TEXT_SECONDARY)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_label)
        
        # Etiqueta
        text_label = QLabel(data['label'])
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; color: {DesignSystem.COLOR_TEXT}; border: none;")
        layout.addWidget(text_label)
        
        # Guardar referencias para actualizar estilos
        card.icon_label = icon_label
        card.text_label = text_label
        
        # Evento de click
        card.mousePressEvent = lambda e: self._on_strategy_clicked(key)
        
        return card

    def _create_date_settings_page(self) -> QWidget:
        """Crea la página de opciones para organización por fecha"""
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(DesignSystem.SPACE_20, DesignSystem.SPACE_16, DesignSystem.SPACE_20, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        label = QLabel("Granularidad:")
        label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT}; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};")
        
        self.date_granularity_combo = QComboBox()
        self.date_granularity_combo.addItems(["Por Mes (YYYY_MM)", "Por Año (YYYY)", "Por Año/Mes (YYYY/MM)"])
        self.date_granularity_combo.setMinimumWidth(200)
        self.date_granularity_combo.setStyleSheet(DesignSystem.get_combobox_style())
        self.date_granularity_combo.currentIndexChanged.connect(lambda: self._on_option_changed(None))
        
        # Checkboxes para opciones combinadas
        self.chk_date_source = QCheckBox("Agrupar también por Fuente (WhatsApp, etc.)")
        self.chk_date_source.setToolTip("Crea subcarpetas por fuente dentro de cada carpeta de fecha")
        self.chk_date_source.stateChanged.connect(lambda: self._on_option_changed(None))
        
        self.chk_date_type = QCheckBox("Agrupar también por Tipo (Fotos/Videos)")
        self.chk_date_type.setToolTip("Crea subcarpetas Fotos y Videos dentro de cada carpeta de fecha")
        self.chk_date_type.stateChanged.connect(lambda: self._on_option_changed(None))

        layout.addWidget(label)
        layout.addWidget(self.date_granularity_combo)
        layout.addWidget(self.chk_date_source)
        layout.addWidget(self.chk_date_type)
        layout.addStretch()
        
        return page

    def _create_type_source_settings_page(self, context: str) -> QWidget:
        """Crea la página de opciones para organización por tipo o fuente"""
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(DesignSystem.SPACE_20, DesignSystem.SPACE_16, DesignSystem.SPACE_20, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        label = QLabel("Agrupación secundaria:")
        label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT}; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};")
        
        combo = QComboBox()
        combo.addItems(["Ninguna", "Por Mes (YYYY_MM)", "Por Año (YYYY)", "Por Año/Mes (YYYY/MM)"])
        combo.setMinimumWidth(200)
        combo.setStyleSheet(DesignSystem.get_combobox_style())
        combo.currentIndexChanged.connect(lambda: self._on_option_changed(None))
        
        if context == "type":
            self.type_secondary_combo = combo
        else:
            self.source_secondary_combo = combo
            
        layout.addWidget(label)
        layout.addWidget(combo)
        layout.addStretch()
        
        return page

    def _create_cleanup_settings_page(self) -> QWidget:
        """Crea la página de opciones para limpieza"""
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(DesignSystem.SPACE_20, DesignSystem.SPACE_16, DesignSystem.SPACE_20, DesignSystem.SPACE_16)
        
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, "information", size=DesignSystem.ICON_SIZE_MD, color=DesignSystem.COLOR_PRIMARY)
        
        text_label = QLabel("Esta opción moverá todos los archivos al directorio raíz y eliminará las carpetas vacías.")
        text_label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        
        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addStretch()
        
        return page

    def _initialize_strategy_selection(self):
        """Inicializa la selección de estrategia y las opciones contextuales."""
        # Determinar la estrategia inicial basada en initial_analysis o un valor por defecto
        initial_strategy_key = 'date' # Default
        if self.initial_analysis:
            # organization_type es un string, comparar con .value de los enums
            org_type_str = self.initial_analysis.organization_type
            
            # Convertir tipos de fecha a enum para comparación
            date_types = [t.value for t in self.strategies['date']['types']]
            
            if org_type_str in date_types:
                initial_strategy_key = 'date'
                # Set initial combo box value for date granularity
                if org_type_str == OrganizationType.BY_MONTH.value:
                    self.date_granularity_combo.setCurrentIndex(0)
                elif org_type_str == OrganizationType.BY_YEAR.value:
                    self.date_granularity_combo.setCurrentIndex(1)
                elif org_type_str == OrganizationType.BY_YEAR_MONTH.value:
                    self.date_granularity_combo.setCurrentIndex(2)
                
                # Set initial checkbox states
                self.chk_date_source.setChecked(self.initial_analysis.group_by_source)
                self.chk_date_type.setChecked(self.initial_analysis.group_by_type)

            elif org_type_str == OrganizationType.BY_TYPE.value:
                initial_strategy_key = 'type'
                # Set initial combo box value for secondary grouping
                if self.initial_analysis.date_grouping_type == 'month':
                    self.type_secondary_combo.setCurrentIndex(1)
                elif self.initial_analysis.date_grouping_type == 'year':
                    self.type_secondary_combo.setCurrentIndex(2)
                elif self.initial_analysis.date_grouping_type == 'year_month':
                    self.type_secondary_combo.setCurrentIndex(3)
                else:
                    self.type_secondary_combo.setCurrentIndex(0) # Ninguna

            elif org_type_str == OrganizationType.BY_SOURCE.value:
                initial_strategy_key = 'source'
                # Set initial combo box value for secondary grouping
                if self.initial_analysis.date_grouping_type == 'month':
                    self.source_secondary_combo.setCurrentIndex(1)
                elif self.initial_analysis.date_grouping_type == 'year':
                    self.source_secondary_combo.setCurrentIndex(2)
                elif self.initial_analysis.date_grouping_type == 'year_month':
                    self.source_secondary_combo.setCurrentIndex(3)
                else:
                    self.source_secondary_combo.setCurrentIndex(0) # Ninguna

            elif org_type_str == OrganizationType.TO_ROOT.value:
                initial_strategy_key = 'cleanup'
        
        # Simulate a click on the initial strategy card to set up UI and trigger analysis
        self._on_strategy_clicked(initial_strategy_key)


    def _on_strategy_clicked(self, key: str):
        """Maneja el click en una tarjeta de estrategia"""
        # Actualizar estilos de tarjetas
        for k, card in self.strategy_cards.items():
            is_selected = (k == key)
            
            if is_selected:
                bg_color = DesignSystem.COLOR_PRIMARY_LIGHT # Más sutil
                border_color = DesignSystem.COLOR_PRIMARY
                text_color = DesignSystem.COLOR_PRIMARY
                icon_color = DesignSystem.COLOR_PRIMARY
                border_style = f"1px solid {border_color}"
            else:
                bg_color = "transparent" # Sin fondo por defecto
                border_color = "transparent"
                text_color = DesignSystem.COLOR_TEXT
                icon_color = DesignSystem.COLOR_TEXT_SECONDARY
                border_style = "1px solid transparent" # Mantener borde transparente para evitar saltos
            
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border: {border_style};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                }}
            """)
            
            # Asegurar que el label no tenga borde
            card.text_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; color: {text_color}; border: none; background: transparent;")
            icon_manager.set_label_icon(card.icon_label, self.strategies[k]['icon'], size=DesignSystem.ICON_SIZE_LG, color=icon_color)

        # Cambiar página del stack
        stack_index = 0
        if key == 'date': stack_index = 0
        elif key == 'type': stack_index = 1
        elif key == 'source': stack_index = 2
        elif key == 'cleanup': stack_index = 3
        
        self.settings_stack.setCurrentIndex(stack_index)
        
        # Trigger update logic
        self._on_option_changed(None)

    def _on_option_changed(self, new_type_or_none):
        """Maneja cambios en cualquier opción (tipo o checkboxes)"""
        if not self.ui_initialized:
            return

        # Recopilar estado actual basado en la página activa del stack
        stack_index = self.settings_stack.currentIndex()
        
        org_type = OrganizationType.BY_MONTH # Default
        group_by_source = False
        group_by_type = False
        date_grouping_type = None
        
        if stack_index == 0: # Date Strategy
            # Leer granularidad
            granularity_index = self.date_granularity_combo.currentIndex()
            if granularity_index == 0:
                org_type = OrganizationType.BY_MONTH
            elif granularity_index == 1:
                org_type = OrganizationType.BY_YEAR
            elif granularity_index == 2:
                org_type = OrganizationType.BY_YEAR_MONTH
                
            # Leer checkboxes
            group_by_source = self.chk_date_source.isChecked()
            group_by_type = self.chk_date_type.isChecked()
            
        elif stack_index == 1: # Type Strategy
            org_type = OrganizationType.BY_TYPE
            # Leer agrupación secundaria
            sec_index = self.type_secondary_combo.currentIndex()
            if sec_index == 1: date_grouping_type = 'month'
            elif sec_index == 2: date_grouping_type = 'year'
            elif sec_index == 3: date_grouping_type = 'year_month'
            
        elif stack_index == 2: # Source Strategy
            org_type = OrganizationType.BY_SOURCE
            # Leer agrupación secundaria
            sec_index = self.source_secondary_combo.currentIndex()
            if sec_index == 1: date_grouping_type = 'month'
            elif sec_index == 2: date_grouping_type = 'year'
            elif sec_index == 3: date_grouping_type = 'year_month'
            
        elif stack_index == 3: # Cleanup Strategy
            org_type = OrganizationType.TO_ROOT
            
        self.current_organization_type = org_type
        
        self.logger.info(f"Configuración cambiada: Tipo={self.current_organization_type.value}, "
                         f"Source={group_by_source}, Type={group_by_type}, DateGrouping={date_grouping_type}")
        
        self._start_analysis(self.current_organization_type, group_by_source, group_by_type, date_grouping_type)

    def _start_analysis(self, org_type: OrganizationType, group_by_source=False, group_by_type=False, date_grouping_type: Optional[str] = None):
        """Inicia análisis en background"""
        if self.is_analyzing and self.worker and self.worker.isRunning():
            # Cancelar worker anterior si es posible o esperar
            # Por simplicidad, bloqueamos nueva solicitud si ya hay una (pero idealmente deberíamos cancelar)
            # En este caso, permitiremos que termine y el usuario tendrá que esperar un poco
            self.logger.warning("Ya hay un análisis en curso")
            return
        
        self.is_analyzing = True
        self._set_ui_loading_state(True)
        
        # Crear y configurar worker
        self.worker = FileOrganizerAnalysisWorker(
            directory=self.root_directory,
            organization_type=org_type,
            group_by_source=group_by_source,
            group_by_type=group_by_type,
            date_grouping_type=date_grouping_type
        )
        self.worker.finished.connect(self._on_analysis_finished)
        self.worker.progress_update.connect(self._on_analysis_progress)
        self.worker.error.connect(self._on_analysis_error)
        
        # Iniciar
        self.worker.start()
    
    def _on_analysis_finished(self, result: OrganizationAnalysisResult):
        """Maneja la finalización del análisis"""
        self.logger.info(f"Análisis completado: {result.items_count} archivos (tipo: {result.organization_type})")
        self.analysis = result
        
        # Actualizar chip de estado
        self._update_filter_chip(
            status_chip=self.status_chip,
            filtered_count=len(result.move_plan),
            total_count=len(result.move_plan),
            is_files_mode=True
        )
        
        # Actualizar opciones de filtros basadas en los datos
        self._update_filter_options()
        
        self.filtered_moves = list(result.move_plan)
        self.current_page = 0
        
        # IMPORTANTE: Establecer is_analyzing=False ANTES de actualizar UI
        # para que el botón OK se habilite correctamente
        self.is_analyzing = False
        
        self._set_ui_loading_state(False)
        self._update_all_ui()
    
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
        # NO actualizar ok_button aquí - se hace en _update_ok_button() con datos frescos
        
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
        
        # Actualizar datos de archivos
        if self.analysis:
            self.all_moves = list(self.analysis.move_plan)
            self.filtered_moves = list(self.analysis.move_plan)
            self._load_initial_items()
        
        # Actualizar botón OK
        self._update_ok_button()
        
        # Re-aplicar estilos a las cards de selección
        # Actualizar botón OK
        self._update_ok_button()
    

    
    def _update_header_metrics(self):
        """Actualiza las métricas del header compacto"""
        # Buscar y actualizar los QLabel de las métricas existentes
        main_layout = self.header_frame.layout()
        if not main_layout:
            return

        # El layout tiene: left_container, spacer, metrics_container
        # metrics_container es el último QHBoxLayout
        metrics_layout = None
        for i in range(main_layout.count() - 1, -1, -1):  # Buscar desde el final
            item = main_layout.itemAt(i)
            if item and item.layout() and isinstance(item.layout(), QHBoxLayout):
                metrics_layout = item.layout()
                break
        
        if not metrics_layout:
            return
        
        # Actualizar cada métrica (son QWidget con QVBoxLayout conteniendo value_label y label_widget)
        # Datos de las métricas
        if not self.analysis:
            metrics_data = ["0", "0", "0 B"]
        else:
            metrics_data = [
                str(self.analysis.items_count),
                str(self.analysis.files_to_move),
                format_size(self.analysis.bytes_total)
            ]
        
        for idx, new_value in enumerate(metrics_data):
            if idx < metrics_layout.count():
                metric_widget = metrics_layout.itemAt(idx).widget()
                if metric_widget and metric_widget.layout():
                    # El primer hijo del layout es el value_label
                    value_label = metric_widget.layout().itemAt(0).widget()
                    if value_label and isinstance(value_label, QLabel):
                        value_label.setText(new_value)
    
    def _get_icon_name_for_type(self, org_type: OrganizationType) -> str:
        """Devuelve el nombre del icono para un tipo de organización"""
        icon_map = {
            OrganizationType.TO_ROOT: "folder-open",
            OrganizationType.BY_MONTH: "calendar-month",
            OrganizationType.BY_YEAR: "calendar-today",
            OrganizationType.BY_YEAR_MONTH: "calendar-range",
            OrganizationType.BY_TYPE: "image",
            OrganizationType.BY_SOURCE: "devices"
        }
        return icon_map.get(org_type, "folder")

    

    
    def _create_folders_info(self) -> Optional[QWidget]:
        """Crea sección de información de carpetas a crear con estilo Material Design"""
        # Inicializar atributos siempre
        self.folders_info_container = None
        self.folders_info_label = None
        
        if not self.analysis or not self.analysis.folders_to_create:
            return None
        
        self.folders_info_container = QFrame()
        self.folders_info_container.setStyleSheet(f"""
            QFrame {{ 
                background-color: {DesignSystem.COLOR_INFO_BG}; 
                border: 1px solid {DesignSystem.COLOR_INFO};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px;
            }}
        """)
        
        layout = QHBoxLayout(self.folders_info_container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        # Icono
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, 'folder-multiple', color=DesignSystem.COLOR_INFO, size=DesignSystem.ICON_SIZE_MD)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        
        self.folders_info_label = QLabel()
        self.folders_info_label.setWordWrap(True)
        self.folders_info_label.setTextFormat(Qt.TextFormat.RichText)
        self.folders_info_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: #055160; /* Darker info color for text readability */
        """)
        layout.addWidget(self.folders_info_label, 1)
        
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
    
    def _create_filter_bar(self) -> QWidget:
        """Crea barra de filtros unificada usando método base"""
        # Diccionario de etiquetas
        labels = {
            'search': 'Buscar por nombre',
            'size': 'Mínimo tamaño',
            'groups': 'Archivos seleccionados',
            'category': 'Tipo de archivo',
            'status': 'Estado'
        }
        
        # Configuración de filtros expandibles
        expandable_filters = [
            {
                'id': 'category',
                'type': 'combo',
                'label': labels['category'],
                'tooltip': 'Filtrar por tipo de archivo (Fotos/Videos)',
                'options': ["Todos"],  # Se actualiza dinámicamente
                'on_change': lambda idx: self._apply_filters(),
                'default_index': 0,
                'min_width': 120
            },
            {
                'id': 'status',
                'type': 'combo',
                'label': labels['status'],
                'tooltip': 'Filtrar por estado (Con/Sin conflictos)',
                'options': ["Todos"],  # Se actualiza dinámicamente
                'on_change': lambda idx: self._apply_filters(),
                'default_index': 0,
                'min_width': 150
            }
        ]
        
        # Crear barra unificada
        filter_bar = self._create_unified_filter_bar(
            on_search_changed=self._apply_filters,
            on_size_filter_changed=lambda idx: self._apply_filters(),
            expandable_filters=expandable_filters,
            is_files_mode=True,
            labels=labels
        )
        
        # Guardar referencias a componentes
        self.search_input = filter_bar.search_input
        self.filter_combo = filter_bar.size_filter_combo
        self.status_chip = filter_bar.status_chip
        self.expand_button = filter_bar.expand_btn
        self.category_combo = filter_bar.filter_widgets.get('category')
        self.status_combo = filter_bar.filter_widgets.get('status')
        
        return filter_bar
    
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
                padding: {DesignSystem.SPACE_4}px;
            }}
            QTreeWidget::item {{
                border: none;
                outline: none;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_4}px;
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};
            }}
            QTreeWidget::item:hover {{
                background-color: {DesignSystem.COLOR_BG_2};
            }}
            QTreeWidget::item:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT};
            }}
            QHeaderView::section {{
                background-color: {DesignSystem.COLOR_BG_1};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_8}px;
                border: none;
                border-bottom: 2px solid {DesignSystem.COLOR_BORDER};
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
            }}
        """)
        tree.setToolTip(
            "Doble clic en archivo para abrirlo\n"
            "Clic derecho para ver detalles y opciones"
        )
        
        return tree
    
    def _configure_tree_columns(self, tree: QTreeWidget):
        """Configura las columnas del tree de forma estandarizada"""
        # Estándar: Nombre Original, Nuevo Nombre, Fecha, Origen, Tamaño
        headers = ["Nombre Original", "Nuevo Nombre", "Fecha", "Origen", "Tamaño"]
        tree.setHeaderLabels(headers)
        
        # Ajustar anchos
        tree.setColumnWidth(0, 400) # Nombre Original (más ancho para path completo)
        tree.setColumnWidth(1, 300) # Nuevo Nombre
        tree.setColumnWidth(2, 160) # Fecha
        tree.setColumnWidth(3, 180) # Origen
        tree.setColumnWidth(4, 80)  # Tamaño
    
    def _create_options_group(self) -> QFrame:
        """Crea grupo de opciones con sección de seguridad + opción de limpieza específica."""
        from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
        from ui.styles.design_system import DesignSystem
        from ui.styles.icons import icon_manager
        
        # Crear contenedor principal con estilo consistente
        container = QFrame()
        container.setObjectName("options-container")
        container.setStyleSheet(f"""
            QFrame#options-container {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_16}px;
            }}
        """)
        
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(int(DesignSystem.SPACE_8))
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # === Fila 1: Opciones de seguridad + cleanup (todo inline) ===
        options_row = QHBoxLayout()
        options_row.setSpacing(int(DesignSystem.SPACE_12))
        options_row.setContentsMargins(0, 0, 0, 0)
        
        # Label "Opciones:"
        options_label = QLabel("Opciones:")
        options_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        options_row.addWidget(options_label)
        
        # Obtener configuración de backup
        from utils.settings_manager import settings_manager
        from config import Config
        
        backup_dir = settings_manager.get_backup_directory(Config.DEFAULT_BACKUP_DIR)
        backup_path_str = str(backup_dir) if backup_dir else str(Config.DEFAULT_BACKUP_DIR)
        
        # Chip de backup
        backup_checked = settings_manager.get_auto_backup_enabled()
        
        self.backup_checkbox = self._create_inline_chip_checkbox(
            icon_name='content-save',
            label="Crear backup antes de mover",
            checked=backup_checked,
            tooltip=f"Crea una copia de seguridad antes de mover archivos.\n"
                    f"Recomendado para operaciones destructivas.\n\n"
                    f"Carpeta de backups: {backup_path_str}\n\n"
                    f"Puedes cambiar la carpeta desde Configuración."
        )
        options_row.addWidget(self.backup_checkbox)
        
        # Chip de dry-run
        dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, False)
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() in ('true', '1', 'yes')
        
        self.dry_run_checkbox = self._create_inline_chip_checkbox(
            icon_name='eye',
            label="Modo simulación",
            checked=bool(dry_run_default),
            tooltip="Simula la operación sin mover archivos realmente.\n"
                    "Útil para verificar qué archivos se moverían.\n\n"
                    "Al activar modo simulación, el backup se deshabilita\n"
                    "automáticamente ya que no se realizarán cambios reales."
        )
        options_row.addWidget(self.dry_run_checkbox)
        
        # Separador visual (línea vertical)
        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        options_row.addWidget(separator)
        
        # Chip de cleanup carpetas vacías (específico de organización)
        self.cleanup_checkbox = self._create_inline_chip_checkbox(
            icon_name='folder-remove',
            label="Limpiar carpetas vacías",
            checked=False,  # Default deshabilitado para ser conservador
            tooltip="Elimina automáticamente las carpetas que queden vacías\n"
                    "después de mover los archivos durante la organización.\n\n"
                    "Solo aplica a carpetas dentro de la ruta seleccionada."
        )
        options_row.addWidget(self.cleanup_checkbox)
        
        options_row.addStretch()
        container_layout.addLayout(options_row)
        
        # === Fila 2: Ruta de backup (siempre presente para mantener tamaño fijo) ===
        # Truncar path si es muy largo
        max_display_len = 60
        display_path = backup_path_str
        if len(display_path) > max_display_len:
            display_path = "..." + display_path[-(max_display_len - 3):]
        
        # Contenedor para la ruta (mantiene espacio fijo)
        self._backup_path_widget = QWidget()
        # Reservar espacio incluso cuando está oculto para evitar saltos en la interfaz
        sp = self._backup_path_widget.sizePolicy()
        if hasattr(sp, 'setRetainSizeWhenHidden'):
            sp.setRetainSizeWhenHidden(True)
            self._backup_path_widget.setSizePolicy(sp)

        path_layout = QHBoxLayout(self._backup_path_widget)
        path_layout.setSpacing(int(DesignSystem.SPACE_6))
        path_layout.setContentsMargins(0, 0, 0, 0)
        
        self._backup_folder_icon = QLabel()
        icon_manager.set_label_icon(
            self._backup_folder_icon, 'folder', 
            size=DesignSystem.ICON_SIZE_SM, 
            color=DesignSystem.COLOR_TEXT_SECONDARY
        )
        path_layout.addWidget(self._backup_folder_icon)
        
        self._backup_path_label = QLabel(f"Carpeta donde se guardarán los archivos movidos: {display_path}")
        self._backup_path_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        self._backup_path_label.setToolTip(
            f"Ruta completa: {backup_path_str}\n\n"
            f"Puedes cambiar esta carpeta desde Configuración."
        )
        path_layout.addWidget(self._backup_path_label)
        path_layout.addStretch()
        
        container_layout.addWidget(self._backup_path_widget)
        
        # Actualizar visibilidad inicial (solo contenido, no espacio)
        self._update_backup_path_visibility(self.is_backup_enabled())
        
        # Configurar lógica de interacción dry-run/backup (actualiza visibilidad de ruta)
        self._setup_dry_run_backup_logic()
        
        return container
    
    def _create_action_buttons(self) -> QDialogButtonBox:
        """Crea botones de acción con estilo Material Design"""
        # Determinar si el botón OK debe estar habilitado
        ok_enabled = bool(self.analysis and self.analysis.files_to_move > 0)
        
        if ok_enabled:
            size_formatted = format_size(self.analysis.bytes_to_move)
            ok_text = f"Organizar Archivos ({self.analysis.files_to_move} archivos, {size_formatted})"
        else:
            ok_text = "Selecciona una opción"
        
        buttons = self.make_ok_cancel_buttons(
            ok_text=ok_text,
            ok_enabled=ok_enabled,
            button_style='primary'
        )
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        
        return buttons
    
    def _update_ok_button(self):
        """Actualiza el texto y estado del botón OK"""
        if not hasattr(self, 'ok_button') or not self.ok_button:
            return
        
        ok_enabled = self.analysis.files_to_move > 0
        final_enabled = ok_enabled and not self.is_analyzing
        
        self.ok_button.setEnabled(final_enabled)
        
        if ok_enabled:
            size_formatted = format_size(self.analysis.bytes_to_move)
            ok_text = f"Organizar Archivos ({self.analysis.files_to_move} archivos, {size_formatted})"
        else:
            ok_text = "Sin archivos para organizar"
        
        self.ok_button.setText(ok_text)
    
    # === FILTROS ===
    
    def _update_filter_options(self):
        """Actualiza las opciones de los filtros basándose en los datos actuales"""
        if not self.analysis or not self.analysis.move_plan:
            return

        # 1. Categorías
        type_map = {'PHOTO': 'Fotos', 'VIDEO': 'Videos'}
        categories = set()
        for move in self.analysis.move_plan:
            categories.add(type_map.get(move.file_type, 'Otros'))
        
        current_cat = self.category_combo.currentText()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItems(["Todos"] + sorted(list(categories)))
        if current_cat in ["Todos"] + sorted(list(categories)):
            self.category_combo.setCurrentText(current_cat)
        else:
            self.category_combo.setCurrentIndex(0)
        self.category_combo.blockSignals(False)



        # 3. Estado (Conflictos)
        has_conflicts = any(move.has_conflict for move in self.analysis.move_plan)
        
        current_status = self.status_combo.currentText()
        self.status_combo.blockSignals(True)
        self.status_combo.clear()
        status_items = ["Todos"]
        if has_conflicts:
            status_items.extend(["Con Conflictos", "Sin Conflictos"])
        
        self.status_combo.addItems(status_items)
        if current_status in status_items:
            self.status_combo.setCurrentText(current_status)
        else:
            self.status_combo.setCurrentIndex(0)
        self.status_combo.blockSignals(False)

    def _apply_filters(self):
        """Aplica filtros a la lista de movimientos"""
        if not self.analysis:
            return
            
        search_text = self.search_input.text().lower() if self.search_input else ""
        size_filter = self.filter_combo.currentText() if self.filter_combo else "Todos los tamaños"
        category_filter = self.category_combo.currentText() if self.category_combo else "Todos"
        status_filter = self.status_combo.currentText() if self.status_combo else "Todos"
        
        self.filtered_moves = []
        
        # Mapeo de categorías
        type_map = {'PHOTO': 'Fotos', 'VIDEO': 'Videos'}
        
        for move in self.all_moves:
            # Filtro de búsqueda
            if search_text and search_text not in move.original_name.lower():
                continue
            
            # Filtro por tamaño
            if not self._matches_size_filter(move.size, size_filter):
                continue
            
            # Filtro por Categoría
            if category_filter != "Todos":
                move_cat = type_map.get(move.file_type, 'Otros')
                if move_cat != category_filter:
                    continue
            
            # Filtro por Estado
            if status_filter == "Con Conflictos" and not move.has_conflict:
                continue
            if status_filter == "Sin Conflictos" and move.has_conflict:
                continue
            
            self.filtered_moves.append(move)
        
        # Reiniciar carga progresiva
        self._load_initial_items()
    
    def _matches_size_filter(self, file_size: int, filter_value: str) -> bool:
        """Verifica si el tamaño del archivo coincide con el filtro seleccionado."""
        if filter_value == "Todos los tamaños":
            return True
        
        mb = file_size / (1024 * 1024)
        
        if filter_value == "< 1 MB":
            return mb < 1
        elif filter_value == "1 - 10 MB":
            return 1 <= mb < 10
        elif filter_value == "10 - 100 MB":
            return 10 <= mb < 100
        elif filter_value == "> 100 MB":
            return mb >= 100
        
        return True
    
    def _clear_filters(self):
        """Limpia todos los filtros"""
        if self.search_input:
            self.search_input.clear()
        if self.filter_combo:
            self.filter_combo.setCurrentIndex(0)
        if self.category_combo:
            self.category_combo.setCurrentIndex(0)
        if self.status_combo:
            self.status_combo.setCurrentIndex(0)
    
    # ========================================================================
    # LÓGICA DE CARGA PROGRESIVA
    # ========================================================================
    
    def _load_initial_items(self):
        """Carga los items iniciales en el árbol."""
        self.loaded_count = 0
        self.files_tree.clear()
        
        # Reconfigurar columnas si cambió el tipo
        self._configure_tree_columns(self.files_tree)
        
        self._load_more_items()
    
    def _load_more_items(self):
        """Carga más items en el árbol."""
        if not self.filtered_moves:
            self._update_pagination_ui()
            return
            
        start = self.loaded_count
        end = min(start + self.LOAD_INCREMENT, len(self.filtered_moves))
        
        items_to_load = self.filtered_moves[start:end]
        
        # Poblar según tipo - para carga incremental, solo añadir archivos directamente
        org_type = self.current_organization_type
        
        # En la primera carga, crear la estructura de grupos
        if start == 0:
            if org_type == OrganizationType.TO_ROOT:
                self._populate_tree_to_root(self.filtered_moves)
            elif org_type in (OrganizationType.BY_MONTH, OrganizationType.BY_YEAR, OrganizationType.BY_YEAR_MONTH):
                self._populate_tree_by_temporal(self.filtered_moves)
            elif org_type in (OrganizationType.BY_TYPE, OrganizationType.BY_SOURCE):
                self._populate_tree_by_category(self.filtered_moves)
            self.loaded_count = len(self.filtered_moves)
        else:
            self.loaded_count = end
        
        self._update_pagination_ui()
    
    def _load_all_items(self):
        """Carga todos los items restantes."""
        from PyQt6.QtWidgets import QMessageBox
        
        if len(self.filtered_moves) > 1000:
            reply = QMessageBox.question(
                self,
                "Cargar todos los archivos",
                f"Hay {len(self.filtered_moves)} archivos. ¿Seguro que quieres cargarlos todos?\n"
                "Esto puede tardar y consumir memoria.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        while self.loaded_count < len(self.filtered_moves):
            self._load_more_items()
    
    def _update_pagination_ui(self):
        """Actualiza la UI de la barra de carga progresiva."""
        if self.pagination_bar and self.analysis:
            self._update_progressive_loading_ui(
                pagination_bar=self.pagination_bar,
                loaded_count=self.loaded_count,
                filtered_count=len(self.filtered_moves),
                total_count=len(self.all_moves),
                load_increment=self.LOAD_INCREMENT
            )
        
        # Actualizar chip de estado (independiente del loaded_count)
        self._update_filter_chip(
            status_chip=self.status_chip,
            filtered_count=len(self.filtered_moves),
            total_count=len(self.all_moves),
            loaded_count=self.loaded_count,
            is_files_mode=True
        )
    
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
        root_parent.setText(0, f"Raíz del directorio ({total_moves} archivos)")
        root_parent.setText(1, "") # Nuevo Nombre
        root_parent.setText(2, "") # Fecha
        root_parent.setText(3, "") # Origen
        root_parent.setText(4, format_size(total_size_all))
        
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
            subdir_node.setText(0, f"  Desde: {subdir} ({len(moves_in_subdir)} archivos)")
            subdir_node.setText(1, "")
            subdir_node.setText(2, "")
            subdir_node.setText(3, "")
            subdir_node.setText(4, format_size(total_size))
            
            subdir_font = QFont()
            subdir_font.setBold(True)
            subdir_node.setFont(0, subdir_font)
            subdir_node.setForeground(0, QColor(DesignSystem.COLOR_TEXT_SECONDARY))
            
            root_parent.addChild(subdir_node)
            
            # Archivos
            for move in sorted(moves_in_subdir, key=lambda m: m.original_name):
                child = QTreeWidgetItem()
                child.setText(0, f"    {move.source_path}")
                
                # Nuevo Nombre
                if move.has_conflict:
                    child.setText(1, move.new_name)
                    child.setForeground(1, QColor(DesignSystem.COLOR_ERROR))
                else:
                    child.setText(1, "Igual")
                    child.setForeground(1, QColor(DesignSystem.COLOR_TEXT_SECONDARY))
                
                # Fecha y Origen
                try:
                    file_metadata = get_all_metadata_from_file(move.source_path)
                    file_date, date_source = select_best_date_from_file(file_metadata)
                    if file_date:
                        child.setText(2, file_date.strftime("%Y-%m-%d %H:%M:%S"))
                        child.setText(3, date_source if date_source else "-")
                    else:
                        child.setText(2, "-")
                        child.setText(3, "-")
                except:
                    child.setText(2, "-")
                    child.setText(3, "-")

                child.setText(4, format_size(move.size))
                
                # Marcado visual de conflictos (texto en rojo)
                if move.has_conflict:
                    child.setForeground(0, QColor(DesignSystem.COLOR_ERROR))
                
                child.setData(0, Qt.ItemDataRole.UserRole, move)
                subdir_node.addChild(child)
            
            if len(moves_in_subdir) <= 20:
                subdir_node.setExpanded(True)
            
            if root_parent.childCount() % 10 == 0:
                QApplication.processEvents()
        
        root_parent.setExpanded(True)
    
    def _populate_tree_by_temporal(self, moves):
        """Poblar tree para organizaciones temporales (BY_MONTH, BY_YEAR, BY_YEAR_MONTH)"""
        # Agrupar por carpeta destino
        by_folder = defaultdict(list)
        for move in moves:
            folder = move.target_folder or "Sin fecha"
            by_folder[folder].append(move)
        
        for folder in sorted(by_folder.keys(), reverse=True):
            moves_in_folder = by_folder[folder]
            total_size = sum(m.size for m in moves_in_folder)
            
            parent = QTreeWidgetItem()
            parent.setText(0, f"{folder}/ ({len(moves_in_folder)} archivos)")
            parent.setText(1, "")
            parent.setText(2, "")
            parent.setText(3, "")
            parent.setText(4, format_size(total_size))
            
            parent_font = QFont()
            parent_font.setBold(True)
            parent.setFont(0, parent_font)
            parent.setForeground(0, QColor(DesignSystem.COLOR_PRIMARY))
            
            self.files_tree.addTopLevelItem(parent)
            
            for move in sorted(moves_in_folder, key=lambda m: m.original_name):
                child = QTreeWidgetItem()
                child.setText(0, f"  {move.source_path}")
                
                # Nuevo Nombre
                if move.has_conflict:
                    child.setText(1, move.new_name)
                    child.setForeground(1, QColor(DesignSystem.COLOR_ERROR))
                else:
                    child.setText(1, "Igual")
                    child.setForeground(1, QColor(DesignSystem.COLOR_TEXT_SECONDARY))
                
                # Fecha y Origen
                try:
                    file_metadata = get_all_metadata_from_file(move.source_path)
                    file_date, date_source = select_best_date_from_file(file_metadata)
                    if file_date:
                        child.setText(2, file_date.strftime("%Y-%m-%d %H:%M:%S"))
                        child.setText(3, date_source if date_source else "-")
                    else:
                        child.setText(2, "Sin fecha")
                        child.setText(3, "-")
                except Exception:
                    child.setText(2, "Error")
                    child.setText(3, "-")
                
                child.setText(4, format_size(move.size))
                
                # Marcado visual de conflictos (texto en rojo)
                if move.has_conflict:
                    child.setForeground(0, QColor(DesignSystem.COLOR_ERROR))
                
                child.setData(0, Qt.ItemDataRole.UserRole, move)
                
                parent.addChild(child)
            
            if len(moves_in_folder) <= 20:
                parent.setExpanded(True)
            
            if self.files_tree.topLevelItemCount() % 10 == 0:
                QApplication.processEvents()
    
    def _populate_tree_by_category(self, moves):
        """Poblar tree para organizaciones por categoría (BY_TYPE, BY_SOURCE)"""
        # Agrupar por carpeta destino (target_folder contiene el tipo o fuente)
        by_category = defaultdict(list)
        for move in moves:
            category = move.target_folder or "Sin categoría"
            by_category[category].append(move)
        
        # Ordenar categorías: primero las conocidas, luego "Unknown" al final
        def category_sort_key(cat):
            if cat == "Unknown":
                return (1, cat)
            return (0, cat)
        
        for category in sorted(by_category.keys(), key=category_sort_key):
            moves_in_category = by_category[category]
            total_size = sum(m.size for m in moves_in_category)
            
            parent = QTreeWidgetItem()
            parent.setText(0, f"{category}/ ({len(moves_in_category)} archivos)")
            parent.setText(1, "")
            parent.setText(2, "")
            parent.setText(3, "")
            parent.setText(4, format_size(total_size))
            
            parent_font = QFont()
            parent_font.setBold(True)
            parent.setFont(0, parent_font)
            
            # Colores especiales para categorías conocidas
            if category == "WhatsApp":
                parent.setForeground(0, QColor("#25d366"))  # Verde WhatsApp
            elif category in ("iPhone", "Android"):
                parent.setForeground(0, QColor("#2196f3"))  # Azul dispositivos
            elif category in ("Camera", "Scanner"):
                parent.setForeground(0, QColor("#ff9800"))  # Naranja cámaras
            elif category == "Screenshot":
                parent.setForeground(0, QColor("#9c27b0"))  # Púrpura screenshots
            elif category in ("Fotos", "Videos"):
                parent.setForeground(0, QColor(DesignSystem.COLOR_PRIMARY))
            else:
                parent.setForeground(0, QColor(DesignSystem.COLOR_TEXT_SECONDARY))
            
            self.files_tree.addTopLevelItem(parent)
            
            for move in sorted(moves_in_category, key=lambda m: m.original_name):
                child = QTreeWidgetItem()
                child.setText(0, f"  {move.source_path}")
                
                # Nuevo Nombre
                if move.has_conflict:
                    child.setText(1, move.new_name)
                    child.setForeground(1, QColor(DesignSystem.COLOR_ERROR))
                else:
                    child.setText(1, "Igual")
                    child.setForeground(1, QColor(DesignSystem.COLOR_TEXT_SECONDARY))
                
                # Fecha y Origen
                try:
                    file_metadata = get_all_metadata_from_file(move.source_path)
                    file_date, date_source = select_best_date_from_file(file_metadata)
                    if file_date:
                        child.setText(2, file_date.strftime("%Y-%m-%d %H:%M:%S"))
                        child.setText(3, date_source if date_source else "-")
                    else:
                        child.setText(2, "-")
                        child.setText(3, "-")
                except:
                    child.setText(2, "-")
                    child.setText(3, "-")

                child.setText(4, format_size(move.size))
                
                # Marcado visual de conflictos (texto en rojo)
                if move.has_conflict:
                    child.setForeground(0, QColor(DesignSystem.COLOR_ERROR))
                
                child.setData(0, Qt.ItemDataRole.UserRole, move)
                
                parent.addChild(child)
            
            if len(moves_in_category) <= 20:
                parent.setExpanded(True)
            
            if self.files_tree.topLevelItemCount() % 10 == 0:
                QApplication.processEvents()
    
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
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        
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
