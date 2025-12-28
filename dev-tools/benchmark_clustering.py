#!/usr/bin/env python3
"""
Benchmark para comparar algoritmo O(N²) vs BK-Tree O(N log N).
Demuestra la mejora real en el clustering.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from unittest.mock import MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.duplicates_similar_service import BKTree, DuplicateGroup
from config import Config


def cluster_naive_on2(
    hashes: Dict[str, Dict[str, Any]], 
    threshold: int
) -> List[DuplicateGroup]:
    """
    Algoritmo ANTIGUO O(N²) - fuerza bruta.
    """
    groups = []
    processed: Set[str] = set()
    paths = list(hashes.keys())
    
    for i, path1 in enumerate(paths):
        if path1 in processed:
            continue
        
        hash1 = hashes[path1]['hash']
        similar_files = [Path(path1)]
        hamming_distances = []
        
        # DOBLE BUCLE - O(N²)
        for j, path2 in enumerate(paths[i + 1:], i + 1):
            if path2 in processed:
                continue
            
            hash2 = hashes[path2]['hash']
            distance = hash1 - hash2
            
            if distance <= threshold:
                similar_files.append(Path(path2))
                hamming_distances.append(distance)
                processed.add(path2)
        
        if len(similar_files) > 1:
            avg_hamming = sum(hamming_distances) / len(hamming_distances)
            similarity_percentage = 100 - (avg_hamming / 64 * 100)
            
            total_size = sum(hashes[str(f)]['size'] for f in similar_files)
            
            group = DuplicateGroup(
                hash_value=str(hash1),
                files=similar_files,
                total_size=total_size,
                similarity_score=similarity_percentage
            )
            groups.append(group)
            processed.add(path1)
    
    return groups


def cluster_bktree_on_logn(
    hashes: Dict[str, Dict[str, Any]], 
    threshold: int
) -> List[DuplicateGroup]:
    """
    Algoritmo NUEVO con BK-Tree O(N log N).
    """
    def hamming_distance(h1, h2):
        return h1 - h2
    
    # Construir BK-Tree
    bk_tree = BKTree(distance_func=hamming_distance)
    paths = list(hashes.keys())
    
    for path in paths:
        bk_tree.add(hashes[path]['hash'], path)
    
    # Clustering con búsquedas eficientes
    groups = []
    processed: Set[str] = set()
    
    for path1 in paths:
        if path1 in processed:
            continue
        
        hash1 = hashes[path1]['hash']
        similar_matches = bk_tree.search(hash1, threshold)
        
        if len(similar_matches) <= 1:
            continue
        
        similar_files = []
        hamming_distances = []
        
        for match_path, distance in similar_matches:
            if match_path not in processed:
                similar_files.append(Path(match_path))
                if match_path != path1:
                    hamming_distances.append(distance)
                processed.add(match_path)
        
        if len(similar_files) > 1:
            avg_hamming = sum(hamming_distances) / len(hamming_distances) if hamming_distances else 0
            similarity_percentage = 100 - (avg_hamming / 64 * 100)
            
            total_size = sum(hashes[str(f)]['size'] for f in similar_files)
            
            group = DuplicateGroup(
                hash_value=str(hash1),
                files=similar_files,
                total_size=total_size,
                similarity_score=similarity_percentage
            )
            groups.append(group)
    
    return groups


def generate_mock_hashes(n: int) -> Dict[str, Dict[str, Any]]:
    """Genera hashes simulados para benchmark."""
    hashes = {}
    
    for i in range(n):
        mock_hash = MagicMock()
        # Simular distancia Hamming basada en diferencia de índices
        mock_hash.__sub__ = lambda self, other, idx=i: abs(getattr(other, '_idx', 0) - idx)
        mock_hash._idx = i
        
        hashes[f"/fake/path/file{i}.jpg"] = {
            'hash': mock_hash,
            'size': 1000000,  # 1MB
            'modified': 1234567890
        }
    
    return hashes


def run_benchmark(n: int, threshold: int = 5):
    """Ejecuta benchmark comparativo."""
    print(f"\n{'='*70}")
    print(f"BENCHMARK: {n:,} archivos, threshold={threshold}")
    print(f"{'='*70}\n")
    
    # Generar datos de prueba
    print(f"Generando {n:,} hashes simulados...")
    hashes = generate_mock_hashes(n)
    print(f"✅ Hashes generados\n")
    
    # Benchmark algoritmo O(N²)
    print(f"🐌 Ejecutando algoritmo ANTIGUO O(N²)...")
    start = time.time()
    groups_naive = cluster_naive_on2(hashes, threshold)
    time_naive = time.time() - start
    print(f"   Tiempo: {time_naive:.3f}s")
    print(f"   Grupos encontrados: {len(groups_naive)}")
    print(f"   Comparaciones estimadas: {n * (n-1) // 2:,}\n")
    
    # Benchmark algoritmo BK-Tree
    print(f"⚡ Ejecutando algoritmo NUEVO BK-Tree O(N log N)...")
    start = time.time()
    groups_bktree = cluster_bktree_on_logn(hashes, threshold)
    time_bktree = time.time() - start
    print(f"   Tiempo: {time_bktree:.3f}s")
    print(f"   Grupos encontrados: {len(groups_bktree)}")
    
    # Resultados
    speedup = time_naive / time_bktree
    print(f"\n{'='*70}")
    print(f"📊 RESULTADOS:")
    print(f"{'='*70}")
    print(f"  Algoritmo O(N²):      {time_naive:.3f}s")
    print(f"  Algoritmo BK-Tree:    {time_bktree:.3f}s")
    print(f"  🚀 MEJORA:            {speedup:.1f}x más rápido")
    print(f"  Tiempo ahorrado:      {time_naive - time_bktree:.3f}s")
    print(f"{'='*70}\n")
    
    return time_naive, time_bktree, speedup


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║  BENCHMARK: Comparación de Algoritmos de Clustering                 ║
║  O(N²) vs BK-Tree O(N log N)                                        ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Benchmarks progresivos
    sizes = [100, 500, 1000, 5000, 10000]
    results = []
    
    for size in sizes:
        if size > 5000:
            print(f"\n⚠️  ADVERTENCIA: {size:,} archivos con O(N²) puede tardar varios minutos...")
            response = input("¿Continuar? (s/n): ")
            if response.lower() != 's':
                print(f"Saltando benchmark de {size:,} archivos")
                continue
        
        time_naive, time_bktree, speedup = run_benchmark(size)
        results.append((size, time_naive, time_bktree, speedup))
        
        # Proyección para dataset completo
        if size >= 1000:
            projected_63k_naive = (time_naive / size) * 63088
            projected_63k_bktree = (time_bktree / size) * 63088
            
            print(f"\n📈 PROYECCIÓN PARA 63,088 ARCHIVOS (tu dataset):")
            print(f"   O(N²):      {projected_63k_naive/60:.1f} minutos")
            print(f"   BK-Tree:    {projected_63k_bktree:.1f} segundos")
            print(f"   Mejora:     {projected_63k_naive/projected_63k_bktree:.0f}x\n")
    
    # Resumen final
    print(f"\n{'='*70}")
    print(f"📊 RESUMEN COMPLETO")
    print(f"{'='*70}")
    print(f"{'Archivos':>10} | {'O(N²) (s)':>12} | {'BK-Tree (s)':>12} | {'Mejora':>10}")
    print(f"{'-'*10}-+-{'-'*12}-+-{'-'*12}-+-{'-'*10}")
    
    for size, t_naive, t_bktree, speedup in results:
        print(f"{size:>10,} | {t_naive:>12.3f} | {t_bktree:>12.3f} | {speedup:>9.1f}x")
    
    print(f"{'='*70}\n")
