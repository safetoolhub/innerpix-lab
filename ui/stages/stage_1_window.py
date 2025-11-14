"""
Stage 1: Selector de carpeta y bienvenida.
Maneja la selección inicial de carpeta con validaciones y UI de bienvenida.
"""

from pathlib import Path
import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget,
    QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from .base_stage import BaseStage
from ui.styles.design_system import DesignSystem
from ui.widgets.dropzone_widget import DropzoneWidget
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from utils.icons import icon_manager
from config import Config


class Stage1Window(BaseStage):
    """
    Stage 1: Selector de carpeta y bienvenida.
    Proporciona la interfaz inicial para seleccionar la carpeta a analizar.
    """

    # Señales
    folder_selected = pyqtSignal(str)  # Emite cuando se selecciona una carpeta válida

    def __init__(self, main_window):
        super().__init__(main_window)

        # Referencias a widgets de la fase
        self.header = None
        self.folder_selection_card = None
        self.next_step_card = None
        self.last_folder_widget = None
        self.dropzone = None

        # Estado
        self.selected_folder = None
        self.last_folder = self.load_last_folder()

    def setup_ui(self) -> None:
        """Configura la interfaz de usuario del Stage 1."""
        self.logger.debug("Configurando UI del Stage 1")

        # Limpiar layout principal
        if self.main_layout:
            while self.main_layout.count():
                child = self.main_layout.takeAt(0)
                if child.widget():
                    child.widget().hide()
                    child.widget().setParent(None)

        # Crear widgets del estado
        self.header = self.create_header(
            title_text=f"Bienvenido a {Config.APP_NAME}",
            subtitle_text="Gestiona y optimiza tu colección de fotos y vídeos de manera segura",
            on_settings_clicked=self._on_settings_clicked,
            on_about_clicked=self._on_about_clicked
        )
        self.folder_selection_card = self._create_folder_selection_card()
        self.next_step_card = self._create_next_step_card()

        # Agregar al layout principal
        self.main_layout.addSpacing(DesignSystem.SPACE_8)
        self.main_layout.addWidget(self.header)
        self.main_layout.addSpacing(DesignSystem.SPACE_16)
        self.main_layout.addWidget(self.folder_selection_card)
        self.main_layout.addSpacing(DesignSystem.SPACE_20)
        self.main_layout.addWidget(self.next_step_card)
        self.main_layout.addStretch()

        self.logger.debug("UI del Estado 1 configurada")

    def cleanup(self) -> None:
        """Limpia los recursos del Estado 1."""
        self.logger.debug("Limpiando Estado 1")

        # Ocultar y desconectar widgets
        widgets_to_cleanup = [
            self.header,
            self.folder_selection_card,
            self.next_step_card,
            self.last_folder_widget
        ]

        for widget in widgets_to_cleanup:
            if widget:
                widget.hide()
                widget.setParent(None)

        # Limpiar referencias
        self.header = None
        self.folder_selection_card = None
        self.next_step_card = None
        self.last_folder_widget = None
        self.dropzone = None

    def _create_folder_selection_card(self) -> QFrame:
        """Crea la card principal para seleccionar carpeta"""
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_20}px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_16)

        # Header de la card
        header_title = QLabel("Paso 1: selecciona la carpeta con tus fotos")
        header_title.setProperty("class", "header")
        layout.addWidget(header_title)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        # Dropzone centrado
        dropzone_container = QHBoxLayout()
        dropzone_container.addStretch()

        self.dropzone = DropzoneWidget()
        self.dropzone.folder_dropped.connect(self._on_folder_selected)
        dropzone_container.addWidget(self.dropzone)

        dropzone_container.addStretch()
        layout.addLayout(dropzone_container)

        # Botón "Seleccionar carpeta..."
        btn_container = QHBoxLayout()
        btn_container.addStretch()

        btn_select = QPushButton("Seleccionar carpeta...")
        btn_select.setObjectName("primary-button")
        btn_select.setMinimumWidth(200)
        # Aplicar estilos directamente al botón
        btn_select.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: 10px 24px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        btn_select.clicked.connect(self._on_browse_folder)
        btn_container.addWidget(btn_select)

        btn_container.addStretch()
        layout.addLayout(btn_container)

        # Separador horizontal
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet(f"background-color: {DesignSystem.COLOR_BORDER};")
        separator2.setFixedHeight(1)
        layout.addWidget(separator2)

        # Consejos compactos centrados
        tips_container = QVBoxLayout()
        tips_container.setSpacing(0)  # Sin espacio entre tips
        tips_container.setContentsMargins(0, 0, 0, 0)

        tips_container.addWidget(self._create_centered_tip(
            "info",
            "Elige la carpeta donde tengas tus fotos y videos del iPhone, de WhatsApp, "
            "o cualquier colección que quieras organizar.",
            icon_color=DesignSystem.COLOR_PRIMARY,  # Azul para info
            icon_size=DesignSystem.ICON_SIZE_LG
        ))

        tips_container.addWidget(self._create_centered_tip(
            "security",
            "Pixaro Lab únicamente " \
            "analizará esa carpeta y todas sus subcarpetas. "
            "No se modificará nada hasta que tú lo autorices.",
            icon_color=DesignSystem.COLOR_ACCENT,  # Azul acento para resaltar
            icon_size=DesignSystem.ICON_SIZE_LG,
            text_color=DesignSystem.COLOR_ACCENT  # Azul acento para resaltar
        ))

        layout.addLayout(tips_container)

        # Línea de última carpeta (si existe)
        if self.last_folder:
            layout.addSpacing(DesignSystem.SPACE_16)
            self.last_folder_widget = self._create_last_folder_line()
            layout.addWidget(self.last_folder_widget)

        return card

    def _create_last_folder_line(self) -> QWidget:
        """Crea una línea con la última carpeta analizada y botón para reutilizarla"""
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(59, 130, 246, 0.08);
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px;
            }}
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_8)

        # Icono de carpeta reciente
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, 'history', color=DesignSystem.COLOR_PRIMARY, size=DesignSystem.ICON_SIZE_MD)
        layout.addWidget(icon_label)

        # Texto combinado en una sola línea
        # Mostrar ruta truncada si es muy larga
        folder_path = self.last_folder
        if len(folder_path) > 60:
            display_path = "..." + folder_path[-57:]
        else:
            display_path = folder_path

        combined_text = f"Última carpeta analizada: {display_path}"
        info_label = QLabel(combined_text)
        info_label.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        info_label.setToolTip(folder_path)
        layout.addWidget(info_label, 1)

        # Botón para usar esta carpeta
        use_btn = QPushButton("Usar esta carpeta")
        use_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: white;
                border: none;
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            }}
            QPushButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {DesignSystem.COLOR_PRIMARY};
            }}
        """)
        use_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        use_btn.clicked.connect(lambda: self._on_use_last_folder())
        layout.addWidget(use_btn)

        return container

    def _create_tip_box(self, icon_name: str, text: str, icon_color: str = None, icon_size: int = 14, text_color: str = None) -> QWidget:
        """Crea un tip compacto y profesional con icono y texto"""
        tip = QWidget()
        tip.setStyleSheet("QWidget { border: none; background: transparent; }")

        layout = QHBoxLayout(tip)
        layout.setContentsMargins(0, 0, 0, 0)  # Sin márgenes verticales
        layout.setSpacing(6)  # Espaciado compacto entre icono y texto

        # Usar color proporcionado o color secundario por defecto
        color = icon_color if icon_color else DesignSystem.COLOR_TEXT_SECONDARY

        # Icono
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, color=color, size=icon_size)
        icon_label.setStyleSheet("QLabel { border: none; background: transparent; }")
        layout.addWidget(icon_label)

        # Texto
        text_color_value = text_color if text_color else DesignSystem.COLOR_TEXT_SECONDARY
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {text_color_value};
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
            }}
        """)
        layout.addWidget(text_label, 1)  # Permite que el texto se expanda

        return tip

    def _create_centered_tip(self, icon_name: str, text: str, icon_color: str = None, icon_size: int = 14, text_color: str = None) -> QWidget:
        """Crea un tip centrado horizontalmente"""
        container = QWidget()
        container.setStyleSheet("QWidget { border: none; background: transparent; margin: 0px; padding: 0px; }")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(-2, -2, -2, -2)  # Márgenes negativos para compensar
        layout.setSpacing(0)

        # Espaciadores mínimos para centrado
        layout.addStretch(0)

        # Tip centrado
        tip = self._create_tip_box(icon_name, text, icon_color, icon_size, text_color)
        layout.addWidget(tip)

        # Espaciador derecho mínimo
        layout.addStretch(0)

        return container

    def _create_next_step_card(self) -> QFrame:
        """Crea la card "Paso 2" (vacía inicialmente)"""
        card = QFrame()
        card.setProperty("class", "card")
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_16}px;
                opacity: 0.5;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(DesignSystem.SPACE_12)

        # Header
        header_title = QLabel("Paso 2: elige qué quieres hacer")
        header_title.setProperty("class", "header")
        layout.addWidget(header_title)


        # Texto centrado
        empty_text = QLabel("Las herramientas aparecerán aquí después de analizar tu carpeta")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_text.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-style: italic;
            padding: {DesignSystem.SPACE_16}px 0;
        """)
        layout.addWidget(empty_text)

        return card

    # ==================== SLOTS ====================

    def _on_browse_folder(self):
        """Abre el diálogo de selección de carpeta"""
        folder = QFileDialog.getExistingDirectory(
            self.main_window,
            "Seleccionar carpeta con fotos",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self._on_folder_selected(folder)

    def _on_use_last_folder(self):
        """Usa la última carpeta analizada"""
        if self.last_folder and Path(self.last_folder).exists():
            self.logger.info(f"Usando última carpeta: {self.last_folder}")
            self._on_folder_selected(self.last_folder)
        else:
            self.logger.warning("La última carpeta ya no existe")
            QMessageBox.warning(
                self.main_window,
                "Carpeta no disponible",
                f"La última carpeta ya no existe:\n{self.last_folder}\n\n"
                "Por favor selecciona otra carpeta."
            )
            # Limpiar la última carpeta
            self.last_folder = None
            # TODO: Implementar settings_manager.remove cuando esté disponible en base_state

    def _on_folder_selected(self, folder_path: str):
        """Maneja cuando se selecciona una carpeta"""
        path = Path(folder_path)

        # Validación 1: La carpeta debe existir
        if not path.exists():
            self.logger.error(f"La carpeta no existe: {folder_path}")
            QMessageBox.critical(
                self.main_window,
                "Error - Carpeta no encontrada",
                f"La carpeta seleccionada no existe:\n\n{folder_path}\n\n"
                "Puede haber sido movida o eliminada."
            )
            return

        # Validación 2: Debe ser un directorio
        if not path.is_dir():
            self.logger.error(f"La ruta no es una carpeta: {folder_path}")
            QMessageBox.warning(
                self.main_window,
                "Selección inválida",
                "Por favor selecciona una carpeta, no un archivo individual."
            )
            return

        # Validación 3: Verificar permisos de lectura
        if not os.access(folder_path, os.R_OK):
            self.logger.error(f"Sin permisos de lectura: {folder_path}")
            QMessageBox.critical(
                self.main_window,
                "Error - Permisos insuficientes",
                f"No tienes permisos de lectura en esta carpeta:\n\n{folder_path}\n\n"
                "Por favor selecciona una carpeta donde tengas acceso de lectura."
            )
            return

        # Validación 4: Advertencia si la carpeta está vacía
        try:
            if not any(path.iterdir()):
                result = QMessageBox.question(
                    self.main_window,
                    "Carpeta vacía",
                    f"La carpeta seleccionada parece estar vacía:\n\n{folder_path}\n\n"
                    "¿Deseas continuar de todos modos?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if result == QMessageBox.StandardButton.No:
                    self.logger.info("Usuario canceló selección de carpeta vacía")
                    return
        except PermissionError:
            self.logger.warning(f"No se pudo verificar contenido de la carpeta: {folder_path}")
            # Continuar de todos modos
        except Exception as e:
            self.logger.error(f"Error verificando carpeta: {e}")
            # Continuar de todos modos

        self.selected_folder = str(path)
        self.logger.info(f"Carpeta seleccionada: {self.selected_folder}")

        # Guardar como última carpeta
        self.save_last_folder(self.selected_folder)

        self.folder_selected.emit(self.selected_folder)

        # Transición al ESTADO 2 a través de MainWindow
        self.main_window._transition_to_state_2(self.selected_folder)

    def _on_settings_clicked(self):
        """Abre el diálogo de configuración"""
        self.logger.info("Abriendo configuración")
        dialog = SettingsDialog(self.main_window)
        dialog.exec()

    def _on_about_clicked(self):
        """Abre el diálogo Acerca de"""
        self.logger.info("Abriendo Acerca de")
        dialog = AboutDialog(self.main_window)
        dialog.exec()