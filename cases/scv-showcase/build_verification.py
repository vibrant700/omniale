"""Build the public SCV scoring verification ZIP from reviewed repository files."""
from pathlib import Path
import hashlib
import json
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE = HERE / 'verification'
SITE = REPO / 'docs/scv-showcase'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    files = sorted(p for p in SOURCE.rglob('*') if p.is_file()
                   and p.name not in {'manifest.json', '.gitattributes'}
                   and '__pycache__' not in p.parts and p.suffix != '.pyc')
    records = [{'path': p.relative_to(SOURCE).as_posix(), 'bytes': p.stat().st_size,
                'sha256': digest(p)} for p in files]
    manifest = {'protocol_version': 'scv-showcase-verification-v1',
                'files': records, 'manifest_excludes_itself': True}
    (SOURCE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    archive = SITE / 'assets/scoring-verification-v1.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in files + [SOURCE / 'manifest.json']:
            entry = zipfile.ZipInfo('scv-scoring-verification-v1/' + path.relative_to(SOURCE).as_posix(),
                                    date_time=(2026, 11, 23, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            bundle.writestr(entry, path.read_bytes())
    # Existing asset entries are already verified; only this download is added/updated.
    asset_manifest_path = SITE / 'assets-manifest.json'
    asset_manifest = json.loads(asset_manifest_path.read_text(encoding='utf-8'))
    rel = archive.relative_to(SITE).as_posix()
    asset_manifest = [r for r in asset_manifest if r['path'] != rel]
    asset_manifest.append({'path': rel, 'mime': 'application/zip', 'bytes': archive.stat().st_size,
                           'sha256': digest(archive)})
    asset_manifest.sort(key=lambda item: item['path'])
    asset_manifest_path.write_text(json.dumps(asset_manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    info = {'file': rel, 'bytes': archive.stat().st_size, 'sha256': digest(archive),
            'protocol_version': manifest['protocol_version'], 'file_count': len(files) + 1}
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
