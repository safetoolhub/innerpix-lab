from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QVBoxLayout as QVLayout,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt
from services.live_photo_cleaner import CleanupMode
from utils.format_utils import format_size
from ui.styles.design_system import DesignSystem
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
        layout.setContentsMargins(0, 0, 0, int(DesignSystem.SPACE_20))

        # Header compacto integrado con métricas inline
        header = self._create_compact_header_with_metrics(
            icon_name='camera',
            title='Live Photos detectadas',
            description='Live Photos de iPhone (JPG + MOV). Selecciona qué componente conservar.',
            metrics=[
                {
                    'value': str(self.analysis.live_photos_found),
                    'label': 'Live Photos',
                    'color': DesignSystem.COLOR_PRIMARY
                },
                {
                    'value': format_size(self.analysis.total_space),
                    'label': 'Espacio',
                    'color': DesignSystem.COLOR_WARNING
                }
            ]
        )
        layout.addWidget(header)

        # Contenedor con margen para el resto del contenido
        from PyQt6.QtWidgets import QWidget
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(int(DesignSystem.SPACE_16))
        content_layout.setContentsMargins(
            int(DesignSystem.SPACE_24),
            int(DesignSystem.SPACE_12),
            int(DesignSystem.SPACE_24),
            0
        )
        layout.addWidget(content_container, 0)  # Sin stretch para evitar expansión vertical

        # Selector de modo con cards
        self.mode_selector = self._create_mode_selector()
        content_layout.addWidget(self.mode_selector)

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
        content_layout.addWidget(options_group)

        # Botones
        live_photos_found = self.analysis.live_photos_found
        ok_enabled = live_photos_found > 0
        ok_text = None if ok_enabled else "No hay Live Photos para limpiar"
        self.buttons = self.make_ok_cancel_buttons(ok_text=ok_text, ok_enabled=ok_enabled)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        # If there are items, update text according to mode
        if live_photos_found > 0:
            self._update_button_text()
        content_layout.addWidget(self.buttons)
        
        # Stretch para mantener el header arriba cuando se maximiza
        layout.addStretch()
        
        # Aplicar estilo global de tooltips
        self.setStyleSheet(DesignSystem.get_tooltip_style())

    def _create_mode_selector(self):
        """Crea selector de modo usando el método centralizado de BaseDialog."""
        modes = [
            (CleanupMode.KEEP_IMAGE, 'image', 'Conservar imágenes (JPG)', 
             'Se eliminarán los videos MOV asociados. Recomendado para ahorrar espacio manteniendo las fotos.'),
            (CleanupMode.KEEP_VIDEO, 'video', 'Conservar videos (MOV)', 
             'Se eliminarán las imágenes JPG asociadas. Útil si prefieres mantener el movimiento/audio.')
        ]
        
        return self._create_option_selector(
            title="¿Qué componente deseas conservar?",
            title_icon='settings',
            options=modes,
            selected_value=self.selected_mode,
            on_change_callback=self._on_mode_card_changed
        )

    def _on_mode_card_changed(self, new_mode):
        """Maneja el cambio de modo desde las cards."""
        if new_mode == self.selected_mode:
            return
        
        self.selected_mode = new_mode
        
        # Actualizar estilos de las cards usando el método centralizado
        if hasattr(self, 'mode_selector'):
            self._update_option_selector_styles(
                self.mode_selector,
                [CleanupMode.KEEP_IMAGE, CleanupMode.KEEP_VIDEO],
                self.selected_mode
            )
        
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
