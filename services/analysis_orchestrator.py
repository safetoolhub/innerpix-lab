"""
Orchestrator de análisis de directorios.
Coordina múltiples servicios para realizar análisis completos sin dependencias de UI.
"""
from pathlib import Path
from typing import Optional, Callable, Dict, List, Any, TYPE_CHECKING, Protocol
from dataclasses import dataclass, field
import time
import gc
import sys

from config import Config
from utils.logger import get_logger, log_section_header_discrete, log_section_footer_discrete
from services.metadata_cache import FileMetadataCache

# Type checking imports para evitar imports circulares
if TYPE_CHECKING:
    from services.result_types import (
        RenameAnalysisResult, 
        LivePhotoDetectionResult,
        OrganizationAnalysisResult, 
        HeicAnalysisResult, 
        DuplicateAnalysisResult,
        ZeroByteAnalysisResult
    )


# Protocols para definir interfaces de servicios sin imports circulares
class AnalyzableService(Protocol):
    """Protocolo para servicios que implementan analyze()"""
    def analyze(self, 
               directory: Path,
               progress_callback: Optional[Callable[[int, int, str], bool]] = None,
               **kwargs) -> Any:
        ...


@dataclass
class DirectoryScanResult:
    """Resultado del escaneo inicial de directorio"""
    total_files: int
    images: List[Path] = field(default_factory=list)
    videos: List[Path] = field(default_factory=list)
    others: List[Path] = field(default_factory=list)
    
    # Caché compartida de metadatos para optimizar fases subsecuentes
    metadata_cache: Optional[FileMetadataCache] = None
    
    # Tamaño total del directorio (calculado durante finalizacion)
    total_size: int = 0
    
    # Desglose por extensiones
    image_extensions: Dict[str, int] = field(default_factory=dict)
    video_extensions: Dict[str, int] = field(default_factory=dict)
    unsupported_extensions: Dict[str, int] = field(default_factory=dict)
    unsupported_files: List[Path] = field(default_factory=list)  # Rutas completas para DEBUG
    
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
    """Resultado completo de análisis de directorio - 100% tipado"""
    directory: Path
    scan: DirectoryScanResult
    phase_timings: Dict[str, PhaseTimingInfo] = field(default_factory=dict)
    
    # Todos los resultados tipados con sus dataclasses específicos
    renaming: Optional['RenameAnalysisResult'] = None  # Forward reference para evitar import circular
    live_photos: Optional['LivePhotoDetectionResult'] = None
    organization: Optional['OrganizationAnalysisResult'] = None
    heic: Optional['HeicAnalysisResult'] = None
    duplicates: Optional['DuplicateAnalysisResult'] = None
    zero_byte: Optional['ZeroByteAnalysisResult'] = None
    total_duration: float = 0.0


class AnalysisOrchestrator:
    """
    Coordina múltiples servicios de análisis para obtener información completa
    de un directorio sin dependencias de UI.
    
    Este servicio puede usarse en:
    - Workers (con callbacks para UI)
    - Scripts CLI (con callbacks para print)
    - Tests (con callbacks para validación)
    
    Los límites de memoria (MAX_CACHE_SIZE, LARGE_DATASET_THRESHOLD) son
    calculados dinámicamente por Config según la RAM disponible del sistema.
    """
    
    def __init__(self):
        self.logger = get_logger('AnalysisOrchestrator')
        
        # Obtener límites dinámicos según RAM del sistema
        self.max_cache_size = Config.get_max_cache_entries()
        self.large_dataset_threshold = Config.get_large_dataset_threshold()
        
        self.logger.debug(
            f"Orchestrator inicializado con límites dinámicos: "
            f"max_cache={self.max_cache_size}, "
            f"large_threshold={self.large_dataset_threshold}"
        )
    
    def _execute_phase(self,
                      phase_id: str,
                      phase_name: str,
                      phase_callable: Callable[[], Any],
                      phase_callback: Optional[Callable[[str], None]] = None,
                      partial_callback: Optional[Callable[[str, Any], None]] = None) -> tuple[Any, PhaseTimingInfo]:
        """
        Ejecuta una fase del análisis con tracking de tiempo y callbacks.
        
        Args:
            phase_id: Identificador único de la fase
            phase_name: Nombre descriptivo de la fase
            phase_callable: Función que ejecuta la fase y retorna el resultado
            phase_callback: Callback opcional para notificar inicio de fase
            partial_callback: Callback opcional para notificar resultado parcial
            
        Returns:
            Tupla (resultado, timing_info)
        """
        if phase_callback:
            phase_callback(phase_id)
        
        phase_start = time.time()
        result = phase_callable()
        phase_end = time.time()
        
        timing_info = PhaseTimingInfo(
            phase_id=phase_id,
            phase_name=phase_name,
            start_time=phase_start,
            end_time=phase_end,
            duration=phase_end - phase_start
        )
        
        if partial_callback:
            partial_callback(phase_id, result)
        
        return result, timing_info
    
    def _check_cancellation(self,
                           progress_callback: Optional[Callable[[int, int, str], bool]],
                           result: FullAnalysisResult,
                           analysis_start_time: float) -> bool:
        """
        Verifica si el usuario solicitó cancelación.
        
        Args:
            progress_callback: Callback de progreso
            result: Resultado actual del análisis
            analysis_start_time: Tiempo de inicio del análisis
            
        Returns:
            True si debe cancelarse, False en caso contrario
        """
        if progress_callback and not progress_callback(0, 0, ""):
            result.total_duration = time.time() - analysis_start_time
            return True
        return False
    
    def scan_directory(self, 
                      directory: Path,
                      progress_callback: Optional[Callable[[int, int, str], bool]] = None,
                      create_metadata_cache: bool = True,
                      precalculate_hashes: bool = False) -> DirectoryScanResult:
        """
        Escanea un directorio y clasifica archivos por tipo.
        Cuando create_metadata_cache=True, también extrae y cachea fechas EXIF
        de archivos de imagen para optimizar fases posteriores.
        
        Args:
            directory: Directorio a escanear
            progress_callback: Función opcional (current, total, message) -> bool.
                             Retorna False para cancelar.
            create_metadata_cache: Si crear caché de metadatos completo (incluye EXIF)
                                  para optimizar fases posteriores
            precalculate_hashes: Si pre-calcular hashes SHA256 durante el escaneo.
                               ADVERTENCIA: Esto hace el escaneo MUCHO más lento pero
                               acelera dramáticamente la fase de duplicados exactos.
        
        Returns:
            DirectoryScanResult con archivos clasificados y caché opcional
            
        Example:
            >>> orchestrator = AnalysisOrchestrator()
            >>> result = orchestrator.scan_directory(Path("/photos"))
            >>> print(f"Imágenes: {result.image_count}")
        """
        # Validación temprana
        if not directory.exists():
            raise FileNotFoundError(f"El directorio no existe: {directory}")
        if not directory.is_dir():
            raise NotADirectoryError(f"La ruta no es un directorio: {directory}")
        
        self.logger.info(f"Escaneando directorio: {directory}")
        
        # Crear caché de metadatos si se solicita
        self.logger.info(f"DEBUG: create_metadata_cache={create_metadata_cache}")
        metadata_cache = None
        if create_metadata_cache:
            try:
                metadata_cache = FileMetadataCache()
                self.logger.info(f"✅ Caché de metadatos creada exitosamente")
                self.logger.info(f"  - Tipo: {type(metadata_cache).__name__}")
                self.logger.info(f"  - Max entries: {metadata_cache._max_entries:,}")
                self.logger.info(f"  - Habilitada: {metadata_cache._enabled}")
                self.logger.info(f"  - ID objeto: {id(metadata_cache)}")
            except Exception as e:
                self.logger.error(f"❌ ERROR creando FileMetadataCache: {type(e).__name__}: {e}")
                import traceback
                self.logger.error(f"Traceback:\n{traceback.format_exc()}")
        else:
            self.logger.warning("⚠️  Caché de metadatos NO creada (create_metadata_cache=False)")
        
        self.logger.info(f"DEBUG ANTES DE CONTAR: metadata_cache={'presente' if metadata_cache is not None else 'None'}")
        
        # Una sola iteración: clasificar directamente sin contar primero
        images, videos, others = [], [], []
        image_extensions = {}
        video_extensions = {}
        unsupported_extensions = {}
        unsupported_files = []
        processed = 0
        
        # Primera pasada: obtener lista de archivos para saber el total
        # Excluir explícitamente el archivo de caché de desarrollo
        all_files = [
            f for f in directory.rglob("*") 
            if f.is_file() and f.name != Config.DEV_CACHE_FILENAME
        ]
        total_files = len(all_files)
        
        
        # Actualizar límite de caché basándose en el número de archivos
        self.logger.info(f"📊 Archivos contados: {total_files:,}")
        if metadata_cache is not None:
            self.logger.info(f"🔄 Actualizando límite de caché basado en {total_files:,} archivos...")
            metadata_cache.update_max_entries(total_files)
        else:
            self.logger.warning("⚠️  NO se puede actualizar límite de caché (metadata_cache es None)")
        
        
        # Segunda pasada: clasificar archivos y cachear metadata completo (incluye EXIF para imágenes)
        scan_message = "Escaneando y calculando hashes (esto puede tardar...)" if precalculate_hashes else "Escaneando archivos y extrayendo metadatos"
        
        if precalculate_hashes:
            self.logger.warning(
                "⚠️  PRE-CÁLCULO DE HASHES ACTIVADO: El escaneo será más lento pero "
                "la fase de duplicados exactos será instantánea"
            )
        
        for f in all_files:
            if progress_callback and not progress_callback(processed, total_files, scan_message):
                self.logger.warning("Escaneo cancelado por usuario")
                break
            
            # Obtener extensión (normalizar a lowercase)
            ext = f.suffix.lower() if f.suffix else '(sin extensión)'
            
            # Clasificar archivo
            if Config.is_image_file(f.name):
                images.append(f)
                file_type = 'image'
                image_extensions[ext] = image_extensions.get(ext, 0) + 1
            elif Config.is_video_file(f.name):
                videos.append(f)
                file_type = 'video'
                video_extensions[ext] = video_extensions.get(ext, 0) + 1
            else:
                others.append(f)
                file_type = 'other'
                unsupported_extensions[ext] = unsupported_extensions.get(ext, 0) + 1
                unsupported_files.append(f)
            
            # Cachear metadata básico durante el escaneo (evita stat() posterior)
            # NOTA: Hashes SHA256 solo se pre-calculan si precalculate_hashes=True
            # Por defecto NO se calculan aquí porque son costosos (I/O intensivo)
            # Los hashes se calculan solo cuando son necesarios (fase de duplicados exactos)
            # y se cachean ahí para futuras ejecuciones
            if metadata_cache is not None:
                try:
                    stat_info = f.stat()
                    metadata_cache.set_basic_metadata(
                        f,
                        size=stat_info.st_size,
                        file_type=file_type,
                        modified_time=stat_info.st_mtime,
                        created_time=stat_info.st_ctime
                    )
                    
                    # Para archivos de imagen, extraer y cachear fechas EXIF durante el scan
                    # Esto optimiza la fase de renaming que las necesita
                    if file_type == 'image':
                        try:
                            from utils.date_utils import get_all_file_dates
                            exif_dates = get_all_file_dates(f)
                            if exif_dates:
                                # Mapear las keys de get_all_file_dates a las esperadas por la caché
                                # get_all_file_dates devuelve:
                                #   - 'exif_create_date': CreateDate/DateTime EXIF tag
                                #   - 'exif_date_time_original': DateTimeOriginal EXIF tag
                                # La caché usa nombres simplificados:
                                #   - exif_date: para CreateDate
                                #   - exif_date_original: para DateTimeOriginal
                                exif_date = exif_dates.get('exif_create_date')
                                exif_date_original = exif_dates.get('exif_date_time_original')
                                
                                # Solo cachear si al menos una fecha existe
                                if exif_date or exif_date_original:
                                    metadata_cache.set_exif_dates(
                                        f,
                                        exif_date=exif_date,
                                        exif_date_original=exif_date_original
                                    )
                        except Exception as e:
                            # No loguear warning para EXIF fallido - es común en archivos sin EXIF
                            pass
                    
                    # Pre-calcular hashes SHA256 si se solicitó (hace el escaneo más lento)
                    if precalculate_hashes and file_type in ('image', 'video'):
                        try:
                            from utils.file_utils import calculate_file_hash
                            file_hash = calculate_file_hash(f)
                            metadata_cache.set_hash(f, file_hash)
                            self.logger.debug(f"🔐 Hash pre-calculado: {f.name} = {file_hash[:8]}...")
                        except Exception as e:
                            self.logger.warning(f"Error calculando hash de {f}: {e}")
                            
                except Exception as e:
                    self.logger.warning(f"No se pudo cachear metadata de {f}: {e}")
            
            processed += 1
            
            # Reportar progreso cada N archivos (evitar demasiadas actualizaciones)
            if progress_callback and processed % Config.UI_UPDATE_INTERVAL == 0:
                progress_callback(processed, total_files, scan_message)
        
        # Reportar progreso final (100%)
        if progress_callback and total_files > 0:
            progress_callback(total_files, total_files, scan_message)
        
        result = DirectoryScanResult(
            total_files=total_files,
            images=images,
            videos=videos,
            others=others,
            metadata_cache=metadata_cache,
            image_extensions=image_extensions,
            video_extensions=video_extensions,
            unsupported_extensions=unsupported_extensions,
            unsupported_files=unsupported_files
        )
        
        # Estadísticas de archivos soportados vs no soportados
        supported_count = result.image_count + result.video_count
        unsupported_count = result.other_count
        supported_percentage = (supported_count / total_files * 100) if total_files > 0 else 0
        unsupported_percentage = (unsupported_count / total_files * 100) if total_files > 0 else 0
        
        # Obtener extensiones de archivos no soportados
        unsupported_extensions = {}
        for f in others:
            ext = f.suffix.lower() if f.suffix else '(sin extensión)'
            unsupported_extensions[ext] = unsupported_extensions.get(ext, 0) + 1
        
        # Formatear extensiones para el log
        ext_summary = ', '.join(f"{ext} ({count})" for ext, count in sorted(unsupported_extensions.items()))
        if not ext_summary:
            ext_summary = "ninguna"
        
        self.logger.info(
            f"*** Escaneo completado: {total_files:,} archivos totales"
        )
        self.logger.info(
            f"*** Archivos SOPORTADOS: {supported_count:,} ({supported_percentage:.1f}%) "
            f"[{result.image_count:,} imágenes + {result.video_count:,} videos]"
        )
        self.logger.info(
            f"*** Archivos NO SOPORTADOS: {unsupported_count:,} ({unsupported_percentage:.1f}%) "
            f"- Extensiones: {ext_summary}"
        )
        if metadata_cache is not None:
            cache_stats = metadata_cache.get_stats()
            exif_cached = sum(1 for m in metadata_cache._cache.values() if m.exif_date or m.exif_date_original)
            hashes_cached = sum(1 for m in metadata_cache._cache.values() if m.sha256_hash)
            self.logger.info(
                f"💾 Caché después del escaneo: "
                f"{cache_stats['size']} entradas, "
                f"{exif_cached} con fechas EXIF, "
                f"{hashes_cached} con hashes SHA256"
            )
            
            if precalculate_hashes and hashes_cached > 0:
                self.logger.info(
                    f"✅ Pre-cálculo de hashes completado: {hashes_cached} archivos "
                    "(la fase de duplicados exactos será instantánea)"
                )
            elif not precalculate_hashes:
                self.logger.info(
                    "ℹ️  Hashes NO pre-calculados (se calcularán en la fase de duplicados exactos)"
                )
        
        return result
    
    def analyze_renaming(self,
                        directory: Path,
                        renamer: AnalyzableService,
                        progress_callback: Optional[Callable[[int, int, str], bool]] = None,
                        metadata_cache: Optional[FileMetadataCache] = None) -> 'RenameAnalysisResult':
        """
        Analiza nombres de archivos que necesitan normalización.
        
        Args:
            directory: Directorio a analizar
            renamer: Instancia de FileRenamer
            progress_callback: Función opcional de progreso
            metadata_cache: Caché opcional de metadatos
            
        Returns:
            RenameAnalysisResult con el análisis de renombrado
        """
        self.logger.info("Analizando nombres de archivos")
        return renamer.analyze(directory, progress_callback=progress_callback, metadata_cache=metadata_cache)
    
    def analyze_live_photos(self,
                           directory: Path,
                           service: AnalyzableService,
                           progress_callback: Optional[Callable[[int, int, str], bool]] = None) -> 'LivePhotoDetectionResult':
        """
        Detecta grupos de Live Photos en el directorio.
        
        Args:
            directory: Directorio a analizar
            service: Instancia de LivePhotoService
            progress_callback: Función opcional de progreso
            
        Returns:
            LivePhotoDetectionResult con grupos y estadísticas
        """
        self.logger.info("Buscando Live Photos")
        
        from services.result_types import LivePhotoDetectionResult
        from services.live_photos_service import CleanupMode
        
        # El nuevo servicio usa analyze() que retorna LivePhotoCleanupAnalysisResult
        cleanup_analysis = service.analyze(
            directory, 
            cleanup_mode=CleanupMode.KEEP_IMAGE,
            progress_callback=progress_callback
        )
        
        # Convertir a LivePhotoDetectionResult para mantener compatibilidad con la estructura esperada
        result = LivePhotoDetectionResult(
            total_files=cleanup_analysis.total_files,
            groups=cleanup_analysis.groups,  # Usar los grupos del análisis
            live_photos_found=cleanup_analysis.live_photos_found,
            total_space=cleanup_analysis.total_space,
            space_to_free=cleanup_analysis.space_to_free
        )
        
        self.logger.info(f"Encontrados {cleanup_analysis.live_photos_found} grupos de Live Photos")
        return result
    
    def analyze_organization(self,
                            directory: Path,
                            organizer: AnalyzableService,
                            organization_type: Optional[str] = None,
                            progress_callback: Optional[Callable[[int, int, str], bool]] = None) -> 'OrganizationAnalysisResult':
        """
        Analiza estructura de directorios para organización.
        
        Args:
            directory: Directorio a analizar
            organizer: Instancia de FileOrganizer
            organization_type: Tipo de organización (opcional)
            progress_callback: Función opcional de progreso
            
        Returns:
            OrganizationAnalysisResult con el plan de organización
        """
        # Importar OrganizationType para manejar el caso None
        from services.file_organizer_service import OrganizationType
        
        # Si organization_type es None, usar el valor por defecto
        if organization_type is None:
            org_type = OrganizationType.TO_ROOT
        else:
            # Convertir string a enum si es necesario
            if isinstance(organization_type, str):
                org_type = OrganizationType(organization_type)
            else:
                org_type = organization_type
        
        self.logger.info(f"Analizando estructura de carpetas (tipo: {org_type.value})")
        
        return organizer.analyze(
            directory,
            organization_type=org_type,
            progress_callback=progress_callback
        )
    
    def analyze_heic_duplicates(self,
                               directory: Path,
                               heic_remover: AnalyzableService,
                               progress_callback: Optional[Callable[[int, int, str], bool]] = None,
                               metadata_cache: Optional[FileMetadataCache] = None) -> 'HeicAnalysisResult':
        """
        Busca duplicados HEIC/JPG.
        
        Args:
            directory: Directorio a analizar
            heic_remover: Instancia de HEICRemover
            progress_callback: Función opcional de progreso
            metadata_cache: Caché opcional de metadatos
            
        Returns:
            HeicAnalysisResult con duplicados HEIC/JPG encontrados
        """
        self.logger.info("Buscando duplicados HEIC/JPG")
        return heic_remover.analyze(directory, progress_callback=progress_callback, metadata_cache=metadata_cache)
    
    def analyze_exact_duplicates(self,
                                 directory: Path,
                                 duplicate_exact_detector: AnalyzableService,
                                 progress_callback: Optional[Callable[[int, int, str], bool]] = None,
                                 metadata_cache: Optional[FileMetadataCache] = None) -> 'DuplicateAnalysisResult':
        """
        Detecta duplicados exactos usando SHA256.
        
        Args:
            directory: Directorio a analizar
            duplicate_exact_detector: Instancia de ExactCopiesDetector
            progress_callback: Función opcional de progreso
            metadata_cache: Caché opcional de metadatos
            
        Returns:
            DuplicateAnalysisResult con duplicados exactos detectados
        """
        self.logger.info("Identificando copias exactas")
        return duplicate_exact_detector.analyze(
            directory,
            progress_callback=progress_callback,
            metadata_cache=metadata_cache
        )

    def analyze_zero_byte_files(self,
                               directory: Path,
                               zero_byte_service: AnalyzableService,
                               progress_callback: Optional[Callable[[int, int, str], bool]] = None) -> 'ZeroByteAnalysisResult':
        """
        Busca archivos de 0 bytes.
        
        Args:
            directory: Directorio a analizar
            zero_byte_service: Instancia de ZeroByteService
            progress_callback: Función opcional de progreso
            
        Returns:
            ZeroByteAnalysisResult con archivos vacíos encontrados
        """
        self.logger.info("Buscando archivos de 0 bytes")
        return zero_byte_service.analyze(directory, progress_callback=progress_callback)
    
    def _log_memory_usage(self, phase: str) -> None:
        """Log del uso de memoria después de cada fase"""
        try:
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / (1024 * 1024)
            self.logger.debug(f"[{phase}] Memoria usada: {mem_mb:.1f} MB")
        except ImportError:
            pass  # psutil no disponible
    
    def _release_memory(self, metadata_cache: Optional[FileMetadataCache]) -> None:
        """Libera memoria forzando garbage collection"""
        if metadata_cache is not None:
            cache_size = len(metadata_cache._cache) if hasattr(metadata_cache, '_cache') else 0
            # Usar el límite dinámico de la caché misma, no el límite estático del orchestrator
            cache_limit = metadata_cache._max_entries if hasattr(metadata_cache, '_max_entries') else self.max_cache_size
            
            if cache_size > cache_limit:
                self.logger.warning(
                    f"Caché grande detectada ({cache_size} archivos, "
                    f"límite: {cache_limit}). Liberando memoria..."
                )
                metadata_cache.clear_cache()
            else:
                self.logger.debug(
                    f"Caché dentro de límites ({cache_size}/{cache_limit} archivos). "
                    "No es necesario liberar memoria."
                )
        
        # Forzar garbage collection
        gc.collect()
        self.logger.debug("Memoria liberada (gc.collect ejecutado)")
    
    def run_full_analysis(self,
                         directory: Path,
                         renamer: Optional[AnalyzableService] = None,
                         live_photos_service: Optional[AnalyzableService] = None,
                         organizer: Optional[AnalyzableService] = None,
                         heic_remover: Optional[AnalyzableService] = None,
                         duplicate_exact_detector: Optional[AnalyzableService] = None,
                         zero_byte_service: Optional[AnalyzableService] = None,
                         organization_type: Optional[str] = None,
                         progress_callback: Optional[Callable[[int, int, str], bool]] = None,
                         phase_callback: Optional[Callable[[str], None]] = None,
                         partial_callback: Optional[Callable[[str, Any], None]] = None,
                         precalculate_hashes: bool = False) -> FullAnalysisResult:
        """
        Ejecuta análisis completo del directorio coordinando todos los servicios.
        
        Args:
            directory: Directorio a analizar
            renamer: FileRenamer opcional
            live_photos_service: LivePhotoService opcional
            organizer: FileOrganizer opcional
            heic_remover: HEICRemover opcional
            duplicate_exact_detector: DuplicateExactDetector opcional
            organization_type: Tipo de organización opcional
            progress_callback: Callback (current, total, msg) -> bool para progreso
            phase_callback: Callback (phase_name) para cambios de fase
            partial_callback: Callback (phase_name, result) para resultados parciales
            precalculate_hashes: Si pre-calcular hashes SHA256 durante el escaneo.
                               Hace el escaneo más lento pero la fase de duplicados
                               exactos será instantánea. Default: False
            
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
        log_section_header_discrete(self.logger, f"INICIANDO ANÁLISIS COMPLETO DE: {directory}")
        analysis_start_time = time.time()
        
        # Fase 1: Escaneo inicial (crea la caché de metadatos)
        scan_result, scan_timing = self._execute_phase(
            phase_id="scan",
            phase_name="Escaneo inicial del directorio",
            phase_callable=lambda: self.scan_directory(
                directory, 
                progress_callback, 
                create_metadata_cache=True,
                precalculate_hashes=precalculate_hashes
            ),
            phase_callback=phase_callback,
            partial_callback=lambda phase_id, scan_res: partial_callback(
                phase_id, {
                    'total': scan_res.total_files,
                    'images': scan_res.image_count,
                    'videos': scan_res.video_count,
                    'others': scan_res.other_count
                }
            ) if partial_callback else None
        )
        
        # Crear resultado con timing de escaneo
        result = FullAnalysisResult(
            directory=directory,
            scan=scan_result
        )
        result.phase_timings['scan'] = scan_timing
        
        # Warning para datasets muy grandes
        if scan_result.total_files > self.large_dataset_threshold:
            self.logger.warning(
                f"Dataset grande detectado ({scan_result.total_files} archivos, "
                f"umbral: {self.large_dataset_threshold}). "
                "El análisis puede ser lento y consumir mucha memoria."
            )
        
        # Obtener caché compartida del escaneo
        metadata_cache = scan_result.metadata_cache
        if metadata_cache is not None:
            cache_stats = metadata_cache.get_stats()
            self.logger.info(
                f"🔗 Caché compartida disponible para todas las fases: "
                f"tamaño={cache_stats['size']}, "
                f"ID={id(metadata_cache)}"
            )
        else:
            self.logger.warning("⚠️  NO hay caché compartida - cada fase calculará desde cero")
        
        # Fase 2: Análisis de renombrado (usa caché para fechas EXIF)
        if renamer:
            if self._check_cancellation(progress_callback, result, analysis_start_time):
                return result
            
            result.renaming, result.phase_timings['renaming'] = self._execute_phase(
                phase_id="renaming",
                phase_name="Recopilando nombres de archivos",
                phase_callable=lambda: self.analyze_renaming(directory, renamer, progress_callback, metadata_cache),
                phase_callback=phase_callback,
                partial_callback=partial_callback
            )
        
        # Fase 3: Live Photos
        if live_photos_service:
            if self._check_cancellation(progress_callback, result, analysis_start_time):
                return result
            
            result.live_photos, result.phase_timings['live_photos'] = self._execute_phase(
                phase_id="live_photos",
                phase_name="Buscando Live Photos",
                phase_callable=lambda: self.analyze_live_photos(directory, live_photos_service, progress_callback),
                phase_callback=phase_callback,
                partial_callback=partial_callback
            )
        
        # Fase 4: Duplicados HEIC (usa caché para tamaños y timestamps)
        if heic_remover:
            if self._check_cancellation(progress_callback, result, analysis_start_time):
                return result
            
            result.heic, result.phase_timings['heic'] = self._execute_phase(
                phase_id="heic",
                phase_name="Buscando duplicados HEIC/JPG",
                phase_callable=lambda: self.analyze_heic_duplicates(directory, heic_remover, progress_callback, metadata_cache),
                phase_callback=phase_callback,
                partial_callback=partial_callback
            )
            
            # Liberar memoria después de fase pesada
            self._log_memory_usage("heic")
            if scan_result.total_files > self.large_dataset_threshold:
                self._release_memory(metadata_cache)
        
        # Fase 5: Duplicados exactos (usa caché para hashes SHA256)
        if duplicate_exact_detector:
            if self._check_cancellation(progress_callback, result, analysis_start_time):
                return result
            
            # Log antes de pasar la caché
            if metadata_cache is not None:
                cache_stats = metadata_cache.get_stats()
                self.logger.info(
                    f"🚀 Iniciando fase de duplicados exactos CON caché: "
                    f"tamaño={cache_stats['size']}, hits={cache_stats['hits']}, "
                    f"misses={cache_stats['misses']}, hit_rate={cache_stats['hit_rate']:.1f}%"
                )
            else:
                self.logger.warning("⚠️  Iniciando fase de duplicados exactos SIN caché (se calculará todo)")
            
            result.duplicates, result.phase_timings['duplicates'] = self._execute_phase(
                phase_id="duplicates",
                phase_name="Identificando copias exactas",
                phase_callable=lambda: self.analyze_exact_duplicates(directory, duplicate_exact_detector, progress_callback, metadata_cache),
                phase_callback=phase_callback,
                partial_callback=partial_callback
            )
            
            # Liberar memoria después de fase pesada
            self._log_memory_usage("duplicates")
            if scan_result.total_files > self.large_dataset_threshold:
                self._release_memory(metadata_cache)
        
        # Fase 6: Archivos de 0 bytes
        if zero_byte_service:
            if self._check_cancellation(progress_callback, result, analysis_start_time):
                return result
            
            result.zero_byte, result.phase_timings['zero_byte'] = self._execute_phase(
                phase_id="zero_byte",
                phase_name="Buscando archivos vacíos",
                phase_callable=lambda: self.analyze_zero_byte_files(directory, zero_byte_service, progress_callback),
                phase_callback=phase_callback,
                partial_callback=partial_callback
            )

        # Fase 7: Organización
        if organizer:
            if self._check_cancellation(progress_callback, result, analysis_start_time):
                return result
            
            result.organization, result.phase_timings['organization'] = self._execute_phase(
                phase_id="organization",
                phase_name="Analizando estructura de carpetas",
                phase_callable=lambda: self.analyze_organization(directory, organizer, organization_type, progress_callback),
                phase_callback=phase_callback,
                partial_callback=partial_callback
            )
        
        # Fase 8: Finalización
        _, result.phase_timings['finalizing'] = self._execute_phase(
            phase_id="finalizing",
            phase_name="Finalizando análisis",
            phase_callable=lambda: None,  # No hay procesamiento real
            phase_callback=phase_callback,
            partial_callback=None
        )
        
        # Log de estadísticas de caché al final
        if metadata_cache is not None:
            self.logger.info("📊 Estadísticas finales de caché:")
            metadata_cache.log_stats()
        else:
            self.logger.warning("⚠️  No hay estadísticas de caché (no se usó caché)")
        
        result.total_duration = time.time() - analysis_start_time
        
        log_section_footer_discrete(self.logger, f"Análisis completo finalizado en {result.total_duration:.2f}s")
        return result
