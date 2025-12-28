"""
Script de prueba para verificar extracción de dimensiones de imagen
"""
import sys
from pathlib import Path

# Agregar path raíz al PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.file_utils import get_exif_from_image

def test_image_dimensions():
    """Prueba la extracción de dimensiones desde imágenes"""
    
    # Buscar una imagen de prueba en el directorio común
    test_dirs = [
        Path("/home/ed/Pictures/TEST_BASE2"),
        Path("/home/ed/Pictures"),
    ]
    
    image_file = None
    for test_dir in test_dirs:
        if test_dir.exists():
            # Buscar primera imagen JPEG o PNG
            for ext in ['*.jpg', '*.jpeg', '*.png']:
                images = list(test_dir.glob(f"**/{ext}"))
                if images:
                    image_file = images[0]
                    break
            if image_file:
                break
    
    if not image_file:
        print("❌ No se encontró ninguna imagen de prueba")
        return
    
    print(f"🔍 Probando con: {image_file.name}")
    print(f"📁 Ruta: {image_file}")
    print()
    
    # Extraer EXIF
    exif_data = get_exif_from_image(image_file)
    
    # Mostrar todos los campos
    print("=" * 60)
    print("CAMPOS EXIF EXTRAÍDOS")
    print("=" * 60)
    
    for key, value in exif_data.items():
        if value is not None:
            print(f"✓ {key:25} = {value}")
        else:
            print(f"  {key:25} = None")
    
    print()
    
    # Verificar dimensiones específicamente
    if exif_data.get('ImageWidth') and exif_data.get('ImageLength'):
        print(f"✅ DIMENSIONES EXTRAÍDAS CORRECTAMENTE")
        print(f"   📐 Resolución: {exif_data['ImageWidth']} × {exif_data['ImageLength']} píxeles")
    else:
        print("⚠️  Las dimensiones NO fueron extraídas")
        print("   Esto puede ser normal para algunos formatos de imagen")

if __name__ == "__main__":
    test_image_dimensions()
