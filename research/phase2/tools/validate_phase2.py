#!/usr/bin/env python3
"""Independently verify published evidence against the allowlisted reader."""
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from audit_data import ROOT, BASE, source

def main():
    integrity=json.loads(subprocess.check_output([sys.executable,str(ROOT/'scripts/verify_canonical.py')],cwd=ROOT,text=True))
    assert integrity['integrity']=='pass'
    data=json.loads((BASE/'foreshadowing.json').read_text())
    rows=data['evidence']; ids=[r['id'] for r in rows]; idset=set(ids)
    assert len(ids)==len(idset)
    assert ids==[f'F-{i:04}' for i in range(1,len(rows)+1)]
    assert len(data['key_to_id'])==len(rows)
    assert set(data['key_to_id'].values())==idset
    required={'id','types','layer','source_class','chapter','location','characters','quote','context','direct_meaning',
        'future_direction','possible_directions','alternatives','strength','confidence','is_zhiyan','has_version_issue',
        'version_refs','version_note','related_evidence','remarks','status_at_80','contamination','independence_group'}
    freeze=json.loads((ROOT/'canonical/metadata/freeze.json').read_text())
    corpus={}; qualified_notes={}; totals={}
    for c in range(1,81):
        _,body=source(c,'main');_,notes=source(c,'zhiyan')
        corpus[c]=body;qualified_notes[c]={n['id']:n for n in notes}
        totals[c]={'main':len(body.splitlines()),'zhiyan':len(notes)}
    for r in rows:
        assert required<=set(r),r['id']
        assert 1<=r['chapter']<=80
        assert r['strength'] in 'ABCD' and 0<=r['confidence']<=100
        assert r['layer'] in ('正文','脂批') and r['is_zhiyan']==bool(r['note_id'])
        assert r['context'] and r['direct_meaning'] and r['future_direction'] and r['alternatives'] and r['possible_directions']
        assert r['status_at_80'] in ('framework','unresolved','partially_realized','realized_before_80')
        assert not re.search(r'〔(?:缺文|缺字|疑缺|待定|补配起):',r['quote']),r['id']
        if r['contamination']=='POTENTIAL_CONTAMINATION':assert r['strength']=='D'
        loc=r['location']; chapter=r['chapter']
        if r['is_zhiyan']:
            note=qualified_notes[chapter][r['note_id']]
            assert note['allowed_for_inference']=='commentary_only_explicit_opt_in'
            text=note['current_text']; expected=f'canonical/annotations/zhiyan/{chapter:03}.json'
            assert loc['container']=='note.current_text'
            assert loc['record_selector']=={'id':r['note_id'],'field':'current_text'}
        else:
            text=corpus[chapter]; expected=f'canonical/chapters/{chapter:03}.md'
            assert hashlib.sha256(text.encode()).hexdigest()==loc['sha256']
            assert loc['container']=='canonical_file'
        assert loc['path']==expected and loc['sha256']==freeze['files'][expected]
        assert text[loc['start_offset']:loc['end_offset']]==r['quote'],r['id']
        assert text[:loc['start_offset']].count('\n')+1==loc['start_line']
        assert text[:loc['end_offset']].count('\n')+1==loc['end_line']
        assert set(r['related_evidence'])<=idset and r['id'] not in r['related_evidence']
        assert len(r['related_evidence'])==len(set(r['related_evidence']))
        assert set(r['themes'])<=set(data['themes'])
        if chapter in (64,67):assert r['version_details']['depends_on_supplement']
        if not r['is_zhiyan'] and chapter==22:
            assert r['version_details']['depends_on_supplement']==(loc['start_offset']>text.index('〔补配起:P00021〕'))
        if not r['is_zhiyan'] and chapter in (17,18,19,80):assert loc['start_line']>1
    for category,prefix in [('conflicts','CONFLICT'),('unresolved_questions','Q')]:
        seq=data[category]
        assert [x['id'] for x in seq]==[f'{prefix}-{i:04}' for i in range(1,len(seq)+1)]
        for item in seq:
            refs=item['evidence_ids'] if prefix=='Q' else item['left_evidence']+item['right_evidence']
            assert refs and set(refs)<=idset
            if prefix=='Q':assert item['answer'] is None
    people='贾宝玉 林黛玉 薛宝钗 王熙凤 史湘云 贾探春 贾迎春 贾惜春 妙玉 巧姐 李纨 秦可卿 贾母 贾政 王夫人 贾琏 贾赦 袭人 晴雯 紫鹃 香菱 薛蟠 贾雨村 甄士隐'.split()
    assert set(people)<=set(data['character_index'])
    for person,refs in data['character_index'].items():assert refs==[r['id'] for r in rows if person in r['characters']]
    assert set(data['theme_index'])=={f'T-{i:02}' for i in range(1,16)}
    for theme,refs in data['theme_index'].items():assert refs==[r['id'] for r in rows if theme in r['themes']]
    assert sum(r['key'].startswith('C005-ALBUM-') for r in rows)==14
    assert sum(r['key'].startswith('C005-SONG-') for r in rows)==14
    assert sum(r['key'].startswith('C063-FLOWER') for r in rows)==8
    assert sum(r['key'].startswith('C064-WUMEI') for r in rows)==5
    yuan=next(r for r in rows if r['key']=='C005-ALBUM-A05')
    assert '虎兔' in yuan['quote'] and 'P00006' in yuan['version_refs']
    paired=[r for r in rows if r['independence_group']=='C022-BAOCHAI-SUPPLEMENT'];assert len(paired)==2
    cov=json.loads((BASE/'audit_coverage.json').read_text())
    assert [c['chapter'] for c in cov['chapters']]==list(range(1,81))
    logs=[json.loads(l) for l in (BASE/'work/audit_forward.jsonl').read_text().splitlines()]
    for c in cov['chapters']:
        chapter=c['chapter']
        assert c['reverse_decision']
        for layer in ('main','zhiyan'):
            assert c['forward'][layer]['total_units']==totals[chapter][layer]
            seen=set()
            for log in logs:
                if log['chapter']==chapter and log['layer']==layer:seen.update(range(log['start'],log['end']+1))
            assert set(range(1,totals[chapter][layer]+1))<=seen
    reverse=json.loads((BASE/'work/reverse_decisions.json').read_text())
    assert [c for c,_ in reverse]==list(range(80,0,-1))
    markdown=(BASE/'foreshadowing.md').read_text()
    assert re.findall(r'^## (F-\d{4})$',markdown,re.M)==ids
    required_files=['foreshadowing.md','foreshadowing.json','character_evidence_index.md','theme_evidence_index.md',
        'conflicts.md','unresolved_questions.md','phase2_report.md','special_inventory.md','audit_log.md']
    for name in required_files:
        text=(BASE/name).read_text();assert text
        if name.endswith('.md'):
            refs=set(re.findall(r'\bF-\d{4}\b',text));assert refs<=idset,(name,refs-idset)
    stats=data['stats']
    assert stats['evidence']==len(rows)
    assert stats['strength']==dict(Counter(r['strength'] for r in rows))
    assert stats['layers']==dict(Counter(r['layer'] for r in rows))
    assert stats['conflicts']==len(data['conflicts']) and stats['questions']==len(data['unresolved_questions'])
    result={'status':'pass','canonical_integrity':integrity,'evidence_verified':len(rows),
        'quote_and_location_failures':0,'dangling_references':0,'required_characters':len(people),
        'themes':15,'chapter5_judgments':14,'chapter5_songs':14,'chapter63_flower_lots':8,
        'forward_chapter_layer_deliveries':160,'reverse_chapter_decisions':80,
        'semantic_review_limit':'机器验证文字和引用，不证明文学解释唯一正确；人工两轮审读记录另见audit_log.md。',
        'source_layers':stats['layers'],'strength':stats['strength'],
        'potential_contamination':stats['potential_contamination'],
        'artifact_sha256':{name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in required_files}}
    (BASE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='artifact_sha256'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
