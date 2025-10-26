"""Controlador de presentación de resultados.

Centraliza toda la lógica de presentación de resultados HTML,
actualización de paneles y gestión de estadísticas.
"""
from PyQt5.QtCore import QObject

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
            try:
                self.logger.info('Operación completada — revisa el log para detalles')
            except Exception:
                try:
                    import config
                    self.main_window.setWindowTitle(
                        f"{config.Config.APP_NAME} — Operación completada"
                    )
                except Exception:
                    pass

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

    def format_renaming_results(self, results: dict) -> str:
        """Genera HTML para resultados de renombrado

        Args:
            results: Diccionario con resultados de renombrado

        Returns:
            HTML formateado
        """
        html = f"""
            <div style='color: #28a745;'>
                <h4>✅ Renombrado Completado</h4>
                <p><strong>Archivos renombrados:</strong> {results.get('files_renamed', 0)}</p>
                <p><strong>Errores:</strong> {len(results.get('errors', []))}</p>
        """

        if results.get('backup_path'):
            html += f"<p><strong>💾 Backup:</strong> {results['backup_path']}</p>"

        html += "</div>"
        return html

    def format_live_photo_results(self, results: dict) -> str:
        """Genera HTML para resultados de limpieza Live Photos

        Args:
            results: Diccionario con resultados de limpieza

        Returns:
            HTML formateado
        """
        dry_run = bool(results.get('dry_run'))
        simulated_count = results.get('simulated_files_deleted', 0)
        simulated_space = results.get('simulated_space_freed', 0)
        space_freed = results.get('space_freed', 0)

        if dry_run:
            space_display = format_size(simulated_space)
            files_display = f"{simulated_count} (simulado)"
        else:
            space_display = format_size(space_freed)
            files_display = f"{results.get('files_deleted', 0)}"

        html = f"""
            <div style='color: #28a745;'>
                <h4>✅ Limpieza de Live Photos Completada</h4>
                <p><strong>Archivos eliminados:</strong> {files_display}</p>
                <p><strong>Espacio liberado:</strong> {space_display}</p>
                <p><strong>Errores:</strong> {len(results.get('errors', []))}</p>
        """

        if results.get('backup_path'):
            html += f"<p><strong>💾 Backup:</strong> {results['backup_path']}</p>"

        if dry_run:
            html += "<p><strong>ℹ️ Modo simulación</strong> - No se eliminaron archivos realmente</p>"

        html += "</div>"
        return html

    def format_organization_results(self, results: dict) -> str:
        """Genera HTML para resultados de organización

        Args:
            results: Diccionario con resultados de organización

        Returns:
            HTML formateado
        """
        html = f"""
            <div style='color: #28a745;'>
                <h4>✅ Organización Completada</h4>
                <p><strong>Archivos movidos:</strong> {results.get('files_moved', 0)}</p>
                <p><strong>Directorios eliminados:</strong> {results.get('empty_directories_removed', 0)}</p>
                <p><strong>Errores:</strong> {len(results.get('errors', []))}</p>
        """

        if results.get('backup_path'):
            html += f"<p><strong>💾 Backup:</strong> {results['backup_path']}</p>"

        html += "</div>"
        return html

    def format_heic_results(self, results: dict) -> str:
        """Genera HTML para resultados de eliminación HEIC

        Args:
            results: Diccionario con resultados de eliminación HEIC

        Returns:
            HTML formateado
        """
        space_freed = results.get('space_freed', 0)

        html = f"""
            <div style='color: #28a745;'>
                <h4>✅ Eliminación de Duplicados HEIC Completada</h4>
                <p><strong>Archivos eliminados:</strong> {results.get('files_removed', 0)}</p>
                <p><strong>Espacio liberado:</strong> {format_size(space_freed)}</p>
                <p><strong>Errores:</strong> {len(results.get('errors', []))}</p>
        """

        if results.get('backup_path'):
            html += f"<p><strong>💾 Backup:</strong> {results['backup_path']}</p>"

        if results.get('kept_format'):
            html += f"<p><strong>📋 Formato mantenido:</strong> {results['kept_format'].upper()}</p>"

        html += "</div>"
        return html

    def show_exact_results(self, results: dict):
        """Formatea y muestra resultados de duplicados exactos

        Args:
            results: Diccionario con resultados de duplicados exactos
        """
        # Verificar que el modo actual sea exact antes de mostrar
        if not self.main_window.exact_mode_radio.isChecked():
            self.logger.warning("Modo actual no es 'exact', ignorando show_exact_results")
            return

        total_groups = results['total_groups']
        total_duplicates = results['total_duplicates']
        space_wasted = results['space_wasted']

        if total_groups == 0:
            try:
                self.main_window.duplicates_details.setHtml(markdown_like_to_html(
                    "✅ **¡Excelente!** No se encontraron duplicados exactos.\n\n"
                    "Tu biblioteca está limpia de copias idénticas."
                ))
            except Exception:
                pass
            return

        size_str = format_size(space_wasted)

        try:
            self.main_window.duplicates_details.setHtml(markdown_like_to_html(
                f"**📊 Duplicados Exactos Encontrados:**\n\n"
                f"• **Grupos encontrados:** {total_groups}\n"
                f"• **Archivos duplicados:** {total_duplicates}\n"
                f"• **Espacio desperdiciado:** {size_str}\n\n"
                f"✅ Estos son duplicados 100% idénticos.\n"
                f"Puedes eliminarlos de forma segura."
            ))
        except Exception:
            pass

        # Mostrar botón de eliminación solo si hay grupos
        try:
            self.main_window.delete_exact_duplicates_btn.setVisible(total_groups > 0)
            self.main_window.delete_exact_duplicates_btn.setEnabled(total_groups > 0)
        except Exception:
            pass

    def show_similar_results(self, results: dict):
        """Formatea y muestra resultados de duplicados similares

        Args:
            results: Diccionario con resultados de duplicados similares
        """
        # Verificar que el modo actual sea similar antes de mostrar
        if not self.main_window.similar_mode_radio.isChecked():
            self.logger.warning("Modo actual no es 'similar', ignorando show_similar_results")
            return

        total_groups = results['total_groups']
        total_similar = results['total_similar']
        space_potential = results['space_potential']
        min_sim = results.get('min_similarity', 0)
        max_sim = results.get('max_similarity', 0)

        if total_groups == 0:
            try:
                self.main_window.duplicates_details.setHtml(markdown_like_to_html(
                    "✅ **No se encontraron duplicados similares** con la sensibilidad actual.\n\n"
                    "Prueba aumentar la sensibilidad si quieres detectar archivos menos similares."
                ))
            except Exception:
                pass
            return

        size_str = format_size(space_potential)

        try:
            self.main_window.duplicates_details.setHtml(markdown_like_to_html(
                f"**🎨 Duplicados Similares Encontrados:**\n\n"
                f"• **Grupos de similitud:** {total_groups}\n"
                f"• **Archivos similares:** {total_similar}\n"
                f"• **Rango de similitud:** {min_sim}-{max_sim}%\n"
                f"• **Espacio potencial:** {size_str}\n\n"
                f"⚠️ **Requiere revisión manual** antes de eliminar.\n"
                f"Estos archivos NO son idénticos."
            ))
        except Exception:
            pass

        # Mostrar botón de revisión solo si hay grupos
        try:
            self.main_window.review_similar_btn.setVisible(total_groups > 0)
            self.main_window.review_similar_btn.setEnabled(total_groups > 0)
        except Exception:
            pass
