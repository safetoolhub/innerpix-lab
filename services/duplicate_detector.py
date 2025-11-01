"""
Servicio de detección de duplicados para PhotoKit Manager

Implementa dos modos:
1. Duplicados exactos (SHA256 hash)
2. Duplicados similares (perceptual hashing con imagehash)
"""

import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config
from utils.callback_utils import safe_progress_callback
from utils.logger import get_logger
from services.result_types import DuplicateAnalysisResult, DuplicateDeletionResult
from utils.settings_manager import settings_manager

# Importaciones opcionales para detección perceptual
try:
    import imagehash
    from PIL import Image
    PERCEPTUAL_AVAILABLE = True
except ImportError:
    imagehash = None  # Definir para evitar NameError en type hints
    PERCEPTUAL_AVAILABLE = False
    
try:
    import cv2
    VIDEO_ANALYSIS_AVAILABLE = True
except ImportError:
    cv2 = None
    VIDEO_ANALYSIS_AVAILABLE = False


@dataclass
class DuplicateGroup:
    """Grupo de archivos duplicados"""
    hash_value: str
    files: List[Path]
    total_size: int
    similarity_score: float = 100.0  # 100% para exactos, variable para similares
    
    @property
    def file_count(self) -> int:
        return len(self.files)
    
    @property
    def space_wasted(self) -> int:
        """Espacio desperdiciado (todos menos el original)"""
        if self.file_count <= 1:
            return 0
        # Mantener el archivo más antiguo o el más grande
        return self.total_size - max(f.stat().st_size for f in self.files)


class DuplicateDetector:
    """Detector de archivos duplicados (exactos y similares)"""
    
    def __init__(self):
        self.logger = get_logger('DuplicateDetector')
        self._hash_cache = {} if Config.ENABLE_HASH_CACHE else None
        # Contenedor para almacenar los resultados del último análisis de duplicados
        # Mantener esto dentro del servicio centraliza el estado y evita que la
        # ventana principal tenga que sincronizarlo manualmente.
        self.duplicate_analysis_results = None

    # ---- Helpers para manejo del estado del último análisis ----
    def get_last_results(self):
        """Devuelve los resultados del último análisis de duplicados o None."""
        return self.duplicate_analysis_results

    def set_last_results(self, results: dict):
        """Almacena los resultados del último análisis de duplicados."""
        self.duplicate_analysis_results = results

    def clear_last_results(self):
        """Limpia el estado del último análisis de duplicados."""
        self.duplicate_analysis_results = None
        
    def analyze_exact_duplicates(
        self,
        directory: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict:
        """
        Analiza duplicados exactos usando SHA256
        
        Args:
            directory: Directorio raíz a analizar
            progress_callback: Función de callback para progreso
            
        Returns:
            Diccionario con resultados del análisis
        """
        self.logger.info(f"Iniciando análisis de duplicados exactos en {directory}")
        
        # Recolectar todos los archivos multimedia
        all_files = []
        for f in directory.rglob("*"):
            if f.is_file() and Config.is_media_file(f.name):
                all_files.append(f)
        
        total_files = len(all_files)
        self.logger.info(f"Archivos multimedia encontrados: {total_files}")
        
        safe_progress_callback(progress_callback, 0, total_files, "Calculando hashes SHA256")
        
        # Obtener número de workers de configuración
        max_workers = settings_manager.get_max_workers(Config.MAX_WORKERS)
        self.logger.debug(f"Usando {max_workers} workers para procesamiento paralelo")
        
        # Calcular hashes en paralelo
        hash_map = defaultdict(list)
        processed = 0
        
        from utils.file_utils import calculate_file_hash
        
        # Función para calcular hash de un archivo
        def process_file(file_path):
            try:
                file_hash = calculate_file_hash(file_path, cache=self._hash_cache)
                return (file_path, file_hash, None)
            except Exception as e:
                return (file_path, None, str(e))
        
        # Procesar archivos en paralelo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Enviar todos los trabajos
            futures = {executor.submit(process_file, f): f for f in all_files}
            
            # Recoger resultados a medida que se completan
            for future in as_completed(futures):
                file_path, file_hash, error = future.result()
                
                if error:
                    self.logger.warning(f"No se pudo procesar {file_path}: {error}")
                elif file_hash:
                    hash_map[file_hash].append(file_path)
                
                processed += 1
                if processed % Config.PROGRESS_CALLBACK_INTERVAL == 0 or processed == total_files:
                    # Si el callback retorna False, detener procesamiento
                    if not safe_progress_callback(progress_callback, processed, total_files, 
                                         "Calculando hashes SHA256"):
                        self.logger.info("Análisis de duplicados exactos cancelado por el usuario")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
        
        # Filtrar solo grupos con duplicados
        duplicate_groups = []
        total_duplicates = 0
        space_wasted = 0
        
        for hash_value, files in hash_map.items():
            if len(files) > 1:
                group = DuplicateGroup(
                    hash_value=hash_value,
                    files=files,
                    total_size=sum(f.stat().st_size for f in files),
                    similarity_score=100.0
                )
                duplicate_groups.append(group)
                total_duplicates += len(files) - 1
                space_wasted += group.space_wasted
        
        self.logger.info(f"Duplicados exactos encontrados: {len(duplicate_groups)} grupos, "
                        f"{total_duplicates} archivos duplicados")
        
        return DuplicateAnalysisResult(
            mode='exact',
            total_files=total_files,
            groups=duplicate_groups,
            total_groups=len(duplicate_groups),
            total_duplicates=total_duplicates,
            space_wasted=space_wasted
        )
    
    def analyze_similar_duplicates(
        self,
        directory: Path,
        sensitivity: int = 10,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict:
        """
        Analiza duplicados similares usando hashing perceptual
        
        Args:
            directory: Directorio raíz a analizar
            sensitivity: Umbral de similitud (0-20, menor = más estricto)
            progress_callback: Función de callback para progreso
            
        Returns:
            Diccionario con resultados del análisis
        """
        if not PERCEPTUAL_AVAILABLE:
            self.logger.error("imagehash no disponible para detección perceptual")
            result = DuplicateAnalysisResult(
                mode='perceptual',
                total_files=0,
                groups=[],
                total_groups=0,
                total_similar=0,
                space_potential=0,
                success=False
            )
            result.add_error('Librerías no disponibles')
            return result
        
        self.logger.info(f"Iniciando análisis de duplicados similares en {directory} "
                        f"(sensibilidad: {sensitivity})")
        
        # Recolectar archivos
        image_files = []
        video_files = []
        
        for f in directory.rglob("*"):
            if f.is_file():
                if Config.is_image_file(f.name):
                    image_files.append(f)
                elif Config.is_video_file(f.name):
                    video_files.append(f)
        
        total_files = len(image_files) + len(video_files)
        self.logger.info(f"Archivos multimedia: {len(image_files)} imágenes, "
                        f"{len(video_files)} videos")
        
        safe_progress_callback(progress_callback, 0, total_files, "Calculando hashes perceptuales...")
        
        # Obtener número de workers de configuración
        max_workers = settings_manager.get_max_workers(Config.MAX_WORKERS)
        self.logger.debug(f"Usando {max_workers} workers para hashing perceptual")
        
        # Calcular hashes perceptuales en paralelo
        perceptual_hashes = {}
        processed = 0
        
        # Función para calcular hash perceptual de una imagen
        def process_image(img_path):
            try:
                phash = self._calculate_perceptual_hash(img_path)
                return (img_path, phash, None)
            except Exception as e:
                return (img_path, None, str(e))
        
        # Procesar imágenes en paralelo
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_image, f): f for f in image_files}
            
            for future in as_completed(futures):
                img_path, phash, error = future.result()
                
                if error:
                    self.logger.warning(f"No se pudo procesar imagen {img_path}: {error}")
                elif phash:
                    perceptual_hashes[img_path] = phash
                
                processed += 1
                if processed % Config.PROGRESS_CALLBACK_INTERVAL == 0 or processed == total_files:
                    # Si el callback retorna False, detener procesamiento
                    if not safe_progress_callback(progress_callback, processed, total_files, 
                                         f"Calculando hashes perceptuales... ({processed}/{total_files})"):
                        self.logger.info("Análisis de duplicados perceptuales cancelado por el usuario")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
        
        # Videos (extraer frames si está disponible)
        if VIDEO_ANALYSIS_AVAILABLE and video_files:
            def process_video(vid_path):
                try:
                    phash = self._calculate_video_hash(vid_path)
                    return (vid_path, phash, None)
                except Exception as e:
                    return (vid_path, None, str(e))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_video, f): f for f in video_files}
                
                for future in as_completed(futures):
                    vid_path, phash, error = future.result()
                    
                    if error:
                        self.logger.warning(f"No se pudo procesar video {vid_path}: {error}")
                    elif phash:
                        perceptual_hashes[vid_path] = phash
                    
                    processed += 1
                    if processed % Config.PROGRESS_CALLBACK_INTERVAL == 0 or processed == total_files:
                        # Si el callback retorna False, detener procesamiento
                        if not safe_progress_callback(progress_callback, processed, total_files,
                                             f"Calculando hashes de videos... ({processed}/{total_files})"):
                            self.logger.info("Análisis de videos cancelado por el usuario")
                            executor.shutdown(wait=False, cancel_futures=True)
                            break
                    elif phash:
                        perceptual_hashes[vid_path] = phash
                    
                    processed += 1
                    if processed % Config.PROGRESS_CALLBACK_INTERVAL == 0 or processed == total_files:
                        safe_progress_callback(progress_callback, processed, total_files, 
                                             f"Calculando hashes perceptuales... ({processed}/{total_files})")
        elif video_files:
            # Si no hay soporte para videos, solo incrementar el contador
            for vid_path in video_files:
                processed += 1
                if processed % Config.PROGRESS_CALLBACK_INTERVAL == 0 or processed == total_files:
                    safe_progress_callback(progress_callback, processed, total_files, 
                                         f"Calculando hashes perceptuales... ({processed}/{total_files})")
        
        # Agrupar por similitud
        safe_progress_callback(progress_callback, total_files, total_files, "Agrupando similares...")
        
        similar_groups = self._group_by_similarity(perceptual_hashes, sensitivity, progress_callback)
        
        total_similar = sum(len(group.files) - 1 for group in similar_groups)
        space_potential = sum(group.space_wasted for group in similar_groups)
        
        self.logger.info(f"Grupos similares: {len(similar_groups)}, "
                        f"{total_similar} archivos similares")
        
        return DuplicateAnalysisResult(
            mode='perceptual',
            total_files=total_files,
            groups=similar_groups,
            total_groups=len(similar_groups),
            total_similar=total_similar,
            space_potential=space_potential,
            sensitivity=sensitivity,
            min_similarity=self._calculate_min_similarity(similar_groups),
            max_similarity=self._calculate_max_similarity(similar_groups)
        )
    
    # SHA256 hashing is delegated to utils.file_utils.calculate_file_hash
    
    def _calculate_perceptual_hash(self, image_path: Path) -> Optional[any]:
        """Calcula hash perceptual de una imagen"""
        if not PERCEPTUAL_AVAILABLE:
            return None
        try:
            with Image.open(image_path) as img:
                # Usar dhash (difference hash) que funciona bien para redimensionados
                return imagehash.dhash(img, hash_size=Config.DEFAULT_HASH_SIZE)
        except Exception as e:
            self.logger.debug(f"No se pudo calcular hash perceptual para {image_path}: {e}")
            return None
    
    def _calculate_video_hash(self, video_path: Path) -> Optional[any]:
        """Calcula hash perceptual de un video (primer frame)"""
        if not VIDEO_ANALYSIS_AVAILABLE or not PERCEPTUAL_AVAILABLE:
            return None
        
        try:
            cap = cv2.VideoCapture(str(video_path))
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Convertir BGR a RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                return imagehash.dhash(img, hash_size=Config.DEFAULT_HASH_SIZE)
        except Exception as e:
            self.logger.debug(f"No se pudo calcular hash para video {video_path}: {e}")
        
        return None
    
    def _group_by_similarity(
        self,
        hashes: Dict[Path, any],
        threshold: int,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[DuplicateGroup]:
        """Agrupa archivos por similitud perceptual"""
        groups = []
        processed = set()
        
        hash_list = list(hashes.items())
        total_items = len(hash_list)
        
        for i, (path1, hash1) in enumerate(hash_list):
            if path1 in processed:
                continue
            
            # Emitir progreso cada N archivos
            if i % Config.PROGRESS_CALLBACK_INTERVAL == 0 or i == total_items - 1:
                safe_progress_callback(progress_callback, i, total_items, "Agrupando similares...")
            
            similar_files = [path1]
            hamming_distances = []
            
            for j, (path2, hash2) in enumerate(hash_list[i+1:], start=i+1):
                if path2 in processed:
                    continue
                
                # Calcular distancia Hamming
                hamming_distance = hash1 - hash2
                
                if hamming_distance <= threshold:
                    similar_files.append(path2)
                    hamming_distances.append(hamming_distance)
                    processed.add(path2)
            
            if len(similar_files) > 1:
                # Calcular score de similitud real basado en la distancia Hamming promedio del grupo
                # Distancia 0 = 100% similar, distancia MAX_HAMMING_THRESHOLD = 0% similar
                avg_hamming = sum(hamming_distances) / len(hamming_distances) if hamming_distances else 0
                # Convertir a porcentaje de similitud (invertido)
                similarity_percentage = 100 - (avg_hamming / Config.MAX_HAMMING_THRESHOLD * 100)
                # Asegurar que esté en el rango [0, 100]
                similarity_percentage = max(0, min(100, similarity_percentage))
                
                group = DuplicateGroup(
                    hash_value=str(hash1),
                    files=similar_files,
                    total_size=sum(f.stat().st_size for f in similar_files),
                    similarity_score=similarity_percentage
                )
                groups.append(group)
                processed.add(path1)
        
        return groups
    
    def _calculate_min_similarity(self, groups: List[DuplicateGroup]) -> int:
        """Calcula similitud mínima de los grupos"""
        if not groups:
            return 0
        return int(min(g.similarity_score for g in groups))
    
    def _calculate_max_similarity(self, groups: List[DuplicateGroup]) -> int:
        """Calcula similitud máxima de los grupos"""
        if not groups:
            return 0
        return int(max(g.similarity_score for g in groups))
    
    def execute_deletion(
        self,
        groups: List[DuplicateGroup],
        keep_strategy: str = 'oldest',
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> DuplicateDeletionResult:
        """
        Ejecuta eliminación de duplicados
        
        Args:
            groups: Grupos de duplicados
            keep_strategy: 'oldest', 'newest', 'largest', 'smallest'
            create_backup: Crear backup antes de eliminar
            dry_run: Si solo simular sin eliminar archivos reales
            progress_callback: Callback de progreso
            
        Returns:
            DuplicateDeletionResult con resultados de la operación
        """
        from datetime import datetime
        import shutil
        
        self.logger.info("=" * 80)
        self.logger.info("*** INICIANDO ELIMINACIÓN DE DUPLICADOS")
        self.logger.info(f"*** Estrategia: {keep_strategy}")
        if dry_run:
            self.logger.info("*** Modo: SIMULACIÓN")
        self.logger.info("=" * 80)
        
        backup_path = None
        if create_backup and not dry_run:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = Config.DEFAULT_BACKUP_DIR / f"duplicates_backup_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Backup creado en: {backup_path}")

        deleted_files = []
        kept_files = []
        errors = []
        simulated_files_deleted = 0
        simulated_space_freed = 0
        # Si la estrategia es 'manual', los grupos contienen los archivos seleccionados
        # para eliminar, por lo que el número de operaciones es la suma de esos archivos.
        if keep_strategy == 'manual':
            total_operations = sum(len(g.files) for g in groups)
        else:
            total_operations = sum(len(g.files) - 1 for g in groups)
        processed = 0
        space_freed = 0

        for group in groups:
            try:
                from utils.file_utils import validate_file_exists
                # Si el usuario seleccionó manualmente los archivos a borrar,
                # los grupos contienen exactamente esos archivos: borramos todos.
                if keep_strategy == 'manual':
                    for file_path in group.files:
                        try:
                            # Verificar que el archivo exista antes de intentar copiar/eliminar
                            try:
                                validate_file_exists(file_path)
                            except FileNotFoundError as e:
                                error_prefix = "[SIMULACIÓN] " if dry_run else ""
                                errors.append({'file': str(file_path), 'error': str(e)})
                                self.logger.error(f"{error_prefix}Archivo no encontrado: {file_path}: {e}")
                                continue
                            
                            # Obtener tamaño y análisis detallado de fechas antes de eliminar
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
                                # Solo simular: no crear backup ni eliminar
                                simulated_files_deleted += 1
                                simulated_space_freed += file_size
                                deleted_files.append(file_path)
                                self.logger.info(f"[SIMULACIÓN] Eliminaría duplicado (manual): {file_path} ({format_size(file_size)}, {file_date_str})")
                            else:
                                # Eliminar realmente
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
                    # Seleccionar archivo a mantener
                    keep_file = self._select_file_to_keep(group.files, keep_strategy)
                    kept_files.append(keep_file)
                    
                    # Obtener análisis detallado de fechas del archivo conservado
                    from utils.date_utils import get_file_date
                    try:
                        keep_date = get_file_date(keep_file, verbose=True)
                        keep_date_str = keep_date.strftime('%Y-%m-%d %H:%M:%S') if keep_date else 'fecha desconocida'
                    except Exception as e:
                        self.logger.warning(f"Error obteniendo fecha de {keep_file}: {e}")
                        keep_date_str = 'fecha desconocida'
                    
                    log_prefix = "[SIMULACIÓN] " if dry_run else ""
                    self.logger.info(f"{log_prefix}  ✓ {'Conservaría' if dry_run else 'Conservado'} ({keep_strategy}): {keep_file} ({keep_date_str})")

                    # Eliminar el resto
                    # Verificar que el archivo a mantener exista antes de borrar el resto
                    try:
                        validate_file_exists(keep_file)
                    except FileNotFoundError as e:
                        error_prefix = "[SIMULACIÓN] " if dry_run else ""
                        errors.append({'file': str(keep_file), 'error': str(e)})
                        self.logger.error(f"{error_prefix}Archivo a mantener no existe: {keep_file}: {e}")
                        continue

                    for file_path in group.files:
                        if file_path == keep_file:
                            continue

                        try:
                            # Verificar que el archivo exista antes de intentar copiar/eliminar
                            try:
                                validate_file_exists(file_path)
                            except FileNotFoundError as e:
                                error_prefix = "[SIMULACIÓN] " if dry_run else ""
                                errors.append({'file': str(file_path), 'error': str(e)})
                                self.logger.error(f"{error_prefix}Archivo no encontrado: {file_path}: {e}")
                                continue

                            # Obtener tamaño y análisis detallado de fechas antes de eliminar
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
                                # Solo simular: no crear backup ni eliminar
                                simulated_files_deleted += 1
                                simulated_space_freed += file_size
                                deleted_files.append(file_path)
                                self.logger.info(f"[SIMULACIÓN] Eliminaría duplicado: {file_path} ({format_size(file_size)}, {file_date_str})")
                            else:
                                # Backup
                                if create_backup and backup_path:
                                    backup_file = backup_path / file_path.name
                                    shutil.copy2(file_path, backup_file)

                                # Eliminar
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
        
    # space_freed fue acumulado durante la eliminación (se obtiene el tamaño
    # antes de llamar a unlink). No recomputar usando deleted_files porque
    # los archivos ya pueden no existir.
        
        # Convertir errores de dict a strings para consistencia
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
            self.logger.info("*** SIMULACIÓN DE ELIMINACIÓN DE DUPLICADOS COMPLETADA")
            self.logger.info(f"*** Resultado: {files_count} archivos se eliminarían, {freed_str} se liberarían")
        else:
            self.logger.info("*** ELIMINACIÓN DE DUPLICADOS COMPLETADA")
            self.logger.info(f"*** Resultado: {files_count} archivos eliminados, {freed_str} liberados")
        if result.has_errors:
            error_prefix = "[SIMULACIÓN] " if dry_run else ""
            self.logger.info(f"*** {error_prefix}Errores encontrados durante la {'simulación' if dry_run else 'eliminación'}:")
            for error in result.errors:
                self.logger.error(f"  ✗ {error}")
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
