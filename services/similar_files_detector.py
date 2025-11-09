"""
Servicio de detección de archivos similares mediante perceptual hashing.
Identifica fotos y vídeos visualmente similares: recortes, rotaciones,
ediciones o diferentes resoluciones.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Callable, Optional, Any, Dict, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import Config
from utils.logger import get_logger
from utils.callback_utils import safe_progress_callback
from services.result_types import DuplicateAnalysisResult, DuplicateDeletionResult


@dataclass
class DuplicateGroup:
    """Grupo de archivos similares (pero no necesariamente idénticos)"""
    hash_value: str  # Perceptual hash
    files: List[Path]
    total_size: int
    similarity_score: float  # Porcentaje de similitud (0-100)
    
    @property
    def file_count(self) -> int:
        """Retorna el número de archivos en el grupo"""
        return len(self.files)


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


class SimilarFilesDetector:
    """
    Servicio de detección de archivos similares mediante perceptual hashing.
    
    Detecta fotos y vídeos visualmente similares: recortes, rotaciones,
    ediciones o diferentes resoluciones. No requiere que sean idénticos
    digitalmente.
    
    El detector ahora usa un enfoque de dos fases:
    1. analyze_initial(): Calcula hashes perceptuales (operación costosa)
    2. SimilarFilesAnalysis.get_groups(): Clustering rápido con sensibilidad
    """

    def __init__(self):
        """Inicializa el detector de archivos similares"""
        self.logger = get_logger('SimilarFilesDetector')
    
    def analyze_initial(
        self,
        workspace_path: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
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
        
        self.logger.info("=" * 80)
        self.logger.info(
            "*** INICIANDO ANÁLISIS INICIAL DE ARCHIVOS SIMILARES"
        )
        self.logger.info("*** Calculando hashes perceptuales...")
        self.logger.info("=" * 80)
        
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
                    safe_progress_callback(
                        progress_callback,
                        processed,
                        total_files,
                        f"Procesado: {file_path.name}"
                    )
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
        
        self.logger.info("=" * 80)
        self.logger.info(
            "*** ANÁLISIS INICIAL COMPLETADO"
        )
        self.logger.info(
            f"*** Hashes calculados: {analysis.total_files}"
        )
        self.logger.info(
            "*** Ahora puedes generar grupos con cualquier sensibilidad"
        )
        self.logger.info("=" * 80)
        
        return analysis

    def analyze_similar_duplicates(
        self,
        directory: Path,
        sensitivity: int = 10,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
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

    def execute_deletion(
        self,
        groups: List[DuplicateGroup],
        keep_strategy: str = 'oldest',
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> DuplicateDeletionResult:
        """
        Ejecuta eliminación de duplicados similares
        
        Args:
            groups: Grupos de duplicados similares
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
        self.logger.info("*** INICIANDO ELIMINACIÓN DE DUPLICADOS SIMILARES")
        self.logger.info(f"*** Estrategia: {keep_strategy}")
        if dry_run:
            self.logger.info("*** Modo: SIMULACIÓN")
        self.logger.info("=" * 80)
        
        backup_path = None
        if create_backup and not dry_run:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = Config.DEFAULT_BACKUP_DIR / f"duplicates_similar_backup_{timestamp}"
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
                                self.logger.info(f"[SIMULACIÓN] Eliminaría duplicado similar (manual): {file_path} ({format_size(file_size)}, {file_date_str})")
                            else:
                                if create_backup and backup_path:
                                    backup_file = backup_path / file_path.name
                                    shutil.copy2(file_path, backup_file)
                                
                                file_path.unlink()
                                deleted_files.append(file_path)
                                space_freed += file_size
                                self.logger.info(f"✓ Eliminado duplicado similar (manual): {file_path} ({format_size(file_size)}, {file_date_str})")
                            
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
                                self.logger.info(f"[SIMULACIÓN] Eliminaría duplicado similar: {file_path} ({format_size(file_size)}, {file_date_str})")
                            else:
                                if create_backup and backup_path:
                                    backup_file = backup_path / file_path.name
                                    shutil.copy2(file_path, backup_file)

                                file_path.unlink()
                                deleted_files.append(file_path)
                                space_freed += file_size
                                self.logger.info(f"✓ Eliminado duplicado similar: {file_path} ({format_size(file_size)}, {file_date_str})")
                            
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
            self.logger.info("*** SIMULACIÓN DE ELIMINACIÓN DE DUPLICADOS SIMILARES COMPLETADA")
            self.logger.info(f"*** Resultado: {files_count} archivos se eliminarían, {freed_str} se liberarían")
        else:
            self.logger.info("*** ELIMINACIÓN DE DUPLICADOS SIMILARES COMPLETADA")
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
