"""Helpers para validar y confirmar cambios de directorio en la UI.

Este módulo centraliza la lógica repetida que estaba en
`ui/main_window.py` para: preguntar confirmaciones de cambio de
directorio, contar archivos de forma segura y avisar al usuario si el
directorio es grande.
"""
from pathlib import Path
from typing import Optional

from PyQt5.QtWidgets import QMessageBox, QWidget


def confirm_directory_change(parent: QWidget, old_directory: Path, new_directory: Path, logger=None) -> bool:
    """Pregunta al usuario si desea cambiar el directorio cuando hay un
    análisis previo en otro directorio.

    Devuelve True si el usuario confirma continuar (y por tanto el llamador
    deberá limpiar el estado de análisis), o False si cancela.
    """
    reply = QMessageBox.question(
        parent,
        "Cambio de Directorio",
        f"Has solicitado cambiar el directorio de análisis.\n\n"
        f"📂 Directorio anterior: {old_directory.name}\n"
        f"📂 Directorio nuevo: {new_directory.name}\n\n"
        f"⚠️ El análisis anterior se perderá y será necesario realizar un nuevo análisis.\n\n"
        f"¿Deseas continuar?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    if reply == QMessageBox.No:
        if logger:
            logger.info("Cambio de directorio cancelado por el usuario")
        return False
    return True


def count_files_in_directory(path: Path) -> int:
    """Cuenta recursivamente el número de archivos dentro de `path`.

    Lanza la excepción original en caso de error de acceso para que el
    llamador la maneje (normalmente mostrando un QMessageBox).
    """
    # Usar rglob para incluir subdirectorios. Se cuenta solo objetos que
    # son archivos (is_file). Esto puede ser costoso en directorios muy
    # grandes; el llamador decide si quiere mostrar una advertencia.
    all_files = list(path.rglob("*"))
    return sum(1 for f in all_files if f.is_file())


def confirm_large_directory(parent: QWidget, new_directory: Path, file_count: int, threshold: int) -> bool:
    """Si `file_count` excede `threshold`, muestra un diálogo que pide al
    usuario confirmar el inicio del análisis. Devuelve True si desea
    iniciar el análisis, False en caso contrario.
    """
    if file_count <= threshold:
        return True

    reply = QMessageBox.question(
        parent,
        "Directorio Grande Detectado",
        f"📁 Directorio: {new_directory.name}\n\n"
        f"📊 Se detectaron aproximadamente {file_count:,} archivos.\n\n"
        f"⏱️ Aviso: El análisis de esta cantidad de archivos podría tardar\n"
        f"varios minutos dependiendo de la potencia de tu equipo.\n\n"
        f"¿Deseas iniciar el análisis ahora?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    )

    return reply == QMessageBox.Yes
