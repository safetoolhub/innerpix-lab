"""
Similarity Analysis Handler for Stage 3.
Maneja toda la lógica de análisis de archivos similares, incluyendo
progreso, resultados y actualización de la UI.
"""

from typing import Optional, Dict, Any
from logging import Logger

from PyQt6.QtWidgets import QMessageBox, QWidget, QDialog

from config import Config
from utils.format_utils import format_size
from ui.dialogs.duplicates_similar_progress_dialog import SimilarFilesProgressDialog
from ui.workers import DuplicatesSimilarAnalysisWorker


class SimilarityAnalysisHandler:
    """
    Handler para el análisis de archivos similares.
    Encapsula toda la lógica de análisis independiente de Stage3Window.
    """

    def __init__(
        self,
        parent_window: QWidget,
        main_window: QWidget,
        analysis_results: Any,
        metadata_cache: Any,
        tool_cards: Dict[str, Any],
        logger: Logger
    ):
        """
        Inicializa el handler de análisis de similares

        Args:
            parent_window: Ventana padre (Stage3Window)
            main_window: Ventana principal de la aplicación
            analysis_results: Resultados del análisis inicial
            metadata_cache: Cache de metadatos compartida
            tool_cards: Diccionario de tool cards
            logger: Logger para mensajes
        """
        self.parent_window = parent_window
        self.main_window = main_window
        self.analysis_results = analysis_results
        self.metadata_cache = metadata_cache
        self.tool_cards = tool_cards
        self.logger = logger

        # Worker y diálogos
        self.similarity_worker: Optional[DuplicatesSimilarAnalysisWorker] = None
        self.similarity_progress_dialog: Optional[SimilarFilesProgressDialog] = None
        self.similarity_analysis = None  # Guardar análisis completado
        
        # Restaurar estado si ya existe análisis previo en analysis_results
        self._restore_state()

    def _restore_state(self):
        """Restaura el estado del análisis si ya existe en analysis_results"""
        if not self.analysis_results:
            return
            
        # Intentar obtener resultados previos (DuplicateAnalysisResult o DuplicatesSimilarAnalysis)
        sim_results = None
        if hasattr(self.analysis_results, 'duplicates_similar') and self.analysis_results.duplicates_similar:
            sim_results = self.analysis_results.duplicates_similar
            
        if sim_results:
            self.logger.debug("Restaurando estado de análisis de similares previo")
            # El objeto puede ser de dos tipos según si vino de caché o worker
            # update_card_with_results espera DuplicateAnalysisResult
            # Pero si viene de caché puede ser el objeto de análisis puro.
            # Verificamos si tiene total_groups (DuplicateAnalysisResult)
            if hasattr(sim_results, 'total_groups'):
                self.update_card_with_results(sim_results)
            elif hasattr(sim_results, 'perceptual_hashes'):
                # Es un DuplicatesSimilarAnalysis (hashes calculados pero no clúster)
                self.update_card_after_analysis(sim_results)
                # Guardar referencia para evitar re-analizar hashes
                self.similarity_analysis = sim_results

    def start_analysis(self):
        """
        Inicia el análisis de archivos similares.

        Flujo:
        1. Si ya hay análisis completado, abrir directamente
        2. Si no, lanzar análisis directo (solo hashes, sin clustering)
        3. Mostrar diálogo de progreso bloqueante
        4. Al completar, abrir diálogo de gestión con slider
        """
        self.logger.info("Iniciando análisis de archivos similares")

        # Si ya hay análisis completado, abrir directamente
        if hasattr(self, 'similarity_analysis') and self.similarity_analysis:
            # Verificar si hay archivos analizados antes de abrir el diálogo
            if self.similarity_analysis.total_files == 0 or not self.similarity_analysis.perceptual_hashes:
                QMessageBox.information(
                    self.main_window,
                    "Sin archivos similares",
                    "No se encontraron archivos similares en el análisis.\\n\\n"
                    "Esto puede ocurrir si:\\n"
                    "• No hay suficientes imágenes para comparar\\n"
                    "• Las imágenes son muy diferentes entre sí\\n"
                    "• La sensibilidad del análisis es demasiado estricta"
                )
                return

            self.open_dialog(self.similarity_analysis)
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
        from services.duplicates_similar_service import DuplicatesSimilarService

        # Crear el detector
        detector = DuplicatesSimilarService()

        # Crear el worker (sin sensibilidad)
        self.similarity_worker = DuplicatesSimilarAnalysisWorker(
            detector=detector
        )

        # Crear diálogo de progreso bloqueante
        self.similarity_progress_dialog = SimilarFilesProgressDialog(
            parent=self.main_window,
            total_files=file_count
        )

        # Conectar señales del worker
        self.similarity_worker.progress_update.connect(
            self._on_progress_update
        )
        self.similarity_worker.finished.connect(
            self._on_analysis_completed
        )
        self.similarity_worker.error.connect(
            self._on_analysis_error
        )

        # Conectar cancelación del diálogo
        self.similarity_progress_dialog.cancel_requested.connect(
            self._on_analysis_cancelled
        )

        # Iniciar worker
        self.similarity_worker.start()

        # Mostrar diálogo bloqueante
        self.similarity_progress_dialog.exec()

    def _on_progress_update(self, current: int, total: int, message: str):
        """Actualiza el progreso en el diálogo"""
        if self.similarity_progress_dialog:
            self.similarity_progress_dialog.update_progress(current, total, message)

    def _on_analysis_completed(self, analysis):
        """
        Maneja la finalización exitosa del análisis.

        Args:
            analysis: DuplicatesSimilarAnalysis con hashes calculados
        """
        self.logger.info("Análisis inicial de archivos similares completado")
        self.similarity_analysis = analysis

        # PERSISTENCIA:
        # Guardar en analysis_results de la ventana principal para que sobreviva a refrescos
        if hasattr(self.analysis_results, 'duplicates_similar'):
             self.analysis_results.duplicates_similar = analysis
             self.logger.debug("Resultados de similares guardados en analysis_results global")

        # Cerrar diálogo de progreso
        if self.similarity_progress_dialog:
            self.similarity_progress_dialog.accept()
            self.similarity_progress_dialog = None

        # Limpiar worker
        if self.similarity_worker:
            self.similarity_worker.deleteLater()
            self.similarity_worker = None

        # Actualizar la card indicando que el análisis está completado
        self.update_card_after_analysis(analysis)

        # Verificar si hay hashes calculados antes de abrir el diálogo
        if analysis.total_files == 0 or not analysis.perceptual_hashes:
            QMessageBox.information(
                self.main_window,
                "Sin archivos similares",
                "No se encontraron archivos similares en la carpeta analizada.\\n\\n"
                "Esto puede ocurrir si:\\n"
                "• No hay suficientes imágenes para comparar\\n"
                "• Las imágenes son muy diferentes entre sí\\n"
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
                f"Se analizaron {analysis.total_files} archivos con éxito.\\n\\n"
                "Debido al tamaño del dataset, el diálogo de gestión no se "
                "abre automáticamente para evitar problemas de memoria.\\n\\n"
                "Haz clic en 'Gestionar ahora' cuando estés listo."
            )
            return

        # Abrir automáticamente el diálogo de gestión con slider (solo datasets pequeños)
        self.open_dialog(analysis)

    def _on_analysis_error(self, error_message: str):
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
            f"Ocurrió un error durante el análisis:\\n\\n{error_message[:500]}"
        )

    def _on_analysis_cancelled(self):
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

    def update_card_with_results(self, results):
        """
        Actualiza la card de similares con los resultados del análisis.

        Args:
            results: DuplicateAnalysisResult
        """
        if 'duplicates_similar' not in self.tool_cards:
            return

        card = self.tool_cards['duplicates_similar']

        if results.total_groups > 0:
            size_text = f"~{format_size(results.space_potential)} recuperables"
            card.set_status_with_results(
                f"{results.total_groups} grupos detectados",
                size_text,
                badge_count=results.total_groups
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

    def update_card_after_analysis(self, analysis):
        """
        Actualiza la card después del análisis inicial.

        Args:
            analysis: DuplicatesSimilarAnalysis con hashes calculados
        """
        if 'duplicates_similar' not in self.tool_cards:
            return

        card = self.tool_cards['duplicates_similar']

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
                "Listo para ajustar sensibilidad",
                badge_count=len(analysis.perceptual_hashes)
            )
            card.action_button.setText("Gestionar ahora")

            # Actualizar descripción
            card.description_label.setText(
                "Análisis completado. Puedes ajustar la sensibilidad "
                "interactivamente para detectar más o menos similitudes."
            )

    def open_dialog(self, analysis):
        """
        Abre el diálogo de gestión con el análisis (slider interactivo).

        Args:
            analysis: DuplicatesSimilarAnalysis con hashes calculados
        """
        from ui.dialogs.duplicates_similar_dialog import DuplicatesSimilarDialog

        dialog = DuplicatesSimilarDialog(analysis, self.main_window)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            # Usuario ejecutó acciones, ejecutar con worker
            # Delegación a stage_3_window para ejecución
            if hasattr(self.parent_window, '_execute_tool_action'):
                self.parent_window._execute_tool_action("duplicates_similar", dialog)
