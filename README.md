# MediaPocket

Aplicación portable para Windows x64 que convierte audio a MP3, intenta comprimir videos por debajo de 25 MB y extrae el primer fotograma decodificable. El procesamiento ocurre localmente; no se suben archivos.

## Descargar

Abre [Actions del repositorio](https://github.com/CHKI541/Prueba-gpt/actions), entra al workflow **Build MediaPocket for Windows**, elige la ejecución más reciente que haya terminado correctamente y descarga el artifact **MediaPocket-Windows-x64**. Descomprime el ZIP y ejecuta MediaPocket.exe con doble clic. No requiere instalar Python ni FFmpeg.

El artifact incluye el ejecutable y el aviso de licencia de FFmpeg. Antes de redistribuir el programa, revisa las condiciones del build de FFmpeg y las obligaciones de licencia aplicables.

## Uso

1. Arrastra un archivo al recuadro o haz clic para seleccionarlo.
2. Elige convertir a MP3, comprimir o extraer fotograma.
3. La salida se guarda junto al original. Si el nombre ya existe, se añade un sufijo numérico; no se sobrescribe el archivo anterior.

## Límite de compresión

La aplicación busca un resultado menor que **25.000.000 bytes (25 MB decimales)**. Consulta la duración y reintenta con varios bitrates y resoluciones. Videos muy largos, con contenido complejo o sin pista de video compatible podrían no alcanzar el límite; en ese caso informa que no pudo hacerlo, sin reemplazar el original. El tamaño final puede variar por el contenedor y la codificación.

El fotograma corresponde al primer fotograma de video que FFmpeg pueda decodificar, por lo que también contempla clips de menos de un segundo.

## Pruebas y alcance

El workflow de GitHub Actions construye el EXE e incluye un smoke test que comprueba que el ejecutable empaquetado puede importar tkinterdnd2 y ejecutar las versiones empaquetadas de FFmpeg y ffprobe. Esto no sustituye una prueba manual de la interfaz gráfica, el arrastre real desde el Explorador de Windows ni conversiones con una colección amplia de archivos.

Windows 10/11 x64. La versión inicial no incluye barra de progreso ni cancelación. Para desarrollo: Python 3.12, `pip install -r requirements.txt`, y FFmpeg/ffprobe junto a `app.py`; luego `python app.py`.
