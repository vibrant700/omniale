# Drum AV Repair

Case showcase: https://vibrant700.github.io/omniale/drum-av-repair/

The page follows the section order and warm, green document styling of the
Thor Arm Transfer reference: task definition, evaluation, model result,
paired audiovisual evidence and production workflow. Task difficulty and
solvability appear at the bottom of the task-definition section.

The four peer score categories are localization (10), performance correspondence
(50), transitions and continuity (20), and timbre consistency and added
artifacts (20). The displayed Astra score is 65.33/100, taken from the user's
reviewed release bundle. Subjective grades were supplied by the user's Gemini
evaluation; this builder does not request or change judgments.

## Build

```sh
python build_page.py --bundle /absolute/path/to/release_bundle --ffmpeg /absolute/path/to/ffmpeg
```

The builder copies the public input, exports browser-compatible AAC previews,
packages the original editable REAPER project, and builds paired reference,
corrupted and repaired excerpts with 1.5 seconds of context at each boundary.
The original 24-bit WAV is supplied separately from browser previews.

The full hidden reference recording, injection script and raw solver logs stay
outside the public site. Only selected paired excerpts are shown as result
evidence. Published score data is filtered to the four peer categories.

Original performance: Daniel Glass / Drumeo; source video
https://www.bilibili.com/video/BV1h5411b7CF?p=34 .

Layout reference: https://starivers152.github.io/OmniALE/thor-arm-transfer/ .
