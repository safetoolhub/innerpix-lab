"""
Clase base abstracta para todos los servicios de Pixaro Lab.

Proporciona funcionalidad común: logging estandarizado, gestión de backup,
y métodos template para operaciones consistentes.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from utils.logger import get_logger


class BaseService(ABC):
    """
    Clase base abstracta para todos los servicios.
    
    Proporciona:
    - Logger configurado por servicio
    - Gestión de backup_dir
    - Logging estandarizado con banners
    - Métodos de formateo de resumen
    
    Los servicios concretos deben heredar de esta clase e implementar
    sus métodos específicos de análisis y ejecución.
    """
    
    def __init__(self, service_name: str):
        """
        Inicializa el servicio base.
        
        Args:
            service_name: Nombre del servicio para el logger
        """
        self.logger = get_logger(service_name)
        self.backup_dir: Optional[Path] = None
    
    def _log_section_header(self, title: str, mode: str = ""):
        """
        Logging estandarizado de encabezado con banner ASCII.
        
        Args:
            title: Título de la sección
            mode: Modo opcional (ej: "SIMULACIÓN", "ANÁLISIS")
        
        Example:
            self._log_section_header("INICIANDO RENOMBRADO", "SIMULACIÓN")
            # Resultado:
            # ================================================================================
            # *** [SIMULACIÓN] INICIANDO RENOMBRADO
            # ================================================================================
        """
        mode_label = f"[{mode.upper()}] " if mode else ""
        self.logger.info("=" * 80)
        self.logger.info(f"*** {mode_label}{title}")
        self.logger.info("=" * 80)
    
    def _log_section_footer(self, result_summary: str):
        """
        Logging estandarizado de cierre.
        
        Args:
            result_summary: Resumen del resultado
        
        Example:
            self._log_section_footer("Operación completada: 10 archivos procesados")
        """
        self.logger.info(f"*** {result_summary}")
        self.logger.info("=" * 80)
    
    def _format_operation_summary(
        self,
        operation_name: str,
        files_count: int,
        space_amount: int = 0,
        dry_run: bool = False
    ) -> str:
        """
        Genera mensaje de resumen estandarizado para operaciones.
        
        Args:
            operation_name: Nombre de la operación (ej: "Renombrado", "Eliminación")
            files_count: Cantidad de archivos procesados
            space_amount: Espacio liberado en bytes (opcional)
            dry_run: Si es simulación
        
        Returns:
            Mensaje formateado
        
        Example:
            >>> self._format_operation_summary("Eliminación", 10, 5242880, True)
            'Eliminación completado: 10 archivos se procesarían, 5.00 MB se liberarían'
        """
        from utils.format_utils import format_size
        
        mode_verb = "se procesarían" if dry_run else "procesados"
        
        if space_amount > 0:
            space_verb = "se liberarían" if dry_run else "liberados"
            return (
                f"{operation_name} completado: "
                f"{files_count} archivos {mode_verb}, "
                f"{format_size(space_amount)} {space_verb}"
            )
        else:
            return f"{operation_name} completado: {files_count} archivos {mode_verb}"
    
    def _handle_cancellation(self, executor=None):
        """
        Manejo estándar de cancelación de operaciones.
        
        Args:
            executor: ThreadPoolExecutor opcional a detener
        """
        self.logger.info("Operación cancelada por el usuario")
        if executor:
            executor.shutdown(wait=False, cancel_futures=True)
