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
from ui.screens.summary_card import SummaryCard
from ui.screens.tool_card import ToolCard
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
        self.main_layout.addSpacing(2)

        # Crear y mostrar header
        self.header = self.create_header(
            on_settings_clicked=self._on_settings_clicked,
            on_about_clicked=self._on_about_clicked
        )
        self.main_layout.addWidget(self.header)
        self.main_layout.addSpacing(DesignSystem.SPACE_4)  # Reducido de SPACE_6 para optimizar espacio vertical

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
        num_images = len(self.analysis_results.scan.images) if hasattr(self.analysis_results.scan, 'images') else 0
        num_videos = len(self.analysis_results.scan.videos) if hasattr(self.analysis_results.scan, 'videos') else 0
        num_others = len(self.analysis_results.scan.others) if hasattr(self.analysis_results.scan, 'others') else 0
        
        # Mostrar estadísticas
        self.summary_card.update_stats(total_files, total_size, num_images, num_videos, num_others)

        # Añadir stretch después de la summary card para mantener el layout
        self.main_layout.addStretch()

        # Crear grid de herramientas con delay escalonado
        QTimer.singleShot(200, self._create_tools_grid)

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
        grid_layout.setSpacing(8)  # Reducido de 10 para optimizar espacio vertical
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
        self.tool_cards['duplicates_exact'] = exact_dup_card

        # Fila 2: Archivos Similares + (espacio vacío)
        similar_dup_card = create_duplicates_similar_card(self._on_tool_clicked)
        grid_layout.addWidget(similar_dup_card, 2, 0)
        self.tool_cards['duplicates_similar'] = similar_dup_card

        # Fila 3: Organizar + Renombrar (herramientas de reorganización juntas)
        organize_card = create_file_organizer_card(self._on_tool_clicked)
        grid_layout.addWidget(organize_card, 3, 0)
        self.tool_cards['file_organizer'] = organize_card

        rename_card = create_file_renamer_card(self._on_tool_clicked)
        grid_layout.addWidget(rename_card, 3, 1)
        self.tool_cards['file_renamer'] = rename_card
        
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
        self.main_layout.addSpacing(2)  # Reducido de SPACE_4 para optimizar espacio vertical

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
        # NOTA: file_renamer y file_organizer SIEMPRE requieren análisis fresco porque
        # modifican los archivos (nombres/ubicaciones) y el análisis previo queda obsoleto
        should_analyze = False
        
        if tool_id == 'live_photos' and not (hasattr(self.analysis_results, 'live_photos') and self.analysis_results.live_photos):
            should_analyze = True
        elif tool_id == 'heic' and not (hasattr(self.analysis_results, 'heic') and self.analysis_results.heic):
            should_analyze = True
        elif tool_id == 'duplicates_exact' and not (hasattr(self.analysis_results, 'duplicates') and self.analysis_results.duplicates):
            should_analyze = True
        elif tool_id == 'zero_byte' and not (hasattr(self.analysis_results, 'zero_byte') and self.analysis_results.zero_byte):
            should_analyze = True
        elif tool_id == 'file_organizer':
            # SIEMPRE analizar file_organizer (modifica ubicaciones de archivos)
            should_analyze = True
        elif tool_id == 'file_renamer':
            # SIEMPRE analizar file_renamer (modifica nombres de archivos)
            should_analyze = True
            
        if should_analyze:
            # Ejecutar análisis bajo demanda
            self._run_analysis_and_open_dialog(tool_id)
            return
        
        # Si ya tenemos datos, abrir el diálogo
        self._open_tool_dialog(tool_id)
    
    def _open_tool_dialog(self, tool_id: str):
        """
        Abre el diálogo correspondiente a una herramienta sin hacer análisis.
        Asume que el análisis ya está disponible en self.analysis_results.
        """
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

        elif tool_id == 'duplicates_exact':
            if hasattr(self.analysis_results, 'duplicates') and self.analysis_results.duplicates:
                dup_data = self.analysis_results.duplicates
                if dup_data.total_groups > 0:
                    dialog = DuplicatesExactDialog(dup_data, self.main_window)
                else:
                     QMessageBox.information(self.main_window, "Info", "No se encontraron copias exactas.")

        elif tool_id == 'duplicates_similar':
            # Similares requieren configuración previa y tienen su propio flujo
            if self.similarity_handler:
                self.similarity_handler.start_analysis()
            return

        elif tool_id == 'file_organizer':
            # Organizing puede funcionar sin análisis previo (usa defaults o analiza on-fly)
            org_data = getattr(self.analysis_results, 'organization', None) if hasattr(self.analysis_results, 'organization') else None
            dialog = FileOrganizerDialog(org_data, self.main_window)

        elif tool_id == 'file_renamer':
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
            'duplicates_exact': (DuplicatesExactAnalysisWorker, "Buscando copias exactas..."),
            'zero_byte': (ZeroByteAnalysisWorker, "Buscando archivos vacíos..."),
            'file_organizer': (FileOrganizerAnalysisWorker, "Analizando estructura..."),
            'file_renamer': (FileRenamerAnalysisWorker, "Analizando nombres...")
        }
        
        if tool_id not in worker_map:
            return

        WorkerClass, message = worker_map[tool_id]
        
        # Crear diálogo de progreso
        progress = QProgressDialog(message, "Cancelar", 0, 0, self.main_window)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        # Crear worker - algunos servicios ya no necesitan metadata_cache
        refactorized_tools = {'live_photos', 'heic', 'duplicates_exact', 'zero_byte', 'file_renamer', 'file_organizer'}
        if tool_id in refactorized_tools:
            worker = WorkerClass(Path(self.selected_folder))
        else:
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
                    
                elif tool_id == 'duplicates_exact':
                    self.analysis_results.duplicates = result
                    self._create_tools_grid()
                    
                elif tool_id == 'zero_byte':
                    self.analysis_results.zero_byte = result
                    self._create_tools_grid()
                
                elif tool_id == 'file_organizer':
                    self.analysis_results.organization = result
                    self._create_tools_grid()
                
                elif tool_id == 'file_renamer':
                    self.analysis_results.renaming = result
                    self._create_tools_grid()
                
                # Abrir el diálogo automáticamente, pero sin volver a analizar
                self._open_tool_dialog(tool_id)
                
            worker.deleteLater()
            
        def on_error(msg):
            progress.close()
            QMessageBox.critical(self.main_window, "Error", f"Error en análisis: {msg}")
            worker.deleteLater()
            
        def on_progress_update(current, total, msg):
            # Si total > 0, usar barra determinada. Si no, indeterminada.
            if total > 0:
                if progress.maximum() != total:
                    progress.setMaximum(total)
                progress.setValue(current)
            else:
                if progress.maximum() != 0:
                    progress.setMaximum(0)
                    progress.setValue(0)
            
            progress.setLabelText(f"{message}\n{msg}")

        worker.progress_update.connect(on_progress_update)
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
        destructive_tools = ['live_photos', 'heic', 'duplicates_exact', 'duplicates_similar', 'zero_byte']
        
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
            from services.heic_service import HeicService
            service = HeicService()
            # HeicExecutionWorker espera (service, analysis: dataclass, keep_format, create_backup, dry_run)
            worker = HeicExecutionWorker(
                service=service,
                analysis=plan.get('analysis'),
                keep_format=plan.get('keep_format', 'jpg'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'duplicates_exact':
            from services.duplicates_exact_service import DuplicatesExactService
            detector = DuplicatesExactService()
            # DuplicatesExecutionWorker espera (detector, analysis: dataclass, keep_strategy, create_backup, dry_run, metadata_cache)
            worker = DuplicatesExecutionWorker(
                detector=detector,
                analysis=plan.get('analysis'),
                keep_strategy=plan.get('keep_strategy', 'first'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False),
                metadata_cache=self.metadata_cache
            )
        
        elif tool_id == 'duplicates_similar':
            from services.duplicates_similar_service import DuplicatesSimilarService
            detector = DuplicatesSimilarService()
            # DuplicatesExecutionWorker espera (detector, analysis: dataclass, keep_strategy, create_backup, dry_run, metadata_cache)
            worker = DuplicatesExecutionWorker(
                detector=detector,
                analysis=plan.get('analysis'),
                keep_strategy=plan.get('keep_strategy', 'manual'),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False),
                metadata_cache=self.metadata_cache
            )
        
        elif tool_id == 'file_organizer':
            from services.file_organizer_service import FileOrganizerService
            organizer = FileOrganizerService()
            # FileOrganizerExecutionWorker espera (organizer, analysis: dataclass, cleanup_empty_dirs, create_backup, dry_run)
            worker = FileOrganizerExecutionWorker(
                organizer=organizer,
                analysis=plan.get('analysis'),
                cleanup_empty_dirs=plan.get('cleanup_empty_dirs', True),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'file_renamer':
            from services.file_renamer_service import FileRenamerService
            renamer = FileRenamerService()
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
            # ZeroByteExecutionWorker espera (service, analysis: dataclass, create_backup, dry_run)
            worker = ZeroByteExecutionWorker(
                service=service,
                analysis=plan.get('analysis'),
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
            
            # Desconectar señal de cancelación antes de cerrar
            try:
                progress_dialog.canceled.disconnect(on_cancel)
            except (RuntimeError, TypeError):
                pass
            
            progress_dialog.close()
            
            # Registrar resultado
            log_msg = f"Operación {tool_id} completada"
            if hasattr(result, 'success'):
                log_msg += f" (Success={result.success})"
            self.logger.info(log_msg)
            
            # Log detallado en debug para no inundar el info con listas enormes de archivos
            self.logger.debug(f"Resultado detallado de {tool_id}: {result}")
            
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
                    # Verificar si se debe pedir confirmación antes de reanalizar
                    should_confirm = settings_manager.get_confirm_reanalyze()
                    
                    if should_confirm:
                        # Pedir confirmación al usuario
                        service_message = self._get_service_update_message(tool_id)
                        
                        reply = QMessageBox.question(
                            self.main_window,
                            "Actualizar estadísticas",
                            service_message,
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            QMessageBox.StandardButton.Yes  # Default to Yes
                        )
                        
                        if reply == QMessageBox.StandardButton.Yes:
                            # Re-analyze specific service
                            log_section_header_discrete(self.logger, f"Actualización de estadísticas solicitada para {tool_id}")
                            # NOTA: No invalidamos la caché aquí porque el usuario quiere actualizar estadísticas
                            # La caché ya está actualizada, solo necesitamos recalcular el análisis del servicio
                            QTimer.singleShot(500, lambda: self._update_service_stats(tool_id))
                        else:
                            # User chose to skip re-analysis
                            self.logger.info("Usuario omitió re-análisis, las estadísticas pueden estar desactualizadas")
                            
                            # NOTA: La caché ya se actualizó automáticamente durante la operación.
                            # Esta invalidación completa es opcional y conservadora por si hubo
                            # algún error en las actualizaciones individuales.
                            self._invalidate_metadata_cache()
                            
                            # Mostrar banner de advertencia
                            if self.stale_banner:
                                self.stale_banner.show()
                                # Asegurar que el banner sea visible (scroll to top if needed)
                                if hasattr(self.main_window, 'scroll_area'):
                                    self.main_window.scroll_area.ensureWidgetVisible(self.stale_banner)
                    else:
                        # Actualizar automáticamente sin confirmación
                        self.logger.info(f"Actualizando estadísticas automáticamente para {tool_id} (sin confirmación)")
                        log_section_header_discrete(self.logger, f"Actualización automática de estadísticas para {tool_id}")
                        # Usar QTimer con lambda que capture excepciones
                        def safe_update():
                            try:
                                self._update_service_stats(tool_id, auto_update=True)
                            except Exception as e:
                                self.logger.error(f"Error crítico en actualización automática de {tool_id}: {e}")
                                import traceback
                                self.logger.error(traceback.format_exc())
                                QMessageBox.critical(
                                    self.main_window,
                                    "Error en actualización",
                                    f"Error actualizando estadísticas de {tool_id}:\n\n{str(e)[:300]}"
                                )
                        QTimer.singleShot(500, safe_update)
        
        def on_error(error_message):
            # Ignorar si ya se canceló
            if is_cancelled:
                return
            
            # Desconectar señal de cancelación antes de cerrar
            try:
                progress_dialog.canceled.disconnect(on_cancel)
            except (RuntimeError, TypeError):
                pass
                
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
    
    def _get_service_update_message(self, tool_id: str) -> str:
        """
        Genera el mensaje específico para actualizar estadísticas de un servicio.
        
        Args:
            tool_id: ID del servicio (live_photos, heic, duplicates_exact, etc.)
            
        Returns:
            Mensaje personalizado para el diálogo
        """
        service_names = {
            'live_photos': 'Live Photos',
            'heic': 'HEIC/JPG',
            'duplicates_exact': 'Duplicados Exactos',
            'duplicates_similar': 'Duplicados Similares', 
            'file_organizer': 'Organización de Archivos',
            'file_renamer': 'Renombrado de Archivos',
            'zero_byte': 'Archivos Vacíos'
        }
        
        service_name = service_names.get(tool_id, tool_id)
        
        return (
            f"¿Deseas actualizar las estadísticas de {service_name}?\n\n"
            f"Esto recalculará únicamente el análisis de {service_name} para reflejar "
            f"los cambios realizados. La caché de metadatos ya está actualizada.\n\n"
            f"Nota: Esta operación es rápida y solo afecta a {service_name}."
        )
    
    def _update_service_stats(self, tool_id: str, auto_update: bool = False) -> None:
        """
        Actualiza las estadísticas de un servicio específico y refresca la UI.
        
        Args:
            tool_id: ID del servicio a actualizar
            auto_update: Si es True, no muestra mensaje de confirmación al finalizar
        """
        self.logger.info(f"Actualizando estadísticas para servicio: {tool_id} (auto_update={auto_update})")
        
        try:
            self.logger.debug(f"Paso 1: Obteniendo análisis actualizado para {tool_id}")
            # Obtener el análisis actualizado para este servicio específico
            updated_analysis = self._get_updated_service_analysis(tool_id)
            self.logger.debug(f"Paso 1 completado: Análisis obtenido = {updated_analysis is not None}")
            
            if updated_analysis:
                self.logger.debug(f"Paso 2: Asignando resultado al objeto analysis_results")
                # Actualizar el análisis en analysis_results según el tipo de servicio
                if tool_id == 'live_photos':
                    self.analysis_results.live_photos = updated_analysis
                elif tool_id == 'heic':
                    self.analysis_results.heic = updated_analysis
                elif tool_id == 'duplicates_exact':
                    self.analysis_results.duplicates = updated_analysis
                elif tool_id == 'duplicates_similar':
                    self.analysis_results.duplicates_similar = updated_analysis
                elif tool_id == 'file_organizer':
                    self.analysis_results.organization = updated_analysis
                elif tool_id == 'file_renamer':
                    self.analysis_results.renaming = updated_analysis
                elif tool_id == 'zero_byte':
                    self.analysis_results.zero_byte = updated_analysis
                else:
                    self.logger.warning(f"No se puede asignar resultado para servicio desconocido: {tool_id}")
                    return
                self.logger.debug(f"Paso 2 completado: Resultado asignado")
                
                # Guardar los resultados actualizados
                self.logger.debug(f"Paso 3: Guardando resultados actualizados")
                self.save_analysis_results(self.analysis_results)
                self.logger.debug(f"Paso 3 completado: Resultados guardados")
                
                # Refrescar toda la UI de Stage 3 con los nuevos datos
                self.logger.debug(f"Paso 4: Refrescando UI de Stage 3")
                self._refresh_stage_3_ui()
                self.logger.debug(f"Paso 4 completado: UI refrescada")
                
                self.logger.info(f"Estadísticas actualizadas exitosamente para {tool_id}")
                
                # Solo mostrar mensaje de éxito si NO es actualización automática
                if not auto_update:
                    service_names = {
                        'live_photos': 'Live Photos',
                        'heic': 'HEIC/JPG',
                        'duplicates_exact': 'Duplicados Exactos',
                        'duplicates_similar': 'Duplicados Similares', 
                        'file_organizer': 'Organización de Archivos',
                        'file_renamer': 'Renombrado de Archivos',
                        'zero_byte': 'Archivos Vacíos'
                    }
                    service_name = service_names.get(tool_id, tool_id)
                    
                    QMessageBox.information(
                        self.main_window,
                        "Estadísticas actualizadas",
                        f"Las estadísticas de {service_name} han sido actualizadas correctamente."
                    )
            else:
                self.logger.warning(f"No se pudo obtener análisis actualizado para {tool_id}")
                
        except Exception as e:
            self.logger.error(f"Error actualizando estadísticas de {tool_id}: {e}")
            QMessageBox.warning(
                self.main_window,
                "Error",
                f"No se pudieron actualizar las estadísticas.\n\n{str(e)}"
            )
    
    def _get_updated_service_analysis(self, tool_id: str):
        """
        Obtiene el análisis actualizado para un servicio específico.
        
        Args:
            tool_id: ID del servicio
            
        Returns:
            Análisis actualizado o None si falla
        """
        try:
            self.logger.debug(f"Iniciando análisis actualizado para {tool_id}")
            # Importar servicios según tool_id
            if tool_id == 'live_photos':
                from services.live_photos_service import LivePhotoService
                service = LivePhotoService()
                self.logger.debug(f"Ejecutando service.analyze() para {tool_id}")
                result = service.analyze()
                self.logger.debug(f"Análisis completado para {tool_id}: {result}")
                return result
                
            elif tool_id == 'heic':
                from services.heic_service import HeicService
                service = HeicService()
                self.logger.debug(f"Ejecutando service.analyze() para {tool_id}")
                result = service.analyze()
                self.logger.debug(f"Análisis completado para {tool_id}: items_count={result.items_count if result else 'None'}")
                return result
                
            elif tool_id == 'duplicates_exact':
                from services.duplicates_exact_service import DuplicatesExactService
                service = DuplicatesExactService()
                self.logger.debug(f"Ejecutando service.analyze() para {tool_id}")
                return service.analyze()
                
            elif tool_id == 'duplicates_similar':
                from services.duplicates_similar_service import DuplicatesSimilarService
                service = DuplicatesSimilarService()
                self.logger.debug(f"Ejecutando service.analyze() para {tool_id}")
                return service.analyze()
                
            elif tool_id == 'file_organizer':
                from services.file_organizer_service import FileOrganizerService
                service = FileOrganizerService()
                self.logger.debug(f"Ejecutando service.analyze() para {tool_id}")
                return service.analyze()
                
            elif tool_id == 'file_renamer':
                from services.file_renamer_service import FileRenamerService
                service = FileRenamerService()
                self.logger.debug(f"Ejecutando service.analyze() para {tool_id}")
                return service.analyze()
                
            elif tool_id == 'zero_byte':
                from services.zero_byte_service import ZeroByteService
                service = ZeroByteService()
                self.logger.debug(f"Ejecutando service.analyze() para {tool_id}")
                return service.analyze()
                
            else:
                self.logger.warning(f"Servicio desconocido: {tool_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error crítico obteniendo análisis para {tool_id}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def _update_tool_card_ui(self, tool_id: str, analysis_result) -> None:
        """
        Método legacy - ahora usamos _refresh_stage_3_ui() para actualizar todo.
        """
        pass  # Implementación movida a _refresh_stage_3_ui
    
    def _refresh_stage_3_ui(self) -> None:
        """
        Refresca la UI completa de Stage 3 con los analysis_results actualizados.
        """
        try:
            self.logger.debug("Refrescando UI de Stage 3 con datos actualizados")
            
            # Limpiar widgets existentes (excepto header que permanece)
            self.logger.debug("Limpiando summary_card...")
            if self.summary_card:
                self.summary_card.hide()
                self.summary_card.setParent(None)
                self.summary_card = None
            
            self.logger.debug("Limpiando tools_grid...")
            if self.tools_grid:
                self.tools_grid.hide()
                self.tools_grid.setParent(None)
                self.tools_grid = None
                
            self.tool_cards.clear()
            
            # Recrear la UI con los datos actualizados
            self.logger.debug("Recreando summary_card...")
            self._show_summary_card()
            
            # Crear el grid de tools inmediatamente (sin delay para refresh)
            self.logger.debug("Recreando tools_grid...")
            self._create_tools_grid()
            
            self.logger.debug("UI de Stage 3 refrescada exitosamente")
            
        except Exception as e:
            self.logger.error(f"Error refrescando UI de Stage 3: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            raise  # Re-lanzar para que se capture en el nivel superior
    
    def _on_reanalyze(self):
        """Maneja el clic en "Reanalizar" (legacy - ahora debería ser raro usarlo)"""
        self.logger.info("Reanalizando carpeta completa (modo legacy)")

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

    

