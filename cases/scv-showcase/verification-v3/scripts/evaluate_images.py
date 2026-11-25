"""Fixed six-view SSIM and silhouette metrics on original RGBA pixels; no registration."""
import argparse
import importlib.metadata
import json
from pathlib import Path


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2,
                                    allow_nan=False) + '\n', encoding='utf-8')


def rgba(path, image_size):
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(path).convert('RGBA')).astype(np.float32) / 255
    if a.shape != (image_size[1], image_size[0], 4):
        raise ValueError(f'Expected unresampled {image_size} RGBA image: {path}; got {a.shape}')
    return a


def composite(a):
    return a[..., :3] * a[..., 3:4] + .5 * (1 - a[..., 3:4])


def image_metrics(public_root, prediction, output, reference_clay=None):
    import numpy as np
    from skimage.metrics import structural_similarity

    def measure(a, b):
        ma, mb = a[..., 3] >= .5, b[..., 3] >= .5
        union, intersection = ma | mb, ma & mb
        ac, bc = composite(a), composite(b)
        _, ssim_map = structural_similarity(ac, bc, data_range=1, channel_axis=2,
            gaussian_weights=True, sigma=1.5, use_sample_covariance=False, full=True)
        mse = float(np.square(ac-bc).mean(axis=2)[union].mean()) if union.any() else 0
        return {
            'silhouette_IoU': float(intersection.sum()/union.sum()) if union.any() else 1,
            'foreground_union_SSIM': float(ssim_map.mean(axis=2)[union].mean()) if union.any() else 1,
            'foreground_union_RGB_MSE': mse,
            'reference_foreground_pixels': int(ma.sum()),
            'submission_foreground_pixels': int(mb.sum()),
            'foreground_union_pixels': int(union.sum()),
            'foreground_intersection_pixels': int(intersection.sum()),
        }

    public_root, prediction = Path(public_root), Path(prediction)
    cal = json.loads((public_root/'cameras.json').read_text(encoding='utf-8'))
    result = {
        'status': 'raw_metrics', 'views': {},
        'alignment': 'Supplied cameras and world coordinates; no image registration',
        'region': 'Union of reference and candidate alpha>=0.5 masks on the fixed full-resolution canvas. RGB composited over common neutral 0.5 gray.',
        'SSIM': 'Gaussian sigma1.5, 11x11 window, population covariance, channel mean; spatial values averaged in union mask.',
        'reference': 'Original provided reference PNGs, unchanged and not resampled.',
        'versions': {name: importlib.metadata.version(name) for name in
            ['numpy', 'Pillow', 'scipy', 'scikit-image']},
    }
    styles = ['textured'] + (['clay'] if reference_clay is not None else [])
    for style in styles:
        result['views'][style] = {}
        for view in cal['views']:
            name = view['id']
            ref_path = public_root/view['image'] if style == 'textured' else Path(reference_clay)/(name+'.png')
            a = rgba(ref_path, cal['image_size'])
            b = rgba(prediction/style/(name+'.png'), cal['image_size'])
            result['views'][style][name] = measure(a, b)
        keys = ['silhouette_IoU', 'foreground_union_SSIM', 'foreground_union_RGB_MSE']
        result.setdefault('mean', {})[style] = {
            k: float(np.mean([v[k] for v in result['views'][style].values()])) for k in keys}
    a = rgba(public_root/cal['views'][0]['image'], cal['image_size'])
    identity = measure(a, a)
    blank = a.copy()
    blank[:] = 0
    empty = measure(a, blank)
    assert abs(identity['silhouette_IoU']-1) < 1e-8
    assert abs(identity['foreground_union_SSIM']-1) < 1e-7
    assert empty['silhouette_IoU'] == 0
    result['controls'] = {'identical_image': identity, 'transparent_empty_submission': empty}
    dump(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-root', required=True, help='Agent input directory containing cameras.json and reference/ PNGs')
    parser.add_argument('--prediction', required=True, help='Canonical capture directory containing textured/<view>.png')
    parser.add_argument('--output', required=True, help='Destination image_metrics.json')
    parser.add_argument('--reference-clay', help='Optional clay renders for diagnostics only; not part of the score')
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = image_metrics(args.public_root, args.prediction, output, args.reference_clay)
    print(json.dumps(result['mean'], ensure_ascii=False))


if __name__ == '__main__':
    main()
