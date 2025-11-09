"""
View Models - Capa de presentación sin dependencias de UI

Este módulo contiene View Models que transforman dataclasses de servicios
en estructuras de datos optimizadas para presentación, completamente
independientes de PyQt6 o cualquier framework de UI.

Beneficios:
- Testeable sin PyQt6
- Reutilizable en CLI, web, mobile
- Lógica de presentación centralizada
- Separación limpia UI/Lógica
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Imports de dataclasses de servicios
from services.result_types import (
    OrganizationAnalysisResult,
    RenameAnalysisResult,
    HeicAnalysisResult,
    DuplicateAnalysisResult
)
from services.file_organizer import FileMove, OrganizationType
from services.heic_remover import DuplicatePair
# DuplicateGroup está definido en ambos servicios duplicate_exact_detector y duplicate_similar_detector
# Importamos desde exact_detector por convención (ambas definiciones son idénticas)
from services.exact_copies_detector import DuplicateGroup


# ============================================================================
# BASE CLASSES
# ============================================================================

@dataclass
class TreeNode:
    """Nodo base para estructuras de árbol - sin Qt"""
    label: str
    children: List['TreeNode'] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    is_expanded: bool = True
    
    def add_child(self, child: 'TreeNode') -> None:
        """Agrega un hijo al nodo"""
        self.children.append(child)
    
    @property
    def has_children(self) -> bool:
        """True si el nodo tiene hijos"""
        return len(self.children) > 0
    
    def __repr__(self) -> str:
        children_count = len(self.children)
        return f"TreeNode(label='{self.label}', children={children_count})"


@dataclass
class TableRow:
    """Fila base para estructuras tabulares - sin Qt"""
    columns: Dict[str, str] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    style_hints: Dict[str, str] = field(default_factory=dict)  # Color, font, etc.
    
    def get_column(self, key: str, default: str = "") -> str:
        """Obtiene valor de columna"""
        return self.columns.get(key, default)
    
    def set_column(self, key: str, value: str) -> None:
        """Establece valor de columna"""
        self.columns[key] = value


# ============================================================================
# ORGANIZATION VIEW MODEL
# ============================================================================

@dataclass
class OrganizationTreeNode(TreeNode):
    """Nodo específico para árbol de organización"""
    file_count: int = 0
    total_size: int = 0
    is_conflict: bool = False
    destination_path: Optional[Path] = None
    
    # Información adicional según modo
    month: Optional[str] = None  # Para BY_MONTH
    is_whatsapp: bool = False  # Para WHATSAPP_SEPARATE


class OrganizationViewModel:
    """
    Transforma OrganizationAnalysisResult en estructura de árbol
    según modo de visualización, SIN dependencias de Qt.
    """
    
    @staticmethod
    def build_tree(
        result: OrganizationAnalysisResult,
        mode: OrganizationType
    ) -> List[OrganizationTreeNode]:
        """
        Genera árbol de nodos según modo de visualización
        
        Args:
            result: Resultado del análisis de organización
            mode: Modo de organización (TO_ROOT, BY_MONTH, WHATSAPP_SEPARATE)
            
        Returns:
            Lista de nodos raíz del árbol
        """
        if mode == OrganizationType.TO_ROOT:
            return OrganizationViewModel._build_to_root_tree(result)
        elif mode == OrganizationType.BY_MONTH:
            return OrganizationViewModel._build_by_month_tree(result)
        elif mode == OrganizationType.WHATSAPP_SEPARATE:
            return OrganizationViewModel._build_whatsapp_tree(result)
        else:
            return []
    
    @staticmethod
    def _build_to_root_tree(result: OrganizationAnalysisResult) -> List[OrganizationTreeNode]:
        """
        Construye árbol agrupado por subdirectorio origen
        
        Estructura:
        - Subdirectory1/
          ├─ archivo1.jpg (Estado: Mover)
          ├─ archivo2.mov (Estado: Mover)
        - Subdirectory2/
          └─ archivo3.png (Estado: Mover)
        """
        nodes = []
        
        # Agrupar por subdirectorio
        moves_by_subdir = defaultdict(list)
        for move in result.move_plan:
            moves_by_subdir[move.subdirectory].append(move)
        
        # Crear nodos de subdirectorios
        for subdir_name in sorted(moves_by_subdir.keys()):
            moves = moves_by_subdir[subdir_name]
            
            # Calcular totales del subdirectorio
            total_files = len(moves)
            total_size = sum(move.size for move in moves)
            has_conflicts = any(move.has_conflict for move in moves)
            
            # Nodo de subdirectorio
            subdir_node = OrganizationTreeNode(
                label=subdir_name,
                file_count=total_files,
                total_size=total_size,
                is_conflict=has_conflicts,
                metadata={
                    'type': 'subdirectory',
                    'path': moves[0].source_path.parent if moves else None
                }
            )
            
            # Agregar archivos como hijos
            for move in sorted(moves, key=lambda m: m.original_name):
                file_node = OrganizationTreeNode(
                    label=move.original_name,
                    file_count=1,
                    total_size=move.size,
                    is_conflict=move.has_conflict,
                    destination_path=move.target_path,
                    metadata={
                        'type': 'file',
                        'move': move,
                        'status': 'Conflicto' if move.has_conflict else 'Mover'
                    }
                )
                subdir_node.add_child(file_node)
            
            nodes.append(subdir_node)
        
        return nodes
    
    @staticmethod
    def _build_by_month_tree(result: OrganizationAnalysisResult) -> List[OrganizationTreeNode]:
        """
        Construye árbol agrupado por mes (YYYY_MM)
        
        Estructura:
        - 2023_10/ (Octubre 2023)
          ├─ archivo1.jpg
          ├─ archivo2.mov
        - 2023_11/ (Noviembre 2023)
          └─ archivo3.png
        """
        nodes = []
        
        # Agrupar por carpeta destino (mes)
        moves_by_month = defaultdict(list)
        for move in result.move_plan:
            month_folder = move.target_folder or "Sin_Fecha"
            moves_by_month[month_folder].append(move)
        
        # Crear nodos de meses
        for month_folder in sorted(moves_by_month.keys(), reverse=True):
            moves = moves_by_month[month_folder]
            
            # Calcular totales del mes
            total_files = len(moves)
            total_size = sum(move.size for move in moves)
            has_conflicts = any(move.has_conflict for move in moves)
            
            # Parsear nombre de carpeta para label bonito
            label = OrganizationViewModel._format_month_label(month_folder)
            
            # Nodo de mes
            month_node = OrganizationTreeNode(
                label=label,
                file_count=total_files,
                total_size=total_size,
                is_conflict=has_conflicts,
                month=month_folder,
                metadata={
                    'type': 'month_folder',
                    'folder_name': month_folder
                }
            )
            
            # Agregar archivos como hijos
            for move in sorted(moves, key=lambda m: m.original_name):
                file_node = OrganizationTreeNode(
                    label=move.original_name,
                    file_count=1,
                    total_size=move.size,
                    is_conflict=move.has_conflict,
                    destination_path=move.target_path,
                    metadata={
                        'type': 'file',
                        'move': move,
                        'subdirectory': move.subdirectory
                    }
                )
                month_node.add_child(file_node)
            
            nodes.append(month_node)
        
        return nodes
    
    @staticmethod
    def _build_whatsapp_tree(result: OrganizationAnalysisResult) -> List[OrganizationTreeNode]:
        """
        Construye árbol separando WhatsApp de otros archivos
        
        Estructura:
        - WhatsApp/
          ├─ IMG-20231025-WA0001.jpg
          └─ VID-20231025-WA0002.mp4
        - Otros/
          ├─ IMG_1234.jpg
          └─ VID_5678.mov
        """
        nodes = []
        
        # Separar WhatsApp de otros
        whatsapp_moves = []
        other_moves = []
        
        for move in result.move_plan:
            if move.target_folder == "WhatsApp":
                whatsapp_moves.append(move)
            else:
                other_moves.append(move)
        
        # Nodo WhatsApp
        if whatsapp_moves:
            wa_node = OrganizationTreeNode(
                label="WhatsApp",
                file_count=len(whatsapp_moves),
                total_size=sum(m.size for m in whatsapp_moves),
                is_whatsapp=True,
                metadata={'type': 'category', 'category': 'whatsapp'}
            )
            
            for move in sorted(whatsapp_moves, key=lambda m: m.original_name):
                file_node = OrganizationTreeNode(
                    label=move.original_name,
                    file_count=1,
                    total_size=move.size,
                    is_conflict=move.has_conflict,
                    destination_path=move.target_path,
                    metadata={'type': 'file', 'move': move}
                )
                wa_node.add_child(file_node)
            
            nodes.append(wa_node)
        
        # Nodo Otros
        if other_moves:
            other_node = OrganizationTreeNode(
                label="Otros",
                file_count=len(other_moves),
                total_size=sum(m.size for m in other_moves),
                metadata={'type': 'category', 'category': 'other'}
            )
            
            for move in sorted(other_moves, key=lambda m: m.original_name):
                file_node = OrganizationTreeNode(
                    label=move.original_name,
                    file_count=1,
                    total_size=move.size,
                    is_conflict=move.has_conflict,
                    destination_path=move.target_path,
                    metadata={'type': 'file', 'move': move}
                )
                other_node.add_child(file_node)
            
            nodes.append(other_node)
        
        return nodes
    
    @staticmethod
    def _format_month_label(month_folder: str) -> str:
        """
        Formatea carpeta de mes a label legible
        
        Examples:
            "2023_10" -> "Octubre 2023"
            "2023_11" -> "Noviembre 2023"
            "Sin_Fecha" -> "Sin Fecha"
        """
        if month_folder == "Sin_Fecha":
            return "Sin Fecha"
        
        try:
            year, month = month_folder.split('_')
            month_names = [
                "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
            ]
            month_name = month_names[int(month) - 1]
            return f"{month_name} {year}"
        except (ValueError, IndexError):
            return month_folder


# ============================================================================
# RENAME VIEW MODEL
# ============================================================================

@dataclass
class RenameTableRow(TableRow):
    """Fila específica para tabla de renombrado"""
    original_path: Path = None
    new_name: str = ""
    has_conflict: bool = False
    sequence: Optional[int] = None
    file_size: int = 0
    date: Optional[datetime] = None


class RenameViewModel:
    """
    Transforma RenameAnalysisResult en estructura tabular
    para preview de cambios.
    """
    
    @staticmethod
    def build_table(result: RenameAnalysisResult) -> List[RenameTableRow]:
        """
        Genera lista de filas para tabla de preview
        
        Args:
            result: Resultado del análisis de renombrado
            
        Returns:
            Lista de filas con información de renombrado
        """
        rows = []
        
        for file_info in result.renaming_plan:
            # Crear fila
            row = RenameTableRow(
                original_path=file_info['original_path'],
                new_name=file_info['new_name'],
                has_conflict=file_info.get('has_conflict', False),
                sequence=file_info.get('sequence'),
                file_size=file_info['original_path'].stat().st_size,
                date=file_info.get('date')
            )
            
            # Columnas para tabla
            row.set_column('original', file_info['original_path'].name)
            row.set_column('new_name', file_info['new_name'])
            row.set_column('size', str(row.file_size))
            
            # Estado/Conflicto
            if row.has_conflict:
                row.set_column('status', f'⚠️ Conflicto #{row.sequence}' if row.sequence else '⚠️ Conflicto')
                row.style_hints['status_color'] = '#ff9800'
            else:
                row.set_column('status', '✓ OK')
                row.style_hints['status_color'] = '#4caf50'
            
            # Metadata adicional
            row.metadata['file_info'] = file_info
            
            rows.append(row)
        
        return rows


# ============================================================================
# HEIC VIEW MODEL
# ============================================================================

@dataclass
class HEICTreeNode(TreeNode):
    """Nodo específico para árbol de duplicados HEIC/JPG"""
    heic_path: Optional[Path] = None
    jpg_path: Optional[Path] = None
    heic_size: int = 0
    jpg_size: int = 0
    pair: Optional[DuplicatePair] = None


class HEICViewModel:
    """
    Transforma HeicAnalysisResult en estructura de árbol
    agrupando pares HEIC/JPG.
    """
    
    @staticmethod
    def build_tree(result: HeicAnalysisResult, group_by_directory: bool = True) -> List[HEICTreeNode]:
        """
        Genera árbol de pares HEIC/JPG
        
        Args:
            result: Resultado del análisis HEIC
            group_by_directory: Si True, agrupa por directorio
            
        Returns:
            Lista de nodos raíz del árbol
        """
        if not group_by_directory:
            # Lista plana de pares
            return HEICViewModel._build_flat_list(result)
        
        # Agrupar por directorio
        return HEICViewModel._build_grouped_tree(result)
    
    @staticmethod
    def _build_flat_list(result: HeicAnalysisResult) -> List[HEICTreeNode]:
        """Lista plana de pares sin agrupación"""
        nodes = []
        
        for pair in result.duplicate_pairs:
            node = HEICTreeNode(
                label=pair.base_name,
                heic_path=pair.heic_path,
                jpg_path=pair.jpg_path,
                heic_size=pair.heic_size,
                jpg_size=pair.jpg_size,
                pair=pair,
                metadata={'type': 'pair', 'directory': str(pair.directory)}
            )
            nodes.append(node)
        
        return nodes
    
    @staticmethod
    def _build_grouped_tree(result: HeicAnalysisResult) -> List[HEICTreeNode]:
        """Árbol agrupado por directorio"""
        nodes = []
        
        # Agrupar por directorio
        pairs_by_dir = defaultdict(list)
        for pair in result.duplicate_pairs:
            pairs_by_dir[pair.directory].append(pair)
        
        # Crear nodos de directorio
        for directory in sorted(pairs_by_dir.keys()):
            pairs = pairs_by_dir[directory]
            
            # Nodo de directorio
            dir_node = HEICTreeNode(
                label=directory.name,
                metadata={
                    'type': 'directory',
                    'path': directory,
                    'pair_count': len(pairs)
                }
            )
            
            # Agregar pares como hijos
            for pair in sorted(pairs, key=lambda p: p.base_name):
                pair_node = HEICTreeNode(
                    label=pair.base_name,
                    heic_path=pair.heic_path,
                    jpg_path=pair.jpg_path,
                    heic_size=pair.heic_size,
                    jpg_size=pair.jpg_size,
                    pair=pair,
                    metadata={'type': 'pair'}
                )
                dir_node.add_child(pair_node)
            
            nodes.append(dir_node)
        
        return nodes


# ============================================================================
# DUPLICATES VIEW MODEL
# ============================================================================

@dataclass
class DuplicateTreeNode(TreeNode):
    """Nodo específico para árbol de duplicados"""
    group: Optional[DuplicateGroup] = None
    file_path: Optional[Path] = None
    file_size: int = 0
    is_selected: bool = False
    similarity_score: Optional[float] = None


class DuplicatesViewModel:
    """
    Transforma DuplicateAnalysisResult en estructura de árbol
    para visualización de grupos de duplicados.
    """
    
    @staticmethod
    def build_tree(result: DuplicateAnalysisResult) -> List[DuplicateTreeNode]:
        """
        Genera árbol de grupos de duplicados
        
        Args:
            result: Resultado del análisis de duplicados
            
        Returns:
            Lista de nodos raíz (grupos)
        """
        nodes = []
        
        for idx, group in enumerate(result.groups, 1):
            # Calcular información del grupo
            duplicates_count = len(group.files) - 1  # Excluir original
            total_size = sum(group.file_sizes)
            
            # Label del grupo
            if result.mode == 'exact':
                label = f"Grupo {idx} - {len(group.files)} archivos ({duplicates_count} duplicados)"
            else:  # perceptual
                similarity = group.similarity_score or 0.0
                label = f"Grupo {idx} - {len(group.files)} similares ({similarity:.1f}% similitud)"
            
            # Nodo de grupo
            group_node = DuplicateTreeNode(
                label=label,
                group=group,
                metadata={
                    'type': 'group',
                    'index': idx,
                    'total_size': total_size,
                    'duplicates_count': duplicates_count,
                    'mode': result.mode
                }
            )
            
            # Agregar archivos del grupo como hijos
            for file_idx, (file_path, file_size) in enumerate(zip(group.files, group.file_sizes)):
                # Primer archivo es el "original"
                is_original = file_idx == 0
                file_label = f"{'[CONSERVAR] ' if is_original else ''}  {file_path.name}"
                
                file_node = DuplicateTreeNode(
                    label=file_label,
                    file_path=file_path,
                    file_size=file_size,
                    is_selected=not is_original,  # Marcar duplicados para eliminar
                    metadata={
                        'type': 'file',
                        'is_original': is_original,
                        'file_index': file_idx
                    }
                )
                group_node.add_child(file_node)
            
            nodes.append(group_node)
        
        return nodes
