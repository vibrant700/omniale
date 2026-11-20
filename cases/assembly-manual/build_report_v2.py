"""Restore the report UI and validate the reviewed public result data.

No private run files or API calls are needed. This script does not change scores.
"""
import hashlib
import json
import shutil
from pathlib import Path

CASE = Path(__file__).resolve().parent
SITE = CASE.parents[1] / 'docs' / 'assembly-manual'


def load(name):
    return json.loads((SITE / name).read_text(encoding='utf-8'))


def asset(relative):
    path = (SITE / relative).resolve()
    assert path.is_relative_to(SITE.resolve()), relative
    assert path.is_file(), relative
    return path


def main():
    data = load('data-v2.json')
    execution = load('execution-v2.json')
    assert data['schemaVersion'] == execution['schemaVersion'] == 2
    assert data['defaultSystem'] in data['systems']
    assert data['scoring']['weights'] == [50, 20, 30]
    asset(data['source']['preview'])
    asset(data['source']['poster'])
    for key, system in data['systems'].items():
        qa = system['qa']
        assert len(qa) == 10
        assert len({q['id'] for q in qa}) == 10
        for q in qa:
            assert len(q['qaChecks']) == len(q['referenceClaims']) == 4
            assert len(q['evidenceChecks']) == 2
            assert abs(sum(c['score'] for c in q['qaChecks']) - q['scores']['qa']) < 1e-8
            assert abs(sum(c['score'] for c in q['evidenceChecks']) - q['scores']['evidence']) < 1e-8
        manual = system['manual']
        assert len(manual['dimensions']) == 4
        assert len({e['root_key'] for e in manual['errors']}) == len(manual['errors'])
        errors = {e['id']: e for e in manual['errors']}
        all_ids = []
        for dim in manual['dimensions']:
            all_ids += dim['errorIds']
            assert all(errors[e]['owner'] == dim['id'] for e in dim['errorIds'])
            assert sum(errors[e]['units'] for e in dim['errorIds']) == dim['units']
            expected_level = 0 if dim['criticalZero'] or dim['units'] >= 4 else 3 if dim['units'] == 0 else 2 if dim['units'] == 1 else 1
            assert expected_level == dim['level']
            assert abs(dim['score'] - dim['level'] / 3 * dim['weight']) < 1e-8
        assert len(all_ids) == len(set(all_ids)) == len(errors)
        scores = system['result']['groups']
        assert abs(sum(q['scores']['qa'] for q in qa) - scores['qa']['score']) < 1e-8
        assert abs(sum(q['scores']['evidence'] for q in qa) - scores['evidence']['score']) < 1e-8
        assert abs(sum(d['score'] for d in manual['dimensions']) - scores['manual']['score']) < 1e-8
        assert abs(sum(g['score'] for g in scores.values()) - system['result']['score']) < 1e-8
        delivery = system['delivery']
        assert delivery['pages'] == len(delivery['pageImages']) == len(delivery['pageTopics'])
        for name, hash_name in [('pdf','pdfSha256'),('docx','docxSha256'),('editableBundle','bundleSha256')]:
            assert hashlib.sha256(asset(delivery[name]).read_bytes()).hexdigest() == delivery[hash_name]
        for path in delivery['pageImages'] + [delivery['answers']] + [i['src'] for i in manual.get('reviewImages',[])]:
            asset(path)
        print(f"{key}: {system['result']['scoreDisplay']}/100, {delivery['pages']} pages; validated")
    for name in ['index.html','case.css','app.js']:
        shutil.copyfile(CASE / 'report-v2-template' / name, SITE / name)
    print('Restored report-v2 UI; data, scores and original deliveries are unchanged.')


if __name__ == '__main__':
    main()
