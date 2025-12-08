"""
Servicio para detectar y eliminar archivos de 0 bytes.
"""
from pathlib import Path
from typing import List, Optional, Callable
import os

from services.result_types import ZeroByteAnalysisResult, ZeroByteDeletionResult
from utils.logger import (
    get_logger,
    log_section_header_relevant,
    log_section_footer_relevant
)
from utils.file_utils import delete_file_securely, create_backup_for_file

class ZeroByteService:
    """
    Servicio para gestionar archivos de 0 bytes.
    """
    
    def __init__(self):
        self.logger = get_logger('ZeroByteService')

    def analyze(self, 
                directory: Path, 
                progress_callback: Optional[Callable[[int, int, str], bool]] = None) -> ZeroByteAnalysisResult:
        """
        Busca archivos de 0 bytes en el directorio.
        
        Args:
            directory: Directorio a analizar
            progress_callback: Callback de progreso
            
        Returns:
            ZeroByteAnalysisResult con los archivos encontrados
        """
        self.logger.info(f"Buscando archivos de 0 bytes en: {directory}")
        
        zero_byte_files = []
        processed = 0
        
        # Recorrer directorio en streaming (sin bloquear)
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
                
            if progress_callback and processed % 100 == 0:
                if not progress_callback(processed, -1, "Buscando archivos vacíos..."):
                    break
            
            if file_path.stat().st_size == 0:
                zero_byte_files.append(file_path)
            
            processed += 1
            
        if progress_callback:
            progress_callback(processed, processed, "Búsqueda completada")
            
        return ZeroByteAnalysisResult(
            total_files=total_files,
            zero_byte_files_found=len(zero_byte_files),
            files=zero_byte_files
        )

    def execute(self, 
                files_to_delete: List[Path],
                create_backup: bool = True,
                dry_run: bool = False,
                progress_callback: Optional[Callable[[int, int, str], bool]] = None) -> ZeroByteDeletionResult:
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
        result = ZeroByteDeletionResult(dry_run=dry_run)
        total = len(files_to_delete)
        
        mode = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(self.logger, "ELIMINACIÓN DE ARCHIVOS VACÍOS", mode=mode)
        self.logger.info(f"*** Archivos a procesar: {total}")
        
        for i, file_path in enumerate(files_to_delete):
            if progress_callback:
                action = "[Simulación] Eliminaría" if dry_run else "Eliminando"
                progress_msg = f"{action}\n{file_path.name}"
                if not progress_callback(i, total, progress_msg):
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
                
                if dry_run:
                    result.simulated_files_deleted += 1
                    result.deleted_files.append(str(file_path))
                    
                    self.logger.info(
                        f"FILE_DELETED_SIMULATION: {file_path} | Size: 0 B | "
                        f"Type: {file_type} | Date: {file_date_str}"
                    )
                else:
                    # Aunque sean 0 bytes, respetamos la opción de backup si el usuario la pide
                    # (aunque un backup de un archivo de 0 bytes es otro archivo de 0 bytes)
                    if create_backup:
                        # Solo hacer backup si el archivo existe (podría haber sido borrado externamente)
                        if file_path.exists():
                            backup_path = create_backup_for_file(file_path)
                            if not result.backup_path and backup_path:
                                # Guardar la ruta del directorio de backup (padre del archivo backup)
                                result.backup_path = str(Path(backup_path).parent)
                    
                    if delete_file_securely(file_path):
                        result.files_deleted += 1
                        result.deleted_files.append(str(file_path))
                        
                        self.logger.info(
                            f"FILE_DELETED: {file_path} | Size: 0 B | "
                            f"Type: {file_type} | Date: {file_date_str}"
                        )
                    else:
                        result.add_error(f"No se pudo eliminar: {file_path}")
                        
            except Exception as e:
                result.add_error(f"Error procesando {file_path}: {e}")
        
        if dry_run:
            result.message = f"Simulación completada. Se eliminarían {result.simulated_files_deleted} archivos."
            summary = f"Simulación completada: {result.simulated_files_deleted} archivos se eliminarían"
        else:
            result.message = f"Se eliminaron {result.files_deleted} archivos correctamente."
            summary = f"Operación completada: {result.files_deleted} archivos eliminados"
        
        log_section_footer_relevant(self.logger, summary)
        
        if progress_callback:
            progress_callback(total, total, "Operación completada")
            
        return result

