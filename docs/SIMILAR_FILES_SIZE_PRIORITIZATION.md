# Priorización de Grupos por Diferencia de Tamaño - Archivos Similares

## Cambios Implementados

Se ha modificado el servicio `duplicates_similar_service.py` para que los grupos de imágenes similares se muestren ordenados priorizando aquellos que tienen mayor diferencia de tamaño entre archivos.

### Motivación

Las imágenes que son idénticas excepto por su tamaño suelen ser la misma foto en diferentes calidades:
- **Fotos originales**: Alta calidad, mayor tamaño (ej. 900 KB)
- **Fotos de WhatsApp**: Compresión automática, menor tamaño (ej. 400 KB)
- **Fotos de email**: Compresión para adjuntos, tamaño reducido

Estas son las más candidatas a ser eliminadas, ya que el usuario probablemente quiera conservar la versión de mayor calidad.

### Implementación

Se agregó al método `_cluster_by_similarity` en `DuplicatesSimilarService`:

1. **Función de score**: `calculate_size_variation_score(group)`
   - Calcula la diferencia porcentual entre el archivo más grande y el más pequeño
   - Retorna 100+ puntos si la diferencia es >50%
   - Retorna el porcentaje de diferencia en caso contrario

2. **Ordenación**: Los grupos se ordenan de mayor a menor score
   - Primero aparecen grupos con diferencia >50%
   - Luego grupos con menor diferencia
   - Finalmente grupos con tamaños similares

3. **Logging**: Se registra cuántos grupos tienen diferencia >50%
   ```
   📊 Grupos con diferencia de tamaño >50%: 15/47
   ```

### Ejemplo

**Antes** (orden aleatorio):
```
Grupo 1: img_001.jpg (2.1 MB), img_002.jpg (2.0 MB)  → Diferencia: 5%
Grupo 2: IMG_20230615.jpg (4.5 MB), WhatsApp_Image.jpg (1.2 MB)  → Diferencia: 275%
Grupo 3: photo.jpg (800 KB), photo_copy.jpg (795 KB)  → Diferencia: 0.6%
```

**Después** (ordenado por prioridad):
```
Grupo 1: IMG_20230615.jpg (4.5 MB), WhatsApp_Image.jpg (1.2 MB)  → Diferencia: 275% ⭐
Grupo 2: img_001.jpg (2.1 MB), img_002.jpg (2.0 MB)  → Diferencia: 5%
Grupo 3: photo.jpg (800 KB), photo_copy.jpg (795 KB)  → Diferencia: 0.6%
```

### Impacto en UI

El diálogo `duplicates_similar_dialog.py` mostrará automáticamente los grupos en este nuevo orden, permitiendo al usuario revisar primero los casos más evidentes de duplicación con diferentes calidades.

### Tests

Todos los tests existentes pasan correctamente:
```bash
pytest tests/unit/services/test_duplicates_similar_service.py -v
# ============ 10 passed in 0.09s ============
```

### Notas

- El cambio NO afecta el clustering en sí, solo la ordenación final
- No hay impacto en el rendimiento (ordenación es O(n log n) con n = número de grupos)
- Compatible con carga incremental y ajuste de sensibilidad en tiempo real
