---
name: video-qc
description: Quality control and critique for short videos (ad spots, reels, shorts) before delivery. A script uses ffmpeg to measure everything measurable (resolution, fps, BT.709 color, cut pacing, loudness, true peak) and generates contact sheets plus silhouette, low-brightness and phone-speaker tests; a 5-axis rubric judges the visuals. Binary verdict: deliver or do not deliver. ALWAYS use before delivering a video or a generated image, and to analyze or compare a reference. Keywords: QA, quality check, video review, loudness, LUFS, true peak, contact sheet, critique.
---

# Video quality control

**Golden rule:** a piece that does not pass this check **is not delivered**. Fix it and measure again. A render that "came out fine" tells you nothing: you have to look at the frames.

## 1. Measure (one command)
Requires Python 3.8+ and ffmpeg/ffprobe on the PATH. No internet access.

```bash
python scripts/qc_video.py piece.mp4 --format 9:16
```

Options: `--format 9:16|1:1|16:9|4:5` · `--lufs -14` · `--tp -1` · `--max-shot 3.0` · `--cut-threshold 0.3` · `--out FOLDER`.

Writes to `piece_qc/`:
| File | What it is for |
|---|---|
| `report.md` / `report.json` | Table of OK / FAIL / REVIEW checks and the verdict |
| `contact_sheet.jpg` | 12 frames spread across the whole piece (pause test) |
| `hook_sheet.jpg` | 12 frames from the first 3 s, every 0.25 s |
| `silhouette.png` | Middle frame at 10%: is the product recognizable? |
| `low_brightness.png` | Middle frame simulating a low-brightness screen: is the text readable? |
| `phone_speaker.wav` | Audio band-passed 300-6000 Hz: is it intelligible on a phone? |

Exits with code 1 if there is any FAIL (useful for automation).

**What it measures on its own:** resolution, fps, BT.709 color metadata, shots longer than `--max-shot`, integrated loudness (±1 LU from target) and true peak.
**What it leaves as REVIEW:** everything visual. Those images **must be opened and looked at**; an agent with vision has to read them before giving an opinion.

## 2. Look (5-axis rubric)
| Axis | Question | Amateur failure | Professional level |
|---|---|---|---|
| 1. Hierarchy and focus | What does the eye read in the first 150 ms? | Text, background and product compete | A single focal point, set by contrast, luminance or the first motion |
| 2. Color | Is the palette unified? | Mismatched saturation; accent everywhere | 60-30-10; accent on ≤10% of the frame; product contrasts with the background |
| 3. Pacing | Does each shot last as long as its information needs? | Long empty shots, or dense half-second ones | Something new every 1.5 to 2.5 s in spots |
| 4. Sound | Does the audio carry the picture? | Music from the wrong genre; SFX out of sync | Right genre, -14 LUFS, SFX locked to the event frame |
| 5. Typography | Is it readable and does it respect the composition? | Static text, over the product, cut off, low contrast | Animated, in negative space, inside the safe zone, high contrast |

On `contact_sheet.jpg` and `hook_sheet.jpg`, also check:
- **Pause test:** every frame has to work as a poster.
- **Hook:** motion from frame 0, text before 0.8 s, no fade in from black.
- **Safe zone (9:16):** nothing important in the top 14%, the bottom 20% or the right 12%.
- **Text over the product:** in no frame.
- **Product/background contrast:** if the product is light on a light background, add a glow, an outline in the brand color, or darken the background.
- **Banding:** on gradients, add 1-2% noise or light grain.

## 3. How to fix each FAIL
| Fail | Fix |
|---|---|
| Resolution | Render at the requested format. Do not upscale a 720p to 1080p and deliver it as good. |
| Color BT.709 | At the end of the video filter chain: `setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709`, and on the output `-color_primaries bt709 -color_trc bt709 -colorspace bt709`. The output flags alone are not always enough. |
| Pacing | Split the long shot, add an event (punch-in, text, element) or trim it. A long shot is fine if something new happens inside it: confirm by looking. |
| Loudness | `loudnorm=I=-14:TP=-1.5:LRA=7` (two passes for accuracy). |
| True peak | Limiter at the end of the audio chain, or lower the master gain. |
| No audio | A spot without audio is not delivered unless the brief says so. |

## 4. How to report
- No empty adjectives: what is up to standard, what is not and why, **with timecode**.
- Measured FAILs first, then the visuals.
- If something does not pass, fix it and repeat the check (up to 3 rounds) **before** showing it.
- On delivery, attach `report.md`: the client sees that it was measured.

## 5. Analyze a reference
Run the same script on the reference video and compare the sheets side by side, with the same number of frames. Full template in `references/reference-analysis.md`.
