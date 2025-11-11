"""Clases/base utilities para diálogos."""
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QCheckBox,
    QDialogButtonBox,
    QPushButton,
    QTableWidget,
    QWidget,
)

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QFrame, QRadioButton

from ui.styles.design_system import DesignSystem
from utils.settings_manager import settings_manager


class BaseDialog(QDialog):
    """Clase base para diálogos con utilidades comunes.
    
    Signals:
        actions_completed(str): Emitida cuando el diálogo ejecuta acciones que modifican archivos.
                                Argumento: tool_name identificador de la herramienta.
    """
    
    actions_completed = pyqtSignal(str)  # tool_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backup_checkbox = None
        self._ok_button_ref = None

    def add_backup_checkbox(self, layout=None, label: str = "Crear backup", checked: Optional[bool] = None):
        """Crea y retorna un QCheckBox para la opción de backup.

        Si se pasa un layout, el checkbox se añadirá al layout.
        Guarda la referencia en `self.backup_checkbox`.
        
        Args:
            layout: Layout opcional donde añadir el checkbox
            label: Texto del checkbox
            checked: Estado inicial. Si es None, usa la configuración guardada del usuario
        """
        # Si no se especifica checked, usar la configuración del usuario
        if checked is None:
            checked = settings_manager.get_auto_backup_enabled()
        
        cb = QCheckBox(label)
        cb.setChecked(checked)
        cb.setToolTip(
            "Crea una copia de seguridad de los archivos antes de la operación.\n"
            "Puedes cambiar este comportamiento por defecto en Configuración."
        )
        self.backup_checkbox = cb
        if layout is not None:
            layout.addWidget(cb)
        return cb

    def is_backup_enabled(self) -> bool:
        """Devuelve True si el checkbox de backup existe y está marcado."""
        return bool(self.backup_checkbox and self.backup_checkbox.isChecked())

    def build_accepted_plan(self, extra: Optional[Dict] = None) -> Dict:
        """Construye un dict para accepted_plan incluyendo el flag de backup.

        Usage: return self.build_accepted_plan({'groups': ..., 'keep_strategy': 'oldest'})
        """
        result = {} if extra is None else dict(extra)
        # Always set create_backup based on the current checkbox state so the
        # dialog selection takes precedence over any provided extra value.
        result['create_backup'] = self.is_backup_enabled()
        return result

    def make_ok_cancel_buttons(
        self, 
        ok_text: Optional[str] = None, 
        ok_enabled: bool = True,
        button_style: str = 'primary'
    ) -> QDialogButtonBox:
        """Crea y devuelve un QDialogButtonBox con Ok/Cancel enlazados a accept/reject.
        
        Aplica automáticamente estilos Material Design consistentes.

        Args:
            ok_text: Texto personalizado para el botón OK (default: "OK")
            ok_enabled: Si el botón OK debe estar habilitado inicialmente
            button_style: Estilo del botón OK: 'primary', 'danger', o 'secondary'

        Returns:
            QDialogButtonBox configurado con estilos Material Design
        """
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = box.button(QDialogButtonBox.StandardButton.Cancel)
        
        # Aplicar textos personalizados
        if ok_text is not None:
            ok_btn.setText(ok_text)
        cancel_btn.setText("Cancelar")
        
        # Aplicar estilos Material Design según el tipo especificado
        if button_style == 'danger':
            ok_btn.setStyleSheet(DesignSystem.get_danger_button_style())
        elif button_style == 'secondary':
            ok_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        else:  # 'primary' por defecto
            ok_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        
        cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        
        ok_btn.setEnabled(ok_enabled)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        
        # remember ok button for convenience
        self.register_ok_button(ok_btn)
        return box

    def register_ok_button(self, button: Optional[QPushButton]):
        """Register the dialog's primary OK button so helpers can enable/disable it.

        Pass None to clear the registration.
        """
        self._ok_button_ref = button

    def set_ok_enabled(self, enabled: bool):
        """Enable/disable previously registered OK button (no-op if none)."""
        if self._ok_button_ref is not None:
            self._ok_button_ref.setEnabled(enabled)

    def make_table(self, headers: List[str], max_height: Optional[int] = None) -> QTableWidget:
        """Create a QTableWidget with given headers and optional maximum height.

        Caller is responsible for populating rows and adding it to a layout.
        """
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        if max_height is not None:
            table.setMaximumHeight(max_height)
        return table

    def add_dry_run_checkbox(self, layout, label: str = "Modo simulación (no eliminar archivos)", checked: bool = False):
        """Convenience: add a dry-run checkbox to dialog and return it."""
        cb = QCheckBox(label)
        cb.setChecked(checked)
        layout.addWidget(cb)
        # store if there's a need to access later; name-based access is simplest
        self.dry_run_checkbox = cb
        return cb

    def _create_explanation_frame(
        self,
        icon_name: str,
        title: str,
        description: str
    ) -> 'QFrame':
        """Crea frame de explicación estandarizado con icono, título y descripción.

        Args:
            icon_name: Nombre del icono de icon_manager (ej: 'content-copy')
            title: Título principal (negrita)
            description: Texto descriptivo
        
        Returns:
            QFrame con el header explicativo
        """
        from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
        from ui.styles.design_system import DesignSystem
        from utils.icons import icon_manager
        
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {DesignSystem.COLOR_BG_1},
                    stop:1 {DesignSystem.COLOR_BG_2});
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(int(DesignSystem.SPACE_12))
        layout.setContentsMargins(
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_8),
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_8)
        )
        
        # Icono
        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label, 
            icon_name, 
            size=DesignSystem.ICON_SIZE_LG,
            color=DesignSystem.COLOR_PRIMARY
        )
        layout.addWidget(icon_label)
        
        # Contenedor de texto
        text_container = QVBoxLayout()
        text_container.setSpacing(int(DesignSystem.SPACE_4))
        
        # Título
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        text_container.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            line-height: 1.5;
        """)
        text_container.addWidget(desc_label)
        
        layout.addLayout(text_container, 1)
        
        return frame
    
    def _create_compact_header_with_metrics(
        self,
        icon_name: str,
        title: str,
        description: str,
        metrics: List[Dict[str, str]]
    ) -> 'QFrame':
        """Crea header compacto integrado con métricas inline estilo Material Design.
        
        Combina icono, título, descripción y métricas en un diseño horizontal compacto
        que ahorra espacio vertical. Las métricas aparecen alineadas a la derecha.

        Args:
            icon_name: Nombre del icono de icon_manager (ej: 'content-copy')
            title: Título principal (negrita)
            description: Texto descriptivo (1-2 líneas)
            metrics: Lista de diccionarios con formato:
                [
                    {'value': '45', 'label': 'Grupos', 'color': COLOR_PRIMARY},
                    {'value': '120', 'label': 'Copias', 'color': COLOR_WARNING},
                    {'value': '2.5 GB', 'label': 'Espacio', 'color': COLOR_SUCCESS}
                ]
        
        Returns:
            QFrame con header compacto y profesional
        """
        from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
        from ui.styles.design_system import DesignSystem
        from utils.icons import icon_manager
        
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border-bottom: 1px solid {DesignSystem.COLOR_BORDER};
                padding: 0px;
            }}
        """)
        
        # Layout principal horizontal
        main_layout = QHBoxLayout(frame)
        main_layout.setSpacing(int(DesignSystem.SPACE_16))
        main_layout.setContentsMargins(
            int(DesignSystem.SPACE_20),
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_20),
            int(DesignSystem.SPACE_12)
        )
        
        # === LADO IZQUIERDO: Icono + Texto ===
        left_container = QHBoxLayout()
        left_container.setSpacing(int(DesignSystem.SPACE_12))
        
        # Icono
        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label, 
            icon_name, 
            size=DesignSystem.ICON_SIZE_XL,  # Más grande para impacto visual
            color=DesignSystem.COLOR_PRIMARY
        )
        left_container.addWidget(icon_label)
        
        # Contenedor de texto (título + descripción apilados)
        text_container = QVBoxLayout()
        text_container.setSpacing(int(DesignSystem.SPACE_2))
        
        # Título
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XL}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        text_container.addWidget(title_label)
        
        # Descripción
        desc_label = QLabel(description)
        desc_label.setWordWrap(False)  # Mantenerlo en una línea
        desc_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        text_container.addWidget(desc_label)
        
        left_container.addLayout(text_container)
        main_layout.addLayout(left_container, 0)  # Sin stretch para mantener pegado a la izquierda
        
        # Stretch para empujar métricas a la derecha
        main_layout.addStretch()
        
        # === LADO DERECHO: Métricas inline ===
        metrics_container = QHBoxLayout()
        metrics_container.setSpacing(int(DesignSystem.SPACE_20))
        
        for metric in metrics:
            metric_widget = self._create_inline_metric(
                value=metric['value'],
                label=metric['label'],
                color=metric.get('color', DesignSystem.COLOR_PRIMARY)
            )
            metrics_container.addWidget(metric_widget)
        
        main_layout.addLayout(metrics_container)
        
        return frame
    
    def _create_inline_metric(
        self,
        value: str,
        label: str,
        color: str
    ) -> 'QWidget':
        """Crea métrica inline minimalista para header compacto.
        
        Args:
            value: Valor numérico o texto a mostrar
            label: Etiqueta descriptiva
            color: Color del indicador y valor
        
        Returns:
            QWidget con la métrica formateada
        """
        from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
        from PyQt6.QtCore import Qt
        from ui.styles.design_system import DesignSystem
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(int(DesignSystem.SPACE_2))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Valor (grande y destacado)
        value_label = QLabel(str(value))
        value_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_2XL}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {color};
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        
        # Label (pequeño y sutil)
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        """)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_widget)
        
        return widget

    def _create_selection_card(
        self,
        card_id: str,
        icon_name: str,
        title: str,
        description: str,
        is_selected: bool,
        radio_button: Optional['QRadioButton'] = None
    ) -> 'QFrame':
        """Crea tarjeta de selección clickeable con RadioButton (patrón organization_dialog).

        Args:
            card_id: ID único de la card (ej: 'strategy-oldest')
            icon_name: Nombre del icono de icon_manager
            title: Título de la opción
            description: Descripción de la opción
            is_selected: Si la card está seleccionada
            radio_button: RadioButton a asociar (opcional, se crea si es None)
        
        Returns:
            QFrame con la card de selección
        """
        from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton
        from ui.styles.design_system import DesignSystem
        from utils.icons import icon_manager
        
        card = QFrame()
        card.setObjectName(card_id)
        card.setStyleSheet(f"""
            QFrame#{card_id} {{
                background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
                border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px;
            }}
            QFrame#{card_id}:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
            }}
            QFrame#{card_id} QLabel {{
                color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
            }}
            QFrame#{card_id} QLabel#title-label {{
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            QFrame#{card_id} QLabel#desc-label {{
                color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(int(DesignSystem.SPACE_8))
        
        # Header: RadioButton + Icono + Título
        header_layout = QHBoxLayout()
        
        if radio_button is None:
            radio_button = QRadioButton()
            radio_button.setChecked(is_selected)
        
        header_layout.addWidget(radio_button)
        
        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label, 
            icon_name, 
            size=DesignSystem.ICON_SIZE_XL,
            color=DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_PRIMARY
        )
        icon_label.icon_name = icon_name  # Guardar nombre del icono para actualización posterior
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setObjectName("title-label")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Descripción
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setObjectName("desc-label")
        layout.addWidget(desc_label)
        
        # Hacer la card clickeable
        card.mousePressEvent = lambda event: radio_button.setChecked(True)
        
        # Guardar referencia al radio en la card
        card.setProperty("radio_button", radio_button)
        
        return card
    
    def _create_option_selector(
        self,
        title: str,
        title_icon: str,
        options: list[tuple],
        selected_value: any,
        on_change_callback: callable
    ) -> 'QFrame':
        """Crea selector de opciones con cards interactivas CENTRALIZADO.
        
        Patrón unificado para todos los dialogs que necesiten radio buttons
        de selección (estrategias, modos, formatos, tipos).
        
        Args:
            title: Título del selector (ej: "Elige qué archivo conservar")
            title_icon: Nombre del icono para el título (ej: 'rule')
            options: Lista de tuplas con formato:
                (value, icon_name, title, description)
                donde value es el identificador único de la opción
            selected_value: Valor actualmente seleccionado
            on_change_callback: Función a llamar cuando cambia la selección.
                Recibe el nuevo valor como argumento.
        
        Returns:
            QFrame con el selector completo
        
        Example:
            selector = self._create_option_selector(
                title="Elige qué archivo conservar",
                title_icon='rule',
                options=[
                    ('oldest', 'access_time', 'Más antiguo', 'Conserva el original'),
                    ('newest', 'update', 'Más reciente', 'Conserva la versión editada')
                ],
                selected_value=self.keep_strategy,
                on_change_callback=self._on_strategy_changed
            )
        """
        from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton, QButtonGroup
        from ui.styles.design_system import DesignSystem
        from utils.icons import icon_manager
        
        frame = QFrame()
        frame.setObjectName("option-selector-frame")
        frame.setStyleSheet(f"""
            QFrame#option-selector-frame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(int(DesignSystem.SPACE_12))
        
        # Título del selector
        title_layout = QHBoxLayout()
        title_icon_label = QLabel()
        icon_manager.set_label_icon(
            title_icon_label, 
            title_icon, 
            size=int(DesignSystem.ICON_SIZE_LG)
        )
        title_layout.addWidget(title_icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # ButtonGroup para RadioButtons
        button_group = QButtonGroup(frame)
        
        # Cards layout (horizontal)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(int(DesignSystem.SPACE_12))
        
        # Crear una card por cada opción
        for idx, (value, icon_name, opt_title, description) in enumerate(options):
            is_selected = (value == selected_value)
            
            # Usar índice para ID consistente y evitar problemas con caracteres especiales
            card_id = f"option-{idx}"
            
            # Crear RadioButton
            radio = QRadioButton()
            radio.setChecked(is_selected)
            radio.toggled.connect(
                lambda checked, v=value: on_change_callback(v) if checked else None
            )
            button_group.addButton(radio)
            
            # Crear card usando el método de BaseDialog
            card = self._create_selection_card(
                card_id,
                icon_name,
                opt_title,
                description,
                is_selected,
                radio
            )
            # Guardar el valor original en la card para referencia posterior
            card.setProperty("option_value", value)
            cards_layout.addWidget(card)
        
        layout.addLayout(cards_layout)
        
        # Guardar referencia al ButtonGroup para acceso posterior si es necesario
        frame.setProperty("button_group", button_group)
        
        return frame
    
    def _update_option_selector_styles(
        self,
        selector_frame: 'QFrame',
        options_values: list,
        selected_value: any
    ):
        """Actualiza los estilos de las cards en un selector de opciones.
        
        Útil cuando cambia la selección y necesitas actualizar visualmente las cards.
        
        Args:
            selector_frame: QFrame retornado por _create_option_selector
            options_values: Lista de valores de las opciones en el mismo orden que se pasaron a _create_option_selector
            selected_value: Valor actualmente seleccionado
        """
        from PyQt6.QtWidgets import QFrame
        from ui.styles.design_system import DesignSystem
        
        for idx, value in enumerate(options_values):
            card_name = f"option-{idx}"
            card = selector_frame.findChild(QFrame, card_name)
            
            if card:
                is_selected = (value == selected_value)
                card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_SURFACE};
                        border: 2px solid {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BORDER};
                        border-radius: {DesignSystem.RADIUS_BASE}px;
                        padding: {DesignSystem.SPACE_12}px;
                    }}
                    QFrame#{card_name}:hover {{
                        border-color: {DesignSystem.COLOR_PRIMARY};
                        background-color: {DesignSystem.COLOR_PRIMARY if is_selected else DesignSystem.COLOR_BG_2};
                    }}
                    QFrame#{card_name} QLabel {{
                        color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT};
                    }}
                    QFrame#{card_name} QLabel#title-label {{
                        font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                    }}
                    QFrame#{card_name} QLabel#desc-label {{
                        color: {DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_TEXT_SECONDARY};
                    }}
                """)
                
                # Actualizar color del icono
                self._update_card_icon_color(card, is_selected)
    
    def _update_card_icon_color(self, card: 'QFrame', is_selected: bool):
        """Actualiza el color del icono en una card de selección.
        
        Args:
            card: QFrame de la card
            is_selected: Si la card está seleccionada
        """
        from PyQt6.QtWidgets import QLabel
        from ui.styles.design_system import DesignSystem
        from utils.icons import icon_manager
        
        # Encontrar el icono (segundo QLabel en el header layout)
        layout = card.layout()
        if layout and layout.count() > 0:
            header_layout = layout.itemAt(0).layout()  # Primer item es el header_layout
            if header_layout and header_layout.count() >= 3:  # RadioButton, Icono, Título
                icon_label = header_layout.itemAt(1).widget()  # Segundo widget es el icono
                if isinstance(icon_label, QLabel):
                    # Obtener el icono actual y actualizar su color
                    current_icon = getattr(icon_label, 'icon_name', None)
                    if current_icon:
                        icon_manager.set_label_icon(
                            icon_label,
                            current_icon,
                            size=DesignSystem.ICON_SIZE_XL,
                            color=DesignSystem.COLOR_PRIMARY_TEXT if is_selected else DesignSystem.COLOR_PRIMARY
                        )
                        icon_label.update()  # Forzar repaint