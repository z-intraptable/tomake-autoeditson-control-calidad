#!/usr/bin/env python3
"""Control de calidad de un video para redes (spots, reels, shorts).

Uso:
    python qc_video.py VIDEO [--salida CARPETA] [--formato 9:16|1:1|16:9|4:5]
                             [--lufs -14] [--tp -1] [--max-plano 3.0] [--umbral-corte 0.3]

Genera en la carpeta de salida:
    reporte.md           tabla de chequeos con OK / FALLA / REVISAR
    reporte.json         lo mismo, legible por un agente
    hoja.jpg             12 cuadros repartidos en toda la pieza (prueba de pausa)
    hoja_gancho.jpg      12 cuadros de los primeros 3 s (cada 0,25 s)
    silueta.png          cuadro central al 10 % (¿se reconoce el producto?)
    brillo_bajo.png      cuadro central simulando pantalla al 10 % de brillo
    parlante_celular.wav audio filtrado 300-6000 Hz (¿se entiende en un celular?)

Solo necesita Python 3.8+ y ffmpeg/ffprobe en el PATH. No usa red.
Las imágenes hay que MIRARLAS: el script mide lo medible y deja lo visual marcado como REVISAR.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

FORMATOS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080), "4:5": (1080, 1350)}


def correr(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def sondear(video):
    code, out, err = correr(["ffprobe", "-v", "error", "-print_format", "json",
                             "-show_streams", "-show_format", str(video)])
    if code != 0:
        sys.exit(f"ffprobe no pudo leer el video: {err.strip()}")
    return json.loads(out)


def fps_de(stream):
    num, _, den = stream.get("avg_frame_rate", "0/1").partition("/")
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def cortes(video, umbral):
    _, _, err = correr(["ffmpeg", "-hide_banner", "-i", str(video), "-an",
                        "-vf", f"select='gt(scene,{umbral})',showinfo", "-f", "null", "-"])
    return [float(t) for t in re.findall(r"pts_time:([0-9.]+)", err)]


def loudness(video):
    _, _, err = correr(["ffmpeg", "-hide_banner", "-i", str(video), "-vn",
                        "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)
    if not m:
        return None, None
    d = json.loads(m.group(0))
    try:
        return float(d["input_i"]), float(d["input_tp"])
    except (KeyError, ValueError):
        return None, None


def hoja(video, salida, inicio, paso, cantidad=12):
    # Extrae `cantidad` cuadros desde `inicio` cada `paso` segundos y los arma en 6x2.
    filtro = f"fps=1/{paso:.4f},scale=360:-2,tile=6x{max(1, (cantidad + 5) // 6)}"
    correr(["ffmpeg", "-hide_banner", "-y", "-ss", f"{inicio:.3f}", "-i", str(video),
            "-vf", filtro, "-frames:v", "1", "-q:v", "3", str(salida)])
    return salida.exists()


def cuadro(video, t, filtro, salida):
    correr(["ffmpeg", "-hide_banner", "-y", "-ss", f"{t:.3f}", "-i", str(video),
            "-frames:v", "1", "-vf", filtro, str(salida)])
    return salida.exists()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap =argparse.ArgumentParser(description="Control de calidad de video para redes")
    ap.add_argument("video")
    ap.add_argument("--salida", default=None)
    ap.add_argument("--formato", default="9:16", choices=list(FORMATOS))
    ap.add_argument("--lufs", type=float, default=-14.0, help="loudness integrado objetivo")
    ap.add_argument("--tp", type=float, default=-1.0, help="true peak máximo en dBTP")
    ap.add_argument("--max-plano", type=float, default=3.0, help="segundos máximos sin corte")
    ap.add_argument("--umbral-corte", type=float, default=0.3, help="sensibilidad de detección de cortes")
    a = ap.parse_args()

    for herramienta in ("ffmpeg", "ffprobe"):
        if not shutil.which(herramienta):
            sys.exit(f"Falta {herramienta} en el PATH.")

    video = Path(a.video).resolve()
    if not video.exists():
        sys.exit(f"No existe {video}")
    out = Path(a.salida or video.with_name(video.stem + "_qc")).resolve()
    out.mkdir(parents=True, exist_ok=True)

    info = sondear(video)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    au = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    if v is None:
        sys.exit("El archivo no tiene pista de video.")
    dur = float(info["format"].get("duration") or v.get("duration") or 0)
    w, h, fps = int(v["width"]), int(v["height"]), fps_de(v)

    checks = []

    def agregar(nombre, estado, detalle):
        checks.append({"chequeo": nombre, "estado": estado, "detalle": detalle})

    # 1. Formato
    ew, eh = FORMATOS[a.formato]
    agregar("Resolución", "OK" if (w, h) == (ew, eh) else "FALLA",
            f"{w}x{h} (pedido {a.formato} = {ew}x{eh})")
    agregar("Cuadros por segundo", "OK" if 23.9 <= fps <= 60.1 else "REVISAR", f"{fps:.2f} fps")
    agregar("Duración", "REVISAR", f"{dur:.2f} s: confirmar contra el pedido")

    # 2. Metadatos de color
    tags = {k: v.get(k, "") for k in ("color_primaries", "color_transfer", "color_space")}
    ok709 = all("709" in (tags[k] or "") for k in tags)
    agregar("Color BT.709", "OK" if ok709 else "FALLA",
            ", ".join(f"{k}={tags[k] or 'sin dato'}" for k in tags) +
            ("" if ok709 else ". Reencodear agregando al final de la cadena de video 'setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709' y en la salida -color_primaries bt709 -color_trc bt709 -colorspace bt709"))

    # 3. Cadencia
    ts = cortes(video, a.umbral_corte)
    bordes = [0.0] + ts + [dur]
    planos = [round(b - a_, 2) for a_, b in zip(bordes, bordes[1:]) if b - a_ > 0.04]
    largos = [(round(bordes[i], 2), p) for i, p in enumerate(planos) if p > a.max_plano]
    prom = sum(planos) / len(planos) if planos else dur
    agregar("Cadencia", "OK" if not largos else "FALLA",
            f"{len(planos)} planos, promedio {prom:.2f} s" +
            (f"; planos de más de {a.max_plano} s en: " + ", ".join(f"{t}s ({p}s)" for t, p in largos)
             if largos else "") +
            ". Un plano largo puede estar bien si adentro pasa algo nuevo: confirmarlo mirando.")

    # 4. Sonido
    if au is None:
        agregar("Audio", "FALLA", "La pieza no tiene pista de audio")
    else:
        i, tp = loudness(video)
        if i is None:
            agregar("Loudness", "REVISAR", "No se pudo medir")
        else:
            agregar("Loudness integrado", "OK" if abs(i - a.lufs) <= 1.0 else "FALLA",
                    f"{i:.1f} LUFS (objetivo {a.lufs:.0f} ±1)")
            agregar("True peak", "OK" if tp <= a.tp else "FALLA", f"{tp:.1f} dBTP (máximo {a.tp:.0f})")
        correr(["ffmpeg", "-hide_banner", "-y", "-i", str(video), "-vn",
                "-af", "highpass=f=300,lowpass=f=6000", str(out / "parlante_celular.wav")])
        agregar("Parlante de celular", "REVISAR", "Escuchar parlante_celular.wav: ¿se entienden voz y SFX?")

    # 5. Visuales (se generan; los juzga quien mira)
    paso = max(dur / 12, 0.05) * 0.999
    if hoja(video, out / "hoja.jpg", 0, paso):
        agregar("Prueba de pausa", "REVISAR",
                "hoja.jpg: cada cuadro tiene que funcionar como póster; un solo foco por cuadro")
    if hoja(video, out / "hoja_gancho.jpg", 0, 0.25 if dur >= 3 else max(dur / 12, 0.04)):
        agregar("Gancho (0-3 s)", "REVISAR",
                "hoja_gancho.jpg: movimiento desde el cuadro 0, texto antes de 0,8 s, sin fundido desde negro")
    medio = dur / 2
    if cuadro(video, medio, "scale=iw/10:-2", out / "silueta.png"):
        agregar("Silueta", "REVISAR", "silueta.png: el producto se tiene que reconocer al 10 %")
    if cuadro(video, medio, "eq=brightness=-0.35:contrast=0.7", out / "brillo_bajo.png"):
        agregar("Brillo bajo", "REVISAR", "brillo_bajo.png: el texto se tiene que seguir leyendo")
    if a.formato == "9:16":
        agregar("Zona segura", "REVISAR",
                "En hoja.jpg: nada importante en el 14 % superior, el 20 % inferior ni el 12 % derecho")

    fallas = sum(c["estado"] == "FALLA" for c in checks)
    veredicto = "NO SE ENTREGA" if fallas else "Pasa lo medible: falta la revisión visual"

    (out / "reporte.json").write_text(json.dumps(
        {"video": str(video), "duracion": dur, "resolucion": [w, h], "fps": fps,
         "cortes": ts, "planos": planos, "chequeos": checks, "veredicto": veredicto},
        ensure_ascii=False, indent=2), encoding="utf-8")

    lineas = [f"# Control de calidad: {video.name}", "",
              f"**Veredicto:** {veredicto} ({fallas} fallas)", "",
              "| Chequeo | Estado | Detalle |", "|---|---|---|"]
    lineas += [f"| {c['chequeo']} | {c['estado']} | {c['detalle']} |" for c in checks]
    (out / "reporte.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    print("\n".join(lineas))
    print(f"\nArchivos en: {out}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
