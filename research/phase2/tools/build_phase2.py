#!/usr/bin/env python3
"""Deterministic Phase 2 publication from reviewed drafts and frozen reader output."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from audit_data import ROOT, BASE, drafts, source

THEMES = dict(zip([f'T-{i:02}' for i in range(1, 16)],
    ['贾府衰败','宝玉精神道路','宝黛关系','金玉关系','十二钗命运','政治风险','经济崩坏',
     '婚姻与家族利益','死亡','离散','出家','盛衰循环','太虚幻境','第一回框架闭环','真假 / 梦幻 / 石头结构']))
PEOPLE = '贾宝玉 林黛玉 薛宝钗 王熙凤 史湘云 贾探春 贾迎春 贾惜春 妙玉 巧姐 李纨 秦可卿 贾母 贾政 王夫人 贾琏 贾赦 袭人 晴雯 紫鹃 香菱 薛蟠 贾雨村 甄士隐'.split()
ALIASES = {'花袭人':'袭人','红玉':'小红','林红玉':'小红','贾巧姐':'巧姐'}
STATUS = {'unresolved':'未闭环','partially_realized':'部分已应 / 后续仍开放',
          'realized_before_80':'80回内已应 / 已落空的比较样本','framework':'框架待闭合或总括'}

def write_json(name, data):
    (BASE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

def write_md(name, lines):
    text='\n'.join(lines)
    (BASE/name).write_text('\n'.join(line.rstrip() for line in text.splitlines()).rstrip()+'\n')

def links(ids):
    return ' '.join(f'[{i}](foreshadowing.md#{i.lower()})' for i in ids)

def main():
    manifest = json.loads((ROOT/'canonical/metadata/chapter_manifest.json').read_text())
    freeze = json.loads((ROOT/'canonical/metadata/freeze.json').read_text())
    provenance = json.loads((ROOT/'canonical/metadata/provenance.json').read_text())
    # Only metadata is projected; excluded or undetermined original text is never published.
    pmeta = {r['id']: {k:r.get(k) for k in ['id','chapter','kind','reason','is_supplement','confidence']}
             for r in provenance['records'] if r['id'].startswith('P')}
    rows = [r for r in drafts() if not r.get('exclude')]
    errors = []
    bodies, notes_by_chapter, counts = {}, {}, {}
    for chapter in range(1,81):
        qualification, body = source(chapter,'main')
        _, notes = source(chapter,'zhiyan')
        assert hashlib.sha256(body.encode()).hexdigest() == manifest[chapter-1]['sha256'], chapter
        bodies[chapter] = body
        notes_by_chapter[chapter] = notes
        counts[chapter] = {'main':len(body.splitlines()), 'zhiyan':len(notes)}
        source_map = json.loads((ROOT/f'canonical/metadata/source_map/{chapter:03}.json').read_text())['lines']
        for row in [r for r in rows if r['chapter']==chapter]:
            note = next((n for n in notes if n['id']==row['note_id']),None)
            if row['layer']=='脂批' and note is None:
                errors.append([row['key'],'note_not_allowed']); continue
            text = note['current_text'] if note else body
            if row['key'].startswith('C005-ALBUM'):
                q = row['quote']
                row['quote'] = q[q.index('畫'):] if '畫' in q else q
            starts = [m.start() for m in re.finditer(re.escape(row['quote']),text)]
            if not starts:
                errors.append([row['key'],'quote_missing']); continue
            occurrence = row.get('occurrence_index',0)
            if len(starts)>1 and 'occurrence_index' not in row:
                errors.append([row['key'],'ambiguous_quote',starts]); continue
            start = starts[occurrence]; end = start+len(row['quote'])
            loc = dict(path=f'canonical/annotations/zhiyan/{chapter:03}.json' if note else manifest[chapter-1]['path'],
                       sha256=freeze['files'][f'canonical/annotations/zhiyan/{chapter:03}.json'] if note else manifest[chapter-1]['sha256'],
                       start_offset=start,end_offset=end,offset_convention='Unicode [start,end)',
                       start_line=text[:start].count('\n')+1,end_line=text[:end].count('\n')+1,
                       container='note.current_text' if note else 'canonical_file',
                       note_id=row['note_id'],occurrence_index=occurrence)
            if note:
                loc['record_selector'] = {'id':note['id'],'field':'current_text'}
                loc['source_location_metadata'] = note['location']
                loc['label'] = '本地标作' + note['current_text'].split('：',1)[0] + '的批语（未认证）'
            row['location']=loc
            row['source_class']='B_脂批' if note else 'A_正文'
            row['is_zhiyan']=bool(note)
            row['characters']=list(dict.fromkeys(ALIASES.get(p,p) for p in row['characters']))
            row['chapter_qualification']=qualification
            chapter_refs = re.findall(r'P\d{5}', ' '.join(qualification['notes']))
            ownrefs=[]
            source_lines = [m for m in source_map if loc['start_line']<=m['canonical_line']<=loc['end_line']] if not note else []
            for p in provenance['records']:
                if p.get('chapter')!=chapter or not p['id'].startswith('P'): continue
                ploc=p.get('location',{})
                if any(m['source']==p.get('source') and m['source_start_line']<=ploc.get('end_line',-1)
                       and m['source_end_line']>=ploc.get('start_line',10**9) for m in source_lines):
                    ownrefs.append(p['id'])
            supplement = chapter in (64,67) or (not note and chapter==22 and start>body.index('〔补配起:P00021〕')) or bool(note and note.get('is_supplement'))
            if supplement:
                ownrefs += ['P00053'] if chapter==64 else ['P00055'] if chapter==67 else ['P00021','P00022'] if chapter==22 else []
            row['version_refs']=sorted(set(['G001']+row.get('version_refs',[])+chapter_refs+ownrefs))
            row['has_version_issue']=bool(chapter_refs or (note and note.get('nested_editorial_ids')))
            row['version_details']={'local_or_same_source_line_refs':sorted(set(ownrefs)),
                'chapter_context_refs':chapter_refs,'depends_on_supplement':supplement,
                'nested_editorial_ids':note.get('nested_editorial_ids',[]) if note else [],
                'scope':'同回资格不等于引文逐字受改；同行编号仅定位处理邻域。G001为全局未定位汇校。'}
            row['version_note']=('依赖有条件补配；' if supplement else '') + ('；'.join(n.rstrip('。') for n in qualification['notes']) if chapter_refs else '无已登记的局部问题') + '。G001全局上游汇校限制仍适用。'
            if row['key']=='C041-NMIAOYU':
                row['version_note']+=' 此条仅使用残存许可批语的“他日瓜州渡口”，隔离插入及缺失语境不用作推理。'
            if row['status_at_80']=='undetermined_at_shard_boundary':
                row['status_at_80']='framework' if chapter==1 else 'unresolved'
            if chapter==5:
                row['identity_basis']='人物名为本库检索标签；未署名图判/曲的归属是以字义及前80回对应建立的有条件识别，不把索引等同正文点名。'
                row['remarks']+=' A级仅指预示措辞明确，不包含人物识别或具体事件方式的确定性。'
                if row['key']=='C005-ALBUM-A01':row['status_at_80']='realized_before_80'
                if row['key'] in ['C005-ALBUM-A03','C005-ALBUM-A07','C005-ALBUM-A09','C005-ALBUM-A14','C005-SONG-S08','C005-SONG-S13']:
                    row['status_at_80']='partially_realized'
            else:
                row['identity_basis']='见上下文；同列人物可能是发言者、被指者或关联对象，不自动都是预言承受者。'
            if row['key'] in ('C062-CHAI-DUST','C062-YUCHAILINE'):
                row['contamination']='POTENTIAL_CONTAMINATION'
                row['strength']='D'
                row['remarks']+=' 风险在于将射覆中的物名转成人名/婚姻象征，不能排除训练记忆的联想；仅作辅助候选，禁止单独推论。'
            row['confidence_meaning']='衡量作为未来指向或必要反证的把握，不是事件发生概率。'
            row['provenance_ref']='canonical/metadata/provenance.json'
            row['independence_group']='C022-BAOCHAI-SUPPLEMENT' if row['key'] in ('C022-ANN-RIDDLECHAI','C022-RIDDLE-CHAI') else row['note_id'] or row['key']
    if errors:
        print(json.dumps(errors,ensure_ascii=False,indent=2)); raise SystemExit(1)
    rows.sort(key=lambda r:(r['chapter'], r['is_zhiyan'],r['location']['start_offset'],r['key']))
    key_to_id={r['key']:f'F-{i:04}' for i,r in enumerate(rows,1)}
    for row in rows: row['id']=key_to_id[row['key']]
    relations=json.loads((BASE/'work/relations.json').read_text())
    related=defaultdict(set)
    conflicts=[]
    for i,(title,left,right,why,coexist,stronger,defer) in enumerate(relations['conflicts'],1):
        lhs=[key_to_id[k] for k in left]; rhs=[key_to_id[k] for k in right]
        conflicts.append(dict(id=f'CONFLICT-{i:04}',title=title,left_evidence=lhs,right_evidence=rhs,
            conflict_reason=why,can_coexist=coexist,current_comparison=stronger,defer_to_phase3=defer))
        for a in lhs:
            related[a].update(rhs)
        for b in rhs:
            related[b].update(lhs)
    questions=[]
    for i,(question,people,keys,reason,priority,predict) in enumerate(relations['questions'],1):
        ids=[key_to_id[k] for k in keys.split()]
        questions.append(dict(id=f'Q-{i:04}',question=question,characters=people.split('、'),evidence_ids=ids,
                              reason_for_later_treatment=reason,importance=priority,predictability=predict,answer=None))
        for a in ids:related[a].update(set(ids)-{a})
    for row in rows:
        for k in row['related_keys']:
            if k in key_to_id: related[row['id']].add(key_to_id[k])
            else: raise ValueError(f'Unknown related key: {k}')
    # Explicit same-character continuity is a fallback, not a causal or supporting assertion.
    for row in rows:
        if not related[row['id']]:
            neighbors=[r for r in rows if r['id']!=row['id'] and set(r['characters'])&set(row['characters']) and set(r['themes'])&set(row['themes'])]
            neighbors.sort(key=lambda r:(abs(r['chapter']-row['chapter']),r['id']))
            related[row['id']].update(r['id'] for r in neighbors[:2])
        row['related_evidence']=sorted(related[row['id']]-{row['id']})
        row['related_evidence_semantics']='冲突、问题共引或同人物同主题邻近线索；关联不等于互相证实，具体冲突见conflicts。'
        row.pop('related_keys',None)
    byperson={p:[r['id'] for r in rows if p in r['characters']] for p in PEOPLE}
    for p in sorted({p for r in rows for p in r['characters']}):
        byperson.setdefault(p,[r['id'] for r in rows if p in r['characters']])
    bytheme={t:[r['id'] for r in rows if t in r['themes']] for t in THEMES}
    strength=Counter(r['strength'] for r in rows); layers=Counter(r['layer'] for r in rows)
    stats={'evidence':len(rows),'strength':dict(sorted(strength.items())),'layers':dict(layers),
           'conflicts':len(conflicts),'questions':len(questions),'status':dict(Counter(r['status_at_80'] for r in rows)),
           'potential_contamination':[r['id'] for r in rows if r['contamination']=='POTENTIAL_CONTAMINATION']}
    data={'schema_version':'phase2-v1','canonical_release':freeze['release'],
          'canonical_dataset_sha256':'a307c6629bb6fbd4a2c1a54560e3c53e4fec435a7017a6d83407bf1c00086a54',
          'scope':'仅前80回；不推演终局；正文与批语分层；C编校仅资格、D不确定原文不入库。',
          'strength_legend':{'A':'明确预示','B':'强烈暗示','C':'有意义但解释空间大','D':'弱证据，仅辅助'},
          'stats':stats,'key_to_id':key_to_id,'evidence':rows,'conflicts':conflicts,'unresolved_questions':questions,
          'character_index':byperson,'themes':THEMES,'theme_index':bytheme}
    write_json('foreshadowing.json',data)
    write_json('version_qualifications.json',{'scope':'C_编校版本元数据，不是文学证据；D_不确定原文未读取。',
        'global_limit':'G001上游汇校未逐字定位，不能声称纯净手稿。',
        'records':{i:pmeta[i] for i in sorted({p for r in rows for p in r['version_refs'] if p.startswith('P')})}})
    md=['# 前80回未来指向证据库','',
        '仅用于Phase 2。A级表示预示措辞明确，不代表具体终局已确定。置信度不是剧情概率。含已应和落空样本；未闭环不等于作者保证后80回逐项交代。',
        '正文、批语分别引用。本地批本标签未经手稿认证。人物索引尤其第5回匿名图判只作有条件归属。版本信息独立见 version_qualifications.json。',
        '稳定定位以冻结文件哈希和Unicode偏移为准；脂批偏移在指定N-ID的current_text内。全部JSON字段与Markdown同步生成。','']
    for r in rows:
        loc=r['location']; pos=f"{loc['path']} / " + (f"{r['note_id']} / " if r['note_id'] else '') + f"L{loc['start_line']} / Unicode [{loc['start_offset']},{loc['end_offset']}) / SHA256 {loc['sha256']}"
        fields=[('类型','、'.join(r['types'])),('来源层',r['layer']+'（'+r['source_class']+'）'),('回目',f"第{r['chapter']}回"),('位置',pos),('涉及人物','、'.join(r['characters']) or '群体 / 框架，未专指'),
            ('原文','\n\n> '+r['quote'].replace('\n','\n> ')),('上下文',r['context']),('直接含义',r['direct_meaning']),('未来指向',r['future_direction']),
            ('可能支持的剧情方向','；'.join(r['possible_directions'])),('其他可能解释','；'.join(r['alternatives'])),('证据强度',r['strength']),('置信度',str(r['confidence'])),
            ('是否来自脂批','是；'+loc.get('label','') if r['is_zhiyan'] else '否'),('是否存在版本问题',('是' if r['has_version_issue'] else '否（未登记局部问题，G001仍适用）')+'；'+r['version_note']+' 编号：'+', '.join(r['version_refs'])),
            ('关联证据',links(r['related_evidence']) or '暂无直接关联'),('截至80回状态',STATUS[r['status_at_80']]),
            ('备注',r['remarks']+' '+r['identity_basis']+' '+r['contamination'])]
        md += [f"## {r['id']}",'']+[f'【{k}】{v}\n' for k,v in fields]
    write_md('foreshadowing.md',md)
    chars=['# 人物证据索引','','同一条可关联多人，人物计数不可相加当证据总数。第5回匿名对象为有条件识别；此处不提供命运结论。','']
    lookup={r['id']:r for r in rows}
    for p,ids in byperson.items():
        topics=sorted({t for i in ids for t in lookup[i]['themes']})
        chars += [f'## 人物：{p}','',f'相关证据（{len(ids)}条）：',links(ids),'','证据主题：','']+[f'- {THEMES[t]}' for t in topics]+['']
    write_md('character_evidence_index.md',chars)
    ts=['# 主题证据索引','','证据可跨主题；索引关联不是因果证明。','']
    for t,name in THEMES.items():ts += [f'## {t} {name}','',links(bytheme[t]),'']
    write_md('theme_evidence_index.md',ts)
    cs=['# 冲突与反证','','含真正方向冲突、可并存的张力、层级差异及已被前80回事实限定的判断。不把它们全称为互斥结局。','']
    for c in conflicts:
        cs += [f"## {c['id']} {c['title']}",'','第一组：'+links(c['left_evidence']),'','第二组：'+links(c['right_evidence']),'',
               '为什么冲突：'+c['conflict_reason'],'','能否同时成立：'+c['can_coexist'],'','当前证据比较：'+c['current_comparison'],'',
               '是否留待Phase 3：'+('是；本阶段不裁决。' if c['defer_to_phase3'] else '无需为已知事实等候；只修正本阶段证据层级，不预测新事件。'),'']
    write_md('conflicts.md',cs)
    qs=['# 未解决问题数据库','','只列问题，不作答。高/中/低衡量当前可预测程度；中也不授权在本阶段推演。次要问题可能只是未收束细节，并不要求佚文必有答案。','']
    for q in questions:
        sources=sorted({f"第{lookup[i]['chapter']}回{lookup[i]['layer']}" for i in q['evidence_ids']})
        qs += [f"## {q['id']}",'',f"【问题】{q['question']}",f"【涉及人物】{'、'.join(q['characters'])}",f"【来源】{'；'.join(sources)}；精确位置见关联F记录。",
               '【相关证据】'+links(q['evidence_ids']),f"【为什么必须/可能在后文处理】{q['reason_for_later_treatment']}",f"【重要程度】{q['importance']}",f"【当前是否能够预测答案】{q['predictability']}",'【答案】本阶段不回答。','']
    write_md('unresolved_questions.md',qs)
    decisions=json.loads((BASE/'work/reverse_decisions.json').read_text())
    logs=[json.loads(l) for l in (BASE/'work/audit_forward.jsonl').read_text().splitlines()]
    coverage=[]
    for chapter in range(1,81):
        entry={'chapter':chapter,'forward':{},'reverse_decision':dict(decisions)[chapter]}
        for layer in ('main','zhiyan'):
            seen=set()
            for log in logs:
                if (log['chapter'],log['layer'])==(chapter,layer):seen.update(range(log['start'],log['end']+1))
            missing=sorted(set(range(1,counts[chapter][layer]+1))-seen)
            assert not missing,(chapter,layer,missing)
            entry['forward'][layer]={'total_units':counts[chapter][layer],'delivery_complete':True}
        coverage.append(entry)
    assert [c for c,_ in decisions]==list(range(80,0,-1))
    write_json('audit_coverage.json',{'forward_order':'1..80','reverse_order':'80..1',
        'method':'正序人工读完正文与允许批语；日志证明交付区间，语义审读声明及查漏决定另列。逆序复核既有候选及读取器派生的未覆盖提示，按需重读上下文；不是第二遍全文阅读。',
        'truncation_recovery':'77回首次整回输出截断后重读L17—23；其余前序读取在分段日志中完成。','chapters':coverage})
    rev=['# 正序与逆序审计记录','','正序80回正文与全部允许批语已读；自动交付覆盖验证不能单独证明理解。逆序是按章查漏而非又读一遍全文，结合候选、未覆盖提示及上下文重读。','',
         '正序日志：work/audit_forward.jsonl。倒查补读日志：work/audit_reverse_read.jsonl。机器范围汇总：audit_coverage.json。','']
    for chapter,decision in decisions:rev += [f'## 第{chapter}回',decision,'']
    write_md('audit_log.md',rev)
    richest=sorted(byperson.items(),key=lambda x:(-len(x[1]),x[0]))[:8]
    report=['# Phase 2：前八十回伏笔与未来指向证据审计报告','',
        '本阶段只建立证据、分歧和未回答问题。已完成Phase 2后停止，未进行Phase 3命运推演、后四十回规划或正文创作。','',
        f"- 证据：{len(rows)}条唯一F-ID；A {strength['A']}、B {strength['B']}、C {strength['C']}、D {strength['D']}。",
        f"- 正文：{layers['正文']}条；脂批：{layers['脂批']}条；其他允许材料作为文学F证据：0条。",
        f"- 冲突/反证：{len(conflicts)}组；未解决问题：{len(questions)}个，均未作答。",
        '- 状态：'+'；'.join(f'{STATUS[s]} {n}' for s,n in stats['status'].items())+'。',
        '- 人物关联最丰富：'+'、'.join(f'{p}（{len(ids)}）' for p,ids in richest)+'。计数含被涉及，不等于命运预测可靠度。',
        '- 正序1—80回正文及允许脂批全部审读；逆序80—1回查漏全部完成，逐回决定见audit_log.md。',
        '- 第5回14组图判、14支曲（含引子和收尾）全部建档；正册11单元中钗黛合写，不能误算成少一钗。','',
        '证据仍不足的问题包括：宝黛钗关系的具体决策过程；尚未实写的死亡提示所对应的具体方式和时间；政治危机的确切案由及责任；白首双星的对象；巧姐曲中亲属的身份；甄贾两玉的实际交接；三春的单一所指；情榜与框架销号如何展开。明确提示与具体机制之间仍有很大距离。','',
        '污染检查：没有访问禁读目录正文、续书、影视或现代具体重建方案，没有联网。逐条检查引文、说话层级和跨回归因，删去过短的“习射”独立条目，并撤回无直接根据的诗句→金玉婚后定向。保留以下POTENTIAL_CONTAMINATION弱候选：'+links(stats['potential_contamination'])+'；风险是将射覆物名联想为人物或婚配，没有排除训练记忆影响的客观方法。两条均D级，不得单独推论。其余CLEAR_LOCAL_SUPPORT表示有可回查本地依据，不表示能证明模型从未受记忆影响。','',
        '来源资格：canonical v1完整性校验通过，数据集SHA256为 `'+data['canonical_dataset_sha256']+'`。64、67回及22后段明确标补配；17/18分回、19/80回目不作独立谶证；第5回保持虎兔；41残批、50隔离开头、52缺题、75缺诗、78待定段均依冻结限制处理。未修改canonical。全局G001限制始终保留。','',
        'A/B是来源层，A/B/C/D是证据强度，二者字段独立。C编校只入版本资格表，D不确定材料不读取原文、不入文学证据；强度D不等于来源D。所有批语只称本地所标批本，不鉴定作者。','',
        '检索：`python3 research/phase2/tools/query_evidence.py F-0001`。JSON的evidence数组及key_to_id、字符偏移、N-ID、哈希可以机器精确引用；conflicts、unresolved_questions与两类索引也在同一JSON内。关系边不自动代表相互证实。','',
        '输出目录：`research/phase2/`。主交付：foreshadowing.md、foreshadowing.json、character_evidence_index.md、theme_evidence_index.md、conflicts.md、unresolved_questions.md、phase2_report.md。辅助：audit_log.md、audit_coverage.json、version_qualifications.json、special_inventory.md、validation.json、tools/。work/是提取与修订输入，不能代替已验证F库。','',
        'Git commit：以 `git log -1 --format=%H -- research/phase2/phase2_report.md` 解析本报告所属提交；提交不能在自身内容中写入自己的哈希。实际提交哈希在最终交付消息列出。','',
        '质量检查的最终机器结果见validation.json：唯一ID、引文逐字回查、位置哈希、引用完整性、必备索引、两轮覆盖及第5回条目数。']
    write_md('phase2_report.md',report)
    inv=['# 专项完整性清单','','## 第5回图判','']
    for r in rows:
        if r['key'].startswith('C005-ALBUM'):inv.append(f"- {links([r['id']])}：{'、'.join(r['characters'])}（有条件识别）；图像和判词同一记录保留。")
    inv += ['','## 第5回曲','']
    titles=['引子','终身悞','枉凝眉','恨无常','分骨肉','乐中悲','世难容','喜冤家','虚花悟','聪明累','留余庆','晚韶华','好事终','收尾：飞鸟各投林']
    for i,title in enumerate(titles,1):inv.append(f"- {title}：{links([key_to_id[f'C005-SONG-S{i:02}']])}")
    inv += ['','## 第一回框架','','石头下世、劫终返本质、刻石抄传、空空道人情空、僧道度脱、北邙销号、绛珠还泪、士隐悟离、雨村仕进及恩义、好了歌四组和解注的荣枯两向均可由以下记录回查：','',links([r['id'] for r in rows if r['chapter']==1]),'',
        '## 诗谜取舍','','第51回十怀古篇目：赤壁、交趾、钟山、淮阴、广陵、桃叶渡、青冢、马嵬、蒲东寺、梅花观。整体未解物谜已登记；七条另有主题性弱证。交趾、广陵、蒲东寺未强配未来人物或单独判作伏笔。',
        '第50回已揭谜底的四书/字谜不强解命运；湘云猴谜作歧义对照；钗宝黛三谜未明底；探春谜未念，不补。第63回八支花签均有独立记录。第64回五美吟五首有条件入库，十独吟只记录批语提示。第70回柳絮词含探春起句与宝玉续句分开；第76回联句保存悲句、现场动机及妙玉翻转。',
        '第75回诗缺文使“佳谶”不能被还原；第50回隔离开头不用于联诗发言归属，第52回不补题。其他诗词已在全文审读中核查，没有明显未来功能者未为数量而立条。']
    write_md('special_inventory.md',inv)
    print(json.dumps(stats,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
