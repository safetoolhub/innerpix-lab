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
import config

# Importaciones opcionales para detección perceptual
try:
    import imagehash
    from PIL import Image
    PERCEPTUAL_AVAILABLE = True
except ImportError:
    PERCEPTUAL_AVAILABLE = False
    
try:
    import cv2
    VIDEO_ANALYSIS_AVAILABLE = True
except ImportError:
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
        self.logger = logging.getLogger('DuplicateDetector')
        self._hash_cache = {} if config.Config.ENABLE_HASH_CACHE else None
        
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
            if f.is_file() and config.Config.is_media_file(f.name):
                all_files.append(f)
        
        total_files = len(all_files)
        self.logger.info(f"Archivos multimedia encontrados: {total_files}")
        
        if progress_callback:
            progress_callback(0, total_files, "Calculando hashes SHA256...")
        
        # Calcular hashes
        hash_map = defaultdict(list)
        processed = 0
        
        from utils.file_utils import calculate_file_hash
        for file_path in all_files:
            try:
                file_hash = calculate_file_hash(file_path, cache=self._hash_cache)
                hash_map[file_hash].append(file_path)

                processed += 1
                if progress_callback and processed % 10 == 0:
                    progress_callback(processed, total_files,
                                      f"Procesando: {file_path.name}")
            except Exception as e:
                self.logger.error(f"Error procesando {file_path}: {e}")
        
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
        
        return {
            'mode': 'exact',
            'total_files': total_files,
            'groups': duplicate_groups,
            'total_groups': len(duplicate_groups),
            'total_duplicates': total_duplicates,
            'space_wasted': space_wasted
        }
    
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
            return {
                'mode': 'perceptual',
                'error': 'Librerías no disponibles',
                'total_files': 0,
                'groups': [],
                'total_groups': 0,
                'total_similar': 0,
                'space_potential': 0
            }
        
        self.logger.info(f"Iniciando análisis de duplicados similares en {directory} "
                        f"(sensibilidad: {sensitivity})")
        
        # Recolectar archivos
        image_files = []
        video_files = []
        
        for f in directory.rglob("*"):
            if f.is_file():
                if config.Config.is_image_file(f.name):
                    image_files.append(f)
                elif config.Config.is_video_file(f.name):
                    video_files.append(f)
        
        total_files = len(image_files) + len(video_files)
        self.logger.info(f"Archivos multimedia: {len(image_files)} imágenes, "
                        f"{len(video_files)} videos")
        
        if progress_callback:
            progress_callback(0, total_files, "Calculando hashes perceptuales...")
        
        # Calcular hashes perceptuales
        perceptual_hashes = {}
        processed = 0
        
        for img_path in image_files:
            try:
                phash = self._calculate_perceptual_hash(img_path)
                if phash:
                    perceptual_hashes[img_path] = phash
                
                processed += 1
                if progress_callback and processed % 5 == 0:
                    progress_callback(processed, total_files, 
                                    f"Analizando: {img_path.name}")
            except Exception as e:
                self.logger.error(f"Error con {img_path}: {e}")
        
        # Videos (extraer frames si está disponible)
        if VIDEO_ANALYSIS_AVAILABLE:
            for vid_path in video_files:
                try:
                    phash = self._calculate_video_hash(vid_path)
                    if phash:
                        perceptual_hashes[vid_path] = phash
                    
                    processed += 1
                    if progress_callback and processed % 2 == 0:
                        progress_callback(processed, total_files, 
                                        f"Analizando video: {vid_path.name}")
                except Exception as e:
                    self.logger.error(f"Error con video {vid_path}: {e}")
        
        # Agrupar por similitud
        if progress_callback:
            progress_callback(total_files, total_files, "Agrupando similares...")
        
        similar_groups = self._group_by_similarity(perceptual_hashes, sensitivity)
        
        total_similar = sum(len(group.files) - 1 for group in similar_groups)
        space_potential = sum(group.space_wasted for group in similar_groups)
        
        self.logger.info(f"Grupos similares: {len(similar_groups)}, "
                        f"{total_similar} archivos similares")
        
        return {
            'mode': 'perceptual',
            'total_files': total_files,
            'groups': similar_groups,
            'total_groups': len(similar_groups),
            'total_similar': total_similar,
            'space_potential': space_potential,
            'sensitivity': sensitivity,
            'min_similarity': self._calculate_min_similarity(similar_groups),
            'max_similarity': self._calculate_max_similarity(similar_groups)
        }
    
    # SHA256 hashing is delegated to utils.file_utils.calculate_file_hash
    
    def _calculate_perceptual_hash(self, image_path: Path) -> Optional[imagehash.ImageHash]:
        """Calcula hash perceptual de una imagen"""
        try:
            img = Image.open(image_path)
            # Usar dhash (difference hash) que funciona bien para redimensionados
            return imagehash.dhash(img, hash_size=config.Config.DEFAULT_HASH_SIZE)
        except Exception as e:
            self.logger.debug(f"No se pudo calcular hash perceptual para {image_path}: {e}")
            return None
    
    def _calculate_video_hash(self, video_path: Path) -> Optional[imagehash.ImageHash]:
        """Calcula hash perceptual de un video (primer frame)"""
        if not VIDEO_ANALYSIS_AVAILABLE:
            return None
        
        try:
            cap = cv2.VideoCapture(str(video_path))
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Convertir BGR a RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                return imagehash.dhash(img, hash_size=config.Config.DEFAULT_HASH_SIZE)
        except Exception as e:
            self.logger.debug(f"No se pudo calcular hash para video {video_path}: {e}")
        
        return None
    
    def _group_by_similarity(
        self,
        hashes: Dict[Path, imagehash.ImageHash],
        threshold: int
    ) -> List[DuplicateGroup]:
        """Agrupa archivos por similitud perceptual"""
        groups = []
        processed = set()
        
        hash_list = list(hashes.items())
        
        for i, (path1, hash1) in enumerate(hash_list):
            if path1 in processed:
                continue
            
            similar_files = [path1]
            
            for j, (path2, hash2) in enumerate(hash_list[i+1:], start=i+1):
                if path2 in processed:
                    continue
                
                # Calcular distancia Hamming
                hamming_distance = hash1 - hash2
                
                if hamming_distance <= threshold:
                    similar_files.append(path2)
                    processed.add(path2)
            
            if len(similar_files) > 1:
                # Calcular score de similitud promedio
                avg_similarity = 100 - (threshold / config.Config.MAX_HAMMING_THRESHOLD * 100)
                
                group = DuplicateGroup(
                    hash_value=str(hash1),
                    files=similar_files,
                    total_size=sum(f.stat().st_size for f in similar_files),
                    similarity_score=avg_similarity
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
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict:
        """
        Ejecuta eliminación de duplicados
        
        Args:
            groups: Grupos de duplicados
            keep_strategy: 'oldest', 'newest', 'largest', 'smallest'
            create_backup: Crear backup antes de eliminar
            progress_callback: Callback de progreso
            
        Returns:
            Resultados de la operación
        """
        from datetime import datetime
        import shutil
        
        self.logger.info(f"Ejecutando eliminación con estrategia: {keep_strategy}")
        
        backup_path = None
        if create_backup:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = config.Config.DEFAULT_BACKUP_DIR / f"duplicates_backup_{timestamp}"
            backup_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Backup creado en: {backup_path}")

        deleted_files = []
        kept_files = []
        errors = []
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
                # Si el usuario seleccionó manualmente los archivos a borrar,
                # los grupos contienen exactamente esos archivos: borramos todos.
                if keep_strategy == 'manual':
                    for file_path in group.files:
                        try:
                            if create_backup and backup_path:
                                backup_file = backup_path / file_path.name
                                shutil.copy2(file_path, backup_file)

                            # Obtener tamaño antes de eliminar
                            try:
                                file_size = file_path.stat().st_size
                            except Exception:
                                file_size = 0

                            file_path.unlink()
                            deleted_files.append(file_path)
                            space_freed += file_size

                            processed += 1
                            if progress_callback:
                                progress_callback(processed, total_operations,
                                                  f"Eliminado: {file_path.name}")
                        except Exception as e:
                            errors.append({'file': str(file_path), 'error': str(e)})
                            self.logger.error(f"Error eliminando {file_path}: {e}")

                else:
                    # Seleccionar archivo a mantener
                    keep_file = self._select_file_to_keep(group.files, keep_strategy)
                    kept_files.append(keep_file)

                    # Eliminar el resto
                    for file_path in group.files:
                        if file_path == keep_file:
                            continue

                        try:
                            # Backup
                            if create_backup and backup_path:
                                backup_file = backup_path / file_path.name
                                shutil.copy2(file_path, backup_file)

                            # Obtener tamaño antes de eliminar
                            try:
                                file_size = file_path.stat().st_size
                            except Exception:
                                file_size = 0

                            # Eliminar
                            file_path.unlink()
                            deleted_files.append(file_path)
                            space_freed += file_size

                            processed += 1
                            if progress_callback:
                                progress_callback(processed, total_operations,
                                                  f"Eliminado: {file_path.name}")

                        except Exception as e:
                            errors.append({'file': str(file_path), 'error': str(e)})
                            self.logger.error(f"Error eliminando {file_path}: {e}")

            except Exception as e:
                errors.append({'group': str(group.hash_value), 'error': str(e)})
                self.logger.error(f"Error procesando grupo: {e}")
        
    # space_freed fue acumulado durante la eliminación (se obtiene el tamaño
    # antes de llamar a unlink). No recomputar usando deleted_files porque
    # los archivos ya pueden no existir.
        result = {
            'files_deleted': len(deleted_files),
            'files_kept': len(kept_files),
            'space_freed': space_freed,
            'errors': errors,
            'backup_path': str(backup_path) if backup_path else None,
            'keep_strategy': keep_strategy
        }
        
        try:
            from utils.format_utils import format_size
            freed_str = format_size(space_freed)
        except Exception:
            freed_str = f"{space_freed / (1024*1024):.2f} MB"

        self.logger.info(f"Eliminación completada: {len(deleted_files)} archivos, {freed_str} liberados")
        
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
