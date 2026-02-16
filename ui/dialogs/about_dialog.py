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
    QFrame, QWidget, QTabWidget, QScrollArea, QGridLayout,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from config import Config
from ui.styles.design_system import DesignSystem
from ui.styles.icons import icon_manager
from ui.tools_definitions import (
    TOOL_CATEGORIES, get_tools_by_category
)

# Colores sutiles por categoría de herramientas
_CATEGORY_COLORS = {
    'cleanup': {
        'bg': 'rgba(13, 110, 253, 0.04)',
        'border': 'rgba(13, 110, 253, 0.12)',
        'accent': '#0D6EFD',
        'icon': '#0D6EFD',
    },
    'visual': {
        'bg': 'rgba(111, 66, 193, 0.04)',
        'border': 'rgba(111, 66, 193, 0.12)',
        'accent': '#6F42C1',
        'icon': '#6F42C1',
    },
    'organization': {
        'bg': 'rgba(25, 135, 84, 0.04)',
        'border': 'rgba(25, 135, 84, 0.12)',
        'accent': '#198754',
        'icon': '#198754',
    },
}


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
        self.tab_widget.addTab(self._create_privacy_tab(), "Privacidad")
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
        title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        left_layout.addWidget(title)
        
        version = QLabel(f"Versión {Config.APP_VERSION}")
        version.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.9);
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        version.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
        privacy_badge.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
        credits.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
        welcome_title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(welcome_title)
        
        description = QLabel(
            "Suite de herramientas para gestionar, optimizar y organizar tus fotos y vídeos. "
            "<b>Privacidad absoluta</b>: todo el procesamiento es 100% local en tu computadora."
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_BASE}px;")
        description.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(description)
        
        # Flujo en lista vertical (4 pasos secuenciales)
        workflow_title = QLabel("Proceso de trabajo (Pasos a seguir en orden)")
        workflow_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_MD}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_PRIMARY};
            margin-top: {DesignSystem.SPACE_8}px;
        """)
        workflow_title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(workflow_title)

        workflow_desc = QLabel(
            "InnerPix Lab está diseñado para seguir un flujo lógico y optimizar tu colección de manera progresiva. "
            "Sigue estos 4 pasos para obtener el mejor resultado:"
        )
        workflow_desc.setWordWrap(True)
        workflow_desc.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px; margin-bottom: {DesignSystem.SPACE_4}px;")
        workflow_desc.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
        hero_title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        hero_layout.addWidget(hero_title, 0, Qt.AlignmentFlag.AlignCenter)
        
        hero_subtitle = QLabel("Tus archivos nunca salen de tu computadora")
        hero_subtitle.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        hero_subtitle.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
            title_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            text_layout.addWidget(title_lbl)
            
            desc_lbl = QLabel(desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
            desc_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
        trust_footer.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(trust_footer)
        
        layout.addStretch()
        return self._create_scroll_content(container)

    def _create_tools_tab(self) -> QWidget:
        """Crea la pestaña de herramientas (8 tools organizadas por categoría con colores)."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_16, DesignSystem.SPACE_24, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_12)
        
        title = QLabel("Herramientas Disponibles")
        title.setStyleSheet(DesignSystem.get_tutorial_section_header_style())
        title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title)
        
        # Crear secciones dinámicamente usando tools_definitions
        for category in TOOL_CATEGORIES:
            colors = _CATEGORY_COLORS.get(category.id, _CATEGORY_COLORS['cleanup'])
            
            # Header de la categoría con acento de color
            header = self._create_category_header(category.title, category.description, colors['accent'])
            layout.addWidget(header)
            
            # Grid de herramientas (2 columnas alineadas)
            tools = get_tools_by_category(category.id)
            grid = QGridLayout()
            grid.setSpacing(DesignSystem.SPACE_12)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)
            
            for i, tool in enumerate(tools):
                row, col = i // 2, i % 2
                card = self._create_tool_mini_card(
                    tool.icon_name, tool.title, tool.long_description,
                    colors['bg'], colors['border'], colors['icon']
                )
                grid.addWidget(card, row, col)
            
            # Si hay un número impar de herramientas, añadir spacer en la última celda
            if len(tools) % 2 != 0:
                spacer = QWidget()
                spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                grid.addWidget(spacer, len(tools) // 2, 1)
            
            layout.addLayout(grid)

        layout.addStretch()
        return self._create_scroll_content(container)

    # ==================== WIDGETS AUXILIARES ====================

    def _create_category_header(self, title: str, subtitle: str, accent_color: str) -> QFrame:
        """Crea un header de categoría de herramientas con acento de color."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_about_category_header_style(accent_color))
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_2)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {accent_color};
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title_label)
        
        subtitle_label = QLabel(f"— {subtitle}")
        subtitle_label.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        subtitle_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(subtitle_label)
        layout.addStretch()
        
        return frame

    def _create_tool_mini_card(self, icon_name: str, title: str, description: str,
                                bg_color: str, border_color: str, icon_color: str) -> QFrame:
        """Crea una mini card de herramienta con color de categoría."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_about_tool_card_category_style(bg_color, border_color))
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_12)
        layout.setContentsMargins(DesignSystem.SPACE_16, DesignSystem.SPACE_12, DesignSystem.SPACE_16, DesignSystem.SPACE_12)
        
        # Icono
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, color=icon_color, size=24)
        icon_label.setFixedSize(28, 28)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        
        # Contenido
        content = QVBoxLayout()
        content.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        content.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        desc_label.setWordWrap(True)
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        content.addWidget(desc_label)
        
        layout.addLayout(content, 1)
        return frame

    def _create_tech_tab(self) -> QWidget:
        """Crea la pestaña de información técnica con sección de desarrollador impactante."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_16, DesignSystem.SPACE_24, DesignSystem.SPACE_16)
        layout.setSpacing(DesignSystem.SPACE_20)
        
        # === HEADER SECTION ===
        header_layout = QVBoxLayout()
        header_layout.setSpacing(DesignSystem.SPACE_4)
        
        title = QLabel("Información del Sistema")
        title.setStyleSheet(DesignSystem.get_tutorial_section_header_style())
        title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Detalles técnicos y créditos de la aplicación.")
        subtitle.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
        subtitle.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        header_layout.addWidget(subtitle)
        
        layout.addLayout(header_layout)
        
        # === DEVELOPER HERO SECTION ===
        dev_hero = self._create_developer_hero()
        layout.addWidget(dev_hero)

        # === TECH INFO GRID ===
        info_grid = QGridLayout()
        info_grid.setSpacing(DesignSystem.SPACE_12)
        
        # Card 1: App Info
        app_card = self._create_info_card("Aplicación", [
            ("Nombre", Config.APP_NAME),
            ("Versión", Config.APP_VERSION),
            ("Plataformas", "Windows • Linux • macOS"),
        ])
        info_grid.addWidget(app_card, 0, 0)
        
        # Card 2: Environment
        env_card = self._create_info_card("Tecnología", [
            ("Lenguaje", "Python 3.x"),
            ("Interfaz", "PyQt6"),
            ("Arquitectura", "Modular / Local-First"),
        ])
        info_grid.addWidget(env_card, 0, 1)

        layout.addLayout(info_grid)
        
        # === FORMATS SECTION ===
        formats_card = self._create_formats_card()
        layout.addWidget(formats_card)
        
        layout.addStretch()
        return self._create_scroll_content(container)

    # ==================== SECCIÓN HERO DEL DESARROLLADOR ====================

    def _create_developer_hero(self) -> QFrame:
        """Crea la sección hero del desarrollador con diseño impactante."""
        outer_frame = QFrame()
        outer_frame.setStyleSheet(DesignSystem.get_about_developer_hero_style())
        
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setSpacing(DesignSystem.SPACE_12)
        outer_layout.setContentsMargins(
            DesignSystem.SPACE_32, DesignSystem.SPACE_24,
            DesignSystem.SPACE_32, DesignSystem.SPACE_24
        )
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icono de escudo
        shield_icon = QLabel()
        icon_manager.set_label_icon(shield_icon, "shield", color="#FFFFFF", size=36)
        outer_layout.addWidget(shield_icon, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Nombre de la organización
        org_name = QLabel("safetoolhub.org")
        org_name.setStyleSheet(f"""
            color: white;
            font-size: {DesignSystem.FONT_SIZE_XL}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        org_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        org_name.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        outer_layout.addWidget(org_name)
        
        # Subtítulo / tagline
        tagline = QLabel("Software 100% privado, gratuito y sin rastreo")
        tagline.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.85);
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """)
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        outer_layout.addWidget(tagline)
        
        # Separador sutil
        sep_line = QFrame()
        sep_line.setFixedHeight(1)
        sep_line.setStyleSheet("background-color: rgba(255, 255, 255, 0.2);")
        outer_layout.addWidget(sep_line)
        
        # Tres badges de valores en horizontal
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(DesignSystem.SPACE_12)
        badges_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        badge_items = [
            ("wifi-off", "100% Offline"),
            ("eye-off", "Sin Rastreo"),
            ("shield", "Código Abierto"),
        ]
        
        for icon_name, text in badge_items:
            badge = self._create_hero_badge(icon_name, text)
            badges_layout.addWidget(badge)
        
        outer_layout.addLayout(badges_layout)
        
        return outer_frame

    def _create_hero_badge(self, icon_name: str, text: str) -> QWidget:
        """Crea un badge dentro del hero del desarrollador."""
        widget = QWidget()
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(255, 255, 255, 0.15);
                border-radius: {DesignSystem.RADIUS_FULL}px;
            }}
        """)
        
        layout = QHBoxLayout(widget)
        layout.setSpacing(DesignSystem.SPACE_6)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_6, DesignSystem.SPACE_12, DesignSystem.SPACE_6)
        
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, color="rgba(255,255,255,0.9)", size=14)
        layout.addWidget(icon_label)
        
        text_label = QLabel(text)
        text_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.9);
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        """)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(text_label)
        
        return widget

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
        num_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(num_label)
        
        # Contenido
        content = QVBoxLayout()
        content.setSpacing(DesignSystem.SPACE_2)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        content.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
        header.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(header)
        
        desc_label = QLabel(desc)
        desc_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        desc_label.setWordWrap(True)
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        header.addWidget(title_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        desc_label.setWordWrap(True)
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(desc_label)
        
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
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title_label)
        
        for label, value in items:
            row = QHBoxLayout()
            row.setSpacing(8)
            
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px;")
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            row.addWidget(lbl)
            
            val = QLabel(value)
            val.setStyleSheet(f"""
                color: {DesignSystem.COLOR_TEXT};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            """)
            val.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
            text.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
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
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title_label)
        
        content_label = QLabel(content)
        content_label.setStyleSheet(DesignSystem.get_tutorial_card_desc_style())
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(content_label)
        
        return frame
