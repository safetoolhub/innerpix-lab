# Funcionalidades de InnerPix Lab

InnerPix Lab es una aplicación para analizar, previsualizar y ejecutar acciones sobre colecciones de imágenes y vídeos (principalmente orientada a fotos iOS), con un enfoque orientado a la privacidad.
Ofrece al usuario 7 servicios principales; cada una se presenta mediante un diálogo (Dialog) específico en la interfaz para permitir la vista previa de los cambios y opciones de ejecución (por ejemplo, creación de backup antes de operaciones destructivas y simulación de la operación (dry-run) sin eliminar ni mover nada realmente).

1. **Limpieza de Live Photos**
   - **Descripción**: Detecta pares foto+vídeo que forman Live Photos y ofrece opciones para limpiar, separar o eliminar el componente de vídeo asociado cuando procede. Facilita mantener sólo el elemento deseado y ahorrar espacio.
   - **Dialog asociado**: `ui/dialogs/live_photos_dialog.py`

2. **Eliminación de duplicados HEIC/JPG**
   - **Descripción**: Busca pares HEIC/JPG que son duplicados del mismo contenido (mismas fotos en formatos distintos) y propone eliminar o conservar según políticas (ej. conservar JPG/HEIC, por tamaño, fecha).
   - **Dialog asociado**: `ui/dialogs/heic_dialog.py`

3. **Detección de copias exactas**
   - **Descripción**: Encuentra archivos idénticos byte-a-byte mediante hashing. Permite revisar los pares/grupos detectados y elegir qué conservar o eliminar.
   - **Dialog asociado**: `ui/dialogs/duplicates_exact_dialog.py`

4. **Detección de archivos similares**
   - **Descripción**: Detecta imágenes o videos visualmente similares (mismo contenido con pequeñas variaciones: recorte, rotación, compresión). Ofrece herramientas para comparar y decidir qué mantener.
   - **Dialog asociado**: `ui/dialogs/duplicates_similar_dialog.py`
   - **Dialog asociado para analisis previo**: `ui/dialogs/duplicates_similar_progress_dialog.py`

5. **Organización de archivos**
   - **Descripción**: Genera planes para reorganizar la colección (por fecha, por carpeta raíz, por origen como WhatsApp, etc.), mostrando la estructura propuesta antes de mover archivos.
   - **Dialog asociado**: `ui/dialogs/file_organizer_dialog.py`

6. **Renombrado de archivos**
   - **Descripción**: Propone esquemas de renombrado (patrones con fecha, secuencias, metadatos) y muestra una vista previa de los nombres resultantes, detectando conflictos y proponiendo resoluciones.
   - **Dialog asociado**: `ui/dialogs/file_renamer_dialog.py`

7. **Eliminación de archivos de 0 bytes**
   - **Descripción**: Busca archivos con tamaño 0 bytes y propone su eliminación.
   - **Dialog asociado**: `ui/dialogs/zero_byte_dialog.py`
