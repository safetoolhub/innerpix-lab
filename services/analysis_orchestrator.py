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
from utils.logger import get_logger, log_section_header_discrete, log_section_footer_discrete
from services.metadata_cache import FileMetadataCache
from services.directory_scanner import DirectoryScanner
from services.result_types import (
    DirectoryScanResult,
    PhaseTimingInfo
)

if TYPE_CHECKING:
    from services.result_types import (
        DirectoryScanResult,
        PhaseTimingInfo,
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
    def analyze(self, *args, **kwargs) -> Any:
        ...


# Result types now imported from services.result_types


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
    

