"""
Ventana Principal de Pixaro Lab - Reimplementación desde cero
Estado 1 (Fase 1): Selector de carpeta y bienvenida
Estado 2 (Fase 2): Análisis con progreso
Estado 3 (Fase 3): Grid de herramientas
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFrame, QFileDialog, QScrollArea, QToolButton,
    QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QIcon

from ui.styles.design_system import DesignSystem
from ui.widgets.dropzone_widget import DropzoneWidget
from ui.widgets.progress_card import ProgressCard
from ui.widgets.analysis_phase_widget import AnalysisPhaseWidget
from ui.widgets.summary_card import SummaryCard
from ui.widgets.tool_card import ToolCard
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.live_photos_dialog import LivePhotoCleanupDialog
from ui.dialogs.heic_dialog import HEICDuplicateRemovalDialog
from ui.dialogs.exact_duplicates_dialog import ExactDuplicatesDialog
from ui.dialogs.similar_duplicates_dialog import SimilarDuplicatesDialog
from ui.dialogs.organization_dialog import FileOrganizationDialog
from ui.dialogs.renaming_dialog import RenamingPreviewDialog
from ui.workers import AnalysisWorker
from utils.logger import get_logger
from utils.icons import icon_manager
from utils.format_utils import format_size, format_file_count
from config import Config


class MainWindow(QMainWindow):
    """
    Ventana principal de Pixaro Lab
    Fase 1: Implementa ESTADO 1 (selector de carpeta)
    Fase 2: Implementa ESTADO 2 (análisis con progreso)
    """
    
    # Señales
    folder_selected = pyqtSignal(str)  # Emite cuando se selecciona una carpeta
    analysis_completed = pyqtSignal(object)  # Emite cuando el análisis termina
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('MainWindow')
        self.selected_folder = None
        self.analysis_worker = None
        self.analysis_results = None
        
        # Referencias a widgets del ESTADO 1
        self.welcome_card = None
        self.folder_selection_card = None
        self.next_step_card = None
        
        # Referencias a widgets del ESTADO 2
        self.progress_card = None
        self.phase_widget = None
        
        # Referencias a widgets del ESTADO 3
        self.summary_card = None
        self.tools_grid = None
        self.tool_cards = {}  # Dict de tool_id -> ToolCard
        
        # Timers para feedback visual de fases de análisis
        self.phase_timers = {}  # Dict de phase_id -> QTimer
        self.current_phase = None  # Fase actualmente en ejecución
        
        # Layout principal (necesario para cambiar widgets)
        self.main_layout = None
        
        self._setup_window()
        self._setup_ui()
        self._apply_stylesheet()
        self.logger.info("MainWindow inicializada en Estado 1")
    
    def _setup_window(self):
        """Configura las propiedades básicas de la ventana"""
        self.setWindowTitle(f"{Config.APP_NAME}")
        self.setMinimumSize(
            DesignSystem.WINDOW_MIN_WIDTH,
            DesignSystem.WINDOW_MIN_HEIGHT
        )
        self.resize(
            DesignSystem.WINDOW_DEFAULT_WIDTH,
            DesignSystem.WINDOW_DEFAULT_HEIGHT
        )
    
    def _setup_ui(self):
        """Configura la interfaz completa del ESTADO 1"""
        # Widget central con scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        central_widget = QWidget()
        scroll.setWidget(central_widget)
        self.setCentralWidget(scroll)
        
        # Layout principal (guardamos referencia para poder modificarlo)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(
            DesignSystem.SPACE_32,
            DesignSystem.SPACE_20,
            DesignSystem.SPACE_32,
            DesignSystem.SPACE_20
        )
        self.main_layout.setSpacing(DesignSystem.SPACE_16)
        
        # Card de bienvenida (compacta con iconos integrados)
        self.welcome_card = self._create_welcome_card()
        self.main_layout.addWidget(self.welcome_card)
        
        # Card de selección de carpeta
        self.folder_selection_card = self._create_folder_selection_card()
        self.main_layout.addWidget(self.folder_selection_card)
        
        # Card "Paso siguiente"
        self.next_step_card = self._create_next_step_card()
        self.main_layout.addWidget(self.next_step_card)
        
        # Espaciador al final
        self.main_layout.addStretch()
    
    def _create_welcome_card(self) -> QFrame:
        """
        Crea la card de bienvenida ultra-compacta con iconos integrados
        """
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(250, 250, 250, 0.8);
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_16}px;
            }}
        """)
        
        # Layout horizontal para todo en una sola línea
        layout = QHBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Título de bienvenida (más pequeño)
        welcome_title = QLabel(f"¡Bienvenido a {Config.APP_NAME}!")
        welcome_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(welcome_title)
        
        # Separador vertical delgado
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator.setFixedWidth(1)
        layout.addWidget(separator)
        
        # Subtítulo inline
        welcome_subtitle = QLabel("Analiza y optimiza tu colección de fotos y vídeos")
        welcome_subtitle.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(welcome_subtitle)
        
        # Espaciador para empujar los iconos a la derecha
        layout.addStretch()
        
        # Botón de configuración (icono)
        btn_settings = QToolButton()
        btn_settings.setAutoRaise(True)
        btn_settings.setToolTip("Configuración")
        icon_manager.set_button_icon(btn_settings, 'settings', color=DesignSystem.COLOR_TEXT_SECONDARY, size=16)
        btn_settings.setIconSize(QSize(16, 16))
        btn_settings.clicked.connect(self._on_settings_clicked)
        btn_settings.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                padding: 4px;
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QToolButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY};
            }}
        """)
        layout.addWidget(btn_settings)
        
        # Botón de acerca de (icono)
        btn_about = QToolButton()
        btn_about.setAutoRaise(True)
        btn_about.setToolTip("Acerca de")
        icon_manager.set_button_icon(btn_about, 'about', color=DesignSystem.COLOR_TEXT_SECONDARY, size=16)
        btn_about.setIconSize(QSize(16, 16))
        btn_about.clicked.connect(self._on_about_clicked)
        btn_about.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                padding: 4px;
                border-radius: {DesignSystem.RADIUS_BASE}px;
            }}
            QToolButton:hover {{
                background-color: {DesignSystem.COLOR_SECONDARY};
            }}
        """)
        layout.addWidget(btn_about)
        
        return card
    
    def _create_folder_selection_card(self) -> QFrame:
        """Crea la card principal para seleccionar carpeta"""
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_20}px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Header de la card
        header_title = QLabel("Selecciona la carpeta con tus fotos")
        header_title.setProperty("class", "header")
        layout.addWidget(header_title)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Dropzone centrado
        dropzone_container = QHBoxLayout()
        dropzone_container.addStretch()
        
        self.dropzone = DropzoneWidget()
        self.dropzone.folder_dropped.connect(self._on_folder_selected)
        dropzone_container.addWidget(self.dropzone)
        
        dropzone_container.addStretch()
        layout.addLayout(dropzone_container)
        
        # Botón "Seleccionar carpeta..."
        btn_container = QHBoxLayout()
        btn_container.addStretch()
        
        btn_select = QPushButton("Seleccionar carpeta...")
        btn_select.setProperty("class", "primary")
        btn_select.clicked.connect(self._on_browse_folder)
        btn_container.addWidget(btn_select)
        
        btn_container.addStretch()
        layout.addLayout(btn_container)
        
        # Separador horizontal
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator2.setFixedHeight(1)
        layout.addWidget(separator2)
        
        # Consejos compactos
        layout.addWidget(self._create_tip_box(
            "info",
            "Elige la carpeta donde tengas tus fotos y videos del iPhone, de WhatsApp, "
            "o cualquier colección que quieras organizar."
        ))
        
        layout.addWidget(self._create_tip_box(
            "check",
            "Pixaro Lab analizará esa carpeta y todas sus subcarpetas. "
            "No se modificará nada hasta que tú lo autorices."
        ))
        
        # TODO: Línea de última carpeta (si existe)
        # layout.addSpacing(DesignSystem.SPACE_16)
        # layout.addWidget(self._create_last_folder_line())
        
        return card
    
    def _create_tip_box(self, icon_name: str, text: str) -> QFrame:
        """Crea una caja de consejo con icono y texto"""
        tip = QFrame()
        tip.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(240, 240, 240, 0.5);
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
            }}
        """)
        
        layout = QHBoxLayout(tip)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        # Icono usando icon_manager
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, color=DesignSystem.COLOR_TEXT_SECONDARY, size=14)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(icon_label)
        
        # Texto
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            line-height: {DesignSystem.LINE_HEIGHT_NORMAL};
        """)
        layout.addWidget(text_label, 1)
        
        return tip
    
    def _create_next_step_card(self) -> QFrame:
        """Crea la card "Paso siguiente" (vacía inicialmente)"""
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_20}px;
                opacity: 0.5;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        # Header
        header_title = QLabel("Paso siguiente: Elige qué quieres hacer")
        header_title.setProperty("class", "header")
        layout.addWidget(header_title)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Texto centrado
        empty_text = QLabel("Las herramientas aparecerán aquí después de analizar tu carpeta")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-style: italic;
            padding: {DesignSystem.SPACE_24}px 0;
        """)
        layout.addWidget(empty_text)
        
        return card
    
    def _apply_stylesheet(self):
        """Aplica el stylesheet global incluyendo tooltips"""
        stylesheet = (
            DesignSystem.get_stylesheet() +
            DesignSystem.get_tooltip_style() +
            DesignSystem.get_progressbar_style()
        )
        self.setStyleSheet(stylesheet)
    
    # ==================== SLOTS ====================
    
    def _on_browse_folder(self):
        """Abre el diálogo de selección de carpeta"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta con fotos",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self._on_folder_selected(folder)
    
    def _on_folder_selected(self, folder_path: str):
        """Maneja cuando se selecciona una carpeta"""
        path = Path(folder_path)
        
        if not path.exists():
            self.logger.error(f"La carpeta no existe: {folder_path}")
            QMessageBox.critical(
                self,
                "Error",
                f"La carpeta seleccionada no existe:\n{folder_path}"
            )
            return
        
        if not path.is_dir():
            self.logger.error(f"La ruta no es una carpeta: {folder_path}")
            QMessageBox.warning(
                self,
                "Selección inválida",
                "Por favor selecciona una carpeta, no un archivo individual."
            )
            return
        
        self.selected_folder = str(path)
        self.logger.info(f"Carpeta seleccionada: {self.selected_folder}")
        self.folder_selected.emit(self.selected_folder)
        
        # Transición al ESTADO 2
        self._transition_to_state_2()
    
    def _on_settings_clicked(self):
        """Abre el diálogo de configuración"""
        self.logger.info("Abriendo configuración")
        #dialog = SettingsDialog(self)
        #dialog.exec()
    
    def _on_about_clicked(self):
        """Abre el diálogo Acerca de"""
        self.logger.info("Abriendo Acerca de")
        dialog = AboutDialog(self)
        dialog.exec()
    
    # ==================== TRANSICIÓN A ESTADO 2 ====================
    
    def _transition_to_state_2(self):
        """
        Transición del ESTADO 1 al ESTADO 2
        Oculta las cards de selección y muestra las de análisis
        """
        self.logger.info("Transición a ESTADO 2: Análisis")
        
        # Ocultar welcome card y folder_selection_card con fade out
        if self.welcome_card:
            self.welcome_card.hide()
        
        if self.folder_selection_card:
            self.folder_selection_card.hide()
        
        # Crear y mostrar card de progreso
        self.progress_card = ProgressCard(self.selected_folder)
        self.main_layout.insertWidget(1, self.progress_card)
        
        # Crear y mostrar widget de fases (opcional pero recomendado)
        self.phase_widget = AnalysisPhaseWidget()
        self.main_layout.insertWidget(2, self.phase_widget)
        
        # El next_step_card permanece visible pero más abajo
        
        # Iniciar análisis
        self._start_analysis()
    
    def _start_analysis(self):
        """Inicia el análisis del directorio seleccionado"""
        from services.file_renamer import FileRenamer
        from services.live_photo_detector import LivePhotoDetector
        from services.file_organizer import FileOrganizer
        from services.heic_remover import HEICRemover
        from services.duplicate_detector import DuplicateDetector
        
        # Crear instancias de servicios
        renamer = FileRenamer()
        lp_detector = LivePhotoDetector()
        organizer = FileOrganizer()
        heic_remover = HEICRemover()
        duplicate_detector = DuplicateDetector()
        
        # Crear worker de análisis
        self.analysis_worker = AnalysisWorker(
            directory=Path(self.selected_folder),
            renamer=renamer,
            lp_detector=lp_detector,
            unifier=organizer,
            heic_remover=heic_remover,
            duplicate_detector=duplicate_detector,
            organization_type=None  # Se usará el default
        )
        
        # Conectar señales del worker
        self.analysis_worker.progress_update.connect(self._on_analysis_progress)
        self.analysis_worker.phase_update.connect(self._on_analysis_phase)
        self.analysis_worker.stats_update.connect(self._on_analysis_stats)
        self.analysis_worker.partial_results.connect(self._on_partial_results)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.error.connect(self._on_analysis_error)
        
        # Iniciar análisis
        self.logger.info("Iniciando worker de análisis")
        self.analysis_worker.start()
    
    # ==================== SLOTS DE ANÁLISIS ====================
    
    def _on_analysis_progress(self, current: int, total: int, message: str):
        """
        Callback de progreso del análisis
        
        Args:
            current: Archivos procesados (puede ser 0 si no aplica)
            total: Total de archivos (puede ser 0 si no aplica)
            message: Mensaje descriptivo
        """
        if not self.progress_card:
            return
        
        # Actualizar mensaje de estado
        self.progress_card.update_status(message)
        
        # Si tenemos números reales, calcular porcentaje
        if total > 0 and current >= 0:
            percentage = int((current / total) * 100)
            self.progress_card.update_progress(current, total, percentage)
    
    def _on_analysis_phase(self, phase: str):
        """
        Callback cuando cambia la fase del análisis
        
        Args:
            phase: Nombre de la fase
        """
        self.logger.info(f"Fase de análisis: {phase}")
        
        if not self.phase_widget:
            return
        
        # Mapear nombres de fase a IDs del widget
        phase_map = {
            'live_photos': 'live_photos',
            'heic': 'heic',
            'duplicates': 'duplicates',
            'similar': 'similar'
        }
        
        # Si hay una fase anterior en ejecución, marcarla como completada con delay
        if self.current_phase and self.current_phase != phase:
            self._schedule_phase_completion(self.current_phase)
        
        # Establecer la nueva fase como running
        if phase in phase_map.values():
            self.phase_widget.set_phase_status(phase, 'running')
            self.current_phase = phase
    
    def _schedule_phase_completion(self, phase_id: str):
        """
        Programa la marcación de una fase como completada con delay mínimo de 1 segundo
        
        Args:
            phase_id: ID de la fase a marcar como completada
        """
        if phase_id in self.phase_timers:
            self.phase_timers[phase_id].stop()
        
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._on_phase_timer_timeout(phase_id))
        timer.start(1000)  # 1 segundo mínimo
        
        self.phase_timers[phase_id] = timer
    
    def _on_phase_timer_timeout(self, phase_id: str):
        """
        Callback cuando expira el timer de una fase
        
        Args:
            phase_id: ID de la fase que se marca como completada
        """
        if self.phase_widget:
            self.phase_widget.set_phase_status(phase_id, 'completed')
        
        # Limpiar el timer
        if phase_id in self.phase_timers:
            del self.phase_timers[phase_id]
    
    def _on_analysis_stats(self, stats):
        """
        Callback con estadísticas del análisis
        
        Args:
            stats: Objeto con estadísticas
        """
        if not self.progress_card:
            return
        
        # Formatear estadísticas
        if hasattr(stats, 'total_files'):
            total = stats.total_files
            # TODO: Agregar tamaño total si está disponible
            stats_text = f"{total:,} archivos encontrados"
            self.progress_card.update_stats(stats_text)
    
    def _on_partial_results(self, results):
        """
        Callback con resultados parciales de cada fase
        
        Args:
            results: Diccionario con resultados parciales
        """
        self.logger.debug(f"Resultados parciales: {results.keys()}")
        # TODO: Podríamos mostrar más info en el UI si es necesario
    
    def _on_analysis_finished(self, results):
        """
        Callback cuando el análisis termina exitosamente
        
        Args:
            results: Diccionario con todos los resultados
        """
        self.logger.info("Análisis completado exitosamente")
        self.analysis_results = results
        
        # Marcar progreso como completo
        if self.progress_card:
            self.progress_card.mark_completed()
        
        # Marcar todas las fases como completadas inmediatamente al terminar
        if self.phase_widget:
            for phase_id in ['live_photos', 'heic', 'duplicates']:
                self.phase_widget.set_phase_status(phase_id, 'completed')
        
        # Marcar progreso como completo
        if self.progress_card:
            self.progress_card.mark_completed()
        
        # Limpiar timers pendientes
        for timer in self.phase_timers.values():
            timer.stop()
        self.phase_timers.clear()
        self.current_phase = None
        
        # Emitir señal de análisis completado
        self.analysis_completed.emit(results)
        
        # Transición a ESTADO 3 con un pequeño delay para que el usuario vea "completado"
        QTimer.singleShot(1500, self._transition_to_state_3)
    
    def _on_analysis_error(self, error_msg: str):
        """
        Callback cuando ocurre un error en el análisis
        
        Args:
            error_msg: Mensaje de error
        """
        self.logger.error(f"Error en análisis: {error_msg}")
        
        QMessageBox.critical(
            self,
            "Error en el análisis",
            f"Ocurrió un error durante el análisis:\n\n{error_msg}\n\n"
            "Por favor revisa los logs para más detalles."
        )
        
        # TODO: Permitir volver al ESTADO 1 o reintentar
    
    # ==================== TRANSICIÓN A ESTADO 3 ====================
    
    def _transition_to_state_3(self):
        """
        Transición del ESTADO 2 al ESTADO 3
        Oculta progress_card y phase_widget, muestra summary_card y grid de herramientas
        """
        self.logger.info("Transición a ESTADO 3: Grid de herramientas")
        
        # Ocultar widgets del ESTADO 2
        if self.progress_card:
            self.progress_card.hide()
            self.progress_card.deleteLater()
            self.progress_card = None
        
        if self.phase_widget:
            self.phase_widget.hide()
            self.phase_widget.deleteLater()
            self.phase_widget = None
        
        # Crear y mostrar summary card
        self.summary_card = SummaryCard(self.selected_folder)
        self.summary_card.change_folder_requested.connect(self._on_change_folder)
        self.summary_card.reanalyze_requested.connect(self._on_reanalyze)
        self.main_layout.insertWidget(1, self.summary_card)
        
        # Actualizar estadísticas de la summary card
        if self.analysis_results:
            stats = self.analysis_results.get('stats', {})
            total_files = stats.get('total', 0)
            # TODO: Obtener tamaño total si está disponible
            self.summary_card.update_stats(total_files, 0)
            
            # Calcular espacio recuperable
            recoverable = self._calculate_recoverable_space()
            self.summary_card.update_recoverable_space(recoverable)
        
        # Crear grid de herramientas
        self._create_tools_grid()
        
        # Ocultar next_step_card
        if self.next_step_card:
            self.next_step_card.hide()
    
    def _calculate_recoverable_space(self) -> int:
        """
        Calcula el espacio total recuperable de todos los análisis
        
        Returns:
            Espacio en bytes
        """
        if not self.analysis_results:
            return 0
        
        total = 0
        
        # Live Photos
        lp_data = self.analysis_results.get('live_photos', {})
        if lp_data and hasattr(lp_data, 'total_groups'):
            # Estimar tamaño aproximado (cada video ~2-3 MB)
            total += lp_data.total_groups * 2.5 * 1024 * 1024
        
        # HEIC/JPG pairs
        heic_data = self.analysis_results.get('heic', {})
        if heic_data and hasattr(heic_data, 'potential_savings_keep_jpg'):
            # Usar el máximo potencial de ahorro
            total += max(heic_data.potential_savings_keep_jpg, heic_data.potential_savings_keep_heic)
        
        # Duplicados exactos
        dup_data = self.analysis_results.get('duplicates', {})
        if dup_data and hasattr(dup_data, 'space_wasted'):
            total += dup_data.space_wasted
        
        return int(total)
    
    def _create_tools_grid(self):
        """Crea el grid 2x3 con las 6 herramientas"""
        # Container para el grid
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(DesignSystem.SPACE_16)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        # Obtener datos de análisis para configurar las cards
        lp_data = self.analysis_results.get('live_photos', {}) if self.analysis_results else {}
        heic_data = self.analysis_results.get('heic', {}) if self.analysis_results else {}
        dup_data = self.analysis_results.get('duplicates', {}) if self.analysis_results else {}
        stats = self.analysis_results.get('stats', {}) if self.analysis_results else {}
        
        # Fila 1: Live Photos + HEIC/JPG
        live_photos_card = self._create_live_photos_card(lp_data)
        grid_layout.addWidget(live_photos_card, 0, 0)
        self.tool_cards['live_photos'] = live_photos_card
        
        heic_card = self._create_heic_card(heic_data)
        grid_layout.addWidget(heic_card, 0, 1)
        self.tool_cards['heic'] = heic_card
        
        # Fila 2: Duplicados Exactos + Similares
        exact_dup_card = self._create_exact_duplicates_card(dup_data)
        grid_layout.addWidget(exact_dup_card, 1, 0)
        self.tool_cards['exact_duplicates'] = exact_dup_card
        
        similar_dup_card = self._create_similar_duplicates_card()
        grid_layout.addWidget(similar_dup_card, 1, 1)
        self.tool_cards['similar_duplicates'] = similar_dup_card
        
        # Fila 3: Organizar + Renombrar
        organize_card = self._create_organize_card(stats)
        grid_layout.addWidget(organize_card, 2, 0)
        self.tool_cards['organize'] = organize_card
        
        rename_card = self._create_rename_card(stats)
        grid_layout.addWidget(rename_card, 2, 1)
        self.tool_cards['rename'] = rename_card
        
        # Agregar grid al layout principal
        self.main_layout.insertWidget(2, grid_container)
        self.tools_grid = grid_container
    
    # ==================== CREACIÓN DE TOOL CARDS ====================
    
    def _create_live_photos_card(self, lp_data: dict) -> ToolCard:
        """Crea la card de Live Photos"""
        card = ToolCard(
            icon_name='camera-burst',
            title='Live Photos',
            description='Gestiona los vídeos asociados a tus Live Photos. Puedes conservar '
                       'solo la foto, solo el vídeo, o ambos según tus preferencias.',
            action_text='Gestionar ahora'
        )
        
        # Configurar estado según datos
        if lp_data and hasattr(lp_data, 'total_groups'):
            count = lp_data.total_groups
            if count > 0:
                # Estimar espacio recuperable (~2.5 MB por video)
                size_text = f"~{format_size(count * 2.5 * 1024 * 1024)} recuperables"
                card.set_status_with_results(
                    f"{count} Live Photos detectadas",
                    size_text
                )
            else:
                card.set_status_ready("No se encontraron Live Photos")
        else:
            card.set_status_ready("Analizando...")
        
        card.clicked.connect(lambda: self._on_tool_clicked('live_photos'))
        return card
    
    def _create_heic_card(self, heic_data: dict) -> ToolCard:
        """Crea la card de HEIC/JPG Duplicados"""
        card = ToolCard(
            icon_name='heic',
            title='HEIC/JPG Duplicados',
            description='Elimina fotos duplicadas que están en dos formatos (HEIC y JPG). '
                       'Decide qué formato conservar.',
            action_text='Gestionar ahora'
        )
        
        # Configurar estado según datos
        if heic_data and hasattr(heic_data, 'total_pairs'):
            pairs = heic_data.total_pairs
            if pairs > 0:
                # Calcular tamaño total (usar el potencial de ahorro)
                savings = max(heic_data.potential_savings_keep_jpg, heic_data.potential_savings_keep_heic)
                size_text = f"~{format_size(savings)} recuperables"
                card.set_status_with_results(
                    f"{pairs} pares encontrados",
                    size_text
                )
            else:
                card.set_status_ready("No se encontraron pares HEIC/JPG")
        else:
            card.set_status_ready("Analizando...")
        
        card.clicked.connect(lambda: self._on_tool_clicked('heic'))
        return card
    
    def _create_exact_duplicates_card(self, dup_data: dict) -> ToolCard:
        """Crea la card de Duplicados Exactos"""
        card = ToolCard(
            icon_name='duplicate-exact',
            title='Duplicados Exactos',
            description='Encuentra archivos que son idénticos byte a byte (copias exactas). '
                       'Revisa los grupos y decide cuáles eliminar.',
            action_text='Gestionar ahora'
        )
        
        # Configurar estado según datos
        if dup_data and hasattr(dup_data, 'total_groups'):
            groups = dup_data.total_groups
            if groups > 0:
                # Usar el espacio wasted calculado
                size_text = f"~{format_size(dup_data.space_wasted)} recuperables"
                card.set_status_with_results(
                    f"{groups} grupos detectados",
                    size_text
                )
            else:
                card.set_status_ready("No se encontraron duplicados exactos")
        else:
            card.set_status_ready("Analizando...")
        
        card.clicked.connect(lambda: self._on_tool_clicked('exact_duplicates'))
        return card
    
    def _create_similar_duplicates_card(self) -> ToolCard:
        """Crea la card de Duplicados Similares (pendiente por defecto)"""
        card = ToolCard(
            icon_name='duplicate-similar',
            title='Duplicados Similares',
            description='Detecta fotos que son visualmente similares pero no idénticas '
                       '(recortes, rotaciones, ediciones).',
            action_text='Analizar ahora'
        )
        
        # Por defecto está pendiente
        card.set_status_pending("Este análisis puede tardar unos minutos.")
        
        card.clicked.connect(lambda: self._on_tool_clicked('similar_duplicates'))
        return card
    
    def _create_organize_card(self, stats: dict) -> ToolCard:
        """Crea la card de Organizar Archivos"""
        card = ToolCard(
            icon_name='organize',
            title='Organizar Archivos',
            description='Reorganiza tu colección en carpetas por fecha, origen '
                       '(WhatsApp, Telegram...) o tipo. Previsualiza antes de mover.',
            action_text='Planificar ahora'
        )
        
        # Siempre está lista
        total = stats.get('total', 0)
        card.set_status_ready(f"{format_file_count(total)} archivos listos")
        
        card.clicked.connect(lambda: self._on_tool_clicked('organize'))
        return card
    
    def _create_rename_card(self, stats: dict) -> ToolCard:
        """Crea la card de Renombrar Archivos"""
        card = ToolCard(
            icon_name='rename',
            title='Renombrar Archivos',
            description='Renombra archivos según patrones personalizados con fechas, '
                       'secuencias o metadatos. Vista previa antes de aplicar cambios.',
            action_text='Configurar ahora'
        )
        
        # Siempre está lista
        total = stats.get('total', 0)
        card.set_status_ready(f"{format_file_count(total)} archivos listos")
        
        card.clicked.connect(lambda: self._on_tool_clicked('rename'))
        return card
    
    # ==================== HANDLERS DE TOOL CARDS ====================
    
    def _on_tool_clicked(self, tool_id: str):
        """
        Maneja el clic en una tool card y abre el diálogo correspondiente
        
        Args:
            tool_id: ID de la herramienta ('live_photos', 'heic', etc.)
        """
        self.logger.info(f"Abriendo diálogo para: {tool_id}")
        
        if not self.analysis_results:
            QMessageBox.warning(self, "Error", "No hay datos de análisis disponibles")
            return
        
        dialog = None
        
        if tool_id == 'live_photos':
            lp_data = self.analysis_results.get('live_photos', {})
            if not lp_data:
                QMessageBox.warning(self, "Sin resultados", "No hay datos de Live Photos")
                return
            # LivePhotoCleanupDialog espera un dict (no dataclass)
            lp_dict = {
                'groups': getattr(lp_data, 'groups', []),
                'live_photos_found': getattr(lp_data, 'total_groups', 0),
                'total_space': getattr(lp_data, 'total_video_size', 0),
            }
            dialog = LivePhotoCleanupDialog(lp_dict, self)
        
        elif tool_id == 'heic':
            heic_data = self.analysis_results.get('heic', {})
            if not heic_data:
                QMessageBox.warning(self, "Sin resultados", "No hay datos de HEIC/JPG")
                return
            dialog = HEICDuplicateRemovalDialog(heic_data, self)
        
        elif tool_id == 'exact_duplicates':
            dup_data = self.analysis_results.get('duplicates', {})
            if not dup_data:
                QMessageBox.warning(self, "Sin resultados", "No hay datos de Duplicados Exactos")
                return
            dialog = ExactDuplicatesDialog(dup_data, self)
        
        elif tool_id == 'similar_duplicates':
            similar_data = self.analysis_results.get('similar', {})
            if not similar_data:
                QMessageBox.warning(self, "Sin resultados", "No hay datos de Duplicados Similares")
                return
            dialog = SimilarDuplicatesDialog(similar_data, self)
        
        elif tool_id == 'organize':
            org_data = self.analysis_results.get('organization', {})
            if not org_data:
                QMessageBox.warning(self, "Sin resultados", "No hay datos de Organización")
                return
            dialog = FileOrganizationDialog(org_data, self)
        
        elif tool_id == 'rename':
            rename_data = self.analysis_results.get('rename', {})
            if not rename_data:
                QMessageBox.warning(self, "Sin resultados", "No hay datos de Renombrado")
                return
            dialog = RenamingPreviewDialog(rename_data, self)
        
        if dialog:
            dialog.exec()
    
    
    def _on_change_folder(self):
        """Maneja el clic en "Cambiar carpeta" """
        reply = QMessageBox.question(
            self,
            "Cambiar carpeta",
            "¿Cambiar de carpeta? Se perderá el análisis actual.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Limpiar estado y volver a ESTADO 1
            self._reset_to_state_1()
    
    def _on_reanalyze(self):
        """Maneja el clic en "Reanalizar" """
        self.logger.info("Reanalizando carpeta")
        
        # Limpiar widgets del ESTADO 3
        if self.summary_card:
            self.summary_card.hide()
            self.summary_card.deleteLater()
            self.summary_card = None
        
        if self.tools_grid:
            self.tools_grid.hide()
            self.tools_grid.deleteLater()
            self.tools_grid = None
        
        self.tool_cards.clear()
        
        # Volver a ESTADO 2 y reanalizar
        self._transition_to_state_2()
    
    def _reset_to_state_1(self):
        """Reinicia la ventana al ESTADO 1"""
        self.logger.info("Reiniciando a ESTADO 1")
        
        # Limpiar todos los widgets
        if self.summary_card:
            self.summary_card.deleteLater()
            self.summary_card = None
        
        if self.tools_grid:
            self.tools_grid.deleteLater()
            self.tools_grid = None
        
        self.tool_cards.clear()
        
        # Limpiar estado
        self.selected_folder = None
        self.analysis_results = None
        self.analysis_worker = None
        
        # Recrear UI del ESTADO 1
        # Limpiar layout principal
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Recrear cards del ESTADO 1
        self.welcome_card = self._create_welcome_card()
        self.main_layout.addWidget(self.welcome_card)
        
        self.folder_selection_card = self._create_folder_selection_card()
        self.main_layout.addWidget(self.folder_selection_card)
        
        self.next_step_card = self._create_next_step_card()
        self.main_layout.addWidget(self.next_step_card)
        
        self.main_layout.addStretch()
