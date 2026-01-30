innerpix Lab actualmente utiliza diferentes nombres y descripciones para las mismas herramientas en distintas partes del código. Vamos a unificar todas las definiciones para lograr coherencia y facilitar la futura internacionalización (i18n).

### Objetivo del refactor

Reestructurar las definiciones de las 8 herramientas ("tools") para que:

- Todas tengan una estructura homogénea con **3 campos**:
**Título**, **Descripción corta**, y **Descripción larga**.
- Esas definiciones se usen **de forma centralizada** en el código (por ejemplo, importándolas desde un único módulo o JSON).
- Preparar el código para una futura localización multilingüe (separar texto estático de la lógica).


### Herramientas y textos oficiales

1. **Archivos vacíos**
    - Descripción corta: Estos archivos ocupan 0 bytes y no contienen información. Es 100% seguro eliminarlos
    - Descripción larga: Escanea sus carpetas en busca de "archivos fantasma" (archivos de 0 bytes) que no contienen datos útiles. Elimínalos de forma segura.
2. **Duplicados HEIC/JPG**
    - Descripción corta: Fotos HEIC con versiones JPG idénticas. Elige qué formato conservar y libera espacio
    - Descripción larga: Encuentra casos donde tienes la misma fotografía en dos formatos: HEIC (usado por iPhones) y el tradicional JPG. La herramienta le ayuda a identificar estos duplicados y eliminar las versiones redundantes para liberar espacio.
3. **Live Photos**
    - Descripción corta: Live Photos de iPhone (Imagen + MOV). Los videos MOV serán eliminados para liberar espacio
    - Descripción larga: Las Live Photos de iPhone constan de una imagen y vídeo corto. Esta herramienta detecta estos pares y te permite decidir si deseas conservar ambos, o limpiar el componente de video para ahorrar espacio si solo te interesa la fotografía estática.
4. **Copias Exactas**
    - Descripción corta: Archivos 100% idénticos aunque tengan nombres diferentes. Es totalmente seguro borrarlos
    - Descripción larga: Analiza tu colección para encontrar archivos que son matemáticamente idénticos. Es la forma más segura de limpieza, ya que garantiza que no estás borrando una foto "parecida", sino exactamente el mismo archivo repetido en diferentes carpetas (aunque tenga distinto nombre).
5. **Copias visualmente idénticas**
    - Descripción corta: Archivos visualmente idénticos, pero con diferentes datos internos. Sucede en fotos enviadas por WhatsApp o redimensionadas.
    - Descripción larga: Identifica imágenes que son visualmente indistinguibles para el ojo humano, aunque técnicamente sean archivos diferentes (por ejemplo, una copia descargada de internet, o la misma foto guardada en diferentes fechas). Ideal para eliminar copias de WhatsApp, screenshots repetidos o imágenes redimensionadas.
6. **Archivos similares**
    - Descripción corta: Detecta imágenes similares pero no iguales (ediciones, recortes, distinta resolución...)
    - Descripción larga: Detecta fotos y vídeos que son muy parecidos pero no idénticos. Esto es perfecto para:
        - Seleccionar la mejor toma de una ráfaga de fotos.
        - Eliminar versiones ligeramente editadas o recortadas que ya no necesita.
        - Detectar copias de baja resolución.
7. **Organización inteligente**
    - Descripción corta: Organiza las imágenes y videos en una nueva estructura de carpetas
    - Descripción larga: Esta herramienta analiza tus archivos y propone una nueva estructura de carpetas organizada lógicamente (por ejemplo, por Año/Mes), permitiéndo reubicar miles de fotos con un solo clic y mantener la biblioteca impecable.
8. **Renombrado completo**
    - Descripción corta: Los archivos se renombrarán al formato YYYY-MM-DD_HH-MM-SS_<PHOTO|VIDEO> usando su fecha de creación
    - Descripción larga: Estandariza los nombres de tus archivos de forma profesional. Puedes cambiar nombres crípticos como `IMG_8823.JPG` a formatos útiles y legibles como `20241231_112300_PHOTO.jpg`, utilizando fechas y secuencias automáticas para evitar conflictos de nombres.

### Lugares de uso en la aplicación

Asegúrate de reemplazar los textos actuales y usar las nuevas definiciones unificadas en los siguientes lugares:

- **`About_dialog` → sección “Herramientas”**
Usar: **Título** + **Descripción larga**
- **`stage_3_window` → tarjetas dentro de `tools_cards`**
(`zero_byte_card.py`, `file_renamer_card.py`, etc.)
Usar: **Título** + **Descripción larga**
- **Encabezados de los diálogos (`header_frame` dentro de `/dialogs/`)**
(`zero_byte_dialog.py`, `file_organizer_dialog.py`, etc.)
Usar: **Título** + **Descripción corta** en los campos `title` y `description`.
- **Mensajes del `stage_3_window` al finalizar una herramienta**
(“Actualización de estadísticas”, “Estadísticas actualizadas”, etc.): usar **Título**.
- **`Project_funcionalities.md`**
Usar: **Título** + **Descripción larga**.
- **Actualizar también:**
`copilot-instructions.md` y `agents.md` para reflejar los nuevos nombres y descripciones.
- **Cualquier otra referencia en el código** a los nombres o descripciones de las herramientas.


### Indicaciones adicionales

- Centralizar las definiciones en un archivo maestro (por ejemplo, `tools_definitions.py`). Puedes pensar donde sería mejor tú. 
- Preparar la estructura para internacionalización, dejando listo el soporte multilenguaje.
- Asegurarse de no duplicar texto en el código: todas las referencias deben venir de la fuente única.
