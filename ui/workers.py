"""
Workers para la aplicación PhotoKit Manager
Este módulo contiene todos los QThread workers que ejecutan operaciones
en segundo plano para no bloquear la interfaz gráfica.
"""
from PyQt5.QtCore import QThread, pyqtSignal
import config


class AnalysisWorker(QThread):
    """Worker unificado para análisis completo"""
    progress_update = pyqtSignal(int, int, str)
    phase_update = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, directory, normalizer, lp_detector, unifier, heic_remover):
        super().__init__()
        self.directory = directory
        self.normalizer = normalizer
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
                        self.progress_update.emit(processed, total_files, "Escaneando archivos")

            results['stats'] = {
                'total': total_files,
                'images': len(images),
                'videos': len(videos),
                'others': len(others)
            }

            # Fase 2: Análisis de renombrado
            if self.normalizer:
                self.phase_update.emit("📝 Analizando nombres de archivo...")

                # Crear callback que emita progress_update SIN procesar eventos
                # El callback solo emite la señal, el procesamiento lo hace Qt internamente
                def norm_progress_callback(current: int, total: int, message: str):
                    # Emitir señal con el formato deseado
                    self.progress_update.emit(current, total, f"{message} ({current}/{total})")

                results['renaming'] = self.normalizer.analyze_directory(
                    self.directory,
                    progress_callback=norm_progress_callback
                )

            # Fase 3: Detección de Live Photos
            if self.lp_detector:
                self.phase_update.emit("📱 Detectando Live Photos...")
                lp_groups = self.lp_detector.detect_in_directory(self.directory)
                if lp_groups:
                    lp_analysis = self.lp_detector.analyze_live_photos(lp_groups)
                    # Convertir al formato esperado
                    results['live_photos'] = {
                        'live_photos_found': lp_analysis.get('total_live_photos', 0),
                        'total_space': lp_analysis.get('total_size', 0),
                        'space_to_free': lp_analysis.get('potential_savings_keep_image', 0),
                        'groups': lp_groups,
                        'analysis': lp_analysis
                    }
                else:
                    results['live_photos'] = {
                        'live_photos_found': 0,
                        'total_space': 0,
                        'space_to_free': 0,
                        'groups': [],
                        'analysis': {}
                    }

            # Fase 4: Análisis de estructura
            if self.unifier:
                self.phase_update.emit("📁 Analizando estructura de directorios...")
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


class RenamingWorker(QThread):
    """Worker para ejecutar renombrado de nombres de archivo"""
    progress_update = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, normalizer, plan, create_backup=True):
        super().__init__()
        self.normalizer = normalizer
        self.plan = plan
        self.create_backup = create_backup

    def run(self):
        try:
            def progress_callback(current: int, total: int, message: str):
                self.progress_update.emit(current, total, message)

            results = self.normalizer.execute_renaming(
                self.plan,
                create_backup=self.create_backup,
                progress_callback=progress_callback
            )
            self.finished.emit(results)
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class LivePhotoCleanupWorker(QThread):
    """Worker para ejecutar limpieza de Live Photos"""
    progress_update = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, cleaner, plan):
        super().__init__()
        self.cleaner = cleaner
        self.plan = plan

    def run(self):
        try:
            analysis = self.plan['analysis']
            results = self.cleaner.execute_cleanup(
                analysis,
                create_backup=self.plan['create_backup'],
                dry_run=self.plan['dry_run']
            )
            self.finished.emit(results)
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class DirectoryUnificationWorker(QThread):
    """Worker para ejecutar unificación de directorios"""
    progress_update = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, unifier, plan, create_backup=True):
        super().__init__()
        self.unifier = unifier
        self.plan = plan
        self.create_backup = create_backup

    def run(self):
        try:
            def progress_callback(current: int, total: int, message: str):
                self.progress_update.emit(current, total, message)

            results = self.unifier.execute_unification(
                self.plan,
                create_backup=self.create_backup,
                progress_callback=progress_callback
            )
            self.finished.emit(results)
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)


class HEICRemovalWorker(QThread):
    """Worker para ejecutar eliminación de duplicados HEIC"""
    progress_update = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, remover, pairs, keep_format, create_backup=True):
        super().__init__()
        self.remover = remover
        self.pairs = pairs
        self.keep_format = keep_format
        self.create_backup = create_backup

    def run(self):
        try:
            results = self.remover.execute_removal(
                self.pairs,
                keep_format=self.keep_format,
                create_backup=self.create_backup
            )
            self.finished.emit(results)
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)
