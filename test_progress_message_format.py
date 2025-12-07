"""
Script de prueba para visualizar el nuevo formato de mensajes de progreso.

Este script muestra cómo se verán los mensajes de progreso con el nuevo
formato de dos líneas en el diálogo de progreso.
"""
import sys
from PyQt6.QtWidgets import QApplication, QProgressDialog
from PyQt6.QtCore import Qt, QTimer


def test_old_format():
    """Formato antiguo: todo en una línea (problema de movimiento)"""
    print("\n=== FORMATO ANTIGUO (UNA LÍNEA) ===")
    print("Problema: texto centrado se mueve constantemente con diferentes longitudes")
    print()
    
    files = [
        "IMG_001.jpg",
        "very_long_filename_with_many_characters_that_makes_dialog_move_around.jpg",
        "IMG_002.jpg",
        "another_very_long_name_for_testing_the_visual_effect.jpg",
        "IMG_003.jpg"
    ]
    
    for i, file in enumerate(files, 1):
        msg = f"[Simulación] Borraría: {file}"
        print(f"{i}/5: {msg}")


def test_new_format():
    """Formato nuevo: dos líneas (acción fija + archivo variable)"""
    print("\n=== FORMATO NUEVO (DOS LÍNEAS) ===")
    print("Mejora: primera línea fija, solo segunda línea cambia")
    print()
    
    files = [
        "IMG_001.jpg",
        "very_long_filename_with_many_characters_that_makes_dialog_move_around.jpg",
        "IMG_002.jpg",
        "another_very_long_name_for_testing_the_visual_effect.jpg",
        "IMG_003.jpg"
    ]
    
    for i, file in enumerate(files, 1):
        action = "[Simulación] Borraría"
        msg = f"{action}\n{file}"
        print(f"{i}/5:")
        print(f"  {action}")
        print(f"  {file}")
        print()


def test_visual_dialog():
    """Prueba visual en un QProgressDialog real"""
    app = QApplication(sys.argv)
    
    files = [
        "IMG_001.jpg",
        "very_long_filename_with_many_characters.jpg",
        "IMG_002.jpg",
        "another_very_long_name_for_testing.jpg",
        "IMG_003.jpg"
    ]
    
    # Test formato antiguo
    progress = QProgressDialog(
        "Formato antiguo (una línea)",
        "Cancelar",
        0, len(files)
    )
    progress.setWindowTitle("Test: Formato Antiguo")
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.show()
    
    for i, file in enumerate(files):
        progress.setValue(i)
        msg = f"[Simulación] Borraría: {file}"
        progress.setLabelText(msg)
        QApplication.processEvents()
        QTimer.singleShot(800, lambda: None)  # Pausa para visualizar
        app.processEvents()
    
    progress.close()
    
    # Test formato nuevo
    progress = QProgressDialog(
        "Formato nuevo (dos líneas)",
        "Cancelar",
        0, len(files)
    )
    progress.setWindowTitle("Test: Formato Nuevo")
    progress.setWindowModality(Qt.WindowModality.ApplicationModal)
    progress.show()
    
    for i, file in enumerate(files):
        progress.setValue(i)
        action = "[Simulación] Borraría"
        msg = f"{action}\n{file}"
        progress.setLabelText(msg)
        QApplication.processEvents()
        QTimer.singleShot(800, lambda: None)  # Pausa para visualizar
        app.processEvents()
    
    progress.close()


if __name__ == "__main__":
    print("=" * 80)
    print("TEST DE FORMATO DE MENSAJES DE PROGRESO")
    print("=" * 80)
    
    test_old_format()
    test_new_format()
    
    print("\n" + "=" * 80)
    print("Para test visual en ventana real, ejecutar: python test_progress_message_format.py --visual")
    print("=" * 80)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--visual":
        test_visual_dialog()
