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
                if emit_numbers:
                    self.progress_update.emit(current, total, message)
                elif counts_in_message:
                    self.progress_update.emit(0, 0, f"{message} ({current}/{total})")
                else:
                    self.progress_update.emit(0, 0, message)
            except Exception:
                # Never let a progress signal error crash the worker
                pass

        return callback


class AnalysisWorker(BaseWorker):
    """Worker unificado para análisis completo"""
    phase_update = pyqtSignal(str)

    def __init__(self, directory, renamer, lp_detector, unifier, heic_remover):
        super().__init__()
        self.directory = directory
        self.renamer = renamer
        self.lp_detector = lp_detector
        self.unifier = unifier
        self.heic_remover = heic_remover

    def run(self):
        try:
            results = {
                'stats': {},
                'renaming': None,
                'live_photos': None,
                'unification': None,
                'heic': None
            }

            # Fase 1: Escaneo de archivos
            self.phase_update.emit("📂 Escaneando archivos...")
            all_files = list(self.directory.rglob("*"))
            total_files = len([f for f in all_files if f.is_file()])
            images, videos, others = [], [], []
            processed = 0

            for f in all_files:
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

            # Fase 2: Análisis de renombrado
            if self.renamer:
                self.phase_update.emit("📝 Analizando nombres de archivos...")

                # Crear callback que emita progress_update SIN procesar eventos
                # El callback solo emite la señal, el procesamiento lo hace Qt internamente
                results['renaming'] = self.renamer.analyze_directory(
                    self.directory,
                    progress_callback=self._create_progress_callback(counts_in_message=True)
                )

            # Fase 3: Detección de Live Photos
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

            # Fase 4: Análisis de estructura
            if self.unifier:
                self.phase_update.emit("📁 Analizando estructura de directorios para unificación...")
                results['unification'] = self.unifier.analyze_directory_structure(self.directory)

            # Fase 5: Duplicados HEIC
            if self.heic_remover:
                self.phase_update.emit("🖼️ Buscando duplicados HEIC/JPG...")
                results['heic'] = self.heic_remover.analyze_heic_duplicates(self.directory)

            self.finished.emit(results)

        except Exception as e:
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
            results = self.renamer.execute_renaming(
                self.plan,
                create_backup=self.create_backup,
                progress_callback=self._create_progress_callback()
            )
            self.finished.emit(results)
        except Exception as e:
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
            self.finished.emit(results)
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class DirectoryUnificationWorker(BaseWorker):
    """Worker para ejecutar unificación de directorios"""

    def __init__(self, unifier, plan, create_backup=True):
        super().__init__()
        self.unifier = unifier
        self.plan = plan
        self.create_backup = create_backup

    def run(self):
        try:
            results = self.unifier.execute_unification(
                self.plan,
                create_backup=self.create_backup,
                progress_callback=self._create_progress_callback()
            )
            self.finished.emit(results)
        except Exception as e:
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
            progress_cb_local = self._create_progress_callback()

            # Attach callback to remover so create_backup (which may not accept
            # progress_callback explicitly) can use it via attribute
            try:
                setattr(self.remover, '_progress_callback', progress_cb_local)
            except Exception:
                pass

            results = self.remover.execute_removal(
                self.pairs,
                keep_format=self.keep_format,
                create_backup=self.create_backup
            )
            # Clean up attribute
            try:
                delattr(self.remover, '_progress_callback')
            except Exception:
                pass
            self.finished.emit(results)
        except Exception as e:
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
            if self.mode == 'exact':
                results = self.detector.analyze_exact_duplicates(
                    self.directory,
                    progress_callback=self._create_progress_callback()
                )
            else:  # perceptual
                results = self.detector.analyze_similar_duplicates(
                    self.directory,
                    sensitivity=self.sensitivity,
                    progress_callback=self._create_progress_callback()
                )
            
            self.finished.emit(results)
        
        except Exception as e:
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
            results = self.detector.execute_deletion(
                self.groups,
                keep_strategy=self.keep_strategy,
                create_backup=self.create_backup,
                progress_callback=self._create_progress_callback()
            )
            
            self.finished.emit(results)
        
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)
