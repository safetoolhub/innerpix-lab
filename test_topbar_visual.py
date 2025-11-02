#!/usr/bin/env python3
"""
Script de prueba visual para verificar el TopBar expandible.
Ejecutar: python test_topbar_visual.py
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Establecer nombre de la app
    app.setApplicationName("Pixaro Lab - Test Visual")
    
    # Crear y mostrar ventana
    window = MainWindow()
    window.show()
    
    print("=" * 60)
    print("TEST VISUAL - TopBar Expandible")
    print("=" * 60)
    print("\n✓ Ventana iniciada correctamente")
    print("\nVerifica visualmente:")
    print("  1. TopBar está en la parte SUPERIOR (no centrada)")
    print("  2. Botón 'Seleccionar' visible")
    print("  3. Iconos de configuración e info visibles")
    print("  4. NO hay espacio blanco arriba del TopBar")
    print("  5. Pestañas ocupan todo el espacio inferior")
    print("\nCuando selecciones un directorio:")
    print("  6. El resumen se expande con animación suave")
    print("  7. Stats, herramientas y progreso son visibles")
    print("  8. Botón 'Ocultar resumen' funciona correctamente")
    print("  9. Ctrl+R alterna el resumen")
    print("\n" + "=" * 60)
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
