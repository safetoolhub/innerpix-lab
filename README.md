# Innerpix Lab

Innerpix Lab es una aplicación de escritorio (PyQt6) para analizar y normalizar colecciones de fotos y vídeos. Está pensada especialmente para flujos provenientes de dispositivos iOS y ofrece herramientas para:

- Detectar y limpiar Live Photos
- Unificar estructuras de directorios
- Renombrado automático inteligente
- Eliminación/gestión de archivos HEIC/HEIF

El objetivo principal es permitir operaciones masivas sobre colecciones multimedia manteniendo un flujo seguro: primero análisis, luego previsualización y, finalmente, ejecución con confirmación del usuario.

## Estructura del repositorio

- `main.py` — Punto de entrada de la aplicación.
- `config.py` — Configuración global (nombre, versión, ajustes por defecto).
- `requirements.txt` — Dependencias Python.
- `ui/` — Componentes de interfaz gráfica (ventanas, diálogos, estilos y workers).
- `services/` — Lógica de negocio (renombrado, unificación de directorios, detección de Live Photos, limpieza de HEIC, etc.).
- `utils/` — Utilidades (logging, manejo de fechas, helpers).
- `docs/` — Documentación adicional y notas de instalación.

## Requisitos

- Python 3.9 o superior
- Plataformas soportadas: Linux, macOS, Windows

Se recomienda usar un entorno virtual para aislar dependencias.

## Instalación (Linux / macOS / WSL)

1. Clona el repositorio:

```bash
git clone <url-del-repositorio>
cd photokit-manager
```

2. Crea y activa un entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Instala dependencias:

```bash
pip install -r requirements.txt
```

Nota: Algunas dependencias como `pillow-heif` pueden requerir librerías del sistema (por ejemplo `libheif`). Si la instalación falla, instala las dependencias nativas con el gestor de paquetes de tu distribución (apt, dnf, brew) y vuelve a intentar.

## Ejecución

Con el entorno virtual activo, ejecuta:

```bash
python main.py
```

Esto abrirá la interfaz gráfica principal (`ui.main_window.MainWindow`).

## Uso básico

1. Selecciona un directorio raíz que contenga tus fotos y vídeos.
2. Ejecuta el análisis para inspeccionar contenido, metadatos y detectar Live Photos o duplicados.
3. Revisa los resultados y previsualiza las operaciones propuestas.
4. Ajusta parámetros (umbral de similitud, filtros por fecha/tipo, reglas de renombrado).
5. Confirma la ejecución. La aplicación intenta operar de forma segura (backups/confirmaciones).

## Desarrollo

Puntos de interés para desarrolladores:

- `ui/workers.py` — implementación de tareas en segundo plano para mantener la UI responsiva.
- `services/` — módulos que contienen la lógica para renombrado, unificación y detección de Live Photos.
- `utils/logger.py` — configuración y utilidades de logging.

Para contribuir:

1. Crea una rama nueva: `git checkout -b feat/mi-cambio`
2. Añade tests y documentación para cambios relevantes.
3. Mantén el estilo PEP 8 y añade type hints donde aplique.
4. Abre un Pull Request describiendo el cambio.

## Testing

Pixaro Lab incluye una suite completa de tests automatizados para asegurar la calidad del código.

### Ejecutar Tests

```bash
# Ejecutar todos los tests
./run_tests.sh

# O directamente con pytest
source .venv/bin/activate
pytest

# Ejecutar con reporte de cobertura
pytest --cov=.
```

### Estructura de Tests

- `tests/` — Suite de tests automatizados
- `pytest.ini` — Configuración de pytest
- `.coveragerc` — Configuración de cobertura de código
- `requirements-dev.txt` — Dependencias para desarrollo y testing

### Tests Implementados

- **test_window_size.py**: Tests para la lógica de configuración automática del tamaño de ventana basado en resolución del monitor

### Desarrollo de Tests

Para agregar nuevos tests:

1. Crear archivo `test_<modulo>.py` en `tests/`
2. Usar `pytest.mark.parametrize` para múltiples casos de prueba
3. Seguir patrón de nombrado: `test_<funcionalidad>_<escenario>`

### Calidad de Código

El proyecto incluye herramientas de calidad:

- **black**: Formateo automático de código
- **isort**: Ordenamiento de imports
- **flake8**: Linting de código
- **mypy**: Verificación de tipos (opcional)

Instalar herramientas de desarrollo:
```bash
pip install -r requirements-dev.txt
```

Configurar pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

## Problemas comunes y soluciones

- ImportError de PyQt5: asegúrate de que el entorno virtual está activado y que la instalación de PyQt5 fue exitosa.
- Problemas con HEIC/HEIF: instala `libheif` y vuelve a instalar `pillow-heif`.
- Errores al renombrar/borar: verifica permisos en los directorios objetivo.
- Ejecución en entornos headless: PyQt5 requiere servidor X para mostrar UI; usa Xvfb si necesitas ejecutar pruebas en CI sin display.

Revisa los logs en `utils/logger.py` si algo falla para obtener trazas detalladas.

## Licencia

Consulta el archivo `LICENSE` en la raíz del repositorio para detalles sobre la licencia.

## Contacto

Si detectas fallos o tienes mejoras, abre un issue o PR en el repositorio. Para consultas urgentes, contacta con los mantenedores referenciados en la cabecera del proyecto.

---

README actualizado: instrucciones de instalación, ejecución, desarrollo y troubleshooting adaptadas al contenido real del repositorio.
