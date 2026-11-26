"""Build a local review package using only the allowed V2 visual inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
VISUAL_INPUTS = [
    'cameras.json', 'timeline.json', 'scene_setup.json',
    'ASSET-ATTRIBUTION.txt', 'INPUT-USE.md',
    'reference/I1.mp4', 'reference/I2.mp4', 'reference/I3.mp4',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-candidate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    source = args.source_candidate.resolve()
    out = args.out.resolve()
    if out == source or source in out.parents or out in source.parents:
        raise ValueError('Source and output directories must be independent.')
    if out.exists():
        raise FileExistsError('Use a new output directory to preserve prior drafts.')
    timeline = json.loads((source / 'timeline.json').read_text(encoding='utf-8'))
    assert (timeline['fps'], timeline['frame_count'], timeline['duration_s']) == (30, 180, 6)
    payload = {name: (source / name).read_bytes() for name in VISUAL_INPUTS}
    payload.update({name: (HERE / name).read_bytes()
                    for name in ['TASK.md', 'SCORING.md', 'ENVIRONMENT.md']})
    out.mkdir(parents=True)
    candidate = out / 'candidate'
    for name, data in payload.items():
        path = candidate / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    archive = out / 'phoenix-agent-input-v3-draft.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            package.writestr(info, data)
    with zipfile.ZipFile(archive) as package:
        assert set(package.namelist()) == set(payload)
        assert package.testzip() is None
        for name, data in payload.items():
            assert package.read(name) == data
        assert not any(name.lower().endswith(('.wav', '.blend', '.glb', '.png', '.npz'))
                       or Path(name).name == 'T1.mp4' for name in package.namelist())
    report = {
        'task_version': 'phoenix-v3-independent-foley-draft',
        'state': 'draft_not_frozen_for_experiment',
        'solver_runs': 0,
        'reference_media': 'V2 visual input bytes reused without re-encoding',
        'source_candidate': str(source),
        'files': {name: {'bytes': len(data), 'sha256': sha(data)}
                  for name, data in sorted(payload.items())},
        'archive_sha256': sha(archive.read_bytes()),
        'no_supplied_sound_or_private_truth': True,
    }
    (out / 'package-verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'archive': str(archive), 'files': len(payload),
                      'bytes': archive.stat().st_size, 'verified': True}, ensure_ascii=True))


if __name__ == '__main__':
    main()
