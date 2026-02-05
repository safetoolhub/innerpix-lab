"""
Servicio de detección de copias exactas mediante SHA256.

Identifica archivos 100% idénticos digitalmente comparando hashes criptográficos.
Usa FileInfoRepositoryCache como única fuente de metadatos.
"""

from pathlib import Path
from typing import List, Optional, Dict, Set
from datetime import datetime

from config import Config
from services.result_types import (
    ExactDuplicateGroup,
    ExactDuplicateAnalysisResult,
    ExactDuplicateExecutionResult
)
from services.base_service import BaseService, BackupCreationError, ProgressCallback
from services.file_metadata_repository_cache import FileInfoRepositoryCache, PopulationStrategy
from utils.logger import (
    log_section_header_discrete,
    log_section_footer_discrete,
    log_section_header_relevant,
    log_section_footer_relevant
)
from utils.format_utils import format_size


# Estrategias de selección soportadas
KEEP_STRATEGIES = ['oldest', 'newest', 'largest', 'smallest', 'manual']


class DuplicatesExactService(BaseService):
    """
    Servicio de detección y eliminación de copias exactas mediante SHA256.
    
    Identifica archivos que son idénticos bit a bit, independientemente
    de su nombre o ubicación.
    """

    def __init__(self):
        """Inicializa el detector de copias exactas."""
        super().__init__('DuplicatesExactService')

    def analyze(
        self,
        progress_callback: Optional[ProgressCallback] = None,
        **kwargs
    ) -> ExactDuplicateAnalysisResult:
        """
        Analiza buscando duplicados exactos (SHA256) usando FileInfoRepository.
        
        Args:
            progress_callback: Callback de progreso
            **kwargs: Args adicionales
            
        Returns:
            ExactDuplicateAnalysisResult con grupos de duplicados exactos
        """
        repo = FileInfoRepositoryCache.get_instance()
        
        log_section_header_discrete(self.logger, "ANÁLISIS DE DUPLICADOS EXACTOS (SHA256)")
        
        all_files = repo.get_all_files()
        total_files = len(all_files)
        self.logger.info(f"Escaneando {total_files} archivos para detección de duplicados")
        
        if total_files == 0:
            return ExactDuplicateAnalysisResult(
                success=True,
                groups=[],
                total_files_scanned=0
            )
        
        # Optimización: solo procesar archivos que comparten tamaño
        # (archivos con tamaño único no pueden ser duplicados)
        supported_exts = Config.SUPPORTED_IMAGE_EXTENSIONS | Config.SUPPORTED_VIDEO_EXTENSIONS
        by_size = repo.get_files_by_size()
        
        files_to_hash = []
        for size, files in by_size.items():
            if len(files) > 1:
                for meta in files:
                    if meta.extension in supported_exts:
                        files_to_hash.append(meta)
        
        self.logger.info(f"Candidatos a duplicados (por coincidencia de tamaño): {len(files_to_hash)}")
        
        # Verificar y calcular hashes faltantes
        if files_to_hash:
            files_missing_hash = [meta.path for meta in files_to_hash if not meta.sha256]
            files_cached_hash = len(files_to_hash) - len(files_missing_hash)
            
            if files_cached_hash > 0:
                self.logger.info(f"Hashes en caché: {files_cached_hash}")
            
            if files_missing_hash:
                self.logger.info(f"Calculando hashes para {len(files_missing_hash)} archivos")
                
                def repo_progress_callback(processed_count, total_count):
                    return self._report_progress(
                        progress_callback,
                        processed_count,
                        total_count,
                        "Calculando firmas digitales..."
                    )
                
                repo.populate_from_scan(
                    files_missing_hash,
                    strategy=PopulationStrategy.HASH,
                    max_workers=4,
                    progress_callback=repo_progress_callback,
                    stop_check_callback=lambda: self._cancelled
                )
        
        # Agrupar por hash
        file_hashes: Dict[str, List[Path]] = {}
        for meta in files_to_hash:
            hash_val = repo.get_hash(meta.path)
            if hash_val:
                if hash_val not in file_hashes:
                    file_hashes[hash_val] = []
                file_hashes[hash_val].append(meta.path)
        
        # Crear grupos de duplicados
        groups = []
        for hash_value, paths in file_hashes.items():
            if len(paths) > 1:
                # Obtener tamaño del primer archivo (todos tienen el mismo tamaño)
                first_meta = repo.get_file_metadata(paths[0])
                file_size = first_meta.fs_size if first_meta else 0
                
                groups.append(ExactDuplicateGroup(
                    hash_value=hash_value,
                    files=paths,
                    file_size=file_size
                ))
        
        # Ordenar grupos por espacio recuperable (mayor primero)
        groups.sort(key=lambda g: g.space_recoverable, reverse=True)
        
        # Calcular estadísticas
        total_groups = len(groups)
        total_duplicates = sum(g.file_count - 1 for g in groups)
        space_recoverable = sum(g.space_recoverable for g in groups)
        
        self.logger.info(f"Grupos encontrados: {total_groups}")
        self.logger.info(f"Espacio recuperable: {format_size(space_recoverable)}")
        
        log_section_footer_discrete(self.logger, "ANÁLISIS COMPLETADO")
        
        return ExactDuplicateAnalysisResult(
            success=True,
            groups=groups,
            total_files_scanned=total_files,
            total_groups=total_groups,
            total_duplicates=total_duplicates,
            space_recoverable=space_recoverable
        )

    def execute(
        self,
        analysis_result: ExactDuplicateAnalysisResult,
        keep_strategy: str = 'oldest',
        files_to_delete: Optional[List[Path]] = None,
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
        **kwargs
    ) -> ExactDuplicateExecutionResult:
        """
        Ejecuta la eliminación de duplicados exactos.
        
        Args:
            analysis_result: Resultado del análisis
            keep_strategy: Estrategia de conservación ('oldest', 'newest', 'largest', 'smallest', 'manual')
            files_to_delete: Lista específica de archivos a eliminar (para modo manual)
            create_backup: Si crear backup antes de eliminar
            dry_run: Si es simulación
            progress_callback: Callback de progreso
            
        Returns:
            ExactDuplicateExecutionResult con resultados de la operación
        """
        mode = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(
            self.logger,
            f"ELIMINACIÓN DE DUPLICADOS EXACTOS - Estrategia: {keep_strategy}",
            mode=mode
        )
        
        if keep_strategy not in KEEP_STRATEGIES:
            raise ValueError(f"Estrategia no válida: {keep_strategy}. Opciones: {KEEP_STRATEGIES}")
        
        groups = analysis_result.groups
        files_to_delete_set = set(files_to_delete) if files_to_delete else None
        
        if not groups:
            self.logger.info("No hay grupos para procesar")
            return ExactDuplicateExecutionResult(
                success=True,
                items_processed=0,
                bytes_processed=0,
                keep_strategy=keep_strategy,
                dry_run=dry_run,
                message="No hay duplicados para eliminar"
            )
        
        # Filtrar grupos con archivos que aún existen
        filtered_groups = self._filter_existing_groups(groups)
        
        if not filtered_groups:
            self.logger.info("Todos los grupos fueron filtrados (archivos ya no existen)")
            return ExactDuplicateExecutionResult(
                success=True,
                items_processed=0,
                bytes_processed=0,
                keep_strategy=keep_strategy,
                dry_run=dry_run,
                message="No hay duplicados para eliminar (archivos ya procesados)"
            )
        
        # Crear backup si es necesario
        backup_path = None
        if create_backup and not dry_run:
            all_files = [f for g in filtered_groups for f in g.files]
            try:
                backup_path = self._create_backup_for_operation(
                    all_files,
                    'exact_duplicates_deletion',
                    progress_callback
                )
                if not backup_path:
                    return ExactDuplicateExecutionResult(
                        success=False,
                        errors=["No se pudo crear el backup"],
                        keep_strategy=keep_strategy,
                        dry_run=dry_run
                    )
            except BackupCreationError as e:
                return ExactDuplicateExecutionResult(
                    success=False,
                    errors=[f"Error creando backup: {e}"],
                    keep_strategy=keep_strategy,
                    dry_run=dry_run
                )
        
        # Procesar eliminaciones
        repo = FileInfoRepositoryCache.get_instance()
        files_affected = []
        files_kept = 0
        errors = []
        bytes_processed = 0
        
        # Calcular total de operaciones
        if keep_strategy == 'manual' and files_to_delete_set:
            total_operations = len(files_to_delete_set)
        elif keep_strategy == 'manual':
            total_operations = sum(len(g.files) for g in filtered_groups)
        else:
            total_operations = sum(len(g.files) - 1 for g in filtered_groups)
        
        processed = 0
        
        for group in filtered_groups:
            # Determinar qué archivo conservar y cuáles eliminar
            if keep_strategy == 'manual':
                if files_to_delete_set:
                    to_delete = [f for f in group.files if f in files_to_delete_set]
                    files_kept += len(group.files) - len(to_delete)
                else:
                    to_delete = group.files
            else:
                keep_file = self._select_file_to_keep(group.files, keep_strategy, repo)
                to_delete = [f for f in group.files if f != keep_file]
                files_kept += 1
                
                # Log del archivo que se conserva
                keep_meta = repo.get_file_metadata(keep_file)
                keep_date = self._get_best_date_for_file(keep_file, repo)
                self.logger.debug(
                    f"Conservando: {keep_file.name} | "
                    f"Tamaño: {format_size(keep_meta.fs_size if keep_meta else 0)} | "
                    f"Fecha: {keep_date}"
                )
            
            # Eliminar archivos seleccionados
            for file_path in to_delete:
                try:
                    meta = repo.get_file_metadata(file_path)
                    file_size = meta.fs_size if meta else file_path.stat().st_size
                    file_date = self._get_best_date_for_file(file_path, repo)
                    
                    if dry_run:
                        self.logger.info(
                            f"FILE_DELETED_SIMULATION: {file_path} | "
                            f"Size: {format_size(file_size)} | "
                            f"Date: {file_date} | "
                            f"Type: exact_duplicate | Strategy: {keep_strategy}"
                        )
                    else:
                        file_path.unlink()
                        repo.remove_file(file_path)
                        self.logger.info(
                            f"FILE_DELETED: {file_path} | "
                            f"Size: {format_size(file_size)} | "
                            f"Date: {file_date} | "
                            f"Type: exact_duplicate | Strategy: {keep_strategy}"
                        )
                    
                    files_affected.append(file_path)
                    bytes_processed += file_size
                    processed += 1
                    
                    if not self._report_progress(
                        progress_callback,
                        processed,
                        total_operations,
                        f"{'[Simulación] ' if dry_run else ''}Eliminando: {file_path.name}"
                    ):
                        break
                        
                except FileNotFoundError:
                    self.logger.warning(f"Archivo no encontrado: {file_path}")
                except Exception as e:
                    errors.append(f"{file_path}: {e}")
                    self.logger.error(f"Error eliminando {file_path}: {e}")
        
        # Construir resultado
        result = ExactDuplicateExecutionResult(
            success=len(errors) == 0,
            items_processed=processed,
            bytes_processed=bytes_processed,
            files_affected=files_affected,
            files_kept=files_kept,
            backup_path=backup_path,
            keep_strategy=keep_strategy,
            dry_run=dry_run,
            errors=errors
        )
        
        # Mensaje de resumen
        result.message = self._format_operation_summary(
            "Eliminación de duplicados exactos",
            processed,
            bytes_processed,
            dry_run
        )
        
        if backup_path:
            result.message += f"\n\nBackup creado en:\n{backup_path}"
        
        log_section_footer_relevant(self.logger, result.message)
        
        return result

    def _filter_existing_groups(
        self,
        groups: List[ExactDuplicateGroup]
    ) -> List[ExactDuplicateGroup]:
        """
        Filtra grupos para incluir solo archivos que aún existen.
        
        Previene errores cuando otro servicio eliminó archivos entre
        el análisis y la ejecución.
        """
        filtered = []
        total_missing = 0
        
        for group in groups:
            existing_files = [f for f in group.files if f.exists()]
            missing = len(group.files) - len(existing_files)
            
            if missing > 0:
                total_missing += missing
                self.logger.debug(f"Grupo {group.hash_value[:8]}...: {missing} archivos ya no existen")
            
            if len(existing_files) >= 2:
                filtered.append(ExactDuplicateGroup(
                    hash_value=group.hash_value,
                    files=existing_files,
                    file_size=group.file_size
                ))
        
        if total_missing > 0:
            self.logger.warning(
                f"⚠️ {total_missing} archivos ya no existen. "
                f"Grupos: {len(groups)} → {len(filtered)}"
            )
        
        return filtered

    def _select_file_to_keep(
        self,
        files: List[Path],
        strategy: str,
        repo: FileInfoRepositoryCache
    ) -> Path:
        """
        Selecciona qué archivo conservar según la estrategia.
        
        IMPORTANTE: Usa FileInfoRepositoryCache para obtener fechas,
        NO accede directamente al disco con stat().
        """
        if strategy == 'oldest':
            return min(files, key=lambda f: self._get_best_date_timestamp(f, repo))
        elif strategy == 'newest':
            return max(files, key=lambda f: self._get_best_date_timestamp(f, repo))
        elif strategy == 'largest':
            return max(files, key=lambda f: self._get_file_size(f, repo))
        elif strategy == 'smallest':
            return min(files, key=lambda f: self._get_file_size(f, repo))
        else:
            raise ValueError(f"Estrategia no válida para selección: {strategy}")

    def _get_best_date_timestamp(self, file_path: Path, repo: FileInfoRepositoryCache) -> float:
        """Obtiene timestamp de la mejor fecha disponible desde el repositorio."""
        best_date, _ = repo.get_best_date(file_path)
        if best_date:
            return best_date.timestamp()
        
        # Fallback a fecha de modificación del filesystem
        meta = repo.get_file_metadata(file_path)
        if meta and meta.fs_mtime:
            return meta.fs_mtime
        
        return 0.0

    def _get_best_date_for_file(self, file_path: Path, repo: FileInfoRepositoryCache) -> str:
        """Obtiene string formateado de la mejor fecha disponible."""
        best_date, source = repo.get_best_date(file_path)
        if best_date:
            return f"{best_date.strftime('%Y-%m-%d %H:%M:%S')} ({source or 'unknown'})"
        
        meta = repo.get_file_metadata(file_path)
        if meta and meta.fs_mtime:
            from datetime import datetime
            dt = datetime.fromtimestamp(meta.fs_mtime)
            return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} (filesystem)"
        
        return "fecha desconocida"

    def _get_file_size(self, file_path: Path, repo: FileInfoRepositoryCache) -> int:
        """Obtiene tamaño del archivo desde el repositorio."""
        meta = repo.get_file_metadata(file_path)
        return meta.fs_size if meta else 0
