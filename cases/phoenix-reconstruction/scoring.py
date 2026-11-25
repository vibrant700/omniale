"""Score existing ten-frame measurements with the user-approved 30/30/30/10 protocol."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from statistics import mean

REVISION = 'phoenix-ten-frames-iou-f1-ssim-audio-v2'
FRAMES = list(range(0, 100, 11))
WEIGHTS = {'view_coverage': 30, 'geometry': 30, 'appearance': 30, 'audio': 10}


def without_removed_metric(data):
    if isinstance(data, dict):
        return {k: without_removed_metric(v) for k, v in data.items() if 'lpips' not in k.lower()}
    if isinstance(data, list):
        return [without_removed_metric(v) for v in data]
    return data


def make_reports(evaluation):
    def read(name):
        return json.loads((evaluation / name).read_text(encoding='utf-8'))

    source = read('score.json')
    geometry = read('geometry_metrics.json')
    images = read('image_metrics.json')
    audio = read('gemini-neon-audio/audio-score.json')
    assert source['frames'] == FRAMES
    assert {int(f) for f in geometry['frames']} == set(FRAMES)
    assert {int(f) for f in images['frames']} == set(FRAMES)
    f1 = mean(geometry['frames'][str(f)]['input_visible_surface']['0.005']['f1'] for f in FRAMES)
    iou = mean(images['frames'][str(f)][v]['IoU'] for f in FRAMES for v in ['I1', 'I2', 'I3', 'T1'])
    ssim = mean(images['frames'][str(f)]['T1']['appearance']['SSIM'] for f in FRAMES)
    for actual, stored in [(f1, geometry['mean_F1']), (iou, images['mean_IoU']), (ssim, images['mean_SSIM'])]:
        assert abs(actual - stored) < 1e-12
    assert sum(item['score'] for item in audio['items']) == audio['total'] == source['scores']['audio']
    scores = {'view_coverage': 30 * iou, 'geometry': 30 * f1,
              'appearance': 30 * max(0, min(1, ssim)), 'audio': audio['total']}
    scores['non_audio_subtotal'] = sum(scores[k] for k in ['view_coverage', 'geometry', 'appearance'])
    scores['full_total_100'] = scores['non_audio_subtotal'] + scores['audio']
    provenance = {
        'revision': REVISION, 'revision_date': '2026-11-25',
        'measurement_reused': True,
        'source_files_sha256': {name: hashlib.sha256((evaluation / name).read_bytes()).hexdigest()
                                for name in ['score.json', 'PROTOCOL.json', 'geometry_metrics.json',
                                             'image_metrics.json', 'gemini-neon-audio/audio-score.json']},
        'description': 'User-approved reweighting of existing fixed-frame measurements; no new solver run or measurement.',
    }
    score = {k: deepcopy(source[k]) for k in ['model', 'effort', 'framework', 'frames', 'elapsed_seconds',
                                              'tool_calls', 'audio_evaluated', 'engineering',
                                              'native_GPU_rendered_frames', 'audio_review']}
    score.update({'protocol': REVISION,
                  'raw': {'F1_at_0.5pct_reference_diagonal': f1, 'IoU': iou, 'SSIM': ssim},
                  'scores': scores, 'maxima': {**WEIGHTS, 'non_audio_subtotal': 90, 'full_total_100': 100},
                  'components': {'silhouette_IoU': scores['view_coverage'], 'surface_F1': scores['geometry'],
                                 'SSIM': scores['appearance'], 'audio': scores['audio']},
                  'score_formula': '30*mean_IoU + 30*mean_F1 + 30*clip(mean_SSIM,0,1) + audio',
                  'provenance': provenance})
    protocol = without_removed_metric(read('PROTOCOL.json'))
    protocol.update({'revision': REVISION, 'measurement_protocol': geometry['protocol'],
                     'freeze_before_solver': False,
                     'measurement_settings_frozen_before_solver': True,
                     'weights': WEIGHTS, 'score_formula': score['score_formula'],
                     'audio': 'Five criteria scored 0/1/2; accepted supplied Gemini 4 Neon review, summed /10.',
                     'provenance': provenance})
    images = without_removed_metric(images)
    images.update({'published_metrics': ['silhouette_IoU', 'RGB_foreground_SSIM'],
                   'provenance': {'source_sha256': provenance['source_files_sha256']['image_metrics.json'],
                                  'description': 'IoU and SSIM retained from original measurements; only current metrics published.'}})
    images['versions'] = {k: v for k, v in images['versions'].items() if k not in ['torch', 'torchvision']}
    return {'score.json': score, 'PROTOCOL.json': protocol, 'image_metrics.json': images}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evaluation', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    reports = make_reports(args.evaluation)
    for name, data in reports.items():
        (args.output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(reports['score.json']['scores'], indent=2))
