"""Download versioned public evaluation inputs and verify their SHA-256 values."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def matches(path, item):
    return path.is_file() and path.stat().st_size == item['bytes'] and sha256(path) == item['sha256']


def extract_input(archive, destination):
    """Extract the small, public input archive without accepting escaping paths."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            target = (destination / item.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError('Input archive member escapes its destination')
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(item) as source, target.open('wb') as sink:
                shutil.copyfileobj(source, sink)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('work'))
    parser.add_argument('--group', choices=['images', 'asset', 'av', 'weights', 'all'], default='images',
                        help='asset/all includes the 297.2 MB scoring reference')
    parser.add_argument('--verify-only', action='store_true', help='Check existing downloads without network access')
    args = parser.parse_args()
    output = args.output.resolve()
    manifest = json.loads((PACKAGE / 'config/resources.json').read_text(encoding='utf-8'))
    selected = [r for r in manifest['resources'] if args.group == 'all' or args.group in r['groups']]
    for item in selected:
        target = output / item['path']
        if not target.resolve().is_relative_to(output):
            raise ValueError('Resource path escapes output directory')
        if not matches(target, item):
            if args.verify_only:
                raise ValueError(f"Missing or mismatched resource: {item['path']}")
            target.parent.mkdir(parents=True, exist_ok=True)
            # Keep a previous complete file until the replacement is fully verified.
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False, suffix='.part') as temporary:
                temporary_path = Path(temporary.name)
            try:
                print(f"Downloading {item['path']} ({item['bytes']} bytes)", flush=True)
                request = urllib.request.Request(item['url'], headers={'User-Agent': 'OmniALE-SCV-verification/1'})
                with urllib.request.urlopen(request, timeout=120) as source, temporary_path.open('wb') as sink:
                    shutil.copyfileobj(source, sink)
                if not matches(temporary_path, item):
                    raise ValueError(f"SHA-256/size mismatch: {item['path']}")
                temporary_path.replace(target)
            finally:
                temporary_path.unlink(missing_ok=True)
        print(f"Verified {item['path']}", flush=True)
    # Re-extract from the verified archive, even if an older extraction is present.
    archive = output / 'agent-input.zip'
    if any(r['path'] == 'agent-input.zip' for r in selected):
        extract_input(archive, output / 'agent-input')
    print(f'Completed {len(selected)} resources in {output}', flush=True)


if __name__ == '__main__':
    main()
