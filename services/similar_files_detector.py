"""
Servicio de detección de archivos similares mediante perceptual hashing.
Identifica fotos y vídeos visualmente similares: recortes, rotaciones,
ediciones o diferentes resoluciones.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Any, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from utils.logger import get_logger, log_section_header_discrete, log_section_footer_discrete
from utils.decorators import deprecated
from services.result_types import DuplicateAnalysisResult, DuplicateDeletionResult, DuplicateGroup
from services.base_detector_service import BaseDetectorService
from services.base_service import ProgressCallback


class SimilarFilesAnalysis:
    """
    Contiene hashes perceptuales y permite generar grupos con
    cualquier sensibilidad en tiempo real.
    
    Esta clase separa el análisis costoso (cálculo de hashes) del
    clustering rápido, permitiendo ajustar la sensibilidad
    interactivamente sin reanalizar.
    
    Attributes:
        perceptual_hashes: Dict con {file_path: hash_data}
        workspace_path: Ruta del workspace analizado
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
        self._logger = get_logger('SimilarFilesAnalysis')
    
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
        total_similar = sum(len(g.files) - 1 for g in groups)
        space_potential = sum(
            (len(g.files) - 1) * g.files[0].stat().st_size
            for g in groups if g.files
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
            f"Duplicados: {total_similar}, "
            f"Similitud: {min_similarity:.0f}%-{max_similarity:.0f}%"
        )
        
        return DuplicateAnalysisResult(
            success=True,
            mode='perceptual',
            groups=groups,
            total_files=self.total_files,
            total_groups=total_groups,
            total_similar=total_similar,
            space_potential=space_potential,
            sensitivity=sensitivity,
            min_similarity=float(min_similarity),
            max_similarity=float(max_similarity)
        )
    
    def _sensitivity_to_threshold(self, sensitivity: int) -> int:
        """
        Convierte sensibilidad (30-100) a threshold de Hamming distance.
        
        Args:
            sensitivity: Valor de sensibilidad (30-100)
        
        Returns:
            Threshold de Hamming distance (0-20)
        
        Notes:
            - Mayor sensibilidad = menor threshold = más estricto
            - Para hash de 64 bits, distancia máxima práctica = 20
            - Mapeo: 100% sens = 0 threshold, 30% sens = 20 threshold
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
        
        Args:
            hashes: Dict con {file_path: {'hash': value, ...}}
            threshold: Máxima distancia para considerar similares
            distance_cache: Cache de distancias ya calculadas
        
        Returns:
            Lista de grupos (DuplicateGroup)
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
                # Calcular score de similitud basado en distancia Hamming
                avg_hamming = (
                    sum(hamming_distances) / len(hamming_distances)
                    if hamming_distances else 0
                )
                # Convertir a porcentaje de similitud (invertido)
                max_dist = Config.MAX_HAMMING_THRESHOLD
                similarity_percentage = 100 - (avg_hamming / max_dist * 100)
                # Asegurar rango [0, 100]
                similarity_percentage = max(0, min(100, similarity_percentage))
                
                group = DuplicateGroup(
                    hash_value=str(hash1),
                    files=similar_files,
                    total_size=sum(
                        f.stat().st_size for f in similar_files
                    ),
                    similarity_score=similarity_percentage
                )
                groups.append(group)
                processed.add(path1)
        
        return groups
    
    def _hamming_distance(
        self,
        hash1: Any,
        hash2: Any
    ) -> int:
        """
        Calcula Hamming distance entre dos hashes.
        
        Extremadamente rápido (operación XOR + POPCNT).
        
        Args:
            hash1: Primer hash perceptual
            hash2: Segundo hash perceptual
        
        Returns:
            Distancia de Hamming (número de bits diferentes)
        """
        # imagehash implementa esto eficientemente con __sub__
        return hash1 - hash2


class SimilarFilesDetector(BaseDetectorService):
    """
    Servicio de detección de archivos similares mediante perceptual hashing.
    
    Detecta fotos y vídeos visualmente similares: recortes, rotaciones,
    ediciones o diferentes resoluciones. No requiere que sean idénticos
    digitalmente.
    
    El detector ahora usa un enfoque de dos fases:
    1. analyze_initial(): Calcula hashes perceptuales (operación costosa)
    2. SimilarFilesAnalysis.get_groups(): Clustering rápido con sensibilidad
    
    Hereda de BaseDetectorService para reutilizar lógica común de eliminación.
    """

    def __init__(self):
        """Inicializa el detector de archivos similares"""
        super().__init__('SimilarFilesDetector')
    
    def analyze(
        self,
        directory: Path,
        sensitivity: int = 10,
        progress_callback: Optional[ProgressCallback] = None
    ) -> DuplicateAnalysisResult:
        """
        Analiza directorio buscando duplicados similares (método unificado)
        
        Args:
            directory: Directorio a analizar
            sensitivity: Sensibilidad (0-20, menor = más estricto)
            progress_callback: Callback de progreso
            
        Returns:
            DuplicateAnalysisResult con grupos de duplicados similares
        """
        return self.analyze_similar_duplicates(directory, sensitivity, progress_callback)

    def analyze_initial(
        self,
        workspace_path: Path,
        progress_callback: Optional[ProgressCallback] = None
    ) -> SimilarFilesAnalysis:
        """
        Análisis inicial: Calcula solo hashes perceptuales.
        
        Esta es la operación costosa (~5 minutos para miles de archivos).
        El clustering posterior con diferentes sensibilidades es casi
        instantáneo.
        
        Args:
            workspace_path: Path del directorio a analizar
            progress_callback: Función callback(current, total, message)
        
        Returns:
            SimilarFilesAnalysis con hashes calculados
        
        Raises:
            ImportError: Si imagehash no está instalado
        """
        try:
            import imagehash
        except ImportError:
            self.logger.error(
                "imagehash no está instalado. "
                "Instala con: pip install imagehash"
            )
            raise ImportError(
                "imagehash library not installed. "
                "Install with: pip install imagehash"
            )
        
        log_section_header_discrete(self.logger, "INICIANDO ANÁLISIS INICIAL DE ARCHIVOS SIMILARES")
        self.logger.info("*** Calculando hashes perceptuales...")
        
        # 1. Escanear archivos de imagen y video
        image_files = []
        for ext in Config.SUPPORTED_IMAGE_EXTENSIONS:
            image_files.extend(workspace_path.rglob(f'*{ext}'))
        
        video_files = []
        for ext in Config.SUPPORTED_VIDEO_EXTENSIONS:
            video_files.extend(workspace_path.rglob(f'*{ext}'))
        
        all_files = image_files + video_files
        total_files = len(all_files)
        
        self.logger.info(
            f"Archivos a procesar: {total_files} "
            f"({len(image_files)} imágenes, {len(video_files)} videos)"
        )
        
        if total_files == 0:
            self.logger.warning("No se encontraron archivos para analizar")
            analysis = SimilarFilesAnalysis()
            analysis.workspace_path = str(workspace_path)
            analysis.total_files = 0
            analysis.analysis_timestamp = datetime.now()
            return analysis
        
        # 2. Calcular hashes perceptuales en paralelo (parte costosa)
        perceptual_hashes = {}
        processed = 0
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Crear futures para imágenes
            future_to_file = {}
            for file_path in image_files:
                future = executor.submit(
                    self._calculate_perceptual_hash,
                    file_path
                )
                future_to_file[future] = file_path
            
            # Crear futures para videos
            for file_path in video_files:
                future = executor.submit(
                    self._calculate_video_hash,
                    file_path
                )
                future_to_file[future] = file_path
            
            # Recopilar resultados
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    phash = future.result()
                    if phash:
                        perceptual_hashes[str(file_path)] = {
                            'hash': phash,
                            'size': file_path.stat().st_size,
                            'modified': file_path.stat().st_mtime
                        }
                    
                    processed += 1
                    if not self._report_progress(
                        progress_callback,
                        processed,
                        total_files,
                        f"Procesado: {file_path.name}"
                    ):
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                except Exception as e:
                    self.logger.error(
                        f"Error calculando hash perceptual de "
                        f"{file_path}: {e}"
                    )
        
        # 3. Crear objeto de análisis
        analysis = SimilarFilesAnalysis()
        analysis.perceptual_hashes = perceptual_hashes
        analysis.workspace_path = str(workspace_path)
        analysis.total_files = len(perceptual_hashes)
        analysis.analysis_timestamp = datetime.now()
        
        self.logger.info(
            "*** ANÁLISIS INICIAL COMPLETADO"
        )
        self.logger.info(
            f"*** Hashes calculados: {analysis.total_files}"
        )
        self.logger.info(
            "*** Ahora puedes generar grupos con cualquier sensibilidad"
        )
        log_section_footer_discrete(self.logger, "Análisis de hashes perceptuales completado")
        
        return analysis

    @deprecated(reason="Nomenclatura inconsistente", replacement="analyze()")
    def analyze_similar_duplicates(
        self,
        directory: Path,
        sensitivity: int = 10,
        progress_callback: Optional[ProgressCallback] = None
    ) -> DuplicateAnalysisResult:
        """
        Analiza directorio buscando duplicados similares (perceptual hash).
        
        Este método mantiene compatibilidad con el flujo anterior,
        pero internamente usa el nuevo enfoque de dos fases.
        
        Args:
            directory: Directorio a analizar
            sensitivity: Sensibilidad (0-20, menor = más estricto)
                        NOTA: Se convierte a escala 30-100 internamente
            progress_callback: Callback de progreso
            
        Returns:
            DuplicateAnalysisResult con grupos de duplicados similares
        """
        self.logger.info(
            "Iniciando análisis de duplicados similares "
            f"(sensibilidad legacy: {sensitivity})"
        )
        
        # Fase 1: Calcular hashes
        analysis = self.analyze_initial(directory, progress_callback)
        
        # Convertir sensibilidad de escala 0-20 a 30-100
        # 0 -> 100 (muy estricto)
        # 10 -> 85 (recomendado)
        # 20 -> 30 (permisivo)
        sensitivity_new_scale = 100 - int((sensitivity / 20) * 70)
        sensitivity_new_scale = max(30, min(100, sensitivity_new_scale))
        
        self.logger.info(
            f"Convirtiendo sensibilidad: {sensitivity} (0-20) -> "
            f"{sensitivity_new_scale} (30-100)"
        )
        
        # Fase 2: Generar grupos con sensibilidad especificada
        result = analysis.get_groups(sensitivity_new_scale)
        
        # Ajustar el campo sensitivity para reflejar el valor original
        result.sensitivity = sensitivity
        
        return result

    def _calculate_perceptual_hash(self, file_path: Path) -> Optional[Any]:
        """Calcula perceptual hash de una imagen"""
        try:
            import imagehash
            from PIL import Image
            
            with Image.open(file_path) as img:
                # Convertir a RGB si es necesario
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calcular perceptual hash (ahash es más rápido, phash más preciso)
                phash = imagehash.phash(img)
                return phash
        except Exception as e:
            self.logger.debug(f"Error calculando hash perceptual de {file_path}: {e}")
            return None

    def _calculate_video_hash(self, file_path: Path) -> Optional[Any]:
        """Calcula perceptual hash de un video (usando frame del medio)"""
        try:
            import cv2
            import imagehash
            from PIL import Image
            
            cap = cv2.VideoCapture(str(file_path))
            if not cap.isOpened():
                return None
            
            # Obtener frame del medio del video
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames == 0:
                cap.release()
                return None
            
            mid_frame = total_frames // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return None
            
            # Convertir BGR a RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            
            # Calcular perceptual hash
            phash = imagehash.phash(img)
            return phash
        except Exception as e:
            self.logger.debug(
                f"Error calculando hash de video {file_path}: {e}"
            )
            return None

    def _calculate_perceptual_hash(self, file_path: Path) -> Optional[Any]:
        """Calcula perceptual hash de una imagen"""
