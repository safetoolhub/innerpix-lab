"""Clases/base utilities para diálogos."""
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog,
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
        
        # Aplicar estilo global a todos los diálogos
        self.setStyleSheet(DesignSystem.get_stylesheet() + DesignSystem.get_tooltip_style())



    def is_backup_enabled(self) -> bool:
        """Devuelve True si el checkbox de backup existe y está marcado."""
        if not self.backup_checkbox:
            return False
        
        # Si es el diseño compacto con contenedor, usar _checkbox interno
        if hasattr(self.backup_checkbox, '_checkbox'):
            return self.backup_checkbox._checkbox.isChecked()
        
        # Si es QCheckBox directo
        return self.backup_checkbox.isChecked()
    
    def is_dry_run_enabled(self) -> bool:
        """Devuelve True si el checkbox de dry-run existe y está marcado."""
        if not self.dry_run_checkbox:
            return False
        
        # Si es el diseño compacto con contenedor, usar _checkbox interno
        if hasattr(self.dry_run_checkbox, '_checkbox'):
            return self.dry_run_checkbox._checkbox.isChecked()
        
        # Si es QCheckBox directo
        return self.dry_run_checkbox.isChecked()
    
    def is_cleanup_enabled(self) -> bool:
        """Devuelve True si el checkbox de cleanup existe y está marcado."""
        if not hasattr(self, 'cleanup_checkbox') or not self.cleanup_checkbox:
            return False
        
        # Si es el diseño compacto con contenedor, usar _checkbox interno
        if hasattr(self.cleanup_checkbox, '_checkbox'):
            return self.cleanup_checkbox._checkbox.isChecked()
        
        # Si es QCheckBox directo
        return self.cleanup_checkbox.isChecked()



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
        
        # Eliminar iconos automáticos de Qt que no respetan los colores personalizados
        from PyQt6.QtGui import QIcon
        ok_btn.setIcon(QIcon())  # Icono vacío
        cancel_btn.setIcon(QIcon())  # Icono vacío
        
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

    def make_styled_button(
        self,
        text: str = "",
        icon_name: str = "",
        button_style: str = 'secondary',
        tooltip: str = "",
        enabled: bool = True,
        custom_style: str = ""
    ) -> QPushButton:
        """Crea un botón estilizado con Material Design.
        
        Args:
            text: Texto del botón
            icon_name: Nombre del icono (opcional)
            button_style: Estilo: 'primary', 'secondary', 'danger'
            tooltip: Tooltip del botón
            enabled: Si está habilitado inicialmente
            custom_style: CSS personalizado (opcional, reemplaza el estilo estándar)
        
        Returns:
            QPushButton configurado
        """
        btn = QPushButton(text)
        if icon_name:
            from utils.icons import icon_manager
            btn.setIcon(icon_manager.get_icon(icon_name))
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setEnabled(enabled)
        
        # Aplicar estilo
        if custom_style:
            btn.setStyleSheet(custom_style)
        else:
            if button_style == 'danger':
                btn.setStyleSheet(DesignSystem.get_danger_button_style())
            elif button_style == 'primary':
                btn.setStyleSheet(DesignSystem.get_primary_button_style())
            else:  # 'secondary' por defecto
                btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        
        return btn

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
    
    def _update_header_metric(self, header_frame: 'QFrame', metric_label: str, new_value: str) -> None:
        """Actualiza dinámicamente el valor de una métrica específica en el header.
        
        Busca la métrica por su etiqueta (label) y actualiza el valor asociado.
        Útil para actualizar métricas cuando el usuario cambia opciones en el diálogo.
        
        Args:
            header_frame: El QFrame retornado por _create_compact_header_with_metrics
            metric_label: El label de la métrica a actualizar (ej: 'Recuperable', 'Grupos')
            new_value: El nuevo valor a mostrar (ej: '2.5 GB', '45')
        
        Example:
            self._update_header_metric(self.header_frame, 'Recuperable', format_size(new_space))
        """
        from PyQt6.QtWidgets import QLabel, QWidget
        
        # Recorrer todos los QWidget del frame para encontrar los contenedores de métricas
        for widget in header_frame.findChildren(QWidget):
            if not widget.layout():
                continue
            
            # Buscar el widget que contiene la métrica (tiene 2 labels: valor y label)
            all_labels = widget.findChildren(QLabel)
            # Filtrar solo hijos directos del widget
            direct_labels = [l for l in all_labels if l.parent() == widget]
            
            if len(direct_labels) == 2:
                # Estructura esperada: [value_label, label_widget]
                value_label, label_widget = direct_labels[0], direct_labels[1]
                
                # Verificar si este es el label que buscamos
                if label_widget.text().lower() == metric_label.lower():
                    value_label.setText(new_value)
                    return

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
        title_icon: Optional[str],
        options: list[tuple],
        selected_value: any,
        on_change_callback: callable
    ) -> 'QFrame':
        """Crea selector de opciones con cards interactivas CENTRALIZADO.
        
        Patrón unificado para todos los dialogs que necesiten radio buttons
        de selección (estrategias, modos, formatos, tipos).
        
        Args:
            title: Título del selector (ej: "Elige qué archivo conservar")
            title_icon: Nombre del icono para el título (ej: 'ruler'). Opcional, si es None no se muestra icono
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
                title_icon='ruler',  # o None para no mostrar icono
                options=[
                    ('oldest', 'clock-outline', 'Más antiguo', 'Conserva el original'),
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
        
        # Solo agregar icono si se proporciona
        if title_icon:
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
    
    def _create_security_options_section(
        self,
        show_backup: bool = True,
        show_dry_run: bool = False,
        show_cleanup_empty_dirs: bool = False,
        backup_label: str = "Crear backup",
        dry_run_label: str = "Modo simulación",
        cleanup_label: str = "Limpiar carpetas vacías"
    ) -> 'QFrame':
        """Crea sección de opciones ultra-compacta con diseño Material Design 3.
        
        Diseño 100% horizontal tipo "chip" con máxima compacidad vertical.
        Todo en una sola línea con chips minimalistas y profesionales.
        
        Args:
            show_backup: Si se debe mostrar el checkbox de backup
            show_dry_run: Si se debe mostrar el checkbox de dry-run
            show_cleanup_empty_dirs: Si se debe mostrar el checkbox de limpieza de carpetas
            backup_label: Texto para el checkbox de backup
            dry_run_label: Texto para el checkbox de dry-run
            cleanup_label: Texto para el checkbox de limpieza de carpetas
        
        Returns:
            QFrame con la sección ultra-compacta configurada
        """
        from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
        from ui.styles.design_system import DesignSystem
        from utils.icons import icon_manager
        from utils.settings_manager import settings_manager
        
        frame = QFrame()
        frame.setObjectName("security-options-frame")
        frame.setStyleSheet(f"""
            QFrame#security-options-frame {{
                background-color: transparent;
                border: none;
                padding: 0px;
            }}
        """)
        
        # Layout principal 100% horizontal (una sola línea)
        main_layout = QHBoxLayout(frame)
        main_layout.setSpacing(int(DesignSystem.SPACE_12))
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # === Label "Opciones:" inline minimalista ===
        options_label = QLabel("Opciones:")
        options_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            padding: 0px;
            margin: 0px;
        """)
        main_layout.addWidget(options_label)
        
        # === Checkbox de backup (inline chip style) ===
        if show_backup:
            backup_checked = settings_manager.get_auto_backup_enabled()
            self.backup_checkbox = self._create_inline_chip_checkbox(
                icon_name='content-save',
                label=backup_label,
                checked=backup_checked,
                tooltip="Crea una copia de seguridad timestamped antes de realizar cambios.\n"
                        "Recomendado para operaciones destructivas."
            )
            main_layout.addWidget(self.backup_checkbox)
        
        # === Checkbox de dry-run (inline chip style) ===
        if show_dry_run:
            dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, False)
            if isinstance(dry_run_default, str):
                dry_run_default = dry_run_default.lower() in ('true', '1', 'yes')
            
            self.dry_run_checkbox = self._create_inline_chip_checkbox(
                icon_name='eye',
                label=dry_run_label,
                checked=bool(dry_run_default),
                tooltip="Simula la operación sin realizar cambios reales.\n"
                        "Útil para verificar qué archivos se verían afectados.\n\n"
                        "⚠️ Nota: Al activar modo simulación, el backup se deshabilita automáticamente\n"
                        "ya que no se realizarán cambios reales."
            )
            main_layout.addWidget(self.dry_run_checkbox)
            
            # Conectar lógica de deshabilitación mutua
            if show_backup and hasattr(self, 'backup_checkbox'):
                self._setup_dry_run_backup_logic()
        
        # === Checkbox de cleanup empty dirs (inline chip style) ===
        if show_cleanup_empty_dirs:
            self.cleanup_checkbox = self._create_inline_chip_checkbox(
                icon_name='folder-remove',
                label=cleanup_label,
                checked=False,  # Default deshabilitado para ser conservador
                tooltip="Elimina automáticamente las carpetas que queden vacías\n"
                        "después de mover los archivos durante la organización."
            )
            main_layout.addWidget(self.cleanup_checkbox)
        
        # Spacer para empujar contenido a la izquierda
        main_layout.addStretch()
        
        return frame
    
    def _create_warning_banner(
        self,
        title: str,
        message: str,
        icon: str = 'alert',
        action_text: Optional[str] = None,
        action_callback: Optional[callable] = None,
        bg_color: str = DesignSystem.COLOR_WARNING_BG,
        border_color: str = DesignSystem.COLOR_WARNING,
        text_color: str = DesignSystem.COLOR_TEXT
    ) -> 'QFrame':
        """Crea un banner de advertencia estandarizado.
        
        Args:
            title: Título en negrita
            message: Mensaje descriptivo (soporta HTML básico)
            icon: Nombre del icono (default: 'alert')
            action_text: Texto del botón de acción (opcional)
            action_callback: Función a llamar al pulsar el botón (opcional)
            bg_color: Color de fondo (default: Warning BG)
            border_color: Color del borde (default: Warning)
            text_color: Color del texto (default: Text)
            
        Returns:
            QFrame configurado con el banner
        """
        from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
        from PyQt6.QtCore import Qt
        from ui.styles.design_system import DesignSystem
        from utils.icons import icon_manager
        
        frame = QFrame()
        frame.setObjectName("warningBanner")
        frame.setStyleSheet(f"""
            QFrame#warningBanner {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_8),
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_8)
        )
        layout.setSpacing(int(DesignSystem.SPACE_12))
        
        # Icono
        icon_label = QLabel()
        # Usar un tamaño un poco más grande para el icono de advertencia
        icon_manager.set_label_icon(
            icon_label, 
            icon, 
            size=DesignSystem.ICON_SIZE_LG,
            color=DesignSystem.COLOR_TEXT  # El icono suele ser texto/emoji o SVG coloreado
        )
        # Si es un emoji (fallback), asegurar tamaño
        icon_label.setStyleSheet(f"font-size: {DesignSystem.FONT_SIZE_LG}px;")
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        
        # Contenedor de texto
        text_layout = QVBoxLayout()
        text_layout.setSpacing(int(DesignSystem.SPACE_4))
        
        # Mensaje compuesto (Título: Mensaje)
        full_message = f"<b>{title}:</b> {message}" if title else message
        text_label = QLabel(full_message)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            color: {text_color};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        text_layout.addWidget(text_label)
        
        layout.addLayout(text_layout, 1)
        
        # Botón de acción (opcional)
        if action_text and action_callback:
            action_btn = QPushButton(action_text)
            # Determinar estilo del botón basado en el tipo de alerta
            btn_bg = border_color  # Usar el color del borde como fondo del botón
            btn_hover = border_color # Simplificación, idealmente un tono más oscuro
            
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    color: {DesignSystem.COLOR_TEXT};
                    border: none;
                    border-radius: {DesignSystem.RADIUS_SM}px;
                    padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_12}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                }}
                QPushButton:hover {{
                    opacity: 0.9;
                }}
            """)
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.clicked.connect(action_callback)
            layout.addWidget(action_btn)
            
        return frame

    def _create_info_banner(
        self,
        title: str,
        message: str,
        icon: str = 'information-outline'
    ) -> 'QFrame':
        """Crea un banner de información (azul) estandarizado.
        
        Wrapper conveniente sobre _create_warning_banner con colores de Info.
        """
        return self._create_warning_banner(
            title=title,
            message=message,
            icon=icon,
            bg_color=DesignSystem.COLOR_INFO_BG,
            border_color=DesignSystem.COLOR_INFO,
            text_color="#055160"  # Color oscuro para texto sobre fondo azul claro
        )
    def _setup_dry_run_backup_logic(self):
        """Configura la lógica de deshabilitación automática entre dry-run y backup.
        
        Cuando dry-run está activo, el backup se deshabilita visualmente Y se desactiva
        automáticamente ya que no se realizarán cambios reales en los archivos.
        Guarda el estado previo para restaurarlo cuando se desactive dry-run.
        """
        # Variable para guardar el estado previo del backup
        self._backup_state_before_dry_run = None
        
        def on_dry_run_changed():
            if not hasattr(self, 'dry_run_checkbox') or not hasattr(self, 'backup_checkbox'):
                return
            
            dry_run_enabled = self.is_dry_run_enabled()
            backup_widget = self.backup_checkbox
            backup_checkbox_internal = backup_widget._checkbox if hasattr(backup_widget, '_checkbox') else backup_widget
            
            if dry_run_enabled:
                # Guardar estado actual del backup antes de deshabilitarlo
                self._backup_state_before_dry_run = backup_checkbox_internal.isChecked()
                
                # Desactivar el checkbox del backup
                backup_checkbox_internal.setChecked(False)
                
                # Deshabilitar visualmente el widget
                backup_widget.setEnabled(False)
                backup_widget.setToolTip(
                    "⚠️ El backup está deshabilitado porque el modo simulación está activo.\n"
                    "No se realizarán cambios reales, por lo que no es necesario crear backup."
                )
            else:
                # Restaurar estado previo del backup si existía
                if self._backup_state_before_dry_run is not None:
                    backup_checkbox_internal.setChecked(self._backup_state_before_dry_run)
                    self._backup_state_before_dry_run = None
                
                # Rehabilitar visualmente el widget
                backup_widget.setEnabled(True)
                backup_widget.setToolTip(
                    "Crea una copia de seguridad timestamped antes de realizar cambios.\n"
                    "Recomendado para operaciones destructivas."
                )
        
        # Conectar señal
        if hasattr(self.dry_run_checkbox, '_checkbox'):
            self.dry_run_checkbox._checkbox.toggled.connect(on_dry_run_changed)
        else:
            self.dry_run_checkbox.toggled.connect(on_dry_run_changed)
        
        
        # Ejecutar lógica inicial
        on_dry_run_changed()
    
    def _create_inline_chip_checkbox(
        self,
        icon_name: str,
        label: str,
        checked: bool,
        tooltip: str
    ) -> QWidget:
        """Crea un checkbox ultra-compacto estilo "chip" Material Design 3.
        
        Diseño inline minimalista profesional con transiciones suaves.
        Inspirado en los filter chips de Material Design 3.
        
        Args:
            icon_name: Nombre del icono de icon_manager
            label: Texto del checkbox
            checked: Estado inicial
            tooltip: Texto del tooltip
        
        Returns:
            QWidget contenedor con el diseño chip inline
        """
        from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox
        from PyQt6.QtCore import Qt
        from ui.styles.design_system import DesignSystem
        from utils.icons import icon_manager
        
        # Contenedor tipo chip
        container = QWidget()
        container.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(
            int(DesignSystem.SPACE_10),
            int(DesignSystem.SPACE_6),
            int(DesignSystem.SPACE_10),
            int(DesignSystem.SPACE_6)
        )
        layout.setSpacing(int(DesignSystem.SPACE_6))
        
        # Checkbox real (oculto)
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.setStyleSheet("QCheckBox { margin: 0; padding: 0; } QCheckBox::indicator { width: 0; height: 0; }")
        
        # Establecer tooltip en el contenedor visual (no en el checkbox oculto)
        container.setToolTip(tooltip)
        
        # Icono Material Design con checkmark integrado
        icon_label = QLabel()
        # Quitar tamaño fijo para evitar cortes horizontales
        layout.addWidget(icon_label)
        
        # Texto del chip
        text_label = QLabel(label)
        text_label.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                padding: 0px;
                margin: 0px;
                border: none;
                background: transparent;
            }}
        """)
        layout.addWidget(text_label)
        
        # Función para toggle
        def toggle_checkbox():
            if container.isEnabled():
                checkbox.setChecked(not checkbox.isChecked())
        
        def update_visual_state():
            is_checked = checkbox.isChecked()
            is_enabled = container.isEnabled()
            
            # Determinar colores según estado
            if not is_enabled:
                bg_color = DesignSystem.COLOR_BG_1
                border_color = DesignSystem.COLOR_BORDER
                text_color = DesignSystem.COLOR_TEXT_SECONDARY
                icon_color = DesignSystem.COLOR_TEXT_SECONDARY
                icon_to_show = icon_name
            elif is_checked:
                bg_color = DesignSystem.COLOR_PRIMARY
                border_color = DesignSystem.COLOR_PRIMARY
                text_color = DesignSystem.COLOR_PRIMARY_TEXT
                icon_color = DesignSystem.COLOR_PRIMARY_TEXT
                icon_to_show = 'check-circle'  # Icono de check cuando está seleccionado
            else:
                bg_color = DesignSystem.COLOR_SURFACE
                border_color = DesignSystem.COLOR_BORDER
                text_color = DesignSystem.COLOR_TEXT
                icon_color = DesignSystem.COLOR_TEXT_SECONDARY
                icon_to_show = icon_name
            
            # Actualizar icono
            icon_manager.set_label_icon(
                icon_label,
                icon_to_show,
                color=icon_color
            )
            
            # Actualizar texto
            text_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                    color: {text_color};
                    padding: 0px;
                    margin: 0px;
                    border: none;
                    background: transparent;
                }}
            """)
            
            # Estilo del contenedor chip con transición suave
            hover_bg = DesignSystem.COLOR_PRIMARY if is_checked else DesignSystem.COLOR_BG_2
            
            if not is_enabled:
                hover_bg = DesignSystem.COLOR_BG_1
            
            container.setStyleSheet(f"""
                QWidget {{
                    background-color: {bg_color};
                    border-radius: 16px;
                }}
                QWidget:hover {{
                    background-color: {hover_bg};
                    border: 1px solid {DesignSystem.COLOR_PRIMARY};
                }}
                QWidget:hover QLabel {{
                    background: transparent;
                }}
            """)
        
        container.mousePressEvent = lambda event: toggle_checkbox()
        update_visual_state()
        
        # Conectar cambios
        checkbox.toggled.connect(update_visual_state)
        
        # Guardar referencias
        container._checkbox = checkbox
        container._update_visual_state = update_visual_state
        
        return container
    
