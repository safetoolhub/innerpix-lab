# Funcionalidades de InnerPix Lab

InnerPix Lab es una suite de herramientas diseñada para gestionar, optimizar y organizar colecciones de fotos y vídeos personales. Su filosofía central es la **privacidad absoluta**: todo el análisis y procesamiento se realiza 100% en su computadora. Ningún archivo, metadato ni información personal sale de su dispositivo en ningún momento.

## Compromiso con la Seguridad y Transparencia

Para garantizar la tranquilidad del usuario, la aplicación incorpora mecanismos de seguridad robustos en todas sus operaciones:

### 🛡️ Copia de Seguridad Automática (Backup)
Antes de realizar cualquier operación que implique eliminar o modificar archivos, InnerPix Lab crea automáticamente una copia de seguridad. Los archivos originales no se borran inmediatamente, sino que se mueven a una carpeta de seguridad predefinida. Esto permite revertir cualquier cambio no deseado y recuperar archivos "eliminados" con total facilidad.

### 📝 Registro de Operaciones (Logs)
La transparencia es fundamental. Todas las acciones realizadas por la aplicación quedan registradas en un historial de operaciones (logs). Usted puede consultar exactamente qué archivos fueron analizados, movidos o eliminados, cuándo ocurrió y por qué motivo.

### 👁️ Modo Simulación (Dry-Run)
Para mayor seguridad, todas las herramientas incluyen un modo de simulación. Puede ejecutar cualquier proceso de limpieza u organización en modo "prueba" para ver qué resultaría, sin modificar ni un solo archivo en realidad.

---

## Herramientas Principales

InnerPix Lab pone a su disposición 8 herramientas especializadas, organizadas según su función:

### 1. Limpieza de Archivos Vacíos
Escanea sus carpetas en busca de "archivos fantasma" (archivos de 0 bytes) que no contienen información pero ensucian su sistema de archivos, y le permite eliminarlos de forma segura.

### 2. Optimización HEIC/JPG
Encuentra casos donde tiene la misma fotografía guardada en dos formatos: el moderno y eficiente HEIC y el tradicional JPG. La herramienta le ayuda a identificar estos duplicados de formato y eliminar las versiones redundantes para liberar espacio sin perder sus recuerdos.

### 3. Limpieza de Live Photos
Gestiona inteligentemente las "Live Photos" (que constan de una imagen y un video clip). Detecta estos pares y le permite decidir si desea conservar ambos, o limpiar el componente de video para ahorrar espacio si solo le interesa la fotografía estática.

### 4. Detección de Duplicados Exactos
Analiza su colección byte por byte para encontrar archivos que son matemáticamente idénticos. Es la forma más segura de limpieza, ya que garantiza que no está borrando una foto "parecida", sino exactamente el mismo archivo repetido en diferentes carpetas.

### 5. Copias Visualmente Idénticas
Identifica imágenes que son visualmente indistinguibles para el ojo humano, aunque técnicamente sean archivos diferentes (por ejemplo, una copia descargada de internet vs la original, o la misma foto guardada con diferente metadata). Ideal para limpiar su galería de repeticiones innecesarias.

### 6. Archivos Similares
Detecta fotos y vídeos que son muy parecidos pero no idénticos. Esto es perfecto para:
- Seleccionar la mejor toma de una ráfaga de fotos.
- Eliminar versiones ligeramente editadas o recortadas que ya no necesita.
- Detectar copias de baja resolución.

### 7. Organización Inteligente
Pone orden en el caos. Esta herramienta analiza sus archivos y propone una nueva estructura de carpetas organizada lógicamente (por ejemplo, por Año/Mes), permitiéndole reubicar miles de fotos con un solo clic y mantener su biblioteca impecable.

### 8. Renombrado Masivo
Estandarice los nombres de sus archivos de forma profesional. Puede cambiar nombres crípticos como `IMG_8823.JPG` a formatos útiles y legibles como `20241231_112300_PHOTO.jpg`, utilizando fechas y secuencias automáticas para evitar conflictos.
