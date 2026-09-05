#!/usr/bin/env python3
"""Deterministic local-only v1 builder. Refuses to overwrite a frozen release.
No web, no inferred words, no source writes. Offsets are Unicode [start,end).
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Dream-of-Red-Chamber-master'
CAN = ROOT / 'canonical'
EX = ROOT / 'excluded_sources/version_audit'
EDITIONS = ('紅樓夢庚辰本', '脂硯齋重評石頭記')
PROV, NOTE_RECORDS, MANIFEST, EXCLUDED = [], [], [], []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def rel(path):
    return str(path.relative_to(ROOT))


def span(text, start, end):
    return {'start_offset': start, 'end_offset': end,
            'start_line': text[:start].count('\n') + 1,
            'end_line': text[:max(start, end-1)].count('\n') + 1}


def braced(text, start):
    assert text[start] == '{'
    depth, j = 1, start + 1
    while j < len(text) and depth:
        if text[j] == '{' and text[j-1] != '\\': depth += 1
        if text[j] == '}' and text[j-1] != '\\': depth -= 1
        j += 1
    assert depth == 0, 'unbalanced TeX group'
    return text[start+1:j-1], j


def notes(text):
    pattern = re.compile(r'\\footnote(?:text)?(?:\[[^\]]*\])?\{')
    pos = 0
    while m := pattern.search(text, pos):
        body, end = braced(text, m.end()-1)
        yield m.start(), end, body
        pos = end


def chapter_title(text):
    m = re.match(r'\\chapter(?:\[([^\]]*)\])?\{', text)
    assert m
    body, end = braced(text, m.end()-1)
    title = m[1] or re.sub(r'\\footnotemark(?:\[[^\]]*\])?', '', body)
    assert '\\' not in title
    return title, end


def quarantine(name, raw, reason, source):
    path = EX / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw)
    record = {'path': rel(path), 'sha256': sha(path.read_bytes()),
              'reason': reason, 'source': source, 'allowed_for_inference': False}
    EXCLUDED.append(record)
    return rel(path)


def register(n, title, path, text, start, end, kind, replacement=None,
             reason='', supplement=False, confidence='high', allowed=False,
             current_override=None, current_ref=None):
    ident = f'P{len(PROV)+1:05d}'
    record = {'id': ident, 'chapter': n, 'title': title,
              'location': span(text, start, end), 'source': rel(path),
              'current_text': text[start:end] if current_override is None else current_override,
              'current_text_ref': current_ref, 'kind': kind,
              'is_supplement': supplement, 'confidence': confidence,
              'allowed_for_inference': allowed, 'reason': reason,
              'canonical_replacement': replacement}
    PROV.append(record)
    return ident


def selected(text, n):
    _, heading_end = chapter_title(text)
    if n == 62:
        a = text.index('話說平兒出來吩咐林之孝家的道')
        b = text.index('不知端詳，且聽下回分解。', a)+len('不知端詳，且聽下回分解。')
        return a, b
    if n == 67:
        a = text.index(r'\section*{列藏本}')+len(r'\section*{列藏本}')
        b = text.index(r'\section*{程甲本}')
        return a, b
    return heading_end, len(text)


def note_layer(body):
    if '似非脂批' in body:
        return 'undetermined', '来源按语对脂批身份提出疑问，暂不裁定'
    s = body.strip()
    if s.startswith(('按', '校者', '音按')) or '蒙本將' in s:
        return 'editorial', '明示编校、异文或来源说明'
    if re.match(r'^(?:前)?[甲庚己蒙戚靖列俄楊舒覺夢鄭][^：:；]{0,45}[：:；]', s) or s.startswith('脂批：'):
        return 'zhiyan', '保留本地传统批本标签；标签不证明批者身份或真伪'
    return 'undetermined', '脚注层明确，批者和年代来源不足；不擅归为脂批'


def export_notes(n, title, path, text, edition):
    lo, hi = selected(text, n)
    rows = []
    for index, (a, b, body) in enumerate(notes(text), 1):
        layer, why = ('editorial', '无批名义版脚注，按编校层处理') if edition == EDITIONS[0] else note_layer(body)
        if body.strip() == '太極圖': layer, why = 'undetermined', '疑正文题名误置脚注，不能凭排版恢复'
        active = lo <= a < hi
        original = body
        excluded_ref = None
        # Mixed modern reconstructions / Cheng-edition quotations stay outside canonical.
        if any(w in body for w in ['程甲', '程乙', '周汝昌', '戴不凡']):
            excluded_ref = quarantine(f'{n:03d}-{0 if edition==EDITIONS[0] else 1}-note-{index:04d}.txt', body,
                                       '含程本文字、混合版本说明或现代具体重建，整条原样隔离', rel(path))
            if any(w in body for w in ['周汝昌', '戴不凡']):
                body = re.sub(r'〈[^〉]*〉', '〔现代校释已隔离〕', body)
                layer, why = note_layer(body)
            else:
                body = '〔混合版本按语已隔离；只允许使用主清单所载来源事实〕'
                layer = 'editorial'
        # Preserve nested editorial notes as a separate layer, not as historical commentary.
        nested_ids = []
        for nested_index, angle in enumerate(re.finditer(r'〈([^〉]*)〉', original), 1):
            nested_id = f'E{n:03d}-{index:04d}-{nested_index:02d}'
            content = angle[1]
            contaminated = any(w in content for w in ['程甲','程乙','周汝昌','戴不凡'])
            start_in_source = a + text[a:b].index(original) + angle.start()
            NOTE_RECORDS.append({'id': nested_id, 'chapter':n,'title':title,'source':rel(path),
                'location':span(text,start_in_source,start_in_source+len(angle[0])),
                'layer':'editorial', 'current_text':'〔现代或混合来源校释已隔离〕' if contaminated else content,
                'raw_sha256':sha(content.encode()),'excluded_raw_ref':excluded_ref if contaminated else None,
                'in_selected_chapter_span':active,'confidence':'high','allowed_for_inference':False,
                'is_supplement':True if '今補' in content else 'unknown',
                'reason':'从传统批注容器内再剥离编者按语；其补批或校释不冒充原批。'})
            nested_ids.append(nested_id)
        body = re.sub(r'〈[^〉]*〉', '', body)
        note_id = f'N{n:03d}-{0 if edition==EDITIONS[0] else 1}-{index:04d}'
        row = {'id': note_id, 'chapter': n, 'title': title, 'source': rel(path),
               'location': span(text,a,b), 'layer': layer, 'current_text': body,
               'raw_sha256': sha(original.encode()), 'excluded_raw_ref': excluded_ref,
               'in_selected_chapter_span': active,
               'confidence': 'medium' if layer=='zhiyan' else 'low' if layer=='undetermined' else 'high',
               'allowed_for_inference': 'commentary_only_explicit_opt_in' if layer=='zhiyan' and active else False,
               'is_supplement': 'unknown' if layer=='undetermined' else False,
               'reason': why, 'nested_editorial_ids':nested_ids}
        NOTE_RECORDS.append(row); rows.append((a,b,row))
    # Angle editorial annotations outside footnotes also need their own record.
    for index,m in enumerate(re.finditer(r'〈([^〉]*)〉', text),1):
        if any(a <= m.start() < b for a,b,_ in rows): continue
        body = m[1]; excluded_ref = None
        if any(w in body for w in ['程甲','程乙','周汝昌','戴不凡']):
            excluded_ref = quarantine(f'{n:03d}-angle-{index:03d}.txt', body, '混合版本／现代重建按语',rel(path))
            body = '〔原文按语已隔离〕'
        NOTE_RECORDS.append({'id': f'A{n:03d}-{index:03d}', 'chapter':n,'title':title,
            'source':rel(path),'location':span(text,m.start(),m.end()),'layer':'editorial',
            'current_text':body,'excluded_raw_ref':excluded_ref,'raw_sha256':sha(m[1].encode()),
            'in_selected_chapter_span':lo<=m.start()<hi,'confidence':'high',
            'allowed_for_inference':False,'is_supplement':False,
            'reason':'尖括号为本地编者约定的按语标记；其中来源说法不当成正文'})
    return rows


def build_chapter(n, path, text):
    title, heading_end = chapter_title(text)
    lo, hi = selected(text,n)
    edits = []
    def patch(a,b,replacement,kind,reason,supplement=False,confidence='high',allowed=False,external=False):
        ref=None
        if external:
            ref=quarantine(f'{n:03d}-removed-{len(PROV):04d}.txt', text[a:b],reason,rel(path))
        pid=register(n,title,path,text,a,b,kind,replacement,reason,supplement,confidence,allowed,
                     current_override='〔原文字串在隔离附录〕' if external else None,current_ref=ref)
        edits.append((a,b,replacement,pid))
        return pid
    def mark(a,b,kind,reason,confidence='low'):
        pid=register(n,title,path,text,a,b,kind,None,reason,False,confidence,False)
        replacement=f'〔待定:{pid}〕' if 'undetermined' in kind else f'〔疑缺:{pid}〕' if kind=='lacuna_suspected' else f'〔缺文:{pid}〕'
        PROV[-1]['canonical_replacement']=replacement
        edits.append((a,b,replacement,pid));return pid
    if n==62:
        body61=(path.parent/'chapter61.tex').read_text().split('\n',1)[1]
        assert text.split('\n',1)[1].replace(text[lo:hi],'',1)==body61
        register(n,title,path,text,lo,hi,'recovered_chapter62',None,
            '从现有错接文件抽取独立本回；余文逐字符等于61回正文。错误已在zip内；上游环节无法追溯。',False,'high',True)
        register(n,title,path,text,heading_end,lo,'discard_duplicate61_prefix','',
                 '重复的61回前段，非62回叙事',False,'high',False)
        register(n,title,path,text,hi,len(text),'discard_duplicate61_suffix','',
                 '重复的61回后段，非62回叙事',False,'high',False)
    if n in (64,67):
        register(n,title,path,text,lo,hi,'whole_chapter_supplement',None,
            '64据README称主要俄藏；67据回内明示采用列藏（与README戚序说冲突）。仅为本地二手来源声明，未核手稿。',True,'medium','conditional_supplement',
            current_override='全回当前文本见 canonical/chapters/%03d.md；原始混合正文不在此重复。'%n)
    if n==64:
        a=text.index('忽然想起家人鮑二來')
        second=[(x,y,z) for x,y,z in notes(text) if '依庚辰本四十四回補' in z][0]
        patch(a,second[1],'賈珍又給了一房家人，名叫鮑二。','restore_locally_quoted_variant',
            '本地脚注明确引列藏、戚序此句，采用该引文替换程甲改句，并移除随后依44回扩补。未见影印，可靠性中；不得再把被删扩补当独立64回事实。',True,'medium','conditional_supplement',True)
    if n==50:
        line=text.splitlines(keepends=True)[2];a=sum(len(x) for x in text.splitlines(keepends=True)[:2]);b=a+len(line.rstrip('\n'))
        mark(a,b,'undetermined_commentary_overlap',
             '第3行明示此段批语混入正文，却无严格起讫。保守隔离整个原段；不宣称整段都是脂批，未裁定其中凤姐对话的层次。')
    # Every parenthesis in the base was inventoried. Unknown prose stays undecided.
    for m in re.finditer(r'（[^（）]*）|\([^()]*\)',text[:hi]):
        if not(lo<=m.start()<hi) or any(a<=m.start()<b for a,b,_,_ in edits):continue
        if any(a<=m.start()<b for a,b,_ in notes(text)):continue
        body=m.group()
        if n==78 and m.start()>=text.index('寶玉自立了半天'):
            mark(m.start(),m.end(),'undetermined_inline_variant','无来源的括号叙事，与周围重复；暂不归正文或脂批。')
        elif body in ('（左分右瓜）','（上喬下皿）'):
            patch(m.start(),m.end(),'','glyph_description','字形描述移到元数据；前面的□保留，未补造字形。')
        elif body=='（口害）':
            pid=mark(m.start(),m.end(),'undetermined_glyph','疑拆字表示，未确定实际字形；不擅补字。')
        elif '此處有缺文' in body:
            mark(m.start(),m.end(),'lacuna','保留明示缺文位置，篇幅未知。','high')
        else:
            assert body=='(kè)' or any(w in body for w in ['按：','校者','註：','有正','庚辰']),body
            patch(m.start(),m.end(),'','editorial_inline','明确校按、异文或读音说明，移出正文。')
    if n==36:
        a=text.index('蒙本回末批同。');patch(a,a+len('蒙本回末批同。'),'','commentary_residue','独立校注残留，不是叙事。')
    if n==78:
        a=text.index('</');patch(a,a+2,'','markup_residue','删除残留HTML片段，不补文字。')
    for ch,unit in [(40,'更助秋情。'),(49,'腳下也穿著'),(53,'賈母也')]:
        if n==ch:
            a=text.index(unit+unit);patch(a,a+len(unit+unit),unit,'adjacent_duplicate',
                '连续同字重出，保留一份；疑录入／整理复写，不能证明发生于哪一手稿。')
    # Remove all note containers in main text, leaving explicit uncertainty/gap markers.
    for a,b,body in notes(text):
        if not(lo<=a<hi) or any(x<=a<y for x,y,_,_ in edits):continue
        if body=='太極圖':
            mark(a,b,'undetermined_misplaced_title','题名疑误置脚注，不能擅填回正文。')
        elif ('缺文' in body or '缺去' in body or '缺「從此空空道人」' in body) and n!=22:
            mark(a,b,'lacuna_suspected' if '疑有缺文' in body else 'lacuna',body,'low' if '疑有缺文' in body else 'high')
        elif n==22 and '以下文字' in body:
            pid=patch(a,b,'','supplement_boundary','从此后以戚序配入、诸本汇校，原底本在此不全。',True,'medium','conditional_supplement')
            edits[-1]=(a,b,f'〔补配起:{pid}〕',pid); PROV[-1]['canonical_replacement']=edits[-1][2]
            register(n,title,path,text,b,hi,'supplement_span',None,'戚序配入并经诸本汇校；以本地按语为限。',True,'medium','conditional_supplement')
        else:
            patch(a,b,'','editorial_footnote','脚注已另层保存；异文并不自动替换正文。',False,'high',False)
    # Source glyph gaps and suspicious words remain present, flagged at their point.
    for m in re.finditer('□',text[lo:hi]):
        a=lo+m.start();pid=register(n,title,path,text,a,a+1,'missing_glyph',None,
                   '现有电子文本缺字；不猜字、不按记忆补字。',False,'high',False)
        edits.append((a,a+1,'□〔缺字:'+pid+'〕',pid));PROV[-1]['canonical_replacement']=edits[-1][2]
    if n==50:
        for word in ['花 碼 脂','擺階來志']:
            a=text.index(word);pid=register(n,title,path,text,a,a+len(word),'suspect_transcription',None,
                '词句疑损，无本地可靠替代；原样保留，不依其精确字面推理。',False,'low',False)
            edits.append((a,a+len(word),word+'〔待定:'+pid+'〕',pid));PROV[-1]['canonical_replacement']=edits[-1][2]
    # Known editorially selected variants / supplied headings.
    for ch,word,reason,supp in [
        (3,'兩彎似蹙非蹙罥煙眉，一雙似泣非泣含露目','眉目句有卞藏异文；未改现行句，精确用字须附异文限制。',False),
        (5,'虎兔','本地另记虎兕；保留虎兔，不按流行引文改动。',False),
        (49,'心中悶悶不解','校按明示采用戚、蒙、列异文而异于庚辰；保留现行汇校选择。',True),
        (49,'蘆雪广','编按明示依庚辰择字，其他本异文不混入正文。',True)]:
        if n==ch:
            a=text.index(word);register(n,title,path,text,a,a+len(word),'editorial_selection',None,reason,supp,'medium','conditional_variant')
    if n in (17,18,19,80):
        register(n,title,path,text,0,heading_end,'editorial_chapter_boundary_or_title',None,
            '17/18原未分回；19/80按语称庚辰无题。现行题目／分回仅为定位，不作独立谶语证据。',True,'medium',False)
    # Exact patch coordinates prevent accidental replacements in another passage.
    edits.sort()
    for prev,cur in zip(edits,edits[1:]):assert prev[1]<=cur[0],(n,prev,cur)
    for a,b,_,_ in edits:assert lo<=a<=b<=hi,(n,a,b,lo,hi)
    pieces=[];origins=[];cursor=lo
    for a,b,replacement,pid in edits:
        pieces.append(text[cursor:a]);origins.extend(range(cursor,a))
        pieces.append(replacement);origins.extend([a]*len(replacement));cursor=b
    pieces.append(text[cursor:hi]);origins.extend(range(cursor,hi))
    body=''.join(pieces);assert len(body)==len(origins)
    # TeX is presentation only. Keep all lexical text; no traditional/simplified conversion.
    tokens=list(re.finditer(r'\\(?:begin|end)\{[^}]+\}|\\footnotemark(?:\[[^\]]*\])?|\\(?:newline|scriptsize)\b|[{}]',body))
    for m in reversed(tokens):
        replacement='\n' if m.group()==r'\newline' else ''
        body=body[:m.start()]+replacement+body[m.end():]
        origins[m.start():m.end()]=[origins[m.start()]]*len(replacement)
    assert not re.search(r'\\[A-Za-z]',body),(n,'unhandled TeX')
    lines=[];mapping=[];offset=0
    for line in body.splitlines(keepends=True):
        clean=line.strip()
        if clean:
            first=offset+len(line)-len(line.lstrip()); last=offset+len(line.rstrip())-1
            mapping.append({'canonical_line':3+2*len(lines),'source':rel(path),
                'source_start_line':text[:origins[first]].count('\n')+1,
                'source_end_line':text[:origins[last]].count('\n')+1})
            lines.append(clean)
        offset+=len(line)
    result=f'# 第{n:03d}回　{title}\n\n'+'\n\n'.join(lines)+'\n'
    dest=CAN/f'chapters/{n:03d}.md';dest.write_text(result)
    dump(CAN/f'metadata/source_map/{n:03d}.json',{'chapter':n,'lines':mapping})
    records=[x for x in PROV if x['chapter']==n]
    pending=any('undetermined' in x['kind'] or x['kind']=='suspect_transcription' for x in records)
    gaps=any(x['kind'].startswith('lacuna') or x['kind']=='missing_glyph' for x in records)
    supplement=any(x['is_supplement'] for x in records)
    MANIFEST.append({'chapter':n,'title':title,'source':rel(path),
        'source_sha256':sha(text.encode()),'selected_source_span':span(text,lo,hi),
        'text_status':'recovered_local_segment' if n==62 else 'qualified_canonical',
        'completeness':'available_with_gaps_or_quarantine' if gaps or pending else 'available_no_known_body_gap',
        'contains_supplement':supplement,'contains_commentary':False,
        'contains_commentary_basis':'显式注容器、已知混入处已剥离；不能证明所有未标记文字皆无隐性混批。',
        'confidence':'medium' if supplement or pending or gaps else 'high_local_transcription_only',
        'notes':[x['id']+': '+x['reason'] for x in records if x['kind'] not in ['editorial_footnote','editorial_inline']],
        'path':rel(dest),'sha256':sha(dest.read_bytes()),'characters':len(result),
        'allowed_for_inference':'conditional_with_provenance' if supplement or pending or gaps else True})


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--initial-build',action='store_true');args=ap.parse_args()
    if not args.initial_build:raise SystemExit('Use --initial-build before freeze only. No implicit regeneration.')
    if (CAN/'metadata/freeze.json').exists():raise SystemExit('Frozen v1 exists: refuse overwrite. Create an explicitly authorized new release.')
    snapshot=[]
    for p in sorted(SOURCE.rglob('*')):
        if p.is_file():snapshot.append({'path':rel(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
    zipfile=ROOT/'Dream-of-Red-Chamber-master.zip'
    snapshot.append({'path':rel(zipfile),'bytes':zipfile.stat().st_size,'sha256':sha(zipfile.read_bytes())})
    dump(CAN/'metadata/source_snapshot.json',snapshot)
    for n in range(1,81):
        for edition in EDITIONS:
            path=SOURCE/edition/f'chapters/chapter{n:02d}.tex';text=path.read_text()
            title,_=chapter_title(text)
            if n==67:
                start=text.index(r'\section*{程甲本}')
                quarantine(f'067-{0 if edition==EDITIONS[0] else 1}-chengjia.tex',text[start:],
                           '程甲第67回独立附录，后续推演与续写禁止读取',rel(path))
            export_notes(n,title,path,text,edition)
        path=SOURCE/EDITIONS[0]/f'chapters/chapter{n:02d}.tex'
        build_chapter(n,path,path.read_text())
    for layer in ('zhiyan','editorial','undetermined'):
        for n in range(1,81):
            rows=[x for x in NOTE_RECORDS if x['chapter']==n and x['layer']==layer]
            rows.extend(x for x in PROV if x['chapter']==n and
                        (('undetermined' in x['kind'] or x['kind']=='suspect_transcription') if layer=='undetermined' else
                         x['kind'] in ('editorial_inline','glyph_description','commentary_residue') if layer=='editorial' else False))
            dump(CAN/f'annotations/{layer}/{n:03d}.json',rows)
    dump(CAN/'metadata/provenance.json',{'schema_version':1,'offset_convention':'Unicode [start,end), one-based lines',
        'scope':'已发现和可机器定位的补配、缺口及变更；逐字上游校改史不详，不宣称所有隐性改文已尽查。',
        'global_provenance':[
            {'id':'G001','chapter':'001-080','title':'全书上游汇校与字形整理',
             'location':'README:12,21,28-36; all canonical chapter bodies',
             'current_text_ref':'canonical/chapters/001.md ... 080.md',
             'source':'Dream-of-Red-Chamber-master/README.md',
             'is_supplement':'unknown_unlocalized','confidence':'low_upstream_history',
             'allowed_for_inference':'local_text_only_no_manuscript_purity_claim',
             'notes':'上游称来自维基文库汇校，少量自补按语，并将爲/幷/册/兎/别改作為/并/冊/兔/別。改动的逐字坐标与被删按语未提供；本轮不逆改，不伪造逐字来源。'},
            {'id':'G002','chapter':'001-080','title':'展示格式转换',
             'location':'all chapters; source_map gives paragraph/verse line correspondence',
             'current_text_ref':'canonical/chapters/',
             'source':'local TeX chapter files', 'is_supplement':False,'confidence':'high',
             'allowed_for_inference':False,
             'notes':'删除已识别TeX版式命令与分组花括号，newline转换为换行；去行首尾空白，以空行分隔原非空行；回目改为固定三位编号Markdown标题。〔缺文/疑缺/缺字/待定/补配起:P编号〕为本轮标记，绝非小说原文。'}],
        'records':PROV,'note_records':NOTE_RECORDS})
    dump(CAN/'metadata/chapter_manifest.json',MANIFEST)
    dump(EX/'inventory.json',EXCLUDED)
    assert all(sha((ROOT/x['path']).read_bytes())==x['sha256'] for x in snapshot)
    print(json.dumps({'chapters':len(MANIFEST),'provenance':len(PROV),
         'notes_by_layer':dict(collections.Counter(x['layer'] for x in NOTE_RECORDS)),
         'excluded_artifacts':len(EXCLUDED),'source_files_unchanged':len(snapshot)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
