from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QGroupBox, QVBoxLayout as QVLayout,
    QRadioButton, QButtonGroup, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from services.live_photo_cleaner import CleanupMode
from utils.format_utils import format_size
from ui import ui_styles
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
        groups = getattr(self.analysis, 'groups', [])
        if not groups:
            return 0

        total_space = 0
        if mode == CleanupMode.KEEP_IMAGE:
            for group in groups:
                total_space += group['video_size']
        elif mode == CleanupMode.KEEP_VIDEO:
            for group in groups:
                total_space += group['image_size']
        return total_space

    def _update_button_text(self):
        """Actualiza el texto del botón según el modo seleccionado"""
        groups = getattr(self.analysis, 'groups', [])
        lp_found = len(groups)
        if lp_found > 0:
            space = self._calculate_space_for_mode(self.selected_mode)
            space_formatted = format_size(space)
            files_type = "videos" if self.selected_mode == CleanupMode.KEEP_IMAGE else "imágenes"
            self.ok_button.setText(f"Eliminar {lp_found} {files_type} ({space_formatted})")

    def init_ui(self):
        self.setWindowTitle("Limpieza de Live Photos")
        self.setModal(True)
        self.resize(650, 450)
        layout = QVBoxLayout(self)

        # Información introductoria
        info_label = QLabel(
            "Los Live Photos de iPhone contienen una imagen JPG y un video MOV con el mismo nombre.\n"
            "Selecciona qué componente deseas conservar:"
        )
        info_label.setStyleSheet(ui_styles.STYLE_INFO_HIGHLIGHT)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Modo de limpieza
        mode_group = QGroupBox("¿Qué deseas conservar?")
        mode_layout = QVLayout(mode_group)
        self.mode_buttons = QButtonGroup()

        r1 = QRadioButton("🖼️ Conservar imágenes (JPG)")
        r1.setChecked(True)
        self.mode_buttons.addButton(r1, 0)
        mode_layout.addWidget(r1)

        desc1 = QLabel(" → Se eliminarán los videos MOV asociados\n"
                       " → Recomendado para ahorrar espacio manteniendo las fotos")
        desc1.setStyleSheet(ui_styles.STYLE_DESC_SMALL_INDENT)
        mode_layout.addWidget(desc1)
        mode_layout.addSpacing(10)

        r2 = QRadioButton("🎥 Conservar videos (MOV)")
        self.mode_buttons.addButton(r2, 1)
        mode_layout.addWidget(r2)

        desc2 = QLabel(" → Se eliminarán las imágenes JPG asociadas\n"
                       " → Útil si prefieres mantener el movimiento/audio de Live Photos")
        desc2.setStyleSheet(ui_styles.STYLE_DESC_SMALL_INDENT)
        mode_layout.addWidget(desc2)

        self.mode_buttons.buttonClicked.connect(self._on_mode_changed)
        layout.addWidget(mode_group)

        # Estadísticas
        stats_group = QGroupBox("Información")
        stats_layout = QVLayout(stats_group)
        lp_found = getattr(self.analysis, 'total_groups', 0)
        total_space = getattr(self.analysis, 'total_size', 0)
        stats_label = QLabel(
            f"📱 Live Photos detectados: <b>{lp_found}</b><br>"
            f"💾 Espacio total ocupado: <b>{format_size(total_space)}</b>"
        )
        stats_label.setTextFormat(Qt.TextFormat.RichText)
        stats_layout.addWidget(stats_label)
        layout.addWidget(stats_group)

        # Opciones
        options_group = QGroupBox("⚙️ Opciones de Seguridad")
        options_group.setMinimumWidth(400)
        options_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        options_layout = QVLayout(options_group)

        # Backup checkbox (primero)
        self.add_backup_checkbox(options_layout, "💾 Crear backup antes de eliminar (Recomendado)")

        # Simulación checkbox (segundo)
        from PyQt6.QtWidgets import QCheckBox
        self.dry_run_checkbox = QCheckBox("🔍 Modo simulación (no eliminar archivos realmente)")
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
        ok_enabled = lp_found > 0
        ok_text = None if ok_enabled else "No hay Live Photos para limpiar"
        self.buttons = self.make_ok_cancel_buttons(ok_text=ok_text, ok_enabled=ok_enabled)
        self.ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        # If there are items, update text according to mode
        if lp_found > 0:
            self._update_button_text()
        layout.addWidget(self.buttons)

    def _on_mode_changed(self, button):
        modes = {0: CleanupMode.KEEP_IMAGE, 1: CleanupMode.KEEP_VIDEO}
        self.selected_mode = modes[self.mode_buttons.id(button)]
        self._update_button_text()

    def accept(self):
        # Preparamos el plan de limpieza asegurándonos de que las rutas son objetos Path
        files_to_delete = getattr(self.analysis, 'files_to_delete', [])
        files_to_keep = getattr(self.analysis, 'files_to_keep', [])
        
        self.accepted_plan = self.build_accepted_plan({
            'mode': self.selected_mode,
            'dry_run': self.dry_run_checkbox.isChecked(),
            'files_to_delete': (
                files_to_delete if self.selected_mode == CleanupMode.KEEP_IMAGE
                else files_to_keep
            )
        })
        super().accept()
