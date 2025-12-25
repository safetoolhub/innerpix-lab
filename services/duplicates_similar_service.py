"""
Servicio de detección de archivos similares mediante perceptual hashing.
Identifica fotos y vídeos visualmente similares: recortes, rotaciones,
ediciones o diferentes resoluciones.
Refactorizado para usar MetadataCache.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import os

from config import Config
from utils.logger import get_logger, log_section_header_discrete, log_section_footer_discrete
from services.result_types import DuplicateAnalysisResult, DuplicateExecutionResult, DuplicateGroup
from services.duplicates_base_service import DuplicatesBaseService
from services.base_service import ProgressCallback
from services.file_metadata_repository_cache import FileInfoRepositoryCache


class DuplicatesSimilarAnalysis:
    """
    Contiene hashes perceptuales y permite generar grupos con
    cualquier sensibilidad en tiempo real.
    
    Esta clase separa el análisis costoso (cálculo de hashes) del
    clustering rápido, permitiendo ajustar la sensibilidad
    interactivamente sin reanalizar.
    
    Attributes:
        perceptual_hashes: Dict con {file_path: hash_data}
        workspace_path: Ruta del workspace analizado (o None)
        total_files: Número total de archivos analizados
        analysis_timestamp: Fecha/hora del análisis
    """
    
    def __init__(self):
        """Inicializa análisis vacío."""
        self.perceptual_hashes: Dict[str, Dict[str, Any]] = {}
        self.workspace_path: Optional[str] = None
        self.total_files: int = 0
        self.analysis_timestamp: Optional[datetime] = None
        self._distance_cache: Dict[Tuple[int, int], int] = {}
        self._logger = get_logger('DuplicatesSimilarAnalysis')
    
    def get_groups(self, sensitivity: int) -> DuplicateAnalysisResult:
        """
        Genera grupos con la sensibilidad especificada.
        
        MUY RÁPIDO (< 1 segundo) porque solo hace clustering
        usando los hashes ya calculados.
        
        Args:
            sensitivity: Sensibilidad de detección (30-100)
                - 100: Solo imágenes idénticas
                - 85: Muy similares (recomendado)
                - 50: Similares
                - 30: Algo similares
        
        Returns:
            DuplicateAnalysisResult con grupos detectados
        """
        self._logger.debug(
            f"Generando grupos con sensibilidad {sensitivity}%"
        )
        
        # Convertir sensibilidad a threshold de Hamming distance
        threshold = self._sensitivity_to_threshold(sensitivity)
        
        # Clustering rápido usando hashes pre-calculados
        groups = self._cluster_by_similarity(
            self.perceptual_hashes,
            threshold,
            self._distance_cache
        )
        
        # Calcular estadísticas
        total_groups = len(groups)
        total_duplicates = sum(len(g.files) - 1 for g in groups) # Using total_duplicates for generic compat
        # Also maintain total_similar for specific logic if needed, but AnalysisResult uses generic fields mainly
        
        space_potential = sum(
            (len(g.files) - 1) * (g.total_size // len(g.files)) for g in groups
        )
        
        min_similarity = (
            min(g.similarity_score for g in groups)
            if groups else 0
        )
        max_similarity = (
            max(g.similarity_score for g in groups)
            if groups else 0
        )
        
        self._logger.info(
            f"Grupos generados: {total_groups}, "
            f"Duplicados: {total_duplicates}, "
            f"Similitud: {min_similarity:.0f}%-{max_similarity:.0f}%"
        )
        
        return DuplicateAnalysisResult(
            success=True,
            mode='perceptual',
            groups=groups,
            total_files=self.total_files,
            total_groups=total_groups,
            total_duplicates=total_duplicates, # Generic field
            space_wasted=space_potential
        )
    
    def _sensitivity_to_threshold(self, sensitivity: int) -> int:
        """
        Convierte sensibilidad (30-100) a threshold de Hamming distance.
        """
        max_distance = Config.MAX_HAMMING_THRESHOLD
        # Mapeo inverso: 100% sens = 0 threshold, 30% sens = 20 threshold
        normalized = (100 - sensitivity) / 70  # 70 = 100 - 30
        return int(max_distance * normalized)
    
    def _cluster_by_similarity(
        self,
        hashes: Dict[str, Dict[str, Any]],
        threshold: int,
        distance_cache: Dict[Tuple[int, int], int]
    ) -> List[DuplicateGroup]:
        """
        Agrupa archivos por similitud usando threshold de Hamming distance.
        """
        if not hashes:
            return []
        
        groups = []
        processed = set()
        
        paths = list(hashes.keys())
        
        for i, path1 in enumerate(paths):
            if path1 in processed:
                continue
            
            hash1 = hashes[path1]['hash']
            similar_files = [Path(path1)]
            hamming_distances = []
            
            for j, path2 in enumerate(paths[i + 1:], i + 1):
                if path2 in processed:
                    continue
                
                hash2 = hashes[path2]['hash']
                
                # Calcular o recuperar distancia del cache
                cache_key = (i, j)  # Siempre i < j
                
                if cache_key in distance_cache:
                    distance = distance_cache[cache_key]
                else:
                    distance = self._hamming_distance(hash1, hash2)
                    distance_cache[cache_key] = distance
                
                # Si es similar según threshold, añadir al grupo
                if distance <= threshold:
                    similar_files.append(Path(path2))
                    hamming_distances.append(distance)
                    processed.add(path2)
            
            # Si el grupo tiene más de 1 archivo, guardarlo
            if len(similar_files) > 1:
                try:
                    # Calcular score de similitud basado en distancia Hamming
                    avg_hamming = (
                        sum(hamming_distances) / len(hamming_distances)
                        if hamming_distances else 0
                    )
                    
                    max_theoretical_dist = 64
                    similarity_percentage = 100 - (avg_hamming / max_theoretical_dist * 100)
                    similarity_percentage = max(0, min(100, similarity_percentage))
                    
                    max_dist = Config.MAX_HAMMING_THRESHOLD
                    min_similarity_from_threshold = 100 - (threshold / max_dist * 100)
                    
                    if similarity_percentage < min_similarity_from_threshold:
                        continue
                    
                    total_size = 0
                    valid_files = []
                    for f in similar_files:
                        try:
                            # Try to get size from hashes dict first if available
                            size = hashes[str(f)]['size']
                            total_size += size
                            valid_files.append(f)
                        except (FileNotFoundError, PermissionError, KeyError):
                            # Fallback to disk or skip
                            if f.exists():
                                size = f.stat().st_size
                                total_size += size
                                valid_files.append(f)
                            continue
                    
                    if len(valid_files) > 1:
                        group = DuplicateGroup(
                            hash_value=str(hash1),
                            files=valid_files,
                            total_size=total_size,
                            similarity_score=similarity_percentage
                        )
                        groups.append(group)
                        processed.add(path1)
                except Exception as e:
                    self._logger.warning(f"Error procesando grupo para {path1}: {e}")
                    continue
        
        return groups
    
    def _hamming_distance(self, hash1: Any, hash2: Any) -> int:
        return hash1 - hash2
    
    def find_new_groups(
        self,
        new_hashes: Dict[str, Dict[str, Any]],
        existing_hashes: Dict[str, Dict[str, Any]],
        sensitivity: int
    ) -> DuplicateAnalysisResult:
        """
        Encuentra grupos que incluyan archivos del batch nuevo.
        
        Compara archivos nuevos contra existentes para análisis incremental
        sin reprocesar todo el dataset. Usado para carga progresiva en UI.
        
        Args:
            new_hashes: Hashes del batch actual a procesar
            existing_hashes: Hashes ya procesados previamente
            sensitivity: Sensibilidad de detección (30-100)
        
        Returns:
            DuplicateAnalysisResult con grupos que incluyen archivos nuevos
        """
        if not new_hashes:
            return DuplicateAnalysisResult(
                success=True,
                mode='perceptual',
                groups=[],
                total_files=0,
                total_groups=0,
                total_duplicates=0,
                space_wasted=0
            )
        
        # Combinar hashes para clustering
        all_hashes = {**existing_hashes, **new_hashes}
        
        # Convertir sensibilidad a threshold
        threshold = self._sensitivity_to_threshold(sensitivity)
        
        # Hacer clustering de todos los hashes
        all_groups = self._cluster_by_similarity(
            all_hashes,
            threshold,
            self._distance_cache
        )
        
        # Filtrar solo grupos que contengan al menos un archivo del batch nuevo
        new_paths = set(new_hashes.keys())
        filtered_groups = []
        
        for group in all_groups:
            # Verificar si algún archivo del grupo pertenece al batch nuevo
            group_paths = {str(f) for f in group.files}
            if group_paths & new_paths:  # Intersección no vacía
                filtered_groups.append(group)
        
        # Calcular estadísticas
        total_groups = len(filtered_groups)
        total_duplicates = sum(len(g.files) - 1 for g in filtered_groups)
        space_wasted = sum(
            (len(g.files) - 1) * (g.total_size // len(g.files))
            for g in filtered_groups
        )
        
        return DuplicateAnalysisResult(
            success=True,
            mode='perceptual',
            groups=filtered_groups,
            total_files=len(new_hashes),
            total_groups=total_groups,
            total_duplicates=total_duplicates,
            space_wasted=space_wasted
        )
        
    def save_to_file(self, filepath: Path) -> None:
        """Guarda el análisis en un archivo para carga rápida posterior."""
        import pickle
        
        # Preparar datos para guardar (sin logger)
        data = {
            'perceptual_hashes': {},
            'workspace_path': self.workspace_path,
            'total_files': self.total_files,
            'analysis_timestamp': self.analysis_timestamp,
        }
        
        # Convertir hashes a formato serializable
        for path, hash_data in self.perceptual_hashes.items():
            data['perceptual_hashes'][path] = {
                'hash_str': str(hash_data['hash']),  # Convertir hash a string
                'size': hash_data['size'],
                'modified': hash_data['modified']
            }
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        self._logger.info(
            f"💾 Análisis guardado en {filepath} "
            f"({len(self.perceptual_hashes)} hashes, "
            f"{filepath.stat().st_size / 1024:.1f} KB)"
        )
    
    @classmethod
    def load_from_file(cls, filepath: Path) -> 'DuplicatesSimilarAnalysis':
        """Carga un análisis previamente guardado."""
        import pickle
        import imagehash
        
        if not filepath.exists():
            raise FileNotFoundError(f"Archivo de caché no encontrado: {filepath}")
        
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        # Crear nueva instancia
        analysis = cls()
        analysis.workspace_path = data['workspace_path']
        analysis.total_files = data['total_files']
        analysis.analysis_timestamp = data['analysis_timestamp']
        
        # Reconstruir hashes desde strings
        for path, hash_data in data['perceptual_hashes'].items():
            analysis.perceptual_hashes[path] = {
                'hash': imagehash.hex_to_hash(hash_data['hash_str']),
                'size': hash_data['size'],
                'modified': hash_data['modified']
            }
        
        logger = get_logger('DuplicatesSimilarAnalysis')
        logger.info(
            f"✅ Análisis cargado desde {filepath} "
            f"({analysis.total_files} archivos, "
            f"{filepath.stat().st_size / 1024:.1f} KB)"
        )
        
        return analysis


class DuplicatesSimilarService(DuplicatesBaseService):
    """
    Servicio de detección de archivos similares mediante perceptual hashing.
    """

    def __init__(self):
        """Inicializa el detector de archivos similares"""
        super().__init__('DuplicatesSimilarService')
        self._cached_analysis: Optional[DuplicatesSimilarAnalysis] = None
    
    def analyze(
        self,
        sensitivity: int = 85,
        progress_callback: Optional[ProgressCallback] = None,
        **kwargs
    ) -> DuplicateAnalysisResult:
        """
        Analiza buscando duplicados similares (perceptual hash).
        
        Este es el método estándar compatible con el patrón de otros servicios.
        Calcula hashes perceptuales y genera grupos con la sensibilidad especificada.
        
        Args:
            sensitivity: Sensibilidad de detección (30-100, default 85)
                - 100: Solo imágenes idénticas
                - 85: Muy similares (recomendado)
                - 50: Similares
                - 30: Algo similares
            progress_callback: Callback de progreso
            **kwargs: Args adicionales
            
        Returns:
            DuplicateAnalysisResult con grupos detectados
        """
        log_section_header_discrete(self.logger, "ANÁLISIS DE DUPLICADOS SIMILARES")
        self.logger.info(f"Sensibilidad configurada: {sensitivity}%")
        
        # Fase 1: Calcular hashes perceptuales
        repo = FileInfoRepositoryCache.get_instance()
        if self._cached_analysis is None:
            self._cached_analysis = self._calculate_perceptual_hashes(repo, progress_callback)
        else:
            self.logger.info("Reutilizando análisis de hashes perceptuales previo en memoria")

        # Fase 2: Generar grupos con sensibilidad especificada
        result = self._cached_analysis.get_groups(sensitivity)
        
        log_section_footer_discrete(self.logger, "ANÁLISIS DE DUPLICADOS SIMILARES COMPLETADO")
        return result
    
    def get_analysis_for_dialog(
        self,
        progress_callback: Optional[ProgressCallback] = None
    ) -> DuplicatesSimilarAnalysis:
        """
        Obtiene objeto DuplicatesSimilarAnalysis para uso interactivo en diálogos.
        
        Permite ajustar sensibilidad en tiempo real sin recalcular hashes.
        Este método es específico para el flujo de UI con ajuste dinámico.
        
        Args:
            progress_callback: Callback de progreso para cálculo de hashes
            
        Returns:
            DuplicatesSimilarAnalysis con hashes precalculados
        """
        repo = FileInfoRepositoryCache.get_instance()
        if self._cached_analysis is None:
            self._cached_analysis = self._calculate_perceptual_hashes(repo, progress_callback)
        else:
            self.logger.info("Reutilizando análisis de hashes perceptuales previo en memoria")
        
        return self._cached_analysis

    def _calculate_perceptual_hashes(
        self,
        repo: FileInfoRepositoryCache,
        progress_callback: Optional[ProgressCallback] = None
    ) -> DuplicatesSimilarAnalysis:
        """
        Calcula hashes perceptuales de todos los archivos.
        
        Método interno usado por analyze() y get_analysis_for_dialog().
        """
        try:
            import imagehash
        except ImportError:
            self.logger.error("imagehash library not installed.")
            raise ImportError("imagehash library not installed.")
        
        log_section_header_discrete(self.logger, "INICIANDO ANÁLISIS INICIAL DE ARCHIVOS SIMILARES")
        self.logger.info("*** Calculando hashes perceptuales...")
        
        # 1. Obtener archivos desde FileInfoRepository
        all_metadata = repo.get_all_files()
        
        image_files = []
        video_files = []
        
        supported_img = Config.SUPPORTED_IMAGE_EXTENSIONS
        supported_vid = Config.SUPPORTED_VIDEO_EXTENSIONS
        
        for meta in all_metadata:
            # Check extension (case sensitive in set? Config sets have uppercase variants)
            if meta.extension in supported_img:
                image_files.append(meta.path)
            elif meta.extension in supported_vid:
                video_files.append(meta.path)
        
        total_files = len(image_files) + len(video_files)
        
        self.logger.info(
            f"Archivos a procesar: {total_files} "
            f"({len(image_files)} imágenes, {len(video_files)} videos)"
        )
        
        analysis = DuplicatesSimilarAnalysis()
        
        if total_files == 0:
            self.logger.warning("No se encontraron archivos soportados en caché")
            analysis.total_files = 0
            analysis.analysis_timestamp = datetime.now()
            return analysis
        
        # 2. Calcular hashes perceptuales en paralelo
        perceptual_hashes = {}
        processed = 0
        errors = 0
        timeouts = 0
        
        with self._parallel_processor(io_bound=False) as executor:
            future_to_file = {}
            for file_path in image_files:
                future = executor.submit(self._calculate_perceptual_hash, file_path)
                future_to_file[future] = file_path
            
            for file_path in video_files:
                future = executor.submit(self._calculate_video_hash, file_path)
                future_to_file[future] = file_path
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    phash = future.result(timeout=5.0)
                    if phash:
                        # Obtener tamaño desde cache si es posible para evitar stat
                        meta = repo.get_file_metadata(file_path)
                        size = meta.fs_size if meta else file_path.stat().st_size
                        mtime = meta.fs_mtime if meta else file_path.stat().st_mtime
                        
                        perceptual_hashes[str(file_path)] = {
                            'hash': phash,
                            'size': size,
                            'modified': mtime
                        }
                    
                    processed += 1
                    if self._should_report_progress(processed, interval=10):
                        if not self._report_progress(
                            progress_callback,
                            processed,
                            total_files,
                            f"Procesado: {file_path.name}"
                        ):
                            break
                except TimeoutError:
                    timeouts += 1
                    processed += 1
                    self.logger.warning(f"Timeout procesando {file_path.name}")
                except Exception as e:
                    errors += 1
                    processed += 1
                    self.logger.debug(f"Error procesando {file_path.name}: {e}")
        
        analysis.perceptual_hashes = perceptual_hashes
        analysis.total_files = len(perceptual_hashes)
        analysis.analysis_timestamp = datetime.now()
        
        # Log stats
        self.logger.info(f"*** Hashes calculados: {analysis.total_files}")
        
        return analysis

    def _calculate_perceptual_hash(self, file_path: Path) -> Optional[Any]:
        """Calcula perceptual hash de una imagen"""
        try:
            import imagehash
            from PIL import Image
            
            with Image.open(file_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                return imagehash.phash(img)
        except Exception:
            return None

    def _calculate_video_hash(self, file_path: Path) -> Optional[Any]:
        """Calcula perceptual hash de un video"""
        # (Implementación simplificada para brevedad)
        try:
            import cv2
            import imagehash
            from PIL import Image
            import os
            
            os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'
            cap = cv2.VideoCapture(str(file_path))
            if not cap.isOpened(): return None
            
            # Using property ID 7 which is FRAME_COUNT
            total_frames = int(cap.get(7)) 
            if total_frames == 0:
                cap.release()
                return None
            
            # Property ID 1 is POS_FRAMES
            cap.set(1, total_frames // 2)
            ret, frame = cap.read()
            cap.release()
            
            if not ret: return None
            
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            return imagehash.phash(img)
        except Exception:
            return None
