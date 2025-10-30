# Tests Unitarios de Pixaro Lab

Este directorio contiene los tests unitarios del proyecto Pixaro Lab.

## Estructura

```
tests/
├── __init__.py
├── test_file_renamer.py    # Tests para el servicio de renombrado
└── README.md                # Este archivo
```

## Ejecutar los Tests

### Todos los tests
```bash
python run_tests.py
```

### Tests específicos de un módulo
```bash
python run_tests.py test_file_renamer
```

### Usando unittest directamente
```bash
python -m unittest discover tests
```

## Tests del FileRenamer

El archivo `test_file_renamer.py` contiene tests para verificar el comportamiento correcto del renombrado de archivos, especialmente la preservación de sufijos originales.

### Casos cubiertos

#### 1. Preservación de Sufijos No Estándar
**Test**: `test_preserve_non_standard_suffix_single_digit`
- **Entrada**: `IMG_3829_2.jpg`
- **Salida esperada**: `20230305_105312_PHOTO_2_001.JPG`
- **Verifica**: Sufijos de 1 dígito se preservan

**Test**: `test_preserve_non_standard_suffix_two_digits`
- **Entrada**: `IMG_3829_12.jpg`
- **Salida esperada**: `20230305_105312_PHOTO_12_001.JPG`
- **Verifica**: Sufijos de 2 dígitos se preservan

**Test**: `test_four_digit_suffix_preserved`
- **Entrada**: `IMG_3829_1234.jpg`
- **Salida esperada**: `20230305_105312_PHOTO_1234_001.JPG`
- **Verifica**: Sufijos de 4+ dígitos se preservan

#### 2. No Preservación de Sufijos Estándar
**Test**: `test_replace_standard_suffix_three_digits`
- **Entrada**: `IMG_photo_001.JPG`
- **Salida esperada**: `20230305_105312_PHOTO_001.JPG`
- **Verifica**: Sufijos de 3 dígitos generados por el programa NO se preservan

#### 3. Comportamiento Normal
**Test**: `test_no_suffix_normal_behavior`
- **Caso sin conflicto**: `IMG_3829.jpg` → `20230305_105312_PHOTO.JPG`
- **Caso con conflicto**: `IMG_photo.jpg` → `20230305_105312_PHOTO_001.JPG`
- **Verifica**: Funcionamiento normal sin sufijos originales

#### 4. Múltiples Conflictos
**Test**: `test_multiple_conflicts_mixed_suffixes`
- **Verifica**: Manejo correcto de múltiples archivos con diferentes tipos de sufijos

#### 5. Casos Extremos
**Test**: `test_no_numeric_suffix`
- **Entrada**: `IMG_test_file.jpg`
- **Verifica**: Guiones bajos sin números no se confunden con sufijos

**Test**: `test_suffix_at_start`
- **Entrada**: `2_IMG_3829.jpg`
- **Verifica**: Números al inicio no se confunden con sufijos

## Añadir Nuevos Tests

Para añadir nuevos tests:

1. Crea un nuevo archivo `test_<nombre>.py` en el directorio `tests/`
2. Importa `unittest` y crea una clase que herede de `unittest.TestCase`
3. Define métodos de test que empiecen con `test_`
4. Usa `setUp()` y `tearDown()` para preparar y limpiar el entorno de test

Ejemplo:

```python
import unittest
from pathlib import Path

class TestNuevaFuncionalidad(unittest.TestCase):
    
    def setUp(self):
        """Preparar entorno antes de cada test"""
        pass
    
    def tearDown(self):
        """Limpiar después de cada test"""
        pass
    
    def test_caso_basico(self):
        """Descripción del test"""
        # Arrange
        input_value = "test"
        
        # Act
        result = funcion_a_testear(input_value)
        
        # Assert
        self.assertEqual(result, "expected")
```

## Dependencias

Los tests utilizan solo bibliotecas estándar de Python:
- `unittest`: Framework de testing
- `tempfile`: Creación de directorios temporales
- `pathlib`: Manejo de rutas

No se requieren dependencias adicionales.

## Convenciones

- Usar `setUp()` y `tearDown()` para crear/limpiar directorios temporales
- Cada test debe ser independiente y no depender de otros
- Usar nombres descriptivos para los tests
- Documentar cada test con un docstring explicando qué verifica
- Los tests deben ejecutarse rápidamente (< 1 segundo cada uno)

## Resultados Esperados

Al ejecutar `python run_tests.py`, deberías ver:

```
test_four_digit_suffix_preserved ... ok
test_multiple_conflicts_mixed_suffixes ... ok
test_no_suffix_normal_behavior ... ok
test_preserve_non_standard_suffix_single_digit ... ok
test_preserve_non_standard_suffix_two_digits ... ok
test_replace_standard_suffix_three_digits ... ok
test_no_numeric_suffix ... ok
test_suffix_at_start ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.056s

OK
```

## Integración Continua

Estos tests pueden integrarse fácilmente en CI/CD:

```bash
# En tu script de CI
python run_tests.py || exit 1
```
