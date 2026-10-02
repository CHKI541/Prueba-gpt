import os, sys, subprocess, threading, tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    Root = TkinterDnD.Tk
    HAS_DND = True
except Exception:
    Root, HAS_DND = tk.Tk, False

BG, PANEL, TEXT, MUTED, ACCENT, GREEN = "#101522", "#1a2233", "#edf2ff", "#9ba9c4", "#7c9cff", "#55d6a7"
def resource_path(name):
    return str(Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name)

class App:
    def __init__(self):
        self.root = Root()
        self.root.title("MediaPocket")
        self.root.geometry("560x540")
        self.root.minsize(500, 500)
        self.root.configure(bg=BG)
        self.source, self.busy = None, False
        self.ffmpeg = resource_path("ffmpeg.exe")
        self.ui()

    def ui(self):
        tk.Label(self.root, text="MediaPocket", bg=BG, fg=TEXT, font=("Segoe UI", 23, "bold")).pack(anchor="w", padx=28, pady=(24, 2))
        tk.Label(self.root, text="Tus archivos multimedia, en unos clics.", bg=BG, fg=MUTED).pack(anchor="w", padx=30)
        self.drop = tk.Frame(self.root, bg=PANEL, highlightbackground="#35425e", highlightthickness=1)
        self.drop.pack(fill="x", padx=26, pady=22, ipady=24)
        self.file_label = tk.Label(self.drop, text="↓  Arrastra aquí un audio o video\n\nO pulsa para elegir un archivo", bg=PANEL, fg=TEXT, font=("Segoe UI", 12), justify="center", cursor="hand2")
        self.file_label.pack(fill="both", expand=True, padx=12, pady=14)
        for w in (self.drop, self.file_label): w.bind("<Button-1>", lambda e: self.pick())
        if HAS_DND:
            for w in (self.drop, self.file_label):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self.on_drop)
        else: self.file_label.configure(text="Pulsa para elegir un archivo\n(Arrastrar y soltar no disponible)")
        actions = tk.Frame(self.root, bg=BG); actions.pack(fill="x", padx=26)
        for label, fn, color in [("♫   Convertir a MP3", self.convert_mp3, ACCENT), ("⇩   Comprimir para mensajería (< 25 MB)", self.compress, "#34415c"), ("▣   Extraer fotograma", self.frame, "#34415c")]:
            tk.Button(actions, text=label, command=fn, bg=color, fg=TEXT, activebackground=ACCENT, relief="flat", bd=0, font=("Segoe UI", 11, "bold"), cursor="hand2").pack(fill="x", pady=5, ipady=8)
        self.status = tk.StringVar(value="Listo · Selecciona un archivo para comenzar")
        tk.Label(self.root, textvariable=self.status, bg=BG, fg=GREEN, wraplength=490, justify="left").pack(anchor="w", padx=29, pady=(17, 5))
        tk.Label(self.root, text="Procesamiento local · Tus archivos no se suben a internet", bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack(pady=(12, 12))

    def pick(self):
        p = filedialog.askopenfilename(title="Elegir archivo multimedia", filetypes=[("Multimedia", "*.mp4 *.mkv *.mov *.avi *.webm *.mp3 *.wav *.m4a *.aac *.flac *.ogg"), ("Todos", "*.*")])
        if p: self.set_file(p)
    def on_drop(self, event):
        try:
            paths = self.root.tk.splitlist(event.data)
            if paths: self.set_file(paths[0])
        except Exception: self.status.set("No pude leer ese archivo. Prueba con el selector.")
    def set_file(self, path):
        p = Path(path.strip("{}"))
        if not p.is_file(): self.status.set("El archivo seleccionado no existe."); return
        self.source = str(p)
        self.file_label.configure(text=f"✓  {p.name}\n\nArchivo listo para procesar", fg=GREEN)
        self.status.set(f"Seleccionado · {p.stat().st_size / 1048576:.1f} MB")

    def start(self, mode):
        if self.busy: return
        if not self.source:
            messagebox.showinfo("Falta un archivo", "Primero arrastra o selecciona un archivo."); return
        if not Path(self.ffmpeg).is_file():
            messagebox.showerror("Falta FFmpeg", "No se encontró ffmpeg.exe. Usa la descarga portable del repositorio."); return
        src = Path(self.source)
        if mode == "mp3":
            out, args = src.with_name(src.stem + "_audio.mp3"), ["-y", "-i", str(src), "-vn", "-codec:a", "libmp3lame", "-q:a", "2"]
        elif mode == "frame":
            out, args = src.with_name(src.stem + "_fotograma.jpg"), ["-y", "-ss", "00:00:01", "-i", str(src), "-frames:v", "1", "-q:v", "2"]
        else:
            out, args = src.with_name(src.stem + "_compacto.mp4"), ["-y", "-i", str(src), "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-b:v", "900k", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart"]
        self.busy = True; self.status.set("Procesando… puede tardar según el tamaño.")
        threading.Thread(target=self.worker, args=(args + [str(out)], out, mode), daemon=True).start()
    def worker(self, args, out, mode):
        try:
            p = subprocess.run([self.ffmpeg, "-hide_banner", "-loglevel", "error", *args], capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=7200)
            if p.returncode: raise RuntimeError((p.stderr or "FFmpeg no pudo procesar el archivo.")[-1200:])
            if not out.is_file() or not out.stat().st_size: raise RuntimeError("La salida no se creó correctamente.")
            if mode == "compress" and out.stat().st_size >= 25 * 1024 * 1024: raise RuntimeError("El resultado supera 25 MB. Prueba con un video más corto o menor resolución.")
            size = out.stat().st_size / 1048576
            self.root.after(0, lambda: self.finish(True, f"Terminado · {out.name} ({size:.1f} MB)", out))
        except Exception as e:
            msg = str(e); self.root.after(0, lambda m=msg: self.finish(False, "No se pudo completar: " + m))
    def finish(self, ok, msg, output=None):
        self.busy = False; self.status.set(msg)
        if ok and messagebox.askyesno("¡Listo!", "Archivo creado. ¿Abrir carpeta?"): os.startfile(str(output.parent))
        elif not ok: messagebox.showerror("Error de procesamiento", msg)
    def convert_mp3(self): self.start("mp3")
    def compress(self): self.start("compress")
    def frame(self): self.start("frame")
    def run(self): self.root.mainloop()

if __name__ == "__main__": App().run()
