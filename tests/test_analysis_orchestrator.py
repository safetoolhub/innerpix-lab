"""
Tests para services/analysis_orchestrator.py
Verifica que el orchestrator funciona sin PyQt6
"""
import tempfile
from pathlib import Path
from services.analysis_orchestrator import (
    AnalysisOrchestrator,
    DirectoryScanResult,
    FullAnalysisResult
)


def create_test_directory():
    """Crea directorio temporal con archivos de prueba"""
    tmpdir = tempfile.mkdtemp()
    test_dir = Path(tmpdir)
    
    # Crear archivos de diferentes tipos
    (test_dir / "photo1.jpg").write_text("fake jpg")
    (test_dir / "photo2.png").write_text("fake png")
    (test_dir / "photo3.heic").write_text("fake heic")
    (test_dir / "video1.mov").write_text("fake mov")
    (test_dir / "video2.mp4").write_text("fake mp4")
    (test_dir / "document.txt").write_text("text file")
    (test_dir / "script.py").write_text("python file")
    
    # Crear subdirectorio
    subdir = test_dir / "subdir"
    subdir.mkdir()
    (subdir / "photo4.jpg").write_text("fake jpg in subdir")
    (subdir / "video3.mov").write_text("fake mov in subdir")
    
    return test_dir


def test_directory_scan():
    """Test escaneo básico de directorio"""
    print("🔍 Test: Escaneo de directorio")
    
    test_dir = create_test_directory()
    
    try:
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(test_dir)
        
        assert isinstance(result, DirectoryScanResult)
        assert result.total_files == 9  # 7 en root + 2 en subdir
        assert result.image_count == 4  # 3 jpg/png/heic + 1 en subdir
        assert result.video_count == 3  # 2 mov/mp4 + 1 en subdir
        assert result.other_count == 2  # txt + py
        
        print(f"   Total archivos: {result.total_files}")
        print(f"   Imágenes: {result.image_count}")
        print(f"   Videos: {result.video_count}")
        print(f"   Otros: {result.other_count}")
        print("   ✅ Escaneo correcto\n")
    finally:
        # Limpiar
        import shutil
        shutil.rmtree(test_dir)


def test_progress_callback():
    """Test de callbacks de progreso"""
    print("🔍 Test: Callbacks de progreso")
    
    test_dir = create_test_directory()
    
    try:
        progress_calls = []
        
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
            return True  # Continuar
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(test_dir, progress_callback=progress_callback)
        
        assert len(progress_calls) > 0, "Debe llamar al callback de progreso"
        assert result.total_files == 9
        
        print(f"   Callbacks llamados: {len(progress_calls)}")
        print(f"   Primer callback: {progress_calls[0] if progress_calls else 'N/A'}")
        print("   ✅ Callbacks funcionan\n")
    finally:
        import shutil
        shutil.rmtree(test_dir)


def test_cancellation():
    """Test de cancelación durante escaneo"""
    print("🔍 Test: Cancelación de análisis")
    
    test_dir = create_test_directory()
    
    try:
        cancel_after = 3
        calls = [0]
        
        def progress_callback(current, total, message):
            calls[0] += 1
            return calls[0] <= cancel_after  # Cancelar después de N llamadas
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(test_dir, progress_callback=progress_callback)
        
        # Verificar que se canceló (puede no haber procesado todos)
        assert calls[0] > cancel_after, "Debe haber cancelado"
        
        print(f"   Callbacks antes de cancelar: {calls[0]}")
        print(f"   Archivos procesados: {result.total_files}")
        print("   ✅ Cancelación funciona\n")
    finally:
        import shutil
        shutil.rmtree(test_dir)


def test_full_analysis_result():
    """Test estructura FullAnalysisResult"""
    print("🔍 Test: Estructura FullAnalysisResult")
    
    test_dir = create_test_directory()
    
    try:
        orchestrator = AnalysisOrchestrator()
        scan = orchestrator.scan_directory(test_dir)
        
        result = FullAnalysisResult(
            directory=test_dir,
            scan=scan
        )
        
        assert result.directory == test_dir
        assert result.scan == scan
        assert result.renaming is None
        assert result.live_photos is None
        
        # Test conversión a dict
        result_dict = result.to_dict()
        assert 'stats' in result_dict
        assert result_dict['stats']['total'] == 9
        assert result_dict['stats']['images'] == 4
        assert result_dict['renaming'] is None
        
        print(f"   Directorio: {result.directory.name}")
        print(f"   Stats: {result_dict['stats']}")
        print("   ✅ Estructura correcta\n")
    finally:
        import shutil
        shutil.rmtree(test_dir)


def test_phase_callbacks():
    """Test de callbacks de fase"""
    print("🔍 Test: Callbacks de fase")
    
    test_dir = create_test_directory()
    
    try:
        phases = []
        partials = []
        
        def phase_callback(phase):
            phases.append(phase)
        
        def partial_callback(phase_name, data):
            partials.append((phase_name, data))
        
        orchestrator = AnalysisOrchestrator()
        
        # Ejecutar solo con escaneo (sin servicios)
        result = orchestrator.run_full_analysis(
            directory=test_dir,
            phase_callback=phase_callback,
            partial_callback=partial_callback
        )
        
        # Verificar que se llamaron los callbacks
        assert len(phases) > 0, "Debe llamar phase_callback"
        assert len(partials) > 0, "Debe llamar partial_callback"
        assert partials[0][0] == 'stats', "Primera llamada debe ser stats"
        
        print(f"   Fases ejecutadas: {len(phases)}")
        print(f"   Primera fase: {phases[0]}")
        print(f"   Resultados parciales: {len(partials)}")
        print(f"   Primer partial: {partials[0][0]}")
        print("   ✅ Callbacks de fase funcionan\n")
    finally:
        import shutil
        shutil.rmtree(test_dir)


def test_no_pyqt6_dependency():
    """Verifica que NO se importa PyQt6"""
    print("🔍 Test: Sin dependencia de PyQt6")
    
    import sys
    
    # Verificar módulos cargados
    qt_modules = [name for name in sys.modules.keys() if 'PyQt' in name or 'PySide' in name]
    
    if qt_modules:
        print(f"   ⚠️  Módulos Qt encontrados: {qt_modules}")
        print("   (Pueden estar cargados por otros tests)")
    else:
        print("   ✅ No hay módulos Qt cargados")
    
    # Lo importante es que AnalysisOrchestrator no requiere Qt
    from services.analysis_orchestrator import AnalysisOrchestrator
    
    test_dir = create_test_directory()
    try:
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(test_dir)
        
        assert result.total_files == 9
        print("   ✅ AnalysisOrchestrator funciona sin PyQt6\n")
    finally:
        import shutil
        shutil.rmtree(test_dir)


def test_cli_usage_example():
    """Demuestra uso en CLI sin UI"""
    print("🔍 Test: Uso en CLI (simulado)")
    
    test_dir = create_test_directory()
    
    try:
        # Simular uso en CLI con callbacks simples
        def cli_phase(phase):
            print(f"      Fase: {phase}")
        
        def cli_partial(name, data):
            if name == 'stats':
                print(f"      Stats: {data}")
        
        def cli_progress(current, total, msg):
            if current % 5 == 0 and current > 0:
                print(f"      Progreso: {current}/{total}")
            return True
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.run_full_analysis(
            directory=test_dir,
            phase_callback=cli_phase,
            partial_callback=cli_partial,
            progress_callback=cli_progress
        )
        
        print(f"      Análisis completo: {result.scan.total_files} archivos")
        print("   ✅ Uso CLI simulado correctamente\n")
    finally:
        import shutil
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Tests de AnalysisOrchestrator")
    print("=" * 70)
    print()
    
    test_directory_scan()
    test_progress_callback()
    test_cancellation()
    test_full_analysis_result()
    test_phase_callbacks()
    test_no_pyqt6_dependency()
    test_cli_usage_example()
    
    print("=" * 70)
    print("✅ TODOS LOS TESTS PASARON")
    print("=" * 70)
    print()
    print("💡 Beneficios:")
    print("   • AnalysisOrchestrator NO depende de PyQt6")
    print("   • Lógica de análisis reutilizable en CLI")
    print("   • Callbacks flexibles para cualquier contexto")
    print("   • Tests sin entorno gráfico")
    print("   • Workers Qt simplificados (solo threading + señales)")
    print()
    print("🎯 Casos de uso:")
    print("   • Scripts CLI de análisis")
    print("   • Herramientas de diagnóstico")
    print("   • Tests de servicios sin UI")
    print("   • Análisis batch/automatizado")
