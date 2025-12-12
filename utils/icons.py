"""
Icon Manager - Sistema centralizado de gestión de iconos con QtAwesome

Este módulo proporciona una interfaz unificada para gestionar iconos Material Design
en toda la aplicación usando QtAwesome, reemplazando el uso problemático de emojis.

Características:
- Sistema de caché para mejorar rendimiento
- Diccionario centralizado de mapeo de iconos
- Métodos helper para aplicar iconos a botones y labels
- Soporte para diferentes tamaños y colores
- Sin dependencia de fuentes de emojis
- Totalmente multiplataforma (Windows, Linux, macOS, Android, iOS)

Uso básico:
    from utils.icons import icon_manager
    
    # En un botón
    icon_manager.set_button_icon(button, 'settings')
    
    # En un label
    icon_manager.set_label_icon(label, 'info', size=16, color='#1e40af')
    
    # Obtener un QIcon directamente
    icon = icon_manager.get_icon('folder', color='#2563eb')
"""

import qtawesome as qta
from typing import Optional, Dict, Any
from PyQt6.QtGui import QIcon, QPixmap, QColor, QGuiApplication
from PyQt6.QtWidgets import QPushButton, QLabel, QToolButton
from PyQt6.QtCore import QSize, Qt


class IconManager:
    """Gestor centralizado de iconos Material Design usando QtAwesome.
    
    Proporciona un sistema de caché y métodos convenientes para aplicar
    iconos a widgets sin afectar las fuentes de texto de la aplicación.
    """
    
    # Diccionario de mapeo: nombre lógico → nombre de icono Material Design en QtAwesome
    ICON_MAP = {
        # Top Bar - Acciones principales
        'cog': 'mdi6.cog',
        'information': 'mdi6.information',
        'information-outline': 'mdi6.information-outline',
        
        # Estados y notificaciones
        'alert': 'mdi6.alert',
        'alert-circle': 'mdi6.alert-circle',
        'check': 'mdi6.check',
        'check-circle': 'mdi6.check-circle',
        'checkbox-marked': 'mdi6.checkbox-marked',
        'checkbox-marked-circle': 'mdi6.checkbox-marked-circle',
        'shield': 'mdi6.shield',
        'shield-check': 'mdi6.shield-check',
        'close': 'mdi6.close',
        'close-circle': 'mdi6.close-circle',
        'pause-circle': 'mdi6.pause-circle',
        'plus-circle': 'mdi6.plus-circle',
        
        # Navegación y acciones de archivos
        'folder': 'mdi6.folder',
        'folder-open': 'mdi6.folder-open',
        'folder-outline': 'mdi6.folder-outline',
        'folder-cog': 'mdi6.folder-cog',
        'folder-remove': 'mdi6.folder-remove',
        'folder-multiple': 'mdi6.folder-multiple',
        'file': 'mdi6.file',
        'file-document-outline': 'mdi6.file-document-outline',
        'file-x': 'mdi6.file-remove',
        'files': 'mdi6.file-multiple',
        'open-in-new': 'mdi6.open-in-new',
        'magnify': 'mdi6.magnify',
        'refresh': 'mdi6.refresh',
        'download': 'mdi6.download',
        'delete': 'mdi6.delete',
        'delete-sweep': 'mdi6.delete-sweep',
        'trash-alt': 'fa5s.trash-alt',
        'content-save': 'mdi6.content-save',
        'backup-restore': 'mdi6.backup-restore',
        'history': 'mdi6.history',
        
        # Estadísticas y métricas
        'chart-bar': 'mdi6.chart-bar',
        'chart-line': 'mdi6.chart-line',
        'timer': 'mdi6.timer',
        'clock-outline': 'mdi6.clock-outline',
        'ruler': 'mdi6.ruler',
        'update': 'mdi6.update',
        'map-marker': 'mdi6.map-marker',
        'arrow-expand': 'mdi6.arrow-expand',
        'arrow-collapse': 'mdi6.arrow-collapse',
        
        # Tipos de archivos multimedia
        'image': 'mdi6.image',
        'image-multiple': 'mdi6.image-multiple',
        'camera': 'mdi6.camera',
        'video': 'mdi6.video',
        'movie': 'mdi6.movie',
        'image-outline': 'mdi6.image-outline',
        'image-album': 'mdi6.image-album',
        
        # Live Photos y duplicados
        'camera-burst': 'mdi6.camera-burst',
        'content-duplicate': 'mdi6.content-duplicate',
        'content-copy': 'mdi6.content-copy',
        'equal': 'mdi6.equal',
        'image-search': 'mdi6.image-search',
        'eye': 'mdi6.eye',
        
        # Organización
        'folder-move': 'mdi6.folder-move',
        'folder-arrow-right': 'mdi6.folder-arrow-right',
        'sort': 'mdi6.sort',
        
        # Renombrado
        'rename-box': 'mdi6.rename-box',
        'rename-box-outline': 'mdi6.rename-box-outline',
        'pencil': 'mdi6.pencil',
        'format-text': 'mdi6.format-text',
        
        # HEIC
        'file-image': 'mdi6.file-image',
        'file-jpg-box': 'mdi6.file-jpg-box',
        'image-filter-hdr': 'mdi6.image-filter-hdr',
        
        # Progreso y loading
        'loading': 'mdi6.loading',
        'progress-clock': 'mdi6.progress-clock',
        'timer-sand': 'mdi6.timer-sand',
        
        # Opciones y configuración
        'cog-outline': 'mdi6.cog-outline',
        'tune': 'mdi6.tune',
        'filter-variant': 'mdi6.filter-variant',
        'auto-fix': 'mdi6.auto-fix',
        'flash': 'mdi6.flash',
        
        # Acciones de usuario
        'play': 'mdi6.play',
        'play-circle': 'mdi6.play-circle',
        'stop': 'mdi6.stop',
        'pause': 'mdi6.pause',
        'skip-previous': 'mdi6.skip-previous',
        'skip-next': 'mdi6.skip-next',
        
        # Directorio y navegación
        'home': 'mdi6.home',
        'arrow-up': 'mdi6.arrow-up',
        'arrow-down': 'mdi6.arrow-down',
        'arrow-left': 'mdi6.arrow-left',
        'arrow-right': 'mdi6.arrow-right',
        'chevron-left': 'mdi6.chevron-left',
        'chevron-right': 'mdi6.chevron-right',
        'chevron-down': 'mdi6.chevron-down',
        
        # Aplicación
        'movie-open': 'mdi6.movie-open',
        
        # Dispositivos
        'cellphone': 'mdi6.cellphone',
        'speedometer': 'mdi6.speedometer',
        'calendar-month': 'mdi6.calendar-month',
        'calendar-today': 'mdi6.calendar-today',
        'calendar-range': 'mdi6.calendar-range',
        'devices': 'mdi6.devices',
        
        # Ayuda e información
        'help-circle': 'mdi6.help-circle',
        'lightbulb-on': 'mdi6.lightbulb-on',
        'tooltip-text': 'mdi6.tooltip-text',
        
        # Targets y objetivos
        'target': 'mdi6.target',
        'bullseye': 'mdi6.bullseye',
        
        # Discos y almacenamiento
        'harddisk': 'mdi6.harddisk',
        'database': 'mdi6.database',
    }
    
    def __init__(self):
        """Inicializa el gestor con un sistema de caché vacío."""
        self._cache: Dict[str, QIcon] = {}
    
    def get_icon(
        self, 
        name: str, 
        color: Optional[str] = None,
        size: Optional[int] = None,
        scale_factor: float = 1.0
    ) -> QIcon:
        """Obtiene un icono Material Design por nombre lógico.
        
        Args:
            name: Nombre lógico del icono (ej: 'settings', 'folder')
            color: Color del icono en formato hex (ej: '#2563eb'). Por defecto None (negro)
            size: Tamaño del icono en píxeles. Por defecto None (usa tamaño del widget)
            scale_factor: Factor de escala adicional (1.0 = tamaño normal)
        
        Returns:
            QIcon con el icono Material Design solicitado
        
        Raises:
            ValueError: Si el nombre de icono no existe en el mapeo
        """
        # Validar que el icono existe
        if name not in self.ICON_MAP:
            raise ValueError(
                f"Icono '{name}' no encontrado. "
                f"Iconos disponibles: {', '.join(sorted(self.ICON_MAP.keys()))}"
            )
        
        # Crear clave de caché única
        cache_key = f"{name}_{color}_{size}_{scale_factor}"
        
        # Retornar desde caché si existe
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Obtener nombre real del icono en QtAwesome
        icon_name = self.ICON_MAP[name]
        
        # Preparar opciones para qtawesome
        options: Dict[str, Any] = {}
        if color:
            options['color'] = color
        if scale_factor != 1.0:
            options['scale_factor'] = scale_factor
        
        # Crear icono con qtawesome
        icon = qta.icon(icon_name, **options)
        
        # Guardar en caché
        self._cache[cache_key] = icon
        
        return icon
    
    def set_button_icon(
        self,
        button: QPushButton,
        icon_name: str,
        color: Optional[str] = None,
        size: int = 16
    ) -> None:
        """Aplica un icono Material Design a un botón.
        
        Args:
            button: QPushButton al que aplicar el icono
            icon_name: Nombre lógico del icono
            color: Color del icono en formato hex
            size: Tamaño del icono en píxeles
        """
        icon = self.get_icon(icon_name, color=color)
        button.setIcon(icon)
        button.setIconSize(QSize(size, size))
    
    def set_label_icon(
        self,
        label: QLabel,
        icon_name: str,
        color: Optional[str] = None,
        size: int = 16
    ) -> None:
        """Aplica un icono Material Design a un label.
        
        Este método convierte el icono en un QPixmap y lo establece en el label,
        evitando cualquier interferencia con la fuente del texto.
        
        Args:
            label: QLabel al que aplicar el icono
            icon_name: Nombre lógico del icono
            color: Color del icono en formato hex
            size: Tamaño del icono en píxeles
            
        Note:
            No establece el tamaño del label automáticamente para permitir
            que el layout y las políticas de tamaño del label se respeten.
            El pixmap se genera con devicePixelRatio para pantallas HiDPI.
        """
        icon = self.get_icon(icon_name, color=color)

        # Detectar device pixel ratio de la pantalla (HiDPI)
        try:
            screen = label.screen() if hasattr(label, 'screen') else QGuiApplication.primaryScreen()
            dpr = float(screen.devicePixelRatio()) if screen is not None else 1.0
        except Exception:
            dpr = 1.0

        # Crear pixmap con resolución física adecuada
        physical_size = QSize(max(1, int(size * dpr)), max(1, int(size * dpr)))
        pixmap = icon.pixmap(physical_size)

        # Si no conseguimos un pixmap a tamaño físico, intentar tamaño lógico
        if pixmap.isNull():
            pixmap = icon.pixmap(QSize(size, size))

        # Si sigue siendo nulo, crear un pixmap transparente de respaldo
        if pixmap.isNull():
            fallback = QPixmap(QSize(size, size))
            fallback.fill(QColor(0, 0, 0, 0))
            label.setPixmap(fallback)
            return

        # Algunos entornos/Qt pueden manejar devicePixelRatio internamente, pero
        # para evitar inconsistencias con QLabel.setScaledContents y distintos
        # backends, escalamos explícitamente el pixmap a su tamaño lógico
        # (size x size) usando SmoothTransformation.
        try:
            logical_pixmap = pixmap.scaled(QSize(size, size), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        except Exception:
            # En caso de que la API difiera, fallback a scaled without enums
            logical_pixmap = pixmap.scaled(size, size)

        # Asegurar DPR 1.0 en el pixmap final para evitar re-escalados inesperados
        try:
            logical_pixmap.setDevicePixelRatio(1.0)
        except Exception:
            pass

        label.setPixmap(logical_pixmap)
        # NO hacer setFixedSize aquí - permitir que el label controle su propio tamaño
    
    def create_icon_label(
        self,
        icon_name: str,
        color: Optional[str] = None,
        size: int = 16
    ) -> QLabel:
        """Crea un nuevo QLabel con un icono Material Design.
        
        Args:
            icon_name: Nombre lógico del icono
            color: Color del icono en formato hex
            size: Tamaño del icono en píxeles
        
        Returns:
            QLabel configurado con el icono
        """
        # Para evitar inconsistencias de rasterizado en HiDPI, creamos un
        # QToolButton plano que usa QIcon internamente. Esto permite que Qt
        # rasterice el icono a la resolución correcta (igual que en pestañas).
        btn = QToolButton()
        btn.setAutoRaise(True)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        btn.setIconSize(QSize(size, size))
        btn.setFixedSize(QSize(max(24, size + 6), max(24, size + 6)))
        btn.setStyleSheet("QToolButton { background: transparent; border: none; padding: 0px; }")
        # Aplicar icono usando la canalización de QIcon/QToolButton
        self.set_button_icon(btn, icon_name, color=color, size=size)
        return btn
    
    def clear_cache(self) -> None:
        """Limpia la caché de iconos.
        
        Útil si se cambia el tema de la aplicación o se necesita liberar memoria.
        """
        self._cache.clear()
    
    def get_cache_size(self) -> int:
        """Retorna el número de iconos en caché."""
        return len(self._cache)
    
    def preload_common_icons(self, color: Optional[str] = None) -> None:
        """Precarga iconos comunes en la caché para mejorar rendimiento.
        
        Args:
            color: Color por defecto para los iconos precargados
        """
        common_icons = [
            'cog', 'information', 'alert', 'alert-circle', 'check-circle',
            'folder', 'file', 'magnify', 'refresh', 'delete',
            'image', 'video', 'camera', 'check', 'close', 'plus-circle'
        ]
        
        for icon_name in common_icons:
            try:
                self.get_icon(icon_name, color=color)
            except ValueError:
                # Ignorar iconos que no existan
                pass


# Instancia global del gestor de iconos
icon_manager = IconManager()