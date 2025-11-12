"""
Clase base abstracta para todos los servicios de Pixaro Lab.

Proporciona funcionalidad común: logging estandarizado, gestión de backup,
y métodos template para operaciones consistentes.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Iterable, Callable, Union, Any, TypeAlias
from utils.logger import get_logger


# Type alias para callbacks de progreso estandarizados
ProgressCallback: TypeAlias = Callable[[int, int, str], Optional[bool]]
"""
Callback de progreso estandarizado para todas las operaciones.

Firma:
    callback(current: int, total: int, message: str) -> Optional[bool]

Args:
    current: Número de elementos procesados hasta ahora
    total: Total de elementos a procesar
    message: Mensaje descriptivo del progreso actual

Returns:
    - True o None: Continuar con la operación
    - False: Cancelar la operación inmediatamente

Example:
    >>> def my_progress(current: int, total: int, message: str) -> bool:
    ...     print(f"[{current}/{total}] {message}")
    ...     return True  # Continuar
    ...
    >>> service.execute(plan, progress_callback=my_progress)
"""


class BackupCreationError(Exception):
    """
    Excepción lanzada cuando falla la creación de backup.
    
    Esta excepción permite diferenciar entre errores de backup
    y otros tipos de errores en la ejecución de operaciones.
    """
    pass


class BaseService(ABC):
    """
    Clase base abstracta para todos los servicios.
    
    Proporciona:
    - Logger configurado por servicio
    - Gestión de backup_dir
    - Logging estandarizado con banners
    - Métodos de formateo de resumen
    - Convención de nomenclatura: analyze() + execute()
    
    Los servicios concretos deben heredar de esta clase e implementar
    sus métodos específicos de análisis y ejecución.
    
    Nomenclatura Recomendada (desde Nov 2025):
    ============================================
    - analyze(directory: Path, **kwargs) -> *AnalysisResult
      Analiza el directorio y genera un plan de operación.
      Reemplaza: analyze_directory(), analyze_*_duplicates(), detect_in_directory()
      
    - execute(analysis_result: AnalysisResult, **kwargs) -> *Result  
      Ejecuta la operación según el análisis previo.
      Reemplaza: execute_renaming(), execute_cleanup(), execute_deletion()
    
    Esta convención mejora:
    - Autocompletado consistente en IDEs
    - Documentación uniforme
    - Reducción de carga cognitiva para nuevos desarrolladores
    
    Los métodos antiguos se mantienen con @deprecated para compatibilidad.
    """
    
    def __init__(self, service_name: str):
        """
        Inicializa el servicio base.
        
        Args:
            service_name: Nombre del servicio para el logger
        """
        self.logger = get_logger(service_name)
        self.backup_dir: Optional[Path] = None
        self._cancelled = False
    
    def _report_progress(
        self,
        callback: Optional[ProgressCallback],
        current: int,
        total: int,
        message: str
    ) -> bool:
        """
        Helper estandarizado para reportar progreso de operaciones.
        
        Este método centraliza toda la lógica de callbacks de progreso,
        eliminando 3 patrones diferentes de manejo de callbacks.
        
        Características:
        - Verifica flag de cancelación antes de llamar al callback
        - Maneja excepciones en callbacks sin interrumpir operación
        - Soporta callbacks que retornan None (no cancelables)
        - Logging automático de cancelaciones
        
        Args:
            callback: Función de callback opcional (ver ProgressCallback)
            current: Número de elementos procesados
            total: Total de elementos a procesar
            message: Mensaje descriptivo del progreso
            
        Returns:
            True si debe continuar la operación, False si se canceló
            
        Example:
            >>> for i, file in enumerate(files):
            ...     if not self._report_progress(progress_callback, i, len(files), f"Procesando {file.name}"):
            ...         break  # Operación cancelada
            ...     # Procesar archivo...
        """
        # Si ya se canceló previamente, no continuar
        if self._cancelled:
            return False
        
        # Si no hay callback, continuar
        if callback is None:
            return True
        
        # Llamar al callback de forma segura
        try:
            result = callback(current, total, message)
            
            # Si el callback retorna explícitamente False, cancelar
            if result is False:
                self._cancelled = True
                self.logger.info(f"Operación cancelada por el usuario en {current}/{total}")
                return False
            
            # None o True: continuar
            return True
            
        except Exception as e:
            # No interrumpir operación por errores en callback
            self.logger.warning(f"Error en callback de progreso: {e}")
            return True
    
    def cancel(self):
        """
        Solicita cancelación de operación en curso.
        
        Este método puede ser llamado desde otro thread (ej: UI)
        para detener una operación larga. La cancelación es cooperativa:
        la operación debe verificar _report_progress() periódicamente.
        
        Example:
            >>> # Desde UI thread
            >>> service.cancel()
            >>> # La operación se detendrá en el siguiente _report_progress()
        """
        self._cancelled = True
        self.logger.info("Cancelación solicitada")
    
    def _create_backup_for_operation(
        self,
        files: Iterable[Union[Path, dict, Any]],
        operation_name: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Optional[Path]:
        """
        Crea backup estandarizado para cualquier operación.
        
        Este método centraliza la lógica de creación de backups,
        eliminando ~50 líneas de código duplicado por servicio.
        
        Características:
        - Encuentra automáticamente el directorio común entre archivos
        - Extrae rutas de diferentes estructuras (Path, dict, dataclass)
        - Genera nombres consistentes con metadata
        - Maneja errores de forma uniforme
        
        Args:
            files: Archivos a incluir en backup. Acepta:
                  - Path objects directamente
                  - Dicts con keys: 'original_path', 'path', 'source_path'
                  - Dataclasses con attrs: path, original_path, source_path
                  - Objetos con atributo 'heic_path' o 'jpg_path' (DuplicatePair)
            operation_name: Nombre de la operación (ej: 'renaming', 'deletion', 'heic_removal')
            progress_callback: Callback opcional para reportar progreso
            
        Returns:
            Path del backup creado, o None si no hay archivos
            
        Raises:
            BackupCreationError: Si el backup falla de forma crítica
            
        Example:
            >>> # Con lista de Path
            >>> backup = self._create_backup_for_operation(
            ...     [Path('file1.jpg'), Path('file2.jpg')],
            ...     'deletion'
            ... )
            
            >>> # Con plan de renombrado (dicts)
            >>> backup = self._create_backup_for_operation(
            ...     [{'original_path': Path('old.jpg')}, ...],
            ...     'renaming'
            ... )
        """
        from utils.file_utils import launch_backup_creation, to_path
        
        # Convertir iterador a lista y extraer Paths
        file_list = []
        for item in files:
            try:
                # to_path maneja Path, dict, dataclass, DuplicatePair, etc.
                file_path = to_path(
                    item, 
                    attr_names=('original_path', 'path', 'source_path', 'heic_path', 'jpg_path')
                )
                if file_path:
                    file_list.append(file_path)
            except Exception as e:
                self.logger.warning(f"No se pudo extraer path de {item}: {e}")
                continue
        
        if not file_list:
            self.logger.warning("No hay archivos para backup")
            return None
        
        # Encontrar directorio común
        base_dir = file_list[0].parent
        for file_path in file_list[1:]:
            try:
                base_dir = Path(os.path.commonpath([base_dir, file_path.parent]))
            except ValueError:
                # No hay path común (ej: diferentes drives en Windows)
                self.logger.warning(
                    f"No hay path común entre {base_dir} y {file_path.parent}, "
                    f"usando {base_dir}"
                )
                break
        
        # Crear backup
        try:
            backup_path = launch_backup_creation(
                file_list,
                base_dir,
                backup_prefix=f'backup_{operation_name}',
                progress_callback=progress_callback,
                metadata_name=f'{operation_name}_metadata.txt'
            )
            self.backup_dir = backup_path
            self.logger.info(f"Backup creado en: {backup_path}")
            return backup_path
        except Exception as e:
            error_msg = f"Fallo creando backup para {operation_name}: {e}"
            self.logger.error(error_msg)
            raise BackupCreationError(error_msg) from e
    
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
