---
name: control-calidad-video
description: Control de calidad y crítica de videos cortos (spots, reels, shorts) antes de entregarlos. Un script mide con ffmpeg lo medible (resolución, fps, color BT.709, cadencia de cortes, loudness, true peak) y genera hojas de contacto, prueba de silueta, de brillo bajo y de parlante de celular; la pauta de 5 ejes juzga lo visual. Veredicto binario: se entrega o no se entrega. Usar SIEMPRE antes de entregar un video o una imagen generada, y para analizar o comparar una referencia. Keywords: QA, quality check, video review, loudness, LUFS, contact sheet, critique.
---

# Control de calidad de video

**Regla de oro:** una pieza que no pasa este control **no se entrega**. Se corrige y se vuelve a medir. Que el render "haya salido bien" no dice nada: hay que mirar los cuadros.

## 1. Medir (un comando)
Requiere Python 3.8+ y ffmpeg/ffprobe en el PATH. No usa internet.

```bash
python scripts/qc_video.py pieza.mp4 --formato 9:16
```

Opciones: `--formato 9:16|1:1|16:9|4:5` · `--lufs -14` · `--tp -1` · `--max-plano 3.0` · `--umbral-corte 0.3` · `--salida CARPETA`.

Genera en `pieza_qc/`:
| Archivo | Para qué |
|---|---|
| `reporte.md` / `reporte.json` | Tabla de chequeos OK / FALLA / REVISAR y el veredicto |
| `hoja.jpg` | 12 cuadros repartidos en toda la pieza (prueba de pausa) |
| `hoja_gancho.jpg` | 12 cuadros de los primeros 3 s, cada 0,25 s |
| `silueta.png` | Cuadro central al 10%: ¿se reconoce el producto? |
| `brillo_bajo.png` | Cuadro central simulando pantalla con poco brillo: ¿se lee el texto? |
| `parlante_celular.wav` | Audio filtrado 300-6000 Hz: ¿se entiende en un celular? |

Sale con código 1 si hay alguna FALLA (sirve para automatizar).

**Lo que mide solo:** resolución, fps, metadatos de color BT.709, planos más largos que `--max-plano`, loudness integrado (±1 LU del objetivo) y true peak.
**Lo que deja en REVISAR:** todo lo visual. Esas imágenes **hay que abrirlas y mirarlas**; un agente con visión las tiene que leer antes de opinar.

## 2. Mirar (pauta de 5 ejes)
| Eje | Pregunta | Falla amateur | Nivel profesional |
|---|---|---|---|
| 1. Jerarquía y foco | ¿Qué lee el ojo en los primeros 150 ms? | Texto, fondo y producto compiten | Un solo foco, marcado por contraste, luminancia o el primer movimiento |
| 2. Color | ¿La paleta está unificada? | Saturaciones dispares; acento por todos lados | 60-30-10; el acento en ≤10% del cuadro; el producto contrasta con el fondo |
| 3. Cadencia | ¿Cada plano dura lo que necesita su información? | Planos vacíos largos, o densos de medio segundo | Algo nuevo cada 1,5 a 2,5 s en spots |
| 4. Sonido | ¿El audio sostiene la imagen? | Música de otro género; SFX corridos | Género correcto, -14 LUFS, SFX clavados al cuadro del evento |
| 5. Tipografía | ¿Se lee y respeta la composición? | Texto quieto, sobre el producto, cortado, poco contraste | Animado, en el espacio negativo, en la zona segura, contraste alto |

Sobre `hoja.jpg` y `hoja_gancho.jpg`, chequear además:
- **Prueba de pausa:** cada cuadro tiene que funcionar como póster.
- **Gancho:** movimiento desde el cuadro 0, texto antes de 0,8 s, sin fundido desde negro.
- **Zona segura (9:16):** nada importante en el 14% superior, el 20% inferior ni el 12% derecho.
- **Texto sobre el producto:** en ningún cuadro.
- **Contraste producto/fondo:** si el producto es claro sobre fondo claro, agregar halo, contorno del color de marca u oscurecer el fondo.
- **Banding:** en degradados, agregar 1-2% de ruido o grano leve.

## 3. Cómo arreglar cada FALLA
| Falla | Arreglo |
|---|---|
| Resolución | Renderizar en el formato pedido. No reescalar un 720p a 1080p y entregarlo como bueno. |
| Color BT.709 | Al final de la cadena de filtros de video: `setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709`, y en la salida `-color_primaries bt709 -color_trc bt709 -colorspace bt709`. Solo los flags de salida no siempre alcanzan. |
| Cadencia | Partir el plano largo, sumar un evento (punch, texto, elemento) o recortarlo. Un plano largo vale si adentro pasa algo nuevo: confirmarlo mirando. |
| Loudness | `loudnorm=I=-14:TP=-1.5:LRA=7` (dos pasadas para precisión). |
| True peak | Limitador al final de la cadena de audio, o bajar la ganancia del master. |
| Sin audio | Un spot sin audio no se entrega salvo que el pedido lo diga. |

## 4. Cómo reportar
- Sin adjetivos vacíos: qué está al nivel, qué no y por qué, **con timecode**.
- Primero las FALLAS medidas, después lo visual.
- Si algo no pasa, corregir y repetir el control (hasta 3 vueltas) **antes** de mostrarlo.
- Al entregar, adjuntar `reporte.md`: el cliente ve que se midió.

## 5. Analizar una referencia
Correr el mismo script sobre el video de referencia y comparar las hojas lado a lado, con el mismo número de cuadros. Ficha completa en `referencias/analisis-de-referencia.md`.
