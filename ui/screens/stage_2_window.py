"""
Stage 2: Análisis con progreso.
Maneja la ejecución del análisis de archivos con indicadores visuales de progreso.
"""

from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QTimer, pyqtSignal

from config import Config
from .base_stage import BaseStage
from ui.styles.design_system import DesignSystem
from ui.screens.progress_card import ProgressCard
from ui.workers.initial_analysis_worker import InitialAnalysisWorker
# Los servicios se importan lazy en _start_analysis() para evitar bloquear la UI


class Stage2Window(BaseStage):
    """
    Stage 2: Análisis con progreso.
    Coordina la ejecución del análisis mostrando progreso y fases.
    """

    # Señales
    analysis_completed = pyqtSignal(object)  # Emite cuando el análisis termina

    def __init__(self, main_window, selected_folder: str):
        super().__init__(main_window)

        # Parámetros del estado
        self.selected_folder = selected_folder

        # Referencias a widgets de la fase
        self.header = None
        self.progress_card = None

        # Estado del análisis
        self.analysis_worker = None
        self.analysis_results = None

        # Gestión de fases
        self.current_phase = None  # Fase actualmente en ejecución
        
        # Estado de cancelación
        self.cancel_dialog_open = False  # Si el diálogo de cancelación está abierto
        self.analysis_completed_while_cancel_dialog_open = False  # Si terminó mientras el diálogo estaba abierto

    def setup_ui(self) -> None:
        """Configura la interfaz de usuario del Stage 2."""
        self.logger.debug("Configurando UI del Stage 2")

        # Limpiar el layout principal para evitar espacios residuales de otras stages
        if self.main_layout:
            while self.main_layout.count():
                item = self.main_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.hide()
                    widget.setParent(None)

        # Crear y mostrar header con pequeño margen superior
        self.header = self.create_header(
            subtitle_text="Análisis de tu carpeta",
            show_settings_button=False,
            show_about_button=False
        )
        # Añadir espaciado encima del header
        self.main_layout.addSpacing(DesignSystem.SPACE_4)
        self.main_layout.addWidget(self.header)
        self.main_layout.addSpacing(DesignSystem.SPACE_8)

        # Crear y mostrar card de progreso (ahora incluye las fases)
        self.progress_card = ProgressCard(self.selected_folder)
        self.progress_card.cancel_requested.connect(self._on_cancel_requested)
        self.main_layout.addWidget(self.progress_card)

        # Añadir espacio y stretch en la parte inferior para que el margen vaya al final
        self.main_layout.addSpacing(DesignSystem.SPACE_20)
        self.main_layout.addStretch()
        self.fade_in_widget(self.progress_card, duration=350)

        # Iniciar análisis con delay para mostrar animaciones y evitar congelar la UI
        # Usar un delay mayor para dar tiempo a que la UI se renderice completamente
        QTimer.singleShot(100, self._start_analysis)

        self.logger.debug("UI del Estado 2 configurada")

    def cleanup(self) -> None:
        """Limpia los recursos del Estado 2."""
        self.logger.debug("Limpiando Estado 2")

        # Detener worker si está ejecutándose
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.logger.info("Deteniendo worker durante cleanup...")
            self.analysis_worker.stop()
            
            # Esperar con timeout generoso para datasets grandes (100k+ archivos)
            # 30 segundos permite cancelación cooperativa de workers paralelos
            if not self.analysis_worker.wait(30000):  # 30 segundos de timeout
                self.logger.warning("Worker no respondió en 30 segundos durante cleanup, terminando forzosamente")
                self.analysis_worker.terminate()
                self.analysis_worker.wait(2000)
            else:
                self.logger.info("Worker detenido correctamente durante cleanup")

        # Limpiar referencias
        if self.header:
            self.header.hide()
            self.header.setParent(None)
            self.header = None

        if self.progress_card:
            self.progress_card.hide()
            self.progress_card.setParent(None)
            self.progress_card = None

        self.current_phase = None

    def _start_analysis(self):
        """Inicia el análisis del directorio seleccionado"""
        # Crear worker de análisis inicial (multi-fase)
        self.analysis_worker = InitialAnalysisWorker(
            directory=Path(self.selected_folder)
        )

        # Conectar señales del worker
        self.analysis_worker.progress_update.connect(self._on_analysis_progress)
        self.analysis_worker.phase_started.connect(self._on_phase_started)
        self.analysis_worker.phase_completed.connect(self._on_phase_completed)
        self.analysis_worker.stats_update.connect(self._on_analysis_stats)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.error.connect(self._on_analysis_error)

        # Iniciar análisis
        self.logger.debug("Iniciando worker de análisis inicial")
        self.analysis_worker.start()

    def _on_analysis_progress(self, current: int, total: int, message: str):
        """
        Callback de progreso del análisis
        
        Args:
            current: Archivos procesados
            total: Total de archivos
            message: Mensaje descriptivo (ignorado)
        """
        # Debug logging para fase de hashes (cada 100 archivos)
        if self.current_phase == 'phase_hash' and current % 100 == 0:
            self.logger.debug(f"Hash progress: {current}/{total}")
        
        # Actualizar contador de la fase actual si hay números válidos
        if self.current_phase and self.progress_card and total > 0:
            self.progress_card.update_phase_progress(self.current_phase, current, total)

    def _on_phase_started(self, phase_id: str, phase_message: str = ""):
        """
        Callback cuando inicia una nueva fase del análisis.
        
        Args:
            phase_id: ID de la fase que inicia
            phase_message: Mensaje descriptivo de la fase (opcional)
        """
        self.logger.info(f"Phase started: {phase_id} - {phase_message}")
        
        if not self.progress_card:
            return

        # Establecer la fase como running
        self.progress_card.set_phase_status(phase_id, 'running')
        self.current_phase = phase_id
        
    def _on_phase_completed(self, phase_id: str):
        """
        Callback cuando una fase se completa (ya con delay mínimo aplicado).
        
        Args:
            phase_id: ID de la fase que se completó
        """
        # Log ya se hace en el worker (mismo thread del análisis, más preciso)
        if not self.progress_card:
            return

        # Marcar la fase como completada
        self.progress_card.set_phase_status(phase_id, 'completed')

    def _on_analysis_stats(self, stats):
        """
        Callback con estadísticas del análisis.
        
        Args:
            stats: Dict con estadísticas (total, images, videos, others)
        """
        self.logger.info(f"Scan statistics: {stats}")

    def _on_analysis_finished(self, results):
        """
        Callback cuando el análisis termina exitosamente.
        El worker ya aplicó el delay de 2s, así que podemos transicionar inmediatamente.

        Args:
            results: Diccionario con todos los resultados
        """
        self.logger.info("Análisis completado exitosamente")
        self.analysis_results = results

        # Logging detallado de extensiones de archivos
        self._log_file_extensions_summary(results)

        # Guardar resultados del análisis para uso futuro
        self.save_analysis_results(results)

        # Marcar progreso como completo
        if self.progress_card:
            self.progress_card.mark_completed()

        # Limpiar estado
        self.current_phase = None

        # Verificar si el diálogo de cancelación está abierto
        if self.cancel_dialog_open:
            self.logger.info("Análisis terminó mientras diálogo de cancelación estaba abierto, esperando...")
            self.analysis_completed_while_cancel_dialog_open = True
            return

        # Emitir señal de análisis completado y transicionar
        self.analysis_completed.emit(results)
        self._perform_stage_3_transition()
    
    def _perform_stage_3_transition(self):
        """Realiza la transición a Fase 3"""
        self.logger.debug("Realizando transición a Stage 3")
        self.main_window._transition_to_state_3(self.analysis_results)

    def _on_analysis_error(self, error_msg: str):
        """
        Callback cuando ocurre un error en el análisis

        Args:
            error_msg: Mensaje de error
        """
        self.logger.error(f"Error en análisis: {error_msg}")

        # Detener el worker si está corriendo
        if hasattr(self, 'analysis_worker') and self.analysis_worker:
            self.analysis_worker.stop()

        # Marcar fase actual como error si existe
        if self.progress_card and self.current_phase:
            self.progress_card.set_phase_status(self.current_phase, 'alert-circle')
        
        self.current_phase = None

        # Detener la barra de progreso
        if self.progress_card:
            self.progress_card.stop_progress()

        # Mostrar diálogo de error con opciones
        msg = QMessageBox(self.main_window)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error en el análisis")
        msg.setText("Ocurrió un error durante el análisis de la carpeta.")
        msg.setInformativeText(f"Detalles del error:\n{error_msg}")
        msg.setDetailedText(f"Carpeta: {self.selected_folder}\n\nError: {error_msg}")

        # Botones de acción
        retry_btn = msg.addButton("Reintentar", QMessageBox.ButtonRole.ActionRole)
        change_btn = msg.addButton("Cambiar carpeta", QMessageBox.ButtonRole.ActionRole)
        exit_btn = msg.addButton("Salir", QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(retry_btn)

        msg.exec()

        # Manejar la respuesta del usuario
        if msg.clickedButton() == retry_btn:
            self.logger.info("Usuario eligió reintentar el análisis")
            self._restart_analysis()
        elif msg.clickedButton() == change_btn:
            self.logger.info("Usuario eligió cambiar de carpeta")
            self._return_to_state_1()
        else:  # exit_btn o cerrar diálogo
            self.logger.info("Usuario eligió salir - volviendo a Stage 1")
            self._return_to_state_1()

    def _restart_analysis(self):
        """Reinicia el análisis de la carpeta actual"""
        self.logger.info("Reiniciando análisis...")

        # Limpiar estado de análisis previo
        if self.progress_card:
            self.progress_card.reset()

        if self.progress_card:
            self.progress_card.reset_phases()

        # Reiniciar análisis
        self._start_analysis()

    def _return_to_state_1(self):
        """Vuelve al Estado 1 para seleccionar otra carpeta"""
        self.logger.info("Volviendo a Estado 1")

        # Limpiar datos del análisis
        self.analysis_results = None
        
        # Invalidar caché para tener datos frescos en el próximo análisis
        from services.file_metadata_repository_cache import FileInfoRepositoryCache
        repo = FileInfoRepositoryCache.get_instance()
        files_count = repo.count()
        repo.clear()
        self.logger.info(f"Caché invalidada - {files_count} archivos eliminados")

        # Transición al Estado 1 a través de MainWindow
        self.main_window._transition_to_state_1()
    
    def _enrich_scan_with_extensions(self, results):
        """
        Enriquece los resultados de análisis con información de extensiones.
        Útil para cachés antiguos que no tienen estos datos.
        
        Args:
            results: Objeto con resultados del análisis (scan + directory)
        """
        if not results or not hasattr(results, 'scan'):
            return
        
        scan = results.scan
        
        # Si ya tiene los datos de extensiones, no hacer nada
        if hasattr(scan, 'image_extensions') and scan.image_extensions:
            self.logger.debug("Caché ya contiene información de extensiones")
            return
        
        self.logger.info("Enriqueciendo caché con información de extensiones...")
        
        # Inicializar dictionaries
        image_extensions = {}
        video_extensions = {}
        unsupported_extensions = {}
        unsupported_files = []
        
        # Analizar archivos existentes en el scan
        if hasattr(scan, 'images') and scan.images:
            for img_path in scan.images:
                ext = img_path.suffix.lower() if img_path.suffix else '(sin extensión)'
                image_extensions[ext] = image_extensions.get(ext, 0) + 1
        
        if hasattr(scan, 'videos') and scan.videos:
            for vid_path in scan.videos:
                ext = vid_path.suffix.lower() if vid_path.suffix else '(sin extensión)'
                video_extensions[ext] = video_extensions.get(ext, 0) + 1
        
        if hasattr(scan, 'others') and scan.others:
            for other_path in scan.others:
                ext = other_path.suffix.lower() if other_path.suffix else '(sin extensión)'
                unsupported_extensions[ext] = unsupported_extensions.get(ext, 0) + 1
                unsupported_files.append(other_path)
        
        # Agregar los datos al scan result
        scan.image_extensions = image_extensions
        scan.video_extensions = video_extensions
        scan.unsupported_extensions = unsupported_extensions
        scan.unsupported_files = unsupported_files
        
        self.logger.info(f"✅ Extensiones agregadas: {len(image_extensions)} imágenes, "
                        f"{len(video_extensions)} videos, {len(unsupported_extensions)} no soportadas")
    
    def _log_file_extensions_summary(self, results):
        """
        Registra información detallada sobre extensiones de archivos encontrados.
        
        Args:
            results: Objeto con resultados del análisis (scan + directory)
        """
        if not results or not hasattr(results, 'scan'):
            self.logger.warning("No hay resultados de escaneo disponibles para logging")
            return
        
        scan = results.scan
        
        # Los campos de extensiones siempre deberían estar presentes gracias a _enrich_scan_with_extensions
        # pero mantener verificación defensiva
        if not hasattr(scan, 'image_extensions'):
            self.logger.warning("Los resultados no incluyen desglose de extensiones")
            return
        
        # INFO: Desglose de imágenes por extensión
        if scan.image_extensions:
            image_summary = ', '.join(
                f"{ext.upper()} ({count})" 
                for ext, count in sorted(scan.image_extensions.items())
            )
            self.logger.info(f"📷 Imágenes por extensión: {image_summary}")
        else:
            self.logger.info("📷 Imágenes por extensión: ninguna")
        
        # INFO: Desglose de videos por extensión
        if scan.video_extensions:
            video_summary = ', '.join(
                f"{ext.upper()} ({count})" 
                for ext, count in sorted(scan.video_extensions.items())
            )
            self.logger.info(f"🎥 Videos por extensión: {video_summary}")
        else:
            self.logger.info("🎥 Videos por extensión: ninguna")
        
        # INFO: Recuento de archivos con extensiones no soportadas
        if scan.unsupported_extensions:
            unsupported_count = sum(scan.unsupported_extensions.values())
            unsupported_summary = ', '.join(
                f"{ext.upper() if ext != '(sin extensión)' else ext} ({count})" 
                for ext, count in sorted(scan.unsupported_extensions.items())
            )
            self.logger.info(f"⚠️  Archivos con extensiones NO SOPORTADAS: {unsupported_count} - {unsupported_summary}")
            
            # DEBUG: Rutas completas de archivos no soportados
            if scan.unsupported_files:
                self.logger.debug(f"📁 Rutas completas de archivos NO SOPORTADOS ({len(scan.unsupported_files)} archivos):")
                for file_path in scan.unsupported_files:
                    self.logger.debug(f"  - {file_path}")
        else:
            self.logger.info("✅ Archivos con extensiones NO SOPORTADAS: ninguno")
    
    def _on_cancel_requested(self):
        """Usuario solicitó cancelar el análisis"""
        self.logger.info("Usuario solicitó cancelar el análisis")
        
        # Marcar que el diálogo está abierto
        self.cancel_dialog_open = True
        
        msg = QMessageBox(self.main_window)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Cancelar análisis")
        msg.setText("¿Estás seguro de que quieres cancelar el análisis?")
        msg.setInformativeText("Se perderá el progreso actual.")
        
        # Botones con roles claros
        continue_btn = msg.addButton("Continuar análisis", QMessageBox.ButtonRole.RejectRole)
        change_btn = msg.addButton("Seleccionar otra carpeta", QMessageBox.ButtonRole.ActionRole)
        msg.setDefaultButton(continue_btn)
        
        msg.exec()
        
        # Marcar que el diálogo se cerró
        self.cancel_dialog_open = False
        
        # Manejar respuesta
        if msg.clickedButton() == change_btn:
            self.logger.info("Usuario eligió seleccionar otra carpeta")
            self._cancel_and_return_to_stage_1()
        else:
            self.logger.info("Usuario eligió continuar el análisis")
            # Si el análisis terminó mientras el diálogo estaba abierto, hacer la transición ahora
            if self.analysis_completed_while_cancel_dialog_open:
                self.logger.info("Análisis terminó mientras diálogo estaba abierto, haciendo transición ahora")
                self._perform_stage_3_transition()
        
        # Resetear la bandera
        self.analysis_completed_while_cancel_dialog_open = False
    
    def _cancel_and_return_to_stage_1(self):
        """Cancela el análisis y vuelve a Fase 1"""
        self.logger.info("Cancelando análisis y volviendo a Fase 1")
        
        # Detener worker si está ejecutándose
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.logger.info("Solicitando cancelación del worker de análisis...")
            self.analysis_worker.stop()
            
            # Esperar con timeout generoso para datasets grandes (100k+ archivos)
            # 30 segundos permite que los workers paralelos terminen cooperativamente
            self.logger.debug("Esperando hasta 30 segundos para cancelación cooperativa...")
            if not self.analysis_worker.wait(30000):  # 30 segundos de timeout
                self.logger.warning("Worker no respondió en 30 segundos, terminando forzosamente")
                self.analysis_worker.terminate()
                # Esperar un poco más después de terminate
                self.analysis_worker.wait(2000)
                self.logger.warning("⚠️ Cancelación forzosa aplicada - puede haber inconsistencias")
            else:
                self.logger.info("✓ Worker cancelado correctamente de forma cooperativa")
        
        # Volver a Estado 1
        self._return_to_state_1()
