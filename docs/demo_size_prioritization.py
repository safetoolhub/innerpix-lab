"""
Script de demostración de la priorización de grupos por tamaño.

Este script demuestra cómo el servicio de duplicados similares
ahora prioriza los grupos donde hay mayor diferencia de tamaño.
"""

from services.result_types import DuplicateGroup
from pathlib import Path


def demo_size_prioritization():
    """Demuestra el algoritmo de priorización por tamaño."""
    
    # Simular datos de hashes para la función
    hashes = {
        # Grupo 1: Gran diferencia de tamaño (WhatsApp vs original)
        '/photos/IMG_001.jpg': {'hash': 12345, 'size': 4_500_000, 'modified': 1.0},  # 4.5 MB
        '/photos/WhatsApp_001.jpg': {'hash': 12346, 'size': 1_200_000, 'modified': 1.0},  # 1.2 MB
        
        # Grupo 2: Tamaños similares (ediciones)
        '/photos/IMG_002.jpg': {'hash': 22345, 'size': 2_100_000, 'modified': 1.0},  # 2.1 MB
        '/photos/IMG_002_edited.jpg': {'hash': 22346, 'size': 2_000_000, 'modified': 1.0},  # 2 MB
        
        # Grupo 3: Enorme diferencia (email vs original)
        '/photos/DSC_0001.jpg': {'hash': 32345, 'size': 3_800_000, 'modified': 1.0},  # 3.8 MB
        '/photos/DSC_0001_email.jpg': {'hash': 32346, 'size': 600_000, 'modified': 1.0},  # 600 KB
    }
    
    # Simular grupos
    groups = [
        DuplicateGroup(
            hash_value='12345',
            files=[Path('/photos/IMG_001.jpg'), Path('/photos/WhatsApp_001.jpg')],
            total_size=5_700_000,
            similarity_score=95.0
        ),
        DuplicateGroup(
            hash_value='22345',
            files=[Path('/photos/IMG_002.jpg'), Path('/photos/IMG_002_edited.jpg')],
            total_size=4_100_000,
            similarity_score=92.0
        ),
        DuplicateGroup(
            hash_value='32345',
            files=[Path('/photos/DSC_0001.jpg'), Path('/photos/DSC_0001_email.jpg')],
            total_size=4_400_000,
            similarity_score=88.0
        ),
    ]
    
    # Función de cálculo de score (copiada del servicio)
    def calculate_size_variation_score(group: DuplicateGroup) -> float:
        """
        Calcula un score basado en la variación de tamaño entre archivos del grupo.
        """
        if len(group.files) < 2:
            return 0.0
        
        # Obtener tamaños de todos los archivos
        sizes = []
        for f in group.files:
            try:
                size = hashes[str(f)]['size']
                sizes.append(size)
            except (KeyError, FileNotFoundError):
                continue
        
        if len(sizes) < 2:
            return 0.0
        
        min_size = min(sizes)
        max_size = max(sizes)
        
        if min_size == 0:
            return 0.0
        
        # Calcular diferencia porcentual
        size_diff_percent = ((max_size - min_size) / min_size) * 100
        
        # Priorizar grupos con diferencia >50%
        if size_diff_percent > 50:
            return 100.0 + size_diff_percent
        
        return size_diff_percent
    
    # Mostrar ANTES de ordenar
    print("=" * 80)
    print("ANTES DE ORDENAR (orden original):")
    print("=" * 80)
    for i, group in enumerate(groups, 1):
        sizes = [hashes[str(f)]['size'] for f in group.files]
        min_s, max_s = min(sizes), max(sizes)
        diff = ((max_s - min_s) / min_s * 100) if min_s > 0 else 0
        score = calculate_size_variation_score(group)
        
        print(f"\nGrupo {i}: Similitud {group.similarity_score:.1f}%")
        print(f"  Archivos: {[f.name for f in group.files]}")
        print(f"  Tamaños: {[f'{s/1_000_000:.1f} MB' for s in sizes]}")
        print(f"  Diferencia: {diff:.1f}%")
        print(f"  Score de prioridad: {score:.1f}")
    
    # Ordenar grupos
    groups.sort(key=calculate_size_variation_score, reverse=True)
    
    # Mostrar DESPUÉS de ordenar
    print("\n" + "=" * 80)
    print("DESPUÉS DE ORDENAR (priorizando diferencia >50%):")
    print("=" * 80)
    for i, group in enumerate(groups, 1):
        sizes = [hashes[str(f)]['size'] for f in group.files]
        min_s, max_s = min(sizes), max(sizes)
        diff = ((max_s - min_s) / min_s * 100) if min_s > 0 else 0
        score = calculate_size_variation_score(group)
        
        priority = "⭐ ALTA PRIORIDAD" if score > 100 else "Baja prioridad"
        
        print(f"\nGrupo {i}: Similitud {group.similarity_score:.1f}% - {priority}")
        print(f"  Archivos: {[f.name for f in group.files]}")
        print(f"  Tamaños: {[f'{s/1_000_000:.1f} MB' for s in sizes]}")
        print(f"  Diferencia: {diff:.1f}%")
        print(f"  Score de prioridad: {score:.1f}")
    
    print("\n" + "=" * 80)
    print("RESUMEN:")
    print("=" * 80)
    high_priority = sum(1 for g in groups if calculate_size_variation_score(g) > 100)
    print(f"Total de grupos: {len(groups)}")
    print(f"Grupos con alta prioridad (diferencia >50%): {high_priority}")
    print(f"Grupos con baja prioridad: {len(groups) - high_priority}")
    print("\n💡 Los grupos con alta prioridad (WhatsApp, email, etc.) aparecen primero")
    print("   para facilitar la revisión de duplicados en diferentes calidades.\n")


if __name__ == "__main__":
    demo_size_prioritization()
