"""
Eliminador de HEIC Duplicados
Refactorizado para usar MetadataCache.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple, Any
from collections import defaultdict

from utils.file_utils import validate_file_exists
from utils.date_utils import get_date_from_file
from services.result_types import HeicAnalysisResult, HeicExecutionResult, DuplicatePair, AnalysisResult
from services.base_service import BaseService, BackupCreationError, ProgressCallback
from services.file_metadata_repository_cache import FileInfoRepositoryCache
from config import Config
from utils.logger import (
    log_section_header_discrete,
    log_section_footer_discrete,
    log_section_header_relevant,
    log_section_footer_relevant
)


class HeicService(BaseService):
    """
    Servicio de HEIC - Compara archivos HEIC con sus equivalentes JPG
    
    Hereda de BaseService para logging estandarizado.
    """
    
    def __init__(self):
        super().__init__("HeicService")
        self.backup_dir = None
        
        # Configuración
        self.heic_extensions = {'.heic', '.heif'}
        self.jpg_extensions = {'.jpg', '.jpeg'}
        
        # Estadísticas
        self.stats = {
            'heic_files_found': 0,
            'jpg_files_found': 0,
            'duplicate_pairs_found': 0,
            'total_heic_size': 0,
            'total_jpg_size': 0,
            'potential_savings': 0,
            'rejected_by_time_diff': 0
        }
    
    def analyze(
        self,
        progress_callback: Optional[ProgressCallback] = None,
        validate_dates: bool = True,
        **kwargs
    ) -> HeicAnalysisResult:
        """
        Analiza duplicados HEIC/JPG usando FileInfoRepository.
        
        Args:
            progress_callback: Callback
            validate_dates: Si validar fechas
            
        Returns:
            HeicAnalysisResult con análisis detallado
        """
        # Obtener FileInfoRepositoryCache
        repo = FileInfoRepositoryCache.get_instance()
        
        log_section_header_discrete(self.logger, "ANÁLISIS DE DUPLICADOS HEIC/JPG")
        self.logger.info(f"Usando FileInfoRepositoryCache con {repo.get_file_count()} archivos")
        self.logger.info(f"Validación de fechas: {'ACTIVADA' if validate_dates else 'DESACTIVADA'}")
        
        if validate_dates:
            self.logger.info(f"Tolerancia máxima: {Config.MAX_TIME_DIFFERENCE_SECONDS}s")
        
        self._reset_stats()
        
        results = {
            'duplicate_pairs': [],
            'orphan_heic': [],
            'orphan_jpg': [],
            'total_heic_files': 0,
            'total_jpg_files': 0,
            'total_duplicates': 0,
            'potential_savings_keep_jpg': 0,
            'potential_savings_keep_heic': 0,
            'by_directory': defaultdict(int)
        }
        
        # Obtener todos los archivos del repo
        all_files = repo.get_all_files()
        total_files = len(all_files)
        
        # Estructura optimizada: dict[Path, dict[str, FileMetadata]]
        heic_by_dir: Dict[Path, Dict[str, FileMetadata]] = defaultdict(dict)
        jpg_by_dir: Dict[Path, Dict[str, FileMetadata]] = defaultdict(dict)
        
        total_heic_count = 0
        total_jpg_count = 0
        
        # Clasificar archivos
        for i, meta in enumerate(all_files):
            if i % 1000 == 0 and not self._report_progress(progress_callback, i, total_files, "Clasificando archivos HEIC/JPG"):
                return self._create_empty_result()
                
            extension = meta.extension
            base_name = meta.path.stem
            parent_dir = meta.path.parent
            
            if extension in self.heic_extensions:
                heic_by_dir[parent_dir][base_name] = meta
                self.stats['total_heic_size'] += meta.fs_size
                total_heic_count += 1
            elif extension in self.jpg_extensions:
                jpg_by_dir[parent_dir][base_name] = meta
                self.stats['total_jpg_size'] += meta.fs_size
                total_jpg_count += 1
        
        results['total_heic_files'] = total_heic_count
        results['total_jpg_files'] = total_jpg_count
        self.stats['heic_files_found'] = total_heic_count
        self.stats['jpg_files_found'] = total_jpg_count
        
        # Emparejar archivos
        duplicate_pairs = []
        matched_heic: Set[Path] = set()
        matched_jpg: Set[Path] = set()
        
        processed_dirs = 0
        total_dirs = len(heic_by_dir)
        
        for directory, heic_dict in heic_by_dir.items():
            processed_dirs += 1
            if processed_dirs % 10 == 0: # Report less frequently
                 self._report_progress(progress_callback, processed_dirs, total_dirs, "Emparejando archivos...")

            if directory not in jpg_by_dir:
                continue
            
            jpg_dict = jpg_by_dir[directory]
            
            # Bases comunes
            common_bases = set(heic_dict.keys()) & set(jpg_dict.keys())
            
            for base_name in common_bases:
                heic_meta = heic_dict[base_name]
                jpg_meta = jpg_dict[base_name]
                
                try:
                    # Obtener fechas
                    # Intentar usar metadata cacheada si tuviera exif, o get_date_from_file (que abre archivo)
                    # Para optimizar, podríamos confiar en mtime si no hay exif, pero heic/jpg suelen requerir exif para ser precisos.
                    # Asumimos que get_date_from_file maneja su propia cache o lectura.
                    
                    # TODO: Optimizar lectura de fecha si es posible
                    heic_date_raw = get_date_from_file(heic_meta.path)
                    heic_date = heic_date_raw or datetime.fromtimestamp(heic_meta.fs_mtime)
                    heic_source = "EXIF" if heic_date_raw else "filesystem"
                    
                    jpg_date_raw = get_date_from_file(jpg_meta.path)
                    jpg_date = jpg_date_raw or datetime.fromtimestamp(jpg_meta.fs_mtime)
                    jpg_source = "EXIF" if jpg_date_raw else "filesystem"
                    
                    # Validación de fecha
                    if validate_dates:
                        time_diff = abs(heic_date - jpg_date)
                        if time_diff.total_seconds() > Config.MAX_TIME_DIFFERENCE_SECONDS:
                            self.logger.warning(f"Par rechazado por tiempo {base_name}: diff {time_diff.total_seconds()}s")
                            self.stats['rejected_by_time_diff'] += 1
                            continue
                            
                    # Crear par
                    duplicate_pair = DuplicatePair(
                        heic_path=heic_meta.path,
                        jpg_path=jpg_meta.path,
                        base_name=base_name,
                        heic_size=heic_meta.fs_size,
                        jpg_size=jpg_meta.fs_size,
                        directory=directory,
                        heic_date=heic_date,
                        jpg_date=jpg_date
                    )
                    
                    duplicate_pairs.append(duplicate_pair)
                    matched_heic.add(heic_meta.path)
                    matched_jpg.add(jpg_meta.path)
                    
                    results['potential_savings_keep_jpg'] += heic_meta.fs_size
                    results['potential_savings_keep_heic'] += jpg_meta.fs_size
                    results['by_directory'][str(directory)] += 1
                    
                except Exception as e:
                    self.logger.warning(f"Error procesando par {base_name}: {e}")

        results['duplicate_pairs'] = duplicate_pairs
        results['total_duplicates'] = len(duplicate_pairs)
        self.stats['duplicate_pairs_found'] = len(duplicate_pairs)
        self.stats['potential_savings'] = results['potential_savings_keep_jpg']
        
        # Encontrar huérfanos
        for directory, heic_dict in heic_by_dir.items():
            for base_name, meta in heic_dict.items():
                if meta.path not in matched_heic:
                    results['orphan_heic'].append(meta.path)
        
        for directory, jpg_dict in jpg_by_dir.items():
            for base_name, meta in jpg_dict.items():
                if meta.path not in matched_jpg:
                    results['orphan_jpg'].append(meta.path)
                    
        log_section_footer_discrete(self.logger, f"Análisis completado: {len(duplicate_pairs)} pares")
        
        return HeicAnalysisResult(
            duplicate_pairs=duplicate_pairs,
            heic_files=results['total_heic_files'],
            jpg_files=results['total_jpg_files'],
            potential_savings_keep_jpg=results['potential_savings_keep_jpg'],
            potential_savings_keep_heic=results['potential_savings_keep_heic']
        )

    def execute(
        self,
        analysis_result: HeicAnalysisResult,
        dry_run: bool = False,
        create_backup: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
        **kwargs
    ) -> HeicExecutionResult:
        """
        Ejecuta eliminación HEIC/JPG.
        
        Args:
            analysis_result: Resultado del análisis
            dry_run: Simulación
            create_backup: Backup
            progress_callback: Progreso
            **kwargs: 'keep_format' ('jpg' o 'heic')
        """
        keep_format = kwargs.get('keep_format', 'jpg')
        duplicate_pairs = analysis_result.duplicate_pairs
        
        if not duplicate_pairs:
             return HeicExecutionResult(
                success=True,
                files_deleted=0,
                space_freed=0,
                message='No hay archivos duplicados para eliminar',
                format_kept=keep_format,
                dry_run=dry_run
            )
            
        # Determinar archivos a eliminar
        if keep_format.lower() == 'jpg':
            files_to_delete = [pair.heic_path for pair in duplicate_pairs]
        else:
            files_to_delete = [pair.jpg_path for pair in duplicate_pairs]
            
        return self._execute_operation(
            files=files_to_delete,
            operation_name='heic_removal',
            execute_fn=lambda dry: self._do_heic_cleanup(
                duplicate_pairs,
                keep_format,
                dry,
                progress_callback
            ),
            create_backup=create_backup,
            dry_run=dry_run,
            progress_callback=progress_callback
        )

    def _do_heic_cleanup(
        self,
        duplicate_pairs: List[DuplicatePair],
        keep_format: str,
        dry_run: bool,
        progress_callback: Optional[ProgressCallback]
    ) -> HeicExecutionResult:
        """Lógica real de eliminación (internal)"""
        
        mode = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(self.logger, "ELIMINACIÓN DE DUPLICADOS HEIC/JPG", mode=mode)
        
        results = HeicExecutionResult(success=True, format_kept=keep_format, dry_run=dry_run)
        total_pairs = len(duplicate_pairs)
        
        files_deleted_list = []
        
        for idx, pair in enumerate(duplicate_pairs):
             if not self._report_progress(progress_callback, idx+1, total_pairs, f"Procesando par {idx+1}/{total_pairs}"):
                 break
                 
             file_to_delete = pair.heic_path if keep_format.lower() == 'jpg' else pair.jpg_path
             file_to_keep = pair.jpg_path if keep_format.lower() == 'jpg' else pair.heic_path
             file_size = pair.heic_size if keep_format.lower() == 'jpg' else pair.jpg_size
             
             try:
                 if not file_to_delete.exists():
                     self.logger.warning(f"Archivo no encontrado: {file_to_delete}")
                     continue
                 
                 from utils.format_utils import format_size
                 format_deleted = 'HEIC' if keep_format.lower() == 'jpg' else 'JPG'
                 
                 if dry_run:
                     results.simulated_files_deleted += 1
                     results.simulated_space_freed += file_size
                     files_deleted_list.append(str(file_to_delete))
                     self.logger.info(f"FILE_DELETED_SIMULATION: {file_to_delete} | Type: {format_deleted}")
                 else:
                     file_to_delete.unlink()
                     results.files_deleted += 1
                     results.space_freed += file_size
                     files_deleted_list.append(str(file_to_delete))
                     self.logger.info(f"FILE_DELETED: {file_to_delete} | Type: {format_deleted}")
                     
                     # Actualizar caché eliminando el archivo
                     from services.file_metadata_repository_cache import FileInfoRepositoryCache
                     repo = FileInfoRepositoryCache.get_instance()
                     repo.remove_file(file_to_delete)
                     
             except Exception as e:
                 err = f"Error eliminando {file_to_delete}: {e}"
                 results.add_error(err)
                 self.logger.error(err)

        # Set files_affected using files_deleted_list for generic compatibility
        results.files_affected = [Path(f) for f in files_deleted_list] if not dry_run else [] 
        # HeicExecutionResult inherits from ExecutionResult, so files_affected is available
        
        results.deleted_files = files_deleted_list # Backward compatibility

        # Resumen
        count = results.simulated_files_deleted if dry_run else results.files_deleted
        space = results.simulated_space_freed if dry_run else results.space_freed
        summary = self._format_operation_summary("Eliminación HEIC/JPG", count, space, dry_run)
        
        results.message = summary
        if results.backup_path:
            results.message += f"\n\nBackup: {results.backup_path}"
            
        log_section_footer_relevant(self.logger, summary)
        return results

    def _create_empty_result(self) -> HeicAnalysisResult:
        return HeicAnalysisResult(
            duplicate_pairs=[],
            heic_files=0,
            jpg_files=0,
            potential_savings_keep_jpg=0,
            potential_savings_keep_heic=0
        )

    def _reset_stats(self):
        for key in self.stats:
            self.stats[key] = 0
            
    def get_stats(self) -> Dict:
        return self.stats.copy()
