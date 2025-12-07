from PyQt6.QtWidgets import (
    QVBoxLayout,
    QDialogButtonBox
)
from services.live_photos_service import CleanupMode
from utils.format_utils import format_size
from ui.styles.design_system import DesignSystem
from ui.styles.design_system import DesignSystem
from .base_dialog import BaseDialog


class LivePhotoCleanupDialog(BaseDialog):
    """Diálogo para limpieza de Live Photos"""

    def __init__(self, analysis, parent=None):
        super().__init__(parent)
        self.analysis = analysis  # Dataclass con atributos
        self.selected_mode = CleanupMode.KEEP_IMAGE
        self.accepted_plan = None
        self.init_ui()

    def _get_unique_files_to_delete_count(self, mode):
        """
        Calcula el número real de archivos únicos a eliminar según el modo.
        
        Esto aplica la misma lógica de deduplicación que el servicio:
        múltiples imágenes pueden compartir el mismo video.
        
        Args:
            mode: CleanupMode seleccionado
            
        Returns:
            Número de archivos únicos que se eliminarían
        """
        groups = self.analysis.groups
        if not groups:
            return 0
        
        seen_paths = set()
        
        if mode == CleanupMode.KEEP_IMAGE:
            # Contamos videos únicos (múltiples imágenes pueden compartir un video)
            for group in groups:
                seen_paths.add(str(group.video_path))
        elif mode == CleanupMode.KEEP_VIDEO:
            # Contamos imágenes únicas
            for group in groups:
                seen_paths.add(str(group.image_path))
        
        return len(seen_paths)

    def _calculate_space_for_mode(self, mode):
        """Calcula el espacio a liberar según el modo seleccionado"""
        groups = self.analysis.groups  # Dataclass attribute
        if not groups:
            return 0

        # Usar set para evitar contar el mismo archivo múltiples veces
        files_to_delete = {}
        
        if mode == CleanupMode.KEEP_IMAGE:
            for group in groups:
                video_key = str(group.video_path)
                if video_key not in files_to_delete:
                    files_to_delete[video_key] = group.video_size
        elif mode == CleanupMode.KEEP_VIDEO:
            for group in groups:
                image_key = str(group.image_path)
                if image_key not in files_to_delete:
                    files_to_delete[image_key] = group.image_size
        
        return sum(files_to_delete.values())

    def _update_button_text(self):
        """Actualiza el texto del botón según el modo seleccionado"""
        groups = self.analysis.groups  # Dataclass attribute
        if not groups:
            return
        
        unique_files_count = self._get_unique_files_to_delete_count(self.selected_mode)
        if unique_files_count > 0:
            space = self._calculate_space_for_mode(self.selected_mode)
            space_formatted = format_size(space)
            files_type = "videos" if self.selected_mode == CleanupMode.KEEP_IMAGE else "imágenes"
            self.ok_button.setText(f"Eliminar {unique_files_count} {files_type} ({space_formatted})")

    def init_ui(self):
        self.setWindowTitle("Limpieza de Live Photos")
        self.setModal(True)
        
        # Ajustar tamaño según si hay warning banner o no
        from config import Config
        if not Config.USE_VIDEO_METADATA:
            # Tamaño más grande cuando hay warning banner
            self.resize(700, 620)
            self.setMinimumHeight(540)
        else:
            # Tamaño normal sin warning
            self.resize(700, 500)
            self.setMinimumHeight(420)
            
        layout = QVBoxLayout(self)
        layout.setSpacing(int(DesignSystem.SPACE_16))
        layout.setContentsMargins(0, 0, 0, int(DesignSystem.SPACE_20))

        # Header compacto integrado con métricas inline
        # Mostrar el número de grupos detectados (no el número de archivos únicos)
        self.header_frame = self._create_compact_header_with_metrics(
            icon_name='camera',
            title='Live Photos detectadas',
            description='Live Photos de iPhone (Imagen + MOV). Selecciona qué componente conservar.',
            metrics=[
                {
                    'value': str(self.analysis.live_photos_found),
                    'label': 'Grupos',
                    'color': DesignSystem.COLOR_PRIMARY
                },
                {
                    'value': format_size(self._calculate_space_for_mode(self.selected_mode)),
                    'label': 'Recuperable',
                    'color': DesignSystem.COLOR_SUCCESS
                }
            ]
        )
        layout.addWidget(self.header_frame)
        
        # Warning sobre metadata de video desactivado
        if not Config.USE_VIDEO_METADATA:
            # Contenedor con margen para el warning banner
            from PyQt6.QtWidgets import QWidget
            warning_container = QWidget()
            warning_container_layout = QVBoxLayout(warning_container)
            warning_container_layout.setContentsMargins(
                int(DesignSystem.SPACE_24),
                int(DesignSystem.SPACE_12),
                int(DesignSystem.SPACE_24),
                0
            )
            warning_container_layout.setSpacing(0)
            
            warning_banner = self._create_warning_banner(
                title='Detección sin validación temporal',
                message='La extracción de metadata de video está desactivada. Los Live Photos se detectan '\
                        'solo por coincidencia de nombres, sin validar que las fechas de captura coincidan. '\
                        'Esto puede incluir falsos positivos.',
                action_text='Activar en Configuración',
                action_callback=self._open_settings
            )
            warning_container_layout.addWidget(warning_banner)
            layout.addWidget(warning_container)

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

        # Opciones de seguridad (método centralizado)
        security_options = self._create_security_options_section(
            show_backup=True,
            show_dry_run=True,
            backup_label="Crear backup antes de eliminar",
            dry_run_label="Modo simulación (no eliminar archivos realmente)"
        )
        content_layout.addWidget(security_options)

        # Botones con estilo Material Design
        live_photos_found = self.analysis.live_photos_found
        ok_enabled = live_photos_found > 0
        ok_text = None if ok_enabled else "No hay Live Photos para limpiar"
        self.buttons = self.make_ok_cancel_buttons(
            ok_text=ok_text,
            ok_enabled=ok_enabled,
            button_style='danger'
        )
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
            title_icon='cog',
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
        
        # Actualizar métrica de espacio recuperable en el header
        recoverable_space = self._calculate_space_for_mode(self.selected_mode)
        self._update_header_metric(self.header_frame, 'Recuperable', format_size(recoverable_space))
        
        self._update_button_text()

    def accept(self):
        # Construir dataclass de análisis con los archivos a eliminar según el modo seleccionado
        from services.result_types import LivePhotoCleanupAnalysisResult
        
        groups = self.analysis.groups  # Dataclass attribute
        files_to_delete = []
        files_to_keep = []
        
        if self.selected_mode == CleanupMode.KEEP_IMAGE:
            # Eliminar videos, mantener imágenes
            seen_delete_paths = set()
            for group in groups:
                # Deduplicate videos (multiple images might share one video)
                if str(group.video_path) not in seen_delete_paths:
                    files_to_delete.append({
                        'path': group.video_path,
                        'type': 'video',
                        'size': group.video_size,
                        'base_name': group.base_name
                    })
                    seen_delete_paths.add(str(group.video_path))
                
                # Always keep the image (unique per group usually, but no harm in adding)
                files_to_keep.append({
                    'path': group.image_path,
                    'type': 'image',
                    'size': group.image_size,
                    'base_name': group.base_name
                })
        elif self.selected_mode == CleanupMode.KEEP_VIDEO:
            # Eliminar imágenes, mantener videos
            seen_keep_paths = set()
            for group in groups:
                files_to_delete.append({
                    'path': group.image_path,
                    'type': 'image',
                    'size': group.image_size,
                    'base_name': group.base_name
                })
                
                # Deduplicate videos to keep
                if str(group.video_path) not in seen_keep_paths:
                    files_to_keep.append({
                        'path': group.video_path,
                        'type': 'video',
                        'size': group.video_size,
                        'base_name': group.base_name
                    })
                    seen_keep_paths.add(str(group.video_path))
        
        # Crear dataclass de análisis
        space_to_free = sum(f['size'] for f in files_to_delete)
        total_space = self.analysis.total_space
        
        cleanup_analysis = LivePhotoCleanupAnalysisResult(
            total_files=len(groups) * 2,
            live_photos_found=len(groups),
            files_to_delete=files_to_delete,
            files_to_keep=files_to_keep,
            space_to_free=space_to_free,
            total_space=total_space,
            cleanup_mode=self.selected_mode.value
        )
        
        # Pasar dataclass + parámetros por separado
        self.accepted_plan = {
            'analysis': cleanup_analysis,
            'create_backup': self.is_backup_enabled(),
            'dry_run': self.is_dry_run_enabled()
        }
        super().accept()
    
    def _open_settings(self):
        """Abre el diálogo de configuración en la pestaña Avanzado"""
        from .settings_dialog import SettingsDialog
        settings_dialog = SettingsDialog(self, initial_tab=2)  # 2 = Avanzado tab
        settings_dialog.exec()
