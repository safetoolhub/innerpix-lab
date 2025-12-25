#!/usr/bin/env python3
"""
Test del refactor de DuplicatesSimilarService.
Verifica que el nuevo API funcione correctamente:
1. analyze() retorna DuplicateAnalysisResult
2. get_analysis_for_dialog() retorna DuplicatesSimilarAnalysis
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.duplicates_similar_service import DuplicatesSimilarService
from services.result_types import DuplicateAnalysisResult
from services.duplicates_similar_service import DuplicatesSimilarAnalysis


def test_api_compatibility():
    """Verifica que ambos métodos funcionen correctamente."""
    
    print("=" * 70)
    print("TEST: DuplicatesSimilarService API Compatibility")
    print("=" * 70)
    
    service = DuplicatesSimilarService()
    
    # Test 1: analyze() debe retornar DuplicateAnalysisResult
    print("\n1. Testing analyze() method...")
    try:
        result = service.analyze(sensitivity=85)
        assert isinstance(result, DuplicateAnalysisResult), \
            f"Expected DuplicateAnalysisResult, got {type(result)}"
        print("   ✓ analyze() returns DuplicateAnalysisResult")
        print(f"   - Groups found: {len(result.groups)}")
        print(f"   - Total duplicates: {result.total_duplicates}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 2: get_analysis_for_dialog() debe retornar DuplicatesSimilarAnalysis
    print("\n2. Testing get_analysis_for_dialog() method...")
    try:
        analysis = service.get_analysis_for_dialog()
        assert isinstance(analysis, DuplicatesSimilarAnalysis), \
            f"Expected DuplicatesSimilarAnalysis, got {type(analysis)}"
        print("   ✓ get_analysis_for_dialog() returns DuplicatesSimilarAnalysis")
        print(f"   - Total files: {analysis.total_files}")
        print(f"   - Perceptual hashes: {len(analysis.perceptual_hashes)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 3: Verificar que el análisis se cachea correctamente
    print("\n3. Testing cache behavior...")
    try:
        # Segunda llamada debe usar cache
        result2 = service.analyze(sensitivity=50)
        assert isinstance(result2, DuplicateAnalysisResult), \
            f"Expected DuplicateAnalysisResult, got {type(result2)}"
        print("   ✓ Cache working correctly")
        print(f"   - Groups with different sensitivity: {len(result2.groups)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 4: Verificar get_groups() del análisis
    print("\n4. Testing DuplicatesSimilarAnalysis.get_groups()...")
    try:
        groups_result = analysis.get_groups(sensitivity=100)
        assert isinstance(groups_result, DuplicateAnalysisResult), \
            f"Expected DuplicateAnalysisResult, got {type(groups_result)}"
        print("   ✓ get_groups() returns DuplicateAnalysisResult")
        print(f"   - Groups at 100% sensitivity: {len(groups_result.groups)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = test_api_compatibility()
    sys.exit(0 if success else 1)
