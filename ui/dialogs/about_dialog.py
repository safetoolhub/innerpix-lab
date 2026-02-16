"""
Diálogo 'Acerca de' con Tutorial integrado para InnerPix Lab.

Este módulo implementa un diálogo informativo profesional que sirve como:
- Información de la aplicación (versión, créditos)
- Tutorial de funcionalidades
- Guía de privacidad y seguridad
- Referencia de herramientas disponibles

El diseño utiliza pestañas laterales para organizar el contenido en secciones
navegables, con cards informativas y estilos consistentes del DesignSystem.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QWidget, QTabWidget, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt
from config import Config
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from ui.tools_definitions import (
    TOOL_CATEGORIES, get_tools_by_category
)


class AboutDialog(QDialog):
    """Diálogo 'Acerca de' con tutorial integrado y diseño profesional.
    
    Implementa un sistema de navegación por pestañas laterales con:
    - Bienvenida y visión general
    - Privacidad y seguridad
    - Herramientas (8 tools en categorías)
    - Información técnica
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._init_ui()

    def _init_ui(self):
        """Inicializa la interfaz del diálogo."""
        self.setWindowTitle(f"Acerca de {Config.APP_NAME}")
        self.setModal(True)
        self.setMinimumSize(1100, 780)
        self.resize(1100, 780)
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())

        # Layout principal sin márgenes
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === HEADER ===
        main_layout.addWidget(self._create_header())

        # === CONTENIDO CON TABS ===
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Tab widget con pestañas laterales compactas
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.West)
        self.tab_widget.setStyleSheet(DesignSystem.get_tutorial_tab_widget_style())
        
        # Crear las pestañas (nombres compactos)
        self.tab_widget.addTab(self._create_welcome_tab(), "Inicio")
        self.tab_widget.addTab(self._create_tools_tab(), "Herramientas")
        self.tab_widget.addTab(self._create_privacy_tab(), "Seguridad")
        self.tab_widget.addTab(self._create_tech_tab(), "Info")

        content_layout.addWidget(self.tab_widget)
        main_layout.addWidget(content_widget, 1)

        # === FOOTER ===
        main_layout.addWidget(self._create_footer())

    def _create_header(self) -> QFrame:
        """Crea el header con gradiente y logo."""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {DesignSystem.COLOR_PRIMARY}, stop:1 {DesignSystem.COLOR_PRIMARY_HOVER});
            }}
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 12, 24, 12)
        
        # Lado izquierdo: Título y versión
        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)
        
        title = QLabel(Config.APP_NAME)
        title.setStyleSheet(f"""
            color: white;
            font-size: {DesignSystem.FONT_SIZE_XL}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        left_layout.addWidget(title)
        
        version = QLabel(f"Versión {Config.APP_VERSION}")
        version.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.9);
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        left_layout.addWidget(version)
        
        header_layout.addLayout(left_layout)
        header_layout.addStretch()
        
        # Lado derecho: Badge de privacidad
        privacy_badge = QLabel("100% Privado • Sin conexión a internet")
        privacy_badge.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_16}px;
                border-radius: {DesignSystem.RADIUS_FULL}px;
            }}
        """)
        header_layout.addWidget(privacy_badge)
        
        return header

    def _create_footer(self) -> QFrame:
        """Crea el footer con botón de cerrar."""
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border-top: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """)
        
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 10, 24, 10)
        
        # Créditos
        credits = QLabel("Desarrollado para simplificar la gestión de fotos")
        credits.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        footer_layout.addWidget(credits)
        
        footer_layout.addStretch()
        
        # Botón cerrar
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(close_btn)
        
        return footer

    def _create_scroll_content(self, content_widget: QWidget) -> QScrollArea:
        """Crea un ScrollArea con el contenido proporcionado."""
        scroll = QScrollArea()
        scroll.setStyleSheet(DesignSystem.get_tutorial_scroll_area_style())
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content_widget)
        return scroll

    # ==================== PESTAÑAS DE CONTENIDO ====================

    def _create_welcome_tab(self) -> QWidget:
        """Crea la pestaña de bienvenida (compacta)."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_16, DesignSystem.SPACE_24, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        # Título + descripción en la misma sección
        welcome_title = QLabel("Bienvenido a InnerPix Lab")
        welcome_title.setStyleSheet(DesignSystem.get_tutorial_section_header_style())
        layout.addWidget(welcome_title)
        
        description = QLabel(
            "Suite de herramientas para gestionar, optimizar y organizar tus fotos y vídeos. "
            "<b>Privacidad absoluta</b>: todo el procesamiento es 100% local en tu computadora."
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_BASE}px;")
        layout.addWidget(description)
        
        # Flujo en lista vertical (4 pasos secuenciales)
        workflow_title = QLabel("Proceso de trabajo (Pasos a seguir en orden)")
        workflow_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_MD}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_PRIMARY};
            margin-top: {DesignSystem.SPACE_8}px;
        """)
        layout.addWidget(workflow_title)

        workflow_desc = QLabel(
            "InnerPix Lab está diseñado para seguir un flujo lógico y optimizar tu colección de manera progresiva. "
            "Sigue estos 4 pasos para obtener el mejor resultado:"
        )
        workflow_desc.setWordWrap(True)
        workflow_desc.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px; margin-bottom: {DesignSystem.SPACE_4}px;")
        layout.addWidget(workflow_desc)
        
        steps_container = QVBoxLayout()
        steps_container.setSpacing(DesignSystem.SPACE_8)
        
        steps = [
            ("1", "Selección de carpeta", "El primer paso es elegir la carpeta que contiene tus fotos y vídeos. El sistema trabajará de forma recursiva."),
            ("2", "Análisis", "Automáticamente escaneamos archivos, extraemos metadatos EXIF y calculamos firmas digitales (hashes)."),
            ("3", "Selección de Herramienta", "Entra en cada herramienta para detectar duplicados, organizar por fechas o limpiar archivos innecesarios."),
            ("4", "Ejecución de Cambios", "Tras revisar los planes de acción propuestos, confirma la ejecución. Recomendamos usar el Modo Simulación primero."),
        ]
        
        for num, title, desc in steps:
            step_widget = self._create_step_widget_compact(num, title, desc)
            steps_container.addWidget(step_widget)
        
        layout.addLayout(steps_container)
        
        # Tips en horizontal
        tips_layout = QHBoxLayout()
        tips_layout.setSpacing(DesignSystem.SPACE_8)
        
        tip1 = self._create_mini_tip("Modo Simulación", "Prueba sin modificar archivos")
        tip2 = self._create_mini_tip("Backup Disponible", "Copia de seguridad de ficheros eliminados")
        tip3 = self._create_mini_tip("Logs Detallados", "Registro de todas las operaciones")
        
        tips_layout.addWidget(tip1)
        tips_layout.addWidget(tip2)
        tips_layout.addWidget(tip3)
        
        layout.addLayout(tips_layout)
        layout.addStretch()
        
        return self._create_scroll_content(container)

    def _create_privacy_tab(self) -> QWidget:
        """Crea la pestaña de privacidad y seguridad con un diseño elegante."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_16, DesignSystem.SPACE_24, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        # === HERO SECTION: PRIVACIDAD TOTAL ===
        hero_frame = QFrame()
        hero_frame.setStyleSheet(DesignSystem.get_privacy_hero_style())
        hero_layout = QVBoxLayout(hero_frame)
        hero_layout.setSpacing(DesignSystem.SPACE_4)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        shield_icon = QLabel()
        icon_manager.set_label_icon(shield_icon, "shield", color=DesignSystem.COLOR_SUCCESS, size=32)
        hero_layout.addWidget(shield_icon, 0, Qt.AlignmentFlag.AlignCenter)
        
        hero_title = QLabel("Privacidad Absoluta")
        hero_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        hero_layout.addWidget(hero_title, 0, Qt.AlignmentFlag.AlignCenter)
        
        hero_subtitle = QLabel("Tus archivos nunca salen de tu computadora")
        hero_subtitle.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        hero_layout.addWidget(hero_subtitle, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(hero_frame)
        
        # === LISTA DE GARANTÍAS ===
        guarantees_container = QWidget()
        guarantees_layout = QVBoxLayout(guarantees_container)
        guarantees_layout.setContentsMargins(DesignSystem.SPACE_8, 0, DesignSystem.SPACE_8, 0)
        guarantees_layout.setSpacing(DesignSystem.SPACE_8)
        
        guarantees = [
            ("wifi-off", "100% Offline", 
             "InnerPix Lab funciona completamente sin conexión a internet. "
             "No enviamos estadísticas, telemetría ni datos de tus archivos a ningún servidor."),
            ("eye-off", "Sin Rastreo", 
             "No utilizamos bases de datos externas ni servicios en la nube. "
             "Todo el procesamiento de imágenes y vídeos es puramente local."),
            ("backup-restore", "Seguridad de Archivos", 
             "Protegemos tus datos con un robusto sistema de copias de seguridad. "
             "Antes de cada operación destructiva, creas un backup para tu tranquilidad.")
        ]
        
        for icon, title, desc in guarantees:
            item_frame = QFrame()
            item_frame.setStyleSheet(DesignSystem.get_privacy_item_style())
            item_layout = QHBoxLayout(item_frame)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(DesignSystem.SPACE_16)
            
            icon_lbl = QLabel()
            icon_manager.set_label_icon(icon_lbl, icon, color=DesignSystem.COLOR_PRIMARY, size=24)
            item_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignTop)
            
            text_layout = QVBoxLayout()
            text_layout.setSpacing(DesignSystem.SPACE_4)
            
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
            text_layout.addWidget(title_lbl)
            
            desc_lbl = QLabel(desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
            text_layout.addWidget(desc_lbl)
            
            item_layout.addLayout(text_layout, 1)
            guarantees_layout.addWidget(item_frame)
        
        layout.addWidget(guarantees_container)
        
        # === FOOTER DE CONFIANZA ===
        trust_footer = QLabel("Todo tu contenido está a salvo y bajo tu control exclusivo.")
        trust_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trust_footer.setStyleSheet(f"""
            color: {DesignSystem.COLOR_SUCCESS};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            padding-top: {DesignSystem.SPACE_8}px;
        """)
        layout.addWidget(trust_footer)
        
        layout.addStretch()
        return self._create_scroll_content(container)

    def _create_tools_tab(self) -> QWidget:
        """Crea la pestaña de herramientas (8 tools organizadas)."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_16, DesignSystem.SPACE_24, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        title = QLabel("Herramientas Disponibles")
        title.setStyleSheet(DesignSystem.get_tutorial_section_header_style())
        layout.addWidget(title)
        
        # Crear secciones dinámicamente usando tools_definitions
        for category in TOOL_CATEGORIES:
            # Header de la categoría
            header = self._create_category_header(category.title, category.description)
            layout.addWidget(header)
            
            # Grid de herramientas
            tools = get_tools_by_category(category.id)
            grid = QGridLayout()
            grid.setSpacing(DesignSystem.SPACE_8)
            
            # Determinar layout: 2 columnas para categorías con 4+ tools, 1 fila para categorías con 2
            if len(tools) > 2:
                # Grid 2x2 (ej: Limpieza con 4 tools)
                for i, tool in enumerate(tools):
                    row, col = i // 2, i % 2
                    card = self._create_tool_mini_card(tool.icon_name, tool.title, tool.long_description)
                    grid.addWidget(card, row, col)
            else:
                # Una fila horizontal (ej: Visual y Organización con 2 tools)
                for i, tool in enumerate(tools):
                    card = self._create_tool_mini_card(tool.icon_name, tool.title, tool.long_description)
                    grid.addWidget(card, 0, i)
            
            layout.addLayout(grid)
        

        
        layout.addStretch()
        return self._create_scroll_content(container)

    def _create_tech_tab(self) -> QWidget:
        """Crea la pestaña de información técnica (compacta)."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_16, DesignSystem.SPACE_24, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        title = QLabel("Información Técnica")
        title.setStyleSheet(DesignSystem.get_tutorial_section_header_style())
        layout.addWidget(title)
        
        # Info en grid horizontal
        info_grid = QGridLayout()
        info_grid.setSpacing(DesignSystem.SPACE_8)
        
        # Card 1: App Info
        app_card = self._create_info_card("Aplicación", [
            ("Nombre", Config.APP_NAME),
            ("Versión", Config.APP_VERSION),
            ("Tecnología", "PyQt6 • Python 3.x"),
            ("Plataformas", "Windows • macOS • Linux"),
        ])
        info_grid.addWidget(app_card, 0, 0)
        
        # Card 2: Formatos
        formats_card = self._create_formats_card()
        info_grid.addWidget(formats_card, 0, 1)
        
        layout.addLayout(info_grid)
        
       
        layout.addStretch()
        return self._create_scroll_content(container)

    # ==================== WIDGETS AUXILIARES COMPACTOS ====================

    def _create_step_widget_compact(self, number: str, title: str, description: str) -> QFrame:
        """Crea un widget de paso numerado compacto."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_tutorial_step_card_style())
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 10, 12, 10)
        
        # Número circular pequeño
        num_label = QLabel(number)
        num_label.setFixedSize(24, 24)
        num_label.setStyleSheet(DesignSystem.get_tutorial_step_number_style())
        layout.addWidget(num_label)
        
        # Contenido
        content = QVBoxLayout()
        content.setSpacing(DesignSystem.SPACE_2)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        content.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        content.addWidget(desc_label)
        
        layout.addLayout(content, 1)
        return frame

    def _create_mini_tip(self, title: str, desc: str) -> QFrame:
        """Crea un mini tip horizontal."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_tutorial_tip_card_style())
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        
        header = QLabel(title)
        header.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        layout.addWidget(header)
        
        desc_label = QLabel(desc)
        desc_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        return frame

    def _create_feature_card_compact(self, icon_name: str, title: str, description: str, 
                                     accent_color: str) -> QFrame:
        """Crea una card de feature compacta."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_tutorial_feature_card_accent_style(accent_color))
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_4)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12)
        
        # Header con icono
        header = QHBoxLayout()
        header.setSpacing(8)
        
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, color=accent_color, size=20)
        header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        header.addWidget(title_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        return frame

    def _create_category_header(self, title: str, subtitle: str) -> QWidget:
        """Crea un header de categoría de herramientas."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, DesignSystem.SPACE_4, 0, DesignSystem.SPACE_4)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        layout.addWidget(title_label)
        
        subtitle_label = QLabel(f"— {subtitle}")
        subtitle_label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        layout.addWidget(subtitle_label)
        layout.addStretch()
        
        return widget

    def _create_tool_mini_card(self, icon_name: str, title: str, description: str) -> QFrame:
        """Crea una mini card de herramienta."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_tutorial_tool_card_style())
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_8)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12)
        
        # Icono
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, color=DesignSystem.COLOR_PRIMARY, size=22)
        layout.addWidget(icon_label)
        
        # Contenido
        content = QVBoxLayout()
        content.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        content.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        desc_label.setWordWrap(True)
        content.addWidget(desc_label)
        
        layout.addLayout(content, 1)
        return frame

    def _create_info_card(self, title: str, items: list) -> QFrame:
        """Crea una card de información con items."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_tutorial_static_info_card_style())
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_4)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        layout.addWidget(title_label)
        
        for label, value in items:
            row = QHBoxLayout()
            row.setSpacing(8)
            
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
            row.addWidget(lbl)
            
            val = QLabel(value)
            val.setStyleSheet(f"""
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            """)
            row.addWidget(val)
            row.addStretch()
            
            layout.addLayout(row)
        
        return frame

    def _create_formats_card(self) -> QFrame:
        """Crea la card de formatos soportados."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_tutorial_static_info_card_style())
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_4)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12, DesignSystem.SPACE_12)
        
        title_label = QLabel("Formatos Soportados")
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        layout.addWidget(title_label)
        
        formats = [
            ("image", "Imágenes", "JPG, PNG, HEIC, WEBP, GIF, BMP, TIFF"),
            ("video", "Vídeos", "MP4, MOV, AVI, MKV, WEBM, M4V"),
        ]
        
        for icon_name, fmt_title, fmt_list in formats:
            row = QHBoxLayout()
            row.setSpacing(8)
            
            icon_label = QLabel()
            icon_manager.set_label_icon(icon_label, icon_name, color=DesignSystem.COLOR_PRIMARY, size=16)
            row.addWidget(icon_label)
            
            text = QLabel(f"<b>{fmt_title}:</b> {fmt_list}")
            text.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
            text.setWordWrap(True)
            row.addWidget(text, 1)
            
            layout.addLayout(row)
        
        return frame

    def _create_highlight_box(self, title: str, content: str, 
                              bg_color: str, border_color: str) -> QFrame:
        """Crea una caja destacada con título y contenido."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_tutorial_highlight_box_style(bg_color, border_color))
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(6)
        layout.setContentsMargins(14, 10, 14, 10)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        layout.addWidget(title_label)
        
        content_label = QLabel(content)
        content_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        content_label.setWordWrap(True)
        layout.addWidget(content_label)
        
        return frame
