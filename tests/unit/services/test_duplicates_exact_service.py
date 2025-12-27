"""
Tests profesionales para DuplicatesExactService
Verifica detección de duplicados exactos mediante SHA256, estrategias de eliminación,
y operaciones consecutivas.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from services.duplicates_exact_service import DuplicatesExactService
from services.result_types import DuplicateAnalysisResult, DuplicateGroup, DuplicateExecutionResult
from services.file_metadata_repository_cache import FileInfoRepositoryCache, PopulationStrategy
from services.file_metadata import FileMetadata
from config import Config


class TestDuplicatesExactServiceBasics:
    """Tests básicos de inicialización y herencia"""
    
    def test_service_initialization(self):
        """El servicio debe inicializarse correctamente"""
        service = DuplicatesExactService()
        assert service is not None
        assert hasattr(service, 'analyze')
        assert hasattr(service, 'execute')
    
    def test_service_inherits_from_base(self):
        """Debe heredar de DuplicatesBaseService"""
        from services.duplicates_base_service import DuplicatesBaseService
        service = DuplicatesExactService()
        assert isinstance(service, DuplicatesBaseService)


class TestDuplicatesExactServiceAnalyze:
    """Tests del método analyze"""
    
    def setup_method(self):
        """Limpiar el repositorio antes de cada test"""
        repo = FileInfoRepositoryCache.get_instance()
        repo.clear()
    
    def test_analyze_empty_repository_returns_no_groups(self):
        """Analizar repositorio vacío debe retornar resultado sin grupos"""
        service = DuplicatesExactService()
        result = service.analyze()
        
        assert isinstance(result, DuplicateAnalysisResult)
        assert len(result.groups) == 0
        assert result.total_duplicates == 0
        assert result.total_groups == 0
    
    def test_analyze_no_duplicates_returns_empty_result(self, tmp_path):
        """Archivos únicos no deben generar grupos"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear 3 archivos diferentes
        for i in range(3):
            test_file = tmp_path / f"unique{i}.jpg"
            test_file.write_bytes(f"unique content {i}".encode())
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=len(f"unique content {i}"),
                fs_ctime=1234567890.0,
                fs_mtime=1234567890.0,
                fs_atime=1234567890.0,
                sha256=f"hash{i}"
            )
            repo.add_file(test_file, metadata)
        
        result = service.analyze()
        
        assert len(result.groups) == 0
        assert result.total_duplicates == 0
    
    def test_analyze_finds_exact_duplicates(self, tmp_path):
        """Debe detectar archivos con mismo hash"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear 3 archivos con el mismo hash (duplicados exactos)
        duplicate_hash = "abc123hash"
        files = []
        for i in range(3):
            test_file = tmp_path / f"duplicate{i}.jpg"
            test_file.write_bytes(b"same content")
            files.append(test_file)
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=12,  # len("same content")
                fs_ctime=1234567890.0,
                fs_mtime=1234567890.0,
                fs_atime=1234567890.0,
                sha256=duplicate_hash
            )
            repo.add_file(test_file, metadata)
        
        result = service.analyze()
        
        assert len(result.groups) == 1
        assert result.total_duplicates == 2  # 3 archivos = 2 duplicados
        assert result.total_groups == 1
        assert result.groups[0].hash_value == duplicate_hash
        assert len(result.groups[0].files) == 3
    
    def test_analyze_multiple_duplicate_groups(self, tmp_path):
        """Debe detectar múltiples grupos de duplicados"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Grupo 1: 3 archivos con hash "aaa"
        for i in range(3):
            test_file = tmp_path / f"group1_{i}.jpg"
            test_file.write_bytes(b"content A")
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=9,
                fs_ctime=1234567890.0,
                fs_mtime=1234567890.0,
                fs_atime=1234567890.0,
                sha256="aaa"
            )
            repo.add_file(test_file, metadata)
        
        # Grupo 2: 2 archivos con hash "bbb"
        for i in range(2):
            test_file = tmp_path / f"group2_{i}.jpg"
            test_file.write_bytes(b"content B")
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=9,
                fs_ctime=1234567890.0,
                fs_mtime=1234567890.0,
                fs_atime=1234567890.0,
                sha256="bbb"
            )
            repo.add_file(test_file, metadata)
        
        result = service.analyze()
        
        assert len(result.groups) == 2
        assert result.total_duplicates == 3  # (3-1) + (2-1)
        assert result.total_groups == 2
        
        # Verificar que hay un grupo de 3 y otro de 2
        group_sizes = sorted([len(g.files) for g in result.groups])
        assert group_sizes == [2, 3]
    
    def test_analyze_calculates_space_wasted_correctly(self, tmp_path):
        """Debe calcular correctamente el espacio desperdiciado"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        file_size = 1000
        num_duplicates = 4
        
        # Crear 4 archivos idénticos de 1000 bytes cada uno
        for i in range(num_duplicates):
            test_file = tmp_path / f"dup{i}.jpg"
            test_file.write_bytes(b"x" * file_size)
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=file_size,
                fs_ctime=1234567890.0,
                fs_mtime=1234567890.0,
                fs_atime=1234567890.0,
                sha256="samehash"
            )
            repo.add_file(test_file, metadata)
        
        result = service.analyze()
        
        # Espacio desperdiciado = (num_duplicates - 1) * file_size
        expected_waste = (num_duplicates - 1) * file_size
        assert result.space_wasted == expected_waste
    
    def test_analyze_with_progress_callback(self, tmp_path):
        """Debe llamar al callback de progreso durante el análisis"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear algunos duplicados
        for i in range(5):
            test_file = tmp_path / f"file{i}.jpg"
            test_file.write_bytes(b"content")
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=7,
                fs_ctime=1234567890.0,
                fs_mtime=1234567890.0,
                fs_atime=1234567890.0,
                sha256=None  # No pre-calcular hash para que se llame el callback
            )
            repo.add_file(test_file, metadata)
        
        progress_calls = []
        
        def progress_callback(current, total, message=""):
            progress_calls.append((current, total, message))
            return True  # Continuar
        
        result = service.analyze(progress_callback=progress_callback)
        
        # Debe haber llamado al callback durante el cálculo de hashes
        assert len(progress_calls) > 0


class TestDuplicatesExactServiceExecute:
    """Tests del método execute con diferentes estrategias"""
    
    def setup_method(self):
        """Limpiar el repositorio antes de cada test"""
        repo = FileInfoRepositoryCache.get_instance()
        repo.clear()
    
    def test_execute_dry_run_does_not_delete_files(self, tmp_path):
        """Dry run no debe eliminar archivos"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear duplicados
        files = []
        for i in range(3):
            test_file = tmp_path / f"dup{i}.jpg"
            test_file.write_bytes(b"same")
            files.append(test_file)
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=4,
                fs_ctime=1234567890.0 + i,
                fs_mtime=1234567890.0 + i,
                fs_atime=1234567890.0,
                sha256="hash"
            )
            repo.add_file(test_file, metadata)
        
        # Analizar
        analysis = service.analyze()
        
        # Ejecutar en modo dry run
        
        exec_result = service.execute(
            analysis_result=analysis,
            keep_strategy='oldest',
            create_backup=False,
            dry_run=True
        )
        
        # Verificar que todos los archivos siguen existiendo
        for f in files:
            assert f.exists()
        
        assert exec_result.dry_run is True
        assert exec_result.items_processed >= 0
    
    def test_execute_keep_oldest_strategy(self, tmp_path):
        """Estrategia KEEP_OLDEST debe mantener el archivo más antiguo"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear 3 duplicados con diferentes tiempos de modificación
        oldest = tmp_path / "oldest.jpg"
        oldest.write_bytes(b"content")
        metadata_oldest = FileMetadata(
            path=oldest,
            fs_size=7,
            fs_ctime=1000.0,
            fs_mtime=1000.0,
            fs_atime=1000.0,
            sha256="hash"
        )
        repo.add_file(oldest, metadata_oldest)
        
        middle = tmp_path / "middle.jpg"
        middle.write_bytes(b"content")
        metadata_middle = FileMetadata(
            path=middle,
            fs_size=7,
            fs_ctime=2000.0,
            fs_mtime=2000.0,
            fs_atime=2000.0,
            sha256="hash"
        )
        repo.add_file(middle, metadata_middle)
        
        newest = tmp_path / "newest.jpg"
        newest.write_bytes(b"content")
        metadata_newest = FileMetadata(
            path=newest,
            fs_size=7,
            fs_ctime=3000.0,
            fs_mtime=3000.0,
            fs_atime=3000.0,
            sha256="hash"
        )
        repo.add_file(newest, metadata_newest)
        
        # Analizar y ejecutar
        analysis = service.analyze()
        
        exec_result = service.execute(
            analysis_result=analysis,
            keep_strategy='oldest',
            create_backup=False,
            dry_run=False
        )
        
        # Verificar que solo el más antiguo permanece
        assert oldest.exists()
        assert not middle.exists()
        assert not newest.exists()
    
    def test_execute_keep_newest_strategy(self, tmp_path):
        """Estrategia KEEP_NEWEST debe mantener el archivo más reciente"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear duplicados con diferentes tiempos
        oldest = tmp_path / "oldest.jpg"
        oldest.write_bytes(b"data")
        metadata_oldest = FileMetadata(
            path=oldest,
            fs_size=4,
            fs_ctime=1000.0,
            fs_mtime=1000.0,
            fs_atime=1000.0,
            sha256="xyz"
        )
        repo.add_file(oldest, metadata_oldest)
        
        newest = tmp_path / "newest.jpg"
        newest.write_bytes(b"data")
        metadata_newest = FileMetadata(
            path=newest,
            fs_size=4,
            fs_ctime=3000.0,
            fs_mtime=3000.0,
            fs_atime=3000.0,
            sha256="xyz"
        )
        repo.add_file(newest, metadata_newest)
        
        analysis = service.analyze()
        
        exec_result = service.execute(
            analysis_result=analysis,
            keep_strategy='newest',
            create_backup=False,
            dry_run=False
        )
        
        # Verificar que solo el más nuevo permanece
        assert not oldest.exists()
        assert newest.exists()
    
    def test_execute_updates_repository_cache(self, tmp_path):
        """La ejecución debe actualizar el repositorio eliminando archivos borrados"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear duplicados
        file1 = tmp_path / "file1.jpg"
        file1.write_bytes(b"same")
        metadata1 = FileMetadata(
            path=file1,
            fs_size=4,
            fs_ctime=1000.0,
            fs_mtime=1000.0,
            fs_atime=1000.0,
            sha256="abc"
        )
        repo.add_file(file1, metadata1)
        
        file2 = tmp_path / "file2.jpg"
        file2.write_bytes(b"same")
        metadata2 = FileMetadata(
            path=file2,
            fs_size=4,
            fs_ctime=2000.0,
            fs_mtime=2000.0,
            fs_atime=2000.0,
            sha256="abc"
        )
        repo.add_file(file2, metadata2)
        
        assert len(repo) == 2
        
        # Analizar y ejecutar
        analysis = service.analyze()
        
        service.execute(
            analysis_result=analysis,
            keep_strategy='oldest',
            create_backup=False,
            dry_run=False
        )
        
        # El repositorio debe haber sido actualizado (file2 eliminado)
        assert len(repo) == 1
        assert repo.get_file_metadata(file1) is not None
        assert repo.get_file_metadata(file2) is None


class TestDuplicatesExactServiceEdgeCases:
    """Tests de casos extremos y situaciones especiales"""
    
    def setup_method(self):
        """Limpiar el repositorio antes de cada test"""
        repo = FileInfoRepositoryCache.get_instance()
        repo.clear()
    
    def test_analyze_with_files_without_hash(self, tmp_path):
        """Archivos sin hash en el repositorio deben ser manejados correctamente"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear archivo sin hash (None)
        test_file = tmp_path / "nohash.jpg"
        test_file.write_bytes(b"content")
        
        metadata = FileMetadata(
            path=test_file,
            fs_size=7,
            fs_ctime=1234567890.0,
            fs_mtime=1234567890.0,
            fs_atime=1234567890.0,
            sha256=None  # Sin hash
        )
        repo.add_file(test_file, metadata)
        
        # No debe crashear
        result = service.analyze()
        assert isinstance(result, DuplicateAnalysisResult)
    
    def test_analyze_single_file(self, tmp_path):
        """Un solo archivo no puede tener duplicados"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        test_file = tmp_path / "single.jpg"
        test_file.write_bytes(b"unique")
        
        metadata = FileMetadata(
            path=test_file,
            fs_size=6,
            fs_ctime=1234567890.0,
            fs_mtime=1234567890.0,
            fs_atime=1234567890.0,
            sha256="uniquehash"
        )
        repo.add_file(test_file, metadata)
        
        result = service.analyze()
        
        assert len(result.groups) == 0
        assert result.total_duplicates == 0
    
    def test_execute_with_empty_analysis(self):
        """Ejecutar con análisis vacío no debe causar errores"""
        service = DuplicatesExactService()
        
        empty_analysis = DuplicateAnalysisResult(groups=[])
        
        
        exec_result = service.execute(
            analysis_result=empty_analysis,
            keep_strategy='oldest',
            create_backup=False,
            dry_run=False
        )
        
        assert exec_result.items_processed == 0
        assert exec_result.success is True


class TestDuplicatesExactServiceIntegration:
    """Tests de integración con operaciones consecutivas"""
    
    def setup_method(self):
        """Limpiar el repositorio antes de cada test"""
        repo = FileInfoRepositoryCache.get_instance()
        repo.clear()
    
    def test_consecutive_analyze_operations(self, tmp_path):
        """Múltiples análisis consecutivos deben dar resultados consistentes"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear duplicados
        for i in range(3):
            test_file = tmp_path / f"dup{i}.jpg"
            test_file.write_bytes(b"same")
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=4,
                fs_ctime=1234567890.0,
                fs_mtime=1234567890.0,
                fs_atime=1234567890.0,
                sha256="hash"
            )
            repo.add_file(test_file, metadata)
        
        # Ejecutar análisis 3 veces
        result1 = service.analyze()
        result2 = service.analyze()
        result3 = service.analyze()
        
        # Todos deben dar el mismo resultado
        assert len(result1.groups) == len(result2.groups) == len(result3.groups) == 1
        assert result1.total_duplicates == result2.total_duplicates == result3.total_duplicates == 2
    
    def test_analyze_execute_analyze_sequence(self, tmp_path):
        """Secuencia: analizar → ejecutar → analizar debe reflejar cambios"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear 4 duplicados
        files = []
        for i in range(4):
            test_file = tmp_path / f"file{i}.jpg"
            test_file.write_bytes(b"content")
            files.append(test_file)
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=7,
                fs_ctime=1000.0 + i,
                fs_mtime=1000.0 + i,
                fs_atime=1000.0,
                sha256="abc123"
            )
            repo.add_file(test_file, metadata)
        
        # 1. Primer análisis: debe encontrar 4 archivos (3 duplicados)
        analysis1 = service.analyze()
        assert len(analysis1.groups) == 1
        assert len(analysis1.groups[0].files) == 4
        assert analysis1.total_duplicates == 3
        
        # 2. Ejecutar: eliminar duplicados manteniendo el más antiguo
        
        service.execute(
            analysis_result=analysis1,
            keep_strategy='oldest',
            create_backup=False,
            dry_run=False
        )
        
        # 3. Segundo análisis: no debe encontrar duplicados
        analysis2 = service.analyze()
        assert len(analysis2.groups) == 0
        assert analysis2.total_duplicates == 0
        
        # Verificar que solo queda 1 archivo
        existing_files = [f for f in files if f.exists()]
        assert len(existing_files) == 1
        assert existing_files[0] == files[0]  # El más antiguo
    
    def test_multiple_execute_operations_in_sequence(self, tmp_path):
        """Múltiples ejecuciones consecutivas deben ser seguras"""
        repo = FileInfoRepositoryCache.get_instance()
        service = DuplicatesExactService()
        
        # Crear dos grupos de duplicados
        # Grupo 1
        for i in range(3):
            test_file = tmp_path / f"group1_{i}.jpg"
            test_file.write_bytes(b"data1")
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=5,
                fs_ctime=1000.0 + i,
                fs_mtime=1000.0 + i,
                fs_atime=1000.0,
                sha256="hash1"
            )
            repo.add_file(test_file, metadata)
        
        # Grupo 2
        for i in range(2):
            test_file = tmp_path / f"group2_{i}.jpg"
            test_file.write_bytes(b"data2")
            
            metadata = FileMetadata(
                path=test_file,
                fs_size=5,
                fs_ctime=2000.0 + i,
                fs_mtime=2000.0 + i,
                fs_atime=2000.0,
                sha256="hash2"
            )
            repo.add_file(test_file, metadata)
        
        # Primera ejecución
        
        analysis1 = service.analyze()
        assert len(analysis1.groups) == 2
        
        exec_result1 = service.execute(
            analysis_result=analysis1,
            keep_strategy='oldest',
            create_backup=False,
            dry_run=False
        )
        
        # Segunda ejecución (no debería encontrar nada)
        analysis2 = service.analyze()
        assert len(analysis2.groups) == 0
        
        exec_result2 = service.execute(
            analysis_result=analysis2,
            keep_strategy='oldest',
            create_backup=False,
            dry_run=False
        )
        
        # Verificar que quedan solo 2 archivos (uno de cada grupo)
        remaining_files = list(tmp_path.glob("*.jpg"))
        assert len(remaining_files) == 2
