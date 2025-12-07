"""
Stage 3: Grid de herramientas.
Muestra el resumen del análisis y el grid de herramientas disponibles.
"""

from typing import Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QMessageBox, QDialog, 
    QFrame, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import QTimer, Qt
import qtawesome as qta

from config import Config
from utils.settings_manager import settings_manager
from .base_stage import BaseStage
from ui.styles.design_system import DesignSystem
from ui.widgets.summary_card import SummaryCard
from ui.widgets.tool_card import ToolCard
from ui.dialogs.live_photos_dialog import LivePhotoCleanupDialog
from ui.dialogs.heic_remover_dialog import HEICDuplicateRemovalDialog
from ui.dialogs.exact_copies_dialog import ExactCopiesDialog
from ui.dialogs.file_organizer_dialog import FileOrganizationDialog
from ui.dialogs.file_organizer_dialog import FileOrganizationDialog
from ui.dialogs.file_renaming_dialog import RenamingPreviewDialog
from ui.dialogs.zero_byte_dialog import ZeroByteDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.similar_files_progress_dialog import SimilarFilesProgressDialog
from utils.format_utils import format_size, format_file_count
from ui.workers import SimilarFilesAnalysisWorker
from utils.logger import log_section_header_discrete


class Stage3Window(BaseStage):
    """
    Stage 3: Grid de herramientas.
    Muestra resumen del análisis y herramientas disponibles para ejecutar.
    """

    def __init__(self, main_window, selected_folder: str, analysis_results: Dict[str, Any]):
        super().__init__(main_window)

        # Parámetros del estado
        self.selected_folder = selected_folder
        self.analysis_results = analysis_results
        
        # Extraer metadata_cache del análisis para reutilizarla
        self.metadata_cache = None
        if analysis_results and analysis_results.scan:
            scan_data = analysis_results.scan
            if hasattr(scan_data, 'metadata_cache') and scan_data.metadata_cache:
                self.metadata_cache = scan_data.metadata_cache
                self.logger.debug("Metadata cache disponible desde análisis inicial")

        # Referencias a widgets del estado
        self.header = None
        self.stale_banner = None
        self.summary_card = None
        self.tools_grid = None
        self.tool_cards = {}  # Dict de tool_id -> ToolCard
        
        # Worker y diálogos para análisis de similares
        self.similarity_worker = None
        self.similarity_progress_dialog = None
        self.similarity_results = None  # Guardar resultados del análisis

    def setup_ui(self) -> None:
        """Configura la interfaz de usuario del Stage 3."""
        self.logger.debug("Configurando UI del Stage 3")

        # Limpiar el layout principal antes de agregar nuevos widgets
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().hide()
                child.widget().setParent(None)

        # Añadir espaciado encima del header
        self.main_layout.addSpacing(DesignSystem.SPACE_4)

        # Crear y mostrar header
        self.header = self.create_header(
            on_settings_clicked=self._on_settings_clicked,
            on_about_clicked=self._on_about_clicked
        )
        self.main_layout.addWidget(self.header)
        self.main_layout.addSpacing(DesignSystem.SPACE_8)

        # Crear banner de advertencia (oculto por defecto)
        self.stale_banner = self._create_stale_banner()
        self.main_layout.addWidget(self.stale_banner)

        # Añadir stretch para mantener el header en la parte superior
        self.main_layout.addStretch()

        # Crear y mostrar summary card con delay
        QTimer.singleShot(300, self._show_summary_card)

        self.logger.debug("UI del Stage 3 configurada")

    def cleanup(self) -> None:
        """Limpia los recursos del Stage 3."""
        self.logger.debug("Limpiando Estado 3")

        # Limpiar referencias
        if self.header:
            self.header.hide()
            self.header.setParent(None)
            self.header = None

        if self.stale_banner:
            self.stale_banner.hide()
            self.stale_banner.setParent(None)
            self.stale_banner = None

        if self.summary_card:
            self.summary_card.hide()
            self.summary_card.setParent(None)
            self.summary_card = None

        if self.tools_grid:
            self.tools_grid.hide()
            self.tools_grid.setParent(None)
            self.tools_grid = None

        self.tool_cards.clear()

    def _create_stale_banner(self) -> QWidget:
        """Crea el banner de advertencia de estadísticas desactualizadas"""
        banner = QFrame()
        banner.setObjectName("staleBanner")
        
        # Estilo del banner
        banner.setStyleSheet(f"""
            QFrame#staleBanner {{
                background-color: {DesignSystem.COLOR_WARNING_BG};
                border: 1px solid {DesignSystem.COLOR_WARNING};
                border-radius: {DesignSystem.RADIUS_MD}px;
            }}
        """)
        
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(DesignSystem.SPACE_16, DesignSystem.SPACE_12, 
                                 DesignSystem.SPACE_16, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Icono
        icon_label = QLabel()
        icon = qta.icon('fa5s.exclamation-triangle', color=DesignSystem.COLOR_WARNING)
        icon_label.setPixmap(icon.pixmap(24, 24))
        layout.addWidget(icon_label)
        
        # Mensaje
        msg_label = QLabel(
            "<b>Estadísticas desactualizadas</b><br>"
            "Se han realizado cambios en los archivos. "
            "Las estadísticas mostradas pueden no ser precisas."
        )
        msg_label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_BASE}px;")
        layout.addWidget(msg_label)
        
        layout.addStretch()
        
        # Botón de re-análisis
        btn = QPushButton("Re-analizar ahora")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIcon(qta.icon('fa5s.sync-alt', color=DesignSystem.COLOR_TEXT))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.5);
                border: 1px solid {DesignSystem.COLOR_WARNING};
                border-radius: {DesignSystem.RADIUS_SM}px;
                padding: 6px 12px;
                color: {DesignSystem.COLOR_TEXT};
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.8);
            }}
        """)
        btn.clicked.connect(self._on_reanalyze)
        layout.addWidget(btn)
        
        banner.hide()
        return banner

    def _show_summary_card(self):
        """Muestra la summary card con animaciones"""
        # Remover el stretch temporal para que el contenido se alinee correctamente
        if self.main_layout.count() > 2:  # header + spacing + stretch
            self.main_layout.takeAt(self.main_layout.count() - 1)  # Remover stretch

        # Crear y mostrar summary card
        self.summary_card = SummaryCard(self.selected_folder)
        self.summary_card.change_folder_requested.connect(self._on_change_folder)
        self.summary_card.reanalyze_requested.connect(self._on_reanalyze)
        self.main_layout.addWidget(self.summary_card)
        # No usar fade_in para evitar problemas con el scroll
        # self.fade_in_widget(self.summary_card, duration=400)

        # Actualizar estadísticas de la summary card
        total_files = self.analysis_results.scan.total_files
        
        # Calcular tamaño total del directorio
        total_size = self._calculate_directory_size()
        self.summary_card.update_stats(total_files, total_size)

        # Calcular espacio recuperable
        recoverable = self._calculate_recoverable_space()
        self.summary_card.update_recoverable_space(recoverable)

        # Añadir stretch después de la summary card para mantener el layout
        self.main_layout.addStretch()

        # Crear grid de herramientas con delay escalonado
        QTimer.singleShot(200, self._create_tools_grid)

    def _calculate_directory_size(self) -> int:
        """
        Calcula el tamaño total del directorio analizado
        
        Returns:
            Tamaño total en bytes
        """
        from pathlib import Path
        
        try:
            directory = Path(self.selected_folder)
            total_size = 0
            
            # Recorrer todos los archivos del directorio
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except (OSError, PermissionError):
                        # Ignorar archivos que no se pueden leer
                        pass
            
            return total_size
        except Exception as e:
            self.logger.warning(f"Error calculando tamaño del directorio: {e}")
            return 0

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
        if self.analysis_results.live_photos:
            live_photo_data = self.analysis_results.live_photos
            if live_photo_data.live_photos_found > 0:
                total += live_photo_data.space_to_free

        # HEIC/JPG pairs
        if self.analysis_results.heic:
            heic_data = self.analysis_results.heic
            if heic_data.potential_savings_keep_jpg > 0 or heic_data.potential_savings_keep_heic > 0:
                # Usar el máximo potencial de ahorro
                total += max(heic_data.potential_savings_keep_jpg, heic_data.potential_savings_keep_heic)

        # Duplicados exactos
        if self.analysis_results.duplicates:
            dup_data = self.analysis_results.duplicates
            if dup_data.space_wasted > 0:
                total += dup_data.space_wasted

        return int(total)

    def _create_tools_grid(self):
        """Crea el grid 2x4 con las 7 herramientas"""
        # Container para el grid
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(12)  # Reducido para optimizar espacio vertical
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Obtener datos de análisis (todos dataclasses tipados)
        live_photo_data = self.analysis_results.live_photos
        heic_data = self.analysis_results.heic
        dup_data = self.analysis_results.duplicates

        # Fila 0: Archivos Vacíos + HEIC/JPG
        zero_byte_card = self._create_zero_byte_card()
        grid_layout.addWidget(zero_byte_card, 0, 0)
        self.tool_cards['zero_byte'] = zero_byte_card
        
        heic_card = self._create_heic_card(heic_data)
        grid_layout.addWidget(heic_card, 0, 1)
        self.tool_cards['heic'] = heic_card

        # Fila 1: Live Photos + Duplicados Exactos
        live_photos_card = self._create_live_photos_card(live_photo_data)
        grid_layout.addWidget(live_photos_card, 1, 0)
        self.tool_cards['live_photos'] = live_photos_card

        exact_dup_card = self._create_exact_duplicates_card(dup_data)
        grid_layout.addWidget(exact_dup_card, 1, 1)
        self.tool_cards['exact_copies'] = exact_dup_card

        # Fila 2: Archivos Similares + (espacio vacío)
        similar_dup_card = self._create_similar_duplicates_card()
        grid_layout.addWidget(similar_dup_card, 2, 0)
        self.tool_cards['similar_files'] = similar_dup_card

        # Fila 3: Organizar + Renombrar (herramientas de reorganización juntas)
        organize_card = self._create_organize_card()
        grid_layout.addWidget(organize_card, 3, 0)
        self.tool_cards['folder-move'] = organize_card

        rename_card = self._create_rename_card()
        grid_layout.addWidget(rename_card, 3, 1)
        self.tool_cards['rename-box'] = rename_card

        # Agregar grid al layout principal
        # Remover el stretch temporal antes de añadir el grid
        if self.main_layout.count() > 3:  # header + spacing + summary_card + stretch
            self.main_layout.takeAt(self.main_layout.count() - 1)  # Remover stretch

        # Añadir espaciado entre summary card y tool cards
        self.main_layout.addSpacing(DesignSystem.SPACE_4)

        self.main_layout.addWidget(grid_container)
        self.tools_grid = grid_container

        # Forzar actualización del scroll area para que funcione correctamente
        if hasattr(self.main_window, 'scroll_area'):
            self.main_window.scroll_area.update()
            self.main_window.scroll_area.viewport().update()
            # Asegurar que el widget contenido tenga el tamaño correcto
            scroll_widget = self.main_window.scroll_area.widget()
            if scroll_widget:
                scroll_widget.adjustSize()
                # Forzar recalculo del layout
                scroll_widget.layout().invalidate()
                scroll_widget.layout().activate()

    def _create_live_photos_card(self, live_photo_data) -> ToolCard:
        """Crea la card de Live Photos"""
        card = ToolCard(
            icon_name='camera-burst',
            title='Live Photos',
            description='Las Live Photos de iPhone combinan imagen y vídeo corto. '
                       'Libera espacio eliminando el componente de vídeo o foto según prefieras, '
                       'mientras conservas la esencia de tus recuerdos.',
            action_text='Gestionar ahora'
        )

        # Configurar estado según datos (live_photo_data es LivePhotoDetectionResult o None)
        if live_photo_data and live_photo_data.live_photos_found > 0:
            size_text = f"~{format_size(live_photo_data.space_to_free)} recuperables"
            card.set_status_with_results(
                f"{live_photo_data.live_photos_found} Live Photos detectadas",
                size_text
            )
        else:
            card.set_status_no_results("No se encontraron Live Photos")

        card.clicked.connect(lambda: self._on_tool_clicked('live_photos'))
        return card

    def _create_heic_card(self, heic_data) -> ToolCard:
        """Crea la card de HEIC/JPG Duplicados"""
        card = ToolCard(
            icon_name='file-image',
            title='HEIC/JPG Duplicados',
            description='iPhone guarda fotos en HEIC (eficiente) y crea versiones JPG para '
                       'compatibilidad. Elimina duplicados conservando el formato que prefieras '
                       'y recupera espacio valioso.',
            action_text='Gestionar ahora'
        )

        # Configurar estado según datos (heic_data es HeicAnalysisResult o None)
        if heic_data and heic_data.total_pairs > 0:
            # Calcular tamaño total (usar el potencial de ahorro)
            savings = max(heic_data.potential_savings_keep_jpg, heic_data.potential_savings_keep_heic)
            size_text = f"~{format_size(savings)} recuperables"
            card.set_status_with_results(
                f"{heic_data.total_pairs} grupos de duplicados HEIC /JPG encontrados",
                size_text
            )
        else:
            card.set_status_no_results("No se encontraron pares HEIC/JPG")

        card.clicked.connect(lambda: self._on_tool_clicked('heic'))
        return card

    def _create_exact_duplicates_card(self, dup_data) -> ToolCard:
        """Crea la card de Copias exactas"""
        card = ToolCard(
            icon_name='content-copy',
            title='Copias exactas',
            description='Encuentra archivos 100% idénticos bit a bit, incluso con nombres '
                       'diferentes. Si las fechas o metadatos son diferentes, no se considera '
                       'idéntico. Para duplicados con metadatos diferentes, usa "Archivos similares".',
            action_text='Gestionar ahora'
        )

        # Configurar estado según datos (dup_data es DuplicateAnalysisResult o None)
        if dup_data and dup_data.total_groups > 0:
            size_text = f"~{format_size(dup_data.space_wasted)} recuperables"
            card.set_status_with_results(
                f"{dup_data.total_groups} grupos detectados con copias idénticas",
                size_text
            )
        else:
            card.set_status_no_results("No se encontraron copias exactas")

        card.clicked.connect(lambda: self._on_tool_clicked('exact_copies'))
        return card

    def _create_similar_duplicates_card(self) -> ToolCard:
        """Crea la card de Archivos similares (pendiente por defecto)"""
        card = ToolCard(
            icon_name='image-search',
            title='Archivos similares',
            description='Detecta fotos y vídeos visualmente idénticos aunque tengan metadatos '
                       'diferentes (fechas, compresión, etc.). Al 100% de similitud son '
                       'prácticamente idénticos visualmente.',
            action_text='Analizar ahora'
        )

        # Por defecto está pendiente
        card.set_status_pending("Este análisis puede tardar bastante tiempo según la cantidad de archivos, por eso no se ha realizado anteriormente.")

        card.clicked.connect(lambda: self._on_tool_clicked('similar_files'))
        return card

    def _create_organize_card(self) -> ToolCard:
        """Crea la card de Organizar Archivos"""
        card = ToolCard(
            icon_name='folder-move',
            title='Organizar Archivos',
            description='Reorganiza tu colección en carpetas por fecha, origen '
                       '(WhatsApp, Telegram...) o tipo. Previsualiza antes de mover.',
            action_text='Planificar ahora'
        )

        # Siempre está lista
        total = self.analysis_results.scan.total_files
        card.set_status_ready(f"{format_file_count(total)} archivos listos")

        card.clicked.connect(lambda: self._on_tool_clicked('folder-move'))
        return card

    def _create_rename_card(self) -> ToolCard:
        """Crea la card de Renombrar Archivos"""
        card = ToolCard(
            icon_name='rename-box',
            title='Renombrar Archivos',
            description='Renombra archivos según patrones personalizados con fechas, '
                       'secuencias o metadatos. Vista previa antes de aplicar cambios.',
            action_text='Configurar ahora'
        )

        # Siempre está lista
        total = self.analysis_results.scan.total_files
        card.set_status_ready(f"{format_file_count(total)} archivos listos")

        card.clicked.connect(lambda: self._on_tool_clicked('rename-box'))
        return card

    def _create_zero_byte_card(self) -> ToolCard:
        """Crea la card de Archivos Vacíos"""
        card = ToolCard(
            icon_name='trash-alt',
            title='Archivos Vacíos',
            description='Detecta y elimina archivos de 0 bytes que no contienen información. '
                       'Limpia tu directorio de archivos corruptos o vacíos innecesarios.',
            action_text='Limpiar ahora'
        )
        
        # Configurar estado
        zero_byte_data = self.analysis_results.zero_byte
        if zero_byte_data and zero_byte_data.zero_byte_files_found > 0:
            card.set_status_with_results(
                f"{zero_byte_data.zero_byte_files_found} archivos vacíos encontrados",
                "0 B recuperables (limpieza)"
            )
        else:
            card.set_status_no_results("No se encontraron archivos vacíos")
            
        card.clicked.connect(lambda: self._on_tool_clicked('zero_byte'))
        return card

    def _on_tool_clicked(self, tool_id: str):
        """
        Maneja el clic en una tool card y abre el diálogo correspondiente

        Args:
            tool_id: ID de la herramienta ('live_photos', 'heic', etc.)
        """
        self.logger.info(f"Abriendo diálogo para: {tool_id}")

        if not self.analysis_results:
            QMessageBox.warning(self.main_window, "Error", "No hay datos de análisis disponibles")
            return

        dialog = None

        if tool_id == 'live_photos':
            live_photo_data = self.analysis_results.live_photos
            if not live_photo_data or live_photo_data.live_photos_found == 0:
                # Card está deshabilitada, no debería llegar aquí
                return
            dialog = LivePhotoCleanupDialog(live_photo_data, self.main_window)

        elif tool_id == 'heic':
            heic_data = self.analysis_results.heic
            if not heic_data or heic_data.total_pairs == 0:
                # Card está deshabilitada, no debería llegar aquí
                return
            dialog = HEICDuplicateRemovalDialog(heic_data, self.main_window)

        elif tool_id == 'exact_copies':
            dup_data = self.analysis_results.duplicates
            if not dup_data or dup_data.total_groups == 0:
                # Card está deshabilitada, no debería llegar aquí
                return
            dialog = ExactCopiesDialog(dup_data, self.main_window)

        elif tool_id == 'similar_files':
            # Similares requieren configuración previa
            self._on_similar_duplicates_clicked()
            return

        elif tool_id == 'folder-move':
            org_data = self.analysis_results.organization
            if not org_data:
                # Card está deshabilitada, no debería llegar aquí
                return
            # Permitir abrir el dialog incluso con 0 archivos, ya que el usuario puede cambiar el tipo
            # Pasar metadata_cache para optimizar re-análisis cuando se cambia el tipo
            dialog = FileOrganizationDialog(org_data, self.main_window, self.metadata_cache)

        elif tool_id == 'rename-box':
            rename_data = self.analysis_results.renaming
            if not rename_data:
                # No hay datos, no debería llegar aquí
                return
            # Permitir abrir incluso con need_renaming=0, el usuario puede configurar patrones personalizados
            dialog = RenamingPreviewDialog(rename_data, self.main_window)
            
        elif tool_id == 'zero_byte':
            zero_byte_data = self.analysis_results.zero_byte
            if not zero_byte_data or zero_byte_data.zero_byte_files_found == 0:
                return
            dialog = ZeroByteDialog(zero_byte_data, self.main_window)

        if dialog:
            result = dialog.exec()
            # Si el usuario aceptó el diálogo, ejecutar las acciones
            if result == QDialog.DialogCode.Accepted:
                self._execute_tool_action(tool_id, dialog)
    
    def _execute_tool_action(self, tool_id: str, dialog):
        """
        Ejecuta las acciones de una herramienta usando el worker correspondiente.
        
        Args:
            tool_id: ID de la herramienta ('live_photos', 'heic', etc)
            dialog: Diálogo que contiene el accepted_plan
        """
        from ui.workers import (
            LivePhotoCleanupWorker,
            HEICRemovalWorker,
            DuplicateDeletionWorker,
            FileOrganizerWorker,
            RenamingWorker,
            ZeroByteDeletionWorker,
        )
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import Qt
        
        if not hasattr(dialog, 'accepted_plan'):
            self.logger.warning(f"Diálogo de {tool_id} no tiene accepted_plan")
            return
        
        plan = dialog.accepted_plan
        self.logger.info(f"Ejecutando acciones de {tool_id} con plan: {list(plan.keys()) if isinstance(plan, dict) else type(plan)}")
        
        # === VERIFICAR CONFIRMACIÓN ADICIONAL PARA ELIMINACIÓN ===
        # Lista de herramientas destructivas (que eliminan archivos)
        destructive_tools = ['live_photos', 'heic', 'exact_copies', 'similar_files', 'zero_byte']
        
        # Solo pedir confirmación si es una operación real (no simulada)
        is_dry_run = plan.get('dry_run', False)
        
        if tool_id in destructive_tools and not is_dry_run and settings_manager.get_confirm_delete():
            reply = QMessageBox.question(
                self.main_window,
                "Confirmar Eliminación",
                "Esta operación eliminará archivos de forma permanente.\n\n"
                "¿Estás seguro de que deseas continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                self.logger.info(f"Operación {tool_id} cancelada por el usuario en confirmación adicional")
                return

        # Crear diálogo de progreso
        progress_dialog = QProgressDialog(
            "Ejecutando operación...",
            "Cancelar",
            0, 100,
            self.main_window
        )
        progress_dialog.setWindowTitle("Procesando")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setMinimumDuration(0)
        progress_dialog.setValue(0)
        
        # Crear worker según la herramienta
        worker = None
        
        if tool_id == 'live_photos':
            from services.live_photos_service import LivePhotoService
            service = LivePhotoService()
            # LivePhotoCleanupWorker espera (service, analysis: dataclass, create_backup, dry_run)
            worker = LivePhotoCleanupWorker(
                service,
                analysis=plan.get('analysis'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'heic':
            from services.heic_remover_service import HEICRemover
            remover = HEICRemover()
            # HEICRemovalWorker espera (remover, analysis: dataclass, keep_format, create_backup, dry_run)
            worker = HEICRemovalWorker(
                remover=remover,
                analysis=plan.get('analysis'),
                keep_format=plan.get('keep_format', 'file-jpg-box'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'exact_copies':
            from services.exact_copies_detector import ExactCopiesDetector
            detector = ExactCopiesDetector()
            # DuplicateDeletionWorker espera (detector, groups, keep_strategy, create_backup, dry_run)
            worker = DuplicateDeletionWorker(
                detector=detector,
                groups=plan.get('groups', []),
                keep_strategy=plan.get('keep_strategy', 'first'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'similar_files':
            from services.similar_files_detector import SimilarFilesDetector
            detector = SimilarFilesDetector()
            # DuplicateDeletionWorker espera (detector, groups, keep_strategy, create_backup, dry_run)
            worker = DuplicateDeletionWorker(
                detector=detector,
                groups=plan.get('groups', []),
                keep_strategy=plan.get('keep_strategy', 'manual'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'folder-move':
            from services.file_organizer_service import FileOrganizer
            organizer = FileOrganizer()
            # FileOrganizerWorker espera (organizer, analysis: dataclass, cleanup_empty_dirs, create_backup, dry_run)
            worker = FileOrganizerWorker(
                organizer=organizer,
                analysis=plan.get('analysis'),
                cleanup_empty_dirs=plan.get('cleanup_empty_dirs', True),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'rename-box':
            from services.file_renamer_service import FileRenamer
            renamer = FileRenamer()
            # RenamingWorker espera (renamer, analysis: dataclass, create_backup, dry_run)
            worker = RenamingWorker(
                renamer=renamer,
                analysis=plan.get('analysis'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )

        elif tool_id == 'zero_byte':
            from services.zero_byte_service import ZeroByteService
            service = ZeroByteService()
            # ZeroByteDeletionWorker espera (service, files, create_backup, dry_run)
            worker = ZeroByteDeletionWorker(
                service=service,
                files=plan.get('files_to_delete', []),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        if not worker:
            self.logger.error(f"No se pudo crear worker para {tool_id}")
            return
        
        # Conectar señales del worker
        def on_progress(current, total, message):
            if total > 0:
                progress_dialog.setValue(int((current / total) * 100))
            progress_dialog.setLabelText(message)
        
        def on_finished(result):
            progress_dialog.close()
            self.logger.info(f"Operación {tool_id} completada: {result}")
            
            # Mostrar resultado
            if result and hasattr(result, 'success') and result.success:
                # Build success message
                msg_content = result.message if (hasattr(result, 'message') and result.message) else ""
                message = f"La operación se completó exitosamente.\n\n{msg_content}"
                
                # Add errors warning if any
                if hasattr(result, 'errors') and result.errors:
                    message += f"\n\nAdvertencia: Se encontraron {len(result.errors)} errores durante la operación."
                
                # First show success message
                QMessageBox.information(
                    self.main_window,
                    "Operación Completada",
                    message
                )
                
                # Only ask for re-analysis if operation was NOT simulated
                # Simulated operations (dry_run=True) don't modify files, so re-analysis is unnecessary
                was_simulation = plan.get('dry_run', False)
                
                if not was_simulation:
                    # Then ask user about re-analysis
                    reply = QMessageBox.question(
                        self.main_window,
                        "Re-analizar carpeta",
                        "¿Deseas re-analizar la carpeta para actualizar las estadísticas?\n\n"
                        "Nota: El re-análisis puede tardar varios minutos con datasets grandes. "
                        "Si omites este paso, las estadísticas mostradas pueden no reflejar los cambios realizados.",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes  # Default to Yes
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # Re-analyze as before
                        log_section_header_discrete(self.logger, f"Re-análisis solicitado por usuario tras completar {tool_id}")
                        QTimer.singleShot(500, self._on_reanalyze)
                    else:
                        # User chose to skip re-analysis
                        self.logger.info("Usuario omitió re-análisis, las estadísticas pueden estar desactualizadas")
                        # Mostrar banner de advertencia
                        if self.stale_banner:
                            self.stale_banner.show()
                            # Asegurar que el banner sea visible (scroll to top if needed)
                            if hasattr(self.main_window, 'scroll_area'):
                                self.main_window.scroll_area.ensureWidgetVisible(self.stale_banner)
                else:
                    # Operation was simulated, no need to re-analyze
                    self.logger.info("Operación simulada completada, no se requiere re-análisis")
            else:
                error_msg = result.message if (result and hasattr(result, 'message')) else "Operación fallida"
                QMessageBox.warning(
                    self.main_window,
                    "Operación Fallida",
                    f"La operación no se completó correctamente.\n\n{error_msg}"
                )
            
            worker.deleteLater()
        
        def on_error(error_message):
            progress_dialog.close()
            self.logger.error(f"Error en operación {tool_id}: {error_message}")
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"Ocurrió un error:\n\n{error_message[:500]}"
            )
            worker.deleteLater()
        
        worker.progress_update.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        
        # Conectar cancelación
        progress_dialog.canceled.connect(worker.stop)
        
        # Iniciar worker
        worker.start()
        self.logger.debug(f"Worker de {tool_id} iniciado")

    def _on_change_folder(self):
        """Maneja el clic en "Cambiar carpeta" """
        reply = QMessageBox.question(
            self.main_window,
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
        if self.stale_banner:
            self.stale_banner.hide()
            self.stale_banner.setParent(None)
            self.stale_banner = None

        if self.summary_card:
            self.summary_card.hide()
            self.summary_card.setParent(None)
            self.summary_card = None

        if self.tools_grid:
            self.tools_grid.hide()
            self.tools_grid.setParent(None)
            self.tools_grid = None

        self.tool_cards.clear()

        # Volver a ESTADO 2 y reanalizar a través de MainWindow
        self.main_window._transition_to_state_2(self.selected_folder)

    def _reset_to_state_1(self):
        """Reinicia la ventana al ESTADO 1"""
        self.logger.info("Reiniciando a ESTADO 1")

        # Limpiar todos los widgets
        if self.summary_card:
            self.summary_card.setParent(None)
            self.summary_card = None

        if self.tools_grid:
            self.tools_grid.setParent(None)
            self.tools_grid = None

        self.tool_cards.clear()

        # Transición al Estado 1 a través de MainWindow
        self.main_window._transition_to_state_1()

    def _on_settings_clicked(self):
        """Maneja el clic en el botón de configuración"""
        self.logger.debug("Abriendo diálogo de configuración")
        dialog = SettingsDialog(self.main_window)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()
        
    def _on_settings_saved(self):
        """Maneja cambios en la configuración"""
        if self.summary_card:
            self.summary_card.update_path_display()

    def _on_about_clicked(self):
        """Maneja el clic en el botón 'Acerca de'"""
        self.logger.debug("Abriendo diálogo 'Acerca de'")
        dialog = AboutDialog(self.main_window)
        dialog.exec()
    
    # ==================== SIMILAR DUPLICATES ====================
    
    def _on_similar_duplicates_clicked(self):
        """
        Maneja el clic en la card de duplicados similares.
        
        Flujo simplificado sin config dialog:
        1. Lanzar análisis directo (solo hashes, sin clustering)
        2. Mostrar diálogo de progreso bloqueante
        3. Al completar, abrir diálogo de gestión con slider
        """
        self.logger.info("Iniciando análisis de archivos similares")
        
        # Si ya hay análisis completado, abrir directamente
        if hasattr(self, 'similarity_analysis') and self.similarity_analysis:
            # Verificar si hay archivos analizados antes de abrir el diálogo
            if self.similarity_analysis.total_files == 0 or not self.similarity_analysis.perceptual_hashes:
                QMessageBox.information(
                    self.main_window,
                    "Sin archivos similares",
                    "No se encontraron archivos similares en el análisis.\n\n"
                    "Esto puede ocurrir si:\n"
                    "• No hay suficientes imágenes para comparar\n"
                    "• Las imágenes son muy diferentes entre sí\n"
                    "• La sensibilidad del análisis es demasiado estricta"
                )
                return
            
            self._open_similarity_dialog_with_analysis(self.similarity_analysis)
            return
        
        # Obtener número de archivos a analizar
        file_count = (
            self.analysis_results.scan.total_files
            if self.analysis_results.scan
            else 0
        )
        
        self.logger.info(f"Iniciando análisis de {file_count} archivos")
        self._start_similarity_analysis(file_count)
    
    def _start_similarity_analysis(self, file_count: int):
        """
        Inicia el análisis inicial de archivos similares (solo hashes).
        
        Args:
            file_count: Número de archivos a analizar
        """
        from services.similar_files_detector import SimilarFilesDetector
        from pathlib import Path
        
        # Crear el detector
        detector = SimilarFilesDetector()
        
        # Crear el worker (sin sensibilidad)
        self.similarity_worker = SimilarFilesAnalysisWorker(
            detector=detector,
            workspace_path=Path(self.selected_folder)
        )
        
        # Crear diálogo de progreso bloqueante
        self.similarity_progress_dialog = SimilarFilesProgressDialog(
            parent=self.main_window,
            total_files=file_count
        )
        
        # Conectar señales del worker
        self.similarity_worker.progress_update.connect(
            self._on_similarity_progress_update
        )
        self.similarity_worker.finished.connect(
            self._on_similarity_analysis_completed
        )
        self.similarity_worker.error.connect(
            self._on_similarity_analysis_error
        )
        
        # Conectar cancelación del diálogo
        self.similarity_progress_dialog.cancel_requested.connect(
            self._on_similarity_analysis_cancelled
        )
        
        # Iniciar worker
        self.similarity_worker.start()
        
        # Mostrar diálogo bloqueante
        self.similarity_progress_dialog.exec()
    
    def _on_similarity_progress_update(self, current: int, total: int, message: str):
        """Actualiza el progreso en el diálogo"""
        if self.similarity_progress_dialog:
            self.similarity_progress_dialog.update_progress(current, total, message)
    
    def _on_similarity_analysis_completed(self, analysis):
        """
        Maneja la finalización exitosa del análisis.
        
        Args:
            analysis: SimilarFilesAnalysis con hashes calculados
        """
        self.logger.info("Análisis inicial de archivos similares completado")
        self.similarity_analysis = analysis
        
        # Cerrar diálogo de progreso
        if self.similarity_progress_dialog:
            self.similarity_progress_dialog.accept()
            self.similarity_progress_dialog = None
        
        # Limpiar worker
        if self.similarity_worker:
            self.similarity_worker.deleteLater()
            self.similarity_worker = None
        
        # Actualizar la card indicando que el análisis está completado
        self._update_similar_duplicates_card_after_analysis(analysis)
        
        # Verificar si hay hashes calculados antes de abrir el diálogo
        if analysis.total_files == 0 or not analysis.perceptual_hashes:
            QMessageBox.information(
                self.main_window,
                "Sin archivos similares",
                "No se encontraron archivos similares en la carpeta analizada.\n\n"
                "Esto puede ocurrir si:\n"
                "• No hay suficientes imágenes para comparar\n"
                "• Las imágenes son muy diferentes entre sí\n"
                "• Ya se han eliminado todos los duplicados"
            )
            return
        
        # Para datasets grandes, no abrir automáticamente
        # para evitar problemas de memoria al cargar la UI
        # El umbral es dinámico según la RAM del sistema
        auto_open_threshold = Config.get_similarity_dialog_auto_open_threshold()
        if analysis.total_files > auto_open_threshold:
            self.logger.info(
                f"Dataset grande ({analysis.total_files} archivos, "
                f"umbral: {auto_open_threshold}). "
                "Diálogo no abierto automáticamente para evitar problemas de memoria."
            )
            QMessageBox.information(
                self.main_window,
                "Análisis completado",
                f"Se analizaron {analysis.total_files} archivos con éxito.\n\n"
                "Debido al tamaño del dataset, el diálogo de gestión no se "
                "abre automáticamente para evitar problemas de memoria.\n\n"
                "Haz clic en 'Gestionar ahora' cuando estés listo."
            )
            return
        
        # Abrir automáticamente el diálogo de gestión con slider (solo datasets pequeños)
        self._open_similarity_dialog_with_analysis(analysis)
    
    def _on_similarity_analysis_error(self, error_message: str):
        """
        Maneja errores durante el análisis
        
        Args:
            error_message: Mensaje de error con traceback
        """
        self.logger.error(f"Error en análisis de similares: {error_message}")
        
        # Cerrar diálogo de progreso
        if self.similarity_progress_dialog:
            self.similarity_progress_dialog.reject()
            self.similarity_progress_dialog = None
        
        # Limpiar worker
        if self.similarity_worker:
            self.similarity_worker.deleteLater()
            self.similarity_worker = None
        
        # Mostrar error al usuario
        QMessageBox.critical(
            self.main_window,
            "Error en análisis",
            f"Ocurrió un error durante el análisis:\n\n{error_message[:500]}"
        )
    
    def _on_similarity_analysis_cancelled(self):
        """Maneja la cancelación del análisis por el usuario"""
        self.logger.info("Análisis de similares cancelado por el usuario")
        
        # Detener worker
        if self.similarity_worker:
            self.similarity_worker.stop()
            self.similarity_worker.wait(2000)  # Esperar 2 segundos
            self.similarity_worker.deleteLater()
            self.similarity_worker = None
        
        # Cerrar diálogo
        if self.similarity_progress_dialog:
            self.similarity_progress_dialog.reject()
            self.similarity_progress_dialog = None
    
    def _update_similar_duplicates_card(self, results):
        """
        Actualiza la card de similares con los resultados del análisis.
        
        Args:
            results: DuplicateAnalysisResult
        """
        if 'similar_files' not in self.tool_cards:
            return
        
        card = self.tool_cards['similar_files']
        
        if results.total_groups > 0:
            size_text = f"~{format_size(results.space_potential)} recuperables"
            card.set_status_with_results(
                f"{results.total_groups} grupos detectados",
                size_text
            )
            card.action_button.setText("Gestionar ahora")
        else:
            card.set_status_no_results("No se encontraron duplicados similares")
            # No cambiar action_button porque está oculto en no_results
        
        # Actualizar descripción para indicar que ya se analizó
        card.description_label.setText(
            "Detecta fotos visualmente similares pero no idénticas "
            "(recortes, rotaciones, ediciones). Análisis completado."
        )
    
    def _update_similar_duplicates_card_after_analysis(self, analysis):
        """
        Actualiza la card después del análisis inicial.
        
        Args:
            analysis: SimilarFilesAnalysis con hashes calculados
        """
        if 'similar_files' not in self.tool_cards:
            return
        
        card = self.tool_cards['similar_files']
        
        # Verificar si hay archivos analizados
        if analysis.total_files == 0:
            card.set_status_no_results("No hay archivos para analizar")
            card.description_label.setText(
                "No se encontraron imágenes o vídeos para analizar."
            )
        elif not analysis.perceptual_hashes or len(analysis.perceptual_hashes) == 0:
            card.set_status_no_results("No se encontraron archivos similares")
            card.description_label.setText(
                f"{analysis.total_files} archivos analizados. "
                "No se encontraron similitudes visuales."
            )
        else:
            # Mostrar que el análisis está completado con hashes calculados
            card.set_status_with_results(
                f"{len(analysis.perceptual_hashes)} archivos analizados",
                "Listo para ajustar sensibilidad"
            )
            card.action_button.setText("Gestionar ahora")
            
            # Actualizar descripción
            card.description_label.setText(
                "Análisis completado. Puedes ajustar la sensibilidad "
                "interactivamente para detectar más o menos similitudes."
            )
    
    def _open_similarity_dialog_with_analysis(self, analysis):
        """
        Abre el diálogo de gestión con el análisis (slider interactivo).
        
        Args:
            analysis: SimilarFilesAnalysis con hashes calculados
        """
        from ui.dialogs.similar_files_dialog import SimilarFilesDialog
        
        dialog = SimilarFilesDialog(analysis, self.main_window)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            # Usuario ejecutó acciones, ejecutar con worker
            self._execute_tool_action("similar_files", dialog)
    
    def _convert_result_to_analysis(self, result):
        """
        Convierte DuplicateAnalysisResult obsoleto a SimilarFilesAnalysis.
        
        (Para compatibilidad con snapshots antiguos)
        
        Args:
            result: DuplicateAnalysisResult
            
        Returns:
            SimilarFilesAnalysis o None si no es posible convertir
        """
        # Por ahora, retornamos None para forzar re-análisis
        # En el futuro podríamos implementar conversión si necesario
        self.logger.warning(
            "No se puede convertir resultado antiguo, "
            "se requiere re-análisis"
        )
        return None
    
    def _open_similarity_dialog(self, results):
        """
        DEPRECATED: Usa _open_similarity_dialog_with_analysis en su lugar.
        
        Mantiene compatibilidad con código antiguo.
        
        Args:
            results: DuplicateAnalysisResult
        """
        from ui.dialogs.similar_files_dialog import SimilarFilesDialog
        
        # Intentar convertir o mostrar advertencia
        self.logger.warning(
            "Usando método deprecated _open_similarity_dialog, "
            "considera usar _open_similarity_dialog_with_analysis"
        )
        
        # Crear análisis temporal con grupos
        from services.similar_files_detector import SimilarFilesAnalysis
        temp_analysis = SimilarFilesAnalysis()
        temp_analysis.groups = results.groups
        temp_analysis.total_files = results.total_files
        
        dialog = SimilarFilesDialog(temp_analysis, self.main_window)
        dialog.exec()

    

