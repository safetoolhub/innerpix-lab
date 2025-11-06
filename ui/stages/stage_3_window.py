"""
Stage 3: Grid de herramientas.
Muestra el resumen del análisis y el grid de herramientas disponibles.
"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QWidget, QGridLayout, QMessageBox
from PyQt6.QtCore import QTimer, pyqtSignal

from .base_stage import BaseStage
from ui.styles.design_system import DesignSystem
from ui.widgets.summary_card import SummaryCard
from ui.widgets.tool_card import ToolCard
from ui.dialogs.live_photos_dialog import LivePhotoCleanupDialog
from ui.dialogs.heic_dialog import HEICDuplicateRemovalDialog
from ui.dialogs.exact_duplicates_dialog import ExactDuplicatesDialog
from ui.dialogs.similar_duplicates_dialog import SimilarDuplicatesDialog
from ui.dialogs.organization_dialog import FileOrganizationDialog
from ui.dialogs.renaming_dialog import RenamingPreviewDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from utils.format_utils import format_size, format_file_count


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

    def setup_ui(self) -> None:
        """Configura la interfaz de usuario del Stage 3."""
        self.logger.info("Configurando UI del Stage 3")

        # Limpiar el layout principal antes de agregar nuevos widgets
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().hide()
                child.widget().setParent(None)

        # Crear y mostrar header
        self.header = self.create_header(
            on_settings_clicked=self._on_settings_clicked,
            on_about_clicked=self._on_about_clicked
        )
        self.main_layout.addWidget(self.header)
        self.main_layout.addSpacing(DesignSystem.SPACE_20)

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
        # Crear y mostrar summary card
        self.summary_card = SummaryCard(self.selected_folder)
        self.summary_card.change_folder_requested.connect(self._on_change_folder)
        self.summary_card.reanalyze_requested.connect(self._on_reanalyze)
        self.main_layout.addWidget(self.summary_card)
        # No usar fade_in para evitar problemas con el scroll
        # self.fade_in_widget(self.summary_card, duration=400)

        # Actualizar estadísticas de la summary card
        stats = self.analysis_results.get('stats', {})
        total_files = stats.get('total', 0)
        # TODO: Obtener tamaño total si está disponible
        self.summary_card.update_stats(total_files, 0)

        # Calcular espacio recuperable
        recoverable = self._calculate_recoverable_space()
        self.summary_card.update_recoverable_space(recoverable)

        # Crear grid de herramientas con delay escalonado
        QTimer.singleShot(200, self._create_tools_grid)

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
        grid_layout.setSpacing(16)  # DesignSystem.SPACE_16
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Obtener datos de análisis para configurar las cards
        lp_data = self.analysis_results.get('live_photos', {})
        heic_data = self.analysis_results.get('heic', {})
        dup_data = self.analysis_results.get('duplicates', {})
        stats = self.analysis_results.get('stats', {})

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
            lp_data = self.analysis_results.get('live_photos', {})
            if not lp_data:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de Live Photos")
                return
            dialog = LivePhotoCleanupDialog(lp_data, self.main_window)

        elif tool_id == 'heic':
            heic_data = self.analysis_results.get('heic', {})
            if not heic_data:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de HEIC/JPG")
                return
            dialog = HEICDuplicateRemovalDialog(heic_data, self.main_window)

        elif tool_id == 'exact_duplicates':
            dup_data = self.analysis_results.get('duplicates', {})
            if not dup_data:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de Duplicados Exactos")
                return
            dialog = ExactDuplicatesDialog(dup_data, self.main_window)

        elif tool_id == 'similar_duplicates':
            similar_data = self.analysis_results.get('similar', {})
            if not similar_data:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de Duplicados Similares")
                return
            dialog = SimilarDuplicatesDialog(similar_data, self.main_window)

        elif tool_id == 'organize':
            org_data = self.analysis_results.get('organization', {})
            if not org_data:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de Organización")
                return
            dialog = FileOrganizationDialog(org_data, self.main_window)

        elif tool_id == 'rename':
            rename_data = self.analysis_results.get('rename', {})
            if not rename_data:
                QMessageBox.warning(self.main_window, "Sin resultados", "No hay datos de Renombrado")
                return
            dialog = RenamingPreviewDialog(rename_data, self.main_window)

        if dialog:
            dialog.exec()

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