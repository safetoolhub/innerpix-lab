"""
Script de demostración del warning de tamaño de video en Live Photos.

Muestra cómo el sistema detecta videos que exceden el tamaño típico
de Live Photos y emite warnings apropiados.
"""
from config import Config
from utils.format_utils import format_size

def main():
    print("=" * 70)
    print("CONFIGURACIÓN DE LIVE PHOTOS - DETECCIÓN DE TAMAÑO SOSPECHOSO")
    print("=" * 70)
    
    # Mostrar configuración
    max_size = Config.LIVE_PHOTO_MAX_VIDEO_SIZE
    max_size_mb = max_size / (1024 * 1024)
    
    print(f"\n📋 Configuración actual:")
    print(f"   LIVE_PHOTO_MAX_VIDEO_SIZE = {format_size(max_size)} ({max_size_mb:.1f} MB)")
    print(f"\n💡 Propósito:")
    print(f"   Los videos de Live Photos típicamente son muy pequeños (1-5 MB).")
    print(f"   Si un video excede {max_size_mb:.1f} MB, puede no ser realmente parte de un Live Photo.")
    
    print(f"\n🔍 Ejemplos de tamaños:")
    test_sizes = [
        (2 * 1024 * 1024, "Video típico de Live Photo", "✅ Normal"),
        (5 * 1024 * 1024, "Video grande de Live Photo", "✅ Normal"),
        (7 * 1024 * 1024, "Video sospechoso", "⚠️  WARNING"),
        (15 * 1024 * 1024, "Video muy sospechoso", "⚠️  WARNING"),
        (50 * 1024 * 1024, "Claramente no es Live Photo", "⚠️  WARNING"),
    ]
    
    for size, description, status in test_sizes:
        exceeds = size > max_size
        print(f"   • {format_size(size):>10} - {description:<30} {status}")
        if exceeds:
            print(f"     └─ Excede el límite por {format_size(size - max_size)}")
    
    print(f"\n📝 Formato del log cuando se detecta:")
    print(f"   ⚠️  SOSPECHA: Video eliminado supera tamaño típico de Live Photo |")
    print(f"   Archivo: /path/to/video.MOV |")
    print(f"   Tamaño: 15.2 MB |")
    print(f"   Límite: {format_size(max_size)} |")
    print(f"   Puede no ser realmente un video de Live Photo")
    
    print(f"\n✨ Ventajas:")
    print(f"   • Detecta posibles errores en la detección de Live Photos")
    print(f"   • Alerta al usuario sobre eliminaciones sospechosas")
    print(f"   • Configurable en config.py (LIVE_PHOTO_MAX_VIDEO_SIZE)")
    print(f"   • Logs grep-friendly en archivos WARNERROR")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
