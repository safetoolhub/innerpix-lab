"""
Stage 3: Grid de herramientas.
Muestra el resumen del análisis y el grid de herramientas disponibles.
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QWidget, QGridLayout, QMessageBox, QDialog
from PyQt6.QtCore import QTimer, pyqtSignal

from .base_stage import BaseStage
from ui.styles.design_system import DesignSystem
from ui.widgets.summary_card import SummaryCard
from ui.widgets.tool_card import ToolCard
from ui.dialogs.live_photos_dialog import LivePhotoCleanupDialog
from ui.dialogs.heic_dialog import HEICDuplicateRemovalDialog
from ui.dialogs.exact_copies_dialog import ExactCopiesDialog
from ui.dialogs.similar_files_dialog import SimilarFilesDialog
from ui.dialogs.organization_dialog import FileOrganizationDialog
from ui.dialogs.renaming_dialog import RenamingPreviewDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.similar_files_config_dialog import SimilarFilesConfigDialog
from ui.dialogs.similar_files_progress_dialog import SimilarFilesProgressDialog
from utils.format_utils import format_size, format_file_count
from services.similar_files_detector import SimilarFilesDetector
from ui.workers import SimilarFilesAnalysisWorker
from pathlib import Path


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

        # Referencias a widgets del estado
        self.header = None
        self.summary_card = None
        self.tools_grid = None
        self.tool_cards = {}  # Dict de tool_id -> ToolCard
        
        # Worker y diálogos para análisis de similares
        self.similarity_worker = None
        self.similarity_progress_dialog = None
        self.similarity_results = None  # Guardar resultados del análisis
        
        # Sistema de re-análisis automático
        self.reanalysis_worker = None  # Worker para re-análisis en background
        self.reanalysis_overlay = None  # Overlay visual de progreso
        self.similarity_results_snapshot = None  # Snapshot de resultados similares antes de invalidar
        self.similarity_timestamp = None  # Timestamp del último análisis de similares
        self.pending_reanalysis = False  # Flag para saber si hay re-análisis pendiente

    def setup_ui(self) -> None:
        """Configura la interfaz de usuario del Stage 3."""
        self.logger.info("Configurando UI del Stage 3")

        # Limpiar el layout principal antes de agregar nuevos widgets
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().hide()
                child.widget().setParent(None)

        # Añadir espaciado encima del header
        self.main_layout.addSpacing(DesignSystem.SPACE_8)

        # Crear y mostrar header
        self.header = self.create_header(
            on_settings_clicked=self._on_settings_clicked,
            on_about_clicked=self._on_about_clicked
        )
        self.main_layout.addWidget(self.header)
        self.main_layout.addSpacing(DesignSystem.SPACE_16)

        # Añadir stretch para mantener el header en la parte superior
        self.main_layout.addStretch()

        # Crear y mostrar summary card con delay
        QTimer.singleShot(300, self._show_summary_card)

        self.logger.info("UI del Stage 3 configurada")

    def cleanup(self) -> None:
        """Limpia los recursos del Stage 3."""
        self.logger.debug("Limpiando Estado 3")

        # Limpiar referencias
        if self.header:
            self.header.hide()
            self.header.setParent(None)
            self.header = None

        if self.summary_card:
            self.summary_card.hide()
            self.summary_card.setParent(None)
            self.summary_card = None

        if self.tools_grid:
            self.tools_grid.hide()
            self.tools_grid.setParent(None)
            self.tools_grid = None

        self.tool_cards.clear()

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
        """Crea el grid 2x3 con las 6 herramientas"""
        # Container para el grid
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(16)  # DesignSystem.SPACE_16
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Obtener datos de análisis (todos dataclasses tipados)
        live_photo_data = self.analysis_results.live_photos
        heic_data = self.analysis_results.heic
        dup_data = self.analysis_results.duplicates

        # Fila 1: Live Photos + HEIC/JPG
        live_photos_card = self._create_live_photos_card(live_photo_data)
        grid_layout.addWidget(live_photos_card, 0, 0)
        self.tool_cards['live_photos'] = live_photos_card

        heic_card = self._create_heic_card(heic_data)
        grid_layout.addWidget(heic_card, 0, 1)
        self.tool_cards['heic'] = heic_card

        # Fila 2: Duplicados Exactos + Similares
        exact_dup_card = self._create_exact_duplicates_card(dup_data)
        grid_layout.addWidget(exact_dup_card, 1, 0)
        self.tool_cards['exact_copies'] = exact_dup_card

        similar_dup_card = self._create_similar_duplicates_card()
        grid_layout.addWidget(similar_dup_card, 1, 1)
        self.tool_cards['similar_files'] = similar_dup_card

        # Fila 3: Organizar + Renombrar
        organize_card = self._create_organize_card()
        grid_layout.addWidget(organize_card, 2, 0)
        self.tool_cards['organize'] = organize_card

        rename_card = self._create_rename_card()
        grid_layout.addWidget(rename_card, 2, 1)
        self.tool_cards['rename'] = rename_card

        # Agregar grid al layout principal
        # Remover el stretch temporal antes de añadir el grid
        if self.main_layout.count() > 3:  # header + spacing + summary_card + stretch
            self.main_layout.takeAt(self.main_layout.count() - 1)  # Remover stretch

        # Añadir espaciado entre summary card y tool cards
        self.main_layout.addSpacing(DesignSystem.SPACE_8)

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
            description='Gestiona los vídeos asociados a tus Live Photos. Puedes conservar '
                       'solo la foto, solo el vídeo, o ambos según tus preferencias.',
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
            card.set_status_ready("No se encontraron Live Photos")

        card.clicked.connect(lambda: self._on_tool_clicked('live_photos'))
        return card

    def _create_heic_card(self, heic_data) -> ToolCard:
        """Crea la card de HEIC/JPG Duplicados"""
        card = ToolCard(
            icon_name='heic',
            title='HEIC/JPG Duplicados',
            description='Elimina fotos duplicadas que están en dos formatos (HEIC y JPG). '
                       'Decide qué formato conservar.',
            action_text='Gestionar ahora'
        )

        # Configurar estado según datos (heic_data es HeicAnalysisResult o None)
        if heic_data and heic_data.total_pairs > 0:
            # Calcular tamaño total (usar el potencial de ahorro)
            savings = max(heic_data.potential_savings_keep_jpg, heic_data.potential_savings_keep_heic)
            size_text = f"~{format_size(savings)} recuperables"
            card.set_status_with_results(
                f"{heic_data.total_pairs} pares encontrados",
                size_text
            )
        else:
            card.set_status_ready("No se encontraron pares HEIC/JPG")

        card.clicked.connect(lambda: self._on_tool_clicked('heic'))
        return card

    def _create_exact_duplicates_card(self, dup_data) -> ToolCard:
        """Crea la card de Copias exactas"""
        card = ToolCard(
            icon_name='content-copy',
            title='Copias exactas',
            description='Encuentra fotos y vídeos copiados (100% idénticos), '
                       'incluso si tienen nombres diferentes. Elimina duplicados.',
            action_text='Gestionar ahora'
        )

        # Configurar estado según datos (dup_data es DuplicateAnalysisResult o None)
        if dup_data and dup_data.total_groups > 0:
            size_text = f"~{format_size(dup_data.space_wasted)} recuperables"
            card.set_status_with_results(
                f"{dup_data.total_groups} grupos detectados",
                size_text
            )
        else:
            card.set_status_ready("No se encontraron copias exactas")

        card.clicked.connect(lambda: self._on_tool_clicked('exact_copies'))
        return card

    def _create_similar_duplicates_card(self) -> ToolCard:
        """Crea la card de Archivos similares (pendiente por defecto)"""
        card = ToolCard(
            icon_name='image-search',
            title='Archivos similares',
            description='Detecta fotos y vídeos visualmente similares: recortes, '
                       'rotaciones, ediciones o diferentes resoluciones.',
            action_text='Configurar y analizar'
        )

        # Por defecto está pendiente
        card.set_status_pending("Este análisis puede tardar unos minutos según la cantidad de archivos.")

        card.clicked.connect(lambda: self._on_tool_clicked('similar_files'))
        return card

    def _create_organize_card(self) -> ToolCard:
        """Crea la card de Organizar Archivos"""
        card = ToolCard(
            icon_name='organize',
            title='Organizar Archivos',
            description='Reorganiza tu colección en carpetas por fecha, origen '
                       '(WhatsApp, Telegram...) o tipo. Previsualiza antes de mover.',
            action_text='Planificar ahora'
        )

        # Siempre está lista
        total = self.analysis_results.scan.total_files
        card.set_status_ready(f"{format_file_count(total)} archivos listos")

        card.clicked.connect(lambda: self._on_tool_clicked('organize'))
        return card

    def _create_rename_card(self) -> ToolCard:
        """Crea la card de Renombrar Archivos"""
        card = ToolCard(
            icon_name='rename',
            title='Renombrar Archivos',
            description='Renombra archivos según patrones personalizados con fechas, '
                       'secuencias o metadatos. Vista previa antes de aplicar cambios.',
            action_text='Configurar ahora'
        )

        # Siempre está lista
        total = self.analysis_results.scan.total_files
        card.set_status_ready(f"{format_file_count(total)} archivos listos")

        card.clicked.connect(lambda: self._on_tool_clicked('rename'))
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
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de Live Photos")
                return
            dialog = LivePhotoCleanupDialog(live_photo_data, self.main_window)

        elif tool_id == 'heic':
            heic_data = self.analysis_results.heic
            if not heic_data or heic_data.total_pairs == 0:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de HEIC/JPG")
                return
            dialog = HEICDuplicateRemovalDialog(heic_data, self.main_window)

        elif tool_id == 'exact_copies':
            dup_data = self.analysis_results.duplicates
            if not dup_data or dup_data.total_groups == 0:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de Copias Exactas")
                return
            dialog = ExactCopiesDialog(dup_data, self.main_window)

        elif tool_id == 'similar_files':
            # Similares requieren configuración previa
            self._on_similar_duplicates_clicked()
            return

        elif tool_id == 'organize':
            org_data = self.analysis_results.organization
            if not org_data or org_data.total_files_to_move == 0:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de Organización")
                return
            dialog = FileOrganizationDialog(org_data, self.main_window)

        elif tool_id == 'rename':
            rename_data = self.analysis_results.renaming
            if not rename_data or rename_data.need_renaming == 0:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de Renombrado")
                return
            dialog = RenamingPreviewDialog(rename_data, self.main_window)

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
        )
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import Qt
        
        if not hasattr(dialog, 'accepted_plan'):
            self.logger.warning(f"Diálogo de {tool_id} no tiene accepted_plan")
            return
        
        plan = dialog.accepted_plan
        self.logger.info(f"Ejecutando acciones de {tool_id} con plan: {list(plan.keys()) if isinstance(plan, dict) else type(plan)}")
        
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
            from services.live_photo_cleaner import LivePhotoCleaner
            cleaner = LivePhotoCleaner()
            # LivePhotoCleanupWorker espera (cleaner, plan: Dict)
            worker = LivePhotoCleanupWorker(cleaner, plan)
        
        elif tool_id == 'heic':
            from services.heic_remover import HEICDuplicateRemover
            remover = HEICDuplicateRemover()
            # HEICRemovalWorker espera (remover, pairs, keep_format, create_backup, dry_run)
            worker = HEICRemovalWorker(
                remover=remover,
                pairs=plan.get('pairs', []),
                keep_format=plan.get('keep_format', 'jpg'),
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
        
        elif tool_id == 'organize':
            from services.file_organizer import FileOrganizer
            organizer = FileOrganizer()
            # FileOrganizerWorker espera (organizer, plan: List[Dict], create_backup, dry_run)
            worker = FileOrganizerWorker(
                organizer=organizer,
                plan=plan.get('plan', []),
                create_backup=plan.get('create_backup', True),
                dry_run=plan.get('dry_run', False)
            )
        
        elif tool_id == 'rename':
            from services.file_renamer import FileRenamer
            renamer = FileRenamer()
            # RenamingWorker espera (renamer, plan: List[Dict], create_backup, dry_run)
            worker = RenamingWorker(
                renamer=renamer,
                plan=plan.get('plan', []),
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
                QMessageBox.information(
                    self.main_window,
                    "Operación Completada",
                    f"La operación se completó exitosamente.\n\n{result.message if hasattr(result, 'message') else ''}"
                )
                
                # Emitir señal de acciones completadas para re-análisis
                self._on_tool_action_completed(tool_id)
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
        self.logger.info(f"Worker de {tool_id} iniciado")

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
        dialog.exec()

    def _on_about_clicked(self):
        """Maneja el clic en el botón 'Acerca de'"""
        self.logger.debug("Abriendo diálogo 'Acerca de'")
        dialog = AboutDialog(self.main_window)
        dialog.exec()
    
    # ==================== SIMILAR DUPLICATES ====================
    
    def _on_similar_duplicates_clicked(self):
        """Maneja el clic en la card de duplicados similares"""
        self.logger.info("Iniciando configuración de análisis de duplicados similares")
        
        # Si hay resultados con grupos pero están obsoletos (snapshot existe), mostrar diálogo
        if self.similarity_results_snapshot:
            choice = self._show_stale_results_dialog()
            
            if choice == 'view_old':
                # Ver resultados del snapshot
                old_results = self.similarity_results_snapshot['results']
                self._open_similarity_dialog(old_results)
                return
            elif choice == 'reanalyze':
                # Continuar con configuración y re-análisis
                pass
            else:  # cancel
                return
        
        # Si ya hay resultados con grupos (y no obsoletos), abrir directamente el diálogo de gestión
        if self.similarity_results and self.similarity_results.total_groups > 0:
            self._open_similarity_dialog(self.similarity_results)
            return
        
        # Si hay resultados pero sin grupos, o no hay resultados, permitir reconfigurar
        # Limpiar resultados previos si no hay grupos
        if self.similarity_results and self.similarity_results.total_groups == 0:
            self.similarity_results = None
        
        # Obtener número de archivos a analizar
        file_count = self.analysis_results.scan.total_files if self.analysis_results.scan else 0
        
        # Obtener sensibilidad previa si existe
        previous_sensitivity = 10  # Valor por defecto
        if self.similarity_results:
            # Intentar extraer la sensibilidad usada (si está guardada en el resultado)
            # Por ahora usamos el valor por defecto
            previous_sensitivity = 10
        
        # Mostrar diálogo de configuración
        config_dialog = SimilarFilesConfigDialog(
            parent=self.main_window,
            file_count=file_count,
            previous_sensitivity=previous_sensitivity
        )
        
        if config_dialog.exec() == QDialog.DialogCode.Accepted:
            sensitivity = config_dialog.get_sensitivity_value()
            self.logger.info(f"Iniciando análisis con sensibilidad: {sensitivity}")
            self._start_similarity_analysis(sensitivity, file_count)
    
    def _start_similarity_analysis(self, sensitivity: int, file_count: int):
        """
        Inicia el análisis de duplicados similares con worker en background
        
        Args:
            sensitivity: Sensibilidad del análisis (0-20)
            file_count: Número de archivos a analizar
        """
        # Crear el detector
        detector = SimilarFilesDetector()
        
        # Crear el worker
        self.similarity_worker = SimilarFilesAnalysisWorker(
            detector=detector,
            workspace_path=Path(self.selected_folder),
            sensitivity=sensitivity
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
    
    def _on_similarity_analysis_completed(self, results):
        """
        Maneja la finalización exitosa del análisis
        
        Args:
            results: DuplicateAnalysisResult con los grupos de similares
        """
        from datetime import datetime
        
        self.logger.info("Análisis de duplicados similares completado")
        self.similarity_results = results
        
        # Guardar timestamp del análisis
        self.similarity_timestamp = datetime.now()
        
        # Limpiar snapshot (ya no es obsoleto)
        self.similarity_results_snapshot = None
        
        # Cerrar diálogo de progreso
        if self.similarity_progress_dialog:
            self.similarity_progress_dialog.accept()
            self.similarity_progress_dialog = None
        
        # Limpiar worker
        if self.similarity_worker:
            self.similarity_worker.deleteLater()
            self.similarity_worker = None
        
        # Actualizar la card con los resultados
        self._update_similar_duplicates_card(results)
        
        # Abrir automáticamente el diálogo de gestión si hay resultados
        if results.total_groups > 0:
            self._open_similarity_dialog(results)
        else:
            QMessageBox.information(
                self.main_window,
                "Sin resultados",
                "No se encontraron duplicados similares con la sensibilidad seleccionada."
            )
    
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
        Actualiza la card de similares con los resultados del análisis
        
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
            card.set_status_ready("No se encontraron duplicados similares")
            card.action_button.setText("Analizar de nuevo")
        
        # Actualizar descripción para indicar que ya se analizó
        card.description_label.setText(
            "Detecta fotos visualmente similares pero no idénticas "
            "(recortes, rotaciones, ediciones). Análisis completado."
        )
    
    def _open_similarity_dialog(self, results):
        """
        Abre el diálogo de gestión de duplicados similares
        
        Args:
            results: DuplicateAnalysisResult
        """
        dialog = SimilarFilesDialog(results, self.main_window)
        dialog.exec()
    
    # ===== SISTEMA DE RE-ANÁLISIS AUTOMÁTICO =====
    
    def _on_tool_action_completed(self, tool_name: str):
        """
        Manejador cuando una herramienta ejecuta acciones (elimina/mueve/renombra archivos).
        
        Determina si es necesario:
        1. Invalidar resultados de similar_duplicates (herramientas destructivas)
        2. Lanzar re-análisis automático de herramientas rápidas
        
        Args:
            tool_name: ID de la herramienta que completó acciones
        """
        from config import Config
        
        self.logger.info(f"Herramienta '{tool_name}' completó acciones, evaluando re-análisis")
        
        # Verificar si la herramienta impacta archivos
        impact = Config.TOOL_IMPACT_ON_FILES.get(tool_name, 'none')
        
        if impact == 'none':
            self.logger.debug(f"Herramienta '{tool_name}' no impacta archivos, no hay re-análisis")
            return
        
        # Si impacta archivos, invalidar resultados de similar_duplicates
        if impact in ('destructive', 'moves', 'renames'):
            self._invalidate_similarity_analysis()
        
        # Lanzar re-análisis automático de herramientas rápidas
        self._trigger_automatic_reanalysis()
    
    def _trigger_automatic_reanalysis(self):
        """
        Dispara el re-análisis automático de las 5 herramientas rápidas.
        
        Si ya hay un re-análisis en curso, marca pending_reanalysis para
        ejecutar otro cuando termine.
        """
        # Si ya hay un re-análisis en curso, marcar como pendiente
        if self.reanalysis_worker and self.reanalysis_worker.isRunning():
            self.logger.info("Re-análisis ya en curso, marcando como pendiente")
            self.pending_reanalysis = True
            return
        
        self.logger.info("Iniciando re-análisis automático")
        self.pending_reanalysis = False
        self._start_reanalysis()
    
    def _start_reanalysis(self):
        """Inicia el worker de re-análisis y muestra el overlay."""
        from ui.workers import WorkspaceReanalysisWorker
        from ui.widgets.reanalysis_overlay import ReanalysisOverlay
        from pathlib import Path
        
        # Crear overlay si no existe
        if not self.reanalysis_overlay:
            self.reanalysis_overlay = ReanalysisOverlay(self)
            # Posicionarlo para que cubra todo el Stage 3
            self.reanalysis_overlay.setGeometry(self.rect())
        
        # Resetear y mostrar overlay
        self.reanalysis_overlay.reset()
        self.reanalysis_overlay.show_overlay()
        
        # Crear y configurar worker
        self.reanalysis_worker = WorkspaceReanalysisWorker(Path(self.selected_folder))
        self.reanalysis_worker.tool_completed.connect(self._handle_reanalysis_tool_completed)
        self.reanalysis_worker.finished.connect(self._finish_reanalysis)
        self.reanalysis_worker.tool_error.connect(self._handle_reanalysis_error)
        
        # Iniciar worker
        self.reanalysis_worker.start()
        self.logger.info("Worker de re-análisis iniciado")
    
    def _handle_reanalysis_tool_completed(self, tool_name: str, result):
        """
        Manejador cuando el worker completa una herramienta individual.
        
        Args:
            tool_name: ID de la herramienta completada ('live_photos', 'heic', etc)
            result: Resultado del análisis (dataclass)
        """
        from config import Config
        
        display_name = Config.TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
        self.logger.info(f"Re-análisis completado para: {display_name}")
        
        # Actualizar overlay con progreso
        completed = list(Config.TOOL_ANALYSIS_COST.keys()).index(tool_name) + 1
        self.reanalysis_overlay.update_progress(display_name, completed)
        
        # Actualizar analysis_results con el nuevo resultado
        self.analysis_results[tool_name] = result
        
        # Actualizar tarjeta correspondiente en el grid
        self._update_tool_card_after_reanalysis(tool_name, result)
    
    def _update_tool_card_after_reanalysis(self, tool_name: str, result):
        """
        Actualiza la tarjeta de herramienta después del re-análisis.
        
        Args:
            tool_name: ID de la herramienta
            result: Resultado actualizado del análisis
        """
        if tool_name not in self.tool_cards:
            return
        
        card = self.tool_cards[tool_name]
        
        # Actualizar según tipo de herramienta
        if tool_name == 'live_photos':
            if result and result.total_live_photos > 0:
                card.set_status_with_results(
                    f"{result.total_live_photos} Live Photos detectadas",
                    f"~{format_size(result.space_potential)} recuperables"
                )
            else:
                card.set_status_ready("No se detectaron Live Photos")
        
        elif tool_name == 'heic':
            if result and result.total_heic > 0:
                card.set_status_with_results(
                    f"{result.total_heic} archivos HEIC con JPG",
                    f"~{format_size(result.space_potential)} recuperables"
                )
            else:
                card.set_status_ready("No se detectaron HEIC duplicados")
        
        elif tool_name == 'exact_copies':
            if result and result.total_groups > 0:
                card.set_status_with_results(
                    f"{result.total_groups} grupos detectados",
                    f"~{format_size(result.space_potential)} recuperables"
                )
            else:
                card.set_status_ready("No se detectaron duplicados exactos")
        
        elif tool_name == 'organize':
            if result and result.files_to_process > 0:
                card.set_status_with_results(
                    f"{format_file_count(result.files_to_process)} archivos",
                    "Listos para organizar"
                )
            else:
                card.set_status_ready("No hay archivos para organizar")
        
        elif tool_name == 'rename':
            if result and result.files_to_rename > 0:
                card.set_status_with_results(
                    f"{format_file_count(result.files_to_rename)} archivos",
                    "Listos para renombrar"
                )
            else:
                card.set_status_ready("No hay archivos para renombrar")
    
    def _handle_reanalysis_error(self, tool_name: str, error_msg: str):
        """
        Manejador de errores durante el re-análisis.
        
        Args:
            tool_name: ID de la herramienta que falló
            error_msg: Mensaje de error
        """
        from config import Config
        
        display_name = Config.TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
        self.logger.error(f"Error en re-análisis de {display_name}: {error_msg}")
        
        # Mostrar error en la tarjeta
        if tool_name in self.tool_cards:
            card = self.tool_cards[tool_name]
            card.set_status_ready(f"Error: {error_msg[:50]}...")
    
    def _finish_reanalysis(self, results: dict):
        """
        Manejador cuando el re-análisis completo termina.
        
        Args:
            results: Dict con todos los resultados {tool_name: result}
        """
        self.logger.info("Re-análisis automático completado")
        
        # Ocultar overlay con delay
        QTimer.singleShot(1000, self.reanalysis_overlay.hide_overlay)
        
        # Si hay re-análisis pendiente, ejecutarlo
        if self.pending_reanalysis:
            self.logger.info("Ejecutando re-análisis pendiente")
            QTimer.singleShot(2000, self._start_reanalysis)
    
    # ===== SISTEMA DE INVALIDACIÓN DE SIMILAR_DUPLICATES =====
    
    def _invalidate_similarity_analysis(self):
        """
        Invalida los resultados de similar_duplicates cuando se modifican archivos.
        
        - Guarda snapshot de resultados actuales
        - Marca timestamp de invalidación
        - Actualiza UI de la tarjeta para mostrar estado "obsoleto"
        """
        if not self.similarity_results:
            self.logger.debug("No hay resultados de similares para invalidar")
            return
        
        from datetime import datetime
        
        self.logger.info("Invalidando resultados de similar_duplicates")
        
        # Guardar snapshot de resultados antes de invalidar
        self.similarity_results_snapshot = {
            'results': self.similarity_results,
            'timestamp': self.similarity_timestamp or datetime.now()
        }
        
        # Actualizar tarjeta con estado "obsoleto"
        self._update_similar_files_card_stale()
    
    def _update_similar_files_card_stale(self):
        """
        Actualiza la tarjeta de similar_duplicates para mostrar estado obsoleto.
        
        Cambia el texto y estilo para indicar que los resultados ya no son válidos
        tras modificaciones en el workspace.
        """
        if 'similar_files' not in self.tool_cards:
            return
        
        card = self.tool_cards['similar_files']
        
        # Cambiar descripción para indicar obsolescencia
        card.description_label.setText(
            "⚠️ Los resultados están desactualizados. "
            "Se modificaron archivos desde el último análisis."
        )
        
        # Cambiar estilo del texto de descripción
        card.description_label.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_WARNING};
                font-size: {DesignSystem.FONT_SIZE_SMALL}px;
                padding-top: {DesignSystem.SPACE_XXS}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
        """)
        
        # Actualizar botón de acción
        if self.similarity_results_snapshot:
            card.action_button.setText("Ver resultados antiguos")
        else:
            card.action_button.setText("Analizar de nuevo")
        
        self.logger.debug("Tarjeta de similares actualizada con estado obsoleto")
    
    def _show_stale_results_dialog(self):
        """
        Muestra diálogo cuando usuario intenta ver resultados obsoletos.
        
        Ofrece 3 opciones:
        1. Ver resultados antiguos (snapshot)
        2. Re-analizar ahora (cierra y lanza análisis)
        3. Cancelar
        
        Returns:
            str: Opción elegida ('view_old', 'reanalyze', 'cancel')
        """
        from PyQt6.QtWidgets import QMessageBox, QPushButton
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Resultados Desactualizados")
        msg.setIcon(QMessageBox.Icon.Warning)
        
        # Texto principal
        if self.similarity_results_snapshot:
            timestamp = self.similarity_results_snapshot['timestamp']
            time_str = timestamp.strftime("%H:%M:%S del %d/%m/%Y")
            
            msg.setText(
                "Los resultados de duplicados similares están desactualizados."
            )
            msg.setInformativeText(
                f"Último análisis: {time_str}\n\n"
                "Desde entonces se han modificado archivos en el workspace. "
                "¿Qué deseas hacer?"
            )
            
            # Botones
            view_old_btn = msg.addButton("Ver Resultados Antiguos", QMessageBox.ButtonRole.ActionRole)
            reanalyze_btn = msg.addButton("Re-analizar Ahora", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = msg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            
            # Styling
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {DesignSystem.COLOR_BACKGROUND_PRIMARY};
                }}
                QLabel {{
                    color: {DesignSystem.COLOR_TEXT_PRIMARY};
                    font-size: {DesignSystem.FONT_SIZE_BODY}px;
                }}
                QPushButton {{
                    background-color: {DesignSystem.COLOR_PRIMARY};
                    color: {DesignSystem.COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: {DesignSystem.RADIUS_SMALL}px;
                    padding: {DesignSystem.SPACE_SM}px {DesignSystem.SPACE_MD}px;
                    font-size: {DesignSystem.FONT_SIZE_BODY}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
                }}
            """)
            
            msg.exec()
            
            clicked_button = msg.clickedButton()
            if clicked_button == view_old_btn:
                return 'view_old'
            elif clicked_button == reanalyze_btn:
                return 'reanalyze'
            else:
                return 'cancel'
        
        else:
            # No hay snapshot, solo re-analizar
            msg.setText("Los resultados están desactualizados")
            msg.setInformativeText(
                "Se han modificado archivos desde el último análisis. "
                "Es necesario re-analizar."
            )
            
            reanalyze_btn = msg.addButton("Re-analizar Ahora", QMessageBox.ButtonRole.AcceptRole)
            cancel_btn = msg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {DesignSystem.COLOR_BACKGROUND_PRIMARY};
                }}
                QLabel {{
                    color: {DesignSystem.COLOR_TEXT_PRIMARY};
                    font-size: {DesignSystem.FONT_SIZE_BODY}px;
                }}
                QPushButton {{
                    background-color: {DesignSystem.COLOR_PRIMARY};
                    color: {DesignSystem.COLOR_TEXT_ON_PRIMARY};
                    border: none;
                    border-radius: {DesignSystem.RADIUS_SMALL}px;
                    padding: {DesignSystem.SPACE_SM}px {DesignSystem.SPACE_MD}px;
                    font-size: {DesignSystem.FONT_SIZE_BODY}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
                }}
            """)
            
            msg.exec()
            
            if msg.clickedButton() == reanalyze_btn:
                return 'reanalyze'
            else:
                return 'cancel'
