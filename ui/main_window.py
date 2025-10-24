"""
Ventana principal de PhotoKit Manager
"""
import os
import logging
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QDialog, QCheckBox,
    QGroupBox, QComboBox, QSplitter, QFrame, QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer

import config
from services.file_renamer import FileRenamer
from ui import styles
from ui.components import Header
from ui.workers import (
    AnalysisWorker, RenamingWorker, LivePhotoCleanupWorker,
    DirectoryUnificationWorker, HEICRemovalWorker
)
from ui.dialogs import (
    RenamingPreviewDialog, LivePhotoCleanupDialog,
    DirectoryUnificationDialog, HEICDuplicateRemovalDialog, SettingsDialog
)
from ui.dialogs import AboutDialog
from services.live_photo_cleaner import LivePhotoCleaner
from services.live_photo_detector import LivePhotoDetector
from services.directory_unifier import DirectoryUnifier
from services.heic_remover import HEICDuplicateRemover
from utils.date_utils import get_file_date, format_renamed_name, is_renamed_filename
from ui.helpers import (
    update_tab_details, show_results_html, reset_analysis_ui,
)
from utils.format_utils import format_size, markdown_like_to_html
from ui.components.progress_bar import create_progress_group as create_progress_bar, show_progress, hide_progress
from ui import tabs

from services.duplicate_detector import DuplicateDetector
from ui.workers import DuplicateAnalysisWorker, DuplicateDeletionWorker
from ui.dialogs import ExactDuplicatesDialog, SimilarDuplicatesDialog
from ui.components import SearchBar


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    def __init__(self):
        super().__init__()

        # Variables de estado
        self.current_directory = None
        self.analysis_results = None
        self.last_analyzed_directory = None

        # Configuración de logging
        self.logs_directory = config.Config.DEFAULT_LOG_DIR
        self.log_level = config.Config.LOG_LEVEL.upper()
        # Asegurar que existe el directorio de logs
        self.logs_directory.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.logs_directory / f"photokit_manager_{timestamp}.log"

        logging.basicConfig(
            level=self.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ],
            force=True
        )

        # Inicializar logger de instancia como `self.logger` (nombre usado en
        # todo el proyecto). Esto centraliza el logger de la ventana principal.
        self.logger = logging.getLogger('PhotokitManager')
        # Alias compatible con otros módulos que esperan `app_logger`
        self.app_logger = self.logger
        self.logger.info("=" * 70)
        self.logger.info("Aplicación iniciada")
        self.logger.info(f"Archivo de log: {self.log_file}")
        self.logger.info("=" * 70)

        # Inicializar servicios
        self.renamer = FileRenamer()
        self.live_photo_detector = LivePhotoDetector()
        self.live_photo_cleaner = LivePhotoCleaner()
        self.directory_unifier = DirectoryUnifier()
        self.heic_remover = HEICDuplicateRemover()

        # Detector de duplicados
        self.duplicate_detector = DuplicateDetector()
        self.duplicate_analysis_results = None

        # Workers
        self.analysis_worker = None
        self.execution_worker = None
        self.active_workers = []
        
        # Inicializar UI
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{config.config.APP_NAME} v{config.config.APP_VERSION}")
        self.setGeometry(100, 100, 1600, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ===== HEADER CON MENÚ DESPLEGABLE =====
        header = Header(self)
        main_layout.addWidget(header)

        # ===== SELECTOR ESTILO SEARCH BAR =====
        search_bar = SearchBar(self)

        # Exponer los controles usados por el resto de MainWindow
        self.directory_edit = search_bar.directory_edit
        self.analyze_btn = search_bar.analyze_btn

        main_layout.addWidget(search_bar)
        main_layout.addSpacing(10)


        # ===== SPLITTER: PANEL RESUMEN + PESTAÑAS =====
        splitter = QSplitter(Qt.Horizontal)
        from ui.components import SummaryPanel
        # Guardar la instancia del componente para poder actualizarlo luego
        self.summary_component = SummaryPanel(self)
        # `create_summary_panel` retorna un widget; mantener compatibilidad
        self.summary_panel = self.summary_component.get_widget()
        splitter.addWidget(self.summary_panel)
        self.tabs_widget = self._create_tabs_widget()
        splitter.addWidget(self.tabs_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([300, 900])
        main_layout.addWidget(splitter, 1)

        # ===== BARRA DE PROGRESO =====
        create_progress_bar(self, main_layout)

        # Reemplazar el botón analyze en el search_layout por un contenedor
        # para que analyze_btn y los botones posteriores ocupen exactamente
        # el mismo lugar (no se verán juntos los tres)
        self.actions_container = QFrame()
        self.actions_container.setFrameStyle(QFrame.NoFrame)
        # Asegurar que el contenedor no tenga fondo ni borde visibles
        self.actions_container.setStyleSheet(styles.STYLE_ACTIONS_CONTAINER)
        self.actions_container.setAttribute(Qt.WA_TranslucentBackground)
        self.actions_layout = QHBoxLayout(self.actions_container)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)

        # Ya existe analyze_btn creado arriba; lo movemos al nuevo contenedor
        # Se añade la referencia guardada en self.analyze_btn
        self.actions_layout.addWidget(self.analyze_btn)

        # Botones que reemplazarán al analyze_btn tras análisis
        # Usar exactamente el mismo estilo y tamaño que el analyze_btn
        self.reanalyze_btn = QPushButton("🔄 Re-analizar")
        self.reanalyze_btn.setVisible(False)
        # Igualar tamaño y estilo exactamente al analyze_btn
        self.reanalyze_btn.setMinimumWidth(200)
        self.reanalyze_btn.setFixedHeight(42)
        self.reanalyze_btn.setCursor(Qt.PointingHandCursor)
        # Reutilizar la hoja de estilos literal del analyze_btn para garantizar
        # identidad visual exacta (incluye gradiente, bordes redondeados, etc.)
        self.reanalyze_btn.setStyleSheet(self.analyze_btn.styleSheet())
        self.reanalyze_btn.clicked.connect(self._reanalyze_same_directory)

        self.change_dir_btn = QPushButton("📂 Cambiar directorio")
        self.change_dir_btn.setVisible(False)
        self.change_dir_btn.setMinimumWidth(200)
        self.change_dir_btn.setFixedHeight(42)
        self.change_dir_btn.setCursor(Qt.PointingHandCursor)
        self.change_dir_btn.setStyleSheet(self.analyze_btn.styleSheet())
        self.change_dir_btn.clicked.connect(self._change_directory_after_analysis)

        # Añadir a layout (serán visibles/ocultos según flujo)
        self.actions_layout.addWidget(self.reanalyze_btn)
        self.actions_layout.addWidget(self.change_dir_btn)

        # Añadir el contenedor de acciones al SearchBar donde estaba el analyze_btn
        # `search_bar` se creó arriba en init_ui; inyectamos el contenedor allí
        try:
            search_bar.add_actions_widget(self.actions_container)
        except NameError:
            # Fallback por seguridad: si no existe search_bar, intentar añadir a un layout global
            pass


    def toggle_config(self):
        """Abre el diálogo de configuración avanzada"""
        dialog = SettingsDialog(self)
        dialog.exec_()

    def show_about_dialog(self):
        """Muestra el diálogo Acerca de usando `AboutDialog`."""
        dialog = AboutDialog(self)
        dialog.exec_()

    
    def _create_tabs_widget(self):
        # Crear mediante el módulo tabs directamente
        return tabs.create_tabs_widget(self)

    def _open_summary_action(self, label_substr):
        """Selecciona la pestaña correspondiente según el botón del summary.

        label_substr: una breve cadena que identifica la funcionalidad (p.ej. 'Live Photos')
        """
        return tabs.open_summary_action(self, label_substr)
    


    # ========================================================================
    # GESTIÓN DE CIERRE Y LIMPIEZA
    # ========================================================================
    
    def closeEvent(self, event):
        """Asegurar limpieza correcta al cerrar"""
        for worker in self.active_workers:
            if worker and worker.isRunning():
                worker.quit()
                worker.wait(1000)
        event.accept()
    
    # ========================================================================
    # MÉTODOS DE CONFIGURACIÓN
    # ========================================================================

    def select_and_analyze_directory(self):
        """Selecciona directorio y analiza automáticamente con confirmación inteligente"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio",
            str(Path.home()),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if not directory:
            return  # Usuario canceló

        new_directory = Path(directory)

        # Verificar si hay un cambio de directorio tras un análisis
        if self.last_analyzed_directory and new_directory != self.last_analyzed_directory:
            reply = QMessageBox.question(
                self,
                "Cambio de Directorio",
                f"Has solicitado cambiar el directorio de análisis.\n\n"
                f"📂 Directorio anterior: {self.last_analyzed_directory.name}\n"
                f"📂 Directorio nuevo: {new_directory.name}\n\n"
                f"⚠️ El análisis anterior se perderá y será necesario realizar un nuevo análisis.\n\n"
                f"¿Deseas continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

            # Usuario confirmó, limpiar análisis previo
            self._reset_analysis_ui()
            self.logger.info(f"Directorio cambiado de {self.last_analyzed_directory} a {new_directory}")

        # Actualizar directorio actual
        self.current_directory = new_directory
        # Mostrar nombre real del directorio (no ruta completa)
        self.directory_edit.setText(f"{self.current_directory.name}")
        self.directory_edit.setToolTip(str(self.current_directory))  # Tooltip con ruta completa

        # Contar archivos rápidamente para dar feedback
        try:
            all_files = list(new_directory.rglob('*'))
            file_count = sum(1 for f in all_files if f.is_file())
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo acceder al directorio:\n{str(e)}"
            )
            return

        # Confirmación inteligente solo para directorios grandes
        if file_count > config.config.LARGE_DIRECTORY_THRESHOLD:
            reply = QMessageBox.question(
                self,
                "Directorio Grande Detectado",
                f"📁 Directorio: {new_directory.name}\n\n"
                f"📊 Se detectaron aproximadamente {file_count:,} archivos.\n\n"
                f"⏱️ Aviso: El análisis de esta cantidad de archivos podría tardar\n"
                f"varios minutos dependiendo de la potencia de tu equipo.\n\n"
                f"¿Deseas iniciar el análisis ahora?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply != QMessageBox.Yes:
                self.logger.info(f"Análisis cancelado por el usuario para: {new_directory}")
                return

        # Ejecutar análisis automáticamente
        self.analyze_directory()

    def browse_logs_directory(self):
        """Cambia directorio de logs"""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Seleccionar Directorio de Logs",
            str(self.logs_directory)
        )
        if directory:
            self.logs_directory = Path(directory)
            self.logger.info(f"Directorio de logs cambiado a: {self.logs_directory}")
    
    

    # ========================================================================
    # ANÁLISIS
    # ========================================================================
    
    def analyze_directory(self):
        """Análisis completo del directorio"""
        if not self.current_directory:
            QMessageBox.warning(self, "Advertencia", "Selecciona un directorio primero")
            return
        
        if not self.current_directory.exists():
            QMessageBox.critical(self, "Error", "El directorio no existe")
            return
        
        # NUEVO: Advertir si hay análisis previo de otro directorio
        if (self.last_analyzed_directory and 
            self.last_analyzed_directory != self.current_directory):
            
            reply = QMessageBox.warning(
                self,
                "Directorio Diferente",
                f"El directorio actual es diferente al último analizado.\n\n"
                f"Último analizado: {self.last_analyzed_directory.name}\n"
                f"Actual: {self.current_directory.name}\n\n"
                "Se realizará un nuevo análisis y se descartará el anterior.\n\n"
                "¿Continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.No:
                return
            
            # Limpiar análisis previo
            self._reset_analysis_ui()
        
        # Limpiar worker anterior si existe
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.analysis_worker.quit()
            self.analysis_worker.wait()

        # Mostrar progreso (modo indeterminado — solo feedback de actividad)
        self.show_progress(0, "Iniciando análisis...")
        
        # Deshabilitar botones
        self.preview_rename_btn.setEnabled(False)
        self.exec_lp_btn.setEnabled(False)
        self.exec_unif_btn.setEnabled(False)
        self.exec_heic_btn.setEnabled(False)
        
        # Crear y configurar worker
        self.analysis_worker = AnalysisWorker(
            self.current_directory,
            self.renamer,
            self.live_photo_detector,
            self.directory_unifier,
            self.heic_remover
        )
        
        # Conectar señales
        self.analysis_worker.phase_update.connect(self.update_phase)
        self.analysis_worker.progress_update.connect(self.update_analysis_progress)
        self.analysis_worker.finished.connect(self.on_analysis_finished)
        self.analysis_worker.error.connect(self.on_analysis_error)
        
        # Autoeliminación cuando termine
        self.analysis_worker.finished.connect(self.analysis_worker.deleteLater)
        self.analysis_worker.error.connect(self.analysis_worker.deleteLater)
        
        # Mantener referencia
        self.active_workers.append(self.analysis_worker)
        
        # Iniciar
        self.analysis_worker.start()
        
        self.logger.info(f"Iniciando análisis de: {self.current_directory}")

        # NOTA: No pasamos callbacks que envíen valores numéricos a la barra de
        # progreso. El progress_bar se mostrará en modo indeterminado mientras
        # haya operaciones en segundo plano. Los mensajes de progreso sí se
        # muestran en la etiqueta.

    def update_analysis_progress(self, current: int, total: int, message: str):
        """Actualiza etiqueta de progreso. Ignora valores numéricos y mantiene
        la barra en modo indeterminado (busy)."""
        try:
            # Mantener la barra en modo indeterminado para evitar mostrar
            # porcentajes/calculos inexactos. Solo actualizar el mensaje.
            self.progress_bar.setMaximum(0)
            self.progress_label.setText(message)
        except Exception:
            # No hacer nada si la UI está en un estado inestable
            pass


    def update_phase(self, phase_text):
        """Actualiza la fase actual del análisis"""
        self.progress_label.setText(phase_text)
        QApplication.processEvents()
    
    def on_analysis_finished(self, results):
        """Callback cuando termina el análisis"""
        # Mostrar botones para re-analizar o cambiar directorio
        self.analyze_btn.setText("🔄 Re-analizar")
        # Quitar el botón principal del layout para que no ocupe espacio
        try:
            self.analyze_btn.setParent(None)
        except Exception:
            # si falla, al menos ocultarlo
            self.analyze_btn.setVisible(False)
        self.reanalyze_btn.setVisible(True)
        self.change_dir_btn.setVisible(True)
        # Asegurar que los botones alternativos estén habilitados al terminar el análisis
        # (especialmente importante después de un re-análisis que los deshabilita)
        self.reanalyze_btn.setEnabled(True)
        self.change_dir_btn.setEnabled(True)
        if self.analysis_worker:
            self.analysis_worker.quit()
            self.analysis_worker.wait(2000)  # Esperar máximo 2 segundos
            if self.analysis_worker in self.active_workers:
                self.active_workers.remove(self.analysis_worker)
            self.analysis_worker = None

        self.hide_progress()
        self.analysis_results = results
        
        # Registrar el directorio que fue analizado
        self.last_analyzed_directory = self.current_directory
        
        # Actualizar panel de resumen
        self.summary_component.update(results)
        
        # Actualizar detalles de cada pestaña
        update_tab_details(self, results)
        
        # Mostrar paneles
        self.summary_panel.setVisible(True)
        self.tabs_widget.setVisible(True)
        
        # Habilitar botones según resultados
        if results.get('renaming') and results['renaming'].get('need_renaming', 0) > 0:
            self.preview_rename_btn.setEnabled(True)
        
        if results.get('live_photos') and len(results['live_photos'].get('groups', [])) > 0:
            self.exec_lp_btn.setEnabled(True)
        
        if results.get('unification') and results['unification'].get('total_files_to_move', 0) > 0:
            self.exec_unif_btn.setEnabled(True)
        
        # CORRECCIÓN: Cambiar de False a True
        if results.get('heic') and results['heic'].get('total_duplicates', 0) > 0:
            self.exec_heic_btn.setEnabled(True)  # ← ERA False, ahora es True
        
        # Mostrar mensaje global solo al completar el análisis por completo
        self._show_results_html("""
            <div style='color: #28a745; font-weight: bold;'>
                ✅ Análisis completado con éxito
            </div>
        """, show_generic_status=True)
        
        self.logger.info(f"Análisis completado para: {self.last_analyzed_directory}")
        
        # Limpiar referencia
        if self.analysis_worker in self.active_workers:
            self.active_workers.remove(self.analysis_worker)
        self.analysis_worker = None

    def _reanalyze_same_directory(self):
        """Reinicia el análisis sobre el mismo directorio sin pedir confirmaciones"""
        # Mantener los botones adicionales visibles pero deshabilitados durante el re-análisis
        # para evitar que el analyze_btn vuelva a aparecer temporalmente.
        self.reanalyze_btn.setVisible(True)
        self.change_dir_btn.setVisible(True)
        self.reanalyze_btn.setEnabled(False)
        self.change_dir_btn.setEnabled(False)

        # Llamar al análisis directamente (analyze_directory maneja la ejecución)
        self.analyze_directory()

    def _change_directory_after_analysis(self):
        """Permite cambiar el directorio tras un análisis, manteniendo el flujo de confirmación actual"""
        # Simular comportamiento de select_and_analyze_directory pero conservando aviso
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar Directorio",
            str(Path.home()),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if not directory:
            return  # Usuario canceló

        new_directory = Path(directory)

        # Si el usuario selecciona el mismo directorio, simplemente re-analizar
        if self.last_analyzed_directory and new_directory == self.last_analyzed_directory:
            # Ocultar botones adicionales antes de re-analizar
            self.reanalyze_btn.setVisible(False)
            self.change_dir_btn.setVisible(False)
            self.analyze_btn.setEnabled(True)
            self.analyze_directory()
            return

        # Preguntar confirmación de cambio de directorio (pérdida de análisis)
        reply = QMessageBox.question(
            self,
            "Cambio de Directorio",
            f"Has solicitado cambiar el directorio de análisis.\n\n"
            f"� Directorio anterior: {self.last_analyzed_directory.name if self.last_analyzed_directory else '—'}\n"
            f"� Directorio nuevo: {new_directory.name}\n\n"
            f"⚠️ El análisis anterior se perderá y será necesario realizar un nuevo análisis.\n\n"
            f"¿Deseas continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        # Tras aceptar el cambio, comprobar tamaño y mostrar advertencia si es grande
        try:
            all_files = list(new_directory.rglob('*'))
            file_count = sum(1 for f in all_files if f.is_file())
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudo acceder al directorio:\n{str(e)}"
            )
            return

        if file_count > config.config.LARGE_DIRECTORY_THRESHOLD:
            reply2 = QMessageBox.question(
                self,
                "Directorio Grande Detectado",
                f"� Directorio: {new_directory.name}\n\n"
                f"� Se detectaron aproximadamente {file_count:,} archivos.\n\n"
                f"⏱️ Aviso: El análisis de esta cantidad de archivos podría tardar\n"
                f"varios minutos dependiendo de la potencia de tu equipo.\n\n"
                f"¿Deseas iniciar el análisis ahora?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply2 != QMessageBox.Yes:
                self.logger.info(f"Cambio de directorio cancelado por el usuario para: {new_directory}")
                return

        # Usuario confirmó, aplicar cambio
        self.current_directory = new_directory
        self.directory_edit.setText(f"{self.current_directory.name}")
        self.directory_edit.setToolTip(str(self.current_directory))

        # Limpiar análisis previo pero NO reinsertar analyze_btn (dejamos
        # visibles los botones alternativos, aunque deshabilitados durante
        # el análisis)
        self._reset_analysis_ui(reinsert_analyze=False)
        # Mostrar alternativas pero deshabilitadas hasta que termine el análisis
        self.reanalyze_btn.setVisible(True)
        self.change_dir_btn.setVisible(True)
        self.reanalyze_btn.setEnabled(False)
        self.change_dir_btn.setEnabled(False)

        # Iniciar nuevo análisis automáticamente
        self.analyze_directory()
    
    def on_analysis_error(self, error):
        """Callback cuando hay error en el análisis"""
        self.hide_progress()
        QMessageBox.critical(self, "Error", f"Error durante el análisis:\n{error}")
        self.logger.error(f"Error en análisis: {error}")

        if self.analysis_worker:
            self.analysis_worker.quit()
            self.analysis_worker.wait(2000)
            if self.analysis_worker in self.active_workers:
                self.active_workers.remove(self.analysis_worker)
            self.analysis_worker = None
        

   
    # ========================================================================
    # RENOMBRADO
    # ========================================================================
    
    def preview_renaming(self):
        """Muestra preview de renombrado"""
        if not self.analysis_results or not self.analysis_results.get('renaming'):
            QMessageBox.warning(self, "Advertencia", "No hay análisis disponible")
            return

        dialog = RenamingPreviewDialog(self.analysis_results['renaming'], self)
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self.renaming_plan = dialog.accepted_plan
            # Ejecutar renombrado directamente desde el diálogo
            # Si el diálogo solo quería preparar el plan sin ejecutar, puede
            # modificarse aquí. Actualmente acepted_plan implica ejecutar.
            self.execute_renaming(skip_confirmation=True)
    
    def execute_renaming(self, skip_confirmation=False):
        """Ejecuta el renombrado"""
        if not hasattr(self, 'renaming_plan'):
            return

        # Si no se solicita omitir confirmación, pedir confirmación al usuario
        if not skip_confirmation:
            reply = QMessageBox.question(
                self,
                "Confirmar",
                f"¿Renombrar {len(self.renaming_plan['plan'])} archivos?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()
        
        self.show_progress(len(self.renaming_plan['plan']), "Renombrando archivos...")

        self.execution_worker = RenamingWorker(
            self.renamer,
            self.renaming_plan['plan'],
            self.renaming_plan['create_backup']
        )
        # Conectar actualizaciones de progreso para mostrar mensajes (ej. backup)
        try:
            self.execution_worker.progress_update.connect(self.update_analysis_progress)
        except Exception:
            pass

        self.execution_worker.finished.connect(self.on_renaming_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)
        
        self.active_workers.append(self.execution_worker)
        self.execution_worker.start()
        
        self.preview_rename_btn.setEnabled(False)
    
    def on_renaming_finished(self, results):
        """Callback al terminar renombrado"""
        self.hide_progress()

        # Actualizar estadísticas si el diálogo está abierto
        for dialog in self.findChildren(RenamingPreviewDialog):
            dialog.update_statistics(results)
        
        html = f"""
            <div style='color: #28a745;'>
                <h4>✅ Renombrado Completado</h4>
                <p><strong>Archivos renombrados:</strong> {results.get('files_renamed', 0)}</p>
                <p><strong>Errores:</strong> {len(results.get('errors', []))}</p>
        """
        
        if results.get('backup_path'):
            html += f"<p><strong>💾 Backup:</strong> {results['backup_path']}</p>"
        
        html += "</div>"
        
        self._show_results_html(html, show_generic_status=False)
        
        if results.get('success'):
            QMessageBox.information(
                self, 
                "Completado",
                f"Se renombraron {results.get('files_renamed', 0)} archivos correctamente"
            )
        # REFRESCAR datos de análisis internos para que la UI muestre el
        # estado actualizado (p. ej. eliminar el cuadro informativo si ya no
        # quedan archivos a renombrar)
        files_renamed = int(results.get('files_renamed', 0))
        if self.analysis_results and self.analysis_results.get('renaming'):
            ren = self.analysis_results['renaming']
            ren['already_renamed'] = ren.get('already_renamed', 0) + files_renamed
            # Reducir need_renaming preservando >= 0
            ren['need_renaming'] = max(0, ren.get('need_renaming', 0) - files_renamed)
            # Si el worker devuelve errores, añadirlos a cannot_process longitud
            errors_count = len(results.get('errors', [])) if results.get('errors') else 0
            if errors_count:
                ren['cannot_process'] = ren.get('cannot_process', 0) + errors_count

            # Ajustar contador de conflictos según los conflictos resueltos durante la operación
            conflicts_resolved = int(results.get('conflicts_resolved', 0)) if results.get('conflicts_resolved') is not None else 0
            if conflicts_resolved:
                ren['conflicts'] = max(0, ren.get('conflicts', 0) - conflicts_resolved)

            self.analysis_results['renaming'] = ren

            # Actualizar paneles y pestañas para reflejar los nuevos valores
            self.summary_component.update(self.analysis_results)
            update_tab_details(self, self.analysis_results)

            # Habilitar/deshabilitar botón de preview según queden archivos
            self.preview_rename_btn.setEnabled(ren.get('need_renaming', 0) > 0)
        else:
            # Si no hay análisis en memoria, simplemente deshabilitar preview
            self.preview_rename_btn.setEnabled(False)

        if self.execution_worker in self.active_workers:
            self.active_workers.remove(self.execution_worker)
        self.execution_worker = None
        # Programar re-análisis automático para mantener consistencia
        try:
            self._schedule_reanalysis()
        except Exception:
            # No interrumpir el flujo por un fallo en el reanálisis
            self.logger.exception("Error al programar re-análisis tras renombrado")
    
    # ========================================================================
    # LIVE PHOTOS
    # ========================================================================
    
    def cleanup_live_photos(self):
        """Limpia Live Photos"""
        if not self.analysis_results or not self.analysis_results.get('live_photos'):
            return
        
        lp_results = self.analysis_results['live_photos']
        
        lp_groups = lp_results.get('groups', [])
            
        if not lp_groups:
            QMessageBox.information(self, "Live Photos", "No hay Live Photos para limpiar")
            return
        
        try:
            # Por defecto, eliminamos los videos y mantenemos las imágenes
            cleanup_analysis = {
                'live_photos_found': len(lp_groups),
                'total_space': lp_results.get('total_space', 0),
                'space_to_free': lp_results.get('space_to_free', 0),
                'cleanup_mode': 'keep_image',
                'files_to_delete': [
                    {
                        'path': Path(group['video_path']),
                        'size': group['video_size'],
                        'type': 'video',
                        'base_name': group['base_name']
                    } 
                    for group in lp_groups
                ],
                'files_to_keep': [
                    {
                        'path': Path(group['image_path']),
                        'size': group['image_size'],
                        'type': 'image',
                        'base_name': group['base_name']
                    }
                    for group in lp_groups
                ],
                'groups': lp_groups  # mantener la referencia a los grupos originales
            }
            
            dialog = LivePhotoCleanupDialog(cleanup_analysis, self)
            if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
                self._execute_lp_cleanup(dialog.accepted_plan)
                
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self, "Error", f"Error preparando limpieza LP:\n{error_msg}")
            self.logger.error(f"Error preparando limpieza LP: {error_msg}")
    
    def _execute_lp_cleanup(self, plan):
        """Ejecuta la limpieza de Live Photos"""
        count = len(plan['files_to_delete'])
        space = sum(file_info['size'] for file_info in plan['files_to_delete'])
        space_formatted = format_size(space)

        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Eliminar {count} archivos ({space_formatted})?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()
        
        self.show_progress(count, "Limpiando Live Photos...")
        
        self.execution_worker = LivePhotoCleanupWorker(self.live_photo_cleaner, plan)
        # Mostrar mensajes de progreso del worker (p.ej. creación de backup)
        try:
            self.execution_worker.progress_update.connect(self.update_analysis_progress)
        except Exception:
            pass

        self.execution_worker.finished.connect(self.on_lp_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)
        
        self.active_workers.append(self.execution_worker)
        self.execution_worker.start()
        
        self.exec_lp_btn.setEnabled(False)
    
    def on_lp_finished(self, results):
        """Callback al terminar limpieza de Live Photos"""
        self.hide_progress()
        
        space_freed = results.get('space_freed', 0)
        
        html = f"""
            <div style='color: #28a745;'>
                <h4>✅ Limpieza de Live Photos Completada</h4>
                <p><strong>Archivos eliminados:</strong> {results.get('files_deleted', 0)}</p>
                <p><strong>Espacio liberado:</strong> {format_size(space_freed)}</p>
                <p><strong>Errores:</strong> {len(results.get('errors', []))}</p>
        """
        
        if results.get('backup_path'):
            html += f"<p><strong>💾 Backup:</strong> {results['backup_path']}</p>"
        
        if results.get('dry_run'):
            html += "<p><strong>ℹ️ Modo simulación</strong> - No se eliminaron archivos realmente</p>"
        
        html += "</div>"
        
        self._show_results_html(html, show_generic_status=False)
        
        if results.get('success'):
            QMessageBox.information(
                self,
                "Completado",
                f"Se eliminaron {results.get('files_deleted', 0)} archivos"
            )
        
        self.exec_lp_btn.setEnabled(False)
        
        if self.execution_worker in self.active_workers:
            self.active_workers.remove(self.execution_worker)
        self.execution_worker = None
        # Programar re-análisis automático (estructura de ficheros ha cambiado)
        try:
            self._schedule_reanalysis()
        except Exception:
            self.logger.exception("Error al programar re-análisis tras limpieza Live Photos")
    
    # ========================================================================
    # UNIFICACIÓN
    # ========================================================================
    
    def unify_directories(self):
        """Unifica directorios"""
        if not self.analysis_results or not self.analysis_results.get('unification'):
            return
        
        unif_analysis = self.analysis_results['unification']
        
        if unif_analysis.get('total_files_to_move', 0) == 0:
            QMessageBox.information(self, "Unificación", "No hay archivos para mover")
            return
        
        dialog = DirectoryUnificationDialog(unif_analysis, self)
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self._execute_unification(dialog.accepted_plan)
    
    def _execute_unification(self, plan):
        """Ejecuta la unificación"""
        count = len(plan['move_plan'])
        
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Mover {count} archivos al directorio raíz?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()
        
        self.show_progress(count, "Unificando directorios...")
        
        self.execution_worker = DirectoryUnificationWorker(
            self.directory_unifier,
            plan['move_plan'],
            plan['create_backup']
        )
        # Mostrar mensajes de progreso del worker (p.ej. "Creando backup antes de unificar...")
        try:
            self.execution_worker.progress_update.connect(self.update_analysis_progress)
        except Exception:
            pass

        self.execution_worker.finished.connect(self.on_unification_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)
        
        self.active_workers.append(self.execution_worker)
        self.execution_worker.start()
        
        self.exec_unif_btn.setEnabled(False)
    
    def on_unification_finished(self, results):
        """Callback al terminar unificación"""
        self.hide_progress()
        
        html = f"""
            <div style='color: #28a745;'>
                <h4>✅ Unificación Completada</h4>
                <p><strong>Archivos movidos:</strong> {results.get('files_moved', 0)}</p>
                <p><strong>Directorios eliminados:</strong> {results.get('empty_directories_removed', 0)}</p>
                <p><strong>Errores:</strong> {len(results.get('errors', []))}</p>
        """
        
        if results.get('backup_path'):
            html += f"<p><strong>💾 Backup:</strong> {results['backup_path']}</p>"
        
        html += "</div>"
        
        self._show_results_html(html, show_generic_status=False)
        
        if results.get('success'):
            QMessageBox.information(
                self,
                "Completado",
                f"Se movieron {results.get('files_moved', 0)} archivos"
            )
        
        self.exec_unif_btn.setEnabled(False)
        # Actualizar análisis interno para reflejar cambios en la estructura
        try:
            if self.current_directory and self.directory_unifier:
                # Re-analizar la estructura para obtener valores actualizados
                updated_unif = self.directory_unifier.analyze_directory_structure(self.current_directory)

                if not self.analysis_results:
                    self.analysis_results = {}

                self.analysis_results['unification'] = updated_unif

                # Refrescar UI
                self.summary_component.update(self.analysis_results)
                update_tab_details(self, self.analysis_results)

                # Ajustar estado del botón según queden archivos por mover
                if updated_unif.get('total_files_to_move', 0) > 0:
                    self.exec_unif_btn.setEnabled(True)
                else:
                    self.exec_unif_btn.setEnabled(False)

        except Exception as e:
            # Registrar pero no interrumpir
            self.logger.error(f"Error re-analizando después de unificación: {e}")

        if self.execution_worker in self.active_workers:
            self.active_workers.remove(self.execution_worker)
        self.execution_worker = None
        # Programar re-análisis completo tras la unificación para evitar inconsistencias
        try:
            self._schedule_reanalysis()
        except Exception:
            self.logger.exception("Error al programar re-análisis tras unificación")
    
    # ========================================================================
    # HEIC
    # ========================================================================
    
    def remove_heic(self):
        """Elimina duplicados HEIC"""
        if not self.analysis_results or not self.analysis_results.get('heic'):
            return
        
        heic_analysis = self.analysis_results['heic']
        
        if heic_analysis.get('total_duplicates', 0) == 0:
            QMessageBox.information(self, "HEIC", "No hay duplicados para eliminar")
            return
        
        dialog = HEICDuplicateRemovalDialog(heic_analysis, self)
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self._execute_heic_removal(dialog.accepted_plan)
    
    def _execute_heic_removal(self, plan):
        """Ejecuta la eliminación de duplicados HEIC"""
        count = len(plan['duplicate_pairs'])
        format_del = 'HEIC' if plan['keep_format'] == 'jpg' else 'JPG'
        
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Eliminar {count} archivos {format_del}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Limpiar worker anterior
        if self.execution_worker and self.execution_worker.isRunning():
            self.execution_worker.quit()
            self.execution_worker.wait()
        
        self.show_progress(count, f"Eliminando archivos {format_del}...")
        
        self.execution_worker = HEICRemovalWorker(
            self.heic_remover,
            plan['duplicate_pairs'],
            plan['keep_format'],
            plan['create_backup']
        )
        # Mostrar mensajes de progreso del worker (p.ej. creación de backup)
        try:
            self.execution_worker.progress_update.connect(self.update_analysis_progress)
        except Exception:
            pass

        self.execution_worker.finished.connect(self.on_heic_finished)
        self.execution_worker.error.connect(self.on_operation_error)
        self.execution_worker.finished.connect(self.execution_worker.deleteLater)
        self.execution_worker.error.connect(self.execution_worker.deleteLater)
        
        self.active_workers.append(self.execution_worker)
        self.execution_worker.start()
        
        self.exec_heic_btn.setEnabled(False)
    
    def on_heic_finished(self, results):
        """Callback al terminar eliminación HEIC"""
        self.hide_progress()
        
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
        
        self._show_results_html(html, show_generic_status=False)
        
        if results.get('success'):
            QMessageBox.information(
                self,
                "Completado",
                f"Se eliminaron {results.get('files_removed', 0)} duplicados"
            )
        
        self.exec_heic_btn.setEnabled(False)
        
        if self.execution_worker in self.active_workers:
            self.active_workers.remove(self.execution_worker)
        self.execution_worker = None

        # Programar re-análisis automático tras eliminación HEIC
        try:
            self._schedule_reanalysis()
        except Exception:
            self.logger.exception("Error al programar re-análisis tras eliminación HEIC")

    def _schedule_reanalysis(self, delay_ms: int = 500):
        """Programa un re-análisis del directorio actual tras operaciones que cambian archivos.

        Usa QTimer.singleShot para evitar reentradas inmediatas y dar tiempo al FS a estabilizarse.
        Si no hay directorio analizado previamente, no hace nada.
        """
        # Si no hay un directorio actual o no se analizó previamente, no re-analizar
        if not self.current_directory:
            self.logger.debug("No hay directorio actual: se omite re-análisis programado")
            return

        # Si el último directorio analizado es distinto, aún así forzamos re-análisis del actual
        def _do_reanalyze():
            try:
                self.logger.info("Iniciando re-análisis automático tras operación que modifica archivos")
                # Asegurarse de que los botones estén en estado adecuado y llamar a analyze_directory
                # Llamamos a _reanalyze_same_directory para respetar el flujo existente
                # Que deshabilita/gestiona botones correctamente
                self._reanalyze_same_directory()
            except Exception:
                self.logger.exception("Fallo durante re-análisis automático")

        # Usar un pequeño retardo para dejar que el sistema de ficheros se estabilice
        QTimer.singleShot(delay_ms, _do_reanalyze)


    # ========================================================================
    # UTILIDADES
    # ========================================================================
    
    def show_progress(self, maximum, message="Procesando"):
        """Muestra la barra de progreso"""
        return show_progress(self, maximum, message)
    
    def hide_progress(self):
        """Oculta la barra de progreso"""
        return hide_progress(self)
    
    def _show_results_html(self, html: str, show_generic_status: bool = False):
        """Muestra resultados que antes iban al QTextEdit removido.

        En lugar de escribir en un QTextEdit, registramos el HTML y mostramos
        un mensaje breve en la statusBar. Esto evita AttributeError si el
        elemento fue eliminado.
        """

        return show_results_html(self, html, show_generic_status)
    
    def on_operation_error(self, error):
        """Callback genérico para errores"""
        self.hide_progress()
        QMessageBox.critical(self, "Error", f"Error durante la operación:\n{error}")
        self.logger.error(f"Error: {error}")

        # Limpiar referencia
        if self.execution_worker in self.active_workers:
            self.active_workers.remove(self.execution_worker)
        self.execution_worker = None
    

    def _reset_analysis_ui(self, reinsert_analyze=True):
        """Reinicia la UI tras cambiar de directorio
        Args:
            reinsert_analyze (bool): si True (por defecto) se reinsertará el
                `analyze_btn` en el layout; si False no se tocará (útil cuando
                el flujo actual debe mantener los botones alternativos visibles).
        """
        return reset_analysis_ui(self, reinsert_analyze)


    # =========================================================================
    # MÉTODOS PARA DUPLICADOS
    # =========================================================================
    
    def on_analyze_duplicates(self):
        """Inicia el análisis de duplicados según el modo seleccionado"""
        if not self.current_directory:
            QMessageBox.warning(
                self,
                "Directorio no seleccionado",
                "Por favor selecciona un directorio primero."
            )
            return
        
        # Determinar modo
        is_exact_mode = self.exact_mode_radio.isChecked()
        mode = 'exact' if is_exact_mode else 'perceptual'
        sensitivity = self.sensitivity_slider.value()
        
        self.logger.info(f"Iniciando análisis de duplicados: modo={mode}, sensitivity={sensitivity}")
        
        # Deshabilitar botones
        self.analyze_duplicates_btn.setEnabled(False)
        self.delete_exact_duplicates_btn.setVisible(False)
        self.review_similar_btn.setVisible(False)
        
        # Actualizar UI
        mode_text = "exactos" if is_exact_mode else "similares"
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(
                f"🔄 Analizando duplicados {mode_text}...\n"
                f"Por favor espera, esto puede tardar varios minutos."
            ))
        except Exception:
            pass
        
        # Crear y ejecutar worker
        self.duplicate_worker = DuplicateAnalysisWorker(
            self.duplicate_detector,
            self.current_directory,
            mode=mode,
            sensitivity=sensitivity
        )
        
        self.duplicate_worker.progress_update.connect(self._update_duplicate_progress)
        self.duplicate_worker.finished.connect(self._on_duplicate_analysis_finished)
        self.duplicate_worker.error.connect(self._on_duplicate_analysis_error)
        
        self.duplicate_worker.start()
    
    def _update_duplicate_progress(self, current, total, message):
        """Actualiza el progreso del análisis de duplicados"""
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(f"🔄 {message}"))
        except Exception:
            pass
    
    def _on_duplicate_analysis_finished(self, results):
        """Maneja la finalización del análisis de duplicados"""
        self.logger.info(f"Análisis completado: {results.get('mode')}")
        
        self.duplicate_analysis_results = results
        self.analyze_duplicates_btn.setEnabled(True)
        
        if results.get('error'):
            QMessageBox.critical(
                self,
                "Error en Análisis",
                f"Error: {results['error']}\n\n"
                "Asegúrate de tener instalados imagehash y opencv-python para detección perceptual."
            )
            try:
                self.duplicates_details.setHtml(markdown_like_to_html(f"❌ Error: {results['error']}"))
            except Exception:
                pass
            return
        
        # Mostrar resultados según el modo
        if results['mode'] == 'exact':
            self._show_exact_results(results)
        else:  # perceptual
            self._show_similar_results(results)
    
    def _show_exact_results(self, results):
        """Muestra resultados de duplicados exactos"""
        total_groups = results['total_groups']
        total_duplicates = results['total_duplicates']
        space_wasted = results['space_wasted']
        
        if total_groups == 0:
            try:
                self.duplicates_details.setHtml(markdown_like_to_html(
                    "✅ **¡Excelente!** No se encontraron duplicados exactos.\n\n"
                    "Tu biblioteca está limpia de copias idénticas."
                ))
            except Exception:
                pass
            return
        
        # Formatear tamaño usando helper central
        size_str = format_size(space_wasted)
        
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(
                f"**📊 Duplicados Exactos Encontrados:**\n\n"
                f"• **Grupos encontrados:** {total_groups}\n"
                f"• **Archivos duplicados:** {total_duplicates}\n"
                f"• **Espacio desperdiciado:** {size_str}\n\n"
                f"✅ Estos son duplicados 100% idénticos.\n"
                f"Puedes eliminarlos de forma segura."
            ))
        except Exception:
            pass
        
        # Mostrar botón de eliminación
        self.delete_exact_duplicates_btn.setVisible(True)
    
    def _show_similar_results(self, results):
        """Muestra resultados de duplicados similares"""
        total_groups = results['total_groups']
        total_similar = results['total_similar']
        space_potential = results['space_potential']
        min_sim = results.get('min_similarity', 0)
        max_sim = results.get('max_similarity', 0)
        
        if total_groups == 0:
            try:
                self.duplicates_details.setHtml(markdown_like_to_html(
                    "✅ **No se encontraron duplicados similares** con la sensibilidad actual.\n\n"
                    "Prueba aumentar la sensibilidad si quieres detectar archivos menos similares."
                ))
            except Exception:
                pass
            return
        
        # Formatear tamaño usando helper central
        size_str = format_size(space_potential)
        
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(
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
        
        # Mostrar botón de revisión
        self.review_similar_btn.setVisible(True)
        # Asegurarse de que el botón esté habilitado (puede haber quedado deshabilitado
        # por operaciones previas como una eliminación). Esto evita que el botón
        # no responda cuando solo hay un grupo encontrado.
        self.review_similar_btn.setEnabled(True)
    
    def _on_duplicate_analysis_error(self, error_msg):
        """Maneja errores en el análisis de duplicados"""
        self.logger.error(f"Error en análisis: {error_msg}")
        
        QMessageBox.critical(
            self,
            "Error en Análisis",
            f"Ocurrió un error durante el análisis:\n\n{error_msg}"
        )
        
        try:
            self.duplicates_details.setHtml(markdown_like_to_html("❌ Error en el análisis. Revisa el log para más detalles."))
        except Exception:
            pass
        
        self.analyze_duplicates_btn.setEnabled(True)
    
    def on_delete_exact_duplicates(self):
        """Muestra diálogo para eliminar duplicados exactos"""
        if not self.duplicate_analysis_results:
            return
        
        dialog = ExactDuplicatesDialog(self.duplicate_analysis_results, self)
        
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self._execute_duplicate_deletion(dialog.accepted_plan)
    
    def on_review_similar_duplicates(self):
        """Muestra diálogo para revisar duplicados similares"""
        if not self.duplicate_analysis_results:
            return
        
        dialog = SimilarDuplicatesDialog(self.duplicate_analysis_results, self)
        
        if dialog.exec_() == QDialog.Accepted and dialog.accepted_plan:
            self._execute_duplicate_deletion(dialog.accepted_plan)
    
    def _execute_duplicate_deletion(self, plan):
        """Ejecuta la eliminación de duplicados"""
        groups = plan['groups']
        keep_strategy = plan['keep_strategy']
        create_backup = plan['create_backup']
        
        # Confirmación final
        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Estás seguro de que deseas eliminar los archivos seleccionados?\n\n"
            f"Se eliminarán archivos de {len(groups)} grupos.\n"
            f"{'Se creará un backup de seguridad.' if create_backup else 'NO se creará backup.'}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.logger.info(f"Ejecutando eliminación de duplicados: {len(groups)} grupos")
        
        # Deshabilitar botones
        self.delete_exact_duplicates_btn.setEnabled(False)
        self.review_similar_btn.setEnabled(False)
        self.analyze_duplicates_btn.setEnabled(False)
        
        try:
            self.duplicates_details.setHtml(markdown_like_to_html("🗑️ Eliminando archivos...\nPor favor espera."))
        except Exception:
            pass
        
        # Crear y ejecutar worker
        self.deletion_worker = DuplicateDeletionWorker(
            self.duplicate_detector,
            groups,
            keep_strategy,
            create_backup
        )
        
        self.deletion_worker.progress_update.connect(self._update_deletion_progress)
        self.deletion_worker.finished.connect(self._on_deletion_finished)
        self.deletion_worker.error.connect(self._on_deletion_error)
        
        self.deletion_worker.start()
    
    def _update_deletion_progress(self, current, total, message):
        """Actualiza progreso de eliminación"""
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(f"🗑️ {message}"))
        except Exception:
            pass
    
    def _on_deletion_finished(self, results):
        """Maneja finalización de eliminación"""
        files_deleted = results['files_deleted']
        space_freed = results['space_freed']
        errors = results['errors']
        backup_path = results.get('backup_path')
        
        # Formatear tamaño usando helper central
        size_str = format_size(space_freed)
        
        self.logger.info(f"Eliminación completada: {files_deleted} archivos, {size_str} liberados")
        
        # Mostrar mensaje de éxito
        msg = (
            f"✅ **Eliminación Completada**\n\n"
            f"• Archivos eliminados: {files_deleted}\n"
            f"• Espacio liberado: {size_str}\n"
        )
        
        if backup_path:
            msg += f"\n📦 Backup guardado en:\n{backup_path}"
        
        if errors:
            msg += f"\n\n⚠️ Errores: {len(errors)}"
        
        QMessageBox.information(self, "Eliminación Completada", msg)
        
        # Actualizar UI
        try:
            self.duplicates_details.setHtml(markdown_like_to_html(
                f"✅ **Eliminación completada exitosamente**\n\n"
                f"• {files_deleted} archivos eliminados\n"
                f"• {size_str} liberados\n\n"
                f"Ejecuta un nuevo análisis para verificar."
            ))
        except Exception:
            pass
        
        # Limpiar resultados y restaurar botones
        self.duplicate_analysis_results = None
        self.analyze_duplicates_btn.setEnabled(True)
        self.delete_exact_duplicates_btn.setVisible(False)
        self.review_similar_btn.setVisible(False)
    
    def _on_deletion_error(self, error_msg):
        """Maneja errores en eliminación"""
        self.logger.error(f"Error en eliminación: {error_msg}")
        
        QMessageBox.critical(
            self,
            "Error en Eliminación",
            f"Ocurrió un error durante la eliminación:\n\n{error_msg}"
        )
        
        self.analyze_duplicates_btn.setEnabled(True)
        self.delete_exact_duplicates_btn.setEnabled(True)
        self.review_similar_btn.setEnabled(True)
