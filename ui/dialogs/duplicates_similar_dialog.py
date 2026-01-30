"""
Diálogo de gestión de archivos similares (70-95% similitud).

Este diálogo está diseñado para archivos SIMILARES pero NO idénticos.
Para copias visuales idénticas (100%), usar el diálogo Visual Identical.

Flujo:
1. Los hashes perceptuales ya están calculados (DuplicatesSimilarAnalysis)
2. El diálogo se muestra con estado de carga
3. El clustering se ejecuta después de que el diálogo sea visible
4. El usuario ajusta sensibilidad con slider (regenera en tiempo real)
"""

from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSlider, QPushButton,
    QDialogButtonBox, QCheckBox, QScrollArea, QWidget,
    QGridLayout, QProgressBar, QMenu
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QColor
from services.duplicates_similar_service import DuplicatesSimilarAnalysis
from services.file_metadata_repository_cache import FileInfoRepositoryCache
from services.result_types import DuplicateGroup
from utils.format_utils import format_size
from utils.image_loader import load_image_as_qpixmap
from utils.video_thumbnail import get_video_thumbnail
from utils.platform_utils import open_file_with_default_app
from utils.logger import get_logger
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from ui.tools_definitions import TOOL_DUPLICATES_SIMILAR
from .base_dialog import BaseDialog
from .dialog_utils import show_file_details_dialog
from .image_preview_dialog import ImagePreviewDialog


class DuplicatesSimilarDialog(BaseDialog):
    """
    Diálogo para gestionar archivos similares (70-95% de similitud).
    
    IMPORTANTE: Este diálogo es para archivos SIMILARES, no idénticos.
    Para copias idénticas, usar el diálogo "Copias Visuales Idénticas".
    """
    
    DEFAULT_SENSITIVITY = 85
    
    def __init__(self, analysis: DuplicatesSimilarAnalysis, parent=None):
        super().__init__(parent)
        
        self.logger = get_logger('DuplicatesSimilarDialog')
        self.analysis = analysis
        self.repo = FileInfoRepositoryCache.get_instance()
        
        self.current_sensitivity = self.DEFAULT_SENSITIVITY
        self.current_result = None
        self.all_groups = []
        self.current_group_index = 0
        self.selections = {}
        self.accepted_plan = None
        self._is_loading = True
        self.keep_strategy = None  # Ninguna estrategia por defecto
        self.strategy_buttons = {}
        
        self._setup_ui()
        self._show_loading_state()
        
        # Cargar grupos DESPUÉS de que el diálogo sea visible
        QTimer.singleShot(100, self._initial_load)
    
    def _setup_ui(self):
        """Configura la interfaz del diálogo."""
        self.setWindowTitle(TOOL_DUPLICATES_SIMILAR.title)
        self.setModal(True)
        self.resize(1280, 900)
        self.setMinimumSize(1100, 750)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name=TOOL_DUPLICATES_SIMILAR.icon_name,
            title=TOOL_DUPLICATES_SIMILAR.title,
            description=TOOL_DUPLICATES_SIMILAR.short_description,
            metrics=[
                {'value': '-', 'label': 'Grupos', 'color': DesignSystem.COLOR_PRIMARY},
                {'value': '-', 'label': 'Similares', 'color': DesignSystem.COLOR_WARNING},
                {'value': '-', 'label': 'Recuperable', 'color': DesignSystem.COLOR_SUCCESS}
            ]
        )
        main_layout.addWidget(self.header_frame)
        
        # Contenedor principal
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setSpacing(DesignSystem.SPACE_16)
        content_layout.setContentsMargins(
            DesignSystem.SPACE_24, DesignSystem.SPACE_20,
            DesignSystem.SPACE_24, DesignSystem.SPACE_20
        )
        
        # Barra de sensibilidad
        self.sensitivity_bar = self._create_sensitivity_bar()
        content_layout.addWidget(self.sensitivity_bar)
        
        # Área de trabajo
        workspace_card = QFrame()
        workspace_card.setObjectName("workspace_card")
        workspace_card.setStyleSheet(f"""
            QFrame#workspace_card {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """)
        workspace_layout = QVBoxLayout(workspace_card)
        workspace_layout.setSpacing(0)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar de navegación
        self.workspace_toolbar = self._create_navigation_toolbar()
        workspace_layout.addWidget(self.workspace_toolbar)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"color: {DesignSystem.COLOR_BORDER_LIGHT};")
        workspace_layout.addWidget(separator)
        
        # Contenedor de grupos
        self.group_container = QWidget()
        self.group_layout = QVBoxLayout(self.group_container)
        self.group_layout.setContentsMargins(
            DesignSystem.SPACE_20, DesignSystem.SPACE_20,
            DesignSystem.SPACE_20, DesignSystem.SPACE_20
        )
        self.group_layout.setSpacing(DesignSystem.SPACE_16)
        
        workspace_layout.addWidget(self.group_container, stretch=1)
        content_layout.addWidget(workspace_card, stretch=1)
        
        main_layout.addWidget(content_wrapper, stretch=1)
        
        # Opciones de seguridad
        security_options = self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de eliminar",
            dry_run_label="Modo simulación"
        )
        content_layout.addWidget(security_options)
        
        # Botones
        button_box = self.make_ok_cancel_buttons(
            ok_text="Eliminar Seleccionados",
            ok_enabled=False,
            button_style='danger'
        )
        self.delete_btn: Optional[QPushButton] = button_box.button(QDialogButtonBox.StandardButton.Ok)
        content_layout.addWidget(button_box)

    def _create_sensitivity_bar(self) -> QFrame:
        """Crea la barra de control de sensibilidad con diseño unificado."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_16}px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(int(DesignSystem.SPACE_16))
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Título + Descripción en línea
        title_desc = QLabel("<b>Sensibilidad:</b> Ajusta lo parecidas que deben ser las imágenes para mostrarlas")
        title_desc.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            color: {DesignSystem.COLOR_TEXT};
        """)
        layout.addWidget(title_desc)
        
        layout.addStretch()
        
        # Contenedor del slider con labels
        slider_container = QHBoxLayout()
        slider_container.setSpacing(int(DesignSystem.SPACE_8))
        
        # Marcador baja
        low_label = QLabel("Baja")
        low_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        slider_container.addWidget(low_label)
        
        # Slider (70-95%)
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(70, 95)
        self.sensitivity_slider.setValue(self.current_sensitivity)
        self.sensitivity_slider.setFixedWidth(180)
        self.sensitivity_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sensitivity_slider.setToolTip(
            "Ajusta el umbral de simulitud de las imágenes.\n"
            "• 95%: Muy similares\n• 85%: Similar (recomendado)\n• 70%: Más tolerante"
        )
        self.sensitivity_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {DesignSystem.COLOR_BORDER};
                height: 6px;
                background: {DesignSystem.COLOR_BG_1};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border: 2px solid {DesignSystem.COLOR_SURFACE};
                width: 18px; height: 18px;
                margin: -7px 0;
                border-radius: 10px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QSlider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 3px;
            }}
        """)
        slider_container.addWidget(self.sensitivity_slider)
        
        # Marcador alta
        high_label = QLabel("Alta")
        high_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        slider_container.addWidget(high_label)
        
        # Valor actual
        self.sensitivity_value_label = QLabel(f"{self.current_sensitivity}%")
        self.sensitivity_value_label.setFixedWidth(45)
        self.sensitivity_value_label.setStyleSheet(f"""
            background-color: {DesignSystem.COLOR_PRIMARY};
            color: {DesignSystem.COLOR_PRIMARY_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
            border-radius: {DesignSystem.RADIUS_BASE}px;
        """)
        self.sensitivity_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slider_container.addWidget(self.sensitivity_value_label)
        
        layout.addLayout(slider_container)
        
        # Conexiones
        self.sensitivity_slider.valueChanged.connect(self._on_slider_changed)
        self.sensitivity_slider.sliderReleased.connect(self._on_slider_released)
        
        return frame
    
    def _create_strategy_buttons(self, parent_layout: QHBoxLayout):
        """Crea los botones de estrategia inline para la toolbar."""
        self.strategy_buttons = {}
        
        strategies = [
            ('keep_largest', 'arrow-expand-all', 'Mayor tamaño', 'Conservar archivo de mayor tamaño'),
            ('keep_highest_res', 'ruler', 'Mayor res.', 'Conservar archivo con mayor resolución'),
            ('keep_oldest', 'clock-outline', 'Más antigua', 'Conservar archivo más antiguo'),
        ]
        
        for strategy_id, icon_name, label, tooltip in strategies:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(False)  # Ninguno seleccionado por defecto
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            icon_manager.set_button_icon(btn, icon_name, size=16)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DesignSystem.COLOR_BG_1};
                    border: 1px solid {DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_BASE}px;
                    padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
                    font-size: {DesignSystem.FONT_SIZE_XS}px;
                    color: {DesignSystem.COLOR_TEXT};
                }}
                QPushButton:hover {{
                    border-color: {DesignSystem.COLOR_PRIMARY};
                    background-color: {DesignSystem.COLOR_SURFACE};
                }}
                QPushButton:checked {{
                    background-color: {DesignSystem.COLOR_PRIMARY};
                    border-color: {DesignSystem.COLOR_PRIMARY};
                    color: {DesignSystem.COLOR_PRIMARY_TEXT};
                }}
            """)
            btn.clicked.connect(lambda checked, s=strategy_id: self._on_strategy_changed(s))
            parent_layout.addWidget(btn)
            self.strategy_buttons[strategy_id] = btn
        
        # Separador antes del botón de selección masiva
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(20)
        sep.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        parent_layout.addWidget(sep)
        
        # Botón de selección masiva (estilo diferenciado - warning sutil)
        self.auto_select_all_btn = QPushButton("Auto")
        self.auto_select_all_btn.setToolTip(
            "Seleccionar automáticamente en TODOS los grupos.\n"
            "⚠️ Requiere confirmación - los archivos NO son idénticos."
        )
        self.auto_select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_manager.set_button_icon(self.auto_select_all_btn, 'delete-sweep', size=14)
        self.auto_select_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {DesignSystem.COLOR_WARNING};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_4}px {DesignSystem.SPACE_8}px;
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                color: {DesignSystem.COLOR_WARNING};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_WARNING};
                color: white;
            }}
        """)
        self.auto_select_all_btn.clicked.connect(self._on_auto_select_all_clicked)
        parent_layout.addWidget(self.auto_select_all_btn)
    
    def _on_strategy_changed(self, strategy_id: str):
        """Maneja el cambio de estrategia de conservación."""
        self.keep_strategy = strategy_id
        
        # Actualizar estado visual de botones
        for btn_id, btn in self.strategy_buttons.items():
            btn.setChecked(btn_id == strategy_id)
        
        # Aplicar estrategia al grupo actual
        self._apply_strategy(strategy_id)
    
    def _reset_strategy_buttons(self):
        """Resetea los botones de estrategia (ninguno seleccionado)."""
        self.keep_strategy = None
        for btn in self.strategy_buttons.values():
            btn.setChecked(False)
    
    def _on_auto_select_all_clicked(self):
        """Maneja el clic en el botón de selección automática masiva."""
        from PyQt6.QtWidgets import QMessageBox
        
        # Diálogo de confirmación
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Confirmar selección automática")
        msg.setText(
            "<b>¿Seleccionar automáticamente en todos los grupos?</b>"
        )
        msg.setInformativeText(
            "⚠️ <b>Atención:</b> Los archivos similares <i>no son idénticos</i>.\n\n"
            "Esta acción marcará para eliminación archivos que pueden tener "
            "diferencias visuales (recortes, ediciones, resoluciones distintas).\n\n"
            "Se recomienda revisar cada grupo individualmente."
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        # Estilo del diálogo
        msg.setStyleSheet(DesignSystem.get_stylesheet())
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self._apply_strategy_to_all_groups()

    def _create_navigation_toolbar(self) -> QWidget:
        """Crea la barra de navegación con estrategia y tip integrados."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_10,
            DesignSystem.SPACE_16, DesignSystem.SPACE_10
        )
        layout.setSpacing(DesignSystem.SPACE_12)
        
        # Navegación
        self.prev_btn = self.make_styled_button(icon_name='chevron-left', button_style='secondary', tooltip="Anterior")
        self.prev_btn.clicked.connect(self._previous_group)
        self.prev_btn.setEnabled(False)
        
        self.group_counter_label = QLabel("Cargando...")
        self.group_counter_label.setMinimumWidth(140)
        self.group_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.group_counter_label.setStyleSheet(f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT};")
        
        self.next_btn = self.make_styled_button(icon_name='chevron-right', button_style='secondary', tooltip="Siguiente")
        self.next_btn.clicked.connect(self._next_group)
        self.next_btn.setEnabled(False)
        
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(DesignSystem.SPACE_8)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.group_counter_label)
        nav_layout.addWidget(self.next_btn)
        
        layout.addLayout(nav_layout)
        
        # Separador visual
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        sep.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        layout.addWidget(sep)
        
        # Botones de estrategia inline
        strategy_label = QLabel("Conservar:")
        strategy_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(strategy_label)
        
        self._create_strategy_buttons(layout)
        
        layout.addStretch()
        
        # Tip de ayuda colapsable
        self.tip_btn = self.create_tip_button(
            "<b>Tip:</b> Esta herramienta detecta imágenes <i>similares</i> (recortes, ediciones). "
            "Para copias <i>idénticas</i> visualmente, usa \"Copias Visuales Idénticas\"."
        )
        layout.addWidget(self.tip_btn)
        
        # Contador de selección
        self.global_summary_label = QLabel("0 seleccionados")
        self.global_summary_label.setMinimumWidth(120)
        self.global_summary_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.global_summary_label.setStyleSheet(f"""
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; 
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        layout.addWidget(self.global_summary_label)
        
        return container

    # ================= LOADING STATE =================

    def _show_loading_state(self):
        """Muestra estado de carga con barra de progreso real.
        
        Usa QProgressBar con rango determinado para mostrar porcentaje real
        del proceso de clustering, manteniendo la UI responsiva mediante
        callbacks que llaman a processEvents().
        """
        for i in reversed(range(self.group_layout.count())):
            item = self.group_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)  # type: ignore[union-attr]
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        # Icono de búsqueda (estático, no animado)
        icon_label = icon_manager.create_icon_label(
            'image-search', size=48, color=DesignSystem.COLOR_PRIMARY
        )
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Mensaje principal (se actualiza dinámicamente)
        self.loading_label = QLabel("Preparando análisis...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            color: {DesignSystem.COLOR_TEXT};
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        layout.addWidget(self.loading_label)
        
        # Barra de progreso con porcentaje real
        total_files = len(self.analysis.perceptual_hashes)
        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, total_files)
        self.loading_progress.setValue(0)
        self.loading_progress.setFixedWidth(350)
        self.loading_progress.setFixedHeight(8)
        self.loading_progress.setTextVisible(False)
        self.loading_progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {DesignSystem.COLOR_BORDER_LIGHT};
            }}
            QProgressBar::chunk {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.loading_progress, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Porcentaje y contador
        self.loading_percent = QLabel("0%")
        self.loading_percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_percent.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_MD}px;
            color: {DesignSystem.COLOR_PRIMARY};
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        layout.addWidget(self.loading_percent)
        
        # Submensaje con detalle de la fase actual
        self.loading_submsg = QLabel(
            f"Sensibilidad: {self.current_sensitivity}% · {total_files:,} archivos"
        )
        self.loading_submsg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_submsg.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        layout.addWidget(self.loading_submsg)
        
        self.group_layout.addWidget(container)
        
        # Deshabilitar controles durante carga
        self.sensitivity_slider.setEnabled(False)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

    def _update_loading_progress(self, current: int, total: int, message: str) -> bool:
        """Callback para actualizar la barra de progreso durante el clustering.
        
        Args:
            current: Archivo actual siendo procesado
            total: Total de archivos
            message: Mensaje descriptivo de la fase actual
            
        Returns:
            True para continuar, False para cancelar (no implementado)
        """
        from PyQt6.QtWidgets import QApplication
        from PyQt6.sip import isdeleted
        
        # Verificar que los widgets existen antes de usarlos
        if (hasattr(self, 'loading_progress') and 
            self.loading_progress is not None and 
            not isdeleted(self.loading_progress)):
            self.loading_progress.setValue(current)
            
            # Actualizar porcentaje
            percent = (current / total * 100) if total > 0 else 0
            if (hasattr(self, 'loading_percent') and 
                self.loading_percent is not None and 
                not isdeleted(self.loading_percent)):
                self.loading_percent.setText(f"{percent:.0f}%")
            
            # Actualizar mensaje de fase
            if (hasattr(self, 'loading_label') and 
                self.loading_label is not None and 
                not isdeleted(self.loading_label)):
                self.loading_label.setText(message)
            
            # Procesar eventos para mantener UI responsiva
            QApplication.processEvents()
        
        return True  # Continuar procesando

    def _initial_load(self):
        """Carga inicial de grupos (llamada después de mostrar el diálogo)."""
        from PyQt6.QtWidgets import QApplication
        
        # Procesar eventos para asegurar que el diálogo está visible
        QApplication.processEvents()
        
        self._regenerate_groups()
        self._is_loading = False
        self.sensitivity_slider.setEnabled(True)

    # ================= LÓGICA =================

    def _on_slider_changed(self, value: int):
        """Actualiza el label mientras se mueve el slider."""
        self.current_sensitivity = value
        self.sensitivity_value_label.setText(f"{value}%")

    def _on_slider_released(self):
        """Regenera grupos cuando se suelta el slider."""
        if not self._is_loading:
            self._is_loading = True
            self._show_loading_state()
            # Pequeño delay para que la UI se actualice antes del procesamiento
            QTimer.singleShot(50, self._do_regenerate_groups)

    def _do_regenerate_groups(self):
        """Ejecuta la regeneración de grupos y restaura el estado de la UI.
        
        Wrapper que llama a _regenerate_groups y luego restaura el slider.
        """
        try:
            self._regenerate_groups()
        finally:
            # SIEMPRE restaurar el estado de la UI
            self._is_loading = False
            self.sensitivity_slider.setEnabled(True)

    def _regenerate_groups(self):
        """Regenera los grupos con la sensibilidad actual.
        
        Usa callback de progreso para mantener la UI responsiva
        y mostrar el avance real del clustering.
        """
        from PyQt6.QtWidgets import QApplication
        from PyQt6.sip import isdeleted
        
        self.logger.info(f"Regenerando grupos con sensibilidad {self.current_sensitivity}%...")
        
        # Actualizar info de sensibilidad (verificar que el widget existe)
        if (hasattr(self, 'loading_submsg') and 
            self.loading_submsg is not None and 
            not isdeleted(self.loading_submsg)):
            total_files = len(self.analysis.perceptual_hashes)
            self.loading_submsg.setText(
                f"Sensibilidad: {self.current_sensitivity}% · {total_files:,} archivos"
            )
            QApplication.processEvents()
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # Ejecutar clustering con callback de progreso
            result = self.analysis.get_groups(
                self.current_sensitivity,
                progress_callback=self._update_loading_progress
            )
            
            self.current_result = result
            self.all_groups = result.groups.copy()
            
            self.logger.info(f"Encontrados {len(self.all_groups)} grupos")
            
            self.selections.clear()
            self._update_header_metrics()
            
            if self.all_groups:
                self.current_group_index = 0
                self._load_group(0)
            else:
                self._show_no_groups_message()
                
        finally:
            QApplication.restoreOverrideCursor()

    def _update_header_metrics(self):
        """Actualiza las métricas del header."""
        total_groups = len(self.all_groups)
        total_similar = sum(len(g.files) - 1 for g in self.all_groups)
        space_potential = sum(
            (len(g.files) - 1) * (g.total_size // len(g.files))
            for g in self.all_groups if g.files
        )
        
        self._update_header_metric(self.header_frame, 'Grupos', str(total_groups))
        self._update_header_metric(self.header_frame, 'Similares', str(total_similar))
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(space_potential))

    def _show_no_groups_message(self):
        """Muestra mensaje cuando no hay grupos."""
        for i in reversed(range(self.group_layout.count())):
            item = self.group_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)  # type: ignore[union-attr]
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(DesignSystem.SPACE_16)
        
        icon_label = icon_manager.create_icon_label('check-circle', size=64, color=DesignSystem.COLOR_SUCCESS)
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        msg = QLabel(
            f"No se encontraron archivos similares\n"
            f"con sensibilidad {self.current_sensitivity}%\n\n"
            "Reduce la sensibilidad para detectar\n"
            "archivos con más diferencias."
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_MD}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
        layout.addWidget(msg)
        
        self.group_layout.addWidget(container)
        
        self.group_counter_label.setText("0 de 0")
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)

    def _load_group(self, index: int):
        """Carga y muestra un grupo específico."""
        if not 0 <= index < len(self.all_groups):
            return
        
        self.current_group_index = index
        group = self.all_groups[index]
        
        self.group_counter_label.setText(f"Grupo {index + 1} de {len(self.all_groups)}")
        self.prev_btn.setEnabled(len(self.all_groups) > 1)
        self.next_btn.setEnabled(len(self.all_groups) > 1)
        
        # Resetear botones de estrategia (ninguno seleccionado)
        self._reset_strategy_buttons()
        
        # Limpiar
        for i in reversed(range(self.group_layout.count())):
            item = self.group_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)  # type: ignore[union-attr]
        
        # Info de similitud
        sim_info = self._create_group_similarity_info(group)
        self.group_layout.addWidget(sim_info)
        
        # Grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(DesignSystem.SPACE_16)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        current_selection = self.selections.get(index, [])
        
        cols = 3
        # Determinar qué archivos se van a conservar (los NO seleccionados cuando hay selección)
        has_selection = len(current_selection) > 0
        for i, file_path in enumerate(group.files):
            is_selected = file_path in current_selection
            will_be_kept = has_selection and not is_selected
            card = self._create_file_card(file_path, is_selected, will_be_kept)
            grid_layout.addWidget(card, i // cols, i % cols)
        
        scroll.setWidget(grid_widget)
        self.group_layout.addWidget(scroll)

    def _create_group_similarity_info(self, group) -> QWidget:
        """Crea widget con info de similitud."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        score = group.similarity_score
        color = (
            DesignSystem.COLOR_SUCCESS if score >= 95 else
            DesignSystem.COLOR_PRIMARY if score >= 85 else
            DesignSystem.COLOR_WARNING
        )
        
        badge = QLabel(f"{score:.1f}% Similitud")
        badge.setStyleSheet(f"""
            background-color: {color}20; color: {color};
            border: 1px solid {color}40; border-radius: 12px;
            padding: 4px 12px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        layout.addWidget(badge)
        
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(score))
        progress.setFixedWidth(120)
        progress.setTextVisible(False)
        progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: {DesignSystem.COLOR_BORDER_LIGHT};
                border-radius: 2px; height: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {color}; border-radius: 2px;
            }}
        """)
        layout.addWidget(progress)
        
        files_info = QLabel(f"{len(group.files)} archivos · {format_size(group.total_size)}")
        files_info.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        layout.addWidget(files_info)
        
        layout.addStretch()
        return container

    def _create_file_card(self, file_path: Path, is_selected: bool, will_be_kept: bool = False) -> QFrame:
        """Crea tarjeta para un archivo."""
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mouseDoubleClickEvent = lambda e: show_file_details_dialog(file_path, self)  # type: ignore[assignment]
        card.setStyleSheet(self._get_card_style(is_selected, will_be_kept))
        
        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_8)
        layout.setContentsMargins(DesignSystem.SPACE_8, DesignSystem.SPACE_8, DesignSystem.SPACE_8, DesignSystem.SPACE_8)
        
        # Header
        header = QHBoxLayout()
        
        checkbox = QCheckBox("Eliminar")
        checkbox.setChecked(is_selected)
        checkbox.setStyleSheet(f"QCheckBox {{ color: {DesignSystem.COLOR_DANGER}; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; }}")
        checkbox.toggled.connect(lambda checked, f=file_path: self._toggle_selection(f, checked))
        header.addWidget(checkbox)
        
        header.addStretch()
        
        info_badge = self._create_info_badge(file_path)
        header.addWidget(info_badge)
        
        try:
            size_text = format_size(file_path.stat().st_size)
        except:
            size_text = "?"
        size_lbl = QLabel(size_text)
        size_lbl.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_XS}px;")
        header.addWidget(size_lbl)
        
        layout.addLayout(header)
        
        # Thumbnail
        thumb_lbl, is_video = self._create_thumbnail(file_path)
        if thumb_lbl:
            thumb_lbl.mousePressEvent = lambda e, f=file_path, v=is_video: self._handle_thumbnail_click(f, v)  # type: ignore[assignment]
            layout.addWidget(thumb_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Nombre
        name_lbl = QLabel(file_path.name)
        name_lbl.setWordWrap(True)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT};")
        layout.addWidget(name_lbl)
        
        # Fecha
        date_info = self._get_file_date_info(file_path)
        if date_info:
            date_lbl = QLabel(date_info)
            date_lbl.setWordWrap(True)
            date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            date_lbl.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_XS}px; color: {DesignSystem.COLOR_TEXT_SECONDARY};")
            layout.addWidget(date_lbl)
        
        card.setProperty("file_path", str(file_path))
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(lambda pos, f=file_path: self._show_context_menu(f))
        
        return card

    def _create_info_badge(self, file_path: Path) -> QLabel:
        """Crea badge de info."""
        badge = QLabel()
        info_icon = icon_manager.get_icon('information-outline', size=16, color=DesignSystem.COLOR_PRIMARY)
        badge.setPixmap(info_icon.pixmap(16, 16))
        badge.setFixedSize(20, 20)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(DesignSystem.get_info_badge_style())
        badge.setCursor(Qt.CursorShape.PointingHandCursor)
        badge.mousePressEvent = lambda e, f=file_path: show_file_details_dialog(f, self)  # type: ignore[assignment]
        return badge

    def _get_card_style(self, is_selected: bool, will_be_kept: bool = False) -> str:
        """Retorna el estilo de la tarjeta según su estado.
        
        - is_selected (rojo): archivo marcado para eliminación
        - will_be_kept (verde): archivo que se conservará (no seleccionado cuando hay selección en el grupo)
        - neutro (blanco): sin selección en el grupo
        """
        if is_selected:
            border_color = DesignSystem.COLOR_DANGER
            bg_color = DesignSystem.COLOR_DANGER_BG
            width = 2
        elif will_be_kept:
            border_color = DesignSystem.COLOR_SUCCESS
            bg_color = f"{DesignSystem.COLOR_SUCCESS}15"  # Verde muy suave
            width = 2
        else:
            border_color = DesignSystem.COLOR_BORDER
            bg_color = DesignSystem.COLOR_SURFACE
            width = 1
        
        return f"""
            QFrame {{
                background-color: {bg_color};
                border: {width}px solid {border_color};
                border-radius: {DesignSystem.RADIUS_MD}px;
            }}
            QFrame:hover {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}
        """

    def _toggle_selection(self, file_path: Path, checked: bool):
        """Toggle selección."""
        if self.current_group_index not in self.selections:
            self.selections[self.current_group_index] = []
        
        if checked and file_path not in self.selections[self.current_group_index]:
            self.selections[self.current_group_index].append(file_path)
        elif not checked and file_path in self.selections[self.current_group_index]:
            self.selections[self.current_group_index].remove(file_path)
        
        self._update_summary()
        
        # Refrescar TODAS las tarjetas del grupo para actualizar estados verde/rojo/blanco
        group = self.all_groups[self.current_group_index]
        for file in group.files:
            is_selected = file in self.selections[self.current_group_index]
            self._update_card_visual(file, is_selected)

    def _update_card_visual(self, file_path: Path, is_selected: bool):
        """Actualiza visual de tarjeta."""
        scroll_area: Optional[QScrollArea] = None
        for i in range(self.group_layout.count()):
            item = self.group_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QScrollArea):
                scroll_area = item.widget()  # type: ignore[assignment]
                break
        
        if not scroll_area or not scroll_area.widget():
            return
        
        inner_widget = scroll_area.widget()
        if not inner_widget:
            return
        grid_layout = inner_widget.layout()
        if not grid_layout:
            return
        
        # Determinar si hay selección en el grupo actual para calcular will_be_kept
        current_selection = self.selections.get(self.current_group_index, [])
        has_selection = len(current_selection) > 0
        will_be_kept = has_selection and not is_selected
        
        target = str(file_path)
        for i in range(grid_layout.count()):
            item = grid_layout.itemAt(i)
            card = item.widget() if item else None
            if card and card.property("file_path") == target:
                card.setStyleSheet(self._get_card_style(is_selected, will_be_kept))
                checkbox = card.findChild(QCheckBox)
                if checkbox:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(is_selected)
                    checkbox.blockSignals(False)
                break

    def _update_summary(self):
        """Actualiza resumen."""
        total_files = sum(len(l) for l in self.selections.values())
        total_bytes = sum(
            f.stat().st_size for files in self.selections.values() for f in files if f.exists()
        )
        
        self.global_summary_label.setText(f"{total_files} archivos seleccionados ({format_size(total_bytes)})")
        if self.delete_btn:
            self.delete_btn.setEnabled(total_files > 0)
            self.delete_btn.setText(f"Eliminar {total_files} Archivos")

    def _previous_group(self):
        if self.all_groups:
            self._load_group((self.current_group_index - 1) % len(self.all_groups))

    def _next_group(self):
        if self.all_groups:
            self._load_group((self.current_group_index + 1) % len(self.all_groups))

    def _apply_strategy(self, strategy: str):
        """Aplica estrategia al grupo actual."""
        if not self.all_groups:
            return
        
        group = self.all_groups[self.current_group_index]
        files = group.files
        if len(files) < 2:
            return
        
        if strategy == 'keep_largest':
            # Conservar el de mayor tamaño
            to_delete = self._get_files_to_delete_by_size(files, keep_largest=True)
        elif strategy == 'keep_highest_res':
            # Conservar el de mayor resolución
            to_delete = self._get_files_to_delete_by_resolution(files)
        elif strategy == 'keep_oldest':
            # Conservar el más antiguo
            to_delete = self._get_files_to_delete_by_date(files, keep_oldest=True)
        else:
            to_delete = []
        
        self.selections[self.current_group_index] = list(to_delete)
        self._load_group(self.current_group_index)
        self._update_summary()
    
    def _get_file_size(self, file_path: Path) -> int:
        """Obtiene el tamaño del archivo desde el repositorio o fallback."""
        if self.repo:
            meta = self.repo.get_file_metadata(file_path)
            if meta and meta.fs_size is not None:
                return meta.fs_size
        
        # Fallback: leer del filesystem directamente
        self.logger.warning(f"Tamaño no encontrado en caché, leyendo de filesystem: {file_path}")
        try:
            return file_path.stat().st_size if file_path.exists() else 0
        except Exception:
            return 0
    
    def _get_file_best_date(self, file_path: Path) -> float:
        """Obtiene la mejor fecha del archivo desde el repositorio o fallback."""
        if self.repo:
            best_date, _ = self.repo.get_best_date(file_path)
            if best_date:
                return best_date.timestamp()
        
        # Fallback: leer mtime del filesystem directamente
        self.logger.warning(f"Best_date no encontrada en caché, usando mtime: {file_path}")
        try:
            return file_path.stat().st_mtime if file_path.exists() else float('inf')
        except Exception:
            return float('inf')
    
    def _get_file_resolution(self, file_path: Path) -> int:
        """Obtiene la resolución del archivo desde el repositorio o fallback."""
        if self.repo:
            meta = self.repo.get_file_metadata(file_path)
            if meta and meta.exif_ImageWidth and meta.exif_ImageLength:
                return meta.exif_ImageWidth * meta.exif_ImageLength
        
        # Fallback: leer con PIL directamente
        self.logger.warning(f"Resolución no encontrada en caché, leyendo con PIL: {file_path}")
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                width, height = img.size
                return width * height
        except Exception:
            return 0
    
    def _get_files_to_delete_by_size(self, files: list, keep_largest: bool = True) -> list:
        """Determina qué archivos eliminar según tamaño."""
        sizes = [(f, self._get_file_size(f)) for f in files]
        sorted_files = sorted(sizes, key=lambda x: x[1], reverse=keep_largest)
        return [f for f, _ in sorted_files[1:]]
    
    def _get_files_to_delete_by_date(self, files: list, keep_oldest: bool = True) -> list:
        """Determina qué archivos eliminar según fecha."""
        dates = [(f, self._get_file_best_date(f)) for f in files]
        sorted_files = sorted(dates, key=lambda x: x[1], reverse=not keep_oldest)
        return [f for f, _ in sorted_files[1:]]
    
    def _get_files_to_delete_by_resolution(self, files: list) -> list:
        """Determina qué archivos eliminar conservando el de mayor resolución."""
        resolutions = [(f, self._get_file_resolution(f)) for f in files]
        sorted_files = sorted(resolutions, key=lambda x: x[1], reverse=True)
        return [f for f, _ in sorted_files[1:]]
    
    def _apply_strategy_to_all_groups(self):
        """Aplica la estrategia 'keep_largest' a todos los grupos."""
        for idx, group in enumerate(self.all_groups):
            files = group.files
            if len(files) < 2:
                continue
            
            # Usar estrategia de mayor tamaño por defecto para selección masiva
            to_delete = self._get_files_to_delete_by_size(files, keep_largest=True)
            self.selections[idx] = list(to_delete)
        
        # Recargar grupo actual y actualizar resumen
        self._load_group(self.current_group_index)
        self._update_summary()

    def _show_context_menu(self, file_path: Path):
        """Muestra menú contextual."""
        menu = QMenu(self)
        menu.setStyleSheet(DesignSystem.get_context_menu_style())
        
        action = menu.addAction(icon_manager.get_icon('information-outline'), "Ver detalles")
        if action:
            action.triggered.connect(lambda: show_file_details_dialog(file_path, self))
        
        menu.exec(QCursor.pos())

    def accept(self):
        """Construye plan de eliminación."""
        selected_groups = []
        total_files_to_delete = 0
        total_size_to_delete = 0
        
        for idx, files_to_delete in self.selections.items():
            if files_to_delete and idx < len(self.all_groups):
                og = self.all_groups[idx]
                group_size = sum(self._get_file_size(f) for f in files_to_delete)
                selected_groups.append(DuplicateGroup(
                    hash_value=og.hash_value,
                    files=files_to_delete,
                    total_size=group_size,
                    similarity_score=og.similarity_score
                ))
                total_files_to_delete += len(files_to_delete)
                total_size_to_delete += group_size
        
        # Validar que hay archivos seleccionados
        if not selected_groups:
            self.show_no_items_message("archivos similares seleccionados")
            return
        
        from services.result_types import DuplicateAnalysisResult
        self.accepted_plan = {
            'analysis': DuplicateAnalysisResult(
                groups=selected_groups,
                mode='perceptual',
                items_count=len(selected_groups),
                total_groups=len(selected_groups),
                space_wasted=total_size_to_delete
            ),
            'keep_strategy': 'manual',
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        super().accept()

    def _get_file_date_info(self, file_path: Path) -> str:
        """Obtiene info de fecha."""
        try:
            from utils.date_utils import select_best_date_from_file, get_all_metadata_from_file
            
            file_metadata = get_all_metadata_from_file(file_path)
            selected_date, source = select_best_date_from_file(file_metadata)
            
            if not selected_date:
                return ""
            
            date_str = selected_date.strftime('%Y-%m-%d %H:%M:%S')
            if source:
                source_short = 'EXIF' if 'EXIF' in source else 'Nombre' if 'Filename' in source else 'Mod.' if 'mtime' in source else source[:10]
            else:
                source_short = '?'
            return f"{date_str}\n({source_short})"
        except Exception:
            return ""

    def _create_thumbnail(self, file_path: Path):
        """Crea thumbnail."""
        try:
            from utils.file_utils import is_video_file
            is_video = is_video_file(str(file_path))
            
            if is_video:
                pixmap = get_video_thumbnail(file_path, max_size=(280, 280), frame_position=0.25)
                if pixmap and not pixmap.isNull():
                    pixmap = self._add_play_overlay(pixmap)
                else:
                    return None, True
            else:
                pixmap = load_image_as_qpixmap(file_path, max_size=(280, 280))
                if not pixmap or pixmap.isNull():
                    return None, False
            
            lbl = QLabel()
            lbl.setPixmap(pixmap)
            lbl.setFixedSize(280, 280)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"background-color: {DesignSystem.COLOR_BACKGROUND}; border-radius: 4px;")
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            
            return lbl, is_video
        except Exception as e:
            self.logger.debug(f"Error thumbnail: {e}")
            return None, False

    def _add_play_overlay(self, pixmap: QPixmap) -> QPixmap:
        """Agrega overlay de play."""
        result = QPixmap(pixmap.size())
        result.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(0, 0, pixmap)
        painter.fillRect(result.rect(), QColor(0, 0, 0, 60))
        
        play_icon = icon_manager.get_icon('play-circle', color=DesignSystem.COLOR_SURFACE)
        icon_pixmap = play_icon.pixmap(QSize(64, 64))
        x = (pixmap.width() - 64) // 2
        y = (pixmap.height() - 64) // 2
        painter.drawPixmap(x, y, icon_pixmap)
        painter.end()
        
        return result

    def _handle_thumbnail_click(self, file_path: Path, is_video: bool):
        """Maneja click en thumbnail."""
        if is_video:
            open_file_with_default_app(file_path)
        else:
            ImagePreviewDialog(file_path, self).exec()
