# ToMake AutoEditson · Control de calidad de video (skill gratis)

Una skill para agentes de IA (Claude Code, Codex CLI, Gemini CLI, OpenCode) que revisa un video antes de entregarlo y da un veredicto binario: **se entrega o no se entrega**.

- **Lo medible, con un script** (`qc_video.py`, Python + ffmpeg): resolución, fps, metadatos de color BT.709, volumen integrado (LUFS) y true peak, cadencia de cortes, cuadros negros, y una hoja de contacto de 12 cuadros.
- **Lo visual, con una pauta de 5 ejes**, más pruebas de silueta, brillo bajo y parlante de celular.
- **Una tabla de arreglos** para cada falla que detecta.
- **Análisis de referencias:** cómo desarmar un video que te gusta y comparar tu pieza contra él.

## Instalación

```bash
cp -r skills/control-calidad-video ~/.claude/skills/
```

Para un solo proyecto, usá `.claude/skills/` dentro del repo. En otros agentes, copiala a su carpeta de skills o citá el `SKILL.md` desde tu `AGENTS.md` o `GEMINI.md`.

**Requisitos:** Python 3.9+ y ffmpeg/ffprobe en el PATH.

## Uso

```
Pasá control de calidad a render/final.mp4
```

O directo con el script:

```bash
python skills/control-calidad-video/scripts/qc_video.py render/final.mp4
```

## El paquete completo
Esta skill es una de las 7 de **ToMake AutoEditson Skills**. Las otras son dirección de spots, prompts de foto publicitaria, motion design en Remotion, guion corto con humor, investigación de contenido y trabajo por dictado.

---
Licencia MIT · ToMake AutoEditson
