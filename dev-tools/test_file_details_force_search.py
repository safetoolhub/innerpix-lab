#!/usr/bin/env python3
"""
Script de prueba para verificar el botón de búsqueda forzada en show_file_details_dialog.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from ui.dialogs.dialog_utils import show_file_details_dialog
from utils.logger import configure_logging

def main():
    """Prueba del diálogo de detalles con búsqueda forzada"""
    
    # Configurar logging
    configure_logging(Path.home() / "Documents" / "Innerpix_Lab" / "logs", level="DEBUG")
    
    app = QApplication(sys.argv)
    
    # Crear ventana de prueba
    window = QWidget()
    window.setWindowTitle("Test File Details Dialog - Force Search")
    layout = QVBoxLayout(window)
    
    # Buscar un archivo de prueba en el directorio actual
    test_files = []
    for pattern in ['*.py', '*.txt', '*.md']:
        test_files.extend(Path(__file__).parent.parent.glob(pattern))
    
    if not test_files:
        print("No se encontraron archivos de prueba")
        return
    
    test_file = test_files[0]
    print(f"Archivo de prueba: {test_file}")
    
    # Botón para abrir el diálogo
    btn = QPushButton(f"Abrir detalles de:\n{test_file.name}")
    btn.clicked.connect(lambda: show_file_details_dialog(test_file, window))
    layout.addWidget(btn)
    
    # Botón para abrir con búsqueda forzada
    btn_force = QPushButton(f"Abrir con búsqueda forzada:\n{test_file.name}")
    btn_force.clicked.connect(lambda: show_file_details_dialog(test_file, window, force_metadata_search=True))
    layout.addWidget(btn_force)
    
    window.show()
    
    print("\n=== INSTRUCCIONES ===")
    print("1. Haz clic en 'Abrir detalles' para ver el diálogo normal")
    print("2. En el diálogo, verás un icono de 'database-refresh' en el header")
    print("3. Haz clic en ese icono para forzar la búsqueda completa de metadatos")
    print("4. El diálogo se recargará con todos los metadatos disponibles (hash + EXIF)")
    print("5. Observa que aparece un icono de check verde indicando búsqueda completa")
    print("\nAlternativamente, usa el botón 'Abrir con búsqueda forzada' para ir directo")
    print("=" * 50)
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
