"""
Configuración de pytest y fixtures compartidas para todos los tests.

Este archivo contiene fixtures reutilizables para crear archivos de prueba,
directorios temporales, y datos de muestra para los tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from PIL import Image
import io


# ==================== FIXTURES DE DIRECTORIOS ====================

@pytest.fixture
def temp_dir():
    """
    Crea un directorio temporal que se limpia automáticamente después del test.
    
    Yields:
        Path: Path del directorio temporal
    
    Example:
        def test_something(temp_dir):
            file = temp_dir / "test.txt"
            file.write_text("content")
    """
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def nested_temp_dir(temp_dir):
    """
    Crea una estructura de directorios anidados para tests.
    
    Estructura:
    temp_dir/
    ├── subdir1/
    ├── subdir2/
    │   └── nested/
    └── subdir3/
    
    Returns:
        Tuple[Path, Dict[str, Path]]: (directorio raíz, dict de subdirectorios)
    """
    subdirs = {
        'subdir1': temp_dir / 'subdir1',
        'subdir2': temp_dir / 'subdir2',
        'nested': temp_dir / 'subdir2' / 'nested',
        'subdir3': temp_dir / 'subdir3',
    }
    
    for subdir in subdirs.values():
        subdir.mkdir(parents=True, exist_ok=True)
    
    return temp_dir, subdirs


# ==================== FIXTURES DE ARCHIVOS ====================

@pytest.fixture
def create_test_image():
    """
    Factory fixture para crear imágenes de prueba.
    
    Returns:
        Callable: Función que crea una imagen con parámetros específicos
    
    Example:
        def test_image(create_test_image):
            img_path = create_test_image(
                path=Path('/tmp/test.jpg'),
                size=(100, 100),
                color='red'
            )
    """
    created_files = []
    
    def _create_image(
        path: Path,
        size: Tuple[int, int] = (100, 100),
        color: str = 'blue',
        format: str = 'JPEG'
    ) -> Path:
        """
        Crea una imagen de prueba.
        
        Args:
            path: Ruta donde guardar la imagen
            size: Tamaño (width, height)
            color: Color de la imagen
            format: Formato (JPEG, PNG, etc.)
        
        Returns:
            Path de la imagen creada
        """
        img = Image.new('RGB', size, color=color)
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, format=format)
        created_files.append(path)
        return path
    
    yield _create_image
    
    # Cleanup
    for file_path in created_files:
        if file_path.exists():
            file_path.unlink()


@pytest.fixture
def create_test_video():
    """
    Factory fixture para crear videos de prueba (archivos .MOV vacíos).
    
    Returns:
        Callable: Función que crea un video de prueba
    
    Example:
        def test_video(create_test_video):
            video_path = create_test_video(
                path=Path('/tmp/test.MOV'),
                size_bytes=1024
            )
    """
    created_files = []
    
    def _create_video(
        path: Path,
        size_bytes: int = 1024
    ) -> Path:
        """
        Crea un archivo de video de prueba.
        
        Args:
            path: Ruta donde guardar el video
            size_bytes: Tamaño del archivo en bytes
        
        Returns:
            Path del video creado
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        # Crear archivo binario con contenido aleatorio
        with open(path, 'wb') as f:
            f.write(b'\x00' * size_bytes)
        created_files.append(path)
        return path
    
    yield _create_video
    
    # Cleanup
    for file_path in created_files:
        if file_path.exists():
            file_path.unlink()


@pytest.fixture
def create_renamed_file():
    """
    Factory fixture para crear archivos con nombres en formato renombrado.
    
    Formato: IMG_YYYYMMDD_HHMMSS.ext o VID_YYYYMMDD_HHMMSS.ext
    
    Returns:
        Callable: Función que crea archivo con nombre renombrado
    """
    created_files = []
    
    def _create_renamed(
        directory: Path,
        date: datetime,
        file_type: str = 'IMG',
        extension: str = '.jpg',
        sequence: int = None,
        size: Tuple[int, int] = (100, 100)
    ) -> Path:
        """
        Crea un archivo con nombre en formato renombrado.
        
        Args:
            directory: Directorio donde crear el archivo
            date: Fecha para el nombre del archivo
            file_type: Tipo (IMG o VID)
            extension: Extensión del archivo
            sequence: Número de secuencia opcional
            size: Tamaño de la imagen
        
        Returns:
            Path del archivo creado
        """
        date_str = date.strftime('%Y%m%d_%H%M%S')
        
        if sequence:
            filename = f"{file_type}_{date_str}_{sequence:03d}{extension}"
        else:
            filename = f"{file_type}_{date_str}{extension}"
        
        file_path = directory / filename
        
        # Crear archivo (imagen simple o archivo vacío)
        if extension.lower() in ['.jpg', '.jpeg', '.png', '.heic']:
            img = Image.new('RGB', size, color='blue')
            file_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(file_path, format='JPEG')
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(b'\x00' * 1024)
        
        created_files.append(file_path)
        return file_path
    
    yield _create_renamed
    
    # Cleanup
    for file_path in created_files:
        if file_path.exists():
            file_path.unlink()


# ==================== FIXTURES DE LIVE PHOTOS ====================

@pytest.fixture
def create_live_photo_pair(create_test_image, create_test_video):
    """
    Factory fixture para crear pares de Live Photos (imagen + video).
    
    Returns:
        Callable: Función que crea un par de Live Photo
    
    Example:
        def test_live_photo(create_live_photo_pair):
            img_path, vid_path = create_live_photo_pair(
                directory=temp_dir,
                base_name='IMG_0001'
            )
    """
    def _create_pair(
        directory: Path,
        base_name: str,
        img_extension: str = '.HEIC',
        vid_extension: str = '.MOV',
        img_size: Tuple[int, int] = (100, 100),
        vid_size: int = 2048
    ) -> Tuple[Path, Path]:
        """
        Crea un par de Live Photo.
        
        Args:
            directory: Directorio donde crear los archivos
            base_name: Nombre base (sin extensión)
            img_extension: Extensión de la imagen
            vid_extension: Extensión del video
            img_size: Tamaño de la imagen
            vid_size: Tamaño del video en bytes
        
        Returns:
            Tuple con (path_imagen, path_video)
        """
        img_path = create_test_image(
            path=directory / f"{base_name}{img_extension}",
            size=img_size
        )
        
        vid_path = create_test_video(
            path=directory / f"{base_name}{vid_extension}",
            size_bytes=vid_size
        )
        
        # Ajustar tiempos de modificación para que sean similares (dentro del límite de 5 segundos)
        # Usando el mismo timestamp para asegurar que son válidos como Live Photo
        import os
        timestamp = datetime.now().timestamp()
        os.utime(img_path, (timestamp, timestamp))
        os.utime(vid_path, (timestamp, timestamp))
        
        return img_path, vid_path
    
    return _create_pair


@pytest.fixture
def sample_live_photos_directory(temp_dir, create_live_photo_pair):
    """
    Crea un directorio con varios Live Photos de muestra.
    
    Estructura:
    - 3 Live Photos válidos
    - 1 imagen huérfana (sin video)
    - 1 video huérfano (sin imagen)
    
    Returns:
        Tuple[Path, Dict]: (directorio, metadata de archivos)
    """
    metadata = {
        'valid_pairs': [],
        'orphan_images': [],
        'orphan_videos': []
    }
    
    # Crear Live Photos válidos
    for i in range(1, 4):
        img, vid = create_live_photo_pair(
            directory=temp_dir,
            base_name=f'IMG_000{i}'
        )
        metadata['valid_pairs'].append({
            'image': img,
            'video': vid,
            'base_name': f'IMG_000{i}'
        })
    
    # Crear imagen huérfana
    orphan_img = temp_dir / 'IMG_ORPHAN.HEIC'
    img = Image.new('RGB', (100, 100), color='red')
    img.save(orphan_img, format='JPEG')
    metadata['orphan_images'].append(orphan_img)
    
    # Crear video huérfano
    orphan_vid = temp_dir / 'VID_ORPHAN.MOV'
    orphan_vid.write_bytes(b'\x00' * 1024)
    metadata['orphan_videos'].append(orphan_vid)
    
    return temp_dir, metadata


# ==================== FIXTURES DE DATOS ====================

@pytest.fixture
def sample_dates():
    """
    Proporciona fechas de muestra para tests.
    
    Returns:
        Dict con diferentes fechas para testing
    """
    now = datetime.now()
    return {
        'now': now,
        'yesterday': now - timedelta(days=1),
        'last_week': now - timedelta(weeks=1),
        'last_month': now - timedelta(days=30),
        'last_year': now - timedelta(days=365),
    }


# ==================== FIXTURES DE CONFIGURACIÓN ====================

@pytest.fixture
def mock_config(monkeypatch):
    """
    Mock de la configuración de la aplicación.
    
    Permite modificar valores de Config sin afectar el sistema real.
    
    Example:
        def test_with_config(mock_config):
            mock_config['MAX_WORKERS'] = 2
    """
    config = {
        'MAX_WORKERS': 4,
        'SUPPORTED_IMAGE_EXTENSIONS': ['.jpg', '.jpeg', '.heic', '.png'],
        'SUPPORTED_VIDEO_EXTENSIONS': ['.mov', '.mp4'],
    }
    
    return config


# ==================== MARKERS DE PYTEST ====================

def pytest_configure(config):
    """
    Configuración adicional de pytest.
    
    Registra markers personalizados y configura el entorno de testing.
    """
    # Registrar markers personalizados programáticamente
    config.addinivalue_line(
        "markers", "unit: Tests unitarios de lógica de negocio (services, utils)"
    )
    config.addinivalue_line(
        "markers", "integration: Tests de integración entre componentes"
    )
    config.addinivalue_line(
        "markers", "ui: Tests de componentes UI (requiere PyQt6)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests que tardan más de 1 segundo"
    )
    config.addinivalue_line(
        "markers", "live_photos: Tests específicos de funcionalidad Live Photos"
    )
    config.addinivalue_line(
        "markers", "duplicates: Tests de detección de duplicados"
    )
    config.addinivalue_line(
        "markers", "renaming: Tests de renombrado de archivos"
    )
    config.addinivalue_line(
        "markers", "organization: Tests de organización de archivos"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modifica items recolectados antes de ejecutar tests.
    
    Agrega markers automáticamente según la ubicación del test.
    """
    for item in items:
        # Auto-marcar tests según su ubicación
        if 'services' in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        if 'ui' in str(item.fspath):
            item.add_marker(pytest.mark.ui)
        
        # Auto-marcar tests lentos (puedes personalizarlo)
        if 'slow' in item.nodeid:
            item.add_marker(pytest.mark.slow)


# ==================== FIXTURES DE REPOSITORIO ====================

@pytest.fixture(autouse=True)
def reset_file_info_repository():
    """
    Resetea el singleton FileInfoRepository entre tests automáticamente.
    
    Esto garantiza que cada test comience con un repositorio limpio
    y evita efectos secundarios entre tests.
    """
    from services.file_info_repository import FileInfoRepository
    # Resetear antes del test
    FileInfoRepository.reset_instance()
    yield
    # Resetear después del test
    FileInfoRepository.reset_instance()
