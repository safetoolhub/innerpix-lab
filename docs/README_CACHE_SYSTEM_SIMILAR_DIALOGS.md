# Sistema de Caché para Desarrollo de Similar Files Dialog

## 🎯 Problema

Durante el desarrollo del diálogo de archivos similares necesitas probarlo con datasets grandes (40k+ archivos) para verificar:
- Rendimiento con grandes volúmenes
- Uso de memoria
- Comportamiento de la UI
- Paginación

**PERO** analizar 40k archivos cada vez tarda **5-10 minutos**, lo cual hace el desarrollo muy lento.

## ✅ Solución: Sistema de Caché Persistente

El sistema te permite:
1. **Analizar UNA VEZ** el dataset grande (lento, pero solo una vez)
2. **Guardar** los resultados en un archivo cache
3. **Cargar INSTANTÁNEAMENTE** (< 1 segundo) los resultados en futuras sesiones

## 📋 Flujo de Trabajo

### 1. Crear la caché (primera vez)

```bash
# Activa el entorno virtual
source .venv/bin/activate

# Analiza tu dataset grande y guarda el resultado
python scripts/cache_similar_analysis.py create /path/to/40k/photos
```

**Tiempo:** 5-10 minutos (solo UNA VEZ)  
**Resultado:** Archivo `~/Documents/Innerpix_Lab/dev_cache/similar_analysis.pkl`

### 2. Cargar y probar (siempre)

```bash
# Prueba que la caché funciona
python scripts/cache_similar_analysis.py load

# O abre directamente el diálogo con los datos cacheados
python scripts/test_similar_dialog_with_cache.py
```

**Tiempo:** < 1 segundo (¡INSTANTÁNEO!)

### 3. Ver información de la caché

```bash
python scripts/cache_similar_analysis.py info
```

## 🔧 Uso en Tu Código

### Opción A: Script de prueba standalone

```python
from pathlib import Path
from services.similar_files_detector import SimilarFilesAnalysis
from ui.dialogs.similar_files_dialog import SimilarFilesDialog

# Cargar análisis desde caché (INSTANTÁNEO)
CACHE_FILE = Path.home() / "Documents" / "Pixaro_Lab" / "dev_cache" / "similar_analysis.pkl"
analysis = SimilarFilesAnalysis.load_from_file(CACHE_FILE)

# Usar con el diálogo
dialog = SimilarFilesDialog(parent=None, analysis=analysis, initial_sensitivity=85)
dialog.show()
```

### Opción B: En tests

```python
import pytest
from pathlib import Path
from services.similar_files_detector import SimilarFilesAnalysis

@pytest.fixture
def large_dataset_analysis():
    """Fixture que carga análisis de 40k archivos instantáneamente"""
    cache_file = Path.home() / "Documents" / "Pixaro_Lab" / "dev_cache" / "similar_analysis.pkl"
    
    if not cache_file.exists():
        pytest.skip("Caché no disponible. Créala con: python scripts/cache_similar_analysis.py create <dir>")
    
    return SimilarFilesAnalysis.load_from_file(cache_file)

def test_dialog_with_large_dataset(large_dataset_analysis):
    """Prueba el diálogo con 40k archivos (carga instantánea)"""
    assert large_dataset_analysis.total_files > 10000
    
    # Probar clustering con diferentes sensibilidades
    result_strict = large_dataset_analysis.get_groups(100)
    result_normal = large_dataset_analysis.get_groups(85)
    result_loose = large_dataset_analysis.get_groups(50)
    
    # Verificar que más sensibilidad = más grupos
    assert result_strict.total_groups >= result_normal.total_groups >= result_loose.total_groups
```

## 📊 Comandos Disponibles

### `create <directorio>`
Analiza un directorio y crea la caché.

```bash
python scripts/cache_similar_analysis.py create /path/to/photos
```

**Salida:**
```
🔍 Analizando directorio: /path/to/photos
⏳ Esto puede tardar varios minutos para datasets grandes...
   Progreso: 100/40234 (0.2%)
   Progreso: 200/40234 (0.5%)
   ...
✅ Análisis completado en 487.3s
   • Archivos analizados: 40,234
   • Hashes calculados: 39,876
💾 Guardando caché en: ~/Documents/Innerpix_Lab/dev_cache/similar_analysis.pkl
✅ ¡Caché creada exitosamente!
```

### `load`
Carga y prueba la caché.

```bash
python scripts/cache_similar_analysis.py load
```

**Salida:**
```
📂 Cargando caché desde: ~/Documents/Innerpix_Lab/dev_cache/similar_analysis.pkl
✅ Caché cargada en 0.843s (¡instantáneo!)
   • Archivos: 40,234
   • Hashes: 39,876
   • Workspace: /path/to/photos
   • Timestamp: 2025-11-24 14:23:45

🧪 Prueba de clustering con diferentes sensibilidades...
   Sens 100%: 523 grupos, 1,046 duplicados (0.234s)
   Sens 85%: 1,234 grupos, 3,456 duplicados (0.287s)
   Sens 50%: 3,456 grupos, 8,901 duplicados (0.421s)

✅ ¡La caché funciona perfectamente!
```

### `info`
Muestra información sobre la caché existente.

```bash
python scripts/cache_similar_analysis.py info
```

**Salida:**
```
📊 Información de caché:
   • Ubicación: ~/Documents/Innerpix_Lab/dev_cache/similar_analysis.pkl
   • Tamaño: 3,456.7 KB
   • Modificado: 2025-11-24 14:23:45
   • Archivos: 40,234
   • Workspace: /path/to/photos
```

## 🚀 Scripts de Prueba

### Test del diálogo completo

```bash
python scripts/test_similar_dialog_with_cache.py
```

Abre el diálogo completo con los datos cacheados. Perfecto para:
- Probar cambios en la UI
- Verificar rendimiento con slider
- Testear paginación
- Debugging visual

### Test de rendimiento (sin UI)

```bash
python scripts/test_similar_dialog_with_cache.py perf
```

Ejecuta benchmarks de clustering con diferentes sensibilidades. Útil para:
- Optimización de algoritmos
- Medir tiempos de respuesta
- Comparar versiones

## 💡 Tips y Mejores Prácticas

### 1. Mantén la caché actualizada
Si cambias el algoritmo de hashing, regenera la caché:
```bash
python scripts/cache_similar_analysis.py create /path/to/photos
```

### 2. Usa diferentes cachés para diferentes datasets
```python
# Renombra o crea múltiples cachés
analysis.save_to_file(Path("~/Documents/Innerpix_Lab/dev_cache/dataset_40k.pkl"))
analysis.save_to_file(Path("~/Documents/Innerpix_Lab/dev_cache/dataset_photos.pkl"))
analysis.save_to_file(Path("~/Documents/Innerpix_Lab/dev_cache/dataset_videos.pkl"))
```

### 3. Git ignore
La caché ya está en `.gitignore` (archivos `.pkl` en `dev_cache/`).

### 4. Comparte con el equipo
Si trabajas en equipo, puedes compartir el archivo de caché:
```bash
# Comprimir para compartir
tar -czf analysis_cache_40k.tar.gz ~/Documents/Innerpix_Lab/dev_cache/similar_analysis.pkl

# Descomprimir en otro equipo
tar -xzf analysis_cache_40k.tar.gz -C ~/Documents/Innerpix_Lab/dev_cache/
```

## 📈 Benchmarks

Tiempos aproximados con dataset de 40k archivos:

| Operación | Tiempo | Comentarios |
|-----------|--------|-------------|
| Análisis completo (primera vez) | ~8 min | Calcula todos los hashes perceptuales |
| Guardar caché | < 1s | Serializa a disco |
| Cargar caché | < 1s | Deserializa desde disco |
| Clustering (sens 85%) | < 0.5s | Solo usa hashes ya calculados |
| Cambiar sensibilidad | < 0.5s | Re-clustering instantáneo |

## 🔍 Estructura de la Caché

La caché guarda:
```python
{
    'perceptual_hashes': {
        '/path/to/photo1.jpg': {
            'hash_str': '8f3e7a12bc45de67',  # String hexadecimal del hash
            'size': 2456789,
            'modified': 1732456789.123
        },
        # ... más archivos
    },
    'workspace_path': '/path/to/photos',
    'total_files': 40234,
    'analysis_timestamp': datetime(2025, 11, 24, 14, 23, 45)
}
```

Formato: `pickle` (binario, rápido)  
Tamaño típico: ~3-5 KB por 1000 archivos

## ❓ FAQ

### ¿La caché funciona si los archivos se mueven?
Sí, pero los paths quedarán obsoletos. Tendrás que regenerar la caché.

### ¿Puedo usar la caché en producción?
**NO**. Esta caché es solo para desarrollo. En producción, siempre analiza en tiempo real.

### ¿Qué pasa si cambio el algoritmo de hashing?
Regenera la caché. Los hashes antiguos no serán compatibles.

### ¿Cuánto espacio ocupa la caché?
Aproximadamente 80-100 bytes por archivo. Para 40k archivos: ~3-4 MB.

## 🎓 Ejemplo Completo: Workflow de Desarrollo

```bash
# DÍA 1: Setup inicial
source .venv/bin/activate
python scripts/cache_similar_analysis.py create ~/Photos/Large_Dataset
# ☕ Espera 8 minutos

# DÍA 2-N: Desarrollo iterativo (cada iteración < 5 segundos)
# 1. Modificas el código del diálogo
# 2. Pruebas instantáneamente:
python scripts/test_similar_dialog_with_cache.py

# 3. Haces cambios
# 4. Vuelves a probar (instantáneo)
python scripts/test_similar_dialog_with_cache.py

# 5. Repites N veces sin esperar ✨
```

## 🚨 Troubleshooting

### Error: "Archivo de caché no encontrado"
```bash
# Verifica que existe
python scripts/cache_similar_analysis.py info

# Si no existe, créala
python scripts/cache_similar_analysis.py create /path/to/photos
```

### Error: "imagehash not installed"
```bash
pip install imagehash
```

### La caché está corrupta
```bash
# Borra y regenera
rm ~/Documents/Innerpix_Lab/dev_cache/similar_analysis.pkl
python scripts/cache_similar_analysis.py create /path/to/photos
```

## 🎉 ¡Listo!

Ahora puedes iterar rápidamente en el desarrollo del diálogo sin esperar análisis largos cada vez. ¡Disfruta del desarrollo ágil! 🚀
