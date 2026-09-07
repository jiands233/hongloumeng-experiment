#!/usr/bin/env python3
"""Load Phase 2 drafts; literary source access goes through the frozen reader."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'research/phase2'

def drafts():
    result = []
    for path in sorted((BASE / 'work').glob('evidence_*.json')):
        result.extend(json.loads(path.read_text()))
    for path in sorted((BASE / 'work').glob('additional*.jsonl')):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            c, k, people, kinds, quote, context, direct, future, alt, strength, confidence, themes, note, status = json.loads(line)
            result.append(dict(chapter=c, key=k, characters=people.split('、'), types=kinds.split('、'),
                               quote=quote, context=context, direct_meaning=direct, future_direction=future,
                               possible_directions=[future], alternatives=[alt], strength=strength,
                               confidence=confidence, themes=themes.split(), note_id=note,
                               layer='脂批' if note else '正文', status_at_80=status,
                               version_refs=[], version_note='', related_keys=[],
                               contamination='CLEAR_LOCAL_SUPPORT', remarks=alt))
    overrides = BASE / 'work/overrides.json'
    patches = json.loads(overrides.read_text()) if overrides.exists() else {}
    for row in result:
        row.update(patches.get(row['key'], {}))
    return sorted(result, key=lambda r: (r['chapter'], r['key']))

def source(chapter, layer):
    raw = subprocess.check_output([sys.executable, str(ROOT / 'scripts/read_canonical.py'), str(chapter),
                                   '--layer', layer], cwd=ROOT, text=True)
    qualification, end = json.JSONDecoder().raw_decode(raw)
    body = raw[end:].lstrip('\n')
    if layer == 'zhiyan':
        return qualification, json.loads(body.split('\n', 1)[1])
    # The frozen reader adds exactly one print newline after the file.
    return qualification, body[:-1]

if __name__ == '__main__':
    rows = drafts()
    if sys.argv[1] == 'keys':
        for row in rows:
            print(row['key'], row['strength'], row['note_id'] or '', row['quote'])
    elif sys.argv[1] == 'check':
        errors = []
        for chapter in range(1, 81):
            _, main = source(chapter, 'main')
            _, notes = source(chapter, 'zhiyan')
            notes = {n['id']: n for n in notes}
            for row in [r for r in rows if r['chapter'] == chapter]:
                body = notes.get(row['note_id'], {}).get('current_text', '') if row['note_id'] else main
                if row['quote'] not in body:
                    errors.append({'key': row['key'], 'quote': row['quote'], 'note_id': row['note_id']})
        print(json.dumps({'count': len(rows), 'quote_errors': errors}, ensure_ascii=False, indent=2))
    elif sys.argv[1] == 'reverse':
        import re
        chapter = int(sys.argv[2])
        selected = [r for r in rows if r['chapter'] == chapter]
        qualification, main = source(chapter, 'main')
        _, notes = source(chapter, 'zhiyan')
        print(json.dumps(qualification, ensure_ascii=False))
        for row in selected:
            print(row['key'], row['quote'], '|', row['future_direction'], '|', row['status_at_80'])
        print('未入库候选（关键词仅用于查漏，不自动入库）:')
        for number, line in enumerate(main.splitlines(), 1):
            if any(r['quote'] in line for r in selected if not r['note_id']):
                continue
            for match in re.finditer(r'將來|後事|後文|日後|他日|伏線|讖|終身|三春|一旦|百年|終有|將散', line):
                print(f'L{number}:', line[max(0, match.start()-45):match.end()+85])
        known_notes = {r['note_id'] for r in selected}
        for note in notes:
            if note['id'] not in known_notes and re.search(r'後文|後事|他日|伏|讖|結局|末回|後回|後數|終身|將來|死期', note['current_text']):
                print(note['id'], note['current_text'])
