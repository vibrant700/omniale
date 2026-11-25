"""Recompute the accepted GPU result from fixed metrics and completed review items.

This checks arithmetic and record consistency; it does not judge images or audio.
Run: python cases/scv-showcase/verification-v3/scripts/aggregate_score.py
"""
import json
import math
from pathlib import Path


def main():
    base = Path(__file__).resolve().parents[1] / 'results'
    load = lambda name: json.loads((base / name).read_text(encoding='utf-8'))
    surface = load('surface_metrics.json')
    images = load('image_metrics.json')
    detail = load('detail-restoration-review.json')
    music = load('music-review.json')
    sfx = load('sfx-review.json')
    for review in [detail, music, sfx]:
        assert review['assessment_status'] == 'complete'
    dimensions = detail['dimensions']
    assert len(dimensions) == 3 and {d['id'] for d in dimensions} == {'D1', 'D2', 'D3'}
    for d in dimensions:
        assert d['confirmed_error_count'] == len(d['deductions'])
        assert d['score'] == max(0, 10 - 5 * d['confirmed_error_count'])
    assert detail['total_score'] == sum(d['score'] for d in dimensions)
    for review, prefix in [(music, 'M'), (sfx, 'S')]:
        assert len(review['items']) == 5
        assert {item['id'] for item in review['items']} == {prefix + str(i) for i in range(1, 6)}
        assert all(item['score'] in (0, 1) for item in review['items'])
        assert review['score'] == sum(item['score'] for item in review['items'])
    views = images['views']['textured']
    assert set(views) == {'front', 'back', 'left', 'right', 'top', 'bottom'}
    mean = lambda key: sum(view[key] for view in views.values()) / 6
    clip = lambda value: min(1, max(0, value))
    scores = {
        'structure': 15 * (surface['fscore'] + mean('silhouette_IoU')),
        'appearance': 30 * clip(mean('foreground_union_SSIM')),
        'detail_restoration': detail['total_score'], 'music': music['score'], 'sfx': sfx['score']
    }
    scores['total'] = sum(scores.values())
    expected = load('expected-score.json')['scores']
    for key, value in scores.items():
        assert math.isclose(value, expected[key], rel_tol=1e-10, abs_tol=1e-10), key
    print(json.dumps({'scoring_version': 'scv-showcase-ssim-v3', 'scores': scores, 'display_total': f'{scores["total"]:.2f}'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
