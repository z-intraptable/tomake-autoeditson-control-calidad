# Reference analysis template

To understand why someone else's piece (or a competitor's) works and what it would take to match it. First run `scripts/qc_video.py` on the reference: it gives you the cuts, the average shot length and the sheets.

```
REFERENCE:      <brand / title / link>
TECHNICAL:      <duration> · <resolution> · <fps> · <loudness> LUFS
SHOTS:          <count> · average shot <s> · longest <s> at <timecode>
HOOK (0-2 s):   <what happens frame by frame>
TECHNIQUES:     <timecode> — <technique> (one per line)
TYPOGRAPHY:     <fonts, size, how it enters and exits>
LAYERS:         <how many at once in the densest shot>
TRANSITIONS:    <types and duration>
COLOR:          <palette, contrast, finish>
SOUND:          <genre, SFX, silences, voice>
ENDING AND CTA: <how it ends, how long the packshot lasts>
```

## After several templates
1. **Common patterns:** whatever repeats in 3 or more references is the norm for the category.
2. **Gap:** for each technique, can we do it today? Yes / partially / no, and how it would be implemented.
3. **What nobody does:** the gap where a piece of your own can stand out.

## Comparing a piece against a reference
- Same number of frames in both sheets, same spacing between frames.
- Stack one above the other and compare frame by frame: focus, density, color, text.
- Report in a table: axis · reference · piece · what to change.
