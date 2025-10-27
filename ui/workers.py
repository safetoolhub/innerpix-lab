"""
Workers para la aplicación PhotoKit Manager
Este módulo contiene todos los QThread workers que ejecutan operaciones
en segundo plano para no bloquear la interfaz gráfica.
"""
from PyQt5.QtCore import QThread, pyqtSignal
import config


class BaseWorker(QThread):
    """Base worker that provides common signals and a helper to create
    progress callbacks to avoid repeating the same small functions in
    every worker.
    """
    progress_update = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_requested = False

    def stop(self):
        """Request the worker to stop gracefully"""
        self._stop_requested = True

    def is_stop_requested(self):
        """Check if stop was requested"""
        return self._stop_requested

    def _create_progress_callback(self, counts_in_message: bool = False, emit_numbers: bool = False):
        """Return a progress callback(current, total, message) with consistent
        behavior across workers.

        - By default emits (0, 0, message) so the UI shows only the text.
        - If counts_in_message is True, appends " (current/total)" to the
          message and still emits numeric placeholders (0,0) for UI.
        - If emit_numbers is True, emits (current, total, message) so the
          UI can use real progress numbers.
        """
        def callback(current: int, total: int, message: str):
            try:
                # Check if stop was requested
                if self._stop_requested:
                    return False  # Signal to stop processing
                
                if emit_numbers:
                    self.progress_update.emit(current, total, message)
                elif counts_in_message:
                    self.progress_update.emit(0, 0, f"{message} ({current}/{total})")
                else:
                    self.progress_update.emit(0, 0, message)
                return True  # Continue processing
            except Exception:
                # La señal de progreso no debe bloquear el worker
                return True

        return callback


class AnalysisWorker(BaseWorker):
    """Worker unificado para análisis completo"""
    phase_update = pyqtSignal(str)
    stats_update = pyqtSignal(dict)  # Nueva señal para actualizar stats parciales
    partial_results = pyqtSignal(dict)  # Nueva señal para resultados parciales de funcionalidades

    def __init__(self, directory, renamer, lp_detector, unifier, heic_remover, organization_type=None):
        super().__init__()
        self.directory = directory
        self.renamer = renamer
        self.lp_detector = lp_detector
        self.unifier = unifier
        self.heic_remover = heic_remover
        self.organization_type = organization_type  # None usará el default (TO_ROOT)

    def run(self):
        try:
            results = {
                'stats': {},
                'renaming': None,
                'live_photos': None,
                'organization': None,
                'heic': None
            }

            # Fase 1: Escaneo de archivos
            if self._stop_requested:
                return
            
            self.phase_update.emit("📂 Escaneando archivos...")
            all_files = list(self.directory.rglob("*"))
            total_files = len([f for f in all_files if f.is_file()])
            images, videos, others = [], [], []
            processed = 0

            for f in all_files:
                if self._stop_requested:
                    return
                
                if f.is_file():
                    if config.config.is_image_file(f.name):
                        images.append(f)
                    elif config.config.is_video_file(f.name):
                        videos.append(f)
                    else:
                        others.append(f)
                    processed += 1
                    if processed % 10 == 0:
                        # Emitir solo mensaje (números se ignoran por la UI)
                        self.progress_update.emit(0, 0, "Escaneando archivos")

            results['stats'] = {
                'total': total_files,
                'images': len(images),
                'videos': len(videos),
                'others': len(others)
            }

            # Emitir estadísticas parciales para actualizar el summary inmediatamente
            self.stats_update.emit(results['stats'])

            # Fase 2: Análisis de renombrado
            if self._stop_requested:
                return
            
            if self.renamer:
                self.phase_update.emit("📝 Analizando nombres de archivos...")

                # Crear callback que emita progress_update SIN procesar eventos
                # El callback solo emite la señal, el procesamiento lo hace Qt internamente
                results['renaming'] = self.renamer.analyze_directory(
                    self.directory,
                    progress_callback=self._create_progress_callback(counts_in_message=True)
                )
                # Emitir resultados parciales después de renombrado
                self.partial_results.emit({'renaming': results['renaming']})

            # Fase 3: Detección de Live Photos
            if self._stop_requested:
                return
            
            if self.lp_detector:
                self.phase_update.emit("📱 Detectando Live Photos...")
                lp_groups = self.lp_detector.detect_in_directory(self.directory)
                # Calcular estadísticas directamente de los grupos
                total_space = sum(group.total_size for group in lp_groups)
                video_space = sum(group.video_size for group in lp_groups)
                
                results['live_photos'] = {
                    'groups': [
                        {
                            'image_path': str(group.image_path),
                            'video_path': str(group.video_path),
                            'base_name': group.base_name,
                            'total_size': group.total_size,
                            'video_size': group.video_size,
                            'image_size': group.image_size
                        }
                        for group in lp_groups
                    ],
                    'total_space': total_space,
                    'space_to_free': video_space,
                    'live_photos_found': len(lp_groups)
                }
                # Emitir resultados parciales después de Live Photos
                self.partial_results.emit({'live_photos': results['live_photos']})

            # Fase 4: Análisis de estructura
            if self._stop_requested:
                return
            
            if self.unifier:
                self.phase_update.emit("📁 Analizando estructura de directorios para organización...")
                # Pasar el tipo de organización si está disponible
                if self.organization_type:
                    results['organization'] = self.unifier.analyze_directory_structure(
                        self.directory, 
                        organization_type=self.organization_type
                    )
                else:
                    results['organization'] = self.unifier.analyze_directory_structure(self.directory)
                # Emitir resultados parciales después de organización
                self.partial_results.emit({'organization': results['organization']})

            # Fase 5: Duplicados HEIC
            if self._stop_requested:
                return
            
            if self.heic_remover:
                self.phase_update.emit("🖼️ Buscando duplicados HEIC/JPG...")
                results['heic'] = self.heic_remover.analyze_heic_duplicates(self.directory)
                # Emitir resultados parciales después de HEIC
                self.partial_results.emit({'heic': results['heic']})

            if not self._stop_requested:
                self.finished.emit(results)

        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class RenamingWorker(BaseWorker):
    """Worker para ejecutar renombrado de nombres de archivos"""

    def __init__(self, renamer, plan, create_backup=True):
        super().__init__()
        self.renamer = renamer
        self.plan = plan
        self.create_backup = create_backup

    def run(self):
        try:
            if self._stop_requested:
                return
            
            results = self.renamer.execute_renaming(
                self.plan,
                create_backup=self.create_backup,
                progress_callback=self._create_progress_callback()
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class LivePhotoCleanupWorker(BaseWorker):
    """Worker para ejecutar limpieza de Live Photos"""

    def __init__(self, cleaner, plan):
        super().__init__()
        self.cleaner = cleaner
        self.plan = plan

    def run(self):
        try:
            if self._stop_requested:
                return
            
            # Convertimos el plan en el formato que espera el cleaner
            cleanup_analysis = {
                'files_to_delete': self.plan['files_to_delete']
            }
            results = self.cleaner.execute_cleanup(
                cleanup_analysis,
                create_backup=self.plan['create_backup'],
                dry_run=self.plan['dry_run'],
                progress_callback=self._create_progress_callback()
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class FileOrganizerWorker(BaseWorker):
    """Worker para ejecutar organización de archivos"""

    def __init__(self, organizer, plan, create_backup=True):
        super().__init__()
        self.organizer = organizer
        self.plan = plan
        self.create_backup = create_backup

    def run(self):
        try:
            if self._stop_requested:
                return
            
            results = self.organizer.execute_organization(
                self.plan,
                create_backup=self.create_backup,
                progress_callback=self._create_progress_callback()
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class HEICRemovalWorker(BaseWorker):
    """Worker para ejecutar eliminación de duplicados HEIC"""

    def __init__(self, remover, pairs, keep_format, create_backup=True):
        super().__init__()
        self.remover = remover
        self.pairs = pairs
        self.keep_format = keep_format
        self.create_backup = create_backup

    def run(self):
        try:
            if self._stop_requested:
                return
            
            progress_cb_local = self._create_progress_callback()

            # Attach callback to remover so create_backup (which may not accept
            # progress_callback explicitly) can use it via attribute
            setattr(self.remover, '_progress_callback', progress_cb_local)

            results = self.remover.execute_removal(
                self.pairs,
                keep_format=self.keep_format,
                create_backup=self.create_backup
            )
            # Clean up attribute
            if hasattr(self.remover, '_progress_callback'):
                delattr(self.remover, '_progress_callback')
            
            if not self._stop_requested:
                self.finished.emit(results)
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)

class DuplicateAnalysisWorker(BaseWorker):
    """Worker para análisis de duplicados (exactos o similares)"""
    
    def __init__(self, detector, directory, mode='exact', sensitivity=10):
        super().__init__()
        self.detector = detector
        self.directory = directory
        self.mode = mode
        self.sensitivity = sensitivity
    
    def run(self):
        try:
            if self._stop_requested:
                return
            
            if self.mode == 'exact':
                results = self.detector.analyze_exact_duplicates(
                    self.directory,
                    progress_callback=self._create_progress_callback(emit_numbers=True)
                )
            else:  # perceptual
                results = self.detector.analyze_similar_duplicates(
                    self.directory,
                    sensitivity=self.sensitivity,
                    progress_callback=self._create_progress_callback(emit_numbers=True)
                )
            
            if not self._stop_requested:
                self.finished.emit(results)
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)


class DuplicateDeletionWorker(BaseWorker):
    """Worker para eliminación de duplicados"""
    
    def __init__(self, detector, groups, keep_strategy, create_backup=True):
        super().__init__()
        self.detector = detector
        self.groups = groups
        self.keep_strategy = keep_strategy
        self.create_backup = create_backup
    
    def run(self):
        try:
            if self._stop_requested:
                return
            
            results = self.detector.execute_deletion(
                self.groups,
                keep_strategy=self.keep_strategy,
                create_backup=self.create_backup,
                progress_callback=self._create_progress_callback()
            )
            
            if not self._stop_requested:
                self.finished.emit(results)
        
        except Exception as e:
            if not self._stop_requested:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                self.error.emit(error_msg)
