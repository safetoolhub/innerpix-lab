import pytest
from pathlib import Path
from services.zero_byte_service import ZeroByteService
from services.file_info_repository import FileInfoRepository
from services.result_types import ZeroByteAnalysisResult

@pytest.fixture
def zero_byte_service():
    return ZeroByteService()

@pytest.fixture
def test_directory(tmp_path):
    """
    Crear estructura de prueba con FileInfoRepository poblado:
    - empty.txt (0 bytes)
    - normal.txt (10 bytes)
    - subdir/
      - empty_sub.txt (0 bytes)
    """
    # Limpiar repositorio
    repo = FileInfoRepository.get_instance()
    repo.clear()
    
    # Crear archivos
    empty1 = tmp_path / "empty.txt"
    empty1.touch()
    
    normal = tmp_path / "normal.txt"
    normal.write_text("1234567890")
    
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    empty2 = subdir / "empty_sub.txt"
    empty2.touch()
    
    # Poblar repositorio
    repo.get_or_create(empty1)
    repo.get_or_create(normal)
    repo.get_or_create(empty2)
    
    return tmp_path

def test_analyze_finds_zero_byte_files(zero_byte_service, test_directory):
    """Test que el análisis detecta correctamente archivos de 0 bytes."""
    result = zero_byte_service.analyze()
    
    # Debug info
    all_files = [f for f in test_directory.rglob("*") if f.is_file()]
    print(f"DEBUG: All files found: {all_files}")
    print(f"DEBUG: Zero byte files found: {result.files}")
    
    # Usar atributos correctos de ZeroByteAnalysisResult
    assert result.items_count == 2  # 2 archivos de 0 bytes
    assert len(result.files) == 2
    
    found_names = [f.name for f in result.files]
    assert "empty.txt" in found_names
    assert "empty_sub.txt" in found_names
    assert "normal.txt" not in found_names

def test_execute_dry_run(zero_byte_service, test_directory):
    """Test que el modo simulación no elimina archivos."""
    # Primero analizar
    analysis_result = zero_byte_service.analyze()
    
    # Ejecutar en dry_run
    result = zero_byte_service.execute(analysis_result, dry_run=True)
    
    assert result.success
    assert result.items_processed == 2
    assert result.dry_run is True
    
    # Verificar que los archivos siguen existiendo
    assert (test_directory / "empty.txt").exists()
    assert (test_directory / "subdir" / "empty_sub.txt").exists()

def test_execute_deletion(zero_byte_service, test_directory):
    """Test que la eliminación funciona correctamente sin backup."""
    # Crear análisis parcial con solo un archivo
    analysis_result = ZeroByteAnalysisResult(
        files=[test_directory / "empty.txt"]
    )
    
    result = zero_byte_service.execute(analysis_result, create_backup=False, dry_run=False)
    
    assert result.success
    assert result.items_processed == 1
    
    # Verificar que el archivo fue eliminado
    assert not (test_directory / "empty.txt").exists()
    # Verificar que el otro archivo vacío sigue existiendo
    assert (test_directory / "subdir" / "empty_sub.txt").exists()

def test_execute_with_backup(zero_byte_service, test_directory):
    """Test que se crea backup antes de eliminar."""
    # Crear análisis parcial con solo un archivo
    analysis_result = ZeroByteAnalysisResult(
        files=[test_directory / "empty.txt"]
    )
    
    result = zero_byte_service.execute(analysis_result, create_backup=True, dry_run=False)
    
    assert result.success
    assert result.items_processed == 1
    assert result.backup_path is not None
    
    # Verificar que el archivo fue eliminado
    assert not (test_directory / "empty.txt").exists()
    
    # Verificar que existe el backup
    backup_dir = Path(result.backup_path)
    assert backup_dir.exists()
    # El backup debería contener el archivo (aunque vacío)
    # Nota: la estructura de backup depende de create_backup_for_file, 
    # asumimos que crea una estructura similar o pone el archivo ahí.
    # Simplemente verificamos que el directorio de backup no esté vacío
    assert any(backup_dir.rglob("*"))
