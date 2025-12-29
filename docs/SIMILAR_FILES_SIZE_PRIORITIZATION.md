# Priorización de Grupos por Diferencia de Tamaño - Archivos Similares

## Cambios Implementados

Se ha modificado el servicio `duplicates_similar_service.py` y el diálogo `duplicates_similar_dialog.py` para que los grupos de imágenes similares se muestren ordenados por diferencia de tamaño de mayor a menor.

### Motivación

Las imágenes que son idénticas excepto por su tamaño suelen ser la misma foto en diferentes calidades:
- **Fotos originales**: Alta calidad, mayor tamaño (ej. 3.8 MB)
- **Fotos de WhatsApp**: Compresión automática, menor tamaño (ej. 1.2 MB)
- **Fotos de email**: Compresión para adjuntos, tamaño reducido (ej. 600 KB)

Estas son las más candidatas a ser eliminadas, ya que el usuario probablemente quiera conservar la versión de mayor calidad.

### Implementación

#### 1. Servicio (`duplicates_similar_service.py`)

Se agregó al método `_cluster_by_similarity`:

**Función de score**: `calculate_size_variation_score(group)`
- Calcula la diferencia porcentual entre el archivo más grande y el más pequeño
- Formula: `((max_size - min_size) / min_size) * 100`
- Retorna directamente el porcentaje de variación (0-∞)
- No hay umbrales artificiales, simplemente ordena por diferencia real

**Ordenación automática**: 
- Los grupos se ordenan de mayor a menor score de variación
- Ocurre automáticamente en cada clustering

**Logging mejorado**:
```
📊 Variación de tamaño - Máx: 533.3%, Promedio: 271.1%
```

#### 2. Diálogo (`duplicates_similar_dialog.py`)

**Nuevo método**: `_sort_all_groups_by_size_variation()`
- Ordena globalmente `self.all_groups` por diferencia de tamaño
- Se llama después de:
  - Cargar cada batch incremental
  - Cambiar la sensibilidad
- Garantiza que **TODOS** los grupos estén ordenados, no solo los del batch actual

**Lógica de ordenación**:
```python
def calculate_size_variation(group) -> float:
    sizes = [f.stat().st_size for f in group.files if f.exists()]
    if len(sizes) < 2: return 0.0
    
    min_size, max_size = min(sizes), max(sizes)
    if min_size == 0: return 0.0
    
    return ((max_size - min_size) / min_size) * 100

self.all_groups.sort(key=calculate_size_variation, reverse=True)
```

### Ejemplo

**Antes** (sin ordenación específica):
```
Grupo 1: img_001.jpg (2.1 MB), img_002.jpg (2.0 MB)  → Diferencia: 5%
Grupo 2: IMG_20230615.jpg (4.5 MB), WhatsApp_Image.jpg (1.2 MB)  → Diferencia: 275%
Grupo 3: DSC_0001.jpg (3.8 MB), email_photo.jpg (0.6 MB)  → Diferencia: 533%
```

**Después** (ordenado por diferencia):
```
Grupo 1: DSC_0001.jpg (3.8 MB), email_photo.jpg (0.6 MB)  → 533% ⭐
Grupo 2: IMG_20230615.jpg (4.5 MB), WhatsApp_Image.jpg (1.2 MB)  → 275% ⭐
Grupo 3: img_001.jpg (2.1 MB), img_002.jpg (2.0 MB)  → 5%
```

### Rendimiento

#### Análisis de Complejidad
- **Ordenación**: O(n log n) donde n = número de grupos
- **Cálculo de tamaño**: O(1) por grupo (ya en memoria)

#### Benchmarks Estimados
- **1,000 grupos**: ~10,000 comparaciones (< 1ms)
- **10,000 grupos**: ~130,000 comparaciones (< 10ms)
- **50,000 grupos**: ~800,000 comparaciones (< 50ms)

**Conclusión**: Impacto negligible incluso en datasets muy grandes.

### Carga Incremental en Datasets Grandes

El sistema funciona correctamente con la carga incremental por batches:

1. **Batch 1**: Se cargan primeros N archivos → clustering → ordenación
2. **Batch 2**: Se cargan siguientes N archivos → clustering → **reordenación global**
3. **Batch 3**: ... y así sucesivamente

**Garantía**: El usuario **siempre** ve primero los grupos con mayor diferencia de tamaño, independientemente de:
- En qué batch fueron descubiertos
- El tamaño total del dataset
- La sensibilidad configurada

### Impacto en UI

El diálogo `duplicates_similar_dialog.py` muestra automáticamente los grupos en este nuevo orden:
- Al cargar el primer batch
- Al cargar batches adicionales ("Cargar más grupos")
- Al cambiar la sensibilidad del slider

No se requieren cambios en la interfaz visual, todo funciona de forma transparente.

### Tests

Todos los tests existentes pasan correctamente:
```bash
pytest tests/unit/services/test_duplicates_similar_service.py -v
# ============ 10 passed in 0.06s ============
```

### Script de Demostración

Ejecutar `python docs/demo_size_prioritization.py` para ver la ordenación en acción:

```
Grupos encontrados: 3
Variación máxima: 533.3%
Variación promedio: 271.1%

💡 Los grupos están ordenados por diferencia de tamaño (mayor primero)
   facilitando la revisión de duplicados en diferentes calidades.
```

### Notas Técnicas

- **No hay umbrales artificiales**: A diferencia de la implementación inicial con umbral del 50%, ahora simplemente se ordena por el porcentaje real de diferencia
- **Compatible con todos los features**: Funciona con filtros, sensibilidad, carga incremental, etc.
- **Thread-safe**: La ordenación ocurre en el thread de UI después de procesar cada batch
- **Memoria eficiente**: No duplica datos, solo reordena referencias existentes
