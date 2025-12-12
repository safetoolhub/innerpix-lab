"""
Stage 3: Grid de herramientas.
Muestra el resumen del análisis y el grid de herramientas disponibles.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QGridLayout, QMessageBox,
    QDialog, QProgressDialog, QPushButton
)
from PyQt6.QtCore import QTimer, Qt
import qtawesome as qta

from config import Config
from utils.settings_manager import settings_manager
from .base_stage import BaseStage
from ui.styles.design_system import DesignSystem
from ui.widgets.summary_card import SummaryCard
from ui.widgets.tool_card import ToolCard
from ui.dialogs.live_photos_dialog import LivePhotosDialog
from ui.dialogs.heic_dialog import HeicDialog
from ui.dialogs.duplicates_exact_dialog import DuplicatesExactDialog
from ui.dialogs.file_organizer_dialog import FileOrganizerDialog
from ui.dialogs.file_renamer_dialog import FileRenamerDialog
from ui.dialogs.zero_byte_dialog import ZeroByteDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.duplicates_similar_progress_dialog import SimilarFilesProgressDialog
from utils.format_utils import format_size, format_file_count
from ui.workers import DuplicatesSimilarAnalysisWorker
from utils.logger import log_section_header_discrete

# Importar tool cards
from ui.screens.tool_cards import (
    create_live_photos_card,
    create_heic_card,
    create_duplicates_exact_card,
    create_duplicates_similar_card,
    create_file_organizer_card,
    create_file_renamer_card,
    create_zero_byte_card,
)
# Importar similarity handler
from ui.screens.similarity_handlers import SimilarityAnalysisHandler


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
        
        # Worker y diálogos para análisis de similares (manejado por handler)
        self.similarity_handler = None  # Se inicializa en _create_tools_grid

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
        self.main_layout.addSpacing(DesignSystem.SPACE_6)  # Reducido para optimizar espacio vertical

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

        # Actualizar estadísticas de la summary card (datos ya calculados en Stage 2)
        total_files = self.analysis_results.scan.total_files
        total_size = self.analysis_results.scan.total_size
        
        # Calcular espacio recuperable (rápido, solo suma valores ya calculados)
        recoverable = self._calculate_recoverable_space()
        
        # Mostrar estadísticas
        self.summary_card.update_stats(total_files, total_size)
        self.summary_card.update_recoverable_space(recoverable)

        # Añadir stretch después de la summary card para mantener el layout
        self.main_layout.addStretch()

        # Crear grid de herramientas con delay escalonado
        QTimer.singleShot(200, self._create_tools_grid)

    def _calculate_recoverable_space(self) -> int:
        """
        Calcula el espacio total recuperable de todas las herramientas.
        
        Returns:
            Bytes totales recuperables (0 si no hay análisis disponibles)
        """
        total = 0
        
        # Ahora los análisis se hacen bajo demanda, así que solo sumamos si existen
        # Live Photos
        if hasattr(self.analysis_results, 'live_photos') and self.analysis_results.live_photos:
            total += self.analysis_results.live_photos.space_to_free
        
        # HEIC/JPG
        if hasattr(self.analysis_results, 'heic') and self.analysis_results.heic:
            # Usar el mayor ahorro entre mantener JPG o mantener HEIC
            savings_jpg = getattr(self.analysis_results.heic, 'potential_savings_keep_jpg', 0) or 0
            savings_heic = getattr(self.analysis_results.heic, 'potential_savings_keep_heic', 0) or 0
            total += max(savings_jpg, savings_heic)
        
        # Duplicados exactos
        if hasattr(self.analysis_results, 'duplicates') and self.analysis_results.duplicates:
            total += self.analysis_results.duplicates.space_wasted or 0
        
        # Archivos de 0 bytes
        if hasattr(self.analysis_results, 'zero_byte') and self.analysis_results.zero_byte:
            total += self.analysis_results.zero_byte.bytes_total or 0
        
        return total

    def _create_tools_grid(self):
        """Crea el grid 2x4 con las 7 herramientas"""
        # Limpiar grid existente si ya existe (para evitar duplicación al refrescar)
        if self.tools_grid:
            # Remover del layout
            self.main_layout.removeWidget(self.tools_grid)
            # Ocultar y eliminar el widget antiguo
            self.tools_grid.hide()
            self.tools_grid.setParent(None)
            self.tools_grid.deleteLater()
            self.tools_grid = None
        
        # Limpiar diccionario de cards antiguas
        self.tool_cards.clear()
        
        # Container para el grid
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(10)  # Reducido para optimizar espacio vertical
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Nota: Los análisis se hacen bajo demanda, así que todas las cards empiezan sin datos
        
        # Fila 0: Archivos Vacíos + HEIC/JPG
        zero_byte_card = create_zero_byte_card(self.analysis_results, self._on_tool_clicked)
        grid_layout.addWidget(zero_byte_card, 0, 0)
        self.tool_cards['zero_byte'] = zero_byte_card
        
        heic_card = create_heic_card(self.analysis_results, self._on_tool_clicked)
        grid_layout.addWidget(heic_card, 0, 1)
        self.tool_cards['heic'] = heic_card

        # Fila 1: Live Photos + Duplicados Exactos
        live_photos_card = create_live_photos_card(self.analysis_results, self._on_tool_clicked)
        grid_layout.addWidget(live_photos_card, 1, 0)
        self.tool_cards['live_photos'] = live_photos_card

        exact_dup_card = create_duplicates_exact_card(self.analysis_results, self._on_tool_clicked)
        grid_layout.addWidget(exact_dup_card, 1, 1)
        self.tool_cards['exact_copies'] = exact_dup_card

        # Fila 2: Archivos Similares + (espacio vacío)
        similar_dup_card = create_duplicates_similar_card(self._on_tool_clicked)
        grid_layout.addWidget(similar_dup_card, 2, 0)
        self.tool_cards['similar_files'] = similar_dup_card

        # Fila 3: Organizar + Renombrar (herramientas de reorganización juntas)
        organize_card = create_file_organizer_card(self._on_tool_clicked)
        grid_layout.addWidget(organize_card, 3, 0)
        self.tool_cards['folder-move'] = organize_card

        rename_card = create_file_renamer_card(self._on_tool_clicked)
        grid_layout.addWidget(rename_card, 3, 1)
        self.tool_cards['rename-box'] = rename_card
        
        # Inicializar similarity handler después de crear las cards
        self.similarity_handler = SimilarityAnalysisHandler(
            parent_window=self,
            main_window=self.main_window,
            analysis_results=self.analysis_results,
            metadata_cache=self.metadata_cache,
            tool_cards=self.tool_cards,
            logger=self.logger
        )

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

    # Card creation methods moved to ui/screens/tool_cards/
    # They are now imported as functions

    def _on_tool_clicked(self, tool_id: str):
        """
        Maneja el clic en una tool card y abre el diálogo correspondiente
        """
        self.logger.info(f"Clic en herramienta: {tool_id}")

        if not self.analysis_results:
            QMessageBox.warning(self.main_window, "Error", "No hay datos de análisis disponibles")
            return

        # Verificar si necesitamos ejecutar análisis primero (usando hasattr)
        should_analyze = False
        
        if tool_id == 'live_photos' and not (hasattr(self.analysis_results, 'live_photos') and self.analysis_results.live_photos):
            should_analyze = True
        elif tool_id == 'heic' and not (hasattr(self.analysis_results, 'heic') and self.analysis_results.heic):
            should_analyze = True
        elif tool_id == 'exact_copies' and not (hasattr(self.analysis_results, 'duplicates') and self.analysis_results.duplicates):
            should_analyze = True
        elif tool_id == 'zero_byte' and not (hasattr(self.analysis_results, 'zero_byte') and self.analysis_results.zero_byte):
            should_analyze = True
        elif tool_id == 'folder-move' and not (hasattr(self.analysis_results, 'organization') and self.analysis_results.organization):
            should_analyze = True
        elif tool_id == 'rename-box' and not (hasattr(self.analysis_results, 'renaming') and self.analysis_results.renaming):
            should_analyze = True
            
        if should_analyze:
            # Ejecutar análisis bajo demanda
            self._run_analysis_and_open_dialog(tool_id)
            return

        
        # Abrir diálogo correspondiente si ya tenemos datos
        dialog = None
        
        if tool_id == 'live_photos':
            if hasattr(self.analysis_results, 'live_photos') and self.analysis_results.live_photos:
                live_photo_data = self.analysis_results.live_photos
                if live_photo_data.items_count > 0:
                    dialog = LivePhotosDialog(live_photo_data, self.main_window)
                else:
                    QMessageBox.information(self.main_window, "Info", "No se encontraron Live Photos.")

        elif tool_id == 'heic':
            if hasattr(self.analysis_results, 'heic') and self.analysis_results.heic:
                heic_data = self.analysis_results.heic
                if heic_data.items_count > 0:
                    dialog = HeicDialog(heic_data, self.main_window)
                else:
                     QMessageBox.information(self.main_window, "Info", "No se encontraron pares HEIC/JPG.")

        elif tool_id == 'exact_copies':
            if hasattr(self.analysis_results, 'duplicates') and self.analysis_results.duplicates:
                dup_data = self.analysis_results.duplicates
                if dup_data.total_groups > 0:
                    dialog = DuplicatesExactDialog(dup_data, self.main_window, self.metadata_cache)
                else:
                     QMessageBox.information(self.main_window, "Info", "No se encontraron copias exactas.")

        elif tool_id == 'similar_files':
            # Similares requieren configuración previa y tienen su propio flujo
            if self.similarity_handler:
                self.similarity_handler.start_analysis()
            return

        elif tool_id == 'folder-move':
            # Organizing puede funcionar sin análisis previo (usa defaults o analiza on-fly)
            org_data = getattr(self.analysis_results, 'organization', None) if hasattr(self.analysis_results, 'organization') else None
            dialog = FileOrganizerDialog(org_data, self.main_window, self.metadata_cache)

        elif tool_id == 'rename-box':
            # Renaming igual
            rename_data = getattr(self.analysis_results, 'renaming', None) if hasattr(self.analysis_results, 'renaming') else None
            dialog = FileRenamerDialog(rename_data, self.main_window)
            
        elif tool_id == 'zero_byte':
            if hasattr(self.analysis_results, 'zero_byte') and self.analysis_results.zero_byte:
                zero_byte_data = self.analysis_results.zero_byte
                if zero_byte_data.items_count > 0:
                    dialog = ZeroByteDialog(zero_byte_data, self.main_window)
                else:
                     QMessageBox.information(self.main_window, "Info", "No se encontraron archivos vacíos.")

        if dialog:
            result = dialog.exec()
            # Si el usuario aceptó el diálogo, ejecutar las acciones
            if result == QDialog.DialogCode.Accepted:
                self._execute_tool_action(tool_id, dialog)
            
    def _run_analysis_and_open_dialog(self, tool_id: str):
        """
        Ejecuta el análisis específico para una herramienta y luego abre su diálogo.
        """
        from ui.workers import (
            LivePhotosAnalysisWorker,
            HeicAnalysisWorker,
            DuplicatesExactAnalysisWorker,
            ZeroByteAnalysisWorker,
            FileOrganizerAnalysisWorker,
            FileRenamerAnalysisWorker
        )
        from PyQt6.QtWidgets import QProgressDialog
        
        # Mapeo de tool_id a Worker Class
        worker_map = {
            'live_photos': (LivePhotosAnalysisWorker, "Analizando Live Photos..."),
            'heic': (HeicAnalysisWorker, "Buscando duplicados HEIC/JPG..."),
            'exact_copies': (DuplicatesExactAnalysisWorker, "Buscando copias exactas..."),
            'zero_byte': (ZeroByteAnalysisWorker, "Buscando archivos vacíos..."),
            'folder-move': (FileOrganizerAnalysisWorker, "Analizando estructura..."),
            'rename-box': (FileRenamerAnalysisWorker, "Analizando nombres...")
        }
        
        if tool_id not in worker_map:
            return

        WorkerClass, message = worker_map[tool_id]
        
        # Crear diálogo de progreso
        progress = QProgressDialog(message, "Cancelar", 0, 0, self.main_window)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        # Crear worker
        worker = WorkerClass(Path(self.selected_folder), self.metadata_cache)
        
        def on_finished(result):
            progress.close()
            if result:
                # Guardar resultado en analysis_results
                if tool_id == 'live_photos':
                    self.analysis_results.live_photos = result
                    # Refrescar el grid completo para actualizar la card
                    self._create_tools_grid()
                    
                elif tool_id == 'heic':
                    self.analysis_results.heic = result
                    self._create_tools_grid()
                    
                elif tool_id == 'exact_copies':
                    self.analysis_results.duplicates = result
                    self._create_tools_grid()
                    
                elif tool_id == 'zero_byte':
                    self.analysis_results.zero_byte = result
                    self._create_tools_grid()
                
                # Update summary card recoverable space
                recoverable = self._calculate_recoverable_space()
                if self.summary_card:
                    self.summary_card.update_recoverable_space(recoverable)

                # Abrir el diálogo automáticamente
                self._on_tool_clicked(tool_id)
                
            worker.deleteLater()
            
        def on_error(msg):
            progress.close()
            QMessageBox.critical(self.main_window, "Error", f"Error en análisis: {msg}")
            worker.deleteLater()
            
        worker.progress_update.connect(
            lambda c, t, m: progress.setLabelText(f"{message}\n{m}")
        )
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        
        progress.canceled.connect(worker.stop)
        worker.start()
        progress.exec()
    
    def _execute_tool_action(self, tool_id: str, dialog):
        """
        Ejecuta las acciones de una herramienta usando el worker correspondiente.
        
        Args:
            tool_id: ID de la herramienta ('live_photos', 'heic', etc)
            dialog: Diálogo que contiene el accepted_plan
        """
        from ui.workers import (
            LivePhotosExecutionWorker,
            HeicExecutionWorker,
            DuplicatesExecutionWorker,
            FileOrganizerExecutionWorker,
            FileRenamerExecutionWorker,
            ZeroByteExecutionWorker,
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
            # LivePhotosExecutionWorker espera (service, analysis: dataclass, create_backup, dry_run)
            worker = LivePhotosExecutionWorker(
                service,
                analysis=plan.get('analysis'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'heic':
            from services.heic_remover_service import HEICRemover
            remover = HEICRemover()
            # HeicExecutionWorker espera (remover, analysis: dataclass, keep_format, create_backup, dry_run)
            worker = HeicExecutionWorker(
                remover=remover,
                analysis=plan.get('analysis'),
                keep_format=plan.get('keep_format', 'file-jpg-box'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'exact_copies':
            from services.duplicates_exact_service import DuplicatesExactService
            detector = DuplicatesExactService()
            # DuplicatesExecutionWorker espera (detector, groups, keep_strategy, create_backup, dry_run, metadata_cache)
            worker = DuplicatesExecutionWorker(
                detector=detector,
                groups=plan.get('groups', []),
                keep_strategy=plan.get('keep_strategy', 'first'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False),
                metadata_cache=self.metadata_cache
            )
        
        elif tool_id == 'similar_files':
            from services.duplicates_similar_service import DuplicatesSimilarService
            detector = DuplicatesSimilarService()
            # DuplicatesExecutionWorker espera (detector, groups, keep_strategy, create_backup, dry_run, metadata_cache)
            worker = DuplicatesExecutionWorker(
                detector=detector,
                groups=plan.get('groups', []),
                keep_strategy=plan.get('keep_strategy', 'manual'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False),
                metadata_cache=self.metadata_cache
            )
        
        elif tool_id == 'folder-move':
            from services.file_organizer_service import FileOrganizer
            organizer = FileOrganizer()
            # FileOrganizerExecutionWorker espera (organizer, analysis: dataclass, cleanup_empty_dirs, create_backup, dry_run)
            worker = FileOrganizerExecutionWorker(
                organizer=organizer,
                analysis=plan.get('analysis'),
                cleanup_empty_dirs=plan.get('cleanup_empty_dirs', True),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'rename-box':
            from services.file_renamer_service import FileRenamer
            renamer = FileRenamer()
            # FileRenamerExecutionWorker espera (renamer, analysis: dataclass, create_backup, dry_run)
            worker = FileRenamerExecutionWorker(
                renamer=renamer,
                analysis=plan.get('analysis'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )

        elif tool_id == 'zero_byte':
            from services.zero_byte_service import ZeroByteService
            service = ZeroByteService()
            # ZeroByteExecutionWorker espera (service, files, create_backup, dry_run)
            worker = ZeroByteExecutionWorker(
                service=service,
                files=plan.get('files_to_delete', []),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        if not worker:
            self.logger.error(f"No se pudo crear worker para {tool_id}")
            return
        
        # Variable para controlar si ya se canceló
        is_cancelled = False
        
        # Conectar señales del worker
        def on_progress(current, total, message):
            # Ignorar actualizaciones si ya se canceló
            if is_cancelled:
                return
            if total > 0:
                progress_dialog.setValue(int((current / total) * 100))
            progress_dialog.setLabelText(message)
        
        def on_finished(result):
            # Ignorar si ya se canceló
            if is_cancelled:
                return
            
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
            # Ignorar si ya se canceló
            if is_cancelled:
                return
            
            progress_dialog.close()
            self.logger.error(f"Error en operación {tool_id}: {error_message}")
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"Ocurrió un error:\n\n{error_message[:500]}"
            )
            worker.deleteLater()
        
        def on_cancel():
            """Maneja la cancelación del diálogo de progreso"""
            nonlocal is_cancelled
            is_cancelled = True
            
            # Solicitar al worker que se detenga
            try:
                worker.stop()
            except RuntimeError:
                # Worker ya fue eliminado, cerrar el diálogo directamente
                progress_dialog.close()
                self.logger.info(f"Operación {tool_id} ya finalizada al momento de cancelar")
                return
            
            # Actualizar el mensaje del diálogo mientras esperamos
            progress_dialog.setLabelText("Cancelando operación, por favor espera...")
            progress_dialog.setCancelButton(None)  # Deshabilitar el botón de cancelar
            
            # Desconectar señales de procesamiento pero mantener finished para limpieza
            try:
                worker.progress_update.disconnect(on_progress)
            except (RuntimeError, TypeError):
                # Worker eliminado o señal ya desconectada
                pass
            
            # Conectar un handler simplificado para finished que solo limpia
            def on_cancelled_cleanup():
                progress_dialog.close()
                try:
                    worker.deleteLater()
                except RuntimeError:
                    pass  # Ya fue eliminado
                self.logger.info(f"Operación {tool_id} cancelada y limpiada correctamente")
            
            # Desconectar handlers anteriores y conectar el de limpieza
            try:
                worker.finished.disconnect(on_finished)
                worker.error.disconnect(on_error)
            except (RuntimeError, TypeError):
                # Worker eliminado o señales ya desconectadas
                pass
            
            # Intentar reconectar solo si el worker todavía existe
            try:
                worker.finished.connect(on_cancelled_cleanup)
                worker.error.connect(on_cancelled_cleanup)
            except RuntimeError:
                # Worker ya fue eliminado, limpiar directamente
                on_cancelled_cleanup()
                return
            
            self.logger.info(f"Operación {tool_id} - Cancelación solicitada por el usuario")
        
        worker.progress_update.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        
        # Conectar cancelación con handler explícito
        progress_dialog.canceled.connect(on_cancel)
        
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
    # Similarity handling moved to ui/screens/similarity_handlers.py
    # Handle through self.similarity_handler
    

