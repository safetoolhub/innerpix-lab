from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QGroupBox, QVBoxLayout as QVLayout,
    QRadioButton, QButtonGroup, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from services.live_photo_cleaner import CleanupMode
from utils.format_utils import format_size
from ui import ui_styles
from ui.styles.design_system import DesignSystem
from utils.icons import icon_manager
from .base_dialog import BaseDialog


class LivePhotoCleanupDialog(BaseDialog):
    """Diálogo para limpieza de Live Photos"""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis  # Dataclass con atributos
        self.selected_mode = CleanupMode.KEEP_IMAGE
        self.accepted_plan = None
        self.init_ui()

    def _calculate_space_for_mode(self, mode):
        """Calcula el espacio a liberar según el modo seleccionado"""
        groups = self.analysis.groups  # Dataclass attribute
        if not groups:
            return 0

        total_space = 0
        if mode == CleanupMode.KEEP_IMAGE:
            for group in groups:
                total_space += group.video_size
        elif mode == CleanupMode.KEEP_VIDEO:
            for group in groups:
                total_space += group.image_size
        return total_space

    def _update_button_text(self):
        """Actualiza el texto del botón según el modo seleccionado"""
        groups = self.analysis.groups  # Dataclass attribute
        live_photos_found = len(groups)
        if live_photos_found > 0:
            space = self._calculate_space_for_mode(self.selected_mode)
            space_formatted = format_size(space)
            files_type = "videos" if self.selected_mode == CleanupMode.KEEP_IMAGE else "imágenes"
            self.ok_button.setText(f"Eliminar {live_photos_found} {files_type} ({space_formatted})")

    def init_ui(self):
        self.setWindowTitle("Limpieza de Live Photos")
        self.setModal(True)
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        layout.setSpacing(int(DesignSystem.SPACE_16))
        layout.setContentsMargins(
            int(DesignSystem.SPACE_24),
            int(DesignSystem.SPACE_20),
            int(DesignSystem.SPACE_24),
            int(DesignSystem.SPACE_20)
        )

        # Header explicativo
        explanation = self._create_explanation_frame(
            'camera',
            'Live Photos detectadas',
            'Los Live Photos de iPhone contienen una imagen JPG y un video MOV con el mismo nombre. '
            'Selecciona qué componente deseas conservar.'
        )
        layout.addWidget(explanation)

        # Métricas
        from PyQt6.QtWidgets import QHBoxLayout
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(int(DesignSystem.SPACE_12))
        
        live_photos_metric = self._create_metric_card(
            str(self.analysis.live_photos_found),
            "Live Photos detectadas",
            DesignSystem.COLOR_PRIMARY
        )
        metrics_layout.addWidget(live_photos_metric)
        
        space_metric = self._create_metric_card(
            format_size(self.analysis.total_space),
            "Espacio total ocupado",
            DesignSystem.COLOR_WARNING
        )
        metrics_layout.addWidget(space_metric)
        
        metrics_layout.addStretch()
        layout.addLayout(metrics_layout)

        # Selector de modo con cards
        mode_selector = self._create_mode_selector()
        layout.addWidget(mode_selector)

        # Opciones
        options_group = QGroupBox("Opciones de Seguridad")
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet(f"QGroupBox {{ font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; padding-top: {DesignSystem.SPACE_12}px; }}")
        options_layout = QVLayout(options_group)

        # Backup checkbox (primero)
        self.add_backup_checkbox(options_layout, "Crear backup antes de eliminar (Recomendado)")

        # Simulación checkbox (segundo)
        from PyQt6.QtWidgets import QCheckBox
        self.dry_run_checkbox = QCheckBox("Modo simulación (no eliminar archivos realmente)")
        # Leer configuración para establecer estado por defecto
        from utils.settings_manager import settings_manager
        dry_run_default = settings_manager.get(settings_manager.KEY_DRY_RUN_DEFAULT, False)
        # Asegurar que es un booleano
        if isinstance(dry_run_default, str):
            dry_run_default = dry_run_default.lower() in ('true', '1', 'yes')
        self.dry_run_checkbox.setChecked(bool(dry_run_default))
        options_layout.addWidget(self.dry_run_checkbox)
        layout.addWidget(options_group)

        # Botones
        live_photos_found = self.analysis.live_photos_found
        ok_enabled = live_photos_found > 0
        ok_text = None if ok_enabled else "No hay Live Photos para limpiar"
        self.buttons = self.make_ok_cancel_buttons(ok_text=ok_text, ok_enabled=ok_enabled)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        # If there are items, update text according to mode
        if live_photos_found > 0:
            self._update_button_text()
        layout.addWidget(self.buttons)
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())

    def _create_mode_selector(self):
        """Crea selector de modo con cards interactivas."""
        from PyQt6.QtWidgets import QFrame, QHBoxLayout
        
        frame = QFrame()
        frame.setObjectName("mode-selector-frame")
        frame.setStyleSheet(f"""
            QFrame#mode-selector-frame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(int(DesignSystem.SPACE_12))
        
        # Título
        title_layout = QHBoxLayout()
        title_icon = QLabel()
        icon_manager.set_label_icon(
            title_icon, 
            'settings', 
            size=int(DesignSystem.ICON_SIZE_LG)
        )
        title_layout.addWidget(title_icon)
        
        title_label = QLabel("¿Qué componente deseas conservar?")
        title_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # ButtonGroup
        self.mode_buttons = QButtonGroup(self)
        
        # Cards layout
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(int(DesignSystem.SPACE_12))
        
        # Modos disponibles
        modes = [
            (CleanupMode.KEEP_IMAGE, 'image', 'Conservar imágenes (JPG)', 
             'Se eliminarán los videos MOV asociados. Recomendado para ahorrar espacio manteniendo las fotos.'),
            (CleanupMode.KEEP_VIDEO, 'video', 'Conservar videos (MOV)', 
             'Se eliminarán las imágenes JPG asociadas. Útil si prefieres mantener el movimiento/audio.')
        ]
        
        for idx, (mode, icon_name, title, description) in enumerate(modes):
            is_selected = (mode == self.selected_mode)
            
            # Crear RadioButton
            radio = QRadioButton()
            radio.setChecked(is_selected)
            radio.toggled.connect(
                lambda checked, m=mode: self._on_mode_card_changed(m) if checked else None
            )
            self.mode_buttons.addButton(radio, idx)
            
            # Crear card
            card = self._create_selection_card(
                f"mode-{mode.value}",
                icon_name,
                title,
                description,
                is_selected,
                radio
            )
            cards_layout.addWidget(card)
        
        layout.addLayout(cards_layout)
        
        return frame

    def _on_mode_card_changed(self, new_mode):
        """Maneja el cambio de modo desde las cards."""
        if new_mode == self.selected_mode:
            return
        
        self.selected_mode = new_mode
        self._update_button_text()

    def _on_mode_changed(self, button):
        modes = {0: CleanupMode.KEEP_IMAGE, 1: CleanupMode.KEEP_VIDEO}
        self.selected_mode = modes[self.mode_buttons.id(button)]
        self._update_button_text()

    def accept(self):
        # Construir lista de archivos a eliminar según el modo seleccionado
        groups = self.analysis.groups  # Dataclass attribute
        files_to_delete = []
        
        if self.selected_mode == CleanupMode.KEEP_IMAGE:
            # Eliminar videos, mantener imágenes
            files_to_delete = [group.video_path for group in groups]
        elif self.selected_mode == CleanupMode.KEEP_VIDEO:
            # Eliminar imágenes, mantener videos
            files_to_delete = [group.image_path for group in groups]
        
        self.accepted_plan = self.build_accepted_plan({
            'mode': self.selected_mode,
            'dry_run': self.dry_run_checkbox.isChecked(),
            'files_to_delete': files_to_delete,
            'groups': groups
        })
        super().accept()
