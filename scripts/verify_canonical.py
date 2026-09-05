#!/usr/bin/env python3
"""Read-only verification; --seal writes once, only before release."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CAN=ROOT/'canonical'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text())
def canonical_paths(root=ROOT):
    return sorted(p for p in (root/'canonical').rglob('*') if p.is_file() and p.name!='freeze.json')

def check_integrity(root=ROOT):
    freeze=load(root/'canonical/metadata/freeze.json')
    actual={str(p.relative_to(root)) for p in canonical_paths(root)}
    expected=set(freeze['files'])
    if actual!=expected:raise ValueError(f'Canonical file set changed: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}')
    for path,h in {**freeze['files'],**freeze['workflow_files']}.items():
        p=root/path
        if not p.is_file() or digest(p)!=h:raise ValueError('Frozen hash mismatch: '+path)
    # Once committed, also pin the seal itself to its latest committed Git blob.
    seal_rel='canonical/metadata/freeze.json'
    tracked=subprocess.run(['git','cat-file','-e','HEAD:'+seal_rel],cwd=root,capture_output=True)
    if tracked.returncode==0:
        committed=subprocess.check_output(['git','show','HEAD:'+seal_rel],cwd=root)
        if committed!=(root/seal_rel).read_bytes():raise ValueError('Freeze seal differs from committed Git blob')
    return freeze


def audit_source_and_content():
    snapshot=load(CAN/'metadata/source_snapshot.json')
    for row in snapshot:
        assert digest(ROOT/row['path'])==row['sha256'],('source changed',row['path'])
    phase1=load(ROOT/'research/phase1/source-audit.json')
    assert all(digest(ROOT/r['path'])==r['sha256'] for r in phase1['files'])
    with zipfile.ZipFile(ROOT/'Dream-of-Red-Chamber-master.zip') as archive:
        assert archive.testzip() is None
        for row in snapshot:
            if row['path'].endswith('.tex'):
                assert hashlib.sha256(archive.read(row['path'])).hexdigest()==row['sha256']
    manifest=load(CAN/'metadata/chapter_manifest.json')
    assert [x['chapter'] for x in manifest]==list(range(1,81))
    assert {p.name for p in (CAN/'chapters').iterdir()}=={f'{n:03d}.md' for n in range(1,81)}
    prov=load(CAN/'metadata/provenance.json');records=prov['records']
    byid={x['id']:x for x in records};assert len(byid)==len(records)
    for row in manifest:
        n=row['chapter'];p=ROOT/row['path'];clean=p.read_text();raw=(ROOT/row['source']).read_text()
        assert digest(p)==row['sha256']
        assert clean.startswith(f'# 第{n:03d}回　{row["title"]}\n\n')
        assert not re.search(r'\\(?:footnote|begin|chapter)|程甲|程乙|周汝昌|戴不凡|</|〈|（',clean)
        lo=row['selected_source_span']['start_offset'];hi=row['selected_source_span']['end_offset']
        # Independently replay the disclosed patch ledger. No undisclosed lexical edits.
        edits=[r for r in records if r['chapter']==n and r['canonical_replacement'] is not None
               and lo<=r['location']['start_offset'] and r['location']['end_offset']<=hi]
        edits.sort(key=lambda r:r['location']['start_offset'])
        cursor=lo;parts=[]
        for r in edits:
            a=r['location']['start_offset'];b=r['location']['end_offset'];assert a>=cursor
            if r['current_text_ref']:
                assert (ROOT/r['current_text_ref']).read_text()==raw[a:b]
            else:assert r['current_text']==raw[a:b],r['id']
            parts.extend([raw[cursor:a],r['canonical_replacement']]);cursor=b
        parts.append(raw[cursor:hi]);replay=''.join(parts)
        replay=re.sub(r'\\(?:begin|end)\{[^}]+\}|\\footnotemark(?:\[[^\]]*\])?|\\scriptsize\b|[{}]','',replay)
        replay=replay.replace('\\newline','\n')
        replay='\n\n'.join(x.strip() for x in replay.splitlines() if x.strip())+'\n'
        assert clean.split('\n\n',1)[1]==replay,('undisclosed body change',n)
        assert re.findall(r'〔(?:缺文|疑缺|待定|缺字|补配起):(P\d+)〕',clean)==[m for m in re.findall(r'〔(?:缺文|疑缺|待定|缺字|补配起):(P\d+)〕',clean) if m in byid]
        source_map=load(CAN/f'metadata/source_map/{n:03d}.json')['lines']
        actual_lines=[i for i,l in enumerate(clean.splitlines(),1) if i>1 and l.strip()]
        assert [x['canonical_line'] for x in source_map]==actual_lines
        assert all(1<=x['source_start_line']<=x['source_end_line']<=len(raw.splitlines()) for x in source_map)
    r62=manifest[61];s62=(ROOT/r62['source']).read_text();a=r62['selected_source_span']['start_offset'];b=r62['selected_source_span']['end_offset']
    s61=(ROOT/manifest[60]['source']).read_text().split('\n',1)[1]
    assert s62.split('\n',1)[1].replace(s62[a:b],'',1)==s61
    assert s62[a:b].startswith('話說平兒出來吩咐林之孝家的道') and s62[a:b].endswith('不知端詳，且聽下回分解。')
    r67=manifest[66];raw67=(ROOT/r67['source']).read_text();b=r67['selected_source_span']['end_offset']
    assert raw67[b:].startswith('\\section*{程甲本}')
    # Byte-only comparison of excluded appendix: it is never printed or imported as evidence.
    for ed,idx in [('紅樓夢庚辰本',0),('脂硯齋重評石頭記',1)]:
        raw=(ROOT/f'Dream-of-Red-Chamber-master/{ed}/chapters/chapter67.tex').read_bytes()
        suffix=raw[raw.index('\\section*{程甲本}'.encode()):]
        assert (ROOT/f'excluded_sources/version_audit/067-{idx}-chengjia.tex').read_bytes()==suffix
    for row in load(ROOT/'excluded_sources/version_audit/inventory.json'):
        assert digest(ROOT/row['path'])==row['sha256']
    # Both full source trees were inventoried; no unseen chapter numbers enter via import.
    for row in snapshot:
        m=re.search(r'/chapters/chapter(\d+)\.tex$',row['path'])
        if m:assert 1<=int(m[1])<=80
    for row in prov['note_records']:
        assert 1<=row['chapter']<=80
        assert not any(x in row['current_text'] for x in ['周汝昌','戴不凡','《程甲本》'])
        assert row['layer'] in ['zhiyan','editorial','undetermined']
    return {'chapters':80,'source_and_archive_hashes':len(snapshot),'patch_records':len(records),
            'annotation_records':len(prov['note_records']),'chapter62_local_extraction':True,
            'chapter67_appendix_separated':True,'source_unchanged':True,'all_lexical_changes_disclosed':True}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seal',action='store_true');ap.add_argument('--audit-sources',action='store_true');a=ap.parse_args()
    f=CAN/'metadata/freeze.json'
    if a.seal:
        if f.exists():raise SystemExit('Refuse to reseal a frozen release')
        result=audit_source_and_content()
        workflow=['AGENTS.md','.ignore','scripts/build_canonical.py','scripts/verify_canonical.py','scripts/read_canonical.py','excluded_sources/README.md','excluded_sources/version_audit/inventory.json']
        data={'release':'red-chamber-canonical-v1','state':'frozen','created_date':'2026-09-05',
            'base_git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'commit_resolution':'The dataset commit is git log -1 --format=%H -- canonical/metadata/freeze.json; a commit cannot embed its own SHA.',
            'files':{str(p.relative_to(ROOT)):digest(p) for p in canonical_paths()},
            'workflow_files':{x:digest(ROOT/x) for x in workflow},'validation':result}
        canonical_digest=hashlib.sha256(json.dumps(data['files'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        data['dataset_sha256']=canonical_digest
        f.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    freeze=check_integrity()
    result=audit_source_and_content() if a.audit_sources or a.seal else {'integrity':'pass'}
    print(json.dumps({'release':freeze['release'],'dataset_sha256':freeze['dataset_sha256'],**result},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
