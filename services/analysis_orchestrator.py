"""
Orchestrator de análisis de directorios.
Coordina múltiples servicios para realizar análisis completos sin dependencias de UI.
"""
from pathlib import Path
from typing import Optional, Callable, Dict, List, Any
from dataclasses import dataclass, field

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
class FullAnalysisResult:
    """Resultado completo de análisis de directorio"""
    directory: Path
    scan: DirectoryScanResult
    renaming: Optional[Any] = None
    live_photos: Optional[Dict] = None
    organization: Optional[Any] = None
    heic: Optional[Any] = None
    duplicates: Optional[Any] = None
    
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
            'duplicates': self.duplicates
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
                           detector) -> Dict:
        """
        Detecta grupos de Live Photos en el directorio.
        
        Args:
            directory: Directorio a analizar
            detector: Instancia de LivePhotoDetector
            
        Returns:
            Dict con grupos de Live Photos y estadísticas
        """
        self.logger.info("Detectando Live Photos")
        
        lp_groups = detector.detect_in_directory(directory)
        
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
                            organization_type=None):
        """
        Analiza estructura de directorios para organización.
        
        Args:
            directory: Directorio a analizar
            organizer: Instancia de FileOrganizer
            organization_type: Tipo de organización (opcional)
            
        Returns:
            Resultado del análisis de organización
        """
        self.logger.info(f"Analizando estructura de directorios (tipo: {organization_type})")
        
        if organization_type:
            return organizer.analyze_directory_structure(
                directory,
                organization_type=organization_type
            )
        else:
            return organizer.analyze_directory_structure(directory)
    
    def analyze_heic_duplicates(self,
                               directory: Path,
                               heic_remover):
        """
        Busca duplicados HEIC/JPG.
        
        Args:
            directory: Directorio a analizar
            heic_remover: Instancia de HEICDuplicateRemover
            
        Returns:
            Resultado del análisis de duplicados HEIC
        """
        self.logger.info("Buscando duplicados HEIC/JPG")
        return heic_remover.analyze_heic_duplicates(directory)
    
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
            FullAnalysisResult con todos los resultados
            
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
        
        # Fase 1: Escaneo inicial
        if phase_callback:
            phase_callback("📂 Escaneando archivos...")
        
        scan_result = self.scan_directory(directory, progress_callback)
        
        if partial_callback:
            partial_callback('stats', {
                'total': scan_result.total_files,
                'images': scan_result.image_count,
                'videos': scan_result.video_count,
                'others': scan_result.other_count
            })
        
        # Crear resultado
        result = FullAnalysisResult(
            directory=directory,
            scan=scan_result
        )
        
        # Fase 2: Análisis de renombrado
        if renamer:
            if progress_callback and not progress_callback(0, 0, ""):
                return result
            
            if phase_callback:
                phase_callback("📝 Analizando nombres de archivos...")
            
            result.renaming = self.analyze_renaming(directory, renamer, progress_callback)
            
            if partial_callback:
                partial_callback('renaming', result.renaming)
        
        # Fase 3: Live Photos
        if lp_detector:
            if progress_callback and not progress_callback(0, 0, ""):
                return result
            
            if phase_callback:
                phase_callback("📱 Detectando Live Photos...")
            
            result.live_photos = self.analyze_live_photos(directory, lp_detector)
            
            if partial_callback:
                partial_callback('live_photos', result.live_photos)
        
        # Fase 4: Organización
        if organizer:
            if progress_callback and not progress_callback(0, 0, ""):
                return result
            
            if phase_callback:
                phase_callback("📁 Analizando estructura de directorios para organización...")
            
            result.organization = self.analyze_organization(directory, organizer, organization_type)
            
            if partial_callback:
                partial_callback('organization', result.organization)
        
        # Fase 5: Duplicados HEIC
        if heic_remover:
            if progress_callback and not progress_callback(0, 0, ""):
                return result
            
            if phase_callback:
                phase_callback("🖼️ Buscando duplicados HEIC/JPG...")
            
            result.heic = self.analyze_heic_duplicates(directory, heic_remover)
            
            if partial_callback:
                partial_callback('heic', result.heic)
        
        # Fase 6: Duplicados exactos
        if duplicate_detector:
            if progress_callback and not progress_callback(0, 0, ""):
                return result
            
            if phase_callback:
                phase_callback("🔍 Detectando duplicados exactos...")
            
            result.duplicates = self.analyze_exact_duplicates(directory, duplicate_detector, progress_callback)
            
            if partial_callback:
                partial_callback('duplicates', result.duplicates)
        
        self.logger.info("=== Análisis completo finalizado ===")
        return result
