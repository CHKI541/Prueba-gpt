# MediaPocket

Aplicación ligera para Windows: convierte audio a MP3, comprime videos para mensajería y extrae un fotograma. El procesamiento es local.

## Descargar

Abre **Actions → Build MediaPocket for Windows → último workflow exitoso → Artifacts → MediaPocket-Windows-x64**. Descomprime el ZIP y ejecuta MediaPocket.exe con doble clic. No requiere instalar Python ni FFmpeg.

El ejecutable estará disponible después de que GitHub Actions termine correctamente.

## Uso

1. Arrastra un archivo al recuadro o haz clic para buscarlo.
2. Elige una de las tres acciones.
3. La salida se guarda junto al original.

La compresión usa H.264/AAC y verifica el límite de 25 MiB. No puede garantizar que cualquier video largo quepa; si excede el límite, informa el problema. El fotograma se extrae en el segundo 1.

## Desarrollo

Python 3.12. Instala dependencias con pip install -r requirements.txt y ejecuta python app.py. Para desarrollo, coloca ffmpeg.exe junto a app.py o en PATH.

El workflow de GitHub Actions construye el ejecutable portable x64 con PyInstaller. FFmpeg se distribuye sujeto a su licencia y a la licencia del build descargado.

## Alcance inicial

Windows 10/11 x64. Esta versión no incluye porcentaje de progreso ni cancelación. La compresión de archivos arbitrariamente largos requiere ajustar duración/resolución manualmente.
