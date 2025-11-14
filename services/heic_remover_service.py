"""
Eliminador de HEIC Duplicados
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass

from utils.file_utils import validate_file_exists
from services.result_types import HeicAnalysisResult, HeicDeletionResult
from services.base_service import BaseService, BackupCreationError, ProgressCallback
from config import Config
from utils.logger import (
    log_section_header_discrete,
    log_section_footer_discrete,
    log_section_header_relevant,
    log_section_footer_relevant
)


@dataclass
class DuplicatePair:
    """Representa un par de archivos duplicados (HEIC + JPG)"""
    
    heic_path: Path
    jpg_path: Path
    base_name: str
    heic_size: int
    jpg_size: int
    directory: Path
    heic_date: Optional[datetime] = None
    jpg_date: Optional[datetime] = None
    similarity_score: float = 1.0  # 1.0 = idénticos (mismo nombre base)
    
    def __post_init__(self):
        """Validaciones"""
        try:
            validate_file_exists(self.heic_path)
        except FileNotFoundError as e:
            raise ValueError(str(e))
        
        try:
            validate_file_exists(self.jpg_path)
        except FileNotFoundError as e:
            raise ValueError(str(e))
        
        # Las fechas ya vienen proporcionadas, no las recalculamos
    
    @property
    def total_size(self) -> int:
        """Tamaño total del par"""
        return self.heic_size + self.jpg_size
    
    @property
    def size_saving_keep_jpg(self) -> int:
        """Ahorro eliminando HEIC"""
        return self.heic_size
    
    @property
    def size_saving_keep_heic(self) -> int:
        """Ahorro eliminando JPG"""
        return self.jpg_size
    
    @property
    def time_difference(self) -> Optional[timedelta]:
        """Diferencia de tiempo entre archivos"""
        if self.heic_date and self.jpg_date:
            return abs(self.heic_date - self.jpg_date)
        return None
    
    def format_sizes(self) -> str:
        """Formatea tamaños para display"""
        def format_bytes(size):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        
        heic_str = format_bytes(self.heic_size)
        jpg_str = format_bytes(self.jpg_size)
        saving_str = format_bytes(self.heic_size)  # Asumiendo que eliminamos HEIC
        return f"HEIC: {heic_str}, JPG: {jpg_str}, Ahorro: {saving_str}"


class HEICRemover(BaseService):
    """
    Eliminador de HEIC Duplicados - Compara archivos HEIC con sus equivalentes JPG
    
    Hereda de BaseService para logging estandarizado.
    """
    
    def __init__(self):
        super().__init__("HEICRemover")
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
        directory: Path,
        recursive: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
        validate_dates: bool = True
    ) -> HeicAnalysisResult:
        """
        Analiza duplicados HEIC/JPG en un directorio.
        
        Args:
            directory: Directorio a analizar
            recursive: Si buscar recursivamente en subdirectorios
            progress_callback: Función opcional (current, total, message) para reportar progreso
            validate_dates: Si validar que las fechas de modificación sean similares
        
        Returns:
            HeicAnalysisResult con análisis detallado
        """
        log_section_header_discrete(self.logger, "ANÁLISIS DE DUPLICADOS HEIC/JPG")
        self.logger.info(f"Analizando en: {directory}")
        self.logger.info(f"Validación de fechas: {'ACTIVADA' if validate_dates else 'DESACTIVADA'}")
        if validate_dates:
            self.logger.info(
                f"Tolerancia máxima: {Config.MAX_TIME_DIFFERENCE_SECONDS}s"
            )
        
        self._reset_stats()
        
        results = {
            'directory': directory,
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
        
        # Encontrar archivos HEIC y JPG
        file_iterator = directory.rglob("*") if recursive else directory.iterdir()
        all_files = [f for f in file_iterator if f.is_file()]
        total_files = len(all_files)
        processed = 0
        
        # Estructura optimizada: dict[Path, dict[str, tuple[Path, int, float]]]
        # Agrupa por directorio primero para evitar comparaciones innecesarias
        heic_by_dir: Dict[Path, Dict[str, Tuple[Path, int, float]]] = defaultdict(dict)
        jpg_by_dir: Dict[Path, Dict[str, Tuple[Path, int, float]]] = defaultdict(dict)
        
        total_heic_count = 0
        total_jpg_count = 0
        
        # Primera pasada: indexar todos los archivos por directorio
        for file_path in all_files:
            if not self._report_progress(
                progress_callback,
                processed,
                total_files,
                "Indexando archivos HEIC/JPG"
            ):
                return self._create_empty_result()
            
            extension = file_path.suffix.lower()
            base_name = file_path.stem
            parent_dir = file_path.parent
            
            if extension in self.heic_extensions or extension in self.jpg_extensions:
                # Una sola llamada a stat() por archivo
                stat_info = file_path.stat()
                file_info = (file_path, stat_info.st_size, stat_info.st_mtime)
                
                if extension in self.heic_extensions:
                    heic_by_dir[parent_dir][base_name] = file_info
                    self.stats['total_heic_size'] += stat_info.st_size
                    total_heic_count += 1
                else:
                    jpg_by_dir[parent_dir][base_name] = file_info
                    self.stats['total_jpg_size'] += stat_info.st_size
                    total_jpg_count += 1
            
            processed += 1
        
        results['total_heic_files'] = total_heic_count
        results['total_jpg_files'] = total_jpg_count
        self.stats['heic_files_found'] = total_heic_count
        self.stats['jpg_files_found'] = total_jpg_count
        
        # Segunda pasada: emparejar archivos (ahora es O(n) en lugar de O(n²))
        duplicate_pairs = []
        matched_heic: Set[Path] = set()
        matched_jpg: Set[Path] = set()
        
        for directory in heic_by_dir:
            if directory not in jpg_by_dir:
                continue
            
            heic_dict = heic_by_dir[directory]
            jpg_dict = jpg_by_dir[directory]
            
            # Encontrar bases comunes en este directorio
            common_bases = set(heic_dict.keys()) & set(jpg_dict.keys())
            
            for base_name in common_bases:
                heic_path, heic_size, heic_mtime = heic_dict[base_name]
                jpg_path, jpg_size, jpg_mtime = jpg_dict[base_name]
                
                try:
                    heic_date = datetime.fromtimestamp(heic_mtime)
                    jpg_date = datetime.fromtimestamp(jpg_mtime)
                    
                    # Validación de diferencia temporal
                    if validate_dates:
                        time_diff = abs(heic_date - jpg_date)
                        if time_diff.total_seconds() > Config.MAX_TIME_DIFFERENCE_SECONDS:
                            self.logger.warning(
                                f"Par rechazado por diferencia temporal: {base_name} "
                                f"en {directory} (diff: {time_diff.total_seconds():.0f}s)"
                            )
                            self.stats['rejected_by_time_diff'] += 1
                            continue
                    
                    # Crear par de duplicados
                    duplicate_pair = DuplicatePair(
                        heic_path=heic_path,
                        jpg_path=jpg_path,
                        base_name=base_name,
                        heic_size=heic_size,
                        jpg_size=jpg_size,
                        directory=directory,
                        heic_date=heic_date,
                        jpg_date=jpg_date
                    )
                    
                    duplicate_pairs.append(duplicate_pair)
                    matched_heic.add(heic_path)
                    matched_jpg.add(jpg_path)
                    
                    # Actualizar estadísticas
                    results['potential_savings_keep_jpg'] += heic_size
                    results['potential_savings_keep_heic'] += jpg_size
                    results['by_directory'][str(directory)] += 1
                    
                    if validate_dates:
                        time_diff_str = f"{duplicate_pair.time_difference.total_seconds():.1f}s"
                        self.logger.debug(
                            f"Duplicado encontrado: {base_name} en {directory} "
                            f"(diff temporal: {time_diff_str})"
                        )
                    else:
                        self.logger.debug(f"Duplicado encontrado: {base_name} en {directory}")
                
                except Exception as e:
                    self.logger.warning(
                        f"No se pudo procesar par {base_name} en {directory}: {e}"
                    )
        
        results['duplicate_pairs'] = duplicate_pairs
        results['total_duplicates'] = len(duplicate_pairs)
        self.stats['duplicate_pairs_found'] = len(duplicate_pairs)
        self.stats['potential_savings'] = results['potential_savings_keep_jpg']
        
        # Encontrar huérfanos (archivos sin pareja en el mismo directorio)
        orphan_heic = []
        orphan_jpg = []
        
        for directory, heic_dict in heic_by_dir.items():
            jpg_dict = jpg_by_dir.get(directory, {})
            for base_name, (heic_path, _, _) in heic_dict.items():
                if heic_path not in matched_heic:
                    orphan_heic.append(heic_path)
        
        for directory, jpg_dict in jpg_by_dir.items():
            heic_dict = heic_by_dir.get(directory, {})
            for base_name, (jpg_path, _, _) in jpg_dict.items():
                if jpg_path not in matched_jpg:
                    orphan_jpg.append(jpg_path)
        
        results['orphan_heic'] = orphan_heic
        results['orphan_jpg'] = orphan_jpg
        
        # Log de resumen
        if validate_dates and self.stats['rejected_by_time_diff'] > 0:
            self.logger.info(
                f"Pares rechazados por diferencia temporal: "
                f"{self.stats['rejected_by_time_diff']}"
            )
        log_section_footer_discrete(self.logger, f"Análisis completado: {len(duplicate_pairs)} pares duplicados encontrados")
        
        return HeicAnalysisResult(
            total_files=results['total_heic_files'] + results['total_jpg_files'],
            duplicate_pairs=duplicate_pairs,
            total_pairs=len(duplicate_pairs),
            heic_files=results['total_heic_files'],
            jpg_files=results['total_jpg_files'],
            total_size=self.stats['total_heic_size'] + self.stats['total_jpg_size'],
            potential_savings_keep_jpg=results['potential_savings_keep_jpg'],
            potential_savings_keep_heic=results['potential_savings_keep_heic'],
            orphan_heic=results.get('orphan_heic', []),
            orphan_jpg=results.get('orphan_jpg', []),
            by_directory=results.get('by_directory', {})
        )
    
    def execute(
        self,
        duplicate_pairs: List[DuplicatePair],
        keep_format: str = 'jpg',
        create_backup: bool = True,
        dry_run: bool = False
    ) -> HeicDeletionResult:
        """
        Ejecuta la eliminación de archivos HEIC duplicados
        
        Args:
            duplicate_pairs: Lista de pares duplicados a procesar
            keep_format: 'jpg' o 'heic' - formato a mantener
            create_backup: Si crear backup antes de eliminar
            dry_run: Si solo simular sin eliminar archivos reales
        
        Returns:
            HeicDeletionResult con el resultado de la operación
        """
        if not duplicate_pairs:
            return HeicDeletionResult(
                success=True,
                files_deleted=0,
                space_freed=0,
                message='No hay archivos duplicados para eliminar',
                format_kept=keep_format,
                dry_run=dry_run
            )
        
        mode = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(self.logger, "ELIMINACIÓN DE DUPLICADOS HEIC/JPG", mode=mode)
        self.logger.info(f"*** Pares a procesar: {len(duplicate_pairs)}")
        self.logger.info(f"*** Formato a conservar: {keep_format.upper()}")
        
        results = HeicDeletionResult(success=True, format_kept=keep_format, dry_run=dry_run)
        
        try:
            # Determinar archivos a eliminar
            if keep_format.lower() == 'jpg':
                files_to_delete = [pair.heic_path for pair in duplicate_pairs]
            else:
                files_to_delete = [pair.jpg_path for pair in duplicate_pairs]
            
            # Crear backup usando método centralizado
            if create_backup and files_to_delete and not dry_run:
                try:
                    backup_path = self._create_backup_for_operation(
                        files_to_delete,
                        'heic_removal'
                    )
                    if backup_path:
                        results.backup_path = str(backup_path)
                except BackupCreationError as e:
                    error_msg = f"Error creando backup: {e}"
                    self.logger.error(error_msg)
                    results.add_error(error_msg)
                    return results
            
            # Procesar cada par
            for pair in duplicate_pairs:
                file_to_delete = pair.heic_path if keep_format.lower() == 'jpg' else pair.jpg_path
                file_to_keep = pair.jpg_path if keep_format.lower() == 'jpg' else pair.heic_path
                
                try:
                    # Validación simplificada (ya validado en __post_init__)
                    if not file_to_delete.exists():
                        error_msg = f"Archivo no existe: {file_to_delete}"
                        results.add_error(error_msg)
                        self.logger.error(error_msg)
                        continue
                    
                    if not file_to_keep.exists():
                        error_msg = f"Archivo a conservar no existe: {file_to_keep}"
                        results.add_error(error_msg)
                        self.logger.error(error_msg)
                        continue
                    
                    file_size = pair.heic_size if keep_format.lower() == 'jpg' else pair.jpg_size
                    from utils.format_utils import format_size
                    
                    format_deleted = 'HEIC' if keep_format.lower() == 'jpg' else 'JPG'
                    format_kept = 'JPG' if keep_format.lower() == 'jpg' else 'HEIC'
                    
                    if dry_run:
                        results.simulated_files_deleted += 1
                        results.simulated_space_freed += file_size
                        results.deleted_files.append(str(file_to_delete))
                        self.logger.info(
                            f"[SIMULACIÓN] Eliminaría {format_deleted}: {file_to_delete} "
                            f"({format_size(file_size)})"
                        )
                        self.logger.info(f"[SIMULACIÓN] Conservaría {format_kept}: {file_to_keep}")
                    else:
                        file_to_delete.unlink()
                        results.files_deleted += 1
                        results.space_freed += file_size
                        results.deleted_files.append(str(file_to_delete))
                        self.logger.info(
                            f"✓ Eliminado {format_deleted}: {file_to_delete} "
                            f"({format_size(file_size)})"
                        )
                        self.logger.info(f"  ✓ Conservado {format_kept}: {file_to_keep}")
                
                except Exception as e:
                    error_msg = f"Error eliminando {file_to_delete}: {str(e)}"
                    results.add_error(error_msg)
                    self.logger.error(f"✗ {error_msg}")
            
            if results.has_errors:
                results.success = len(results.errors) < len(duplicate_pairs)
            
            # Generar resumen
            files_count = (
                results.simulated_files_deleted if dry_run else results.files_deleted
            )
            space_freed = (
                results.simulated_space_freed if dry_run else results.space_freed
            )
            
            summary = self._format_operation_summary(
                "Eliminación HEIC/JPG",
                files_count,
                space_freed,
                dry_run
            )
            
            log_section_footer_relevant(self.logger, summary)
            
            from utils.format_utils import format_size
            freed = format_size(space_freed)
            
            if dry_run:
                results.message = (
                    f"Simulación completada: {files_count} archivos "
                    f"{keep_format.upper()} ({freed}) se eliminarían"
                )
            else:
                results.message = (
                    f"Eliminados {files_count} archivos {keep_format.upper()}, "
                    f"liberados {freed}"
                )
            
            if results.backup_path:
                results.message += f"\n\nBackup creado en:\n{results.backup_path}"
            
            if results.errors:
                error_prefix = "[SIMULACIÓN] " if dry_run else ""
                self.logger.info(
                    f"*** {error_prefix}Errores encontrados durante la "
                    f"{'simulación' if dry_run else 'eliminación'}:"
                )
                for error in results.errors:
                    self.logger.error(f"  ✗ {error}")
                results.message += f"\n\nAdvertencia: {len(results.errors)} errores encontrados"
        
        except Exception as e:
            error_msg = f"Error durante eliminación: {str(e)}"
            results.add_error(error_msg)
            results.message = error_msg
            self.logger.error(error_msg)
        
        return results
    
    def _create_empty_result(self) -> HeicAnalysisResult:
        """Crea un resultado vacío para cuando se cancela la operación"""
        return HeicAnalysisResult(
            total_files=0,
            duplicate_pairs=[],
            total_pairs=0,
            heic_files=0,
            jpg_files=0,
            total_size=0,
            potential_savings_keep_jpg=0,
            potential_savings_keep_heic=0,
            orphan_heic=[],
            orphan_jpg=[],
            by_directory={}
        )
    
    def _reset_stats(self):
        """Reinicia estadísticas"""
        for key in self.stats:
            self.stats[key] = 0
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas actuales"""
        return self.stats.copy()
