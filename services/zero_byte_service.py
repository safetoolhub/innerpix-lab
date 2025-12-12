"""
Servicio para detectar y eliminar archivos de 0 bytes.
Refactorizado para usar MetadataCache y ResultTypes genéricos.
"""
from pathlib import Path
from typing import List, Optional

from services.base_service import BaseService, ProgressCallback
from services.result_types import ZeroByteAnalysisResult, ZeroByteDeletionResult
from services.metadata_cache import MetadataCache
from utils.logger import log_section_header_relevant, log_section_footer_relevant
from utils.file_utils import delete_file_securely


class ZeroByteService(BaseService):
    """
    Servicio para gestionar archivos de 0 bytes.
    """
    
    def __init__(self):
        super().__init__('ZeroByteService')

    def analyze(self, 
                metadata_cache: MetadataCache, 
                progress_callback: Optional[ProgressCallback] = None,
                **kwargs) -> ZeroByteAnalysisResult:
        """
        Busca archivos de 0 bytes usando la caché de metadatos.
        
        Args:
            metadata_cache: Caché con metadatos de archivos
            progress_callback: Callback de progreso
            
        Returns:
            ZeroByteAnalysisResult
        """
        # Ya no validamos directorio aqui, asumimos que metadata_cache está poblada
        self.logger.info(f"Buscando archivos de 0 bytes en caché ({len(metadata_cache.get_all_files())} archivos)")
        
        zero_byte_files = []
        all_files = metadata_cache.get_all_files()
        total = len(all_files)
        
        for i, meta in enumerate(all_files):
            if meta.size == 0:
                zero_byte_files.append(meta.path)
            
            # Reportar progreso periódicamente
            if self._should_report_progress(i, interval=5000): # Intervalo alto, es memoria rapida
                 if not self._report_progress(progress_callback, i, total, "Filtrando archivos vacíos..."):
                     break
                     
        self.logger.info(f"Encontrados {len(zero_byte_files)} archivos de 0 bytes")
        
        return ZeroByteAnalysisResult(
            files=zero_byte_files,
            items_count=len(zero_byte_files)
        )

    def execute(self, 
                analysis_result: ZeroByteAnalysisResult,
                dry_run: bool = False,
                create_backup: bool = True,
                progress_callback: Optional[ProgressCallback] = None,
                **kwargs) -> ZeroByteDeletionResult:
        """
        Elimina los archivos identificados en el análisis.
        """
        files_to_delete = analysis_result.files
        
        # Usar template method _execute_operation de BaseService
        return self._execute_operation(
            files=files_to_delete,
            operation_name='zero_byte_deletion',
            execute_fn=lambda dr: self._do_zero_byte_deletion(
                files_to_delete, 
                dr, 
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
        """
        result = ZeroByteDeletionResult(dry_run=dry_run)
        total = len(files_to_delete)
        
        mode = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(self.logger, "ELIMINACIÓN DE ARCHIVOS VACÍOS", mode=mode)
        self.logger.info(f"*** Archivos a procesar: {total}")
        
        files_affected = []
        items_processed = 0
        
        for i, file_path in enumerate(files_to_delete):
            if not self._report_progress(
                progress_callback,
                i,
                total,
                f"{'[Simulación] Eliminaría' if dry_run else 'Eliminando'}\n{file_path.name}"
            ):
                break
            
            try:
                # Obtener extensión para log
                file_extension = file_path.suffix.upper().lstrip('.')
                file_type = file_extension if file_extension else 'UNKNOWN'
                
                # Intentar obtener fecha (opcional, para log)
                # Podríamos sacarla de metadata_cache si la pasamos, pero aqui acceso a disco es OK
                file_date_str = "unknown" # Simplificado para evitar import circular o lecturas extra
                
                # Formato de log estandarizado
                log_type = "FILE_DELETED_SIMULATION" if dry_run else "FILE_DELETED"
                log_msg = (
                    f"{log_type}: {file_path} | Size: 0 B | "
                    f"Type: {file_type}"
                )
                
                if dry_run:
                    items_processed += 1
                    files_affected.append(file_path)
                    self.logger.info(log_msg)
                else:
                    if delete_file_securely(file_path):
                        items_processed += 1
                        files_affected.append(file_path)
                        self.logger.info(log_msg)
                    else:
                        result.add_error(f"No se pudo eliminar: {file_path}")
                        
            except Exception as e:
                result.add_error(f"Error procesando {file_path}: {e}")
        
        result.items_processed = items_processed
        result.files_affected = files_affected
        
        # Usar _format_operation_summary de BaseService
        summary = self._format_operation_summary(
            "Eliminación de archivos vacíos",
            items_processed,
            space_amount=0,  # Son archivos de 0 bytes
            dry_run=dry_run
        )
        
        result.message = summary
        log_section_footer_relevant(self.logger, summary)
        
        self._report_progress(progress_callback, total, total, "Operación completada")
            
        return result

