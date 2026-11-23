"""Apply the published 30/30/30/10 formula to metrics and completed item reviews."""
import argparse
import json
import math
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]


def number(value, label, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: a completed finite numeric result is required')
    if minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise ValueError(f'{label}: out of range')
    return value


def close(a, b, label):
    if not math.isclose(a, b, abs_tol=1e-8, rel_tol=1e-8):
        raise ValueError(f'{label}: reported total disagrees with item results')


def binary_review(review, prefix):
    if review.get('assessment_status') != 'complete':
        raise ValueError(f'{prefix}: only complete reviews can be aggregated')
    items = review['items']
    # The supplied original music result uses a keyed object; normalized records use an array.
    if isinstance(items, dict):
        items = [{**item, 'id': key} for key, item in items.items()]
    expected = {prefix + str(i) for i in range(1, 6)}
    if len(items) != 5 or {item['id'] for item in items} != expected:
        raise ValueError(f'{prefix}: expected five distinct criterion IDs')
    total = 0
    for item in items:
        value = number(item['score'], item['id'], 0, 1)
        if value not in (0, 1):
            raise ValueError(f"{item['id']}: only 0/1 is scored; null remains unassessed")
        if not item.get('evidence') or not (item.get('reason') or any(e.get('reason') for e in item['evidence'])):
            raise ValueError(f"{item['id']}: evidence and reasoning are required")
        total += value
    reported_total = review.get('score', review.get('music_score' if prefix == 'M' else 'sfx_score'))
    close(number(reported_total, prefix + ' total', 0, 5), total, prefix)
    return total


def dynamic_review(review):
    if review.get('assessment_status') != 'complete':
        raise ValueError('Dynamic: only complete reviews can be aggregated')
    criteria = review['criteria']
    if len(criteria) != 3 or {item['id'] for item in criteria} != {'D1', 'D2', 'D3'}:
        raise ValueError('Dynamic: three distinct criteria are required')
    total = 0
    for item in criteria:
        count = number(item['independent_error_count'], item['id'] + ' count', 0)
        if int(count) != count:
            raise ValueError('Dynamic: independent error count must be an integer')
        if count and not item.get('events'):
            raise ValueError('Dynamic: counted errors require event evidence')
        events = item.get('events', [])
        if len(events) != count or len({e.get('event_id') for e in events}) != count or any(not e.get('event_id') for e in events):
            raise ValueError('Dynamic: independent error count must match distinct, identified evidence events')
        if item.get('count_is_lower_bound') and count < 2:
            raise ValueError('Dynamic: a lower bound only fixes the score when the deduction is saturated')
        value = max(0, 10 - 5 * count)
        close(number(item['score'], item['id'], 0, 10), value, item['id'])
        total += value
    close(number(review['score'], 'dynamic total', 0, 30), total, 'dynamic')
    return total


def aggregate(surface, images, dynamic, music, sfx):
    visible = surface['six_input_view_visible_samples']['fscore_by_reference_diagonal_fraction']['0.005']
    f1 = number(visible['fscore'], 'visible F1@0.5%', 0, 1)
    precision = number(visible['precision'], 'precision', 0, 1)
    recall = number(visible['recall'], 'recall', 0, 1)
    close(f1, 2 * precision * recall / (precision + recall) if precision + recall else 0, 'F1')
    views = images['views']['textured']
    if set(views) != {'front', 'back', 'left', 'right', 'top', 'bottom'}:
        raise ValueError('Images: the six fixed views are required')
    means = {}
    for key in ['silhouette_IoU', 'foreground_union_SSIM', 'foreground_union_LPIPS_alex_spatial']:
        values = [number(v[key], key) for v in views.values()]
        means[key] = sum(values) / 6
        close(number(images['mean']['textured'][key], key + ' mean'), means[key], key)
    iou = number(means['silhouette_IoU'], 'IoU mean', 0, 1)
    clip = lambda value: max(0, min(1, value))
    parts = {
        'structure': 15 * f1 + 15 * iou,
        'appearance': 15 * (clip(means['foreground_union_SSIM']) + 1 - clip(means['foreground_union_LPIPS_alex_spatial'])),
        'dynamic': dynamic_review(dynamic),
        'music': binary_review(music, 'M'),
        'sfx': binary_review(sfx, 'S'),
    }
    total = sum(parts.values())
    return {'protocol_version': 'scv-showcase-verification-v1',
            'weights': {'structure': 30, 'appearance': 30, 'dynamic': 30, 'music': 5, 'sfx': 5},
            'scores': {**parts, 'total': total}, 'display_total': f'{total:.2f}',
            'engineering_weight': 0,
            'note': 'This aggregates completed evidence-backed reviews; it does not perform media judgment.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--published', action='store_true', help='Verify the included completed result records')
    for name in ['surface', 'images', 'dynamic', 'music', 'sfx']:
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    names = {'surface': 'surface_metrics.json', 'images': 'image_metrics.json',
             'dynamic': 'dynamic-review.json', 'music': 'music-review.json', 'sfx': 'sfx-review.json'}
    records = {}
    for key, filename in names.items():
        path = getattr(args, key)
        if path is None and args.published:
            path = PACKAGE / 'results' / filename
        if path is None:
            parser.error(f'--{key} is required without --published')
        records[key] = json.loads(path.read_text(encoding='utf-8'))
    result = aggregate(**records)
    if args.published:
        expected = json.loads((PACKAGE / 'results/expected-score.json').read_text(encoding='utf-8'))['scores']
        for key, value in result['scores'].items():
            close(value, expected[key], key + ' published')
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding='utf-8')
    print(payload, end='')


if __name__ == '__main__':
    main()
