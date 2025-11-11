"""
Servicio de detección de copias exactas mediante SHA256.
Identifica archivos 100% idénticos digitalmente comparando hashes criptográficos.
"""

from pathlib import Path
from typing import List, Callable, Optional
from dataclasses import dataclass
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from utils.logger import get_logger
from utils.callback_utils import safe_progress_callback
from utils.file_utils import calculate_file_hash
from services.result_types import DuplicateAnalysisResult, DuplicateDeletionResult


@dataclass
class DuplicateGroup:
    """Grupo de archivos duplicados (copias exactas o similares)"""
    hash_value: str  # SHA256 hash o perceptual hash
    files: List[Path]
    total_size: int
    similarity_score: float = 100.0  # Copias exactas siempre 100%


class ExactCopiesDetector:
    """
    Servicio de detección de copias exactas mediante hashing SHA256.
    
    Identifica fotos y vídeos 100% idénticos digitalmente (mismo SHA256),
    incluso si tienen nombres diferentes. También conocidos como duplicados exactos.
    """

    def __init__(self):
        """Inicializa el detector de copias exactas"""
        self.logger = get_logger('ExactCopiesDetector')

    def analyze_exact_duplicates(
        self,
        directory: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> DuplicateAnalysisResult:
        """
        Analiza directorio buscando duplicados exactos (SHA256)
        
        Args:
            directory: Directorio a analizar
            progress_callback: Callback de progreso
            
        Returns:
            DuplicateAnalysisResult con grupos de duplicados exactos
        """
        self.logger.info("=" * 80)
        self.logger.info("*** INICIANDO ANÁLISIS DE DUPLICADOS EXACTOS (SHA256)")
        self.logger.info("=" * 80)
        
        # Recopilar archivos soportados (imágenes y videos)
        image_files = []
        for ext in Config.SUPPORTED_IMAGE_EXTENSIONS:
            image_files.extend(directory.rglob(f'*{ext}'))
        
        video_files = []
        for ext in Config.SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(directory.rglob(f'*{ext}'))
        
        files = image_files + video_files
        total_files = len(files)
        self.logger.info(f"Archivos a procesar: {total_files} ({len(image_files)} imágenes, {len(video_files)} videos)")
        
        if total_files == 0:
            return DuplicateAnalysisResult(
                success=True,
                mode='exact',
                groups=[],
                total_files=0,
                total_groups=0,
                total_duplicates=0,
                space_wasted=0
            )
        
        # Calcular hashes en paralelo con caché compartido
        # El caché permite reutilizar hashes si se analiza el mismo directorio múltiples veces
        hash_cache = {}
        file_hashes = {}
        processed = 0
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {
                executor.submit(calculate_file_hash, file_path, cache=hash_cache): file_path
                for file_path in files
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    file_hash = future.result()
                    if file_hash:
                        if file_hash not in file_hashes:
                            file_hashes[file_hash] = []
                        file_hashes[file_hash].append(file_path)
                    
                    processed += 1
                    safe_progress_callback(
                        progress_callback,
                        processed,
                        total_files,
                        f"Procesado: {file_path.name}"
                    )
                except Exception as e:
                    self.logger.error(f"Error calculando hash de {file_path}: {e}")
        
        # Crear grupos de duplicados (solo hashes con 2+ archivos)
        groups = []
        for hash_value, file_list in file_hashes.items():
            if len(file_list) > 1:
                group = DuplicateGroup(
                    hash_value=hash_value,
                    files=file_list,
                    total_size=sum(f.stat().st_size for f in file_list),
                    similarity_score=100.0  # Duplicados exactos siempre 100%
                )
                groups.append(group)
        
        # Calcular estadísticas
        total_groups = len(groups)
        total_duplicates = sum(len(g.files) - 1 for g in groups)  # Total de duplicados
        space_wasted = sum(
            (len(g.files) - 1) * g.files[0].stat().st_size
            for g in groups
        )
        
        self.logger.info("=" * 80)
        self.logger.info("*** ANÁLISIS DE DUPLICADOS EXACTOS COMPLETADO")
        self.logger.info(f"*** Archivos analizados: {total_files}")
        self.logger.info(f"*** Grupos de duplicados: {total_groups}")
        self.logger.info(f"*** Duplicados encontrados: {total_duplicates}")
        try:
            from utils.format_utils import format_size
            self.logger.info(f"*** Espacio potencialmente recuperable: {format_size(space_wasted)}")
        except Exception:
            self.logger.info(f"*** Espacio potencialmente recuperable: {space_wasted / (1024*1024):.2f} MB")
        self.logger.info("=" * 80)
        
        return DuplicateAnalysisResult(
            success=True,
            mode='exact',
            groups=groups,
            total_files=total_files,
            total_groups=total_groups,
            total_duplicates=total_duplicates,
            space_wasted=space_wasted
        )

    def execute_deletion(
        self,
        groups: List[DuplicateGroup],
        keep_strategy: str = 'oldest',
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> DuplicateDeletionResult:
        """
        Ejecuta eliminación de duplicados exactos
        
        Args:
            groups: Grupos de duplicados
            keep_strategy: 'oldest', 'newest', 'largest', 'smallest', 'manual'
            create_backup: Crear backup antes de eliminar
            dry_run: Si solo simular sin eliminar archivos reales
            progress_callback: Callback de progreso
            
        Returns:
            DuplicateDeletionResult con resultados de la operación
        """
        from datetime import datetime
        import shutil
        
        self.logger.info("=" * 80)
        self.logger.info("*** INICIANDO ELIMINACIÓN DE DUPLICADOS EXACTOS")
        self.logger.info(f"*** Estrategia: {keep_strategy}")
        if dry_run:
            self.logger.info("*** Modo: SIMULACIÓN")
        self.logger.info("=" * 80)
        
        backup_path = None
        if create_backup and not dry_run:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = Config.DEFAULT_BACKUP_DIR / f"duplicates_exact_backup_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Backup creado en: {backup_path}")

        deleted_files = []
        kept_files = []
        errors = []
        simulated_files_deleted = 0
        simulated_space_freed = 0
        
        if keep_strategy == 'manual':
            total_operations = sum(len(g.files) for g in groups)
        else:
            total_operations = sum(len(g.files) - 1 for g in groups)
        processed = 0
        space_freed = 0

        for group in groups:
            try:
                from utils.file_utils import validate_file_exists
                
                if keep_strategy == 'manual':
                    # Modo manual: eliminar todos los archivos del grupo
                    for file_path in group.files:
                        try:
                            try:
                                validate_file_exists(file_path)
                            except FileNotFoundError as e:
                                error_prefix = "[SIMULACIÓN] " if dry_run else ""
                                errors.append({'file': str(file_path), 'error': str(e)})
                                self.logger.error(f"{error_prefix}Archivo no encontrado: {file_path}: {e}")
                                continue
                            
                            try:
                                file_size = file_path.stat().st_size
                                from utils.date_utils import get_file_date
                                file_date = get_file_date(file_path, verbose=True)
                                file_date_str = file_date.strftime('%Y-%m-%d %H:%M:%S') if file_date else 'fecha desconocida'
                            except Exception as e:
                                self.logger.warning(f"Error obteniendo información de {file_path}: {e}")
                                file_size = 0
                                file_date_str = 'fecha desconocida'
                            
                            from utils.format_utils import format_size
                            
                            if dry_run:
                                simulated_files_deleted += 1
                                simulated_space_freed += file_size
                                deleted_files.append(file_path)
                                self.logger.info(f"[SIMULACIÓN] Eliminaría duplicado (manual): {file_path} ({format_size(file_size)}, {file_date_str})")
                            else:
                                if create_backup and backup_path:
                                    backup_file = backup_path / file_path.name
                                    shutil.copy2(file_path, backup_file)
                                
                                file_path.unlink()
                                deleted_files.append(file_path)
                                space_freed += file_size
                                self.logger.info(f"✓ Eliminado duplicado (manual): {file_path} ({format_size(file_size)}, {file_date_str})")
                            
                            processed += 1
                            progress_msg = f"{'Simularía' if dry_run else 'Eliminado'}: {file_path.name}"
                            safe_progress_callback(progress_callback, processed, total_operations, progress_msg)
                        except Exception as e:
                            errors.append({'file': str(file_path), 'error': str(e)})
                            self.logger.error(f"Error eliminando {file_path}: {e}")

                else:
                    # Modo automático: seleccionar archivo a mantener
                    keep_file = self._select_file_to_keep(group.files, keep_strategy)
                    kept_files.append(keep_file)
                    
                    from utils.date_utils import get_file_date
                    try:
                        keep_date = get_file_date(keep_file, verbose=True)
                        keep_date_str = keep_date.strftime('%Y-%m-%d %H:%M:%S') if keep_date else 'fecha desconocida'
                    except Exception as e:
                        self.logger.warning(f"Error obteniendo fecha de {keep_file}: {e}")
                        keep_date_str = 'fecha desconocida'
                    
                    log_prefix = "[SIMULACIÓN] " if dry_run else ""
                    self.logger.info(f"{log_prefix}  ✓ {'Conservaría' if dry_run else 'Conservado'} ({keep_strategy}): {keep_file} ({keep_date_str})")

                    # Verificar que el archivo a mantener exista
                    try:
                        validate_file_exists(keep_file)
                    except FileNotFoundError as e:
                        error_prefix = "[SIMULACIÓN] " if dry_run else ""
                        errors.append({'file': str(keep_file), 'error': str(e)})
                        self.logger.error(f"{error_prefix}Archivo a mantener no existe: {keep_file}: {e}")
                        continue

                    # Eliminar el resto
                    for file_path in group.files:
                        if file_path == keep_file:
                            continue

                        try:
                            try:
                                validate_file_exists(file_path)
                            except FileNotFoundError as e:
                                error_prefix = "[SIMULACIÓN] " if dry_run else ""
                                errors.append({'file': str(file_path), 'error': str(e)})
                                self.logger.error(f"{error_prefix}Archivo no encontrado: {file_path}: {e}")
                                continue

                            try:
                                file_size = file_path.stat().st_size
                                file_date = get_file_date(file_path, verbose=True)
                                file_date_str = file_date.strftime('%Y-%m-%d %H:%M:%S') if file_date else 'fecha desconocida'
                            except Exception as e:
                                self.logger.warning(f"Error obteniendo información de {file_path}: {e}")
                                file_size = 0
                                file_date_str = 'fecha desconocida'

                            from utils.format_utils import format_size
                            
                            if dry_run:
                                simulated_files_deleted += 1
                                simulated_space_freed += file_size
                                deleted_files.append(file_path)
                                self.logger.info(f"[SIMULACIÓN] Eliminaría duplicado: {file_path} ({format_size(file_size)}, {file_date_str})")
                            else:
                                if create_backup and backup_path:
                                    backup_file = backup_path / file_path.name
                                    shutil.copy2(file_path, backup_file)

                                file_path.unlink()
                                deleted_files.append(file_path)
                                space_freed += file_size
                                self.logger.info(f"✓ Eliminado duplicado: {file_path} ({format_size(file_size)}, {file_date_str})")
                            
                            processed += 1
                            progress_msg = f"{'Simularía' if dry_run else 'Eliminado'}: {file_path.name}"
                            safe_progress_callback(progress_callback, processed, total_operations, progress_msg)

                        except Exception as e:
                            errors.append({'file': str(file_path), 'error': str(e)})
                            self.logger.error(f"Error eliminando {file_path}: {e}")

            except Exception as e:
                errors.append({'group': str(group.hash_value), 'error': str(e)})
                self.logger.error(f"Error procesando grupo: {e}")
        
        # Convertir errores de dict a strings
        error_messages = []
        for error in errors:
            if isinstance(error, dict):
                error_messages.append(f"{error.get('file', 'Unknown')}: {error.get('error', 'Unknown error')}")
            else:
                error_messages.append(str(error))
        
        result = DuplicateDeletionResult(
            success=len(error_messages) == 0,
            files_deleted=len(deleted_files) if not dry_run else 0,
            files_kept=len(kept_files),
            space_freed=space_freed if not dry_run else 0,
            errors=error_messages,
            backup_path=str(backup_path) if backup_path else None,
            deleted_files=[str(f) for f in deleted_files],
            keep_strategy=keep_strategy,
            dry_run=dry_run,
            simulated_files_deleted=simulated_files_deleted if dry_run else 0,
            simulated_space_freed=simulated_space_freed if dry_run else 0
        )
        
        try:
            from utils.format_utils import format_size
            if dry_run:
                freed_str = format_size(simulated_space_freed)
                files_count = simulated_files_deleted
            else:
                freed_str = format_size(space_freed)
                files_count = len(deleted_files)
        except Exception:
            if dry_run:
                freed_str = f"{simulated_space_freed / (1024*1024):.2f} MB"
                files_count = simulated_files_deleted
            else:
                freed_str = f"{space_freed / (1024*1024):.2f} MB"
                files_count = len(deleted_files)

        self.logger.info("=" * 80)
        if dry_run:
            self.logger.info("*** SIMULACIÓN DE ELIMINACIÓN DE DUPLICADOS EXACTOS COMPLETADA")
            self.logger.info(f"*** Resultado: {files_count} archivos se eliminarían, {freed_str} se liberarían")
            result.message = f"Simulación completada: {files_count} duplicados ({freed_str}) se eliminarían"
        else:
            self.logger.info("*** ELIMINACIÓN DE DUPLICADOS EXACTOS COMPLETADA")
            self.logger.info(f"*** Resultado: {files_count} archivos eliminados, {freed_str} liberados")
            result.message = f"Eliminados {files_count} duplicados, liberados {freed_str}"
            if result.backup_path:
                result.message += f"\n\nBackup creado en:\n{result.backup_path}"
        
        if result.has_errors:
            error_prefix = "[SIMULACIÓN] " if dry_run else ""
            self.logger.info(f"*** {error_prefix}Errores encontrados durante la {'simulación' if dry_run else 'eliminación'}:")
            for error in result.errors:
                self.logger.error(f"  ✗ {error}")
            result.message += f"\n\nAdvertencia: {len(result.errors)} errores encontrados"
        self.logger.info("=" * 80)
        
        return result
    
    def _select_file_to_keep(self, files: List[Path], strategy: str) -> Path:
        """Selecciona qué archivo mantener según la estrategia"""
        if strategy == 'oldest':
            return min(files, key=lambda f: f.stat().st_mtime)
        elif strategy == 'newest':
            return max(files, key=lambda f: f.stat().st_mtime)
        elif strategy == 'largest':
            return max(files, key=lambda f: f.stat().st_size)
        elif strategy == 'smallest':
            return min(files, key=lambda f: f.stat().st_size)
        else:
            return files[0]
