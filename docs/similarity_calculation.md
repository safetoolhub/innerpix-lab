# Cálculo de Similitud en Grupos

Este documento explica cómo se calcula el porcentaje de similitud cuando un grupo contiene más de dos imágenes en el servicio de duplicados similares.

## Metodología: El enfoque del "Pivote"

En lugar de realizar comparaciones cruzadas exhaustivas entre todos los miembros del grupo (lo cual sería ineficiente), el sistema utiliza un modelo basado en un **pivote central**.

### 1. Identificación del Pivote
Durante el proceso de clustering, la primera imagen que se encuentra y que no pertenece a ningún grupo existente se convierte en el **pivote** (o raíz). Todas las imágenes subsiguientes encontradas mediante la búsqueda en el **BK-Tree** que estén dentro del umbral de distancia se añaden a este grupo.

### 2. Cálculo de la Distancia Media
El porcentaje de similitud que se muestra en la interfaz para el grupo completo se calcula basándose en la **Distancia de Hamming promedio** de todos los miembros comparados específicamente contra el pivote:

```python
# 'hamming_distances' contiene la distancia de cada miembro respecto al pivote
avg_hamming = sum(hamming_distances) / len(hamming_distances)
```

### 3. Conversión a Porcentaje
Para transformar esta distancia técnica en un valor legible por el usuario, se utiliza la longitud total del hash perceptual (64 bits):

```python
max_theoretical_dist = 64
similarity_percentage = 100 - (avg_hamming / max_theoretical_dist * 100)
```

## Resumen de Implicaciones

- **Representatividad**: El porcentaje indica qué tan similares son, en promedio, los miembros del grupo **respecto a la imagen original del grupo**.
- **Eficiencia**: Este método permite filtrar miles de imágenes en milisegundos, ya que aprovecha las distancias ya calculadas durante la fase de búsqueda en el árbol BK-Tree.
- **Consistencia**: Al usar el promedio, se evita que una sola imagen ligeramente distinta degrade excesivamente la puntuación del grupo, manteniendo una representación equilibrada de la calidad del "match".
