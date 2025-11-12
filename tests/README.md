# Tests de Pixaro Lab# Suite de Tests - Pixaro Lab



Sistema de testing profesional con pytest para garantizar la calidad del código.Esta carpeta contiene la suite de tests automatizados para Pixaro Lab.



## Estructura del Proyecto## Estructura



``````

tests/tests/

├── conftest.py              # Fixtures compartidas y configuración global├── __init__.py                 # Paquete de tests

├── unit/                    # Tests unitarios (lógica aislada)├── test_window_size.py         # Tests para lógica de tamaño de ventana

│   ├── services/           # Tests de servicios (FileRenamer, LivePhotoCleaner, etc.)└── ...                         # Más tests en el futuro

│   └── utils/              # Tests de utilidades (file_utils, date_utils, etc.)```

├── integration/             # Tests de integración (múltiples componentes)

└── README.md               # Esta documentación## Ejecutar Tests

```

### Opción 1: Script dedicado

## Ejecutar Tests```bash

./run_tests.sh

### Todos los tests```

```bash

pytest### Opción 2: pytest directamente

``````bash

# Activar entorno virtual

### Tests por directoriosource .venv/bin/activate

```bash

pytest tests/unit/services/          # Solo tests de servicios# Ejecutar todos los tests

pytest tests/unit/utils/             # Solo tests de utilidadespytest

pytest tests/integration/            # Solo tests de integración

```# Ejecutar con cobertura

pytest --cov=.

### Tests por archivo

```bash# Ejecutar tests específicos

pytest tests/unit/services/test_live_photo_detector.pypytest tests/test_window_size.py

pytest tests/unit/services/test_live_photo_cleaner.py

```# Ejecutar un test específico

pytest tests/test_window_size.py::TestWindowSizeLogic::test_window_size_logic

### Tests con marcadores```

```bash

pytest -m unit                       # Solo tests unitarios## Configuración

pytest -m live_photos                # Solo tests de Live Photos

pytest -m "unit and live_photos"     # Intersección de marcadores- **pytest.ini**: Configuración de pytest

pytest -m "not slow"                 # Excluir tests lentos- **.coveragerc**: Configuración de coverage

```- **requirements-dev.txt**: Dependencias para desarrollo y testing



### Opciones útiles## Tests Implementados

```bash

pytest -v                            # Verbose (más detalles)### test_window_size.py

pytest -s                            # Mostrar prints

pytest --tb=short                    # Traceback cortoTests para la lógica de configuración automática del tamaño de ventana:

pytest -x                            # Detenerse en primer fallo

pytest --lf                          # Solo ejecutar fallos previos (last failed)- **TestWindowSizeLogic**:

pytest --ff                          # Ejecutar fallos primero (failed first)  - `test_window_size_logic`: Tests parametrizados que verifican la lógica de maximización vs FullHD

pytest -k "test_cleanup"             # Ejecutar tests que contengan "cleanup"  - `test_window_centering_calculation`: Verifica el cálculo correcto del centrado

```  - `test_screen_resolution_detection`: Tests de mocking para detección de resolución

  - `test_resolution_categories`: Clasificación de resoluciones en categorías

### Coverage (cobertura de código)

```bash- **TestWindowSizeIntegration**:

# Ejecutar con reporte de cobertura  - Tests de integración (pendientes de implementar completamente)

pytest --cov=services --cov=utils --cov-report=html

## Cobertura

# Ver reporte en navegador

open htmlcov/index.htmlLos tests están configurados para:

```- Cobertura mínima del 80%

- Reportes HTML en `htmlcov/`

## Marcadores Disponibles- Exclusión de archivos de venv y cache



Configurados en `pytest.ini`:## Desarrollo



- `@pytest.mark.unit` - Tests unitarios (componentes aislados)### Agregar nuevos tests

- `@pytest.mark.integration` - Tests de integración (múltiples componentes)

- `@pytest.mark.ui` - Tests de interfaz gráfica1. Crear archivo `test_<modulo>.py` en `tests/`

- `@pytest.mark.slow` - Tests que tardan mucho tiempo2. Usar `pytest.mark.parametrize` para tests con múltiples casos

- `@pytest.mark.live_photos` - Tests específicos de Live Photos3. Seguir el patrón de nombrado: `test_<funcionalidad>_<escenario>`

- `@pytest.mark.duplicates` - Tests específicos de duplicados

- `@pytest.mark.renaming` - Tests específicos de renombrado### Instalar dependencias de desarrollo

- `@pytest.mark.organization` - Tests específicos de organización

```bash

## Fixtures Disponiblespip install -r requirements-dev.txt

```

Definidas en `conftest.py`:

### Configurar pre-commit hooks

### Básicas

- `temp_dir` - Directorio temporal con limpieza automática```bash

- `create_test_image(path, name, size, format)` - Factory para crear imágenes de pruebapip install pre-commit

- `create_test_video(path, name, size)` - Factory para crear videos de pruebapre-commit install

```

### Live Photos

- `create_live_photo_pair(directory, base_name, img_size, vid_size)` - Crea un par imagen+video## CI/CD

- `sample_live_photos_directory(temp_dir)` - Directorio completo con múltiples Live Photos

Los tests están preparados para integración continua con:

### Ejemplo de uso- Ejecución automática en push/PR

```python- Cobertura de código

def test_my_feature(temp_dir, create_test_image):- Linting con flake8

    """Test que usa fixtures."""- Formateo con black/isort
    # temp_dir es un Path a directorio temporal limpio
    img_path = create_test_image(temp_dir, 'test.jpg', (100, 100))
    
    # Tu lógica de test aquí
    assert img_path.exists()
    # temp_dir se limpia automáticamente al terminar
```

## Escribir Nuevos Tests

### Estructura Recomendada

```python
"""
Descripción breve del módulo de tests.
"""

import pytest
from pathlib import Path
from services.mi_servicio import MiServicio


@pytest.mark.unit
@pytest.mark.nombre_funcionalidad
class TestMiServicioBasics:
    """Tests básicos de funcionalidad."""
    
    def test_initialization(self):
        """Test que el servicio se inicializa correctamente."""
        service = MiServicio()
        assert service is not None
        assert service.logger is not None
    
    def test_basic_functionality(self, temp_dir):
        """Test de funcionalidad básica."""
        service = MiServicio()
        result = service.do_something(temp_dir)
        
        assert result.success == True
        assert result.data is not None


@pytest.mark.unit
@pytest.mark.nombre_funcionalidad
class TestMiServicioEdgeCases:
    """Tests de casos edge y situaciones especiales."""
    
    def test_handles_empty_input(self):
        """Test que maneja entrada vacía correctamente."""
        service = MiServicio()
        result = service.do_something(Path('/nonexistent'))
        
        assert result.success == False
        assert result.message is not None
```

### Convenciones de Naming

- **Archivos**: `test_<nombre_servicio>.py` (ej: `test_file_renamer.py`)
- **Clases**: `Test<Nombre><Aspecto>` (ej: `TestFileRenamerBasics`)
- **Funciones**: `test_<lo_que_prueba>` (ej: `test_renames_single_file`)

### Organización por Clases

Agrupa tests relacionados en clases con nombres descriptivos:

- `TestXxxBasics` - Inicialización, funcionalidad básica
- `TestXxxAnalysis` - Tests de análisis/detección
- `TestXxxExecution` - Tests de ejecución/operaciones
- `TestXxxEdgeCases` - Casos edge, situaciones especiales
- `TestXxxValidation` - Validación de datos, dataclasses
- `TestXxxIntegration` - Integración con otros componentes

### Assertions Claras

```python
# ✅ BIEN: Assertions claras y específicas
assert result.success == True
assert result.files_processed == 5
assert img_path.exists()
assert len(analysis.errors) == 0

# ❌ MAL: Assertions genéricas o ambiguas
assert result
assert len(files) > 0
```

### Docstrings Descriptivos

```python
def test_analyze_cleanup_keep_image_mode(self, temp_dir, create_live_photo_pair):
    """Test análisis en modo KEEP_IMAGE (eliminar videos)."""
    # El docstring explica claramente qué se está probando
```

## Mejores Prácticas

### 1. Tests Independientes
Cada test debe poder ejecutarse solo y en cualquier orden.

```python
# ✅ BIEN: Cada test crea su propio setup
def test_feature_a(temp_dir, create_test_image):
    img = create_test_image(temp_dir, 'test.jpg')
    # test logic...

def test_feature_b(temp_dir, create_test_image):
    img = create_test_image(temp_dir, 'another.jpg')
    # test logic...
```

### 2. Usar Fixtures para Setup/Teardown
Las fixtures manejan limpieza automáticamente.

```python
# ✅ BIEN: Usa fixture temp_dir con limpieza automática
def test_with_files(temp_dir, create_test_image):
    img = create_test_image(temp_dir, 'test.jpg')
    # temp_dir se limpia al terminar

# ❌ MAL: Limpieza manual propensa a errores
def test_with_files():
    temp = Path('/tmp/test')
    temp.mkdir()
    try:
        # test logic...
    finally:
        shutil.rmtree(temp)  # Puede fallar si hay errores
```

### 3. Tests Rápidos
Los tests unitarios deben ser rápidos (<1 segundo cada uno).

```python
# ✅ BIEN: Usa datos mínimos necesarios
def test_detection(temp_dir, create_live_photo_pair):
    create_live_photo_pair(temp_dir, 'IMG_0001')  # 1 par suficiente
    detector = LivePhotoDetector()
    result = detector.detect_in_directory(temp_dir)
    assert len(result) == 1

# ❌ MAL: Crea datos innecesarios
def test_detection(temp_dir, create_live_photo_pair):
    for i in range(1000):  # Demasiados datos para test simple
        create_live_photo_pair(temp_dir, f'IMG_{i:04d}')
```

### 4. Marcar Tests Lentos
Si un test necesita mucho tiempo, márcalo con `@pytest.mark.slow`:

```python
@pytest.mark.slow
def test_process_large_dataset(temp_dir):
    """Test con dataset grande (5+ segundos)."""
    # Este test puede saltarse con: pytest -m "not slow"
```

### 5. Tests Descriptivos con Arrange-Act-Assert

```python
def test_cleanup_deletes_videos_keep_images(self, temp_dir, create_live_photo_pair):
    """Test que cleanup en modo KEEP_IMAGE elimina videos y mantiene imágenes."""
    # Arrange (preparar)
    img_path, vid_path = create_live_photo_pair(temp_dir, 'IMG_0001')
    cleaner = LivePhotoCleaner()
    analysis = cleaner.analyze_cleanup(temp_dir, mode=CleanupMode.KEEP_IMAGE)
    
    # Act (actuar)
    result = cleaner.execute_cleanup(analysis, create_backup=False, dry_run=False)
    
    # Assert (verificar)
    assert result.success == True
    assert img_path.exists()
    assert not vid_path.exists()
```

## Estado Actual (Diciembre 2024)

### Tests Implementados ✅

- **LivePhotoDetector**: 24 tests
  - Inicialización y herencia
  - Detección de pares (single, múltiple, renombrados)
  - Detección recursiva
  - Validación de LivePhotoGroup
  - Casos edge y caracteres especiales
  
- **LivePhotoCleaner**: 20 tests
  - Inicialización y modos de limpieza
  - Análisis (KEEP_IMAGE, KEEP_VIDEO, KEEP_LARGER, KEEP_SMALLER)
  - Ejecución (dry-run, real, con backup)
  - Casos edge (archivos faltantes, análisis vacíos)
  - Integración con detector

**Total: 44 tests pasando al 100%**

### Próximos Pasos 🚧

Pendiente de implementar tests para:

- `FileRenamer` - Renombrado de archivos
- `FileOrganizer` - Organización por fechas
- `HEICRemover` - Eliminación de HEIC duplicados
- `ExactCopiesDetector` - Detección de copias exactas
- `SimilarFilesDetector` - Detección de archivos similares
- `AnalysisOrchestrator` - Orquestación de análisis completo
- Utilidades (`file_utils`, `date_utils`, `format_utils`)

## Recursos

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Pytest Markers](https://docs.pytest.org/en/stable/mark.html)
- [Pytest Coverage](https://pytest-cov.readthedocs.io/)
