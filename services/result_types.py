"""
Tipos de resultados estandarizados para servicios de PhotoKit Manager

Define dataclasses consistentes para resultados de análisis y operaciones,
eliminando la heterogeneidad de diccionarios con keys variables.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class OperationResult:
    """Resultado base de cualquier operación"""
    success: bool = True
    errors: List[str] = field(default_factory=list)
    message: Optional[str] = None

    def __post_init__(self):
        """Validaciones post-inicialización"""
        if self.errors is None:
            self.errors = []

    @property
    def has_errors(self) -> bool:
        """True si hay errores"""
        return len(self.errors) > 0
    
    @property
    def error(self) -> Optional[str]:
        """Primer error de la lista (para compatibilidad)"""
        return self.errors[0] if self.errors else None

    def add_error(self, error: str):
        """Añade un error a la lista"""
        self.errors.append(error)
        if self.success:
            self.success = False

    def __getitem__(self, key):
        """Permite acceso tipo diccionario para compatibilidad con código existente"""
        return getattr(self, key)
    
    def get(self, key, default=None):
        """Permite acceso tipo diccionario con valor por defecto"""
        return getattr(self, key, default)


@dataclass
class AnalysisResult(OperationResult):
    """Resultado base de análisis"""
    total_files: int = 0


@dataclass
class DeletionResult(OperationResult):
    """Resultado de operación de eliminación"""
    files_deleted: int = 0
    space_freed: int = 0
    backup_path: Optional[str] = None
    deleted_files: List[str] = field(default_factory=list)


@dataclass
class RenameResult(OperationResult):
    """Resultado de operación de renombrado"""
    files_renamed: int = 0
    renamed_files: List[dict] = field(default_factory=list)
    backup_path: Optional[str] = None
    conflicts_resolved: int = 0


@dataclass
class OrganizationResult(OperationResult):
    """Resultado de operación de organización"""
    files_moved: int = 0
    empty_directories_removed: int = 0
    moved_files: List[str] = field(default_factory=list)
    backup_path: Optional[str] = None
    folders_created: List[str] = field(default_factory=list)


@dataclass
class DuplicateAnalysisResult(AnalysisResult):
    """Resultado de análisis de duplicados (exactos o similares)"""
    mode: str = 'exact'  # 'exact' o 'perceptual'
    groups: List = field(default_factory=list)  # List[DuplicateGroup]
    total_groups: int = 0
    total_duplicates: int = 0  # Para exactos
    total_similar: int = 0  # Para similares
    space_wasted: int = 0  # Para exactos
    space_potential: int = 0  # Para similares
    sensitivity: Optional[int] = None  # Solo para similares
    min_similarity: Optional[float] = None  # Solo para similares
    max_similarity: Optional[float] = None  # Solo para similares

    def __post_init__(self):
        """Post-init validation"""
        super().__post_init__()
        # Normalizar campos según modo
        if self.mode == 'exact':
            self.total_similar = 0
            self.space_potential = 0
        elif self.mode == 'perceptual':
            self.total_duplicates = 0
            self.space_wasted = 0


@dataclass
class HeicAnalysisResult(AnalysisResult):
    """Resultado de análisis de duplicados HEIC"""
    duplicate_pairs: List = field(default_factory=list)  # List[DuplicatePair]
    total_pairs: int = 0
    heic_files: int = 0
    jpg_files: int = 0
    total_size: int = 0
    
    @property
    def total_duplicates(self) -> int:
        """Alias para compatibilidad"""
        return self.total_pairs


@dataclass
class HeicDeletionResult(DeletionResult):
    """Resultado de eliminación de HEIC"""
    format_kept: Optional[str] = None
    
    @property
    def kept_format(self) -> Optional[str]:
        """Alias para compatibilidad"""
        return self.format_kept


@dataclass
class LivePhotoAnalysisResult(AnalysisResult):
    """Resultado de análisis de Live Photos"""
    total_groups: int = 0
    total_images: int = 0
    total_videos: int = 0
    total_size: int = 0
    avg_time_diff: float = 0.0


@dataclass
class LivePhotoCleanupAnalysisResult(AnalysisResult):
    """Resultado de análisis de limpieza de Live Photos"""
    live_photos_found: int = 0
    files_to_delete: List[dict] = field(default_factory=list)
    files_to_keep: List[dict] = field(default_factory=list)
    space_to_free: int = 0
    total_space: int = 0
    cleanup_mode: str = 'keep_image'


@dataclass
class LivePhotoCleanupResult(DeletionResult):
    """Resultado de limpieza de Live Photos"""
    dry_run: bool = False
    simulated_files_deleted: int = 0
    simulated_space_freed: int = 0


# Funciones de conversión para compatibilidad con código existente
def to_dict(result: OperationResult) -> dict:
    """
    Convierte un resultado dataclass a diccionario
    
    Útil para compatibilidad con código que espera diccionarios
    """
    from dataclasses import asdict
    return asdict(result)


def from_dict(data: dict, result_class: type) -> OperationResult:
    """
    Crea un resultado dataclass desde un diccionario
    
    Args:
        data: Diccionario con datos
        result_class: Clase del resultado (ej: DeletionResult)
    
    Returns:
        Instancia del resultado
    """
    return result_class(**{k: v for k, v in data.items() if k in result_class.__annotations__})
