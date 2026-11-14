#!/usr/bin/env python3
"""Quality check for a social video (ad spots, reels, shorts).

Usage:
    python qc_video.py VIDEO [--out FOLDER] [--format 9:16|1:1|16:9|4:5]
                             [--lufs -14] [--tp -1] [--max-shot 3.0] [--cut-threshold 0.3]

Writes to the output folder:
    report.md            check table with OK / FAIL / REVIEW
    report.json          the same, machine-readable for an agent
    contact_sheet.jpg    12 frames spread across the whole piece (pause test)
    hook_sheet.jpg       12 frames from the first 3 s (every 0.25 s)
    silhouette.png       middle frame at 10 % size (is the product recognizable?)
    low_brightness.png   middle frame simulating a screen at 10 % brightness
    phone_speaker.wav    audio band-passed 300-6000 Hz (is it intelligible on a phone?)

Only needs Python 3.8+ and ffmpeg/ffprobe on the PATH. No network access.
The images must be LOOKED AT: the script measures what can be measured and flags the visual checks as REVIEW.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

FORMATS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080), "4:5": (1080, 1350)}


def run(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout, r.stderr


def probe(video):
    code, out, err = run(["ffprobe", "-v", "error", "-print_format", "json",
                          "-show_streams", "-show_format", str(video)])
    if code != 0:
        sys.exit(f"ffprobe could not read the video: {err.strip()}")
    return json.loads(out)


def fps_of(stream):
    num, _, den = stream.get("avg_frame_rate", "0/1").partition("/")
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def cuts(video, threshold):
    _, _, err = run(["ffmpeg", "-hide_banner", "-i", str(video), "-an",
                     "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    return [float(t) for t in re.findall(r"pts_time:([0-9.]+)", err)]


def loudness(video):
    _, _, err = run(["ffmpeg", "-hide_banner", "-i", str(video), "-vn",
                     "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)
    if not m:
        return None, None
    d = json.loads(m.group(0))
    try:
        return float(d["input_i"]), float(d["input_tp"])
    except (KeyError, ValueError):
        return None, None


def sheet(video, output, start, step, count=12):
    # Grabs `count` frames from `start`, one every `step` seconds, and tiles them 6x2.
    vf = f"fps=1/{step:.4f},scale=360:-2,tile=6x{max(1, (count + 5) // 6)}"
    run(["ffmpeg", "-hide_banner", "-y", "-ss", f"{start:.3f}", "-i", str(video),
         "-vf", vf, "-frames:v", "1", "-q:v", "3", str(output)])
    return output.exists()


def frame(video, t, vf, output):
    run(["ffmpeg", "-hide_banner", "-y", "-ss", f"{t:.3f}", "-i", str(video),
         "-frames:v", "1", "-vf", vf, str(output)])
    return output.exists()


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap =argparse.ArgumentParser(description="Quality check for social videos")
    ap.add_argument("video", help="video file to check")
    ap.add_argument("--out", default=None, help="output folder (default: VIDEO_qc next to the video)")
    ap.add_argument("--format", default="9:16", choices=list(FORMATS), help="expected aspect ratio / resolution")
    ap.add_argument("--lufs", type=float, default=-14.0, help="target integrated loudness")
    ap.add_argument("--tp", type=float, default=-1.0, help="maximum true peak in dBTP")
    ap.add_argument("--max-shot", type=float, default=3.0, help="maximum seconds without a cut")
    ap.add_argument("--cut-threshold", type=float, default=0.3, help="cut-detection sensitivity")
    a = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is missing from the PATH.")

    video = Path(a.video).resolve()
    if not video.exists():
        sys.exit(f"{video} does not exist")
    out = Path(a.out or video.with_name(video.stem + "_qc")).resolve()
    out.mkdir(parents=True, exist_ok=True)

    info = probe(video)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    au = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    if v is None:
        sys.exit("The file has no video stream.")
    dur = float(info["format"].get("duration") or v.get("duration") or 0)
    w, h, fps = int(v["width"]), int(v["height"]), fps_of(v)

    checks = []

    def add(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    # 1. Format
    ew, eh = FORMATS[a.format]
    add("Resolution", "OK" if (w, h) == (ew, eh) else "FAIL",
        f"{w}x{h} (requested {a.format} = {ew}x{eh})")
    add("Frame rate", "OK" if 23.9 <= fps <= 60.1 else "REVIEW", f"{fps:.2f} fps")
    add("Duration", "REVIEW", f"{dur:.2f} s: confirm against the brief")

    # 2. Color metadata
    tags = {k: v.get(k, "") for k in ("color_primaries", "color_transfer", "color_space")}
    ok709 = all("709" in (tags[k] or "") for k in tags)
    add("Color BT.709", "OK" if ok709 else "FAIL",
        ", ".join(f"{k}={tags[k] or 'missing'}" for k in tags) +
        ("" if ok709 else ". Re-encode adding 'setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709' at the end of the video filter chain and -color_primaries bt709 -color_trc bt709 -colorspace bt709 on the output"))

    # 3. Pacing
    ts = cuts(video, a.cut_threshold)
    edges = [0.0] + ts + [dur]
    shots = [round(b - a_, 2) for a_, b in zip(edges, edges[1:]) if b - a_ > 0.04]
    long_shots = [(round(edges[i], 2), p) for i, p in enumerate(shots) if p > a.max_shot]
    avg = sum(shots) / len(shots) if shots else dur
    add("Pacing", "OK" if not long_shots else "FAIL",
        f"{len(shots)} shots, average {avg:.2f} s" +
        (f"; shots longer than {a.max_shot} s at: " + ", ".join(f"{t}s ({p}s)" for t, p in long_shots)
         if long_shots else "") +
        ". A long shot can be fine if something new happens inside it: confirm by looking.")

    # 4. Sound
    if au is None:
        add("Audio", "FAIL", "The piece has no audio stream")
    else:
        i, tp = loudness(video)
        if i is None:
            add("Loudness", "REVIEW", "Could not be measured")
        else:
            add("Integrated loudness", "OK" if abs(i - a.lufs) <= 1.0 else "FAIL",
                f"{i:.1f} LUFS (target {a.lufs:.0f} ±1)")
            add("True peak", "OK" if tp <= a.tp else "FAIL", f"{tp:.1f} dBTP (max {a.tp:.0f})")
        run(["ffmpeg", "-hide_banner", "-y", "-i", str(video), "-vn",
             "-af", "highpass=f=300,lowpass=f=6000", str(out / "phone_speaker.wav")])
        add("Phone speaker", "REVIEW", "Listen to phone_speaker.wav: are the voice and SFX intelligible?")

    # 5. Visuals (generated here; judged by whoever looks at them)
    step = max(dur / 12, 0.05) * 0.999
    if sheet(video, out / "contact_sheet.jpg", 0, step):
        add("Pause test", "REVIEW",
            "contact_sheet.jpg: every frame has to work as a poster; a single focal point per frame")
    if sheet(video, out / "hook_sheet.jpg", 0, 0.25 if dur >= 3 else max(dur / 12, 0.04)):
        add("Hook (0-3 s)", "REVIEW",
            "hook_sheet.jpg: motion from frame 0, text before 0.8 s, no fade in from black")
    mid = dur / 2
    if frame(video, mid, "scale=iw/10:-2", out / "silhouette.png"):
        add("Silhouette", "REVIEW", "silhouette.png: the product has to be recognizable at 10 %")
    if frame(video, mid, "eq=brightness=-0.35:contrast=0.7", out / "low_brightness.png"):
        add("Low brightness", "REVIEW", "low_brightness.png: the text still has to be readable")
    if a.format == "9:16":
        add("Safe zone", "REVIEW",
            "In contact_sheet.jpg: nothing important in the top 14 %, the bottom 20 % or the right 12 %")

    fails = sum(c["status"] == "FAIL" for c in checks)
    verdict = "DO NOT DELIVER" if fails else "Passes the measurable checks: visual review still pending"

    (out / "report.json").write_text(json.dumps(
        {"video": str(video), "duration": dur, "resolution": [w, h], "fps": fps,
         "cuts": ts, "shots": shots, "checks": checks, "verdict": verdict},
        ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# Quality check: {video.name}", "",
             f"**Verdict:** {verdict} ({fails} fails)", "",
             "| Check | Status | Detail |", "|---|---|---|"]
    lines += [f"| {c['check']} | {c['status']} | {c['detail']} |" for c in checks]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print(f"\nFiles in: {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
