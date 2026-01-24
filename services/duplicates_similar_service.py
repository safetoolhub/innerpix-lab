"""
Servicio de detección de archivos similares mediante perceptual hashing.
Identifica fotos y vídeos visualmente similares: recortes, rotaciones,
ediciones o diferentes resoluciones.
Refactorizado para usar MetadataCache.
Optimizado con BK-Tree para clustering O(N log N).
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any, Dict, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import os

from config import Config
from utils.logger import get_logger, log_section_header_discrete, log_section_footer_discrete
from services.result_types import DuplicateAnalysisResult, DuplicateExecutionResult, DuplicateGroup
from services.duplicates_base_service import DuplicatesBaseService
from services.base_service import ProgressCallback
from services.file_metadata_repository_cache import FileInfoRepositoryCache


class BKTreeNode:
    """
    Nodo de un BK-Tree (Burkhard-Keller Tree) para búsqueda métrica.
    Estructura de datos optimizada para búsquedas por distancia de Hamming.
    """
    def __init__(self, hash_value: Any, path: str):
        self.hash = hash_value
        self.path = path
        self.children: Dict[int, 'BKTreeNode'] = {}


class BKTree:
    """
    BK-Tree implementado para búsqueda eficiente de hashes perceptuales similares.
    
    Reduce complejidad de O(N²) a O(N log N) promedio para clustering.
    Basado en métrica de distancia de Hamming.
    """
    
    def __init__(self, distance_func):
        """
        Args:
            distance_func: Función para calcular distancia entre hashes (e.g., Hamming)
        """
        self.root: Optional[BKTreeNode] = None
        self.distance_func = distance_func
        self._size = 0
    
    def add(self, hash_value: Any, path: str) -> None:
        """Añade un hash al árbol."""
        if self.root is None:
            self.root = BKTreeNode(hash_value, path)
            self._size += 1
            return
        
        current = self.root
        while True:
            distance = self.distance_func(current.hash, hash_value)
            
            if distance in current.children:
                current = current.children[distance]
            else:
                current.children[distance] = BKTreeNode(hash_value, path)
                self._size += 1
                break
    
    def search(self, target_hash: Any, threshold: int) -> List[Tuple[str, int]]:
        """
        Busca todos los hashes dentro del threshold de distancia.
        
        Args:
            target_hash: Hash objetivo a buscar
            threshold: Distancia máxima permitida
            
        Returns:
            Lista de tuplas (path, distance) dentro del threshold
        """
        if self.root is None:
            return []
        
        results = []
        self._search_recursive(self.root, target_hash, threshold, results)
        return results
    
    def _search_recursive(
        self, 
        node: BKTreeNode, 
        target: Any, 
        threshold: int,
        results: List[Tuple[str, int]]
    ) -> None:
        """Búsqueda recursiva en el árbol."""
        distance = self.distance_func(node.hash, target)
        
        if distance <= threshold:
            results.append((node.path, distance))
        
        # Solo explorar ramas que puedan contener matches
        # Poda basada en desigualdad triangular
        min_dist = max(0, distance - threshold)
        max_dist = distance + threshold
        
        for child_dist, child_node in node.children.items():
            if min_dist <= child_dist <= max_dist:
                self._search_recursive(child_node, target, threshold, results)
    
    def __len__(self) -> int:
        return self._size


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
    
    def get_groups(
        self, 
        sensitivity: int,
        progress_callback: Optional[Any] = None
    ) -> DuplicateAnalysisResult:
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
            progress_callback: Callable opcional (current, total, message) -> bool
                Permite reportar progreso y mantener UI responsiva.
                Si retorna False, el proceso debe detenerse.
        
        Returns:
            DuplicateAnalysisResult con grupos detectados
        """
        import time
        start_time = time.time()
        
        self._logger.info(
            f"🔍 Iniciando clustering con sensibilidad {sensitivity}% para {len(self.perceptual_hashes)} archivos..."
        )
        
        # Convertir sensibilidad a threshold de Hamming distance
        threshold = self._sensitivity_to_threshold(sensitivity)
        
        # Clustering rápido usando hashes pre-calculados
        groups = self._cluster_by_similarity(
            self.perceptual_hashes,
            threshold,
            self._distance_cache,
            progress_callback
        )
        
        elapsed = time.time() - start_time
        self._logger.info(
            f"⚡ Clustering completado en {elapsed:.3f}s ({len(groups)} grupos encontrados)"
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
        distance_cache: Dict[Tuple[int, int], int],
        progress_callback: Optional[Any] = None
    ) -> List[DuplicateGroup]:
        """
        Agrupa archivos por similitud usando threshold de Hamming distance.
        
        Optimizado con BK-Tree: O(N log N) en promedio vs O(N²) anterior.
        
        Args:
            hashes: Dict con {path: {hash, size, ...}}
            threshold: Distancia Hamming máxima para considerar similares
            distance_cache: Cache de distancias (no usado actualmente con BK-Tree)
            progress_callback: Callable opcional (current, total, message) -> bool
        """
        import time
        
        if not hashes:
            return []
        
        total_files = len(hashes)
        
        # Fase 1: Construir BK-Tree para búsqueda eficiente
        tree_start = time.time()
        bk_tree = BKTree(distance_func=self._hamming_distance)
        
        paths = list(hashes.keys())
        
        # Reportar progreso durante construcción del árbol
        for i, path in enumerate(paths):
            bk_tree.add(hashes[path]['hash'], path)
            
            # Reportar cada 5% para no saturar la UI
            if progress_callback and i % max(1, total_files // 20) == 0:
                should_continue = progress_callback(
                    i, total_files, 
                    f"Construyendo índice... ({i:,}/{total_files:,})"
                )
                if should_continue is False:
                    return []
        
        tree_time = time.time() - tree_start
        self._logger.info(f"  🌲 BK-Tree construido: {len(bk_tree)} nodos en {tree_time:.3f}s")
        
        # Fase 2: Búsqueda y agrupación
        search_start = time.time()
        groups = []
        processed: Set[str] = set()
        total_searches = 0
        total_matches = 0
        files_searched = 0
        
        for path1 in paths:
            if path1 in processed:
                continue
            
            hash1 = hashes[path1]['hash']
            
            # Búsqueda eficiente de similares usando BK-Tree
            similar_matches = bk_tree.search(hash1, threshold)
            total_searches += 1
            total_matches += len(similar_matches)
            files_searched += 1
            
            # Reportar progreso cada 5% durante la búsqueda
            if progress_callback and files_searched % max(1, total_files // 20) == 0:
                should_continue = progress_callback(
                    files_searched, total_files,
                    f"Agrupando archivos similares... ({files_searched:,}/{total_files:,})"
                )
                if should_continue is False:
                    return groups  # Retornar lo que tengamos hasta ahora
            
            if len(similar_matches) <= 1:  # Solo encontró a sí mismo
                continue
            
            # Construir grupo con archivos similares no procesados
            similar_files = []
            hamming_distances = []
            
            for match_path, distance in similar_matches:
                if match_path not in processed:
                    similar_files.append(Path(match_path))
                    if match_path != path1:  # No contar distancia a sí mismo
                        hamming_distances.append(distance)
                    processed.add(match_path)
            
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
                except Exception as e:
                    self._logger.warning(f"Error procesando grupo para {path1}: {e}")
                    continue
        
        search_time = time.time() - search_start
        self._logger.info(
            f"  🔎 Búsquedas: {total_searches} archivos, {total_matches} matches totales en {search_time:.3f}s"
        )
        
        # Ordenar grupos priorizando aquellos con mayor diferencia de tamaño
        # Los grupos con imágenes de diferentes tamaños (ej. WhatsApp vs originales) son más relevantes
        def calculate_size_variation_score(group: DuplicateGroup) -> float:
            """
            Calcula un score basado en la variación de tamaño entre archivos del grupo.
            Retorna el porcentaje de diferencia entre el archivo más grande y el más pequeño.
            Score más alto = mayor prioridad.
            """
            if len(group.files) < 2:
                return 0.0
            
            # Obtener tamaños de todos los archivos
            sizes = []
            for f in group.files:
                try:
                    size = hashes[str(f)]['size']
                    sizes.append(size)
                except (KeyError, FileNotFoundError):
                    continue
            
            if len(sizes) < 2:
                return 0.0
            
            min_size = min(sizes)
            max_size = max(sizes)
            
            # Evitar división por cero
            if min_size == 0:
                return 0.0
            
            # Calcular y retornar diferencia porcentual
            size_diff_percent = ((max_size - min_size) / min_size) * 100
            return size_diff_percent
        
        # Ordenar grupos: primero los de mayor variación de tamaño
        groups.sort(key=calculate_size_variation_score, reverse=True)
        
        # Log de estadísticas de variación
        if groups:
            scores = [calculate_size_variation_score(g) for g in groups]
            max_variation = max(scores) if scores else 0
            avg_variation = sum(scores) / len(scores) if scores else 0
            self._logger.info(
                f"  📊 Variación de tamaño - Máx: {max_variation:.1f}%, Promedio: {avg_variation:.1f}%"
            )
        
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
        
        repo = FileInfoRepositoryCache.get_instance()
        if self._cached_analysis is None:
            self._cached_analysis = self._calculate_perceptual_hashes(
                repo,
                progress_callback,
                algorithm=Config.PERCEPTUAL_HASH_ALGORITHM,
                hash_size=Config.PERCEPTUAL_HASH_SIZE,
                target=Config.PERCEPTUAL_HASH_TARGET,
                highfreq_factor=Config.PERCEPTUAL_HASH_HIGHFREQ_FACTOR
            )
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
            self._cached_analysis = self._calculate_perceptual_hashes(
                repo,
                progress_callback,
                algorithm=Config.PERCEPTUAL_HASH_ALGORITHM,
                hash_size=Config.PERCEPTUAL_HASH_SIZE,
                target=Config.PERCEPTUAL_HASH_TARGET,
                highfreq_factor=Config.PERCEPTUAL_HASH_HIGHFREQ_FACTOR
            )
        else:
            self.logger.info("Reutilizando análisis de hashes perceptuales previo en memoria")
        
        return self._cached_analysis

    def _calculate_perceptual_hashes(
        self,
        repo: FileInfoRepositoryCache,
        progress_callback: Optional[ProgressCallback] = None,
        algorithm: str = "dhash",
        hash_size: int = 8,
        target: str = "images",
        highfreq_factor: int = 4
    ) -> DuplicatesSimilarAnalysis:
        """
        Calcula hashes perceptuales de todos los archivos.
        
        Método interno usado por analyze() y get_analysis_for_dialog().
        
        Args:
            repo: Repositorio de metadatos de archivos
            progress_callback: Callback de progreso
            algorithm: Algoritmo de hash ("dhash", "phash", "ahash")
            hash_size: Tamaño del hash (8, 16, 32)
            target: Target de archivos ("images", "videos", "both")
            highfreq_factor: Factor de alta frecuencia para phash (4, 8)
        
        Returns:
            DuplicatesSimilarAnalysis con hashes calculados
        """
        try:
            import imagehash
        except ImportError:
            self.logger.error("imagehash library not installed.")
            raise ImportError("imagehash library not installed.")
        
        import time
        
        log_section_header_discrete(self.logger, "INICIANDO ANÁLISIS INICIAL DE ARCHIVOS SIMILARES")
        hash_calc_start = time.time()
        self.logger.info(
            f"⏳ Calculando hashes perceptuales (algoritmo={algorithm}, "
            f"hash_size={hash_size}, target={target})..."
        )
        
        # 1. Obtener archivos desde FileInfoRepository
        all_metadata = repo.get_all_files()
        
        image_files = []
        video_files = []
        
        supported_img = Config.SUPPORTED_IMAGE_EXTENSIONS
        supported_vid = Config.SUPPORTED_VIDEO_EXTENSIONS
        
        for meta in all_metadata:
            if meta.extension in supported_img:
                image_files.append(meta.path)
            elif meta.extension in supported_vid:
                video_files.append(meta.path)
        
        # Filtrar según target configurado
        files_to_process_images = [] if target == "videos" else image_files
        files_to_process_videos = [] if target == "images" else video_files
        
        total_files = len(files_to_process_images) + len(files_to_process_videos)
        
        self.logger.info(
            f"Archivos a procesar: {total_files} "
            f"({len(files_to_process_images)} imágenes, {len(files_to_process_videos)} videos) "
            f"[target={target}]"
        )
        
        analysis = DuplicatesSimilarAnalysis()
        
        if total_files == 0:
            self.logger.warning("No se encontraron archivos soportados para procesar")
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
            
            # Procesar imágenes
            for file_path in files_to_process_images:
                future = executor.submit(
                    self._calculate_image_perceptual_hash,
                    file_path,
                    algorithm,
                    hash_size,
                    highfreq_factor
                )
                future_to_file[future] = file_path
            
            # Procesar videos
            for file_path in files_to_process_videos:
                future = executor.submit(
                    self._calculate_video_perceptual_hash,
                    file_path,
                    algorithm,
                    hash_size,
                    highfreq_factor
                )
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
        hash_calc_time = time.time() - hash_calc_start
        self.logger.info(
            f"✅ Hashes calculados: {analysis.total_files} en {hash_calc_time:.1f}s "
            f"({analysis.total_files/hash_calc_time:.1f} archivos/s)"
        )
        
        if errors > 0:
            self.logger.warning(f"⚠️  Errores: {errors}, Timeouts: {timeouts}")
        
        return analysis

    def _calculate_image_perceptual_hash(
        self,
        file_path: Path,
        algorithm: str = "dhash",
        hash_size: int = 8,
        highfreq_factor: int = 4
    ) -> Optional[Any]:
        """
        Calcula hash perceptual de una imagen.
        
        Args:
            file_path: Ruta al archivo de imagen
            algorithm: Algoritmo de hash ("dhash", "phash", "ahash")
            hash_size: Tamaño del hash (8, 16, 32). Mayor = más preciso pero más lento
            highfreq_factor: Factor de alta frecuencia para phash (solo aplica a phash)
        
        Returns:
            Hash perceptual de la imagen o None si hay error
        """
        try:
            import imagehash
            from PIL import Image
            
            with Image.open(file_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Seleccionar algoritmo de hash
                if algorithm == "phash":
                    return imagehash.phash(img, hash_size=hash_size, highfreq_factor=highfreq_factor)
                elif algorithm == "ahash":
                    return imagehash.average_hash(img, hash_size=hash_size)
                else:  # dhash (default)
                    return imagehash.dhash(img, hash_size=hash_size)
                    
        except Exception:
            return None

    def _calculate_video_perceptual_hash(
        self,
        file_path: Path,
        algorithm: str = "dhash",
        hash_size: int = 8,
        highfreq_factor: int = 4
    ) -> Optional[Any]:
        """
        Calcula hash perceptual de un video extrayendo el frame central.
        
        Args:
            file_path: Ruta al archivo de video
            algorithm: Algoritmo de hash ("dhash", "phash", "ahash")
            hash_size: Tamaño del hash (8, 16, 32). Mayor = más preciso pero más lento
            highfreq_factor: Factor de alta frecuencia para phash (solo aplica a phash)
        
        Returns:
            Hash perceptual del video (basado en frame central) o None si hay error
        """
        try:
            import cv2
            import imagehash
            from PIL import Image
            import os
            
            os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'
            cap = cv2.VideoCapture(str(file_path))
            if not cap.isOpened():
                return None
            
            # Property ID 7 = CAP_PROP_FRAME_COUNT
            total_frames = int(cap.get(7))
            if total_frames == 0:
                cap.release()
                return None
            
            # Property ID 1 = CAP_PROP_POS_FRAMES - buscar frame central
            cap.set(1, total_frames // 2)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return None
            
            # Convertir BGR a RGB para PIL
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            
            # Seleccionar algoritmo de hash
            if algorithm == "phash":
                return imagehash.phash(img, hash_size=hash_size, highfreq_factor=highfreq_factor)
            elif algorithm == "ahash":
                return imagehash.average_hash(img, hash_size=hash_size)
            else:  # dhash (default)
                return imagehash.dhash(img, hash_size=hash_size)
                
        except Exception:
            return None
