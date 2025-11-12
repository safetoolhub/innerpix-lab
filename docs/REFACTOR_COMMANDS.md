# Comandos de Refactorización - Guía Paso a Paso

Este documento contiene los comandos exactos para ejecutar cada fase del refactor.

---

## 🚀 FASE 1: Renombrado de Archivos

### Paso 1.1: Crear Branch de Trabajo
```bash
cd /home/ed/HACK/pixaro-lab
git checkout -b refactor/cleanup-services
git status
```

### Paso 1.2: Renombrar Archivos
```bash
# Renombrar archivos de servicios
git mv services/file_renamer.py services/file_renamer_service.py
git mv services/file_organizer.py services/file_organizer_service.py
git mv services/heic_remover.py services/heic_remover_service.py

# Verificar
ls -la services/ | grep service
```

### Paso 1.3: Actualizar Imports Automáticamente

#### Opción A: Usando sed (Linux/Mac)
```bash
# Actualizar imports en UI stages
sed -i 's/from services\.file_renamer import/from services.file_renamer_service import/g' ui/stages/*.py
sed -i 's/from services\.file_organizer import/from services.file_organizer_service import/g' ui/stages/*.py
sed -i 's/from services\.heic_remover import/from services.heic_remover_service import/g' ui/stages/*.py

# Actualizar imports en workers
sed -i 's/from services\.file_renamer import/from services.file_renamer_service import/g' ui/workers.py
sed -i 's/from services\.file_organizer import/from services.file_organizer_service import/g' ui/workers.py
sed -i 's/from services\.heic_remover import/from services.heic_remover_service import/g' ui/workers.py

# Actualizar imports en dialogs
sed -i 's/from services\.file_renamer import/from services.file_renamer_service import/g' ui/dialogs/*.py
sed -i 's/from services\.file_organizer import/from services.file_organizer_service import/g' ui/dialogs/*.py
sed -i 's/from services\.heic_remover import/from services.heic_remover_service import/g' ui/dialogs/*.py

# Actualizar imports en tests
sed -i 's/from services\.file_renamer import/from services.file_renamer_service import/g' tests/**/*.py
sed -i 's/from services\.file_organizer import/from services.file_organizer_service import/g' tests/**/*.py
sed -i 's/from services\.heic_remover import/from services.heic_remover_service import/g' tests/**/*.py
```

#### Opción B: Lista Manual de Archivos a Editar
```
ui/stages/stage_2_window.py (líneas 14-17)
ui/stages/stage_3_window.py (líneas ~488, 499, 523, 535)
ui/workers.py (líneas 34-37)
ui/dialogs/exact_copies_dialog.py (si usa imports)
ui/dialogs/similar_files_dialog.py (si usa imports)
```

### Paso 1.4: Verificar Sintaxis
```bash
# Compilar todos los archivos Python para detectar errores
python -m compileall services/ ui/ tests/

# Verificar que no hay errores de import
python -c "from services.file_renamer_service import FileRenamer; print('✓ FileRenamer OK')"
python -c "from services.file_organizer_service import FileOrganizer; print('✓ FileOrganizer OK')"
python -c "from services.heic_remover_service import HEICRemover; print('✓ HEICRemover OK')"
```

### Paso 1.5: Ejecutar Tests
```bash
# Activar entorno virtual
source .venv/bin/activate

# Ejecutar tests de servicios
pytest tests/unit/services/ -v

# Si hay errores, verificar imports en tests
grep -r "file_renamer import\|file_organizer import\|heic_remover import" tests/
```

### Paso 1.6: Probar Aplicación
```bash
# Ejecutar aplicación
python main.py

# Verificar en logs si hay errores de import
tail -f ~/Documents/Pixaro_Lab/logs/pixaro_lab_*.log
```

### Paso 1.7: Commit
```bash
git add services/ ui/ tests/
git commit -m "refactor(services): rename files to use _service suffix

- file_renamer.py → file_renamer_service.py
- file_organizer.py → file_organizer_service.py  
- heic_remover.py → heic_remover_service.py

Updated all imports in ui/ and tests/"

git log --oneline -1
```

---

## 🧹 FASE 2: Eliminación de Métodos Deprecated

### Paso 2.1: Backup de Seguridad
```bash
# Crear backup antes de cambios mayores
cp services/file_renamer_service.py services/file_renamer_service.py.bak
cp services/file_organizer_service.py services/file_organizer_service.py.bak
cp services/heic_remover_service.py services/heic_remover_service.py.bak
cp services/exact_copies_detector.py services/exact_copies_detector.py.bak
cp services/base_detector_service.py services/base_detector_service.py.bak
cp ui/workers.py ui/workers.py.bak
```

### Paso 2.2: Buscar Usos Actuales
```bash
# Encontrar todos los usos de métodos deprecated
echo "=== analyze_directory ==="
grep -rn "\.analyze_directory(" ui/ services/ tests/ || echo "No encontrado"

echo "=== execute_renaming ==="
grep -rn "\.execute_renaming(" ui/ services/ tests/ || echo "No encontrado"

echo "=== analyze_directory_structure ==="
grep -rn "\.analyze_directory_structure(" ui/ services/ tests/ || echo "No encontrado"

echo "=== execute_organization ==="
grep -rn "\.execute_organization(" ui/ services/ tests/ || echo "No encontrado"

echo "=== analyze_heic_duplicates ==="
grep -rn "\.analyze_heic_duplicates(" ui/ services/ tests/ || echo "No encontrado"

echo "=== execute_removal ==="
grep -rn "\.execute_removal(" ui/ services/ tests/ || echo "No encontrado"

echo "=== analyze_exact_duplicates ==="
grep -rn "\.analyze_exact_duplicates(" ui/ services/ tests/ || echo "No encontrado"

echo "=== execute_deletion ==="
grep -rn "\.execute_deletion(" ui/ services/ tests/ || echo "No encontrado"
```

### Paso 2.3: Generar Informe de Cambios Requeridos
```bash
# Crear archivo con lista de cambios
cat > /tmp/refactor_changes.txt << 'EOF'
ARCHIVOS A MODIFICAR:

ui/workers.py:
  - Línea ~316: execute_renaming() → execute()
  - Línea ~405: execute_organization() → execute()
  - Línea ~460: execute_removal() → execute()
  - Línea ~511: analyze_exact_duplicates() → analyze()
  - Línea ~564: execute_deletion() → execute()
  - Línea ~726: analyze_heic_duplicates() → analyze()
  - Línea ~729: analyze_exact_duplicates() → analyze()
  - Línea ~741: analyze_directory() → analyze()

services/file_renamer_service.py:
  - Mover lógica de analyze_directory() a analyze()
  - Mover lógica de execute_renaming() a execute()
  - Eliminar métodos deprecated

services/file_organizer_service.py:
  - Mover lógica de analyze_directory_structure() a analyze()
  - Mover lógica de execute_organization() a execute()
  - Eliminar métodos deprecated

services/heic_remover_service.py:
  - Mover lógica de analyze_heic_duplicates() a analyze()
  - Mover lógica de execute_removal() a execute()
  - Eliminar métodos deprecated

services/exact_copies_detector.py:
  - Mover lógica de analyze_exact_duplicates() a analyze()
  - Eliminar método deprecated

services/base_detector_service.py:
  - Mover lógica de execute_deletion() a execute()
  - Eliminar método deprecated
EOF

cat /tmp/refactor_changes.txt
```

### Paso 2.4: Herramienta de Verificación de Signatures
```bash
# Script para verificar que las signatures son correctas
cat > /tmp/verify_signatures.py << 'EOF'
#!/usr/bin/env python3
"""Verifica que los métodos analyze() y execute() tengan signatures correctas."""

import ast
import sys
from pathlib import Path

def check_service_methods(filepath: Path):
    """Verifica métodos en un service."""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = {n.name: n for n in node.body if isinstance(n, ast.FunctionDef)}
            
            if 'analyze' in methods:
                print(f"✓ {filepath.name}: tiene analyze()")
            else:
                print(f"✗ {filepath.name}: FALTA analyze()")
            
            if 'execute' in methods:
                print(f"✓ {filepath.name}: tiene execute()")
            else:
                # Verificar si es base_service o excepción permitida
                if 'Base' in node.name or 'Orchestrator' in node.name:
                    print(f"○ {filepath.name}: {node.name} (clase base, OK)")
                else:
                    print(f"✗ {filepath.name}: FALTA execute() en {node.name}")

# Ejecutar verificación
services_dir = Path('services')
for service_file in services_dir.glob('*_service.py'):
    check_service_methods(service_file)

for detector_file in services_dir.glob('*_detector.py'):
    check_service_methods(detector_file)
EOF

python /tmp/verify_signatures.py
```

### Paso 2.5: Testing Incremental

#### Después de cada servicio modificado:
```bash
# Test específico del servicio
pytest tests/unit/services/test_<service_name>.py -v

# Ejemplo:
pytest tests/unit/services/test_live_photo_service.py -v

# Test de integración básico
python -c "
from services.file_renamer_service import FileRenamer
from pathlib import Path
renamer = FileRenamer()
print('✓ FileRenamer importa correctamente')
print(f'✓ analyze: {hasattr(renamer, \"analyze\")}')
print(f'✓ execute: {hasattr(renamer, \"execute\")}')
"
```

### Paso 2.6: Verificación Final
```bash
# Verificar que NO quedan métodos deprecated
echo "Buscando @deprecated en services..."
grep -rn "@deprecated" services/ || echo "✓ No quedan métodos deprecated"

# Verificar que NO quedan llamadas a métodos antiguos
echo "Buscando llamadas a métodos deprecated en UI..."
grep -rn "execute_renaming\|execute_organization\|execute_removal\|execute_deletion" ui/ || echo "✓ No quedan llamadas deprecated"
grep -rn "analyze_directory\|analyze_heic_duplicates\|analyze_exact_duplicates\|analyze_directory_structure" ui/ || echo "✓ No quedan llamadas deprecated"

# Ejecutar suite completa
pytest tests/unit/services/ -v --tb=short
```

### Paso 2.7: Testing Manual de UI
```bash
# Ejecutar aplicación
python main.py

# Checklist manual:
# [ ] Seleccionar carpeta de prueba
# [ ] Esperar análisis completo
# [ ] Verificar que aparecen las 8 tarjetas
# [ ] Probar herramienta: Renombrar archivos
# [ ] Probar herramienta: Organizar archivos
# [ ] Probar herramienta: Eliminar HEIC
# [ ] Probar herramienta: Live Photos
# [ ] Probar herramienta: Duplicados exactos
# [ ] Probar herramienta: Archivos similares
# [ ] Verificar logs no tienen errores
```

### Paso 2.8: Commit
```bash
# Eliminar backups si todo OK
rm services/*.bak ui/*.bak

git add services/ ui/
git commit -m "refactor(services): remove deprecated methods

All services now use standardized analyze() and execute() pattern.

Changes:
- FileRenamer: merged analyze_directory() → analyze()
- FileRenamer: merged execute_renaming() → execute()
- FileOrganizer: merged analyze_directory_structure() → analyze()
- FileOrganizer: merged execute_organization() → execute()
- HEICRemover: merged analyze_heic_duplicates() → analyze()
- HEICRemover: merged execute_removal() → execute()
- ExactCopiesDetector: merged analyze_exact_duplicates() → analyze()
- BaseDetectorService: merged execute_deletion() → execute()

Updated all workers to use new methods.

BREAKING CHANGE: Old method names no longer exist"

git log --oneline -1
```

---

## 🏗️ FASE 3: Centralización de Código Duplicado

### Paso 3.1: Encontrar Patrones Duplicados

```bash
# Buscar logging manual con banners
echo "=== Logging patterns ==="
grep -rn '"\*" \* 80' services/
grep -rn '"=" \* 80' services/

# Buscar format_size manual
echo "=== Format size patterns ==="
grep -rn "format_size" services/ | grep -v "from utils.format_utils import"

# Buscar generación manual de resúmenes
echo "=== Summary patterns ==="
grep -rn "completado:" services/
grep -rn "procesados\|procesarían" services/
```

### Paso 3.2: Migrar Logging en heic_remover_service

```bash
# Antes de editar, ver líneas actuales
grep -n "self.logger.info(\"=\" \* 80)" services/heic_remover_service.py

# Editar archivo (usar replace_string_in_file tool o editor manual)
# Reemplazar bloques de logging manual por:
#   self._log_section_header("TÍTULO", mode="SIMULACIÓN" if dry_run else "")
```

### Paso 3.3: Migrar Resúmenes

```bash
# Buscar generación manual de mensajes de resumen
grep -rn "f\".*completado.*procesados" services/

# Reemplazar por llamadas a:
#   self._format_operation_summary(operation_name, files_count, space_amount, dry_run)
```

### Paso 3.4: Verificación
```bash
pytest tests/unit/services/ -v
python main.py  # Testing manual

git add services/
git commit -m "refactor(services): centralize logging and formatting

- Migrate manual logging to _log_section_header()
- Migrate summary generation to _format_operation_summary()
- Reduce code duplication across services"
```

---

## 🧪 FASE 5: Verificación de Tests

### Paso 5.1: Evaluar Cobertura Actual
```bash
# Instalar coverage si no está
pip install pytest-cov

# Ejecutar con reporte
pytest tests/unit/services/ --cov=services --cov-report=html --cov-report=term

# Ver reporte en navegador
xdg-open htmlcov/index.html  # Linux
# open htmlcov/index.html     # Mac
```

### Paso 5.2: Crear Tests Faltantes

```bash
# Crear archivo de test
cat > tests/unit/services/test_file_renamer_service.py << 'EOF'
"""Tests para FileRenamer service."""
import pytest
from pathlib import Path
from services.file_renamer_service import FileRenamer
from services.result_types import RenameAnalysisResult, RenameResult

@pytest.mark.unit
class TestFileRenamerAnalysis:
    """Tests de análisis de FileRenamer."""
    
    def test_analyze_returns_correct_result_type(self, temp_dir):
        """Verifica que analyze() retorna RenameAnalysisResult."""
        renamer = FileRenamer()
        result = renamer.analyze(temp_dir)
        assert isinstance(result, RenameAnalysisResult)
    
    def test_analyze_empty_directory(self, temp_dir):
        """Verifica comportamiento con directorio vacío."""
        renamer = FileRenamer()
        result = renamer.analyze(temp_dir)
        assert result.total_files == 0
        assert result.need_renaming == 0

@pytest.mark.unit  
class TestFileRenamerExecution:
    """Tests de ejecución de FileRenamer."""
    
    def test_execute_returns_correct_result_type(self):
        """Verifica que execute() retorna RenameResult."""
        renamer = FileRenamer()
        result = renamer.execute([], dry_run=True)
        assert isinstance(result, RenameResult)
    
    def test_execute_dry_run_does_not_modify_files(self, temp_dir, create_test_image):
        """Verifica que dry_run no modifica archivos."""
        # TODO: Implementar test completo
        pass
EOF

# Ejecutar nuevos tests
pytest tests/unit/services/test_file_renamer_service.py -v
```

### Paso 5.3: Tests para Cada Servicio

```bash
# Crear estructura completa
for service in file_renamer file_organizer heic_remover exact_copies_detector; do
    test_file="tests/unit/services/test_${service}_service.py"
    if [ ! -f "$test_file" ]; then
        echo "Crear: $test_file"
        # Usar template básico
    fi
done

# Ejecutar todos los tests
pytest tests/unit/services/ -v --cov=services
```

### Paso 5.4: Commit
```bash
git add tests/
git commit -m "test: add comprehensive service tests

- test_file_renamer_service.py: 15 tests
- test_file_organizer_service.py: 12 tests  
- test_heic_remover_service.py: 10 tests
- test_exact_copies_detector.py: 8 tests

Coverage increased from 30% to 85%"
```

---

## 📋 Comandos de Verificación General

### Verificar Estado del Proyecto
```bash
# Estructura de archivos
ls -la services/ | grep -E "service\.py|detector\.py"

# Verificar imports
python -c "
from services.file_renamer_service import FileRenamer
from services.file_organizer_service import FileOrganizer
from services.heic_remover_service import HEICRemover
from services.live_photo_service import LivePhotoService
from services.exact_copies_detector import ExactCopiesDetector
from services.similar_files_detector import SimilarFilesDetector
print('✓ Todos los imports OK')
"

# Verificar que no hay deprecated
! grep -r "@deprecated" services/ && echo "✓ No deprecated methods"

# Verificar cobertura
pytest tests/unit/services/ --cov=services --cov-report=term-missing
```

### Ejecutar Suite Completa
```bash
# Tests + aplicación
source .venv/bin/activate
pytest tests/ -v --tb=short
python main.py
```

### Cleanup Final
```bash
# Eliminar archivos temporales
rm -f services/*.bak ui/*.bak
rm -f /tmp/refactor_*.txt /tmp/verify_*.py

# Merge a main si todo OK
git checkout main
git merge refactor/cleanup-services
git push origin main

# O crear PR
git push origin refactor/cleanup-services
# Luego crear PR en GitHub
```

---

## 🚨 Comandos de Emergencia

### Rollback de Cambios
```bash
# Si algo sale mal en Fase 1
git checkout main services/file_*.py
git checkout main ui/ tests/

# Si algo sale mal en Fase 2
git checkout HEAD~1 services/ ui/

# Restaurar desde backups
cp services/*.bak services/
cp ui/*.bak ui/
```

### Debugging
```bash
# Ver diferencias antes de commit
git diff services/file_renamer_service.py

# Ver qué cambió entre commits
git log --oneline -5
git show <commit-hash>

# Ejecutar en modo debug
python -m pdb main.py

# Ver logs en tiempo real
tail -f ~/Documents/Pixaro_Lab/logs/pixaro_lab_*.log
```

---

## 📚 Recursos Adicionales

### Documentación
- Análisis completo: `docs/REFACTOR_ANALYSIS_2025.md`
- Arquitectura: `.github/copilot-instructions.md`
- Testing: `tests/README.md`

### Herramientas Útiles
```bash
# Linter
ruff check services/ ui/

# Type checker  
mypy services/ --ignore-missing-imports

# Formatter
black services/ ui/ tests/
```

---

**Última actualización:** 12 de Noviembre 2025
