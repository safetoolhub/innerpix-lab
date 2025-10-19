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
                def rename_progress_callback(current: int, total: int, message: str):
                    # No enviar números; solo emitir mensaje para la UI
                    self.progress_update.emit(0, 0, f"{message} ({current}/{total})")

                results['renaming'] = self.renamer.analyze_directory(
                    self.directory,
                    progress_callback=rename_progress_callback
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


class RenamingWorker(QThread):
    """Worker para ejecutar renombrado de nombres de archivos"""
    progress_update = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, renamer, plan, create_backup=True):
        super().__init__()
        self.renamer = renamer
        self.plan = plan
        self.create_backup = create_backup

    def run(self):
        try:
            def progress_callback(current: int, total: int, message: str):
                # Enviar solo el mensaje; los valores numéricos serán ignorados
                self.progress_update.emit(0, 0, message)

            results = self.renamer.execute_renaming(
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
            # Convertimos el plan en el formato que espera el cleaner
            cleanup_analysis = {
                'files_to_delete': self.plan['files_to_delete']
            }
            def progress_callback(current: int, total: int, message: str):
                self.progress_update.emit(0, 0, message)

            results = self.cleaner.execute_cleanup(
                cleanup_analysis,
                create_backup=self.plan['create_backup'],
                dry_run=self.plan['dry_run'],
                progress_callback=progress_callback
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
                self.progress_update.emit(0, 0, message)

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
            def progress_callback(current: int, total: int, message: str):
                self.progress_update.emit(0, 0, message)

            # Attach callback to remover so create_backup (which may not accept
            # progress_callback explicitly) can use it via attribute
            try:
                setattr(self.remover, '_progress_callback', progress_callback)
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
