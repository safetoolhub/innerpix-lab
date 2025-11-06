"""
Orchestrator de análisis de directorios.
Coordina múltiples servicios para realizar análisis completos sin dependencias de UI.
"""
from pathlib import Path
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass, field
import time

from config import Config
from utils.logger import get_logger


@dataclass
class DirectoryScanResult:
    """Resultado del escaneo inicial de directorio"""
    total_files: int
    images: List[Path] = field(default_factory=list)
    videos: List[Path] = field(default_factory=list)
    others: List[Path] = field(default_factory=list)
    
    @property
    def image_count(self) -> int:
        return len(self.images)
    
    @property
    def video_count(self) -> int:
        return len(self.videos)
    
    @property
    def other_count(self) -> int:
        return len(self.others)


@dataclass
class PhaseTimingInfo:
    """Información de timing de una fase del análisis"""
    phase_id: str
    phase_name: str
    start_time: float
    end_time: float
    duration: float
    
    def needs_delay(self, min_duration: float = 2.0) -> float:
        """
        Calcula si necesita delay para alcanzar duración mínima.
        
        Args:
            min_duration: Duración mínima en segundos
            
        Returns:
            Segundos de delay necesarios (0 si no necesita)
        """
        if self.duration >= min_duration:
            return 0.0
        return min_duration - self.duration


@dataclass
class FullAnalysisResult:
    """Resultado completo de análisis de directorio"""
    directory: Path
    scan: DirectoryScanResult
    phase_timings: Dict[str, PhaseTimingInfo] = field(default_factory=dict)
    renaming: Optional[Any] = None
    live_photos: Optional[Dict] = None
    organization: Optional[Any] = None
    heic: Optional[Any] = None
    duplicates: Optional[Any] = None
    total_duration: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario para compatibilidad con código existente"""
        return {
            'stats': {
                'total': self.scan.total_files,
                'images': self.scan.image_count,
                'videos': self.scan.video_count,
                'others': self.scan.other_count
            },
            'renaming': self.renaming,
            'live_photos': self.live_photos,
            'organization': self.organization,
            'heic': self.heic,
            'duplicates': self.duplicates,
            'phase_timings': {k: {
                'phase_id': v.phase_id,
                'phase_name': v.phase_name,
                'duration': v.duration,
                'start_time': v.start_time,
                'end_time': v.end_time
            } for k, v in self.phase_timings.items()},
            'total_duration': self.total_duration
        }


class AnalysisOrchestrator:
    """
    Coordina múltiples servicios de análisis para obtener información completa
    de un directorio sin dependencias de UI.
    
    Este servicio puede usarse en:
    - Workers (con callbacks para UI)
    - Scripts CLI (con callbacks para print)
    - Tests (con callbacks para validación)
    """
    
    def __init__(self):
        self.logger = get_logger('AnalysisOrchestrator')
    
    def scan_directory(self, 
                      directory: Path,
                      progress_callback: Optional[Callable[[int, int, str], bool]] = None) -> DirectoryScanResult:
        """
        Escanea un directorio y clasifica archivos por tipo.
        
        Args:
            directory: Directorio a escanear
            progress_callback: Función opcional (current, total, message) -> bool.
                             Retorna False para cancelar.
        
        Returns:
            DirectoryScanResult con archivos clasificados
            
        Example:
            >>> orchestrator = AnalysisOrchestrator()
            >>> result = orchestrator.scan_directory(Path("/photos"))
            >>> print(f"Imágenes: {result.image_count}")
        """
        self.logger.info(f"Escaneando directorio: {directory}")
        
        # Listar todos los archivos
        all_files = list(directory.rglob("*"))
        files_only = [f for f in all_files if f.is_file()]
        total_files = len(files_only)
        
        images, videos, others = [], [], []
        processed = 0
        
        for f in all_files:
            # Verificar cancelación
            if progress_callback and not progress_callback(processed, total_files, "Escaneando archivos"):
                self.logger.warning("Escaneo cancelado por usuario")
                break
            
            if f.is_file():
                if Config.is_image_file(f.name):
                    images.append(f)
                elif Config.is_video_file(f.name):
                    videos.append(f)
                else:
                    others.append(f)
                
                processed += 1
                
                # Reportar progreso cada 10 archivos
                if processed % 10 == 0 and progress_callback:
                    progress_callback(processed, total_files, "Escaneando archivos")
        
        result = DirectoryScanResult(
            total_files=total_files,
            images=images,
            videos=videos,
            others=others
        )
        
        self.logger.info(
            f"Escaneo completado: {result.image_count} imágenes, "
            f"{result.video_count} videos, {result.other_count} otros"
        )
        
        return result
    
    def analyze_renaming(self,
                        directory: Path,
                        renamer,
                        progress_callback: Optional[Callable[[int, int, str], bool]] = None):
        """
        Analiza nombres de archivos que necesitan normalización.
        
        Args:
            directory: Directorio a analizar
            renamer: Instancia de FileRenamer
            progress_callback: Función opcional de progreso
            
        Returns:
            Resultado del análisis de renombrado
        """
        self.logger.info("Analizando nombres de archivos")
        return renamer.analyze_directory(directory, progress_callback=progress_callback)
    
    def analyze_live_photos(self, 
                           directory: Path,
                           detector,
                           progress_callback: Optional[Callable[[int, int, str], bool]] = None) -> Dict:
        """
        Detecta grupos de Live Photos en el directorio.
        
        Args:
            directory: Directorio a analizar
            detector: Instancia de LivePhotoDetector
            progress_callback: Función opcional de progreso
            
        Returns:
            Dict con grupos de Live Photos y estadísticas
        """
        self.logger.info("Detectando Live Photos")
        
        lp_groups = detector.detect_in_directory(directory, progress_callback=progress_callback)
        
        # Calcular estadísticas
        total_space = sum(group.total_size for group in lp_groups)
        video_space = sum(group.video_size for group in lp_groups)
        
        result = {
            'groups': [
                {
                    'image_path': str(group.image_path),
                    'video_path': str(group.video_path),
                    'base_name': group.base_name,
                    'total_size': group.total_size,
                    'video_size': group.video_size,
                    'image_size': group.image_size
                }
                for group in lp_groups
            ],
            'total_space': total_space,
            'space_to_free': video_space,
            'live_photos_found': len(lp_groups)
        }
        
        self.logger.info(f"Encontrados {len(lp_groups)} grupos de Live Photos")
        return result
    
    def analyze_organization(self,
                            directory: Path,
                            organizer,
                            organization_type=None,
                            progress_callback: Optional[Callable[[int, int, str], bool]] = None):
        """
        Analiza estructura de directorios para organización.
        
        Args:
            directory: Directorio a analizar
            organizer: Instancia de FileOrganizer
            organization_type: Tipo de organización (opcional)
            progress_callback: Función opcional de progreso
            
        Returns:
            Resultado del análisis de organización
        """
        self.logger.info(f"Analizando estructura de directorios (tipo: {organization_type})")
        
        if organization_type:
            return organizer.analyze_directory_structure(
                directory,
                organization_type=organization_type,
                progress_callback=progress_callback
            )
        else:
            return organizer.analyze_directory_structure(directory, progress_callback=progress_callback)
    
    def analyze_heic_duplicates(self,
                               directory: Path,
                               heic_remover,
                               progress_callback: Optional[Callable[[int, int, str], bool]] = None):
        """
        Busca duplicados HEIC/JPG.
        
        Args:
            directory: Directorio a analizar
            heic_remover: Instancia de HEICDuplicateRemover
            progress_callback: Función opcional de progreso
            
        Returns:
            Resultado del análisis de duplicados HEIC
        """
        self.logger.info("Buscando duplicados HEIC/JPG")
        return heic_remover.analyze_heic_duplicates(directory, progress_callback=progress_callback)
    
    def analyze_exact_duplicates(self,
                                 directory: Path,
                                 duplicate_detector,
                                 progress_callback: Optional[Callable[[int, int, str], bool]] = None):
        """
        Detecta duplicados exactos usando SHA256.
        
        Args:
            directory: Directorio a analizar
            duplicate_detector: Instancia de DuplicateDetector
            progress_callback: Función opcional de progreso
            
        Returns:
            Resultado del análisis de duplicados exactos
        """
        self.logger.info("Detectando duplicados exactos (SHA256)")
        return duplicate_detector.analyze_exact_duplicates(
            directory,
            progress_callback=progress_callback
        )
    
    def run_full_analysis(self,
                         directory: Path,
                         renamer=None,
                         lp_detector=None,
                         organizer=None,
                         heic_remover=None,
                         duplicate_detector=None,
                         organization_type=None,
                         progress_callback: Optional[Callable[[int, int, str], bool]] = None,
                         phase_callback: Optional[Callable[[str], None]] = None,
                         partial_callback: Optional[Callable[[str, Any], None]] = None) -> FullAnalysisResult:
        """
        Ejecuta análisis completo del directorio coordinando todos los servicios.
        
        Args:
            directory: Directorio a analizar
            renamer: FileRenamer opcional
            lp_detector: LivePhotoDetector opcional
            organizer: FileOrganizer opcional
            heic_remover: HEICDuplicateRemover opcional
            duplicate_detector: DuplicateDetector opcional
            organization_type: Tipo de organización opcional
            progress_callback: Callback (current, total, msg) -> bool para progreso
            phase_callback: Callback (phase_name) para cambios de fase
            partial_callback: Callback (phase_name, result) para resultados parciales
            
        Returns:
            FullAnalysisResult con todos los resultados y timing info
            
        Example:
            >>> orchestrator = AnalysisOrchestrator()
            >>> result = orchestrator.run_full_analysis(
            ...     Path("/photos"),
            ...     renamer=FileRenamer(),
            ...     phase_callback=lambda p: print(f"Fase: {p}")
            ... )
            >>> print(f"Total archivos: {result.scan.total_files}")
        """
        self.logger.info(f"=== Iniciando análisis completo de: {directory} ===")
        analysis_start_time = time.time()
        
        # Fase 1: Escaneo inicial
        if phase_callback:
            phase_callback("scan")
        
        phase_start = time.time()
        scan_result = self.scan_directory(directory, progress_callback)
        phase_end = time.time()
        
        # Crear resultado con timing de escaneo
        result = FullAnalysisResult(
            directory=directory,
            scan=scan_result
        )
        
        result.phase_timings['scan'] = PhaseTimingInfo(
            phase_id='scan',
            phase_name='Escaneo de archivos',
            start_time=phase_start,
            end_time=phase_end,
            duration=phase_end - phase_start
        )
        
        if partial_callback:
            partial_callback('scan', {
                'total': scan_result.total_files,
                'images': scan_result.image_count,
                'videos': scan_result.video_count,
                'others': scan_result.other_count
            })
        
        # Fase 2: Análisis de renombrado
        if renamer:
            if progress_callback and not progress_callback(0, 0, ""):
                result.total_duration = time.time() - analysis_start_time
                return result
            
            if phase_callback:
                phase_callback("renaming")
            
            phase_start = time.time()
            result.renaming = self.analyze_renaming(directory, renamer, progress_callback)
            phase_end = time.time()
            
            result.phase_timings['renaming'] = PhaseTimingInfo(
                phase_id='renaming',
                phase_name='Análisis de nombres',
                start_time=phase_start,
                end_time=phase_end,
                duration=phase_end - phase_start
            )
            
            if partial_callback:
                partial_callback('renaming', result.renaming)
        
        # Fase 3: Live Photos
        if lp_detector:
            if progress_callback and not progress_callback(0, 0, ""):
                result.total_duration = time.time() - analysis_start_time
                return result
            
            if phase_callback:
                phase_callback("live_photos")
            
            phase_start = time.time()
            result.live_photos = self.analyze_live_photos(directory, lp_detector, progress_callback)
            phase_end = time.time()
            
            result.phase_timings['live_photos'] = PhaseTimingInfo(
                phase_id='live_photos',
                phase_name='Detección de Live Photos',
                start_time=phase_start,
                end_time=phase_end,
                duration=phase_end - phase_start
            )
            
            if partial_callback:
                partial_callback('live_photos', result.live_photos)
        
        # Fase 4: Duplicados HEIC
        if heic_remover:
            if progress_callback and not progress_callback(0, 0, ""):
                result.total_duration = time.time() - analysis_start_time
                return result
            
            if phase_callback:
                phase_callback("heic")
            
            phase_start = time.time()
            result.heic = self.analyze_heic_duplicates(directory, heic_remover, progress_callback)
            phase_end = time.time()
            
            result.phase_timings['heic'] = PhaseTimingInfo(
                phase_id='heic',
                phase_name='Duplicados HEIC/JPG',
                start_time=phase_start,
                end_time=phase_end,
                duration=phase_end - phase_start
            )
            
            if partial_callback:
                partial_callback('heic', result.heic)
        
        # Fase 5: Duplicados exactos
        if duplicate_detector:
            if progress_callback and not progress_callback(0, 0, ""):
                result.total_duration = time.time() - analysis_start_time
                return result
            
            if phase_callback:
                phase_callback("duplicates")
            
            phase_start = time.time()
            result.duplicates = self.analyze_exact_duplicates(directory, duplicate_detector, progress_callback)
            phase_end = time.time()
            
            result.phase_timings['duplicates'] = PhaseTimingInfo(
                phase_id='duplicates',
                phase_name='Duplicados exactos',
                start_time=phase_start,
                end_time=phase_end,
                duration=phase_end - phase_start
            )
            
            if partial_callback:
                partial_callback('duplicates', result.duplicates)
        
        # Fase 6: Organización
        if organizer:
            if progress_callback and not progress_callback(0, 0, ""):
                result.total_duration = time.time() - analysis_start_time
                return result
            
            if phase_callback:
                phase_callback("organization")
            
            phase_start = time.time()
            result.organization = self.analyze_organization(directory, organizer, organization_type, progress_callback)
            phase_end = time.time()
            
            result.phase_timings['organization'] = PhaseTimingInfo(
                phase_id='organization',
                phase_name='Análisis de organización',
                start_time=phase_start,
                end_time=phase_end,
                duration=phase_end - phase_start
            )
            
            if partial_callback:
                partial_callback('organization', result.organization)
        
        # Fase 7: Finalización
        if phase_callback:
            phase_callback("finalizing")
        
        phase_start = time.time()
        # Aquí podríamos hacer cualquier procesamiento final si fuera necesario
        phase_end = time.time()
        
        result.phase_timings['finalizing'] = PhaseTimingInfo(
            phase_id='finalizing',
            phase_name='Finalizando análisis',
            start_time=phase_start,
            end_time=phase_end,
            duration=phase_end - phase_start
        )
        
        result.total_duration = time.time() - analysis_start_time
        
        self.logger.info(
            f"=== Análisis completo finalizado en {result.total_duration:.2f}s ==="
        )
        return result
