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
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import QPushButton, QLabel
from PyQt6.QtCore import QSize


class IconManager:
    """Gestor centralizado de iconos Material Design usando QtAwesome.
    
    Proporciona un sistema de caché y métodos convenientes para aplicar
    iconos a widgets sin afectar las fuentes de texto de la aplicación.
    """
    
    # Diccionario de mapeo: nombre lógico → nombre de icono Material Design en QtAwesome
    ICON_MAP = {
        # Top Bar - Acciones principales
        'settings': 'mdi6.cog',
        'info': 'mdi6.information',
        'about': 'mdi6.information-outline',
        
        # Estados y notificaciones
        'warning': 'mdi6.alert',
        'error': 'mdi6.alert-circle',
        'success': 'mdi6.check-circle',
        'check': 'mdi6.check',
        'close': 'mdi6.close',
        'cancel': 'mdi6.close-circle',
        
        # Navegación y acciones de archivos
        'folder': 'mdi6.folder',
        'folder-open': 'mdi6.folder-open',
        'file': 'mdi6.file',
        'search': 'mdi6.magnify',
        'refresh': 'mdi6.refresh',
        'delete': 'mdi6.delete',
        'save': 'mdi6.content-save',
        'backup': 'mdi6.backup-restore',
        
        # Estadísticas y métricas
        'stats': 'mdi6.chart-bar',
        'chart': 'mdi6.chart-line',
        'timer': 'mdi6.timer',
        'clock': 'mdi6.clock-outline',
        
        # Tipos de archivos multimedia
        'image': 'mdi6.image',
        'camera': 'mdi6.camera',
        'video': 'mdi6.video',
        'film': 'mdi6.movie',
        'photo': 'mdi6.image-outline',
        'picture': 'mdi6.image-multiple',
        
        # Live Photos y duplicados
        'live-photo': 'mdi6.camera-burst',
        'duplicate': 'mdi6.content-duplicate',
        'duplicate-exact': 'mdi6.equal',
        'duplicate-similar': 'mdi6.image-search',
        'eye': 'mdi6.eye',
        
        # Organización
        'organize': 'mdi6.folder-move',
        'move': 'mdi6.folder-arrow-right',
        'sort': 'mdi6.sort',
        
        # Renombrado
        'rename': 'mdi6.rename-box',
        'edit': 'mdi6.pencil',
        'format': 'mdi6.format-text',
        
        # HEIC
        'heic': 'mdi6.file-image',
        'jpg': 'mdi6.file-jpg-box',
        'format-image': 'mdi6.image-filter-hdr',
        
        # Progreso y loading
        'loading': 'mdi6.loading',
        'progress': 'mdi6.progress-clock',
        'hourglass': 'mdi6.timer-sand',
        
        # Opciones y configuración
        'config': 'mdi6.cog-outline',
        'settings-outline': 'mdi6.cog-outline',
        'options': 'mdi6.tune',
        
        # Acciones de usuario
        'play': 'mdi6.play',
        'stop': 'mdi6.stop',
        'pause': 'mdi6.pause',
        
        # Directorio y navegación
        'home': 'mdi6.home',
        'up': 'mdi6.arrow-up',
        'down': 'mdi6.arrow-down',
        'left': 'mdi6.arrow-left',
        'right': 'mdi6.arrow-right',
        
        # Aplicación
        'app': 'mdi6.movie-open',
        'logo': 'mdi6.movie-open',
        
        # Ayuda e información
        'help': 'mdi6.help-circle',
        'lightbulb': 'mdi6.lightbulb-on',
        'tooltip': 'mdi6.tooltip-text',
        
        # Targets y objetivos
        'target': 'mdi6.target',
        'bullseye': 'mdi6.bullseye',
        
        # Discos y almacenamiento
        'disk': 'mdi6.harddisk',
        'storage': 'mdi6.database',
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
        """
        icon = self.get_icon(icon_name, color=color)
        pixmap = icon.pixmap(QSize(size, size))
        label.setPixmap(pixmap)
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
        label = QLabel()
        self.set_label_icon(label, icon_name, color=color, size=size)
        return label
    
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
            'settings', 'info', 'warning', 'error', 'success',
            'folder', 'file', 'search', 'refresh', 'delete',
            'image', 'video', 'camera', 'check', 'close'
        ]
        
        for icon_name in common_icons:
            try:
                self.get_icon(icon_name, color=color)
            except ValueError:
                # Ignorar iconos que no existan
                pass


# Instancia global del gestor de iconos
icon_manager = IconManager()


# ============================================================================
# Funciones de conveniencia para uso rápido
# ============================================================================

def get_icon(name: str, color: Optional[str] = None, size: Optional[int] = None) -> QIcon:
    """Función de conveniencia para obtener un icono directamente.
    
    Args:
        name: Nombre lógico del icono
        color: Color del icono en formato hex
        size: Tamaño del icono en píxeles
    
    Returns:
        QIcon con el icono solicitado
    """
    return icon_manager.get_icon(name, color=color, size=size)


def set_button_icon(button: QPushButton, icon_name: str, color: Optional[str] = None, size: int = 16) -> None:
    """Función de conveniencia para aplicar icono a un botón.
    
    Args:
        button: QPushButton al que aplicar el icono
        icon_name: Nombre lógico del icono
        color: Color del icono
        size: Tamaño del icono
    """
    icon_manager.set_button_icon(button, icon_name, color=color, size=size)


def set_label_icon(label: QLabel, icon_name: str, color: Optional[str] = None, size: int = 16) -> None:
    """Función de conveniencia para aplicar icono a un label.
    
    Args:
        label: QLabel al que aplicar el icono
        icon_name: Nombre lógico del icono
        color: Color del icono
        size: Tamaño del icono
    """
    icon_manager.set_label_icon(label, icon_name, color=color, size=size)


def create_icon_label(icon_name: str, color: Optional[str] = None, size: int = 16) -> QLabel:
    """Función de conveniencia para crear un label con icono.
    
    Args:
        icon_name: Nombre lógico del icono
        color: Color del icono
        size: Tamaño del icono
    
    Returns:
        QLabel con el icono configurado
    """
    return icon_manager.create_icon_label(icon_name, color=color, size=size)
