"""
Clase base para servicios de detección de duplicados.

Proporciona lógica unificada para:
- Selección de archivos según estrategia (oldest, newest, largest, smallest)
- Eliminación de duplicados con backup
- Procesamiento de grupos con dry-run
"""

from pathlib import Path
from typing import List, Callable, Optional, Dict, Any
from services.base_service import BaseService
from services.result_types import DuplicateGroup, DuplicateDeletionResult
from utils.callback_utils import safe_progress_callback
from utils.decorators import deprecated
import shutil


class BaseDetectorService(BaseService):
    """
    Clase base para detectores de duplicados (exactos y similares).
    
    Centraliza toda la lógica común de eliminación de duplicados,
    eliminando ~200 líneas de código duplicado entre detectores.
    
    Estrategias soportadas:
    - 'oldest': Mantener archivo más antiguo
    - 'newest': Mantener archivo más reciente
    - 'largest': Mantener archivo más grande
    - 'smallest': Mantener archivo más pequeño
    - 'manual': Eliminar todos (usuario decide)
    """
    
    STRATEGIES = ['oldest', 'newest', 'largest', 'smallest', 'manual']
    
    def select_file_to_keep(
        self,
        files: List[Path],
        strategy: str
    ) -> Path:
        """
        Selecciona archivo a mantener según estrategia.
        
        Args:
            files: Lista de archivos duplicados
            strategy: Estrategia de selección
        
        Returns:
            Path del archivo a mantener
        
        Raises:
            ValueError: Si la estrategia no es válida
        """
        if strategy not in self.STRATEGIES:
            raise ValueError(
                f"Estrategia no válida: {strategy}. "
                f"Opciones: {', '.join(self.STRATEGIES)}"
            )
        
        if strategy == 'oldest':
            return min(files, key=lambda f: f.stat().st_mtime)
        elif strategy == 'newest':
            return max(files, key=lambda f: f.stat().st_mtime)
        elif strategy == 'largest':
            return max(files, key=lambda f: f.stat().st_size)
        elif strategy == 'smallest':
            return min(files, key=lambda f: f.stat().st_size)
        else:
            # 'manual' - no se selecciona ninguno, se eliminan todos
            raise ValueError("Estrategia 'manual' no requiere selección")
    
    def execute(
        self,
        groups: List[DuplicateGroup],
        keep_strategy: str = 'oldest',
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> DuplicateDeletionResult:
        """
        Ejecuta la eliminación de duplicados (lógica unificada).
        
        Elimina el código duplicado de 200+ líneas entre detectores.
        Maneja backup, dry-run, progress reporting y error handling.
        
        Args:
            groups: Lista de grupos de duplicados
            keep_strategy: Estrategia para seleccionar archivo a mantener
            create_backup: Si crear backup antes de eliminar
            dry_run: Si solo simular sin eliminar archivos reales
            progress_callback: Callback para reportar progreso
        
        Returns:
            DuplicateDeletionResult con estadísticas de la operación
        """
        from datetime import datetime
        
        # Header con información de operación
        mode = "SIMULACIÓN" if dry_run else ""
        self._log_section_header(
            f"ELIMINACIÓN DE DUPLICADOS - Estrategia: {keep_strategy}",
            mode=mode
        )
        
        if not groups:
            self.logger.warning("No hay grupos para procesar")
            return DuplicateDeletionResult(
                success=True,
                files_deleted=0,
                files_kept=0,
                space_freed=0,
                keep_strategy=keep_strategy,
                dry_run=dry_run,
                message="No hay duplicados para eliminar"
            )
        
        # Crear backup una sola vez (común para todos los archivos)
        backup_path = None
        if create_backup and not dry_run:
            all_files = [f for g in groups for f in g.files]
            if all_files:
                try:
                    from services.base_service import BackupCreationError
                    backup_path = self._create_backup_for_operation(
                        all_files,
                        'duplicates_deletion',
                        progress_callback
                    )
                except BackupCreationError as e:
                    self.logger.error(f"Error creando backup: {e}")
                    return DuplicateDeletionResult(
                        success=False,
                        errors=[str(e)],
                        keep_strategy=keep_strategy,
                        dry_run=dry_run
                    )
        
        # Procesar eliminaciones grupo por grupo
        deleted_files = []
        kept_files = []
        errors = []
        space_freed = 0
        simulated_space_freed = 0
        
        # Calcular total de operaciones para progress
        if keep_strategy == 'manual':
            total_operations = sum(len(g.files) for g in groups)
        else:
            total_operations = sum(len(g.files) - 1 for g in groups)
        
        processed = 0
        
        for group in groups:
            result = self._process_group_deletion(
                group=group,
                keep_strategy=keep_strategy,
                dry_run=dry_run,
                backup_path=backup_path,
                progress_callback=progress_callback,
                processed_count=processed,
                total_count=total_operations
            )
            
            deleted_files.extend(result['deleted'])
            kept_files.extend(result['kept'])
            errors.extend(result['errors'])
            
            if dry_run:
                simulated_space_freed += result['space_freed']
            else:
                space_freed += result['space_freed']
            
            processed += result['processed']
        
        # Construir resultado
        error_messages = [
            f"{e.get('file', 'Unknown')}: {e.get('error', 'Unknown error')}"
            if isinstance(e, dict) else str(e)
            for e in errors
        ]
        
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
            simulated_files_deleted=len(deleted_files) if dry_run else 0,
            simulated_space_freed=simulated_space_freed if dry_run else 0
        )
        
        # Logging de resumen
        from utils.format_utils import format_size
        
        if dry_run:
            count = len(deleted_files)
            freed = format_size(simulated_space_freed)
            summary = f"Simulación completada: {count} archivos se eliminarían, {freed} se liberarían"
        else:
            count = len(deleted_files)
            freed = format_size(space_freed)
            summary = f"Eliminados {count} duplicados, liberados {freed}"
            if result.backup_path:
                summary += f"\n\nBackup creado en:\n{result.backup_path}"
        
        result.message = summary
        
        if result.has_errors:
            error_prefix = "[SIMULACIÓN] " if dry_run else ""
            self.logger.info(f"*** {error_prefix}Errores durante la operación:")
            for error in result.errors:
                self.logger.error(f"  ✗ {error}")
            result.message += f"\n\nAdvertencia: {len(result.errors)} errores encontrados"
        
        self._log_section_footer(summary)
        
        return result
    
    def _process_group_deletion(
        self,
        group: DuplicateGroup,
        keep_strategy: str,
        dry_run: bool,
        backup_path: Optional[Path],
        progress_callback: Optional[Callable],
        processed_count: int,
        total_count: int
    ) -> Dict[str, Any]:
        """
        Procesa eliminación de un grupo de duplicados.
        
        Extrae la lógica común de procesamiento que estaba duplicada
        entre ExactCopiesDetector y SimilarFilesDetector.
        
        Args:
            group: Grupo de archivos duplicados
            keep_strategy: Estrategia de selección
            dry_run: Si es simulación
            backup_path: Path del backup (None si no hay)
            progress_callback: Callback de progreso
            processed_count: Archivos procesados hasta ahora
            total_count: Total de archivos a procesar
        
        Returns:
            Dict con 'deleted', 'kept', 'errors', 'space_freed', 'processed'
        """
        from utils.file_utils import validate_file_exists
        from utils.format_utils import format_size
        from utils.date_utils import get_file_date
        
        deleted = []
        kept = []
        errors = []
        space_freed = 0
        processed = 0
        
        # Determinar archivos a eliminar según estrategia
        if keep_strategy == 'manual':
            # Modo manual: eliminar todos
            files_to_delete = group.files
            self.logger.info(f"  Grupo (manual): {len(group.files)} archivos a eliminar")
        else:
            # Modo automático: seleccionar uno para mantener
            try:
                keep_file = self.select_file_to_keep(group.files, keep_strategy)
                kept.append(keep_file)
                files_to_delete = [f for f in group.files if f != keep_file]
                
                # Log del archivo que se mantiene
                try:
                    keep_date = get_file_date(keep_file, verbose=True)
                    keep_date_str = (
                        keep_date.strftime('%Y-%m-%d %H:%M:%S')
                        if keep_date else 'fecha desconocida'
                    )
                except Exception:
                    keep_date_str = 'fecha desconocida'
                
                log_prefix = "[SIMULACIÓN] " if dry_run else ""
                self.logger.info(
                    f"{log_prefix}  ✓ {'Conservaría' if dry_run else 'Conservado'} "
                    f"({keep_strategy}): {keep_file.name} ({keep_date_str})"
                )
                
            except Exception as e:
                self.logger.error(f"Error seleccionando archivo a mantener: {e}")
                errors.append({'group': str(group.hash_value), 'error': str(e)})
                return {
                    'deleted': deleted,
                    'kept': kept,
                    'errors': errors,
                    'space_freed': space_freed,
                    'processed': processed
                }
        
        # Eliminar archivos del grupo
        for file_path in files_to_delete:
            try:
                # Validar existencia
                validate_file_exists(file_path)
                
                # Obtener información del archivo
                file_size = file_path.stat().st_size
                
                try:
                    file_date = get_file_date(file_path, verbose=True)
                    file_date_str = (
                        file_date.strftime('%Y-%m-%d %H:%M:%S')
                        if file_date else 'fecha desconocida'
                    )
                except Exception:
                    file_date_str = 'fecha desconocida'
                
                # Ejecutar eliminación (o simulación)
                if dry_run:
                    deleted.append(file_path)
                    space_freed += file_size
                    self.logger.info(
                        f"[SIMULACIÓN] Eliminaría: {file_path.name} "
                        f"({format_size(file_size)}, {file_date_str})"
                    )
                else:
                    # Backup ya se hizo antes, solo eliminar
                    file_path.unlink()
                    deleted.append(file_path)
                    space_freed += file_size
                    self.logger.info(
                        f"✓ Eliminado: {file_path.name} "
                        f"({format_size(file_size)}, {file_date_str})"
                    )
                
                processed += 1
                
                # Reportar progreso
                progress_msg = f"{'Simularía' if dry_run else 'Eliminado'}: {file_path.name}"
                safe_progress_callback(
                    progress_callback,
                    processed_count + processed,
                    total_count,
                    progress_msg
                )
                
            except FileNotFoundError as e:
                error_prefix = "[SIMULACIÓN] " if dry_run else ""
                errors.append({'file': str(file_path), 'error': str(e)})
                self.logger.error(f"{error_prefix}Archivo no encontrado: {file_path}: {e}")
            except Exception as e:
                errors.append({'file': str(file_path), 'error': str(e)})
                self.logger.error(f"Error eliminando {file_path}: {e}")
        
        return {
            'deleted': deleted,
            'kept': kept,
            'errors': errors,
            'space_freed': space_freed,
            'processed': processed
        }
