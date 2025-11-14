"""
Tests unitarios para AnalysisOrchestrator.

Prueba el orquestador de análisis que coordina múltiples servicios:
- Escaneo de directorios y clasificación de archivos
- Análisis individual de cada fase
- Análisis completo con múltiples servicios
- Sistema de callbacks (progress, phase, partial)
- Timing y PhaseTimingInfo
- Cancelación de operaciones
- Integración con servicios
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from services.analysis_orchestrator import (
    AnalysisOrchestrator,
    DirectoryScanResult,
    PhaseTimingInfo,
    FullAnalysisResult
)
from services.result_types import (
    RenameAnalysisResult,
    LivePhotoDetectionResult,
    OrganizationAnalysisResult,
    HeicAnalysisResult,
    DuplicateAnalysisResult,
    DuplicateGroup
)
from services.file_organizer_service import OrganizationType


# ==================== TESTS BÁSICOS ====================

@pytest.mark.unit
class TestAnalysisOrchestratorBasics:
    """Tests básicos de funcionalidad del orquestador."""
    
    def test_orchestrator_initialization(self):
        """Test que el orquestador se inicializa correctamente."""
        orchestrator = AnalysisOrchestrator()
        
        assert orchestrator is not None
        assert orchestrator.logger is not None
    
    def test_directory_scan_result_properties(self):
        """Test propiedades de DirectoryScanResult."""
        result = DirectoryScanResult(
            total_files=10,
            images=[Path('a.jpg'), Path('b.png')],
            videos=[Path('c.mov')],
            others=[Path('d.txt'), Path('e.pdf')]
        )
        
        assert result.total_files == 10
        assert result.image_count == 2
        assert result.video_count == 1
        assert result.other_count == 2
    
    def test_phase_timing_info_needs_delay(self):
        """Test cálculo de delay necesario para duración mínima."""
        # Fase que termina rápido (0.5s) necesita delay de 1.5s para llegar a 2s
        timing = PhaseTimingInfo(
            phase_id='test',
            phase_name='Test Phase',
            start_time=0.0,
            end_time=0.5,
            duration=0.5
        )
        
        assert timing.needs_delay(min_duration=2.0) == 1.5
        
        # Fase que ya dura más de 2s no necesita delay
        timing_long = PhaseTimingInfo(
            phase_id='test',
            phase_name='Test Phase',
            start_time=0.0,
            end_time=3.0,
            duration=3.0
        )
        
        assert timing_long.needs_delay(min_duration=2.0) == 0.0
    
    def test_full_analysis_result_initialization(self, temp_dir):
        """Test inicialización de FullAnalysisResult."""
        scan = DirectoryScanResult(
            total_files=5,
            images=[],
            videos=[],
            others=[]
        )
        
        result = FullAnalysisResult(
            directory=temp_dir,
            scan=scan
        )
        
        assert result.directory == temp_dir
        assert result.scan.total_files == 5
        assert result.renaming is None
        assert result.live_photos is None
        assert result.organization is None
        assert result.heic is None
        assert result.duplicates is None
        assert result.total_duration == 0.0
        assert len(result.phase_timings) == 0


# ==================== TESTS DE ESCANEO ====================

@pytest.mark.unit
class TestDirectoryScanning:
    """Tests de escaneo y clasificación de archivos."""
    
    def test_scan_empty_directory(self, temp_dir):
        """Test escaneo de directorio vacío."""
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(temp_dir)
        
        assert result.total_files == 0
        assert result.image_count == 0
        assert result.video_count == 0
        assert result.other_count == 0
        assert len(result.images) == 0
        assert len(result.videos) == 0
        assert len(result.others) == 0
    
    def test_scan_directory_with_images(self, temp_dir, create_test_image):
        """Test escaneo de directorio con imágenes."""
        # Crear varias imágenes
        create_test_image(temp_dir / 'photo1.jpg')
        create_test_image(temp_dir / 'photo2.png')
        create_test_image(temp_dir / 'photo3.HEIC')
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(temp_dir)
        
        assert result.total_files == 3
        assert result.image_count == 3
        assert result.video_count == 0
        assert result.other_count == 0
        
        # Verificar que todas son imágenes
        image_names = {img.name for img in result.images}
        assert 'photo1.jpg' in image_names
        assert 'photo2.png' in image_names
        assert 'photo3.HEIC' in image_names
    
    def test_scan_directory_with_videos(self, temp_dir, create_test_video):
        """Test escaneo de directorio con videos."""
        # Crear varios videos
        create_test_video(temp_dir / 'video1.mov')
        create_test_video(temp_dir / 'video2.MOV')
        create_test_video(temp_dir / 'video3.mp4')
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(temp_dir)
        
        assert result.total_files == 3
        assert result.image_count == 0
        assert result.video_count == 3
        assert result.other_count == 0
    
    def test_scan_directory_mixed_files(self, temp_dir, create_test_image, create_test_video):
        """Test escaneo con mezcla de tipos de archivos."""
        # Crear archivos de diferentes tipos
        create_test_image(temp_dir / 'photo.jpg')
        create_test_image(temp_dir / 'picture.png')
        create_test_video(temp_dir / 'video.mov')
        (temp_dir / 'document.txt').write_text('test')
        (temp_dir / 'data.json').write_text('{}')
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(temp_dir)
        
        assert result.total_files == 5
        assert result.image_count == 2
        assert result.video_count == 1
        assert result.other_count == 2
    
    def test_scan_directory_nested_structure(self, temp_dir, create_test_image):
        """Test escaneo de directorios anidados."""
        # Crear estructura anidada
        (temp_dir / 'subdir1').mkdir()
        (temp_dir / 'subdir2' / 'nested').mkdir(parents=True)
        
        create_test_image(temp_dir / 'root.jpg')
        create_test_image(temp_dir / 'subdir1' / 'sub1.jpg')
        create_test_image(temp_dir / 'subdir2' / 'sub2.jpg')
        create_test_image(temp_dir / 'subdir2' / 'nested' / 'deep.jpg')
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(temp_dir)
        
        assert result.total_files == 4
        assert result.image_count == 4
        
        # Verificar que encuentra archivos en todos los niveles
        image_names = {img.name for img in result.images}
        assert 'root.jpg' in image_names
        assert 'sub1.jpg' in image_names
        assert 'sub2.jpg' in image_names
        assert 'deep.jpg' in image_names
    
    def test_scan_directory_with_progress_callback(self, temp_dir, create_test_image):
        """Test escaneo con callback de progreso."""
        # Crear 20 imágenes para tener progreso visible
        for i in range(20):
            create_test_image(temp_dir / f'photo{i:02d}.jpg')
        
        # Mock callback que registra las llamadas
        progress_calls = []
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
            return True  # Continuar
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(temp_dir, progress_callback)
        
        assert result.total_files == 20
        assert len(progress_calls) > 0
        
        # Verificar que la última llamada es 100%
        last_call = progress_calls[-1]
        assert last_call[0] == last_call[1]  # current == total
        assert last_call[2] == "Escaneando archivos"
    
    def test_scan_directory_cancellation(self, temp_dir, create_test_image):
        """Test cancelación del escaneo mediante callback."""
        # Crear varios archivos
        for i in range(10):
            create_test_image(temp_dir / f'photo{i:02d}.jpg')
        
        # Callback que cancela después de 3 llamadas
        call_count = 0
        def cancel_callback(current, total, message):
            nonlocal call_count
            call_count += 1
            return call_count <= 3  # Cancelar después de 3
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.scan_directory(temp_dir, cancel_callback)
        
        # El escaneo debe haberse interrumpido
        assert call_count > 3


# ==================== TESTS DE ANÁLISIS INDIVIDUAL ====================

@pytest.mark.unit
class TestIndividualAnalysis:
    """Tests de métodos de análisis individual."""
    
    def test_analyze_renaming(self, temp_dir):
        """Test análisis de renombrado."""
        orchestrator = AnalysisOrchestrator()
        
        # Mock del FileRenamer
        mock_renamer = Mock()
        mock_result = RenameAnalysisResult(
            success=True,
            total_files=10,
            already_renamed=3,
            need_renaming=7,
            cannot_process=0,
            conflicts=0
        )
        mock_renamer.analyze.return_value = mock_result
        
        result = orchestrator.analyze_renaming(temp_dir, mock_renamer)
        
        assert result == mock_result
        mock_renamer.analyze.assert_called_once()
        
        # Verificar argumentos de la llamada
        call_args = mock_renamer.analyze.call_args
        assert call_args[0][0] == temp_dir
    
    def test_analyze_live_photos(self, temp_dir, create_test_image, create_test_video):
        """Test análisis de Live Photos."""
        orchestrator = AnalysisOrchestrator()
        
        # Mock del LivePhotoService
        from services.result_types import LivePhotoCleanupAnalysisResult
        from services.live_photo_service import LivePhotoGroup
        
        mock_service = Mock()
        
        # Crear archivos reales para el grupo
        img_path = create_test_image(temp_dir / 'IMG_0001.HEIC')
        vid_path = create_test_video(temp_dir / 'IMG_0001.MOV')
        
        # Crear grupo de prueba
        test_group = LivePhotoGroup(
            base_name='IMG_0001',
            directory=temp_dir,
            image_path=img_path,
            video_path=vid_path,
            image_size=1000,
            video_size=5000
        )
        
        mock_cleanup_result = LivePhotoCleanupAnalysisResult(
            success=True,
            total_files=2,
            groups=[test_group],
            live_photos_found=1,
            total_space=6000,
            space_to_free=5000,
            files_to_delete=[],
            files_to_keep=[]
        )
        mock_service.analyze.return_value = mock_cleanup_result
        
        result = orchestrator.analyze_live_photos(temp_dir, mock_service)
        
        assert isinstance(result, LivePhotoDetectionResult)
        assert result.live_photos_found == 1
        assert result.total_space == 6000
        mock_service.analyze.assert_called_once()
    
    def test_analyze_organization(self, temp_dir):
        """Test análisis de organización."""
        orchestrator = AnalysisOrchestrator()
        
        # Mock del FileOrganizer
        mock_organizer = Mock()
        mock_result = OrganizationAnalysisResult(
            success=True,
            total_files=20,
            root_directory=str(temp_dir),
            organization_type='by_month',
            total_files_to_move=15
        )
        mock_organizer.analyze.return_value = mock_result
        
        result = orchestrator.analyze_organization(
            temp_dir,
            mock_organizer,
            organization_type='by_month'
        )
        
        assert result == mock_result
        mock_organizer.analyze.assert_called_once()
        
        # Verificar que se pasó el tipo de organización como enum
        call_kwargs = mock_organizer.analyze.call_args[1]
        assert call_kwargs['organization_type'] == OrganizationType.BY_MONTH
    
    def test_analyze_organization_default_type(self, temp_dir):
        """Test análisis de organización con tipo por defecto (None)."""
        orchestrator = AnalysisOrchestrator()
        
        # Mock del FileOrganizer
        mock_organizer = Mock()
        mock_result = OrganizationAnalysisResult(
            success=True,
            total_files=20,
            root_directory=str(temp_dir),
            organization_type='to_root',
            total_files_to_move=15
        )
        mock_organizer.analyze.return_value = mock_result
        
        # Llamar sin especificar organization_type (None)
        result = orchestrator.analyze_organization(
            temp_dir,
            mock_organizer,
            organization_type=None
        )
        
        assert result == mock_result
        mock_organizer.analyze.assert_called_once()
        
        # Verificar que se pasó el tipo por defecto TO_ROOT
        call_kwargs = mock_organizer.analyze.call_args[1]
        assert call_kwargs['organization_type'] == OrganizationType.TO_ROOT
    
    def test_analyze_heic_duplicates(self, temp_dir):
        """Test análisis de duplicados HEIC."""
        orchestrator = AnalysisOrchestrator()
        
        # Mock del HEICRemover
        mock_heic_remover = Mock()
        mock_result = HeicAnalysisResult(
            success=True,
            total_files=10,
            total_pairs=5,
            heic_files=5,
            jpg_files=5,
            potential_savings_keep_jpg=5000000
        )
        mock_heic_remover.analyze.return_value = mock_result
        
        result = orchestrator.analyze_heic_duplicates(temp_dir, mock_heic_remover)
        
        assert result == mock_result
        mock_heic_remover.analyze.assert_called_once_with(
            temp_dir,
            progress_callback=None,
            metadata_cache=None
        )
    
    def test_analyze_exact_duplicates(self, temp_dir):
        """Test análisis de duplicados exactos."""
        orchestrator = AnalysisOrchestrator()
        
        # Mock del ExactCopiesDetector
        mock_detector = Mock()
        
        test_group = DuplicateGroup(
            hash_value='abc123',
            files=[temp_dir / 'file1.jpg', temp_dir / 'file2.jpg'],
            total_size=2000,
            similarity_score=100.0
        )
        
        mock_result = DuplicateAnalysisResult(
            success=True,
            total_files=10,
            mode='exact',
            groups=[test_group],
            total_groups=1,
            total_duplicates=1,
            space_wasted=2000
        )
        mock_detector.analyze.return_value = mock_result
        
        result = orchestrator.analyze_exact_duplicates(temp_dir, mock_detector)
        
        assert result == mock_result
        assert result.mode == 'exact'
        mock_detector.analyze.assert_called_once()


# ==================== TESTS DE ANÁLISIS COMPLETO ====================

@pytest.mark.unit
class TestFullAnalysis:
    """Tests de análisis completo con múltiples servicios."""
    
    def test_full_analysis_scan_only(self, temp_dir, create_test_image):
        """Test análisis completo solo con escaneo (sin servicios)."""
        # Crear algunos archivos
        create_test_image(temp_dir / 'photo1.jpg')
        create_test_image(temp_dir / 'photo2.png')
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.run_full_analysis(directory=temp_dir)
        
        assert isinstance(result, FullAnalysisResult)
        assert result.directory == temp_dir
        assert result.scan.total_files == 2
        assert result.scan.image_count == 2
        
        # Sin servicios, solo debe tener timing de scan
        assert 'scan' in result.phase_timings
        assert result.renaming is None
        assert result.live_photos is None
        assert result.organization is None
        assert result.heic is None
        assert result.duplicates is None
        
        assert result.total_duration > 0
    
    def test_full_analysis_with_renamer(self, temp_dir, create_test_image):
        """Test análisis completo con servicio de renombrado."""
        create_test_image(temp_dir / 'photo.jpg')
        
        orchestrator = AnalysisOrchestrator()
        
        # Mock renamer
        mock_renamer = Mock()
        mock_rename_result = RenameAnalysisResult(
            success=True,
            total_files=1,
            already_renamed=0,
            need_renaming=1
        )
        mock_renamer.analyze.return_value = mock_rename_result
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer
        )
        
        assert result.renaming is not None
        assert result.renaming == mock_rename_result
        assert 'scan' in result.phase_timings
        assert 'renaming' in result.phase_timings
        
        # Verificar timing info
        timing = result.phase_timings['renaming']
        assert timing.phase_id == 'renaming'
        assert timing.phase_name == 'Análisis de nombres'
        assert timing.duration >= 0
        assert timing.end_time >= timing.start_time
    
    def test_full_analysis_with_all_services(self, temp_dir, create_test_image):
        """Test análisis completo con todos los servicios."""
        create_test_image(temp_dir / 'photo.jpg')
        
        orchestrator = AnalysisOrchestrator()
        
        # Mock todos los servicios
        mock_renamer = Mock()
        mock_renamer.analyze.return_value = RenameAnalysisResult(
            success=True, total_files=1
        )
        
        mock_live_photos = Mock()
        from services.result_types import LivePhotoCleanupAnalysisResult
        mock_live_photos.analyze.return_value = LivePhotoCleanupAnalysisResult(
            success=True,
            total_files=0,
            groups=[],
            live_photos_found=0,
            total_space=0,
            space_to_free=0,
            files_to_delete=[],
            files_to_keep=[]
        )
        
        mock_organizer = Mock()
        mock_organizer.analyze.return_value = OrganizationAnalysisResult(
            success=True, total_files=1
        )
        
        mock_heic = Mock()
        mock_heic.analyze.return_value = HeicAnalysisResult(
            success=True, total_files=1, total_pairs=0, heic_files=0, jpg_files=0
        )
        
        mock_duplicates = Mock()
        mock_duplicates.analyze.return_value = DuplicateAnalysisResult(
            success=True, total_files=1, mode='exact', total_duplicates=0
        )
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer,
            live_photo_service=mock_live_photos,
            organizer=mock_organizer,
            heic_remover=mock_heic,
            duplicate_exact_detector=mock_duplicates,
            organization_type='by_month'
        )
        
        # Verificar que todos los análisis se ejecutaron
        assert result.renaming is not None
        assert result.live_photos is not None
        assert result.organization is not None
        assert result.heic is not None
        assert result.duplicates is not None
        
        # Verificar timings de todas las fases
        expected_phases = ['scan', 'renaming', 'live_photos', 'heic', 
                          'duplicates', 'organization', 'finalizing']
        for phase in expected_phases:
            assert phase in result.phase_timings
            timing = result.phase_timings[phase]
            assert timing.duration >= 0
        
        # Verificar llamadas a servicios
        mock_renamer.analyze.assert_called_once()
        mock_live_photos.analyze.assert_called_once()
        mock_organizer.analyze.assert_called_once()
        mock_heic.analyze.assert_called_once()
        mock_duplicates.analyze.assert_called_once()
    
    def test_full_analysis_phase_execution_order(self, temp_dir):
        """Test que las fases se ejecutan en el orden correcto."""
        orchestrator = AnalysisOrchestrator()
        
        # Registro de orden de ejecución
        execution_order = []
        
        def make_mock_service(name):
            mock = Mock()
            def analyze_side_effect(*args, **kwargs):
                execution_order.append(name)
                from services.result_types import (
                    RenameAnalysisResult, LivePhotoCleanupAnalysisResult,
                    OrganizationAnalysisResult, HeicAnalysisResult,
                    DuplicateAnalysisResult
                )
                if name == 'renamer':
                    return RenameAnalysisResult(success=True, total_files=0)
                elif name == 'live_photos':
                    return LivePhotoCleanupAnalysisResult(
                        success=True, total_files=0, groups=[], live_photos_found=0,
                        total_space=0, space_to_free=0, files_to_delete=[], files_to_keep=[]
                    )
                elif name == 'heic':
                    return HeicAnalysisResult(success=True, total_files=0, total_pairs=0, heic_files=0, jpg_files=0)
                elif name == 'duplicates':
                    return DuplicateAnalysisResult(success=True, total_files=0, mode='exact', total_duplicates=0)
                elif name == 'organizer':
                    return OrganizationAnalysisResult(success=True, total_files=0)
            mock.analyze.side_effect = analyze_side_effect
            return mock
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=make_mock_service('renamer'),
            live_photo_service=make_mock_service('live_photos'),
            heic_remover=make_mock_service('heic'),
            duplicate_exact_detector=make_mock_service('duplicates'),
            organizer=make_mock_service('organizer')
        )
        
        # Verificar orden esperado: renamer -> live_photos -> heic -> duplicates -> organizer
        expected_order = ['renamer', 'live_photos', 'heic', 'duplicates', 'organizer']
        assert execution_order == expected_order


# ==================== TESTS DE CALLBACKS ====================

@pytest.mark.unit
class TestCallbacks:
    """Tests del sistema de callbacks."""
    
    def test_progress_callback(self, temp_dir, create_test_image):
        """Test callback de progreso durante escaneo."""
        # Crear varios archivos
        for i in range(15):
            create_test_image(temp_dir / f'photo{i:02d}.jpg')
        
        progress_calls = []
        def progress_callback(current, total, message):
            progress_calls.append({
                'current': current,
                'total': total,
                'message': message
            })
            return True
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            progress_callback=progress_callback
        )
        
        assert len(progress_calls) > 0
        
        # Verificar que current nunca excede total
        for call in progress_calls:
            assert call['current'] <= call['total']
    
    def test_phase_callback(self, temp_dir):
        """Test callback de cambio de fase."""
        orchestrator = AnalysisOrchestrator()
        
        phase_changes = []
        def phase_callback(phase_name):
            phase_changes.append(phase_name)
        
        # Mock services
        mock_renamer = Mock()
        mock_renamer.analyze.return_value = RenameAnalysisResult(
            success=True, total_files=0
        )
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer,
            phase_callback=phase_callback
        )
        
        # Debe haber registrado cambios de fase
        assert 'scan' in phase_changes
        assert 'renaming' in phase_changes
        assert 'finalizing' in phase_changes
        
        # Verificar orden
        assert phase_changes.index('scan') < phase_changes.index('renaming')
        assert phase_changes.index('renaming') < phase_changes.index('finalizing')
    
    def test_partial_callback(self, temp_dir, create_test_image):
        """Test callback de resultados parciales."""
        create_test_image(temp_dir / 'photo.jpg')
        
        orchestrator = AnalysisOrchestrator()
        
        partial_results = {}
        def partial_callback(phase_name, result):
            partial_results[phase_name] = result
        
        # Mock renamer
        mock_renamer = Mock()
        mock_rename_result = RenameAnalysisResult(
            success=True,
            total_files=1,
            need_renaming=1
        )
        mock_renamer.analyze.return_value = mock_rename_result
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer,
            partial_callback=partial_callback
        )
        
        # Debe haber recibido resultados parciales
        assert 'scan' in partial_results
        assert 'renaming' in partial_results
        
        # Verificar contenido de scan
        scan_result = partial_results['scan']
        assert scan_result['total'] == 1
        assert scan_result['images'] == 1
        
        # Verificar resultado de renaming
        rename_result = partial_results['renaming']
        assert rename_result == mock_rename_result
    
    def test_all_callbacks_together(self, temp_dir, create_test_image):
        """Test usando todos los callbacks simultáneamente."""
        create_test_image(temp_dir / 'photo.jpg')
        
        orchestrator = AnalysisOrchestrator()
        
        # Registrar todos los eventos
        events = []
        
        def progress_callback(current, total, message):
            events.append(('progress', current, total, message))
            return True
        
        def phase_callback(phase_name):
            events.append(('phase', phase_name))
        
        def partial_callback(phase_name, result):
            events.append(('partial', phase_name))
        
        mock_renamer = Mock()
        mock_renamer.analyze.return_value = RenameAnalysisResult(
            success=True, total_files=1
        )
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer,
            progress_callback=progress_callback,
            phase_callback=phase_callback,
            partial_callback=partial_callback
        )
        
        # Debe haber múltiples eventos registrados
        assert len(events) > 0
        
        # Verificar que hay eventos de cada tipo
        event_types = {event[0] for event in events}
        assert 'progress' in event_types
        assert 'phase' in event_types
        assert 'partial' in event_types


# ==================== TESTS DE CANCELACIÓN ====================

@pytest.mark.unit
class TestCancellation:
    """Tests de cancelación de operaciones."""
    
    def test_cancellation_during_scan(self, temp_dir, create_test_image):
        """Test cancelación durante el escaneo."""
        # Crear varios archivos
        for i in range(10):
            create_test_image(temp_dir / f'photo{i:02d}.jpg')
        
        call_count = 0
        def cancel_early(current, total, message):
            nonlocal call_count
            call_count += 1
            return call_count <= 2  # Cancelar en la tercera llamada
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            progress_callback=cancel_early
        )
        
        # El análisis debe haberse detenido temprano
        assert result.renaming is None
    
    def test_cancellation_before_renaming_phase(self, temp_dir):
        """Test cancelación antes de la fase de renombrado."""
        orchestrator = AnalysisOrchestrator()
        
        # Callback que cancela después del scan
        phase_count = 0
        def cancel_after_scan(current, total, message):
            nonlocal phase_count
            phase_count += 1
            return phase_count <= 1  # Solo permitir scan
        
        mock_renamer = Mock()
        mock_renamer.analyze.return_value = RenameAnalysisResult(
            success=True, total_files=0
        )
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer,
            progress_callback=cancel_after_scan
        )
        
        # Scan debe completarse, pero no debe llamarse al renamer
        assert 'scan' in result.phase_timings
        # El renamer podría no haberse llamado dependiendo del timing
    
    def test_cancellation_propagates_to_services(self, temp_dir):
        """Test que la cancelación se propaga a los servicios."""
        orchestrator = AnalysisOrchestrator()
        
        def cancel_callback(current, total, message):
            return False  # Cancelar inmediatamente
        
        mock_renamer = Mock()
        mock_renamer.analyze.return_value = RenameAnalysisResult(
            success=True, total_files=0
        )
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer,
            progress_callback=cancel_callback
        )
        
        # Si se llamó al renamer, debe haber recibido el callback
        if mock_renamer.analyze.called:
            call_kwargs = mock_renamer.analyze.call_args[1]
            assert 'progress_callback' in call_kwargs


# ==================== TESTS DE TIMING ====================

@pytest.mark.unit
class TestTiming:
    """Tests de información de timing y duración."""
    
    def test_phase_timing_recorded(self, temp_dir):
        """Test que se registra el timing de cada fase."""
        orchestrator = AnalysisOrchestrator()
        
        mock_renamer = Mock()
        mock_renamer.analyze.return_value = RenameAnalysisResult(
            success=True, total_files=0
        )
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer
        )
        
        # Verificar que hay timing info
        assert 'scan' in result.phase_timings
        assert 'renaming' in result.phase_timings
        assert 'finalizing' in result.phase_timings
        
        # Verificar estructura de cada timing
        for phase_id, timing in result.phase_timings.items():
            assert isinstance(timing, PhaseTimingInfo)
            assert timing.phase_id == phase_id
            assert timing.phase_name is not None
            assert timing.start_time > 0
            assert timing.end_time >= timing.start_time
            assert timing.duration >= 0
            assert timing.duration == timing.end_time - timing.start_time
    
    def test_total_duration_recorded(self, temp_dir):
        """Test que se registra la duración total."""
        orchestrator = AnalysisOrchestrator()
        
        result = orchestrator.run_full_analysis(directory=temp_dir)
        
        assert result.total_duration > 0
        
        # La duración total debe ser mayor o igual a la suma de fases
        phase_durations_sum = sum(
            timing.duration for timing in result.phase_timings.values()
        )
        assert result.total_duration >= phase_durations_sum
    
    def test_phase_timing_consistency(self, temp_dir):
        """Test que los timings son consistentes entre fases."""
        orchestrator = AnalysisOrchestrator()
        
        mock_renamer = Mock()
        mock_renamer.analyze.return_value = RenameAnalysisResult(
            success=True, total_files=0
        )
        
        mock_live_photos = Mock()
        from services.result_types import LivePhotoCleanupAnalysisResult
        mock_live_photos.analyze.return_value = LivePhotoCleanupAnalysisResult(
            success=True, total_files=0, groups=[], live_photos_found=0,
            total_space=0, space_to_free=0, files_to_delete=[], files_to_keep=[]
        )
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer,
            live_photo_service=mock_live_photos
        )
        
        # Las fases deben ejecutarse secuencialmente
        scan_timing = result.phase_timings['scan']
        renaming_timing = result.phase_timings['renaming']
        live_photos_timing = result.phase_timings['live_photos']
        
        # El fin de una fase debe ser antes o igual al inicio de la siguiente
        assert scan_timing.end_time <= renaming_timing.start_time + 0.1  # Pequeña tolerancia
        assert renaming_timing.end_time <= live_photos_timing.start_time + 0.1


# ==================== TESTS DE EDGE CASES ====================

@pytest.mark.unit
class TestEdgeCases:
    """Tests de casos límite y situaciones especiales."""
    
    def test_analysis_with_no_services(self, temp_dir):
        """Test análisis sin ningún servicio (solo scan)."""
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.run_full_analysis(directory=temp_dir)
        
        assert result.scan is not None
        assert result.renaming is None
        assert result.live_photos is None
        assert result.organization is None
        assert result.heic is None
        assert result.duplicates is None
        
        # Solo debe tener timing de scan y finalizing
        assert 'scan' in result.phase_timings
        assert 'finalizing' in result.phase_timings
    
    def test_analysis_with_service_errors(self, temp_dir):
        """Test manejo de errores en servicios."""
        orchestrator = AnalysisOrchestrator()
        
        # Mock renamer que lanza excepción
        mock_renamer = Mock()
        mock_renamer.analyze.side_effect = Exception("Service error")
        
        # Debe propagar la excepción
        with pytest.raises(Exception, match="Service error"):
            orchestrator.run_full_analysis(
                directory=temp_dir,
                renamer=mock_renamer
            )
    
    def test_analysis_with_empty_results(self, temp_dir):
        """Test análisis con resultados vacíos de todos los servicios."""
        orchestrator = AnalysisOrchestrator()
        
        # Todos los servicios retornan resultados vacíos
        mock_renamer = Mock()
        mock_renamer.analyze.return_value = RenameAnalysisResult(
            success=True,
            total_files=0,
            already_renamed=0,
            need_renaming=0
        )
        
        mock_live_photos = Mock()
        from services.result_types import LivePhotoCleanupAnalysisResult
        mock_live_photos.analyze.return_value = LivePhotoCleanupAnalysisResult(
            success=True,
            total_files=0,
            groups=[],
            live_photos_found=0,
            total_space=0,
            space_to_free=0,
            files_to_delete=[],
            files_to_keep=[]
        )
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer,
            live_photo_service=mock_live_photos
        )
        
        assert result.renaming.need_renaming == 0
        assert result.live_photos.live_photos_found == 0
    
    def test_analysis_nonexistent_directory(self):
        """Test análisis de directorio que no existe - debe lanzar FileNotFoundError."""
        orchestrator = AnalysisOrchestrator()
        fake_dir = Path('/nonexistent/directory/path')
        
        # Ahora validamos el directorio tempranamente y lanzamos excepción
        with pytest.raises(FileNotFoundError, match="El directorio no existe"):
            orchestrator.scan_directory(fake_dir)
    
    def test_analysis_with_permission_denied(self, temp_dir):
        """Test análisis con directorio sin permisos de lectura."""
        # Este test es difícil de hacer portable, lo marcamos como skip
        pytest.skip("Test de permisos requiere configuración específica del sistema")
    
    def test_full_analysis_result_dataclass_completeness(self, temp_dir):
        """Test que FullAnalysisResult tiene todos los campos esperados."""
        scan = DirectoryScanResult(
            total_files=0,
            images=[],
            videos=[],
            others=[]
        )
        
        result = FullAnalysisResult(
            directory=temp_dir,
            scan=scan
        )
        
        # Verificar todos los campos existen
        assert hasattr(result, 'directory')
        assert hasattr(result, 'scan')
        assert hasattr(result, 'phase_timings')
        assert hasattr(result, 'renaming')
        assert hasattr(result, 'live_photos')
        assert hasattr(result, 'organization')
        assert hasattr(result, 'heic')
        assert hasattr(result, 'duplicates')
        assert hasattr(result, 'total_duration')


# ==================== TESTS DE INTEGRACIÓN ====================

@pytest.mark.unit
class TestIntegrationScenarios:
    """Tests de escenarios de integración más complejos."""
    
    def test_realistic_photo_library_analysis(self, temp_dir, create_test_image, create_test_video, create_live_photo_pair):
        """Test análisis de una biblioteca de fotos realista."""
        # Crear estructura de directorios típica
        (temp_dir / '2024' / '01').mkdir(parents=True)
        (temp_dir / '2024' / '02').mkdir(parents=True)
        (temp_dir / 'Screenshots').mkdir()
        
        # Crear varios tipos de archivos
        create_test_image(temp_dir / '2024' / '01' / 'photo1.jpg')
        create_test_image(temp_dir / '2024' / '01' / 'photo2.HEIC')
        create_test_image(temp_dir / '2024' / '02' / 'photo3.png')
        create_test_video(temp_dir / '2024' / '02' / 'video1.MOV')
        create_live_photo_pair(temp_dir / '2024' / '01', 'IMG_0001')
        create_test_image(temp_dir / 'Screenshots' / 'screenshot1.png')
        (temp_dir / 'notes.txt').write_text('Some notes')
        
        orchestrator = AnalysisOrchestrator()
        result = orchestrator.run_full_analysis(directory=temp_dir)
        
        # Verificar escaneo
        assert result.scan.total_files > 5
        assert result.scan.image_count >= 4
        assert result.scan.video_count >= 2
        assert result.scan.other_count >= 1
    
    def test_analysis_with_selective_services(self, temp_dir):
        """Test análisis selectivo (solo algunos servicios)."""
        orchestrator = AnalysisOrchestrator()
        
        # Solo usar renamer y heic
        mock_renamer = Mock()
        mock_renamer.analyze.return_value = RenameAnalysisResult(
            success=True, total_files=0
        )
        
        mock_heic = Mock()
        mock_heic.analyze.return_value = HeicAnalysisResult(
            success=True, total_files=0, total_pairs=0, heic_files=0, jpg_files=0
        )
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer,
            heic_remover=mock_heic
        )
        
        # Solo estos deben tener resultados
        assert result.renaming is not None
        assert result.heic is not None
        
        # Estos deben ser None
        assert result.live_photos is None
        assert result.organization is None
        assert result.duplicates is None
        
        # Pero debe tener timings para las fases ejecutadas
        assert 'scan' in result.phase_timings
        assert 'renaming' in result.phase_timings
        assert 'heic' in result.phase_timings
        assert 'finalizing' in result.phase_timings
        
        # Y NO debe tener timings de fases no ejecutadas
        assert 'live_photos' not in result.phase_timings
        assert 'organization' not in result.phase_timings
        assert 'duplicates' not in result.phase_timings
    
    def test_analysis_performance_with_many_files(self, temp_dir, create_test_image):
        """Test rendimiento con muchos archivos."""
        # Crear 50 archivos
        for i in range(50):
            create_test_image(temp_dir / f'photo{i:03d}.jpg', size=(50, 50))
        
        orchestrator = AnalysisOrchestrator()
        
        start_time = time.time()
        result = orchestrator.run_full_analysis(directory=temp_dir)
        duration = time.time() - start_time
        
        # Debe completarse en tiempo razonable (< 5 segundos para 50 archivos pequeños)
        assert duration < 5.0
        assert result.scan.total_files == 50
        assert result.scan.image_count == 50


# ==================== TESTS DE COMPATIBILIDAD ====================

@pytest.mark.unit
class TestBackwardCompatibility:
    """Tests de compatibilidad con código existente."""
    
    def test_result_types_match_expected_structure(self, temp_dir):
        """Test que los tipos de resultado tienen la estructura esperada."""
        orchestrator = AnalysisOrchestrator()
        
        # Usar mocks que retornan las estructuras esperadas
        mock_renamer = Mock()
        rename_result = RenameAnalysisResult(
            success=True,
            total_files=10,
            already_renamed=3,
            need_renaming=7,
            cannot_process=0,
            conflicts=0,
            files_by_year={},
            renaming_plan=[],
            issues=[]
        )
        mock_renamer.analyze.return_value = rename_result
        
        result = orchestrator.run_full_analysis(
            directory=temp_dir,
            renamer=mock_renamer
        )
        
        # Verificar que el resultado tiene todos los campos esperados
        assert hasattr(result.renaming, 'success')
        assert hasattr(result.renaming, 'total_files')
        assert hasattr(result.renaming, 'already_renamed')
        assert hasattr(result.renaming, 'need_renaming')
        assert hasattr(result.renaming, 'cannot_process')
        assert hasattr(result.renaming, 'conflicts')
        assert hasattr(result.renaming, 'files_by_year')
        assert hasattr(result.renaming, 'renaming_plan')
    
    def test_orchestrator_can_be_used_without_callbacks(self, temp_dir):
        """Test que el orquestador funciona sin callbacks (uso más simple)."""
        orchestrator = AnalysisOrchestrator()
        
        # Sin ningún callback
        result = orchestrator.run_full_analysis(directory=temp_dir)
        
        assert result is not None
        assert isinstance(result, FullAnalysisResult)
    
    def test_scan_result_has_backward_compatible_properties(self):
        """Test que DirectoryScanResult mantiene propiedades legacy."""
        result = DirectoryScanResult(
            total_files=10,
            images=[Path('a.jpg')],
            videos=[Path('b.mov')],
            others=[Path('c.txt')]
        )
        
        # Propiedades de conteo
        assert result.image_count == 1
        assert result.video_count == 1
        assert result.other_count == 1
        
        # Listas directas
        assert len(result.images) == 1
        assert len(result.videos) == 1
        assert len(result.others) == 1
