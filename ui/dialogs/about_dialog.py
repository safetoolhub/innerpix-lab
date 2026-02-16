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
from utils.i18n import tr

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
        self.setWindowTitle(tr("about.title", name=Config.APP_NAME))
        self.setModal(True)
        self.setMinimumSize(1100, 850)
        self.resize(1100, 850)
        
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
        self.tab_widget.addTab(self._create_welcome_tab(), tr("about.tab.welcome"))
        self.tab_widget.addTab(self._create_tools_tab(), tr("about.tab.tools"))
        self.tab_widget.addTab(self._create_tech_tab(), tr("about.tab.info"))

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
        
        version = QLabel(tr("about.header.version", version=Config.APP_VERSION))
        version.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.9);
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        version.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        left_layout.addWidget(version)
        
        header_layout.addLayout(left_layout)
        header_layout.addStretch()
        
        # Lado derecho: Badge de privacidad
        privacy_badge = QLabel(tr("about.header.privacy_badge"))
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
        credits = QLabel(tr("about.footer.credits"))
        credits.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        credits.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        footer_layout.addWidget(credits)
        
        footer_layout.addStretch()
        
        # Botón cerrar
        close_btn = QPushButton(tr("common.close"))
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
        layout.setSpacing(DesignSystem.SPACE_10)
        
        # Título + descripción en la misma sección
        welcome_title = QLabel(tr("about.welcome.title"))
        welcome_title.setStyleSheet(DesignSystem.get_tutorial_section_header_style())
        welcome_title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(welcome_title)
        
        description = QLabel(tr("about.welcome.description"))
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_BASE}px;")
        description.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(description)
        
        # Flujo en lista vertical (4 pasos secuenciales)
        workflow_title = QLabel(tr("about.welcome.workflow_title"))
        workflow_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_MD}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_PRIMARY};
            margin-top: {DesignSystem.SPACE_8}px;
        """)
        workflow_title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(workflow_title)

        workflow_desc = QLabel(tr("about.welcome.workflow_description"))
        workflow_desc.setWordWrap(True)
        workflow_desc.setStyleSheet(f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_SM}px; margin-bottom: {DesignSystem.SPACE_4}px;")
        workflow_desc.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(workflow_desc)
        
        steps_container = QVBoxLayout()
        steps_container.setSpacing(DesignSystem.SPACE_8)
        
        steps = [
            ("1", tr("about.welcome.steps.1.title"), tr("about.welcome.steps.1.description")),
            ("2", tr("about.welcome.steps.2.title"), tr("about.welcome.steps.2.description")),
            ("3", tr("about.welcome.steps.3.title"), tr("about.welcome.steps.3.description")),
            ("4", tr("about.welcome.steps.4.title"), tr("about.welcome.steps.4.description")),
        ]
        
        for num, title, desc in steps:
            step_widget = self._create_step_widget_compact(num, title, desc)
            steps_container.addWidget(step_widget)
        
        layout.addLayout(steps_container)
        
        # Tips en horizontal
        tips_layout = QHBoxLayout()
        tips_layout.setSpacing(DesignSystem.SPACE_8)
        
        tip1 = self._create_mini_tip(tr("about.welcome.tips.simulation.title"), tr("about.welcome.tips.simulation.description"))
        tip2 = self._create_mini_tip(tr("about.welcome.tips.backup.title"), tr("about.welcome.tips.backup.description"))
        tip3 = self._create_mini_tip(tr("about.welcome.tips.logs.title"), tr("about.welcome.tips.logs.description"))
        
        tips_layout.addWidget(tip1)
        tips_layout.addWidget(tip2)
        tips_layout.addWidget(tip3)
        
        layout.addLayout(tips_layout)
        
        # Navegación sutil
        nav_widget = self._create_tab_navigation(next_tab=1, next_label=tr("about.nav.view_tools"))
        layout.addWidget(nav_widget)
        
        layout.addStretch()
        
        return self._create_scroll_content(container)



    def _create_tools_tab(self) -> QWidget:
        """Crea la pestaña de herramientas (8 tools organizadas por categoría con colores)."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(DesignSystem.SPACE_16, DesignSystem.SPACE_8, DesignSystem.SPACE_16, DesignSystem.SPACE_8)
        layout.setSpacing(DesignSystem.SPACE_6)
        
        title = QLabel(tr("about.tools_section.title"))
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
            grid.setSpacing(DesignSystem.SPACE_8)
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

        # Navegación sutil
        nav_widget = self._create_tab_navigation(prev_tab=0, prev_label=tr("about.nav.home"), next_tab=2, next_label=tr("about.nav.view_info"))
        layout.addWidget(nav_widget)

        layout.addStretch()
        return self._create_scroll_content(container)

    # ==================== WIDGETS AUXILIARES ====================

    def _create_tab_navigation(self, prev_tab=None, prev_label=None, next_tab=None, next_label=None) -> QFrame:
        """Crea widget de navegación sutil entre pestañas.
        
        Args:
            prev_tab: Índice de la pestaña anterior (opcional)
            prev_label: Texto para el botón anterior
            next_tab: Índice de la pestaña siguiente (opcional)
            next_label: Texto para el botón siguiente
        """
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
                margin-top: {DesignSystem.SPACE_16}px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, DesignSystem.SPACE_12, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_8)
        
        # Botón anterior
        if prev_tab is not None and prev_label:
            prev_btn = QPushButton(f"← {prev_label}")
            prev_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {DesignSystem.COLOR_PRIMARY};
                    border: 1px solid {DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_MD}px;
                    padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_16}px;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                    border-color: {DesignSystem.COLOR_PRIMARY};
                }}
            """)
            prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            prev_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(prev_tab))
            layout.addWidget(prev_btn)
        
        layout.addStretch()
        
        # Botón siguiente
        if next_tab is not None and next_label:
            next_btn = QPushButton(f"{next_label} →")
            next_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DesignSystem.COLOR_PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {DesignSystem.RADIUS_MD}px;
                    padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_16}px;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
                }}
            """)
            next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            next_btn.clicked.connect(lambda: self.tab_widget.setCurrentIndex(next_tab))
            layout.addWidget(next_btn)
        
        return frame

    # ==================== WIDGETS AUXILIARES (CONTINUACIÓN) ====================

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
        layout.setSpacing(DesignSystem.SPACE_10)
        layout.setContentsMargins(DesignSystem.SPACE_12, DesignSystem.SPACE_8, DesignSystem.SPACE_12, DesignSystem.SPACE_8)
        
        # Icono
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, color=icon_color, size=20)
        icon_label.setFixedSize(24, 24)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        
        # Contenido
        content = QVBoxLayout()
        content.setSpacing(2)
        
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
        layout.setContentsMargins(DesignSystem.SPACE_24, DesignSystem.SPACE_12, DesignSystem.SPACE_24, DesignSystem.SPACE_12)
        layout.setSpacing(DesignSystem.SPACE_10)
        
        # === HEADER SECTION ===
        title = QLabel(tr("about.info.title"))
        title.setStyleSheet(DesignSystem.get_tutorial_section_header_style())
        title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title)
        
        # === DEVELOPER HERO SECTION ===
        dev_hero = self._create_developer_hero()
        layout.addWidget(dev_hero)

        # === TECH INFO GRID ===
        info_grid = QGridLayout()
        info_grid.setSpacing(DesignSystem.SPACE_8)
        
        # Card 1: App Info
        app_card = self._create_info_card(tr("about.info.app_card.title"), [
            (tr("about.info.app_card.name"), Config.APP_NAME),
            (tr("about.info.app_card.version"), Config.APP_VERSION),
            (tr("about.info.app_card.platforms"), tr("about.info.app_card.platforms_value")),
        ])
        info_grid.addWidget(app_card, 0, 0)
        
        # Card 2: Environment
        env_card = self._create_info_card(tr("about.info.tech_card.title"), [
            (tr("about.info.tech_card.language"), "Python 3.x"),
            (tr("about.info.tech_card.ui"), "PyQt6"),
            (tr("about.info.tech_card.architecture"), tr("about.info.tech_card.architecture_value")),
        ])
        info_grid.addWidget(env_card, 0, 1)

        layout.addLayout(info_grid)
        
        # === FORMATS SECTION ===
        formats_card = self._create_formats_card()
        layout.addWidget(formats_card)
        
        # Navegación sutil
        nav_widget = self._create_tab_navigation(prev_tab=1, prev_label=tr("about.nav.view_tools"))
        layout.addWidget(nav_widget)
        
        layout.addStretch()
        return self._create_scroll_content(container)

    # ==================== SECCIÓN HERO DEL DESARROLLADOR ====================

    def _create_developer_hero(self) -> QFrame:
        """Crea la sección del desarrollador con diseño moderno."""
        outer_frame = QFrame()
        outer_frame.setStyleSheet(DesignSystem.get_about_dev_section_style())
        
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setSpacing(DesignSystem.SPACE_8)
        outer_layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_12,
            DesignSystem.SPACE_16, DesignSystem.SPACE_12
        )
        
        # Header con icono y nombre
        header_layout = QHBoxLayout()
        header_layout.setSpacing(DesignSystem.SPACE_10)
        
        shield_icon = QLabel()
        icon_manager.set_label_icon(shield_icon, "shield", color=DesignSystem.COLOR_PRIMARY, size=28)
        header_layout.addWidget(shield_icon)
        
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(2)
        
        org_name = QLabel('<a href="https://safetoolhub.org" style="text-decoration: none;">safetoolhub.org</a>')
        org_name.setStyleSheet(DesignSystem.get_about_dev_org_name_style())
        org_name.setOpenExternalLinks(True)
        org_name.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        org_name.setCursor(Qt.CursorShape.PointingHandCursor)
        header_text_layout.addWidget(org_name)
        
        tagline = QLabel(tr("about.dev.tagline"))
        tagline.setStyleSheet(DesignSystem.get_about_dev_tagline_style())
        tagline.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        header_text_layout.addWidget(tagline)
        
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()
        
        outer_layout.addLayout(header_layout)
        
        # Subtítulo explicativo
        subtitle = QLabel(tr("about.dev.subtitle"))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        subtitle.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            padding-top: {DesignSystem.SPACE_4}px;
        """)
        subtitle.setWordWrap(True)
        subtitle.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        outer_layout.addWidget(subtitle)
        
        # Separador horizontal
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(DesignSystem.get_about_separator_style())
        outer_layout.addWidget(sep)
        
        # Grid de valores en 2x2
        values_grid = QGridLayout()
        values_grid.setSpacing(DesignSystem.SPACE_12)
        
        value_items = [
            ("wifi-off", tr("about.dev.values.offline.title"), tr("about.dev.values.offline.description")),
            ("eye-off", tr("about.dev.values.no_tracking.title"), tr("about.dev.values.no_tracking.description")),
            ("backup-restore", tr("about.dev.values.backup.title"), tr("about.dev.values.backup.description")),
            ("shield", tr("about.dev.values.open_source.title"), tr("about.dev.values.open_source.description")),
        ]
        
        for i, (icon_name, title, desc) in enumerate(value_items):
            value_card = self._create_value_card(icon_name, title, desc)
            row, col = i // 2, i % 2
            values_grid.addWidget(value_card, row, col)
        
        outer_layout.addLayout(values_grid)
        
        # Footer de confianza
        trust_footer = QLabel(tr("about.dev.trust_footer"))
        trust_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trust_footer.setStyleSheet(f"""
            color: {DesignSystem.COLOR_SUCCESS};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            padding-top: {DesignSystem.SPACE_8}px;
        """)
        trust_footer.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        outer_layout.addWidget(trust_footer)
        
        return outer_frame

    def _create_value_card(self, icon_name: str, title: str, desc: str) -> QFrame:
        """Crea una card de valor para la sección de desarrollador."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_about_value_card_style())
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_4)
        layout.setContentsMargins(DesignSystem.SPACE_8, DesignSystem.SPACE_6, DesignSystem.SPACE_8, DesignSystem.SPACE_6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Icono
        icon_label = QLabel()
        icon_manager.set_label_icon(icon_label, icon_name, color=DesignSystem.COLOR_PRIMARY, size=20)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignLeft)
        
        # Título
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_about_value_title_style())
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel(desc)
        desc_label.setStyleSheet(DesignSystem.get_about_value_desc_style())
        desc_label.setWordWrap(True)
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(desc_label)
        
        return frame

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
        frame.setStyleSheet(DesignSystem.get_about_info_card_style())
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_2)
        layout.setContentsMargins(DesignSystem.SPACE_10, DesignSystem.SPACE_8, DesignSystem.SPACE_10, DesignSystem.SPACE_8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title_label)
        
        for label, value in items:
            row = QHBoxLayout()
            row.setSpacing(6)
            
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(DesignSystem.get_about_info_label_style())
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            row.addWidget(lbl)
            
            val = QLabel(value)
            val.setStyleSheet(DesignSystem.get_about_info_value_style())
            val.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            row.addWidget(val)
            row.addStretch()
            
            layout.addLayout(row)
        
        return frame

    def _create_formats_card(self) -> QFrame:
        """Crea la card de formatos soportados."""
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_about_info_card_style())
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_2)
        layout.setContentsMargins(DesignSystem.SPACE_10, DesignSystem.SPACE_8, DesignSystem.SPACE_10, DesignSystem.SPACE_8)
        
        title_label = QLabel(tr("about.info.formats.title"))
        title_label.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        title_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(title_label)
        
        formats = [
            ("image", tr("about.info.formats.images"), "JPG, PNG, HEIC, WEBP, GIF, BMP, TIFF"),
            ("video", tr("about.info.formats.videos"), "MP4, MOV, AVI, MKV, WEBM, M4V"),
        ]
        
        for icon_name, fmt_title, fmt_list in formats:
            row = QHBoxLayout()
            row.setSpacing(6)
            
            icon_label = QLabel()
            icon_manager.set_label_icon(icon_label, icon_name, color=DesignSystem.COLOR_PRIMARY, size=14)
            row.addWidget(icon_label)
            
            text = QLabel(f"<b>{fmt_title}:</b> {fmt_list}")
            text.setStyleSheet(DesignSystem.get_about_formats_text_style())
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
