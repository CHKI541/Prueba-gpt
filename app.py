import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    Root = TkinterDnD.Tk
    HAS_DND = True
except Exception:
    Root, HAS_DND = tk.Tk, False

BG, PANEL, TEXT, MUTED, ACCENT, GREEN = "#101522", "#1a2233", "#edf2ff", "#9ba9c4", "#7c9cff", "#55d6a7"
MAX_BYTES = 25_000_000
TARGET_BYTES = 23_500_000


def resource_path(name):
    return str(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name)


def unique_path(path):
    """Return a non-existing output path without overwriting user data."""
    path = Path(path)
    if not path.exists():
        return path
    for n in range(2, 10000):
        candidate = path.with_name(f"{path.stem}_{n}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError("Hay demasiados archivos con el mismo nombre en la carpeta.")


def run_hidden(command, timeout=7200):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=timeout,
    )


def self_test():
    import tkinterdnd2
    for exe in ("ffmpeg.exe", "ffprobe.exe"):
        result = run_hidden([resource_path(exe), "-version"], timeout=30)
        if result.returncode:
            raise RuntimeError(f"Fallo {exe}: {result.stderr}")
    return 0


class App:
    def __init__(self):
        self.root = Root()
        self.root.title("MediaPocket")
        self.root.geometry("560x540")
        self.root.minsize(500, 500)
        self.root.configure(bg=BG)
        self.source, self.busy, self.closing = None, False, False
        self.ffmpeg = resource_path("ffmpeg.exe")
        self.ffprobe = resource_path("ffprobe.exe")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.ui()

    def ui(self):
        tk.Label(self.root, text="MediaPocket", bg=BG, fg=TEXT, font=("Segoe UI", 23, "bold")).pack(anchor="w", padx=28, pady=(24, 2))
        tk.Label(self.root, text="Tus archivos multimedia, en unos clics.", bg=BG, fg=MUTED).pack(anchor="w", padx=30)
        self.drop = tk.Frame(self.root, bg=PANEL, highlightbackground="#35425e", highlightthickness=1)
        self.drop.pack(fill="x", padx=26, pady=22, ipady=24)
        self.file_label = tk.Label(self.drop, text="↓  Arrastra aquí un audio o video\n\nO pulsa para elegir un archivo", bg=PANEL, fg=TEXT, font=("Segoe UI", 12), justify="center", cursor="hand2")
        self.file_label.pack(fill="both", expand=True, padx=12, pady=14)
        for w in (self.drop, self.file_label):
            w.bind("<Button-1>", lambda e: self.pick())
        if HAS_DND:
            for w in (self.drop, self.file_label):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self.on_drop)
        else:
            self.file_label.configure(text="Pulsa para elegir un archivo\n(Arrastrar y soltar no disponible)")
        actions = tk.Frame(self.root, bg=BG)
        actions.pack(fill="x", padx=26)
        for label, fn, color in [
            ("♫   Convertir a MP3", self.convert_mp3, ACCENT),
            ("⇩   Comprimir para mensajería (< 25 MB)", self.compress, "#34415c"),
            ("▣   Extraer primer fotograma", self.frame, "#34415c"),
        ]:
            tk.Button(actions, text=label, command=fn, bg=color, fg=TEXT, activebackground=ACCENT, relief="flat", bd=0, font=("Segoe UI", 11, "bold"), cursor="hand2").pack(fill="x", pady=5, ipady=8)
        self.status = tk.StringVar(value="Listo · Selecciona un archivo para comenzar")
        tk.Label(self.root, textvariable=self.status, bg=BG, fg=GREEN, wraplength=490, justify="left").pack(anchor="w", padx=29, pady=(17, 5))
        tk.Label(self.root, text="Procesamiento local · Tus archivos no se suben a internet", bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(pady=(12, 12))

    def pick(self):
        p = filedialog.askopenfilename(
            title="Elegir archivo multimedia",
            filetypes=[("Multimedia", "*.mp4 *.mkv *.mov *.avi *.webm *.mp3 *.wav *.m4a *.aac *.flac *.ogg"), ("Todos", "*.*")],
        )
        if p:
            self.set_file(p)

    def on_drop(self, event):
        try:
            # Tk's splitlist handles quoted/braced paths with spaces and literal braces.
            paths = self.root.tk.splitlist(event.data)
            if paths:
                self.set_file(paths[0])
        except Exception:
            self.status.set("No pude leer ese archivo. Prueba con el selector.")

    def set_file(self, path):
        p = Path(path)
        if not p.is_file():
            self.status.set("El archivo seleccionado no existe.")
            return
        self.source = str(p)
        self.file_label.configure(text=f"✓  {p.name}\n\nArchivo listo para procesar", fg=GREEN)
        self.status.set(f"Seleccionado · {p.stat().st_size / 1_000_000:.1f} MB")

    def start(self, mode):
        if self.busy:
            return
        if not self.source:
            messagebox.showinfo("Falta un archivo", "Primero arrastra o selecciona un archivo.")
            return
        if not Path(self.ffmpeg).is_file() or (mode == "compress" and not Path(self.ffprobe).is_file()):
            messagebox.showerror("Faltan herramientas", "No se encontraron las herramientas multimedia incluidas. Descarga la versión portable del repositorio.")
            return
        src = Path(self.source)
        if mode == "mp3":
            out = unique_path(src.with_name(src.stem + "_audio.mp3"))
        elif mode == "frame":
            out = unique_path(src.with_name(src.stem + "_fotograma.jpg"))
        else:
            out = unique_path(src.with_name(src.stem + "_compacto.mp4"))
        self.busy = True
        self.status.set("Procesando… puede tardar según el tamaño.")
        threading.Thread(target=self.worker, args=(src, out, mode), daemon=True).start()

    def compress_to_limit(self, src, out):
        probe = run_hidden([
            self.ffprobe, "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(src),
        ], timeout=60)
        if probe.returncode:
            raise RuntimeError("No pude determinar la duración del video. Comprueba que sea un archivo válido.")
        try:
            duration = float(probe.stdout.strip().splitlines()[0])
        except (ValueError, IndexError):
            raise RuntimeError("El video no informa una duración válida.")
        if duration <= 0:
            raise RuntimeError("La duración del video debe ser mayor que cero.")

        temp = out.with_name(out.stem + ".working" + out.suffix)
        # Start conservatively, then reduce the video bitrate/resolution if necessary.
        audio_kbps = 64
        budget_kbps = max(48, int((TARGET_BYTES * 8 / duration / 1000) * 0.88) - audio_kbps)
        attempts = [(1280, max(48, int(budget_kbps * (0.78 ** i)))) for i in range(6)]
        attempts += [(960, max(32, int(budget_kbps * (0.62 ** i)))) for i in range(1, 5)]
        attempts += [(640, max(24, int(budget_kbps * (0.48 ** i)))) for i in range(1, 4)]
        last_error = ""
        try:
            for width, video_kbps in attempts:
                try:
                    temp.unlink(missing_ok=True)
                    args = [
                        self.ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
                        "-i", str(src), "-vf", f"scale='min({width},iw)':-2",
                        "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{video_kbps}k",
                        "-maxrate", f"{video_kbps}k", "-bufsize", f"{video_kbps * 2}k",
                        "-c:a", "aac", "-b:a", f"{audio_kbps}k", "-movflags", "+faststart",
                        str(temp),
                    ]
                    result = run_hidden(args)
                    if result.returncode:
                        last_error = (result.stderr or "FFmpeg no pudo codificar.")[-900:]
                        continue
                    if temp.is_file() and 0 < temp.stat().st_size < MAX_BYTES:
                        # The destination was reserved as a unique name before processing.
                        temp.replace(out)
                        return
                except OSError as exc:
                    last_error = str(exc)
            raise RuntimeError(
                "No se pudo reducir el archivo por debajo de 25 MB tras varios intentos. "
                "Puede ser demasiado largo para el límite solicitado. " + last_error
            )
        finally:
            temp.unlink(missing_ok=True)

    def worker(self, src, out, mode):
        try:
            if mode == "compress":
                self.compress_to_limit(src, out)
            else:
                if mode == "mp3":
                    args = ["-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-i", str(src), "-vn", "-codec:a", "libmp3lame", "-q:a", "2", str(out)]
                else:
                    # No seek offset: FFmpeg extracts the first decodable video frame, even for sub-second clips.
                    args = ["-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-i", str(src), "-frames:v", "1", "-q:v", "2", str(out)]
                result = run_hidden([self.ffmpeg, *args])
                if result.returncode:
                    raise RuntimeError((result.stderr or "FFmpeg no pudo procesar el archivo.")[-1200:])
            if not out.is_file() or not out.stat().st_size:
                raise RuntimeError("La salida no se creó correctamente.")
            size = out.stat().st_size / 1_000_000
            self.root.after(0, lambda: self.finish(True, f"Terminado · {out.name} ({size:.1f} MB)", out))
        except Exception as exc:
            msg = str(exc)
            try:
                self.root.after(0, lambda m=msg: self.finish(False, "No se pudo completar: " + m))
            except tk.TclError:
                pass

    def finish(self, ok, msg, output=None):
        if self.closing:
            return
        self.busy = False
        self.status.set(msg)
        if ok and messagebox.askyesno("¡Listo!", "Archivo creado. ¿Abrir carpeta?"):
            os.startfile(str(output.parent))
        elif not ok:
            messagebox.showerror("Error de procesamiento", msg)

    def close(self):
        self.closing = True
        self.root.destroy()

    def convert_mp3(self):
        self.start("mp3")

    def compress(self):
        self.start("compress")

    def frame(self):
        self.start("frame")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    App().run()
