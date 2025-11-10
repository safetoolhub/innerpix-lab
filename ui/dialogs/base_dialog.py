"""Clases/base utilities para diálogos."""
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QCheckBox,
    QDialogButtonBox,
    QPushButton,
    QTableWidget,
)

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QFrame, QRadioButton

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

    def make_ok_cancel_buttons(self, ok_text: Optional[str] = None, ok_style: Optional[str] = None,
                               ok_enabled: bool = True) -> QDialogButtonBox:
        """Crea y devuelve un QDialogButtonBox con Ok/Cancel enlazados a accept/reject.

        Does not mutate dialog state except wiring signals. The caller can further
        customize the returned button box or button texts/styles.
        """
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = box.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_text is not None:
            ok_btn.setText(ok_text)
        if ok_style is not None:
            ok_btn.setStyleSheet(ok_style)
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

    def _create_metric_card(
        self,
        value: str,
        label: str,
        color: Optional[str] = None
    ) -> 'QFrame':
        """Crea tarjeta de métrica inline estandarizada.

        Args:
            value: Valor a mostrar (número, texto)
            label: Etiqueta descriptiva
            color: Color del borde izquierdo (opcional, por defecto PRIMARY)
        
        Returns:
            QFrame con la métrica formateada
        """
        from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
        from ui.styles.design_system import DesignSystem
        
        if color is None:
            color = DesignSystem.COLOR_PRIMARY
        
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BG_1};
                border-left: 3px solid {color};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_8}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(
            int(DesignSystem.SPACE_8),
            int(DesignSystem.SPACE_4),
            int(DesignSystem.SPACE_8),
            int(DesignSystem.SPACE_4)
        )
        layout.setSpacing(int(DesignSystem.SPACE_2))
        
        # Valor
        value_label = QLabel(str(value))
        value_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_2XL}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        
        # Label
        desc_label = QLabel(label)
        desc_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
        """)
        
        layout.addWidget(value_label)
        layout.addWidget(desc_label)
        
        return frame

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
