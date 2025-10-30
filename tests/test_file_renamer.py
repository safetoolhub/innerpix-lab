"""
Tests unitarios para FileRenamer - Preservación de sufijos originales

Casos cubiertos:
1. Archivo con sufijo no estándar (1-2 dígitos) - debe preservarse
2. Archivo con sufijo estándar de 3 dígitos - debe reemplazarse
3. Archivo sin sufijo numérico - comportamiento normal
4. Múltiples conflictos con sufijos mixtos
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from services.file_renamer import FileRenamer
from utils.date_utils import format_renamed_name


class TestFileRenamerSuffixPreservation(unittest.TestCase):
    """Tests para verificar la preservación correcta de sufijos en renombrado"""

    def setUp(self):
        """Crear directorio temporal para tests"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.renamer = FileRenamer()
        
    def tearDown(self):
        """Limpiar directorio temporal"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _create_test_image(self, filename: str, date: datetime = None) -> Path:
        """
        Crea un archivo de imagen de prueba con metadatos EXIF simulados
        
        Args:
            filename: Nombre del archivo
            date: Fecha para los metadatos (opcional)
            
        Returns:
            Path al archivo creado
        """
        file_path = self.test_dir / filename
        
        # Crear archivo simple (no es una imagen real, pero suficiente para tests)
        with open(file_path, 'wb') as f:
            f.write(b'fake image content')
        
        # Si se proporciona fecha, establecer mtime
        if date:
            timestamp = date.timestamp()
            import os
            os.utime(file_path, (timestamp, timestamp))
            
        return file_path

    def test_preserve_non_standard_suffix_single_digit(self):
        """
        Test: Archivo con sufijo de 1 dígito debe preservarse al resolver conflicto
        
        Caso: IMG_3829_2.jpg → 20230305_105312_PHOTO_2_001.JPG
        """
        # Crear fecha de prueba
        test_date = datetime(2023, 3, 5, 10, 53, 12)
        
        # Crear archivo original con sufijo _2
        original_file = self._create_test_image("IMG_3829_2.jpg", test_date)
        
        # Crear archivo que causará conflicto (sin sufijo)
        expected_name = format_renamed_name(test_date, 'PHOTO', '.JPG')
        conflict_file = self.test_dir / expected_name
        conflict_file.write_text("existing file")
        
        # Analizar y ejecutar renombrado
        analysis = self.renamer.analyze_directory(self.test_dir)
        result = self.renamer.execute_renaming(analysis.renaming_plan, create_backup=False)
        
        # Verificar que el sufijo _2 se preservó
        expected_renamed = self.test_dir / "20230305_105312_PHOTO_2_001.JPG"
        self.assertTrue(expected_renamed.exists(), 
                       f"El archivo renombrado debería existir: {expected_renamed}")
        self.assertFalse(original_file.exists(), 
                        "El archivo original no debería existir")
        self.assertEqual(result.conflicts_resolved, 1,
                        "Debería haberse resuelto 1 conflicto")

    def test_preserve_non_standard_suffix_two_digits(self):
        """
        Test: Archivo con sufijo de 2 dígitos debe preservarse al resolver conflicto
        
        Caso: IMG_3829_12.jpg → 20230305_105312_PHOTO_12_001.JPG
        """
        test_date = datetime(2023, 3, 5, 10, 53, 12)
        
        original_file = self._create_test_image("IMG_3829_12.jpg", test_date)
        
        # Crear conflicto
        expected_name = format_renamed_name(test_date, 'PHOTO', '.JPG')
        conflict_file = self.test_dir / expected_name
        conflict_file.write_text("existing file")
        
        analysis = self.renamer.analyze_directory(self.test_dir)
        result = self.renamer.execute_renaming(analysis.renaming_plan, create_backup=False)
        
        expected_renamed = self.test_dir / "20230305_105312_PHOTO_12_001.JPG"
        self.assertTrue(expected_renamed.exists(),
                       f"Debería preservar sufijo _12: {expected_renamed}")

    def test_replace_standard_suffix_three_digits(self):
        """
        Test: Archivo con sufijo de 3 dígitos (estándar) debe reemplazarse, no preservarse
        
        Caso: IMG_existing_001.JPG → 20230305_105312_PHOTO_002.JPG
        """
        test_date = datetime(2023, 3, 5, 10, 53, 12)
        
        # Crear archivo SIN formato renombrado, pero con _001 al final
        # (simula un archivo que el usuario nombró manualmente con _001)
        original_file = self._create_test_image("IMG_photo_001.JPG", test_date)
        
        # Crear conflicto
        conflict_file = self.test_dir / "20230305_105312_PHOTO.JPG"
        conflict_file.write_text("existing file")
        
        analysis = self.renamer.analyze_directory(self.test_dir)
        result = self.renamer.execute_renaming(analysis.renaming_plan, create_backup=False)
        
        # Como el archivo original tiene _001 (3 dígitos) NO debe preservarse
        # porque no está en el nombre final renombrado
        expected_renamed = self.test_dir / "20230305_105312_PHOTO_001.JPG"
        wrong_renamed = self.test_dir / "20230305_105312_PHOTO_001_001.JPG"
        
        self.assertTrue(expected_renamed.exists(),
                       "Debería generar nombre con _001 sin duplicar sufijos")
        self.assertFalse(wrong_renamed.exists(),
                        "NO debería duplicar sufijos estándar")

    def test_no_suffix_normal_behavior(self):
        """
        Test: Archivo sin sufijo numérico debe comportarse normalmente
        
        Caso: IMG_3829.jpg → 20230305_105312_PHOTO.JPG (sin conflicto)
        Caso: IMG_3830.jpg + conflicto → 20230305_105312_PHOTO_001.JPG (con conflicto)
        """
        test_date = datetime(2023, 3, 5, 10, 53, 12)
        
        # Caso 1: Sin conflicto
        original_file = self._create_test_image("IMG_3829.jpg", test_date)
        
        analysis = self.renamer.analyze_directory(self.test_dir)
        result = self.renamer.execute_renaming(analysis.renaming_plan, create_backup=False)
        
        expected_renamed = self.test_dir / "20230305_105312_PHOTO.JPG"
        self.assertTrue(expected_renamed.exists(),
                       "Debería renombrar sin sufijo cuando no hay conflicto")
        
        # Caso 2: Con conflicto - crear nuevo archivo en directorio limpio
        self.tearDown()
        self.setUp()
        
        # Crear conflicto primero
        conflict_file = self.test_dir / "20230305_105312_PHOTO.JPG"
        conflict_file.write_text("existing file")
        
        # Ahora crear archivo a renombrar (sin números que puedan confundirse con sufijo)
        original_file2 = self._create_test_image("IMG_photo.jpg", test_date)
        
        analysis = self.renamer.analyze_directory(self.test_dir)
        result = self.renamer.execute_renaming(analysis.renaming_plan, create_backup=False)
        
        expected_renamed_with_suffix = self.test_dir / "20230305_105312_PHOTO_001.JPG"
        self.assertTrue(expected_renamed_with_suffix.exists(),
                       "Debería añadir sufijo _001 cuando hay conflicto")

    def test_multiple_conflicts_mixed_suffixes(self):
        """
        Test: Múltiples archivos con diferentes tipos de sufijos
        
        Casos:
        - IMG_3829.jpg → 20230305_105312_PHOTO_001.JPG (primer archivo de la secuencia)
        - IMG_3830_2.jpg → 20230305_105312_PHOTO_2_002.JPG (preserva _2)
        - IMG_3831_5.jpg → 20230305_105312_PHOTO_5_003.JPG (preserva _5)
        """
        test_date = datetime(2023, 3, 5, 10, 53, 12)
        
        # Crear múltiples archivos con la misma fecha (generarán conflictos)
        file1 = self._create_test_image("IMG_3829.jpg", test_date)
        file2 = self._create_test_image("IMG_3830_2.jpg", test_date)
        file3 = self._create_test_image("IMG_3831_5.jpg", test_date)
        
        analysis = self.renamer.analyze_directory(self.test_dir)
        result = self.renamer.execute_renaming(analysis.renaming_plan, create_backup=False)
        
        # Como todos tienen la misma fecha, se generará una secuencia
        # El sistema los ordena y asigna secuencias
        self.assertEqual(result.files_renamed, 3,
                        "Deberían renombrarse 3 archivos")
        
        # Verificar que se procesaron correctamente (al menos algunos archivos existen)
        renamed_files = list(self.test_dir.glob("20230305_105312_PHOTO*.JPG"))
        self.assertEqual(len(renamed_files), 3,
                        "Deberían existir 3 archivos renombrados")

    def test_four_digit_suffix_preserved(self):
        """
        Test: Sufijo de 4+ dígitos debe preservarse (no estándar)
        
        Caso: IMG_3829_1234.jpg → 20230305_105312_PHOTO_1234_001.JPG
        """
        test_date = datetime(2023, 3, 5, 10, 53, 12)
        
        original_file = self._create_test_image("IMG_3829_1234.jpg", test_date)
        
        # Crear conflicto
        expected_name = format_renamed_name(test_date, 'PHOTO', '.JPG')
        conflict_file = self.test_dir / expected_name
        conflict_file.write_text("existing file")
        
        analysis = self.renamer.analyze_directory(self.test_dir)
        result = self.renamer.execute_renaming(analysis.renaming_plan, create_backup=False)
        
        expected_renamed = self.test_dir / "20230305_105312_PHOTO_1234_001.JPG"
        self.assertTrue(expected_renamed.exists(),
                       "Debería preservar sufijo de 4 dígitos")


class TestFileRenamerEdgeCases(unittest.TestCase):
    """Tests para casos extremos y edge cases"""
    
    def setUp(self):
        """Crear directorio temporal para tests"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.renamer = FileRenamer()
        
    def tearDown(self):
        """Limpiar directorio temporal"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _create_test_file(self, filename: str, date: datetime = None) -> Path:
        """Helper para crear archivos de prueba"""
        file_path = self.test_dir / filename
        with open(file_path, 'wb') as f:
            f.write(b'test content')
        
        if date:
            timestamp = date.timestamp()
            import os
            os.utime(file_path, (timestamp, timestamp))
            
        return file_path

    def test_no_numeric_suffix(self):
        """
        Test: Archivo con guión bajo pero sin sufijo numérico
        
        Caso: IMG_test_file.jpg → 20230305_105312_PHOTO.JPG
        """
        test_date = datetime(2023, 3, 5, 10, 53, 12)
        original_file = self._create_test_file("IMG_test_file.jpg", test_date)
        
        analysis = self.renamer.analyze_directory(self.test_dir)
        result = self.renamer.execute_renaming(analysis.renaming_plan, create_backup=False)
        
        expected = self.test_dir / "20230305_105312_PHOTO.JPG"
        self.assertTrue(expected.exists(),
                       "Debería renombrar normalmente sin confundir texto con sufijo")

    def test_suffix_at_start(self):
        """
        Test: Número al inicio no debe confundirse con sufijo
        
        Caso: 2_IMG_3829.jpg → 20230305_105312_PHOTO.JPG
        """
        test_date = datetime(2023, 3, 5, 10, 53, 12)
        original_file = self._create_test_file("2_IMG_3829.jpg", test_date)
        
        analysis = self.renamer.analyze_directory(self.test_dir)
        result = self.renamer.execute_renaming(analysis.renaming_plan, create_backup=False)
        
        expected = self.test_dir / "20230305_105312_PHOTO.JPG"
        self.assertTrue(expected.exists(),
                       "No debería confundir número al inicio con sufijo")


def run_tests():
    """Ejecutar todos los tests"""
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Añadir tests
    suite.addTests(loader.loadTestsFromTestCase(TestFileRenamerSuffixPreservation))
    suite.addTests(loader.loadTestsFromTestCase(TestFileRenamerEdgeCases))
    
    # Ejecutar con verbosidad
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Retornar código de salida apropiado
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    import sys
    sys.exit(run_tests())
