"""
Detector de Live Photos de iPhone - Corregido para archivos renombrados
"""
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass

import config
from utils.logger import get_logger


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


class LivePhotoDetector:
    """Detector de Live Photos de iPhone"""

    def __init__(self):
        self.logger = get_logger("LivePhotoDetector")

        # Extensiones para Live Photos - Convertir todas a mayúsculas para comparación
        self.photo_extensions = {ext.upper() for ext in {'.heic', '.jpg', '.jpeg'}}
        self.video_extensions = {'.MOV'}  # Live Photos usan específicamente .MOV
        
        self.logger.debug(f"Extensiones de foto configuradas: {self.photo_extensions}")
        self.logger.debug(f"Extensiones de video configuradas: {self.video_extensions}")

        # Tolerancia de tiempo
        self.time_tolerance = 2.0

    def detect_in_directory(self, directory: Path, recursive: bool = True) -> List[LivePhotoGroup]:
        """
        Detecta Live Photos en un directorio

        Args:
            directory: Directorio a analizar
            recursive: Si buscar recursivamente

        Returns:
            Lista de LivePhotoGroup detectados
        """
        self.logger.info(f"Detectando Live Photos en: {directory}")

        if not directory.exists():
            raise ValueError(f"Directorio no existe: {directory}")

        # Recopilar archivos
        photos = []
        videos = []

        iterator = directory.rglob("*") if recursive else directory.iterdir()

        for file_path in iterator:
            if not file_path.is_file():
                continue

            ext = file_path.suffix.upper()  # Convertir la extensión a mayúsculas
            self.logger.debug(f"Analizando archivo: {file_path.name} con extensión {ext}")
            
            if ext in self.photo_extensions:
                self.logger.debug(f"Encontrada foto: {file_path.name}")
                photos.append(file_path)
            elif ext in self.video_extensions:
                self.logger.debug(f"Encontrado video: {file_path.name}")
                videos.append(file_path)

        self.logger.info(f"Encontrados: {len(photos)} fotos, {len(videos)} videos")

        if not photos or not videos:
            return []

        # Detectar grupos
        groups = []
        groups.extend(self._detect_live_photos(photos, videos))

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

    def _detect_live_photos(self, photos: List[Path], videos: List[Path]) -> List[LivePhotoGroup]:
        """Detecta Live Photos buscando parejas de fotos con videos .MOV"""
        groups = []
        
        # Crear un mapa de nombres base a videos .MOV
        video_map = defaultdict(list)
        for video in videos:
            normalized_name = self._normalize_name(video.stem)
            video_map[normalized_name].append(video)
            self.logger.debug(f"Video registrado: {video.name} con nombre normalizado: {normalized_name}")

        # Por cada foto, buscar su video .MOV correspondiente usando nombres normalizados
        for photo in photos:
            normalized_name = self._normalize_name(photo.stem)
            self.logger.debug(f"Buscando video para foto: {photo.name} con nombre normalizado: {normalized_name}")
            self.logger.debug(f"Videos disponibles: {[k for k in video_map.keys()]}")
            if normalized_name in video_map:
                self.logger.debug(f"¡Match encontrado para {photo.name}!")
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
                            self.logger.debug(f"Live Photo encontrado: {original_name}")
                        except Exception as e:
                            self.logger.warning(f"Error creando grupo para {original_name}: {e}")

        return groups
        timestamp_pattern = re.compile(r'(\d{8}_\d{6})')

        image_timestamps = defaultdict(list)
        for img in images:
            match = timestamp_pattern.search(img.stem)
            if match:
                image_timestamps[match.group(1)].append(img)

        video_timestamps = defaultdict(list)
        for vid in videos:
            match = timestamp_pattern.search(vid.stem)
            if match:
                video_timestamps[match.group(1)].append(vid)

        for timestamp in image_timestamps.keys():
            if timestamp in video_timestamps:
                for img in image_timestamps[timestamp]:
                    for vid in video_timestamps[timestamp]:
                        if img.parent == vid.parent:
                            try:
                                group = LivePhotoGroup(
                                    image_path=img,
                                    video_path=vid,
                                    base_name=timestamp,
                                    directory=img.parent,
                                    image_size=img.stat().st_size,
                                    video_size=vid.stat().st_size
                                )
                                groups.append(group)
                            except Exception as e:
                                self.logger.warning(f"Error creando grupo: {e}")

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

    def analyze_live_photos(self, groups: List[LivePhotoGroup]) -> Dict:
        """Obtiene estadísticas de los grupos detectados"""
        if not groups:
            return {
                'total_groups': 0,
                'total_images': 0,
                'total_videos': 0,
                'total_size': 0,
                'avg_time_diff': 0.0
            }

        total_size = sum(g.total_size for g in groups)
        avg_time_diff = sum(g.time_difference for g in groups) / len(groups)

        return {
            'total_groups': len(groups),
            'total_images': len(groups),
            'total_videos': len(groups),
            'total_size': total_size,
            'avg_time_diff': avg_time_diff
        }
