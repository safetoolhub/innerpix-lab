# Suite de Tests - Pixaro Lab

Esta carpeta contiene la suite de tests automatizados para Pixaro Lab.

## Estructura

```
tests/
├── __init__.py                 # Paquete de tests
├── test_window_size.py         # Tests para lógica de tamaño de ventana
└── ...                         # Más tests en el futuro
```

## Ejecutar Tests

### Opción 1: Script dedicado
```bash
./run_tests.sh
```

### Opción 2: pytest directamente
```bash
# Activar entorno virtual
source .venv/bin/activate

# Ejecutar todos los tests
pytest

# Ejecutar con cobertura
pytest --cov=.

# Ejecutar tests específicos
pytest tests/test_window_size.py

# Ejecutar un test específico
pytest tests/test_window_size.py::TestWindowSizeLogic::test_window_size_logic
```

## Configuración

- **pytest.ini**: Configuración de pytest
- **.coveragerc**: Configuración de coverage
- **requirements-dev.txt**: Dependencias para desarrollo y testing

## Tests Implementados

### test_window_size.py

Tests para la lógica de configuración automática del tamaño de ventana:

- **TestWindowSizeLogic**:
  - `test_window_size_logic`: Tests parametrizados que verifican la lógica de maximización vs FullHD
  - `test_window_centering_calculation`: Verifica el cálculo correcto del centrado
  - `test_screen_resolution_detection`: Tests de mocking para detección de resolución
  - `test_resolution_categories`: Clasificación de resoluciones en categorías

- **TestWindowSizeIntegration**:
  - Tests de integración (pendientes de implementar completamente)

## Cobertura

Los tests están configurados para:
- Cobertura mínima del 80%
- Reportes HTML en `htmlcov/`
- Exclusión de archivos de venv y cache

## Desarrollo

### Agregar nuevos tests

1. Crear archivo `test_<modulo>.py` en `tests/`
2. Usar `pytest.mark.parametrize` para tests con múltiples casos
3. Seguir el patrón de nombrado: `test_<funcionalidad>_<escenario>`

### Instalar dependencias de desarrollo

```bash
pip install -r requirements-dev.txt
```

### Configurar pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

## CI/CD

Los tests están preparados para integración continua con:
- Ejecución automática en push/PR
- Cobertura de código
- Linting con flake8
- Formateo con black/isort