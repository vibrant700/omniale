# Novel View Synthesis — T1 & T2

Reconstructed 3-D talking-head scene rendered from two held-out camera
positions (T1, T2) using three calibrated input views (I1, I2, I3).

## Files

| File         | Description                                   |
|--------------|-----------------------------------------------|
| `scene.blend`| Editable Blender 5.3 scene with all 5 cameras |
| `T1.mp4`     | Rendered video from camera T1 (668×1024 30fps)|
| `T2.mp4`     | Rendered video from camera T2 (668×1024 30fps)|
| `build.py`   | Reproducible build entry point                |
| `assets/`    | Symlinks to input frames and audio            |

## Dependencies

- Blender ≥ 5.3 (headless)
- Python ≥ 3.10 with NumPy, Pillow
- FFmpeg ≥ 5

## Rebuild

```bash
cd submission
python build.py
```

This regenerates `scene.blend`, `T1.mp4`, and `T2.mp4` from the
calibration data and input frames in `candidate/`.

## Method

A spherical proxy geometry is placed at the estimated 3-D face centre.
For each output pixel a ray is cast from the target camera onto the
sphere, then projected into the three input views.  Colour is blended
from all valid projections weighted by surface-facing angle and
camera-view alignment.  Background pixels fall back to a planar
reprojection of the frontal I2 view.

The Blender scene stores the proxy mesh, all five calibrated cameras,
and is ready for manual editing, relighting, or re-rendering.
