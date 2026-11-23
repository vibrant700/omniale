"""Verify every file listed in the unpacked scoring package manifest (no dependencies)."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Missing/invalid package file: {item['path']}")
        if path.stat().st_size != item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError(f"Integrity mismatch: {item['path']}")
    print(f"Verified {len(manifest['files'])} package files; protocol {manifest['protocol_version']}")


if __name__ == '__main__':
    main()
