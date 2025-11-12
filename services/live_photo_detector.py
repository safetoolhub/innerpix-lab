"""
Detector de Live Photos de iPhone - Corregido para archivos renombrados
"""
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from collections import defaultdict
from dataclasses import dataclass

from config import Config
from services.result_types import LivePhotoAnalysisResult
from services.base_service import BaseService


@dataclass
class LivePhotoGroup:
    """Representa un grupo de Live Photo detectado"""
    image_path: Path
    video_path: Path
    base_name: str
    directory: Path
    image_size: int
    video_size: int
    image_date: Optional[datetime] = None
    video_date: Optional[datetime] = None

    def __post_init__(self):
        """Validaciones y cálculos adicionales"""
        if not self.image_path.exists():
            raise ValueError(f"Imagen no existe: {self.image_path}")
        if not self.video_path.exists():
            raise ValueError(f"Video no existe: {self.video_path}")

        if not self.image_date:
            self.image_date = datetime.fromtimestamp(self.image_path.stat().st_mtime)
        if not self.video_date:
            self.video_date = datetime.fromtimestamp(self.video_path.stat().st_mtime)

    @property
    def total_size(self) -> int:
        """Tamaño total del grupo"""
        return self.image_size + self.video_size

    @property
    def time_difference(self) -> float:
        """Diferencia en segundos entre imagen y video"""
        if self.image_date and self.video_date:
            return abs((self.image_date - self.video_date).total_seconds())
        return 0.0


class LivePhotoDetector(BaseService):
    """
    Detector de Live Photos de iPhone
    
    Hereda de BaseService para logging estandarizado.
    """

    def __init__(self):
        super().__init__("LivePhotoDetector")

        # Extensiones para Live Photos - Convertir todas a mayúsculas para comparación
        self.photo_extensions = {ext.upper() for ext in {'.heic', '.jpg', '.jpeg'}}
        self.video_extensions = {'.MOV'}  # Live Photos usan específicamente .MOV
        
        self.logger.debug(f"Extensiones de foto configuradas: {self.photo_extensions}")
        self.logger.debug(f"Extensiones de video configuradas: {self.video_extensions}")

        # Tolerancia de tiempo
        self.time_tolerance = 2.0

    def detect_in_directory(self, directory: Path, recursive: bool = True, progress_callback=None) -> List[LivePhotoGroup]:
        """
        Detecta Live Photos en un directorio

        Args:
            directory: Directorio a analizar
            recursive: Si buscar recursivamente
            progress_callback: Función opcional (current, total, message) para reportar progreso

        Returns:
            Lista de LivePhotoGroup detectados
        """
        self._log_section_header("DETECCIÓN DE LIVE PHOTOS")
        self.logger.info(f"Analizando en: {directory}")

        if not directory.exists():
            raise ValueError(f"Directorio no existe: {directory}")

        # Recopilar archivos
        photos = []
        videos = []
        
        # Primero contamos total de archivos para progress
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        all_files = [f for f in iterator if f.is_file()]
        total_files = len(all_files)
        processed = 0

        self.logger.info(f"Escaneando {total_files} archivos para detectar Live Photos")

        for file_path in all_files:
            # Reportar progreso y verificar si se solicitó cancelación
            if progress_callback:
                # Si el callback retorna False, el usuario canceló - detener inmediatamente
                if not progress_callback(processed, total_files, "Detectando Live Photos"):
                    self.logger.info("Detección de Live Photos cancelada por el usuario")
                    return []  # Retornar lista vacía al cancelar
            
            ext = file_path.suffix.upper()  # Convertir la extensión a mayúsculas
            
            if ext in self.photo_extensions:
                photos.append(file_path)
            elif ext in self.video_extensions:
                videos.append(file_path)
            
            processed += 1

        # Reportar progreso final (100%)
        if progress_callback and total_files > 0:
            if not progress_callback(total_files, total_files, "Detectando Live Photos"):
                self.logger.info("Detección de Live Photos cancelada por el usuario")
                return []

        self.logger.info(f"Encontrados: {len(photos)} fotos, {len(videos)} videos")

        if not photos or not videos:
            return []

        # Detectar grupos con progreso
        self.logger.info("Iniciando matching de Live Photos...")
        groups = self._detect_live_photos(photos, videos, progress_callback)

        if groups is None:  # Cancelación durante matching
            return []

        # Eliminar duplicados
        unique_groups = self._remove_duplicate_groups(groups)

        self.logger.info(f"Detectados {len(unique_groups)} grupos de Live Photos")

        return unique_groups

    def _normalize_name(self, name: str) -> str:
        """Normaliza el nombre eliminando sufijos comunes de fotos y videos"""
        name = name.lower()
        # Eliminar sufijos comunes que se añaden al renombrar
        suffixes = ['_photo', '_video', ' photo', ' video', '-photo', '-video']
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name

    def _detect_live_photos(self, photos: List[Path], videos: List[Path], progress_callback=None) -> List[LivePhotoGroup]:
        """
        Detecta Live Photos buscando parejas de fotos con videos .MOV
        
        Args:
            photos: Lista de fotos a procesar
            videos: Lista de videos a buscar
            progress_callback: Callback opcional para reportar progreso
            
        Returns:
            Lista de grupos encontrados, o None si se cancela
        """
        groups = []
        total_photos = len(photos)
        
        self.logger.info(f"Construyendo mapa de videos ({len(videos)} videos)...")
        
        # Crear un mapa de nombres base a videos .MOV
        video_map = defaultdict(list)
        for video in videos:
            normalized_name = self._normalize_name(video.stem)
            video_map[normalized_name].append(video)

        self.logger.info(f"Mapa de videos construido con {len(video_map)} nombres únicos")
        self.logger.info(f"Procesando {total_photos} fotos para matching...")

        # Por cada foto, buscar su video .MOV correspondiente usando nombres normalizados
        for idx, photo in enumerate(photos, 1):
            # Reportar progreso cada 1000 fotos
            if idx % 1000 == 0:
                self.logger.info(f"Procesadas {idx}/{total_photos} fotos, {len(groups)} Live Photos encontrados hasta ahora")
                
                # Verificar cancelación
                if progress_callback:
                    if not progress_callback(idx, total_photos, "Matching Live Photos"):
                        self.logger.info("Matching de Live Photos cancelado por el usuario")
                        return None  # Señal de cancelación
            
            normalized_name = self._normalize_name(photo.stem)
            
            if normalized_name in video_map:
                original_name = photo.stem
                for video in video_map[normalized_name]:
                    if photo.parent == video.parent:
                        try:
                            group = LivePhotoGroup(
                                image_path=photo,
                                video_path=video,
                                base_name=original_name,
                                directory=photo.parent,
                                image_size=photo.stat().st_size,
                                video_size=video.stat().st_size
                            )
                            groups.append(group)
                        except Exception as e:
                            self.logger.warning(f"Error creando grupo para {original_name}: {e}")

        # Log final
        self.logger.info(f"Matching completado: {len(groups)} Live Photos encontrados")
        
        return groups

    def _remove_duplicate_groups(self, groups: List[LivePhotoGroup]) -> List[LivePhotoGroup]:
        """Elimina grupos duplicados"""
        unique_groups = []
        seen_pairs = set()

        sorted_groups = sorted(groups, key=lambda g: g.time_difference)

        for group in sorted_groups:
            pair_id = (str(group.image_path), str(group.video_path))

            if pair_id not in seen_pairs:
                unique_groups.append(group)
                seen_pairs.add(pair_id)

        return unique_groups

    def analyze_live_photos(self, groups: List[LivePhotoGroup]) -> LivePhotoAnalysisResult:
        """Obtiene estadísticas de los grupos detectados"""
        if not groups:
            return LivePhotoAnalysisResult(
                total_files=0,
                total_groups=0,
                total_images=0,
                total_videos=0,
                total_size=0,
                avg_time_diff=0.0
            )

        total_size = sum(g.total_size for g in groups)
        avg_time_diff = sum(g.time_difference for g in groups) / len(groups)

        return LivePhotoAnalysisResult(
            total_files=len(groups) * 2,
            total_groups=len(groups),
            total_images=len(groups),
            total_videos=len(groups),
            total_size=total_size,
            avg_time_diff=avg_time_diff
        )
