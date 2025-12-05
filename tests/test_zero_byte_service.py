import pytest
from pathlib import Path
from services.zero_byte_service import ZeroByteService

@pytest.fixture
def zero_byte_service():
    return ZeroByteService()

@pytest.fixture
def test_directory(tmp_path):
    # Crear estructura de prueba
    # - empty.txt (0 bytes)
    # - normal.txt (10 bytes)
    # - subdir/
    #   - empty_sub.txt (0 bytes)
    
    (tmp_path / "empty.txt").touch()
    
    normal = tmp_path / "normal.txt"
    normal.write_text("1234567890")
    
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "empty_sub.txt").touch()
    
    return tmp_path

def test_analyze_finds_zero_byte_files(zero_byte_service, test_directory):
    result = zero_byte_service.analyze(test_directory)
    
    # Debug info
    all_files = [f for f in test_directory.rglob("*") if f.is_file()]
    print(f"DEBUG: All files found: {all_files}")
    print(f"DEBUG: Zero byte files found: {result.files}")
    
    assert result.total_files == 3
    assert result.zero_byte_files_found == 2
    
    found_names = [f.name for f in result.files]
    assert "empty.txt" in found_names
    assert "empty_sub.txt" in found_names
    assert "normal.txt" not in found_names

def test_execute_dry_run(zero_byte_service, test_directory):
    files_to_delete = [
        test_directory / "empty.txt",
        test_directory / "subdir" / "empty_sub.txt"
    ]
    
    result = zero_byte_service.execute(files_to_delete, dry_run=True)
    
    assert result.success
    assert result.simulated_files_deleted == 2
    assert result.files_deleted == 0
    
    # Verificar que los archivos siguen existiendo
    assert (test_directory / "empty.txt").exists()
    assert (test_directory / "subdir" / "empty_sub.txt").exists()

def test_execute_deletion(zero_byte_service, test_directory):
    files_to_delete = [
        test_directory / "empty.txt"
    ]
    
    result = zero_byte_service.execute(files_to_delete, create_backup=False, dry_run=False)
    
    assert result.success
    assert result.files_deleted == 1
    
    # Verificar que el archivo fue eliminado
    assert not (test_directory / "empty.txt").exists()
    # Verificar que el otro archivo vacío sigue existiendo
    assert (test_directory / "subdir" / "empty_sub.txt").exists()

def test_execute_with_backup(zero_byte_service, test_directory):
    files_to_delete = [
        test_directory / "empty.txt"
    ]
    
    result = zero_byte_service.execute(files_to_delete, create_backup=True, dry_run=False)
    
    assert result.success
    assert result.files_deleted == 1
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
