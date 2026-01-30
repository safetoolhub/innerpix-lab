"""
Clase base para servicios de detección de duplicados.

Proporciona lógica unificada para:
- Selección de archivos según estrategia (oldest, newest, largest, smallest)
- Eliminación de duplicados con backup
- Procesamiento de grupos con dry-run
"""

import logging
from pathlib import Path
from typing import List, Callable, Optional
from dataclasses import dataclass, field
from services.base_service import BaseService
from services.file_metadata_repository_cache import FileInfoRepositoryCache
from services.result_types import DuplicateGroup, DuplicateExecutionResult
from utils.logger import log_section_header_relevant, log_section_footer_relevant



@dataclass
class GroupDeletionResult:
    """
    Resultado del procesamiento de un grupo de duplicados.
    
    Usado internamente por _process_group_deletion para retornar
    resultados tipados en lugar de diccionarios.
    """
    deleted: List[Path] = field(default_factory=list)
    kept: List[Path] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)
    space_freed: int = 0
    processed: int = 0


class DuplicatesBaseService(BaseService):
    """
    Clase base para servicios de duplicados (exactos y similares).
    
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
        analysis_result: 'DuplicateAnalysisResult',
        dry_run: bool = False,
        create_backup: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        **kwargs
    ) -> DuplicateExecutionResult:
        """
        Ejecuta la eliminación de duplicados (lógica unificada).
        
        Args:
            analysis_result: Resultado del análisis (contiene los grupos)
            dry_run: Si solo simular
            create_backup: Si crear backup
            progress_callback: Callback
            **kwargs: Debe contener 'keep_strategy'
        """
        from datetime import datetime
        
        groups = analysis_result.groups
        keep_strategy = kwargs.get('keep_strategy', 'oldest')
        
        # Header con información de operación
        mode = "SIMULACIÓN" if dry_run else ""
        log_section_header_relevant(
            self.logger,
            f"ELIMINACIÓN DE DUPLICADOS - Estrategia: {keep_strategy}",
            mode=mode
        )
        
        if not groups:
            self.logger.warning("No hay grupos para procesar")
            return DuplicateExecutionResult(
                success=True,
                items_processed=0,
                bytes_processed=0,
                keep_strategy=keep_strategy,
                dry_run=dry_run,
                message="No hay duplicados para eliminar"
            )
        
        # =====================================================================
        # FILTRAR ARCHIVOS INEXISTENTES DE LOS GRUPOS
        # Esto previene errores cuando otro servicio eliminó archivos entre
        # el análisis y la ejecución (ej: Live Photos elimina MOVs que también
        # aparecen como duplicados exactos)
        # =====================================================================
        filtered_groups = []
        total_missing_files = 0
        
        for group in groups:
            existing_files = [f for f in group.files if f.exists()]
            missing_count = len(group.files) - len(existing_files)
            
            if missing_count > 0:
                total_missing_files += missing_count
                self.logger.debug(
                    f"Grupo {group.hash_value[:8]}...: {missing_count} archivos ya no existen"
                )
            
            # Solo mantener el grupo si tiene al menos 2 archivos existentes
            # (un duplicado necesita al menos 2 archivos)
            if len(existing_files) >= 2:
                # Crear nuevo grupo con solo los archivos existentes
                from services.result_types import DuplicateGroup
                updated_group = DuplicateGroup(
                    hash_value=group.hash_value,
                    files=existing_files,
                    total_size=sum(f.stat().st_size for f in existing_files),
                    similarity_score=group.similarity_score
                )
                filtered_groups.append(updated_group)
            elif len(existing_files) == 1:
                # Solo queda 1 archivo, ya no es duplicado
                self.logger.debug(
                    f"Grupo {group.hash_value[:8]}... descartado: "
                    f"solo queda 1 archivo ({existing_files[0].name})"
                )
        
        if total_missing_files > 0:
            self.logger.warning(
                f"⚠️ {total_missing_files} archivos ya no existen "
                f"(posiblemente eliminados por otra operación). "
                f"Grupos reducidos: {len(groups)} → {len(filtered_groups)}"
            )
        
        groups = filtered_groups
        
        if not groups:
            self.logger.info("Todos los grupos fueron filtrados (archivos ya no existen)")
            return DuplicateExecutionResult(
                success=True,
                items_processed=0,
                bytes_processed=0,
                keep_strategy=keep_strategy,
                dry_run=dry_run,
                message="No hay duplicados para eliminar (archivos ya procesados)"
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
                    if backup_path:
                        self.logger.info(f"Backup creado exitosamente: {backup_path}")
                    else:
                        # Si no se pudo crear backup, no continuar con la operación
                        error_msg = "No se pudo crear el backup. Operación cancelada por seguridad."
                        self.logger.error(error_msg)
                        return DuplicateExecutionResult(
                            success=False,
                            errors=[error_msg],
                            keep_strategy=keep_strategy,
                            dry_run=dry_run
                        )
                except BackupCreationError as e:
                    error_msg = f"Error creando backup: {e}"
                    self.logger.error(error_msg)
                    return DuplicateExecutionResult(
                        success=False,
                        errors=[error_msg],
                        keep_strategy=keep_strategy,
                        dry_run=dry_run
                    )
        
        # Procesar eliminaciones grupo por grupo
        files_affected = []
        kept_files = []
        errors = []
        bytes_processed = 0
        
        # Calcular total de operaciones para progress
        if keep_strategy == 'manual':
            total_operations = sum(len(g.files) for g in groups)
        else:
            total_operations = sum(len(g.files) - 1 for g in groups)
        
        items_processed = 0
        
        for group in groups:
            result_group = self._process_group_deletion(
                group=group,
                keep_strategy=keep_strategy,
                dry_run=dry_run,
                backup_path=backup_path,
                progress_callback=progress_callback,
                processed_count=items_processed,
                total_count=total_operations
            )
            
            files_affected.extend(result_group.deleted)
            kept_files.extend(result_group.kept)
            errors.extend(result_group.errors)
            bytes_processed += result_group.space_freed
            items_processed += result_group.processed
        
        # Construir resultado
        error_messages = [
            f"{e.get('file', 'Unknown')}: {e.get('alert-circle', 'Unknown error')}"
            if isinstance(e, dict) else str(e)
            for e in errors
        ]
        
        result = DuplicateExecutionResult(
            success=len(error_messages) == 0,
            items_processed=items_processed,
            bytes_processed=bytes_processed,
            files_affected=files_affected,
            files_kept=len(kept_files),
            errors=error_messages,
            backup_path=str(backup_path) if backup_path else None,
            keep_strategy=keep_strategy,
            dry_run=dry_run
        )
        
        # Logging de resumen usando método centralizado
        summary = self._format_operation_summary(
            "Eliminación duplicados",
            items_processed,
            bytes_processed,
            dry_run
        )
        
        if not dry_run and result.backup_path:
            summary += f"\n\nBackup creado en:\n{result.backup_path}"
        
        result.message = summary
        
        if result.errors:
            error_prefix = "[SIMULACIÓN] " if dry_run else ""
            self.logger.info(f"*** {error_prefix}Errores durante la operación:")
            for error in result.errors:
                self.logger.error(f"  ✗ {error}")
            result.message += f"\n\nAdvertencia: {len(result.errors)} errores encontrados"
        
        log_section_footer_relevant(self.logger, summary)

        # Mostramos estadísticas de la caché al final
        repo = FileInfoRepositoryCache.get_instance()
        repo.log_cache_statistics(level=logging.INFO)
        
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
    ) -> GroupDeletionResult:
        """
        Procesa eliminación de un grupo de duplicados.
        
        Extrae la lógica común de procesamiento que estaba duplicada
        entre DuplicatesExactService y DuplicatesSimilarService.
        
        Args:
            group: Grupo de archivos duplicados
            keep_strategy: Estrategia de selección
            dry_run: Si es simulación
            backup_path: Path del backup (None si no hay)
            progress_callback: Callback de progreso
            processed_count: Archivos procesados hasta ahora
            total_count: Total de archivos a procesar
        
        Returns:
            GroupDeletionResult con archivos procesados y estadísticas
        """
        from utils.file_utils import validate_file_exists
        from utils.format_utils import format_size
        from utils.date_utils import select_best_date_from_file, get_all_metadata_from_file
        
        deleted = []
        kept = []
        errors = []
        space_freed = 0
        processed = 0
        
        # Determinar archivos a eliminar según estrategia
        keep_file = None
        keep_file_info = None  # Para incluir en logs de eliminación
        
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
                
                # Obtener información del archivo que se mantiene (sin verbose para evitar logs extra)
                try:
                    file_metadata = get_all_metadata_from_file(keep_file)
                    keep_date, keep_date_source = select_best_date_from_file(file_metadata)
                    keep_date_str = (
                        keep_date.strftime('%Y-%m-%d %H:%M:%S')
                        if keep_date else 'fecha desconocida'
                    )
                    # Normalizar source si está disponible
                    if not keep_date_source:
                        keep_date_source = 'unknown'
                    keep_file_size = file_metadata.fs_size
                except Exception:
                    keep_date_str = 'fecha desconocida'
                    keep_date_source = 'unknown'
                    keep_file_size = keep_file.stat().st_size  # Fallback si falla metadata
                
                # Guardar info para incluir en logs de eliminación
                keep_file_info = {
                    'path': str(keep_file),
                    'name': keep_file.name,
                    'date': keep_date_str,
                    'date_source': keep_date_source,
                    'size': keep_file_size
                }
                
            except Exception as e:
                self.logger.error(f"Error seleccionando archivo a mantener: {e}")
                errors.append({'group': str(group.hash_value), 'alert-circle': str(e)})
                return GroupDeletionResult(
                    deleted=deleted,
                    kept=kept,
                    errors=errors,
                    space_freed=space_freed,
                    processed=processed
                )
        
        # Eliminar archivos del grupo
        for file_path in files_to_delete:
            try:
                # Validar existencia
                validate_file_exists(file_path)
                
                # Obtener información del archivo a eliminar (sin verbose para evitar logs extra)
                # FileInfoRepositoryCache.get_instance() se llama internamente en get_all_metadata_from_file()
                try:
                    file_metadata = get_all_metadata_from_file(file_path)
                    file_date, file_date_source = select_best_date_from_file(file_metadata)
                    file_date_str = (
                        file_date.strftime('%Y-%m-%d %H:%M:%S')
                        if file_date else 'fecha desconocida'
                    )
                    # Normalizar source si está disponible
                    if not file_date_source:
                        file_date_source = 'unknown'
                    file_size = file_metadata.fs_size
                except Exception:
                    file_date_str = 'fecha desconocida'
                    file_date_source = 'unknown'
                    file_size = file_path.stat().st_size  # Fallback si falla metadata
                
                # Ejecutar eliminación (o simulación)
                if dry_run:
                    deleted.append(file_path)
                    space_freed += file_size
                    
                    # Log unificado con toda la información en UNA sola línea
                    if keep_file_info:
                        # Comparación completa: archivo eliminado vs archivo conservado
                        self.logger.info(
                            f"FILE_DELETED_SIMULATION: "
                            f"{file_path} | size={format_size(file_size)} | "
                            f"date={file_date_str} ({file_date_source})] "
                            f"<> KEPT=[{keep_file_info['path']} | "
                            f"size={format_size(keep_file_info['size'])} | "
                            f"date={keep_file_info['date']} ({keep_file_info['date_source']}) | "
                            f"strategy={keep_strategy}"
                        )
                    else:
                        # Modo manual: no hay archivo conservado
                        self.logger.info(
                            f"FILE_DELETED_SIMULATION: {file_path} | "
                            f"Size: {format_size(file_size)} | "
                            f"Date: {file_date_str} ({file_date_source}) | "
                            f"Type: duplicate | Strategy: {keep_strategy}"
                        )
                else:
                    # Backup ya se hizo antes, solo eliminar
                    file_path.unlink()
                    deleted.append(file_path)
                    space_freed += file_size
                    
                    # Actualizar caché eliminando el archivo
                    from services.file_metadata_repository_cache import FileInfoRepositoryCache
                    repo = FileInfoRepositoryCache.get_instance()
                    repo.remove_file(file_path)
                    
                    # Log unificado con toda la información en UNA sola línea
                    if keep_file_info:
                        # Comparación completa: archivo eliminado vs archivo conservado
                        self.logger.info(
                            f"DUPLICATE_DELETED: "
                            f"DELETED=[{file_path} | size={format_size(file_size)} | "
                            f"date={file_date_str} ({file_date_source})] "
                            f"<> KEPT=[{keep_file_info['path']} | "
                            f"size={format_size(keep_file_info['size'])} | "
                            f"date={keep_file_info['date']} ({keep_file_info['date_source']})] | "
                            f"strategy={keep_strategy}"
                        )
                    else:
                        # Modo manual: no hay archivo conservado
                        self.logger.info(
                            f"FILE_DELETED: {file_path} | "
                            f"Size: {format_size(file_size)} | "
                            f"Date: {file_date_str} ({file_date_source}) | "
                            f"Type: duplicate | Strategy: {keep_strategy}"
                        )
                
                processed += 1
                
                # Reportar progreso usando método de BaseService
                action = "[Simulación] Eliminaría" if dry_run else "Eliminado"
                progress_msg = f"{action}\n{file_path.name}"
                if not self._report_progress(
                    progress_callback,
                    processed_count + processed,
                    total_count,
                    progress_msg
                ):
                    # Cancelación detectada
                    break
                
            except FileNotFoundError:
                # Archivo ya no existe, por causa desconocida
                # Loguear warning pero no contar como error ni sumar a estadísticas
                warn_msg = f"Archivo no encontrado durante eliminación: {file_path}"
                self.logger.warning(warn_msg)
                # No añadimos a 'deleted' ni 'space_freed', simplemente continuamos
                continue
            except Exception as e:
                errors.append({'file': str(file_path), 'alert-circle': str(e)})
                self.logger.error(f"Error eliminando {file_path}: {e}")
        
        return GroupDeletionResult(
            deleted=deleted,
            kept=kept,
            errors=errors,
            space_freed=space_freed,
            processed=processed
        )
