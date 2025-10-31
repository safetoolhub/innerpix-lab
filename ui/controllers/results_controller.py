"""Controlador de presentación de resultados.

Centraliza toda la lógica de presentación de resultados HTML,
actualización de paneles y gestión de estadísticas.
"""
from PyQt6.QtCore import QObject

from ui.helpers import update_tab_details
from utils.format_utils import format_size, markdown_like_to_html
from utils.logger import get_logger


class ResultsController(QObject):
    """Controlador centralizado para presentación de resultados"""

    def __init__(self, main_window):
        """Constructor del controlador de resultados

        Args:
            main_window: Instancia de MainWindow
        """
        super().__init__()
        self.main_window = main_window
        self.logger = get_logger('ResultsController')

    def show_results_html(self, html: str, show_generic_status: bool = False):
        """Muestra resultados HTML en statusBar o similar

        Args:
            html: Contenido HTML a mostrar
            show_generic_status: Si True, muestra mensaje genérico en statusBar
        """
        self.logger.info(f"Mostrando resultados HTML:\n{html}")

        if show_generic_status:
            self.logger.info('Operación completada — revisa el log para detalles')

    def update_ui_after_operation(self, results: dict, operation_type: str):
        """Actualiza summary panel y tabs tras una operación

        Args:
            results: Resultados de la operación
            operation_type: Tipo de operación ('renaming', 'live_photo', 'organization', 'heic')
        """
        try:
            if self.main_window.analysis_results:
                self.main_window.summary_component.update(self.main_window.analysis_results)
                update_tab_details(self.main_window, self.main_window.analysis_results)

            self.logger.info(f"UI actualizada tras operación: {operation_type}")
        except Exception as e:
            self.logger.error(f"Error actualizando UI tras {operation_type}: {e}")

    def refresh_analysis_display(self, analysis_results: dict):
        """Refresca toda la UI tras re-análisis

        Args:
            analysis_results: Resultados del análisis completo
        """
        try:
            self.main_window.summary_component.update(analysis_results)
            update_tab_details(self.main_window, analysis_results)

            from ui.components.action_buttons import update_buttons_after_analysis
            update_buttons_after_analysis(self.main_window, analysis_results)

            self.logger.info("Display de análisis refrescado completamente")
        except Exception as e:
            self.logger.error(f"Error refrescando display de análisis: {e}")

    def format_renaming_results(self, results) -> str:
        """Genera HTML para resultados de renombrado

        Args:
            results: RenameResult con resultados de renombrado

        Returns:
            HTML formateado
        """
        if results.dry_run:
            # Simulación
            title = "🔍 Simulación de Renombrado Completada"
            color = "#0066cc"  # Azul para simulación
            files_label = "Archivos que se renombrarían"
        else:
            # Ejecución real
            title = "✅ Renombrado Completado"
            color = "#28a745"  # Verde para éxito
            files_label = "Archivos renombrados"

        html = f"""
            <div style='color: {color};'>
                <h4>{title}</h4>
                <p><strong>{files_label}:</strong> {results.files_renamed}</p>
                <p><strong>Errores:</strong> {len(results.errors)}</p>
        """

        if results.backup_path and not results.dry_run:
            html += f"<p><strong>💾 Backup:</strong> {results.backup_path}</p>"

        html += "</div>"
        return html

    def format_live_photo_results(self, results) -> str:
        """Genera HTML para resultados de limpieza Live Photos

        Args:
            results: LivePhotoCleanupResult con resultados de limpieza

        Returns:
            HTML formateado
        """
        dry_run = results.dry_run
        simulated_count = results.simulated_files_deleted
        simulated_space = results.simulated_space_freed
        space_freed = results.space_freed

        if dry_run:
            space_display = format_size(simulated_space)
            files_display = f"{simulated_count} (simulado)"
        else:
            space_display = format_size(space_freed)
            files_display = f"{results.files_deleted}"

        html = f"""
            <div style='color: #28a745;'>
                <h4>✅ Limpieza de Live Photos Completada</h4>
                <p><strong>Archivos eliminados:</strong> {files_display}</p>
                <p><strong>Espacio liberado:</strong> {space_display}</p>
                <p><strong>Errores:</strong> {len(results.errors)}</p>
        """

        if results.backup_path:
            html += f"<p><strong>💾 Backup:</strong> {results.backup_path}</p>"

        if dry_run:
            html += "<p><strong>ℹ️ Modo simulación</strong> - No se eliminaron archivos realmente</p>"

        html += "</div>"
        return html

    def format_organization_results(self, results) -> str:
        """Genera HTML para resultados de organización

        Args:
            results: OrganizationResult con resultados de organización

        Returns:
            HTML formateado
        """
        if results.dry_run:
            # Simulación
            title = "🔍 Simulación de Organización Completada"
            color = "#0066cc"  # Azul para simulación
            files_label = "Archivos que se moverían"
            dirs_label = "Directorios que se eliminarían"
        else:
            # Ejecución real
            title = "✅ Organización Completada"
            color = "#28a745"  # Verde para éxito
            files_label = "Archivos movidos"
            dirs_label = "Directorios eliminados"

        html = f"""
            <div style='color: {color};'>
                <h4>{title}</h4>
                <p><strong>{files_label}:</strong> {results.files_moved}</p>
                <p><strong>{dirs_label}:</strong> {results.empty_directories_removed}</p>
                <p><strong>Errores:</strong> {len(results.errors)}</p>
        """

        if results.backup_path and not results.dry_run:
            html += f"<p><strong>💾 Backup:</strong> {results.backup_path}</p>"

        html += "</div>"
        return html

    def format_heic_results(self, results) -> str:
        """Genera HTML para resultados de eliminación HEIC

        Args:
            results: HeicDeletionResult con resultados de eliminación HEIC

        Returns:
            HTML formateado
        """
        # Usar valores simulados o reales según dry_run
        if results.dry_run:
            files_count = results.simulated_files_deleted
            space_freed = results.simulated_space_freed
            title = "🔍 Simulación de Eliminación de Duplicados HEIC Completada"
            color = "#0066cc"  # Azul para simulación
            files_label = "Archivos que se eliminarían"
            space_label = "Espacio que se liberaría"
        else:
            files_count = results.files_deleted
            space_freed = results.space_freed
            title = "✅ Eliminación de Duplicados HEIC Completada"
            color = "#28a745"  # Verde para operación real
            files_label = "Archivos eliminados"
            space_label = "Espacio liberado"

        html = f"""
            <div style='color: {color};'>
                <h4>{title}</h4>
                <p><strong>{files_label}:</strong> {files_count}</p>
                <p><strong>{space_label}:</strong> {format_size(space_freed)}</p>
                <p><strong>Errores:</strong> {len(results.errors)}</p>
        """

        if results.dry_run:
            html += "<p style='font-style: italic; color: #666;'>⚠️ Modo simulación: no se eliminó ningún archivo realmente</p>"

        if results.backup_path and not results.dry_run:
            html += f"<p><strong>💾 Backup:</strong> {results.backup_path}</p>"

        if results.kept_format:
            html += f"<p><strong>📋 Formato mantenido:</strong> {results.kept_format.upper()}</p>"

        html += "</div>"
        return html

    def show_exact_results(self, results):
        """Formatea y muestra resultados de duplicados exactos en el bloque específico

        Args:
            results: DuplicateAnalysisResult con resultados de duplicados exactos
        """
        total_groups = results.total_groups
        total_duplicates = results.total_duplicates
        space_wasted = results.space_wasted

        if total_groups == 0:
            # No hay duplicados
            self.main_window.exact_status_label.setText(
                "✅ Sin duplicados - Todos los archivos son únicos"
            )
            self.main_window.exact_status_label.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: #28a745; padding: 4px;"
            )
            self.main_window.exact_details_text.setVisible(False)
            self.main_window.delete_exact_duplicates_btn.setVisible(False)
            return

        size_str = format_size(space_wasted)

        # Actualizar label de estado con instrucción
        self.main_window.exact_status_label.setText(
            f"✅ {total_groups} grupos encontrados - Haz clic en 'Revisar' para ver detalles"
        )
        self.main_window.exact_status_label.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #2c5aa0; padding: 4px;"
        )
        
        # Mostrar detalles
        details_html = markdown_like_to_html(
            f"**Archivos duplicados:** {total_duplicates}\n"
            f"**Espacio desperdiciado:** {size_str}\n\n"
            f"✅ Estos archivos son 100% idénticos y pueden eliminarse de forma segura."
        )
        self.main_window.exact_details_text.setHtml(details_html)
        self.main_window.exact_details_text.setVisible(True)
        
        # Mostrar botón de eliminación
        self.main_window.delete_exact_duplicates_btn.setVisible(True)
        self.main_window.delete_exact_duplicates_btn.setEnabled(True)

    def show_similar_results(self, results):
        """Formatea y muestra resultados de duplicados similares en el bloque específico

        Args:
            results: DuplicateAnalysisResult con resultados de duplicados similares
        """
        total_groups = results.total_groups
        total_similar = results.total_similar
        space_potential = results.space_potential
        min_sim = results.min_similarity or 0
        max_sim = results.max_similarity or 0

        if total_groups == 0:
            # No hay duplicados similares
            self.main_window.similar_status_label.setText(
                "✅ Sin duplicados similares - Prueba ajustar la sensibilidad"
            )
            self.main_window.similar_status_label.setStyleSheet(
                "font-size: 11px; font-weight: 600; color: #28a745; padding: 4px;"
            )
            self.main_window.similar_details_text.setVisible(False)
            self.main_window.review_similar_btn.setVisible(False)
            return

        size_str = format_size(space_potential)

        # Actualizar label de estado con instrucción
        self.main_window.similar_status_label.setText(
            f"✅ {total_groups} grupos encontrados - Haz clic en 'Revisar' para seleccionar qué eliminar"
        )
        self.main_window.similar_status_label.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #9c27b0; padding: 4px;"
        )
        
        # Mostrar detalles
        details_html = markdown_like_to_html(
            f"**Archivos similares:** {total_similar}\n"
            f"**Rango de similitud:** {min_sim:.1f}% - {max_sim:.1f}%\n"
            f"**Espacio potencial:** {size_str}\n\n"
            f"⚠️ **Requiere revisión manual** antes de eliminar."
        )
        self.main_window.similar_details_text.setHtml(details_html)
        self.main_window.similar_details_text.setVisible(True)
        
        # Mostrar botón de revisión
        self.main_window.review_similar_btn.setVisible(True)
        self.main_window.review_similar_btn.setEnabled(True)
    
    def clear_exact_results(self):
        """Limpia el estado de duplicados exactos"""
        self.main_window.exact_status_label.setText("⏳ Analizando en el análisis inicial...")
        self.main_window.exact_status_label.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #2c5aa0; padding: 4px;"
        )
        self.main_window.exact_details_text.setVisible(False)
        self.main_window.exact_details_text.clear()
        self.main_window.delete_exact_duplicates_btn.setVisible(False)
    
    def clear_similar_results(self):
        """Limpia el estado de duplicados similares"""
        self.main_window.similar_status_label.setText("▶ Haz clic en 'Analizar' para buscar imágenes similares")
        self.main_window.similar_status_label.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #9c27b0; padding: 4px;"
        )
        self.main_window.similar_details_text.setVisible(False)
        self.main_window.similar_details_text.clear()
        self.main_window.review_similar_btn.setVisible(False)
    
    def show_exact_analyzing(self):
        """Muestra estado de análisis en progreso para duplicados exactos"""
        self.main_window.exact_status_label.setText("🔄 Analizando duplicados exactos...")
        self.main_window.exact_status_label.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #007bff; padding: 4px;"
        )
        self.main_window.exact_details_text.setVisible(False)
        self.main_window.delete_exact_duplicates_btn.setVisible(False)
    
    def show_similar_analyzing(self):
        """Muestra estado de análisis en progreso para duplicados similares"""
        self.main_window.similar_status_label.setText("🔄 Analizando duplicados similares... (puede tardar varios minutos)")
        self.main_window.similar_status_label.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #007bff; padding: 4px;"
        )
        self.main_window.similar_details_text.setVisible(False)
        self.main_window.review_similar_btn.setVisible(False)
