#!/usr/bin/env python3
"""
Script para ejecutar tests del proyecto Pixaro Lab

Uso:
    python run_tests.py                    # Ejecutar todos los tests
    python run_tests.py test_file_renamer  # Ejecutar solo tests de FileRenamer
"""

import sys
import unittest
from pathlib import Path

# Añadir el directorio raíz al path para imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_all_tests():
    """Ejecutar todos los tests del proyecto"""
    loader = unittest.TestLoader()
    start_dir = project_root / 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


def run_specific_test(test_name):
    """Ejecutar un test específico"""
    loader = unittest.TestLoader()
    
    try:
        # Intentar cargar el módulo de test específico
        module_path = f'tests.{test_name}'
        suite = loader.loadTestsFromName(module_path)
    except Exception as e:
        print(f"Error cargando test '{test_name}': {e}")
        return 1
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Ejecutar test específico
        exit_code = run_specific_test(sys.argv[1])
    else:
        # Ejecutar todos los tests
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
