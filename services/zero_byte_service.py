"""
Servicio para detectar y eliminar archivos de 0 bytes.
"""
from pathlib import Path
from typing import List, Optional

from services.base_service import BaseService, ProgressCallback
from services.result_types import ZeroByteAnalysisResult, ZeroByteDeletionResult
from utils.logger import log_section_header_relevant, log_section_footer_relevant
from utils.file_utils import delete_file_securely


class ZeroByteService(BaseService):
    """
    Servicio para gestionar archivos de 0 bytes.
    """
    
    def __init__(self):
        super().__init__('ZeroByteService')

    def analyze(self, 
                directory: Path, 
                progress_callback: Optional[ProgressCallback] = None) -> ZeroByteAnalysisResult:
        """
        Busca archivos de 0 bytes en el directorio.
        
        Args:
            directory: Directorio a analizar
            progress_callback: Callback de progreso
            
        Returns:
            ZeroByteAnalysisResult con los archivos encontrados
        """
        # Validar directorio usando método de BaseService
        self._validate_directory(directory)
        
        self.logger.info(f"Buscando archivos de 0 bytes en: {directory}")
        
        zero_byte_files = []
        processed = 0
        
        # Recorrer directorio en streaming (sin bloquear)
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Usar _report_progress de BaseService
            if self._should_report_progress(processed):
                if not self._report_progress(
                    progress_callback, 
                    processed, 
                    -1, 
                    "Buscando archivos vacíos..."
                ):
                    break
            
            if file_path.stat().st_size == 0:
                zero_byte_files.append(file_path)
            
            processed += 1
        
        # Reporte final
        self._report_progress(
            progress_callback, 
            processed, 
            processed, 
            "Búsqueda completada"
        )
            
        return ZeroByteAnalysisResult(
            total_files=processed,
            files=zero_byte_files
        )

    def execute(self, 
                files_to_delete: List[Path],
                create_backup: bool = True,
                dry_run: bool = False,
                progress_callback: Optional[ProgressCallback] = None) -> ZeroByteDeletionResult:
        """
        Elimina los archivos especificados.
        
        Args:
            files_to_delete: Lista de archivos a eliminar
            create_backup: Si crear backup antes de eliminar (aunque sean 0 bytes, por consistencia)
            dry_run: Si es simulación
            progress_callback: Callback de progreso
            
        Returns:
            ZeroByteDeletionResult
        """
        # Usar template method _execute_operation de BaseService
        return self._execute_operation(
            files=files_to_delete,
            operation_name='zero_byte_deletion',
            execute_fn=lambda dry: self._do_zero_byte_deletion(
                files_to_delete, 
                dry, 
                progress_callback
            ),
            create_backup=create_backup,
            dry_run=dry_run,
            progress_callback=progress_callback
        )
    
    def _do_zero_byte_deletion(
        self,
        files_to_delete: List[Path],
        dry_run: bool,
        progress_callback: Optional[ProgressCallback]
    ) -> ZeroByteDeletionResult:
        """
        Lógica real de eliminación de archivos de 0 bytes.
        
        Args:
            files_to_delete: Archivos a eliminar
            dry_run: Si es simulación
            progress_callback: Callback de progreso
            
        Returns:
            ZeroByteDeletionResult con resultados de la operación
        """
        result = ZeroByteDeletionResult(dry_run=dry_run)
        total = len(files_to_delete)
        
        mode = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(self.logger, "ELIMINACIÓN DE ARCHIVOS VACÍOS", mode=mode)
        self.logger.info(f"*** Archivos a procesar: {total}")
        
        for i, file_path in enumerate(files_to_delete):
            # Usar _report_progress de BaseService
            if not self._report_progress(
                progress_callback,
                i,
                total,
                f"{'[Simulación] Eliminaría' if dry_run else 'Eliminando'}\n{file_path.name}"
            ):
                break
            
            try:
                # Obtener extensión del archivo para el tipo
                file_extension = file_path.suffix.upper().lstrip('.')
                file_type = file_extension if file_extension else 'UNKNOWN'
                
                # Obtener fecha del archivo
                from utils.date_utils import get_date_from_file
                try:
                    file_date = get_date_from_file(file_path, verbose=False)
                    file_date_str = file_date.strftime('%Y-%m-%d %H:%M:%S') if file_date else 'unknown'
                except Exception:
                    file_date_str = 'unknown'
                
                # Formato de log estandarizado
                log_type = "FILE_DELETED_SIMULATION" if dry_run else "FILE_DELETED"
                log_msg = (
                    f"{log_type}: {file_path} | Size: 0 B | "
                    f"Type: {file_type} | Date: {file_date_str}"
                )
                
                if dry_run:
                    result.simulated_files_deleted += 1
                    result.deleted_files.append(str(file_path))
                    self.logger.info(log_msg)
                else:
                    if delete_file_securely(file_path):
                        result.files_deleted += 1
                        result.deleted_files.append(str(file_path))
                        self.logger.info(log_msg)
                    else:
                        result.add_error(f"No se pudo eliminar: {file_path}")
                        
            except Exception as e:
                result.add_error(f"Error procesando {file_path}: {e}")
        
        # Usar _format_operation_summary de BaseService
        summary = self._format_operation_summary(
            "Eliminación de archivos vacíos",
            result.simulated_files_deleted if dry_run else result.files_deleted,
            space_amount=0,  # Son archivos de 0 bytes
            dry_run=dry_run
        )
        
        result.message = summary
        log_section_footer_relevant(self.logger, summary)
        
        # Reporte final
        self._report_progress(
            progress_callback,
            total,
            total,
            "Operación completada"
        )
            
        return result

